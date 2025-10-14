import os
import subprocess
from pathlib import Path
from typing import Optional

from django.conf import settings
from PIL import Image


def _binary_available() -> bool:
    bin_path = getattr(settings, "REAL_ESRGAN_BIN", None)
    return bool(bin_path and Path(bin_path).exists() and os.access(bin_path, os.X_OK))


def upscale_image(input_path: Path, output_dir: Path, scale: Optional[int] = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    scale = scale or int(getattr(settings, "REAL_ESRGAN_SCALE", 2))
    model = getattr(settings, "REAL_ESRGAN_MODEL", "realesrgan-x4plus")
    gpu_index = str(getattr(settings, "GPU_INDEX", 0))

    in_path = Path(input_path)
    out_path = output_dir / f"{in_path.stem}_x{scale}{in_path.suffix}"

    if _binary_available():
        cmd = [
            settings.REAL_ESRGAN_BIN,
            "-i", str(in_path),
            "-o", str(out_path),
            "-n", model,
            "-s", str(scale),
            "-g", gpu_index,
        ]
        subprocess.run(cmd, check=True)
        return out_path

    # Fallback: simple PIL resize to simulate upscaling
    with Image.open(in_path) as img:
        new_size = (int(img.width * scale), int(img.height * scale))
        up = img.resize(new_size, Image.LANCZOS)
        up.save(out_path)
    return out_path



