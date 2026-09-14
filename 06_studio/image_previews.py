"""Finite, immutable WebP previews. Source photographs are never rewritten."""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError
from fastapi import HTTPException

WIDTHS = (320, 480, 800)
VERSION = 'v1'
NAME = re.compile(r'[a-f0-9]{64}\.(?:jpg|png|webp)')
CACHE_CONTROL = 'public, max-age=31536000, immutable'
MIME_TYPES = {'.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
_encoders = threading.BoundedSemaphore(2)


def preview(media_dir: Path, name: str, width: int) -> Path:
    if width not in WIDTHS or not NAME.fullmatch(name):
        raise HTTPException(404)
    source = media_dir / name
    if not source.is_file():
        raise HTTPException(404)
    target = media_dir / 'previews' / VERSION / str(width) / (name + '.webp')
    if target.is_file():
        return target
    # Encoding runs in FastAPI's thread pool, with a separate CPU/memory bound.
    # Prewarming the public catalogue avoids putting this work on first visitors.
    if not _encoders.acquire(timeout=3):
        raise HTTPException(503, 'preview_busy', headers={'Retry-After': '1'})
    temporary = None
    try:
        if target.is_file():
            return target
        with Image.open(source) as original:
            if original.width * original.height > 60_000_000:
                raise ValueError('too many pixels')
            picture = ImageOps.exif_transpose(original)
            icc = picture.info.get('icc_profile')
            if picture.mode == 'CMYK' and icc:
                srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
                picture = ImageCms.profileToProfile(picture, ImageCms.ImageCmsProfile(io.BytesIO(icc)), srgb, outputMode='RGB')
                icc = srgb.tobytes()
            picture = picture.convert('RGBA' if 'A' in picture.getbands() or 'transparency' in picture.info else 'RGB')
            # Scale by width, preserve the entire composition, and never upscale.
            if picture.width > width:
                picture = picture.resize((width, max(1, round(picture.height * width / picture.width))), Image.Resampling.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(uuid.uuid4().hex + '.tmp')
            picture.save(temporary, format='WEBP', quality=85, method=4, **({'icc_profile': icc} if icc else {}))
        os.replace(temporary, target)
        return target
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError, ImageCms.PyCMSError) as error:
        raise HTTPException(422, 'preview_unavailable') from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        _encoders.release()


def warm_catalog(database: Path, media_dir: Path) -> dict:
    """Read-only catalogue scan; only derived files are created in shared media."""
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        products = [json.loads(row[0]) for row in db.execute('SELECT payload FROM commerce_products')]
    names = set()
    for product in products:
        images = product.get('images') or []
        if product.get('shop_visible') and images:
            source = images[0]
            name = source.removeprefix('/studio-api/media/')
            if source.startswith('/studio-api/media/') and NAME.fullmatch(name):
                names.add(name)
    start = time.monotonic()
    sizes = {str(width): 0 for width in WIDTHS}
    original_bytes = 0
    for name in sorted(names):
        original_bytes += (media_dir / name).stat().st_size
        for width in WIDTHS:
            sizes[str(width)] += preview(media_dir, name, width).stat().st_size
    return {'sources': len(names), 'previews': len(names) * len(WIDTHS), 'original_bytes': original_bytes,
            'bytes_by_width': sizes, 'elapsed_seconds': round(time.monotonic() - start, 2)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--media-dir', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(warm_catalog(options.db, options.media_dir)))
