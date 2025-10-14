from pathlib import Path
from typing import Dict
from PIL import Image


def crop_bbox(image_path: Path, bbox: Dict) -> Image.Image:
    """Crop an image by bbox.

    Supports two bbox formats:
    - Absolute pixels: { left, top, width, height } or { x, y, w, h }
    - Normalized 0..1: { x, y, w, h, normalized: true } or values <= ~1.0

    Values are clamped to the image bounds and minimally sized.
    """
    img = Image.open(image_path)
    img_w, img_h = img.size

    def clamp(value: int, low: int, high: int) -> int:
        return max(low, min(value, high))

    # Parse bbox variants
    if "x" in bbox and "w" in bbox:
        x = float(bbox.get("x", 0))
        y = float(bbox.get("y", 0))
        w = float(bbox.get("w", 0))
        h = float(bbox.get("h", 0))
        is_normalized = bool(bbox.get("normalized", False)) or (
            0.0 <= x <= 1.2 and 0.0 <= y <= 1.2 and 0.0 <= w <= 1.2 and 0.0 <= h <= 1.2
        )
        if is_normalized:
            left = int(round(x * img_w))
            top = int(round(y * img_h))
            width = int(round(w * img_w))
            height = int(round(h * img_h))
        else:
            left = int(round(x))
            top = int(round(y))
            width = int(round(w))
            height = int(round(h))
    else:
        left = int(round(float(bbox.get("left", 0))))
        top = int(round(float(bbox.get("top", 0))))
        width = int(round(float(bbox.get("width", 0))))
        height = int(round(float(bbox.get("height", 0))))

    # Ensure sane and in-bounds crop
    left = clamp(left, 0, max(0, img_w - 1))
    top = clamp(top, 0, max(0, img_h - 1))
    width = max(1, width)
    height = max(1, height)
    right = clamp(left + width, left + 1, img_w)
    bottom = clamp(top + height, top + 1, img_h)

    cropped = img.crop((left, top, right, bottom))

    # Convert RGBA to RGB if necessary (for JPEG compatibility)
    if cropped.mode == 'RGBA':
        rgb_img = Image.new('RGB', cropped.size, (255, 255, 255))
        rgb_img.paste(cropped, mask=cropped.split()[3])  # Use alpha channel as mask
        return rgb_img
    elif cropped.mode not in ('RGB', 'L'):
        # Convert other modes to RGB
        return cropped.convert('RGB')

    return cropped



