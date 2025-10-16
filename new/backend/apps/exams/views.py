from typing import List

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.files import (
    validate_image_file,
    validate_pdf_file,
    save_uploaded_image,
    save_uploaded_pdf,
    delete_image_file,
    delete_image_files,
)
from pathlib import Path
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from apps.common.image_ops import crop_bbox
from apps.common.labels import parse_question_label
from .models import Exam, Question
from .serializers import ExamSerializer, QuestionSerializer
from .solver import solve_question


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all().order_by("-id")
    serializer_class = ExamSerializer

    @action(detail=True, methods=["post"], url_path="upload")
    def upload(self, request, pk=None):
        exam = get_object_or_404(Exam, pk=pk)
        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

        saved_paths: List[str] = []
        target_dir = settings.MEDIA_EXAMS_DIR / f"exam_{exam.id}"

        for f in files:
            name = f.name.lower()
            if name.endswith(".pdf"):
                ok, msg = validate_pdf_file(f)
                if not ok:
                    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
                images = save_uploaded_pdf(f, target_dir, prefix=f"exam{exam.id}")
                saved_paths.extend([str(p) for p in images])
            else:
                ok, msg = validate_image_file(f)
                if not ok:
                    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
                img_path = save_uploaded_image(f, target_dir, prefix=f"exam{exam.id}")
                saved_paths.append(str(img_path))

        # Merge with existing
        existing = exam.original_image_paths or []
        merged = existing + saved_paths
        exam.original_image_paths = merged
        exam.save(update_fields=["original_image_paths"])

        return Response({"image_paths": merged}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="images")
    def images(self, request, pk=None):
        exam = get_object_or_404(Exam, pk=pk)
        paths = exam.original_image_paths or []
        media_root = str(settings.MEDIA_ROOT)
        media_url = settings.MEDIA_URL.rstrip("/")
        urls = []
        for p in paths:
            try:
                sp = str(p)
                # Handle Unicode normalization issues by normalizing both paths
                import unicodedata
                normalized_path = unicodedata.normalize('NFC', sp)
                normalized_media_root = unicodedata.normalize('NFC', media_root)
                
                if normalized_path.startswith(normalized_media_root):
                    rel = normalized_path[len(normalized_media_root):].lstrip("/")
                    # Build absolute URL so FE on a different port can load it
                    urls.append(request.build_absolute_uri(f"{media_url}/{rel}"))
                else:
                    # fallback: return as-is; browser may still access if served
                    urls.append(sp)
            except Exception:
                urls.append(p)
        return Response({"count": len(urls), "urls": urls})

    @action(detail=True, methods=["get"], url_path="questions")
    def questions(self, request, pk=None):
        exam = get_object_or_404(Exam, pk=pk)
        qs = Question.objects.filter(exam=exam).order_by("order_index", "part_label")
        data = [
            {
                "id": q.id,
                "label": f"{q.order_index}{q.part_label or ''}",
            }
            for q in qs
        ]
        return Response({"count": len(data), "items": data})


