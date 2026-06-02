"""
QR-авторизация через Telegram.

Поток:
  1. Гость открывает дашборд → видит QR со ссылкой t.me/<bot>?start=<token>.
  2. Сканирует телефоном → Telegram открывает бота с этим токеном.
  3. Бот проверяет, что Telegram ID совпадает с разрешённым, и помечает
     токен подтверждённым (mark_confirmed).
  4. Страница логина опрашивает /auth/status?token=... — как только токен
     подтверждён, сервер выдаёт session-cookie и пускает на дашборд.

Хранилище токенов и сессий — в памяти процесса (для одного пользователя
этого достаточно). Всё потокобезопасно через Lock.
"""
import secrets
import threading
import time

TOKEN_TTL = 300        # секунд: сколько живёт QR-токен до подтверждения
SESSION_TTL = 30 * 24 * 3600   # 30 дней: срок жизни сессии после входа


class AuthStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._tokens = {}     # token -> {"created", "confirmed", "tg_id"}
        self._sessions = {}   # session_id -> {"created", "tg_id"}

    # --- QR-токены ---

    def new_token(self) -> str:
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._tokens[token] = {
                "created": time.time(),
                "confirmed": False,
                "tg_id": None,
            }
            self._gc()
        return token

    def mark_confirmed(self, token: str, tg_id: int) -> bool:
        """Вызывается ботом после проверки ID. True — если токен валиден."""
        with self._lock:
            t = self._tokens.get(token)
            if not t:
                return False
            if time.time() - t["created"] > TOKEN_TTL:
                self._tokens.pop(token, None)
                return False
            t["confirmed"] = True
            t["tg_id"] = tg_id
            return True

    def check_token(self, token: str):
        """Возвращает tg_id, если токен подтверждён, иначе None."""
        with self._lock:
            t = self._tokens.get(token)
            if not t or not t["confirmed"]:
                return None
            if time.time() - t["created"] > TOKEN_TTL + 60:
                self._tokens.pop(token, None)
                return None
            return t["tg_id"]

    # --- сессии ---

    def create_session(self, tg_id: int) -> str:
        sid = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[sid] = {"created": time.time(), "tg_id": tg_id}
        return sid

    def valid_session(self, sid: str) -> bool:
        if not sid:
            return False
        with self._lock:
            s = self._sessions.get(sid)
            if not s:
                return False
            if time.time() - s["created"] > SESSION_TTL:
                self._sessions.pop(sid, None)
                return False
            return True

    def drop_session(self, sid: str):
        with self._lock:
            self._sessions.pop(sid, None)

    def _gc(self):
        """Чистка протухших токенов (вызывается под локом)."""
        now = time.time()
        dead = [k for k, v in self._tokens.items()
                if now - v["created"] > TOKEN_TTL + 120]
        for k in dead:
            self._tokens.pop(k, None)


# Единый стор на процесс
store = AuthStore()
