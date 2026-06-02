"""
Telegram-бот (long-polling) для подтверждения входа по QR.

Запускается фоновым потоком вместе с веб-сервером. Слушает обновления,
ловит команду /start <token>. Если Telegram ID совпадает с разрешённым
(TELEGRAM_CHAT_ID), помечает токен подтверждённым в общем AuthStore.
"""
import logging
import threading
import time
import requests

from .auth import store

log = logging.getLogger("digest.bot")


class TelegramAuthBot:
    def __init__(self, token: str, allowed_id: str):
        self.token = token
        self.allowed_id = str(allowed_id).strip()
        self.base = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self._stop = threading.Event()

    def _api(self, method: str, **params):
        try:
            r = requests.get(f"{self.base}/{method}", params=params, timeout=35)
            return r.json()
        except Exception as e:
            log.warning("bot api %s error: %s", method, e)
            return None

    def _send(self, chat_id, text):
        self._api("sendMessage", chat_id=chat_id, text=text)

    def get_username(self) -> str:
        data = self._api("getMe")
        if data and data.get("ok"):
            return data["result"].get("username", "")
        return ""

    def _handle(self, update):
        msg = update.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat = msg.get("chat") or {}
        from_user = msg.get("from") or {}
        user_id = str(from_user.get("id", ""))
        chat_id = chat.get("id")

        if not text.startswith("/start"):
            return

        parts = text.split(maxsplit=1)
        token = parts[1].strip() if len(parts) > 1 else ""

        # Проверка: пускаем только владельца
        if user_id != self.allowed_id:
            self._send(chat_id, "Доступ запрещён. Этот ассистент приватный.")
            log.warning("Отклонён вход для чужого ID: %s", user_id)
            return

        if not token:
            self._send(chat_id, "Привет! Чтобы войти в дашборд, "
                                "отсканируй QR на странице входа.")
            return

        if store.mark_confirmed(token, int(user_id)):
            self._send(chat_id, "✓ Вход подтверждён! Возвращайся на вкладку "
                                "с дашбордом — она откроется автоматически.")
            log.info("Вход подтверждён для владельца %s", user_id)
        else:
            self._send(chat_id, "Ссылка устарела или недействительна. "
                                "Обнови страницу входа и попробуй ещё раз.")

    def run(self):
        log.info("Telegram auth-бот запущен (long-polling).")
        while not self._stop.is_set():
            data = self._api("getUpdates", offset=self.offset, timeout=30)
            if not data or not data.get("ok"):
                time.sleep(3)
                continue
            for upd in data.get("result", []):
                self.offset = upd["update_id"] + 1
                try:
                    self._handle(upd)
                except Exception as e:
                    log.warning("handle update error: %s", e)

    def start_background(self):
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t

    def stop(self):
        self._stop.set()