class QuestionViewSet(viewsets.GenericViewSet):
    queryset = Question.objects.all().order_by("exam_id", "order_index", "part_label")
    serializer_class = QuestionSerializer

    def list(self, request):
        """List all questions"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exam_id = serializer.validated_data["exam"].id if hasattr(serializer.validated_data["exam"], "id") else serializer.validated_data["exam"]
        exam = get_object_or_404(Exam, pk=exam_id)
        label = serializer.validated_data["label"]
        page_index = serializer.validated_data["page_index"]
        bbox = serializer.validated_data["bbox"]

        paths = exam.original_image_paths or []
        if page_index < 0 or page_index >= len(paths):
            return Response({"detail": "Invalid page_index"}, status=status.HTTP_400_BAD_REQUEST)

        src_path = Path(paths[page_index])
        if not src_path.exists():
            return Response({"detail": "Source image not found"}, status=status.HTTP_400_BAD_REQUEST)

        # crop
        try:
            cropped = crop_bbox(src_path, bbox)
        except Exception as e:
            return Response({"detail": f"Crop failed: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        # save via storage (S3 or local)
        order_index, part_label = parse_question_label(label)
        filename = f"q_{order_index}{part_label or ''}_{src_path.stem}.jpg"
        key = f"questions/exam_{exam.id}/{filename}"
        buf = BytesIO()
        cropped.save(buf, "JPEG", quality=95)
        default_storage.save(key, ContentFile(buf.getvalue()))

        question = Question.objects.create(
            exam=exam,
            question_image_paths=[key],
            has_multiple_images=False,
            order_index=order_index,
            part_label=part_label,
        )

        return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="solve")
    def solve(self, request, pk=None):
        question = get_object_or_404(Question, pk=pk)
        paths = question.question_image_paths or []
        if not paths:
            return Response({"detail": "No question images"}, status=status.HTTP_400_BAD_REQUEST)
        solution = solve_question(paths)
        question.solution_answer = solution.get("answer")
        question.solution_steps = solution.get("steps")
        question.solution_points = [s.get("points", 0) for s in solution.get("steps", [])]
        question.solution_generated_at = solution.get("generated_at")
        question.save(update_fields=["solution_answer", "solution_steps", "solution_points", "solution_generated_at"])
        return Response(solution)

    @action(detail=True, methods=["get"], url_path="solution")
    def get_solution(self, request, pk=None):
        question = get_object_or_404(Question, pk=pk)
        return Response({
            "answer": question.solution_answer,
            "steps": question.solution_steps,
            "points": question.solution_points,
            "generated_at": question.solution_generated_at,
            "verified": bool(question.solution_verified),
        })

    @action(detail=True, methods=["post"], url_path="verify")
    def verify_solution(self, request, pk=None):
        question = get_object_or_404(Question, pk=pk)
        body = request.data or {}
        verified = body.get("verified")
        if verified is None:
            return Response({"detail": "verified is required (true/false)"}, status=status.HTTP_400_BAD_REQUEST)
        question.solution_verified = bool(verified)
        question.save(update_fields=["solution_verified"])
        return Response({"id": question.id, "verified": question.solution_verified})

    @action(detail=True, methods=["get"], url_path="images")
    def get_images(self, request, pk=None):
        """Get all question image URLs"""
        question = get_object_or_404(Question, pk=pk)
        paths = question.question_image_paths or []
        media_root = str(settings.MEDIA_ROOT)
        media_url = settings.MEDIA_URL.rstrip("/")
        urls = []
        for p in paths:
            try:
                sp = str(p)
                import unicodedata
                normalized_path = unicodedata.normalize('NFC', sp)
                normalized_media_root = unicodedata.normalize('NFC', media_root)
                
                if normalized_path.startswith(normalized_media_root):
                    rel = normalized_path[len(normalized_media_root):].lstrip("/")
                    urls.append(request.build_absolute_uri(f"{media_url}/{rel}"))
                else:
                    urls.append(sp)
            except Exception:
                urls.append(p)
        return Response({
            "count": len(urls),
            "urls": urls,
            "has_multiple": question.has_multiple_images
        })

    def destroy(self, request, pk=None):
        """Delete a question and its images"""
        question = get_object_or_404(Question, pk=pk)
        # Delete associated image files
        paths = question.question_image_paths or []
        delete_image_files(paths)
        # Delete the question record
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="images/(?P<image_index>[0-9]+)")
    def delete_image(self, request, pk=None, image_index=None):
        """Delete a specific image from a question"""
        question = get_object_or_404(Question, pk=pk)
        paths = question.question_image_paths or []
        
        try:
            idx = int(image_index)
            if idx < 0 or idx >= len(paths):
                return Response({"detail": "Invalid image index"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete the file
            image_path = paths[idx]
            delete_image_file(image_path)
            
            # Remove from list
            paths.pop(idx)
            question.question_image_paths = paths
            question.has_multiple_images = len(paths) > 1
            question.save(update_fields=["question_image_paths", "has_multiple_images"])
            
            return Response({"count": len(paths), "deleted_index": idx}, status=status.HTTP_200_OK)
        except (ValueError, IndexError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"], url_path="append-image")
    def append_image(self, request, pk=None):
        """Append a new cropped image to an existing question"""
        question = get_object_or_404(Question, pk=pk)
        page_index = request.data.get("page_index")
        bbox = request.data.get("bbox")
        
        if page_index is None or bbox is None:
            return Response({"detail": "page_index and bbox required"}, status=status.HTTP_400_BAD_REQUEST)
        
        exam = question.exam
        paths = exam.original_image_paths or []
        if page_index < 0 or page_index >= len(paths):
            return Response({"detail": "Invalid page_index"}, status=status.HTTP_400_BAD_REQUEST)
        
        src_path = Path(paths[page_index])
        if not src_path.exists():
            return Response({"detail": "Source image not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Crop the image
        try:
            cropped = crop_bbox(src_path, bbox)
        except Exception as e:
            return Response({"detail": f"Crop failed: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Save with unique filename via storage
        import uuid
        filename = f"q_{question.order_index}{question.part_label or ''}_{uuid.uuid4().hex[:8]}.jpg"
        key = f"questions/exam_{exam.id}/{filename}"
        buf = BytesIO()
        cropped.save(buf, "JPEG", quality=95)
        default_storage.save(key, ContentFile(buf.getvalue()))
        
        # Append to existing paths
        existing_paths = question.question_image_paths or []
        existing_paths.append(key)
        question.question_image_paths = existing_paths
        question.has_multiple_images = len(existing_paths) > 1
        question.save(update_fields=["question_image_paths", "has_multiple_images"])
        
        return Response({
            "id": question.id,
            "image_count": len(existing_paths),
            "has_multiple_images": question.has_multiple_images
        }, status=status.HTTP_200_OK)


