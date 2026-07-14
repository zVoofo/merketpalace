# Подтверждение Email и телефона

## Тестовый режим (уже работает)

По умолчанию проект настроен для локальной разработки:

### Email
- Письма **не уходят наружу**, а выводятся в **консоль**, где запущен `python manage.py runserver`
- После нажатия «Отправить код» в профиле смотрите терминал — там будет строка с 6-значным кодом
- На экране в DEBUG-режиме код также показывается во всплывающем сообщении

### SMS (телефон)
- SMS **не отправляется** — код печатается в консоль: `[SMS TEST] Phone +7900... code: 123456`
- Также показывается во всплывающем сообщении на сайте

### Как проверить
1. Войдите в аккаунт → Профиль
2. Укажите email и телефон → «Сохранить профиль»
3. Нажмите «Отправить код» для email или «Отправить SMS-код» для телефона
4. Скопируйте код из консоли или сообщения на сайте
5. Введите код → «Подтвердить»

---

## Боевая отправка Email (SMTP)

Откройте `config/settings.py` и замените блок EMAIL:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'          # или smtp.gmail.com, smtp.mail.ru
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'ваш@email.ru'
EMAIL_HOST_PASSWORD = 'пароль-приложения'
DEFAULT_FROM_EMAIL = 'ваш@email.ru'
```

**Yandex:** включите «Пароли приложений» в настройках безопасности.  
**Gmail:** создайте App Password в Google Account.

---

## Боевая отправка SMS

Подключите один из шлюзов (нужен API-ключ):

| Сервис | Сайт |
|--------|------|
| SMSAero | https://smsaero.ru |
| SMSC.ru | https://smsc.ru |
| Twilio | https://twilio.com |

Пример для SMSAero — добавьте в `accounts/verification.py` в функцию `send_phone_verification`:

```python
import requests
requests.post('https://gate.smsaero.ru/v2/sms/send', auth=('email', 'api_key'), json={
    'number': phone,
    'text': f'Код MarketPlace: {code}',
    'sign': 'MarketPlace',
})
```

Ключи храните в переменных окружения, не в коде:

```powershell
$env:SMSAERO_EMAIL = "your@email.ru"
$env:SMSAERO_API_KEY = "ваш-ключ"
```

---

## Фото профиля

Загружается в Профиль → «Фото профиля». Файлы сохраняются в папку `media/avatars/`.

---

## AI-изображения при поиске

Если фото не найдено в интернете, генерируется через **Pollinations.ai** (бесплатно, без ключа).  
Для своего AI-сервиса измените функцию `_ai_product_image` в `catalog/external.py`.
