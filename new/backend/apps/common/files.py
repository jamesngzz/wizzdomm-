import os
import uuid
from pathlib import Path
from typing import Tuple, List, Union
import unicodedata

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
from pdf2image import convert_from_path


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_filename(prefix: str, original_name: str) -> str:
    ext = os.path.splitext(original_name)[1].lower()
    base = prefix.strip().replace(" ", "_") or "file"
    return f"{base}_{uuid.uuid4().hex}{ext}"


def validate_image_file(upload: UploadedFile) -> Tuple[bool, str]:
    name = upload.name.lower()
    size_mb = upload.size / (1024 * 1024)
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        return False, f"Image too large (> {settings.MAX_IMAGE_SIZE_MB} MB)"
    if not any(name.endswith(f".{ext}") for ext in settings.SUPPORTED_IMAGE_FORMATS):
        return False, "Unsupported image format"
    return True, "ok"


def validate_pdf_file(upload: UploadedFile) -> Tuple[bool, str]:
    size_mb = upload.size / (1024 * 1024)
    if size_mb > settings.MAX_PDF_SIZE_MB:
        return False, f"PDF too large (> {settings.MAX_PDF_SIZE_MB} MB)"
    if not upload.name.lower().endswith(".pdf"):
        return False, "Unsupported PDF format"
    return True, "ok"


def _to_key(target_dir: Path, filename: str) -> str:
    """Build a storage key relative to MEDIA_ROOT.

    If target_dir is under settings.MEDIA_ROOT, strip that prefix; otherwise
    fall back to the raw string (useful in dev).
    """
    base_path = Path(target_dir)
    try:
        rel = base_path.relative_to(settings.MEDIA_ROOT)
        base = str(rel).strip("/")
    except Exception:
        base = str(base_path).strip("/")
    return f"{base}/{filename}" if base else filename


def save_uploaded_image(upload: UploadedFile, target_dir: Path, prefix: str = "") -> Path:
    """Save an uploaded image using the active storage backend.

    Returns a pathlib.Path representing the logical key (for backward compat).
    """
    filename = _safe_filename(prefix, upload.name)
    key = _to_key(target_dir, filename)
    # Write via storage
    content = ContentFile(b"".join(upload.chunks()))
    default_storage.save(key, content)
    # Verify image by opening back from storage
    with default_storage.open(key, "rb") as fh:
        Image.open(fh).verify()
    return Path(key)


def save_uploaded_pdf(upload: UploadedFile, target_dir: Path, prefix: str = "", dpi: int = 200) -> List[Path]:
    """Store the uploaded PDF, convert to images, and save via storage backend.

    Returns a list of logical keys as Path objects.
    """
    # Save the raw PDF first via storage
    pdf_filename = _safe_filename(prefix or "document", upload.name)
    pdf_key = _to_key(target_dir, pdf_filename)
    default_storage.save(pdf_key, ContentFile(b"".join(upload.chunks())))

    # Convert to images using a local temp file handle
    # Download/open from storage for conversion
    from tempfile import NamedTemporaryFile
    with default_storage.open(pdf_key, "rb") as src, NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(src.read())
        tmp.flush()
        pages = convert_from_path(tmp.name, dpi=dpi)

    image_paths: List[Path] = []
    for idx, page in enumerate(pages, 1):
        img_name = f"{Path(pdf_filename).stem}_p{idx:03d}.jpg"
        img_key = _to_key(target_dir, img_name)
        from io import BytesIO
        buf = BytesIO()
        page.save(buf, "JPEG", quality=95)
        default_storage.save(img_key, ContentFile(buf.getvalue()))
        image_paths.append(Path(img_key))
    return image_paths


def delete_image_file(image_path: Union[str, Path]) -> bool:
    """
    Delete an image file from disk.
    Returns True if deleted, False if file doesn't exist or error occurred.
    """
    try:
        key = str(image_path)
        if default_storage.exists(key):
            default_storage.delete(key)
            return True
        return False
    except Exception as e:
        print(f"Error deleting image file {image_path}: {e}")
        return False


def delete_image_files(image_paths: List[str | Path]) -> int:
    """
    Delete multiple image files from disk.
    Returns the count of successfully deleted files.
    """
    count = 0
    for path in image_paths:
        if delete_image_file(path):
            count += 1
    return count


# --- Robust filesystem helpers ---
def _normalize_path_variants(path_like: Union[str, Path]) -> List[Path]:
    """
    Return common Unicode-normalized variants (NFC/NFD) of a filesystem path.
    This mitigates macOS/APFS normalization mismatches (e.g., "học" vs "ho\u0323c").
    """
    s = str(path_like)
    return [
        Path(unicodedata.normalize("NFC", s)),
        Path(unicodedata.normalize("NFD", s)),
    ]


def normalized_path_exists(path_like: Union[str, Path]) -> bool:
    """Check whether a path exists, trying both NFC and NFD representations."""
    for candidate in _normalize_path_variants(path_like):
        try:
            if candidate.exists():
                return True
        except Exception:
            # Fall through and try other variants
            pass
    return False


