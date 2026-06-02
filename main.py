"""
Daily Digest — личный командный центр.
Собирает почту, новости, погоду и курсы → сводка с делами и рекомендациями.
Доставка: Telegram + веб-страница.

Запуск:
  python main.py serve   — веб-сервер + планировщик (основной режим)
  python main.py run      — собрать и отправить сводку один раз (для cron/теста)
  python main.py web       — только веб-сервер, без планировщика
"""
import sys
import logging

from flask import Flask, Response, request, redirect, make_response, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import config
from app.digest import build_digest
from app.render import render_html, render_telegram
from app.telegram import send_telegram
from app.auth import store as auth_store
from app.login_page import render_login
from app.bot import TelegramAuthBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("digest")

app = Flask(__name__)

SESSION_COOKIE = "digest_session"
# Имя бота определяется при старте (getMe), нужно для deep-link в QR
BOT_USERNAME = {"value": ""}


def _authed() -> bool:
    """Авторизация выключена (локальный режим) ИЛИ есть валидная сессия."""
    if not config.auth_enabled:
        return True
    return auth_store.valid_session(request.cookies.get(SESSION_COOKIE, ""))


@app.route("/")
def index():
    """Веб-дашборд: собирает свежую сводку при каждом открытии."""
    if not _authed():
        return redirect("/login")
    try:
        data = build_digest()
        return Response(render_html(data), mimetype="text/html")
    except Exception as e:
        log.exception("Ошибка генерации дашборда")
        return Response(f"<h1>Ошибка</h1><pre>{e}</pre>",
                        mimetype="text/html", status=500)


@app.route("/login")
def login():
    """Страница входа с QR-кодом."""
    if _authed():
        return redirect("/")
    if not BOT_USERNAME["value"]:
        return Response("<h1>Бот не настроен</h1>"
                        "<p>Проверь TELEGRAM_BOT_TOKEN.</p>",
                        mimetype="text/html", status=503)
    token = auth_store.new_token()
    return Response(render_login(token, BOT_USERNAME["value"]),
                    mimetype="text/html")


@app.route("/auth/status")
def auth_status():
    """Опрашивается страницей логина. Если токен подтверждён — выдаёт сессию."""
    token = request.args.get("token", "")
    tg_id = auth_store.check_token(token)
    if tg_id is None:
        return jsonify({"authenticated": False})
    sid = auth_store.create_session(tg_id)
    resp = make_response(jsonify({"authenticated": True}))
    resp.set_cookie(SESSION_COOKIE, sid, max_age=30 * 24 * 3600,
                    httponly=True, samesite="Lax",
                    secure=config.COOKIE_SECURE)
    return resp


@app.route("/logout")
def logout():
    auth_store.drop_session(request.cookies.get(SESSION_COOKIE, ""))
    resp = make_response(redirect("/login"))
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.route("/health")
def health():
    return {"status": "ok"}


def run_once():
    """Собрать сводку и отправить в Telegram."""
    log.info("Собираю сводку...")
    data = build_digest()
    log.info("Сводка собрана на %s", data["generated_at"])

    if config.telegram_enabled:
        text = render_telegram(data)
        ok = send_telegram(config.TELEGRAM_BOT_TOKEN,
                           config.TELEGRAM_CHAT_ID, text)
        log.info("Telegram: %s", "отправлено" if ok else "ОШИБКА отправки")
    else:
        log.warning("Telegram не настроен — пропускаю отправку.")
    return data


def start_scheduler():
    """Ежедневный запуск в DIGEST_TIME по таймзоне погоды."""
    hour, minute = config.DIGEST_TIME.split(":")
    sched = BackgroundScheduler(timezone=config.WEATHER_TZ)
    sched.add_job(run_once, "cron", hour=int(hour), minute=int(minute),
                  id="daily_digest")
    sched.start()
    log.info("Планировщик запущен: ежедневно в %s (%s)",
             config.DIGEST_TIME, config.WEATHER_TZ)


def start_auth_bot():
    """Запускает Telegram-бота для QR-входа (если включена авторизация)."""
    if not config.auth_enabled:
        log.info("Авторизация выключена (AUTH_ENABLED=false) — вход без QR.")
        return
    if not config.telegram_enabled:
        log.warning("Авторизация включена, но Telegram не настроен — "
                    "вход по QR работать не будет.")
        return
    bot = TelegramAuthBot(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    username = bot.get_username()
    if username:
        BOT_USERNAME["value"] = username
        log.info("Auth-бот: @%s", username)
    else:
        log.warning("Не удалось получить имя бота (getMe).")
    bot.start_background()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "serve"

    if mode == "run":
        run_once()
        return

    if mode == "serve":
        start_scheduler()

    if mode in ("serve", "web"):
        start_auth_bot()

    log.info("Веб-сервер: http://%s:%s", config.WEB_HOST, config.WEB_PORT)
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False)


if __name__ == "__main__":
    main()
