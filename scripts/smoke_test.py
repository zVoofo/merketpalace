"""Smoke-test: все публичные URL должны отдавать не 500."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import get_resolver

User = get_user_model()

FAIL = []
OK = []
HOST = 'localhost'


def get(client, path, **kwargs):
    return client.get(path, HTTP_HOST=HOST, **kwargs)


def record(path, status, note=''):
    entry = (path, status, note)
    if status >= 500:
        FAIL.append(entry)
    else:
        OK.append(entry)


def walk_urls(urlpatterns, prefix=''):
    for p in urlpatterns:
        if hasattr(p, 'url_patterns'):
            walk_urls(p.url_patterns, prefix + str(p.pattern))
            continue
        pattern = prefix + str(p.pattern)
        if '<' in pattern:
            continue
        yield '/' + pattern.lstrip('/')


def main():
    client = Client(raise_request_exception=False)
    resolver = get_resolver()

    # Public pages
    for path in sorted(set(walk_urls(resolver.url_patterns))):
        if path.startswith('/files/'):
            continue
        r = get(client, path, follow=False)
        record(path, r.status_code)

    # Catalog with filter edge cases
    filter_cases = [
        '/catalog/?price_min=abc&price_max=999999999999&sort=hack&page=-1',
        '/catalog/?in_stock=1&preorder=1&category=99999&brand=99999',
        '/catalog/?q=тормозные+колодки&rating=4.5',
        '/catalog/?price_min=1000&price_max=500',
    ]
    for path in filter_cases:
        r = get(client, path)
        record(path, r.status_code, 'filters')

    # Auth pages
    for user, pwd in [('buyer', 'buyer123'), ('seller', 'seller123'), ('admin', 'admin123')]:
        c = Client(raise_request_exception=False)
        if not c.login(username=user, password=pwd):
            FAIL.append((f'login:{user}', 500, 'login failed'))
            continue
        auth_paths = [
            '/accounts/profile/',
            '/accounts/my-requests/',
            '/accounts/wallet/',
            '/accounts/cabinet/',
            '/orders/',
            '/cart/',
            '/messages/',
            '/seller/',
            '/seller/listings/',
            '/seller/requests/',
            '/listing/create/',
        ]
        if user == 'admin':
            auth_paths += ['/panel/', '/panel/moderation/', '/panel/users/']
        for path in auth_paths:
            r = get(c, path)
            record(f'{path} [{user}]', r.status_code)

    # Listing detail if any exists
    from listings.models import Listing
    listing = Listing.objects.filter(status='active').first()
    if listing:
        r = get(client, f'/listing/{listing.slug}/')
        record(f'/listing/{listing.slug}/', r.status_code)

    print(f'OK: {len(OK)}')
    print(f'FAIL (5xx): {len(FAIL)}')
    for path, status, note in FAIL:
        print(f'  {status} {path} {note}')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
