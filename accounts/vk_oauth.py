"""Вход через VK OAuth (классический flow oauth.vk.com)."""
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.urls import reverse

VK_API_VERSION = '5.199'


def vk_configured() -> bool:
    return bool(settings.VK_APP_ID and settings.VK_APP_SECRET)


def vk_redirect_uri(request) -> str:
    if settings.VK_REDIRECT_URI:
        return settings.VK_REDIRECT_URI.rstrip('/')
    return request.build_absolute_uri(reverse('accounts:vk_callback')).rstrip('/')


def build_authorize_url(redirect_uri: str, state: str) -> str:
    params = {
        'client_id': settings.VK_APP_ID,
        'display': 'page',
        'redirect_uri': redirect_uri,
        'scope': 'email',
        'response_type': 'code',
        'state': state,
        'v': VK_API_VERSION,
    }
    return f'https://oauth.vk.com/authorize?{urllib.parse.urlencode(params)}'


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'MarketPlace/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def exchange_code(code: str, redirect_uri: str) -> dict:
    params = {
        'client_id': settings.VK_APP_ID,
        'client_secret': settings.VK_APP_SECRET,
        'redirect_uri': redirect_uri,
        'code': code,
    }
    url = f'https://oauth.vk.com/access_token?{urllib.parse.urlencode(params)}'
    try:
        data = _http_get_json(url)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        raise ValueError(body or str(e)) from e
    if 'error' in data:
        raise ValueError(data.get('error_description') or data['error'])
    return data


def fetch_profile(access_token: str, user_id: str) -> dict:
    params = {
        'user_ids': user_id,
        'fields': 'photo_200,screen_name',
        'access_token': access_token,
        'v': VK_API_VERSION,
    }
    url = f'https://api.vk.com/method/users.get?{urllib.parse.urlencode(params)}'
    data = _http_get_json(url)
    if 'error' in data:
        err = data['error']
        raise ValueError(err.get('error_msg') or err.get('error_code'))
    items = data.get('response') or []
    return items[0] if items else {}


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)
