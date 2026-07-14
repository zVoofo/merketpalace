"""Расширенная проверка: импорты, шаблоны, граничные запросы."""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import Client
from django.urls import reverse

User = get_user_model()
FAILURES = []
HOST = 'localhost'


def get(client, path, **kwargs):
    return client.get(path, HTTP_HOST=HOST, **kwargs)


def fail(name, exc):
    FAILURES.append((name, exc))
    print(f'FAIL {name}: {exc}')


def ok(name):
    print(f'OK   {name}')


# 1. Import all app modules
MODULES = [
    'catalog.views', 'catalog.filter_params', 'catalog.validators', 'catalog.recommendations',
    'accounts.views', 'accounts.notifications',
    'listings.views', 'listings.forms', 'listings.moderation',
    'orders.views', 'chat.views',
]
for mod in MODULES:
    try:
        __import__(mod)
        ok(f'import {mod}')
    except Exception as e:
        fail(f'import {mod}', e)


# 2. Key templates compile
TEMPLATES = [
    'base.html', 'home/index.html', 'catalog/index.html',
    'accounts/profile.html', 'accounts/my_requests.html',
    'accounts/login.html', 'listings/create.html', 'listings/show.html',
    'includes/cabinet_nav.html', 'includes/listing_form_fields.html',
]
for tpl in TEMPLATES:
    try:
        get_template(tpl)
        ok(f'template {tpl}')
    except Exception as e:
        fail(f'template {tpl}', e)


# 3. Edge-case HTTP requests
client = Client(raise_request_exception=False)
EDGE_CASES = [
    ('/', 'GET'),
    ('/catalog/', 'GET'),
    ('/catalog/?price_min=-100&price_max=abc&sort=DROP&page=99999', 'GET'),
    ('/catalog/?in_stock=1&preorder=1', 'GET'),
    ('/catalog/?q=!!!@@@', 'GET'),
    ('/catalog/preview/?q=test', 'GET'),
    ('/accounts/profile/', 'GET'),
    ('/listing/create/', 'GET'),
]

for user, pwd in [('buyer', 'buyer123'), ('seller', 'seller123'), ('admin', 'admin123')]:
    c = Client(raise_request_exception=False)
    if not c.login(username=user, password=pwd):
        fail(f'login {user}', 'credentials invalid')
        continue
    ok(f'login {user}')
    for path, method in EDGE_CASES:
        if path == '/listing/create/' and user == 'buyer':
            continue
        try:
            r = get(c, path) if method == 'GET' else c.post(path, HTTP_HOST=HOST)
            if r.status_code >= 500:
                fail(f'{user} {path}', f'HTTP {r.status_code}')
            else:
                ok(f'{user} {path} -> {r.status_code}')
        except Exception as e:
            fail(f'{user} {path}', e)


# 4. ListingForm validation edge cases
try:
    from listings.forms import ListingForm
    from catalog.models import Category
    cat = Category.objects.filter(is_active=True).first()
    data = {
        'type': 'product', 'title': 'Test brake pads BMW', 'category': cat.pk if cat else '',
        'price': '99999999999', 'quantity': '1', 'availability': 'stock', 'condition': 'new',
        'description': 'Valid description for test product listing',
    }
    form = ListingForm(data)
    form.is_valid()
    if 'price' not in form.errors:
        fail('ListingForm price cap', 'expected price error')
    else:
        ok('ListingForm rejects absurd price')
except Exception as e:
    fail('ListingForm', e)


# 5. parse_catalog_filters
try:
    from catalog.filter_params import parse_catalog_filters
    cleaned, errors = parse_catalog_filters(
        {'price_min': '1', 'price_max': '2', 'sort': 'new'},
        category_ids=set(), brand_ids=set(), make_ids=set(), price_cap=100000,
    )
    assert cleaned['price_min'] == 1
    ok('parse_catalog_filters normal')
    cleaned2, errors2 = parse_catalog_filters(
        {'price_min': 'abc'},
        category_ids=set(), brand_ids=set(), make_ids=set(), price_cap=100000,
    )
    assert cleaned2['price_min'] is None and errors2
    ok('parse_catalog_filters invalid')
except Exception as e:
    fail('parse_catalog_filters', e)


print('\n--- SUMMARY ---')
print(f'Total failures: {len(FAILURES)}')
if FAILURES:
    for name, exc in FAILURES:
        print(f'\n{name}:')
        if isinstance(exc, BaseException):
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        else:
            print(exc)
    sys.exit(1)
print('All extended checks passed.')
sys.exit(0)
