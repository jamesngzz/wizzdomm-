import os
import subprocess
from pathlib import Path
from typing import Optional
import io

from django.conf import settings
from PIL import Image

try:
    import requests  # type: ignore
except Exception:  # requests may not be installed in some envs
    requests = None  # type: ignore


def _binary_available() -> bool:
    bin_path = getattr(settings, "REAL_ESRGAN_BIN", None)
    return bool(bin_path and Path(bin_path).exists() and os.access(bin_path, os.X_OK))


def upscale_image(input_path: Path, output_dir: Path, scale: Optional[int] = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    scale = scale or int(getattr(settings, "REAL_ESRGAN_SCALE", 2))
    model = getattr(settings, "REAL_ESRGAN_MODEL", "realesrgan-x4plus")
    gpu_index = str(getattr(settings, "GPU_INDEX", 0))

    in_path = Path(input_path)
    # Resolve relative keys to absolute files under MEDIA_ROOT when using local storage
    if not in_path.is_absolute():
        candidate = Path(settings.MEDIA_ROOT) / in_path
        if candidate.exists():
            in_path = candidate
    out_path = output_dir / f"{in_path.stem}_x{scale}{in_path.suffix}"

    # Preferred: remote HTTP service if configured
    base_url = getattr(settings, "REAL_ESRGAN_HTTP_BASE", None)
    endpoint_path = getattr(settings, "REAL_ESRGAN_HTTP_PATH", "/upscale")
    api_key = getattr(settings, "REAL_ESRGAN_API_KEY", None)
    auth_header = getattr(settings, "REAL_ESRGAN_HTTP_AUTH_HEADER", "X-API-Key")
    if base_url and requests is not None:
        url = f"{base_url.rstrip('/')}{endpoint_path}"
        headers = {}
        if api_key:
            headers[auth_header] = str(api_key)
        try:
            with open(in_path, "rb") as fh:
                files = {"image": (in_path.name, fh, "application/octet-stream")}
                data = {"scale": str(scale), "model": model}
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
            resp.raise_for_status()
            # Try to read image bytes from response; support both raw bytes and JSON {image: base64}
            content_type = resp.headers.get("content-type", "")
            raw_bytes: bytes
            if "application/json" in content_type:
                try:
                    payload = resp.json()
                    import base64
                    raw_b64 = payload.get("image") or payload.get("data")
                    if not raw_b64:
                        raise ValueError("No image data in JSON response")
                    raw_bytes = base64.b64decode(raw_b64)
                except Exception as e:  # fall back to raw
                    raise RuntimeError(f"Invalid JSON response from upscaler: {e}")
            else:
                raw_bytes = resp.content
            # Persist to out_path
            with open(out_path, "wb") as out_f:
                out_f.write(raw_bytes)
            return out_path
        except Exception:
            # If remote fails, continue to other methods
            pass

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



