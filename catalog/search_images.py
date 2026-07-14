"""
Стабильное превью для поиска: скачиваем фото один раз или генерируем локально.
"""
import hashlib
import io
import os
import textwrap
import urllib.request
from pathlib import Path

from django.conf import settings

from .external import _duckduckgo_image, _wikipedia_image


CACHE_DIR = Path(settings.MEDIA_ROOT) / 'search_previews'


def _query_hash(query: str) -> str:
    return hashlib.md5(query.strip().lower().encode('utf-8')).hexdigest()


def _media_url(filename: str) -> str:
    return f'{settings.MEDIA_URL}search_previews/{filename}'


def _download_bytes(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; MarketPlace/1.0)'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) < 500:
                return None
            if data[:2] == b'\xff\xd8' or data[:8] == b'\x89PNG\r\n\x1a\n':
                return data
    except Exception:
        pass
    return None


def _pick_font(size: int):
    from PIL import ImageFont
    for path in (
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/segoeui.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _generate_product_card(query: str) -> bytes:
    from PIL import Image, ImageDraw

    size = 400
    h = int(_query_hash(query)[:6], 16)
    r1, g1, b1 = 40 + (h % 80), 80 + ((h >> 8) % 100), 160 + ((h >> 16) % 80)
    r2, g2, b2 = min(r1 + 60, 255), min(g1 + 40, 255), min(b1 + 30, 255)

    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        draw.line([(0, y), (size, y)], fill=(
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        ))

    draw.rounded_rectangle((100, 90, 300, 260), radius=16, fill=(255, 255, 255))
    draw.rounded_rectangle((120, 110, 280, 200), radius=8, fill=(240, 245, 250))

    font_title = _pick_font(15)
    font_small = _pick_font(12)
    font_icon = _pick_font(48)
    draw.text((200, 145), '📦', font=font_icon, anchor='mm', fill=(100, 116, 139))

    y_text = 220
    for line in textwrap.wrap(query.strip(), width=22)[:4]:
        draw.text((200, y_text), line, font=font_title, anchor='mm', fill=(30, 41, 59))
        y_text += 22

    draw.text((200, 375), 'Пример товара · MarketPlace', font=font_small, anchor='mm', fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=88)
    return buf.getvalue()


def get_cached_search_image(query: str) -> dict:
    if not query or len(query.strip()) < 3:
        return {'url': None, 'source': None}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    file_hash = _query_hash(query)
    filename = f'{file_hash}.jpg'
    filepath = CACHE_DIR / filename
    media_url = _media_url(filename)

    if filepath.exists() and filepath.stat().st_size > 500:
        return {'url': media_url, 'source': 'cache'}

    for remote_fn, source in ((_wikipedia_image, 'web'), (_duckduckgo_image, 'web')):
        remote_url = remote_fn(query)
        if remote_url:
            data = _download_bytes(remote_url)
            if data:
                filepath.write_bytes(data)
                return {'url': media_url, 'source': source}

    filepath.write_bytes(_generate_product_card(query))
    return {'url': media_url, 'source': 'generated'}
