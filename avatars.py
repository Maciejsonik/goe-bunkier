"""Helper for caching and retrieving channel avatar images."""

import hashlib
import io
import os
import urllib.request
from PIL import Image

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "avatars")


def get_cached_avatar(
    channel_id: str, avatar_url: str, size: tuple[int, int] = (72, 72)
) -> Image.Image:
    """Downloads (if needed) and returns a square resized PIL Image of the avatar."""
    os.makedirs(CACHE_DIR, exist_ok=True)

    # File path based on channel_id
    safe_name = hashlib.md5(channel_id.encode("utf-8")).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{safe_name}.png")

    if os.path.exists(cache_path):
        try:
            with Image.open(cache_path) as img:
                return img.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        except Exception:
            pass

    # Download if not cached
    if avatar_url:
        try:
            req = urllib.request.Request(
                avatar_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw_data = resp.read()
                with Image.open(io.BytesIO(raw_data)) as img:
                    img_rgba = img.convert("RGBA").resize(
                        size, Image.Resampling.LANCZOS
                    )
                    img_rgba.save(cache_path, "PNG")
                    return img_rgba
        except Exception as e:
            print(f"[Avatar] Błąd pobierania {channel_id}: {e}")

    # Fallback placeholder if download fails
    placeholder = Image.new("RGBA", size, (30, 30, 38, 255))
    return placeholder
