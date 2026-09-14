import hashlib
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

import content
import image_previews
from test_reservations import client


def store(picture, kind='PNG', **options):
    data = io.BytesIO()
    picture.save(data, format=kind, **options)
    raw = data.getvalue()
    photo = content.store_image(raw, original=True)
    return photo['src'], raw


def url(src, width=320):
    return f'/studio-api/media/previews/v1/{width}/' + src.rsplit('/', 1)[1]


@pytest.mark.parametrize('width', image_previews.WIDTHS)
def test_preview_size_full_composition_and_original_unchanged(client, width):
    picture = Image.new('RGB', (1200, 1800), '#b4dbef')
    picture.paste('#fa2345', (0, 0, 150, 150))
    picture.paste('#32da74', (1050, 1650, 1200, 1800))
    src, original = store(picture)
    response = client.get(url(src, width))
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/webp'
    assert response.headers['cache-control'] == image_previews.CACHE_CONTROL
    image = Image.open(io.BytesIO(response.content))
    assert image.size == (width, round(width * 1.5))
    assert image.getpixel((5, 5))[0] > 220
    assert image.getpixel((image.width - 5, image.height - 5))[1] > 180
    assert client.get(src).content == original
    assert client.get(src).headers['content-type'] == 'image/png'
    assert hashlib.sha256(original).hexdigest() in src
    assert client.get(url(src, width)).content == response.content


def test_preview_alpha_no_upscale_orientation_and_changed_upload(client):
    src, _ = store(Image.new('RGBA', (40, 60), (255, 0, 0, 0)))
    image = Image.open(io.BytesIO(client.get(url(src)).content))
    assert image.size == (40, 60) and image.getpixel((0, 0))[3] == 0
    exif = Image.Exif(); exif[274] = 6
    first, original = store(Image.new('RGB', (900, 600), 'red'), 'JPEG', exif=exif)
    image = Image.open(io.BytesIO(client.get(url(first)).content))
    assert image.size == (320, 480)
    assert client.get(first).content == original
    second, _ = store(Image.new('RGB', (900, 600), 'blue'), 'JPEG')
    assert url(first) != url(second)
    assert client.get(url(first)).content != client.get(url(second)).content


def test_preview_concurrent_atomic_cache(client):
    src, raw = store(Image.new('RGB', (1000, 900), '#436cc5'))
    name = src.rsplit('/', 1)[1]
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(lambda _: image_previews.preview(content.MEDIA_DIR, name, 480), range(12)))
    assert len(set(paths)) == 1
    assert Image.open(paths[0]).size == (480, 432)
    assert not list(content.MEDIA_DIR.rglob('*.tmp'))
    assert (content.MEDIA_DIR / name).read_bytes() == raw


@pytest.mark.parametrize('path', [
    '/studio-api/media/previews/v1/481/' + 'a' * 64 + '.jpg',
    '/studio-api/media/previews/v1/320/' + 'a' * 64 + '.jpg',
    '/studio-api/media/previews/v1/320/secret.env',
    '/studio-api/media/previews/v1/320/https:%2F%2Fexample.com%2Ffile.jpg',
    '/studio-api/media/previews/v1/320/%2e%2e%2fsecret.jpg',
])
def test_preview_rejects_arbitrary_sources_and_does_not_cache_errors(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.headers['cache-control'] == 'no-store'


def test_unavailable_encoder_leaves_original_available(client, monkeypatch):
    src, raw = store(Image.new('RGB', (1200, 600), 'green'))
    class Busy:
        def acquire(self, **kwargs): return False
    monkeypatch.setattr(image_previews, '_encoders', Busy())
    response = client.get(url(src))
    assert response.status_code == 503 and response.headers['cache-control'] == 'no-store'
    assert client.get(src).content == raw
