import os
import shutil
from pathlib import Path


def ensure_env():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    # Use sqlite to satisfy settings without external DB
    os.environ.setdefault("DATABASE_URL", "sqlite:///db.sqlite3")
    # Default media root under repo if not set
    base_dir = Path(__file__).resolve().parents[1]
    os.environ.setdefault("MEDIA_ROOT", str(base_dir / "media"))

    # Configure remote upscaler from env, if provided
    # REAL_ESRGAN_HTTP_BASE, REAL_ESRGAN_API_KEY, REAL_ESRGAN_HTTP_PATH are read by settings


def main():
    ensure_env()
    import django

    django.setup()

    from django.conf import settings
    from apps.jobs.realesrgan import upscale_image
    from apps.common.image_ops import crop_bbox
    from PIL import Image

    media_root = Path(settings.MEDIA_ROOT)
    submission_dir = media_root / "submissions" / "submission_1"
    upscaled_dir = submission_dir / "upscaled"
    answers_dir = media_root / "answers" / "submission_1"
    for d in [submission_dir, upscaled_dir, answers_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Prepare input image
    repo_root = Path(__file__).resolve().parents[1]
    sample_src = repo_root / "test.jpg"
    if not sample_src.exists():
        raise FileNotFoundError(f"Sample image not found: {sample_src}")
    input_path = submission_dir / "page_001.jpg"
    shutil.copyfile(sample_src, input_path)

    # Upscale
    out_path = upscale_image(input_path, upscaled_dir)
    if not out_path.exists():
        raise RuntimeError("Upscaled image was not created")

    # Basic sanity check: dimensions increased
    with Image.open(input_path) as im_in, Image.open(out_path) as im_out:
        print(f"Input size: {im_in.size}, Upscaled size: {im_out.size}")
        if im_out.width <= im_in.width or im_out.height <= im_in.height:
            raise RuntimeError("Upscaled image is not larger than input")

    # Crop from upscaled image
    bbox = {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5, "normalized": True}
    cropped = crop_bbox(out_path, bbox)
    crop_path = answers_dir / "test_crop.jpg"
    cropped.save(crop_path, "JPEG", quality=95)
    print(f"OK - Upscaled: {out_path}, Cropped: {crop_path}")


if __name__ == "__main__":
    main()


