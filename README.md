# MarketPlace — Django

Многофункциональная торговая площадка на **Django + SQLite** (MySQL опционально).

## Подтверждение email и телефона

См. файл [VERIFICATION.md](VERIFICATION.md) — тестовый режим и настройка SMTP/SMS.

## Быстрый старт

```powershell
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Создать базу данных
python manage.py migrate

# 3. Заполнить демо-данными
python manage.py seed

# 4. Запустить сервер
python manage.py runserver
```

Откройте http://127.0.0.1:8000

## Тестовые аккаунты

| Роль | Логин | Пароль |
|------|-------|--------|
| Админ | admin | admin123 |
| Продавец | seller | seller123 |
| Покупатель | buyer | buyer123 |

## Функционал

- Регистрация / вход / профиль (переключение покупатель ↔ продавец)
- Каталог с поиском, фильтрами, заявкой «товар не найден»
- Объявления (товар/услуга), модерация, фото
- Корзина, оформление заказа, эскроу
- Чат с продавцом
- Отзывы
- Кабинет продавца + аналитика поиска
- Панель `/panel/` + Django Admin `/admin/`

## Структура

```
portal/
├── manage.py
├── config/          # settings, urls
├── accounts/        # пользователи, профиль
├── catalog/         # категории, поиск
├── listings/        # объявления, отзывы
├── orders/          # корзина, заказы
├── chat/            # мессенджер
├── templates/
├── static/
└── media/
```

## MySQL (опционально)

В `config/settings.py` замените блок `DATABASES` на MySQL и выполните `migrate`.

## Старый PHP-код

Папки `src/`, `public/`, `views/` — предыдущая PHP-версия, можно удалить.
