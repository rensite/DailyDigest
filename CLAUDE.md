# CLAUDE.md

Контекст проекта для Claude Code. Прочитай это перед изменениями.

## Что это

**Daily Digest** — самостоятельный сервис (Python), который каждое утро
собирает в одну персональную сводку: почту (Gmail IMAP), новости (RSS),
погоду (Open-Meteo) и курсы валют (ЦБ РФ). Сверху — опциональный LLM-слой
(OpenAI / Anthropic / Grok / Gemini): утреннее обращение, AI-приоритеты дел,
разбор почты и выжимка новостей.

Доставка: Telegram-бот + веб-дашборд. Вход на дашборд — по QR через Telegram.
Деплой: Docker + Caddy (авто-HTTPS) на VPS.

## Команды

```bash
# Локальный запуск (веб + планировщик + auth-бот)
python main.py serve

# Разовый сбор и отправка в Telegram (для cron/теста)
python main.py run

# Только веб-сервер
python main.py web

# Зависимости
pip install -r requirements.txt

# Прод-деплой (с Caddy + HTTPS)
docker compose -f docker-compose.prod.yml up -d --build

# Простой запуск (без Caddy, для локалки/туннеля)
docker compose up -d --build
```

Проверка синтаксиса всех модулей:
```bash
python -m py_compile main.py app/*.py app/sources/*.py
```

## Архитектура

```
main.py                 точка входа: Flask-роуты, режимы (serve/run/web),
                        планировщик (APScheduler), запуск auth-бота
app/
  config.py             загрузка .env в объект config (единый источник настроек)
  digest.py             build_digest(): собирает все источники + умный слой
  sources/
    mail.py             Gmail через IMAP (app password)
    news.py             RSS через feedparser, round-robin по лентам
    weather.py          Open-Meteo (без ключа)
    currency.py         ЦБ РФ через cbr-xml-daily.ru (без ключа)
  llm.py                LLMClient — единый интерфейс к 4 провайдерам (HTTP)
  intelligence.py       промпты умного слоя (обращение, почта, новости, дела)
  render.py             render_html() для дашборда, render_telegram() для бота
  telegram.py           отправка сводки в Telegram
  auth.py               AuthStore: QR-токены + сессии (в памяти процесса)
  bot.py                TelegramAuthBot: long-polling, подтверждение входа
  login_page.py         HTML страницы входа с QR (qrcode.js с CDN)
```

### Поток данных
`build_digest()` в `digest.py` — центральная функция. Она вызывает все
`sources/*`, строит дела и рекомендации (эвристики), затем `_build_intelligence()`
прогоняет данные через LLM (если настроен). Результат — один dict, который
`render.py` превращает в HTML и в текст для Telegram.

### Поток авторизации (QR)
1. Гость на `/` без сессии → редирект `/login`.
2. `/login` создаёт токен (`auth.store.new_token`) и рисует QR со ссылкой
   `t.me/<bot>?start=<token>`.
3. Пользователь сканирует → бот (`bot.py`) ловит `/start <token>`, проверяет
   что Telegram ID == `TELEGRAM_CHAT_ID`, вызывает `mark_confirmed`.
4. Страница опрашивает `/auth/status?token=...`; при подтверждении сервер
   выдаёт session-cookie. Сессии и токены живут в памяти (`AuthStore`).

## Ключевые конвенции

- **Graceful degradation везде.** Любой источник или LLM может упасть — сервис
  должен продолжать работать и отдавать сводку из того, что доступно. Все
  внешние вызовы обёрнуты в try/except и возвращают `{"ok": False, ...}` или None.
- **Все настройки — через `.env`** и объект `config`. Не хардкодь ключи/значения.
- **Без тяжёлых SDK.** Внешние API (LLM, Telegram, погода) вызываются через
  `requests` напрямую. Зависимости держим минимальными (см. requirements.txt).
- **Секреты не коммитим.** `.env` в `.gitignore` и `.dockerignore`.
- Язык интерфейса и LLM-промптов — русский, обращение на «ты».
- QR рисуется на клиенте (qrcode.js), серверной QR-библиотеки нет.

## Чего пока нет (идеи для развития)

- Telegram как источник чтения (каналы через бот-админа или Telethon).
- Кнопка «обновить» на дашборде без перезагрузки.
- Календарь, пробки, доп. источники.
- Персистентное хранилище сессий (сейчас в памяти — теряются при рестарте;
  для одного пользователя это ок, для многих — нужен Redis/SQLite).

## Тестирование

Автотестов пока нет. Минимальная проверка перед коммитом:
1. `python -m py_compile main.py app/*.py app/sources/*.py`
2. Прогон источников без ключей (погода/курсы/новости работают сразу).
3. Проверка QR-потока через `app.test_client()` (см. историю — тестировался
   редирект, /login, /auth/status, выдача cookie).
