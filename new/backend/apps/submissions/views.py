from typing import List
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from apps.common.files import (
    validate_image_file,
    validate_pdf_file,
    save_uploaded_image,
    save_uploaded_pdf,
    delete_image_file,
    delete_image_files,
)
from pathlib import Path, PurePosixPath
from io import BytesIO
from tempfile import NamedTemporaryFile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from apps.exams.models import Exam, Question
from apps.common.image_ops import crop_bbox
from apps.common.files import normalized_path_exists
from .models import Submission, SubmissionItem
from .serializers import SubmissionSerializer
from apps.jobs.services import enqueue_upscale_submission
from apps.jobs.services import enqueue, enqueue_grade_item_if_not_exists
from .grading import grade_item_and_persist
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import uuid

# Register Unicode font for Vietnamese text support
UNICODE_FONT = 'Helvetica'  # Default fallback
try:
    # Try common font paths for different systems
    font_paths = [
        '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',  # macOS
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Linux alternative
        'C:\\Windows\\Fonts\\arial.ttf',  # Windows
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
            UNICODE_FONT = 'UnicodeFont'
            print(f"Registered Unicode font: {font_path}")
            break
except Exception as e:
    print(f"Could not register Unicode font, using Helvetica: {e}")

# Unicode symbols for correct/incorrect markers
CORRECT_ICON = "✓"  # or use "✅"
INCORRECT_ICON = "✗"  # or use "❌"


def decode_unicode_escapes(text):
    """Decode Unicode escape sequences in text"""
    if not isinstance(text, str):
        return text
    
    # Handle Unicode escape sequences like \u0394 (both literal and escaped)
    def replace_unicode(match):
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return match.group(0)
    
    # First try to decode literal escape sequences like \\u0394
    text = re.sub(r'\\\\u([0-9a-fA-F]{4})', replace_unicode, text)
    # Then try to decode actual escape sequences like \u0394
    text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
    
    return text

def normalize_math_text(raw_text: str) -> str:
    """Normalize LaTeX-ish math input to Unicode-friendly plain text.
    - Remove $...$ and \( \)
    - Replace '-' with true minus '−'
    - Convert ^digits to superscript digits
    - Normalize icons
    """
    try:
        if raw_text is None:
            return ''
        text = str(raw_text)
        # strip LaTeX delimiters
        text = re.sub(r"\\\\\(|\\\\\)", "", text)
        text = text.replace('$', '')
        # icons
        text = text.replace('✅','✓').replace('❌','✗').replace('⚠️','!').replace('⚠','!')
        # minus
        text = text.replace('-', '−')
        # superscript digits after caret
        sup_map = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹'}
        def sup_repl(m):
            return ''.join(sup_map.get(ch, ch) for ch in m.group(1))
        text = re.sub(r"\^(\d+)", sup_repl, text)
        return text
    except Exception:
        return str(raw_text or '')

def sanitize_saved_lines(saved_lines):
    """Fix lines accidentally saved as comma-joined graphemes like 'A,H, ,=, ,1'.
    Heuristic: if a line contains multiple commas, strip commas (and surrounding spaces).
    """
    try:
        fixed = []
        for ln in saved_lines or []:
            s = str(ln)
            if s.count(',') >= 2:
                s = re.sub(r"\s*,\s*", "", s)
            fixed.append(s)
        return fixed
    except Exception:
        return [str(ln) for ln in (saved_lines or [])]


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all().order_by("-id")
    serializer_class = SubmissionSerializer

    @action(detail=True, methods=["post"], url_path="upload")
    def upload(self, request, pk=None):
        submission = get_object_or_404(Submission, pk=pk)
        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

        saved_paths: List[str] = []
        target_dir = settings.MEDIA_SUBMISSIONS_DIR / f"submission_{submission.id}"

        for f in files:
            name = f.name.lower()
            if name.endswith(".pdf"):
                ok, msg = validate_pdf_file(f)
                if not ok:
                    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
                images = save_uploaded_pdf(f, target_dir, prefix=f"sub{submission.id}")
                saved_paths.extend([str(p) for p in images])
            else:
                ok, msg = validate_image_file(f)
                if not ok:
                    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
                img_path = save_uploaded_image(f, target_dir, prefix=f"sub{submission.id}")
                saved_paths.append(str(img_path))

        existing = submission.original_image_paths or []
        submission.original_image_paths = existing + saved_paths
        submission.save(update_fields=["original_image_paths"])

        # Enqueue upscaling job
        try:
            enqueue_upscale_submission(submission.id, submission.original_image_paths)
        except Exception:
            pass

        return Response({"image_paths": submission.original_image_paths}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="images")
    def images(self, request, pk=None):
        submission = get_object_or_404(Submission, pk=pk)
        paths = submission.original_image_paths or []
        urls = []
        for p in paths:
            try:
                sp = str(p)
                if default_storage.exists(sp):
                    urls.append(default_storage.url(sp))
                else:
                    urls.append(request.build_absolute_uri(f"{settings.MEDIA_URL.rstrip('/')}/{sp.lstrip('/')}"))
            except Exception:
                urls.append(str(p))
        return Response({"count": len(urls), "urls": urls})

    @action(detail=True, methods=["post"], url_path="items")
    def create_item(self, request, pk=None):
        submission = get_object_or_404(Submission, pk=pk)
        question_id = request.data.get("question_id")
        page_index = request.data.get("page_index")
        bbox = request.data.get("bbox")

        if not all([question_id is not None, page_index is not None, bbox]):
            return Response({"detail": "question_id, page_index, bbox are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            question = Question.objects.get(pk=int(question_id))
        except Exception:
            return Response({"detail": "Question not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            page_index = int(page_index)
        except Exception:
            return Response({"detail": "Invalid page_index"}, status=status.HTTP_400_BAD_REQUEST)

        paths = submission.original_image_paths or []
        if page_index < 0 or page_index >= len(paths):
            return Response({"detail": "Invalid page_index"}, status=status.HTTP_400_BAD_REQUEST)

        raw = str(paths[page_index])
        # Prefer upscaled page if available in storage
        pref = raw
        try:
            scale = int(getattr(settings, "REAL_ESRGAN_SCALE", 2))
        except Exception:
            scale = 2
        try:
            p = PurePosixPath(raw)
            up_dir = p.parent / "upscaled"
            up_name = f"{p.stem}_x{scale}{p.suffix}"
            up_key = str(up_dir / up_name)
            if default_storage.exists(up_key):
                pref = up_key
        except Exception:
            pref = raw

        if default_storage.exists(pref):
            with default_storage.open(pref, "rb") as src, NamedTemporaryFile(suffix=Path(pref).suffix, delete=False) as tmp:
                tmp.write(src.read())
                tmp.flush()
                src_path = Path(tmp.name)
        else:
            src_path = Path(pref)
            if not src_path.exists():
                return Response({"detail": "Source image not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cropped = crop_bbox(src_path, bbox)
        except Exception as e:
            return Response({"detail": f"Crop failed: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        # Save cropped answer via storage
        filename = f"ans_q{question.order_index}{question.part_label or ''}_{src_path.stem}.jpg"
        key = f"answers/submission_{submission.id}/{filename}"
        buf = BytesIO()
        cropped.save(buf, "JPEG", quality=95)
        try:
            default_storage.save(key, ContentFile(buf.getvalue()))
        except Exception as e:
            return Response({"detail": f"Failed to save answer image: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # original page dimensions for scaling annotations
        from PIL import Image as PILImage
        with PILImage.open(src_path) as original_img:
            orig_w, orig_h = int(original_img.width), int(original_img.height)

        item = SubmissionItem.objects.create(
            submission=submission,
            question=question,
            source_page_indices=[page_index],
            answer_image_paths=[key],
            has_multiple_images=False,
            answer_bbox=bbox,
            original_image_dimensions={"width": orig_w, "height": orig_h},
        )

        # Optionally enqueue grading job based on feature flag
        try:
            from django.conf import settings as dj_settings
            if getattr(dj_settings, "AUTO_GRADE_ON_CREATE", False):
                enqueue("GRADE_ITEM", {"submission_item_id": item.id})
        except Exception:
            pass

        return Response({
            "id": item.id,
            "submission": submission.id,
            "question": question.id,
            "source_page_indices": item.source_page_indices,
            "answer_image_paths": item.answer_image_paths,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="grade")
    def grade_submission(self, request, pk=None):
        """
        Grade all items in a submission concurrently using ThreadPoolExecutor.
        With concurrent grading, 10 items take ~15-20s instead of ~150s sequential.
        """
        submission = get_object_or_404(Submission, pk=pk)
        items = list(submission.items.all())
        
        if not items:
            return Response({"graded_count": 0, "message": "No items to grade"})
        
        # Concurrency limit: max workers for parallel grading
        # For 3-4 users, this means max 30-40 concurrent calls total
        max_concurrent = getattr(settings, 'MAX_CONCURRENT_GRADING', 10)
        
        # Non-blocking mode: enqueue each item if not already being graded
        job_ids = []
        for it in items:
            job_id = enqueue_grade_item_if_not_exists(it.id)
            if job_id:
                job_ids.append(job_id)
        return Response({
            "status": "queued",
            "queued_jobs": job_ids,
            "queued_count": len(job_ids),
            "total_items": len(items),
            "note": "Grading runs in background. You can navigate away and return to check results."
        })

    @action(detail=True, methods=["post"], url_path="regrade")
    def regrade_with_clarify(self, request, pk=None):
        """Regrade with clarification, also concurrent."""
        submission = get_object_or_404(Submission, pk=pk)
        clarify = request.data.get("clarify")
        
        if not clarify:
            return Response({"detail": "clarify is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        items = list(submission.items.all())
        
        if not items:
            return Response({"graded_count": 0, "clarify": clarify})
        
        # Same concurrency limit
        max_concurrent = getattr(settings, 'MAX_CONCURRENT_GRADING', 10)
        
        results = []
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all regrading tasks with clarify parameter
            future_to_item = {
                executor.submit(grade_item_and_persist, item, clarify): item 
                for item in items
            }
            
            for future in as_completed(future_to_item):
                try:
                    result = future.result()
                    results.append(result)
                    successful += 1
                except Exception as e:
                    item = future_to_item[future]
                    print(f"Failed to regrade item {item.id}: {e}")
                    failed += 1
        
        response_data = {
            "graded_count": successful,
            "total_items": len(items),
            "failed_count": failed,
            "clarify": clarify,
        }
        
        if failed > 0:
            response_data["message"] = f"{failed} items failed to regrade"
        
        return Response(response_data)

    @action(detail=True, methods=["get"], url_path="grading_summary")
    def grading_summary(self, request, pk=None):
        submission = get_object_or_404(Submission, pk=pk)
        items = submission.items.select_related("grading", "question").all()
        summary = []
        for it in items:
            g = getattr(it, "grading", None)
            
            # Decode Unicode escape sequences in critical_errors and part_errors
            critical_errors = getattr(g, "critical_errors", None)
            if critical_errors:
                critical_errors = self._decode_errors(critical_errors)
            
            part_errors = getattr(g, "part_errors", None)
            if part_errors:
                part_errors = self._decode_errors(part_errors)
            
            summary.append({
                "item_id": it.id,
                "question": {
                    "id": it.question.id,
                    "label": f"{it.question.order_index}{it.question.part_label or ''}",
                },
                "graded": bool(g),
                "is_correct": getattr(g, "is_correct", None),
                "critical_errors": critical_errors,
                "part_errors": part_errors,
                "partial_credit": getattr(g, "partial_credit", None),
            })
        return Response({
            "submission": submission.id,
            "student_name": submission.student_name,
            "items": summary,
        })
    
    @action(detail=True, methods=["get"], url_path="items-list")
    def list_items(self, request, pk=None):
        """List all submission items with image status"""
        submission = get_object_or_404(Submission, pk=pk)
        items = submission.items.select_related("question").all()
        result = []
        for item in items:
            # Remove any missing paths and persist cleanup
            raw_paths = item.answer_image_paths or []
            paths = [p for p in raw_paths if normalized_path_exists(p)]
            urls = []
            for p in paths:
                try:
                    sp = str(p)
                    if default_storage.exists(sp):
                        urls.append(default_storage.url(sp))
                    else:
                        urls.append(request.build_absolute_uri(f"{settings.MEDIA_URL.rstrip('/')}/{sp.lstrip('/')}"))
                except Exception:
                    urls.append(str(p))
            if paths != raw_paths:
                try:
                    item.answer_image_paths = paths
                    item.has_multiple_images = len(paths) > 1
                    item.save(update_fields=["answer_image_paths", "has_multiple_images"])
                except Exception:
                    pass
            
            result.append({
                "item_id": item.id,
                "question_id": item.question.id,
                "question_label": f"{item.question.order_index}{item.question.part_label or ''}",
                "has_images": len(paths) > 0,
                "image_count": len(paths),
                "image_urls": urls,
                "has_multiple_images": item.has_multiple_images,
            })
        
        return Response({"count": len(result), "items": result})

    def _decode_errors(self, errors):
        """Decode Unicode escape sequences in error objects"""
        if not errors:
            return errors
        
        decoded_errors = []
        for error in errors:
            if isinstance(error, dict):
                decoded_error = {}
                for key, value in error.items():
                    if isinstance(value, str):
                        decoded_error[key] = decode_unicode_escapes(value)
                    elif isinstance(value, list):
                        decoded_error[key] = [decode_unicode_escapes(item) if isinstance(item, str) else item for item in value]
                    else:
                        decoded_error[key] = value
                decoded_errors.append(decoded_error)
            else:
                decoded_errors.append(decode_unicode_escapes(str(error)) if isinstance(error, str) else error)
        
        return decoded_errors

    @action(detail=True, methods=["post"], url_path="export")
    def export_pdf(self, request, pk=None):
        # Helper: wrap text by a maximum width using current font metrics
        def wrap_text_to_width(text: str, font_name: str, font_size: int, max_width: float):
            try:
                sw = pdfmetrics.stringWidth
            except Exception:
                # Fallback: no wrapping if metrics unavailable
                return str(text or '').split('\n')

            paragraphs = str(text or '').split('\n')
            wrapped_lines = []
            for para in paragraphs:
                words = para.split()
                if not words:
                    wrapped_lines.append('')
                    continue
                line = words[0]
                for word in words[1:]:
                    trial = f"{line} {word}"
                    if sw(trial, font_name, font_size) <= max_width:
                        line = trial
                    else:
                        wrapped_lines.append(line)
                        line = word
                wrapped_lines.append(line)
            return wrapped_lines

        submission = get_object_or_404(Submission, pk=pk)
        images = submission.original_image_paths or []
        if not images:
            return Response({"detail": "No images to export"}, status=status.HTTP_400_BAD_REQUEST)

        export_dir = settings.MEDIA_EXPORTS_DIR
        export_dir.mkdir(parents=True, exist_ok=True)
        out_key = f"exports/submission_{submission.id}.pdf"

        # Create a PDF concatenating images to A4 pages and overlaying annotations
        from io import BytesIO
        pdf_buf = BytesIO()
        c = pdf_canvas.Canvas(pdf_buf, pagesize=A4)
        page_w, page_h = A4
        for page_idx, img_path in enumerate(images):
            try:
                sp = str(img_path)
                img_reader = None
                try:
                    if default_storage.exists(sp):
                        with default_storage.open(sp, "rb") as fh:
                            img_reader = ImageReader(BytesIO(fh.read()))
                except Exception:
                    img_reader = None
                if img_reader is None:
                    img_reader = ImageReader(str(sp))
                img = img_reader
                iw, ih = img.getSize()
                # fit into page with margins
                scale = min((page_w - 40) / iw, (page_h - 40) / ih)
                dw, dh = iw * scale, ih * scale
                x = (page_w - dw) / 2
                y = (page_h - dh) / 2
                c.drawImage(img, x, y, width=dw, height=dh, preserveAspectRatio=True, anchor='c')

                # Overlay annotations for items mapped to this page
                items = submission.items.select_related('grading', 'question').all()
                print(f"\nPage {page_idx}: Found {items.count()} items")
                
                # Removed page-level status header per requirement; status should come from annotations only
                
                # Now process annotations for each item
                for it in items:
                    src_pages = (it.source_page_indices or [])
                    print(f"  Item {it.id}: source_pages={src_pages}, annotations={len(it.annotations or [])}")
                    if page_idx not in src_pages:
                        continue
                    ann = it.annotations or []
                    print(f"  -> Processing {len(ann)} annotations for item {it.id}")
                    # Determine this image's index within the item's images
                    try:
                        image_slot_index = src_pages.index(page_idx)
                    except ValueError:
                        image_slot_index = 0
                    
                    # Get crop bbox to transform coordinates from crop-space to full-page-space
                    bbox = it.answer_bbox or {}
                    has_bbox = bbox.get('normalized') and 'x' in bbox and 'y' in bbox and 'w' in bbox and 'h' in bbox
                    
                    for obj in ann:
                        try:
                            otype = obj.get('type')
                            print(f"    Processing annotation: type={otype}, keys={list(obj.keys())}")

                            # Skip ALL rectangle boxes - we'll render clean text instead
                            if otype == 'rect':
                                print(f"      -> Skipping rect annotation completely")
                                continue

                            # Normalized annotations (0..1 relative to CROPPED answer image)
                            if 'x' in obj and 'y' in obj and 'w' in obj and 'h' in obj:
                                # Strict page gating:
                                # - If annotation has explicit 'page', render only when it matches image_slot_index
                                # - If no 'page', render only on first image (slot 0)
                                try:
                                    obj_page_val = obj.get('page')
                                    if obj_page_val is None:
                                        if image_slot_index != 0:
                                            print("      -> Skipping (no page, not first image)")
                                            continue
                                    else:
                                        if int(obj_page_val) != int(image_slot_index):
                                            print(f"      -> Skipping (page {obj_page_val} != slot {image_slot_index})")
                                            continue
                                except Exception:
                                    # On any error, default to draw only first image
                                    if image_slot_index != 0:
                                        continue
                                nx = float(obj.get('x', 0.0))
                                ny = float(obj.get('y', 0.0))
                                nw = float(obj.get('w', 0.0))
                                nh = float(obj.get('h', 0.0))
                                
                                # Transform coordinates from crop-space to full-image-space
                                if has_bbox:
                                    # Annotations are normalized to the CROP, not the full image
                                    # Step 1: Scale annotation by crop size
                                    # Step 2: Add crop offset
                                    bbox_x = float(bbox['x'])
                                    bbox_y = float(bbox['y'])
                                    bbox_w = float(bbox['w'])
                                    bbox_h = float(bbox['h'])
                                    
                                    nx = bbox_x + nx * bbox_w
                                    ny = bbox_y + ny * bbox_h
                                    nw = nw * bbox_w
                                    nh = nh * bbox_h
                                    print(f"      Transformed: bbox=({bbox_x:.3f},{bbox_y:.3f},{bbox_w:.3f},{bbox_h:.3f}) -> ann=({nx:.3f},{ny:.3f},{nw:.3f},{nh:.3f})")
                                
                                # Now nx, ny, nw, nh are normalized to FULL image
                                # Scale normalized -> drawn image space
                                left = x + nx * dw
                                top_img_space = ny * dh
                                width_scaled = nw * dw
                                height_scaled = nh * dh
                                
                                # Convert to reportlab coords (from bottom)
                                base_y = y + (dh - top_img_space - height_scaled)

                                if otype == 'rect':
                                    stroke = obj.get('stroke', '#ff0000')
                                    if isinstance(stroke, str) and stroke.startswith('#'):
                                        r = int(stroke[1:3], 16) / 255
                                        g = int(stroke[3:5], 16) / 255
                                        b = int(stroke[5:7], 16) / 255
                                        c.setStrokeColorRGB(r, g, b)
                                    else:
                                        c.setStrokeColorRGB(1, 0, 0)
                                    c.setLineWidth(int(obj.get('strokeWidth', 2)))
                                    c.rect(left, base_y, width_scaled, height_scaled, stroke=1, fill=0)
                                    print(f"      -> Drew rect at ({left}, {base_y}) size ({width_scaled}, {height_scaled})")
                                    
                                elif otype in ('textbox', 'text'):
                                    # If per-annotation page is present, render only on matching page
                                    try:
                                        ann_page = int(obj.get('page'))
                                        # Determine this item's image index among its answer images
                                        # It is '0' for first image for the item on this submission page
                                        # Since we iterate images as submission pages, require ann_page == 0 when matching current page
                                        # For multi-image items, compare ann_page with the index of this image within the item's list
                                        # Here we assume one image per submission page per item, so skip when page mismatch
                                        if ann_page != 0 and page_idx not in (it.source_page_indices or []):
                                            raise Exception('skip')
                                    except Exception as _:
                                        pass
                                    text = obj.get('text', '')
                                    text = normalize_math_text(decode_unicode_escapes(text))
                                    try:
                                        # Normalize icons to PDF-safe symbols
                                        text = text.replace('✅', '✓').replace('❌', '✗')
                                        text = text.replace('⚠️', '!').replace('⚠', '!')
                                        # Normalize common labels
                                        text = text.replace('Incorrect', 'sai').replace('Correct', 'đúng')
                                    except Exception:
                                        pass
                                    font_size = int(obj.get('fontSize', 16))
                                    line_height = float(obj.get('lineHeight', 1.2))
                                    text_align = (obj.get('textAlign') or 'left').lower()
                                    fill = obj.get('fill', '#ff0000')
                                    
                                    if isinstance(fill, str) and fill.startswith('#'):
                                        r = int(fill[1:3], 16) / 255
                                        g = int(fill[3:5], 16) / 255
                                        b = int(fill[5:7], 16) / 255
                                        c.setFillColorRGB(r, g, b)
                                    else:
                                        c.setFillColorRGB(1, 0, 0)
                                    
                                    c.setFont(UNICODE_FONT, font_size)
                                    # Prefer saved lines from the canvas for exact parity
                                    saved_lines = obj.get('lines')
                                    max_w = max(0, (width_scaled - 2))
                                    lines = sanitize_saved_lines(saved_lines) if isinstance(saved_lines, list) and saved_lines else \
                                        wrap_text_to_width(text, UNICODE_FONT, font_size, max_w)

                                    for i, line in enumerate(lines):
                                        try:
                                            # Horizontal alignment: left/center/right within the textbox
                                            if text_align == 'center':
                                                tx = left + (max_w - pdfmetrics.stringWidth(line, UNICODE_FONT, font_size)) / 2.0
                                            elif text_align == 'right':
                                                tx = left + (max_w - pdfmetrics.stringWidth(line, UNICODE_FONT, font_size))
                                            else:
                                                tx = left
                                            ty = base_y + height_scaled - (i + 1) * font_size * line_height
                                            c.drawString(tx, ty, line)
                                        except Exception as text_err:
                                            try:
                                                c.setFont('Helvetica', font_size)
                                                if text_align == 'center':
                                                    tx = left + (max_w - pdfmetrics.stringWidth(line, 'Helvetica', font_size)) / 2.0
                                                elif text_align == 'right':
                                                    tx = left + (max_w - pdfmetrics.stringWidth(line, 'Helvetica', font_size))
                                                else:
                                                    tx = left
                                                ty = base_y + height_scaled - (i + 1) * font_size * line_height
                                                c.drawString(tx, ty, line)
                                            except:
                                                pass
                                    print(f"      -> Drew text '{text}' at ({left}, {base_y})")
                                        
                                elif otype == 'circle':
                                    radius = float(obj.get('radius', 0.05)) * dw  # normalized radius
                                    cx = left + width_scaled / 2
                                    cy = base_y + height_scaled / 2
                                    stroke = obj.get('stroke', '#ff0000')
                                    if isinstance(stroke, str) and stroke.startswith('#'):
                                        r = int(stroke[1:3], 16) / 255
                                        g = int(stroke[3:5], 16) / 255
                                        b = int(stroke[5:7], 16) / 255
                                        c.setStrokeColorRGB(r, g, b)
                                    else:
                                        c.setStrokeColorRGB(1, 0, 0)
                                    c.setLineWidth(int(obj.get('strokeWidth', 2)))
                                    c.circle(cx, cy, radius, stroke=1, fill=0)
                                    print(f"      -> Drew circle at ({cx}, {cy}) radius {radius}")
                                continue

                            # Backward-compat: Fabric-style absolute objects
                            left = float(obj.get('left', 0))
                            top = float(obj.get('top', 0))
                            width = float(obj.get('width', 0))
                            height = float(obj.get('height', 0))
                            base_x = x + left
                            base_y = y + (dh - top - height)

                            if otype in ('textbox', 'text'):
                                # For legacy absolute objects, also gate by page if present
                                try:
                                    obj_page_val = obj.get('page')
                                    if obj_page_val is not None and int(obj_page_val) != 0:
                                        continue
                                except Exception:
                                    pass
                                text = obj.get('text', '')
                                # Standardize icons and Vietnamese labels for PDF
                                try:
                                    text = text.replace('✅', '✓').replace('❌', '✗')
                                    text = text.replace('⚠️', '!').replace('⚠', '!')
                                    # English -> Vietnamese for common labels
                                    text = text.replace('Incorrect', 'sai').replace('Correct', 'đúng')
                                except Exception:
                                    pass
                                text = normalize_math_text(decode_unicode_escapes(text))
                                font_size = int(obj.get('fontSize', 16))
                                line_height = float(obj.get('lineHeight', 1.2))
                                text_align = (obj.get('textAlign') or 'left').lower()
                                c.setFillColorRGB(1, 0, 0)
                                c.setFont(UNICODE_FONT, font_size)
                                # Prefer saved lines from the canvas
                                saved_lines = obj.get('lines')
                                max_w = max(0, (width - 2))
                                lines = sanitize_saved_lines(saved_lines) if isinstance(saved_lines, list) and saved_lines else \
                                    wrap_text_to_width(text, UNICODE_FONT, font_size, max_w)
                                for i, line in enumerate(lines):
                                    try:
                                        if text_align == 'center':
                                            tx = base_x + (max_w - pdfmetrics.stringWidth(line, UNICODE_FONT, font_size)) / 2.0
                                        elif text_align == 'right':
                                            tx = base_x + (max_w - pdfmetrics.stringWidth(line, UNICODE_FONT, font_size))
                                        else:
                                            tx = base_x
                                        ty = base_y + (height - (i + 1) * font_size * line_height)
                                        c.drawString(tx, ty, line)
                                    except:
                                        try:
                                            c.setFont('Helvetica', font_size)
                                            if text_align == 'center':
                                                tx = base_x + (max_w - pdfmetrics.stringWidth(line, 'Helvetica', font_size)) / 2.0
                                            elif text_align == 'right':
                                                tx = base_x + (max_w - pdfmetrics.stringWidth(line, 'Helvetica', font_size))
                                            else:
                                                tx = base_x
                                            ty = base_y + (height - (i + 1) * font_size * line_height)
                                            c.drawString(tx, ty, line)
                                        except:
                                            pass
                            elif otype == 'circle':
                                radius = float(obj.get('radius', min(width, height) / 2 or 20))
                                cx = x + (left + radius)
                                cy = y + (dh - (top + radius))
                                c.setStrokeColorRGB(1, 0, 0)
                                c.setLineWidth(2)
                                c.circle(cx, cy, radius, stroke=1, fill=0)
                        except Exception:
                            continue
                c.showPage()
            except Exception:
                continue
        c.save()
        # write via storage
        try:
            default_storage.save(out_key, ContentFile(pdf_buf.getvalue()))
            url = default_storage.url(out_key)
        except Exception:
            # fallback to local path
            abs_path = (export_dir / f"submission_{submission.id}.pdf")
            with open(abs_path, "wb") as fh:
                fh.write(pdf_buf.getvalue())
            rel = str(abs_path)[len(str(settings.MEDIA_ROOT)):].lstrip("/")
            url = request.build_absolute_uri(f"{settings.MEDIA_URL.rstrip('/')}/{rel}")
        return Response({"pdf_url": url})


class GradeItemAPIView(APIView):
    def post(self, request, item_id: int):
        try:
            item = SubmissionItem.objects.select_related("question", "submission").get(id=item_id)
        except SubmissionItem.DoesNotExist:
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        # Non-blocking: enqueue grading if not already running
        job_id = enqueue_grade_item_if_not_exists(item.id)
        return Response({"status": "queued", "job_id": job_id})


class ItemDetailAPIView(APIView):
    def get(self, request, item_id: int):
        try:
            item = SubmissionItem.objects.select_related("question", "submission").get(id=item_id)
        except SubmissionItem.DoesNotExist:
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        media_url = settings.MEDIA_URL.rstrip("/")

        def to_url(p: str) -> str:
            sp = str(p)
            try:
                if default_storage.exists(sp):
                    return default_storage.url(sp)
            except Exception:
                pass
            return f"{media_url}/{sp.lstrip('/')}"

        # Filter out missing files (unicode-safe) and persist cleanup
        existing_paths = []
        for p in (item.answer_image_paths or []):
            if normalized_path_exists(p):
                existing_paths.append(p)
        if existing_paths != (item.answer_image_paths or []):
            item.answer_image_paths = existing_paths
            item.has_multiple_images = len(existing_paths) > 1
            item.save(update_fields=["answer_image_paths", "has_multiple_images"])

        answer_urls = [to_url(p) for p in existing_paths]

        return Response({
            "id": item.id,
            "submission_id": item.submission_id,
            "question_id": item.question_id,
            "question_label": f"{item.question.order_index}{item.question.part_label or ''}",
            "source_page_indices": item.source_page_indices or [],
            "answer_image_paths": item.answer_image_paths or [],
            "answer_image_urls": answer_urls,
            "answer_bbox": item.answer_bbox,
            "original_image_dimensions": item.original_image_dimensions,
            "annotations": item.annotations,
            "grading": (lambda g: {
                "is_correct": getattr(g, "is_correct", None),
                "critical_errors": getattr(g, "critical_errors", None),
                "part_errors": getattr(g, "part_errors", None),
                "partial_credit": getattr(g, "partial_credit", None),
            } if g else None)(getattr(item, "grading", None)),
        })

    def put(self, request, item_id: int):
        import json
        print(f"\n=== PUT /items/{item_id}/ ===")
        print(f"Request data: {json.dumps(request.data, indent=2)}")
        
        try:
            item = SubmissionItem.objects.get(id=item_id)
        except SubmissionItem.DoesNotExist:
            print(f"Item {item_id} not found")
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data or {}
        annotations = data.get("annotations")
        
        print(f"Annotations received: {type(annotations)}, length: {len(annotations) if isinstance(annotations, list) else 'N/A'}")
        
        if annotations is None:
            print("ERROR: annotations is None")
            return Response({"detail": "annotations is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Sanitize annotations: normalize symbols and deduplicate exact duplicates
        def _normalize_text_symbols(text: str) -> str:
            try:
                # Normalize common icons to PDF-safe symbols
                normalized = str(text or "")
                normalized = normalized.replace('✅', '✓').replace('❌', '✗')
                # Replace warning emoji with ASCII to avoid tofu/rectangles in PDF
                normalized = normalized.replace('⚠️', '!').replace('⚠', '!')
                # Common label normalization
                normalized = normalized.replace('Incorrect', 'sai').replace('Correct', 'đúng')
                return normalized
            except Exception:
                return str(text or "")

        def _roundf(v):
            try:
                return round(float(v), 4)
            except Exception:
                return v

        def _dedup(anns):
            seen = set()
            cleaned = []
            for obj in anns or []:
                if not isinstance(obj, dict):
                    continue
                otype = obj.get('type')
                # Normalize text if present
                text = obj.get('text')
                if text is not None:
                    text = _normalize_text_symbols(text)
                # Build a dedup key based on type, geometry and text
                key = (
                    otype,
                    _roundf(obj.get('x')), _roundf(obj.get('y')),
                    _roundf(obj.get('w')), _roundf(obj.get('h')),
                    _roundf(obj.get('left')), _roundf(obj.get('top')),
                    _roundf(obj.get('width')), _roundf(obj.get('height')),
                    text,
                )
                if key in seen:
                    continue
                seen.add(key)
                # Write back normalized text
                if text is not None:
                    obj = {**obj, 'text': text}
                cleaned.append(obj)
            return cleaned

        annotations = _dedup(annotations)

        item.annotations = annotations
        item.save(update_fields=["annotations"])
        
        print(f"Saved {len(annotations) if isinstance(annotations, list) else 0} annotations to item {item_id}")
        print("=== END PUT ===\n")
        
        return Response({"id": item.id, "annotations": item.annotations})

    def delete(self, request, item_id: int):
        """Delete a submission item and its images"""
        try:
            item = SubmissionItem.objects.get(id=item_id)
        except SubmissionItem.DoesNotExist:
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Delete associated image files
        paths = item.answer_image_paths or []
        delete_image_files(paths)
        
        # Delete the item record (and cascade to grading)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ItemImageDeleteView(APIView):
    """Delete a specific image from a submission item"""
    
    def delete(self, request, item_id: int, image_index: int):
        try:
            item = SubmissionItem.objects.get(id=item_id)
        except SubmissionItem.DoesNotExist:
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        paths = item.answer_image_paths or []
        
        if image_index < 0 or image_index >= len(paths):
            return Response({"detail": "Invalid image index"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete the file
        image_path = paths[image_index]
        delete_image_file(image_path)
        
        # Remove from list
        paths.pop(image_index)
        item.answer_image_paths = paths
        item.has_multiple_images = len(paths) > 1
        item.save(update_fields=["answer_image_paths", "has_multiple_images"])
        
        return Response({"count": len(paths), "deleted_index": image_index}, status=status.HTTP_200_OK)


class ItemAppendImageView(APIView):
    """Append a new cropped answer image to an existing submission item"""

    def patch(self, request, item_id: int):
        try:
            item = SubmissionItem.objects.select_related("question", "submission").get(id=item_id)
        except SubmissionItem.DoesNotExist:
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        page_index = request.data.get("page_index")
        bbox = request.data.get("bbox")
        if page_index is None or bbox is None:
            return Response({"detail": "page_index and bbox are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            page_index = int(page_index)
        except Exception:
            return Response({"detail": "Invalid page_index"}, status=status.HTTP_400_BAD_REQUEST)

        submission = item.submission
        paths = submission.original_image_paths or []
        if page_index < 0 or page_index >= len(paths):
            return Response({"detail": "Invalid page_index"}, status=status.HTTP_400_BAD_REQUEST)

        raw = str(paths[page_index])
        # Prefer upscaled page if available in storage
        pref = raw
        try:
            scale = int(getattr(settings, "REAL_ESRGAN_SCALE", 2))
        except Exception:
            scale = 2
        try:
            p = PurePosixPath(raw)
            up_dir = p.parent / "upscaled"
            up_name = f"{p.stem}_x{scale}{p.suffix}"
            up_key = str(up_dir / up_name)
            if default_storage.exists(up_key):
                pref = up_key
        except Exception:
            pref = raw

        if default_storage.exists(pref):
            with default_storage.open(pref, "rb") as src, NamedTemporaryFile(suffix=Path(pref).suffix, delete=False) as tmp:
                tmp.write(src.read())
                tmp.flush()
                src_path = Path(tmp.name)
        else:
            src_path = Path(pref)
            if not normalized_path_exists(src_path):
                return Response({"detail": "Source image not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cropped = crop_bbox(src_path, bbox)
        except Exception as e:
            return Response({"detail": f"Crop failed: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        filename = f"ans_q{item.question.order_index}{item.question.part_label or ''}_{uuid.uuid4().hex[:8]}.jpg"
        key = f"answers/submission_{submission.id}/{filename}"
        buf = BytesIO()
        cropped.save(buf, "JPEG", quality=95)
        try:
            default_storage.save(key, ContentFile(buf.getvalue()))
        except Exception as e:
            return Response({"detail": f"Failed to save answer image: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        existing_paths = item.answer_image_paths or []
        existing_paths.append(key)
        item.answer_image_paths = existing_paths
        item.has_multiple_images = len(existing_paths) > 1
        # Also record page index mapping
        src_pages = item.source_page_indices or []
        src_pages.append(page_index)
        item.source_page_indices = src_pages
        item.save(update_fields=["answer_image_paths", "has_multiple_images", "source_page_indices"])

        # Build URLs back
        urls = []
        for p in existing_paths:
            sp = str(p)
            try:
                if default_storage.exists(sp):
                    urls.append(default_storage.url(sp))
                else:
                    # fallback to MEDIA_URL relative
                    urls.append(request.build_absolute_uri(f"{settings.MEDIA_URL.rstrip('/')}/{sp.lstrip('/')}"))
            except Exception:
                urls.append(sp)

        return Response({
            "item_id": item.id,
            "count": len(existing_paths),
            "image_paths": existing_paths,
            "image_urls": urls,
            "has_multiple_images": item.has_multiple_images,
        }, status=status.HTTP_200_OK)

