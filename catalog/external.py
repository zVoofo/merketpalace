import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class ExternalOffer:
    source: str
    title: str
    url: str
    price: str | None
    image: str | None


def _fetch_json(url: str, timeout: int = 5) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MarketPlace/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _duckduckgo_image(query: str) -> str | None:
    q = urllib.parse.quote(query.strip())
    data = _fetch_json(f'https://api.duckduckgo.com/?q={q}&format=json&no_redirect=1&skip_disambig=1')
    if not data:
        return None
    if data.get('Image'):
        return data['Image']
    for topic in data.get('RelatedTopics') or []:
        if isinstance(topic, dict):
            icon = topic.get('Icon', {}).get('URL')
            if icon and 'duckduckgo' not in icon:
                return icon
    return None


def _wikipedia_image(query: str, lang: str = 'ru') -> str | None:
    q = urllib.parse.quote(query.strip())
    data = _fetch_json(
        f'https://{lang}.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={q}'
        f'&prop=pageimages&piprop=thumbnail&pithumbsize=500&format=json&gsrlimit=1'
    )
    if not data:
        return None
    for page in data.get('query', {}).get('pages', {}).values():
        thumb = page.get('thumbnail', {}).get('source')
        if thumb:
            return thumb
    return None


def get_external_offers(query: str) -> list[ExternalOffer]:
    q = query.strip()
    encoded = urllib.parse.quote(q)
    preview_url = f'/catalog/preview/?q={encoded}'
    sources = [
        ('Avito', f'https://www.avito.ru/all?q={encoded}'),
        ('Youla', f'https://youla.ru/search?q={encoded}'),
        ('Ozon', f'https://www.ozon.ru/search/?text={encoded}'),
        ('Wildberries', f'https://www.wildberries.ru/catalog/0/search.aspx?search={encoded}'),
        ('Auto.ru', f'https://auto.ru/parts/all/?query={encoded}'),
    ]
    return [
        ExternalOffer(source=name, title=f'{q} — на {name}', url=url, price=None, image=preview_url)
        for name, url in sources
    ]
