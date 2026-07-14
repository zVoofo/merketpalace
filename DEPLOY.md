# Деплой на бесплатный хостинг (Render)

Сайт подготовлен для **[Render.com](https://render.com)** — бесплатный тариф для Django + PostgreSQL.

> Я не могу залить сайт за вас без вашего аккаунта на GitHub и Render. Ниже — 10 минут, и сайт будет в интернете.

## Что получится

- URL вида `https://marketplace-xxxx.onrender.com`
- Бесплатно (сервер «засыпает» после 15 мин без посещений, первый заход ~30 сек)
- PostgreSQL на Render (бесплатная БД)
- Демо-данные (`seed`) загрузятся при первом деплое

**Файлы (фото, видео, чат):** сохраняются в PostgreSQL автоматически — ничего настраивать не нужно. См. [STORAGE.md](STORAGE.md).

---

## Шаг 1 — GitHub

1. Зарегистрируйтесь на [github.com](https://github.com)
2. Создайте новый репозиторий (например `marketplace-portal`), **без** README
3. В папке проекта выполните в PowerShell:

```powershell
cd "c:\Users\vaxry\OneDrive\Рабочий стол\portal"
git init
git add .
git commit -m "MarketPlace Django — готов к деплою"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/marketplace-portal.git
git push -u origin main
```

Замените `ВАШ_ЛОГИН` и имя репозитория на свои.

---

## Шаг 2 — Render (автоматически через Blueprint)

1. Зайдите на [render.com](https://render.com) → **Sign Up** (можно через GitHub)
2. **New** → **Blueprint**
3. Подключите репозиторий `marketplace-portal`
4. Render увидит файл `render.yaml` и создаст:
   - Web Service `marketplace`
   - PostgreSQL `marketplace-db`
5. Нажмите **Apply** и дождитесь деплоя (5–10 мин)

После успеха откроется ссылка на сайт.

---

## Шаг 3 — Проверка

| Логин | Пароль |
|-------|--------|
| admin | admin123 |
| seller | seller123 |
| buyer | buyer123 |

Админка: `https://ваш-сайт.onrender.com/admin/`  
Панель: `https://ваш-сайт.onrender.com/panel/`

---

## Альтернатива: PythonAnywhere (без Git)

1. [pythonanywhere.com](https://www.pythonanywhere.com) → бесплатный аккаунт
2. Загрузите ZIP проекта (без `venv`, `db.sqlite3`, `media/`)
3. В Bash:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py seed
```

4. Настройте WSGI на `config.wsgi.application`
5. URL: `вашлогин.pythonanywhere.com`

---

## Файлы деплоя в проекте

| Файл | Назначение |
|------|------------|
| `render.yaml` | Конфиг Render Blueprint |
| `build.sh` | Сборка: static, migrate, seed |
| `requirements.txt` | gunicorn, whitenoise, PostgreSQL |
| `.env.example` | Переменные окружения |

## Проблемы

**502 / долгая загрузка** — бесплатный Render просыпается, подождите 30–60 сек.

**Ошибка БД** — в Render Dashboard проверьте, что `DATABASE_URL` привязан к PostgreSQL.

**Статика не грузится** — в логах Build должно быть `collectstatic` без ошибок.

---

Нужна помощь с конкретным шагом (GitHub, Render, ошибка в логах) — напишите, на каком шаге застряли.
