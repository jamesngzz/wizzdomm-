import os
import uuid
from pathlib import Path
from typing import Tuple, List, Union
import unicodedata

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
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


def save_uploaded_image(upload: UploadedFile, target_dir: Path, prefix: str = "") -> Path:
    _ensure_dir(target_dir)
    filename = _safe_filename(prefix, upload.name)
    dest = target_dir / filename
    with dest.open("wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)
    # verify image can be opened
    Image.open(dest).verify()
    return dest


def save_uploaded_pdf(upload: UploadedFile, target_dir: Path, prefix: str = "", dpi: int = 200) -> List[Path]:
    _ensure_dir(target_dir)
    filename = _safe_filename(prefix or "document", upload.name)
    pdf_path = target_dir / filename
    with pdf_path.open("wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)
    # convert to images
    pages = convert_from_path(str(pdf_path), dpi=dpi)
    image_paths: List[Path] = []
    for idx, page in enumerate(pages, 1):
        img_name = f"{pdf_path.stem}_p{idx:03d}.jpg"
        img_path = target_dir / img_name
        page.save(str(img_path), "JPEG", quality=95)
        image_paths.append(img_path)
    return image_paths


def delete_image_file(image_path: Union[str, Path]) -> bool:
    """
    Delete an image file from disk.
    Returns True if deleted, False if file doesn't exist or error occurred.
    """
    try:
        path = Path(image_path)
        if path.exists() and path.is_file():
            path.unlink()
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


