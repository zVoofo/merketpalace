from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-change-in-production-marketplace-2024')

DEBUG = os.environ.get('DEBUG', '1') == '1'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
_extra_hosts = os.environ.get('ALLOWED_HOSTS', '')
if _extra_hosts:
    ALLOWED_HOSTS.extend(h.strip() for h in _extra_hosts.split(',') if h.strip())

CSRF_TRUSTED_ORIGINS = []
if _render_host:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_render_host}')
_extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS.extend(o.strip() for o in _extra_csrf.split(',') if o.strip())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'accounts',
    'catalog',
    'listings',
    'orders',
    'chat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.ActivityLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'orders.context_processors.cart_count',
                'accounts.context_processors.site_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=_database_url,
        conn_max_age=600,
        ssl_require=False,
    )

# Для MySQL раскомментируйте:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'marketplace',
#         'USER': 'root',
#         'PASSWORD': '',
#         'HOST': '127.0.0.1',
#         'OPTIONS': {'charset': 'utf8mb4'},
#     }
# }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'accounts.storage_db.DatabaseStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/files/'
MEDIA_ROOT = BASE_DIR / 'media'
FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800  # 50 MB
MAX_DB_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# --- Опционально: S3 (Яндекс и т.д.) — только если заданы переменные ---
_S3_BUCKET = os.environ.get('AWS_STORAGE_BUCKET_NAME')
if _S3_BUCKET:
    INSTALLED_APPS += ['storages']
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
    }
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = _S3_BUCKET
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ru-central1')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', '') or None
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    _custom_domain = os.environ.get('AWS_S3_CUSTOM_DOMAIN', '')
    if _custom_domain:
        AWS_S3_CUSTOM_DOMAIN = _custom_domain
        MEDIA_URL = f'https://{_custom_domain}/'
    elif AWS_S3_ENDPOINT_URL and 'yandex' in AWS_S3_ENDPOINT_URL:
        AWS_S3_CUSTOM_DOMAIN = f'{_S3_BUCKET}.storage.yandexcloud.net'
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

ITEMS_PER_PAGE = 20
COMMISSION_RATE = 0.05

# --- Email (тестовый режим: письма в консоль) ---
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@marketplace.local'
# Для реальной отправки замените на SMTP:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.yandex.ru'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your@email.ru'
# EMAIL_HOST_PASSWORD = 'your-password'

# --- SMS (тестовый режим: код в консоли сервера) ---
SMS_TEST_MODE = DEBUG

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
