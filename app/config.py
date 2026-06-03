"""Загрузка конфигурации из переменных окружения (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()


def _split(value: str):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


class Config:
    # Gmail
    GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    GMAIL_MAX_EMAILS = int(os.getenv("GMAIL_MAX_EMAILS", "20"))
    GMAIL_UNREAD_ONLY = os.getenv("GMAIL_UNREAD_ONLY", "true").lower() == "true"

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    # Погода
    WEATHER_LAT = float(os.getenv("WEATHER_LAT", "55.7558"))
    WEATHER_LON = float(os.getenv("WEATHER_LON", "37.6173"))
    WEATHER_CITY = os.getenv("WEATHER_CITY", "Москва")
    WEATHER_TZ = os.getenv("WEATHER_TZ", "Europe/Moscow")

    # Новости
    NEWS_FEEDS = _split(os.getenv("NEWS_FEEDS", ""))
    NEWS_MAX_ITEMS = int(os.getenv("NEWS_MAX_ITEMS", "8"))

    # Курсы
    CURRENCIES = _split(os.getenv("CURRENCIES", "USD,EUR"))

    # Криптовалюты (id CoinGecko). Пусто → карточка крипты скрыта.
    CRYPTO_COINS = _split(
        os.getenv("CRYPTO_COINS", "bitcoin,ethereum,the-open-network"))

    # Расписание
    DIGEST_TIME = os.getenv("DIGEST_TIME", "08:00")

    # Веб
    WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT = int(os.getenv("WEB_PORT", "8080"))

    # Авторизация (вход по QR через Telegram)
    AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
    DIGEST_DOMAIN = os.getenv("DIGEST_DOMAIN", "").strip()

    # LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()  # openai|anthropic|grok|gemini
    LLM_MODEL = os.getenv("LLM_MODEL", "").strip()  # пусто = дефолт провайдера
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
    GROK_API_KEY = os.getenv("GROK_API_KEY", "").strip()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    # Профиль пользователя (для персонализации LLM)
    PROFILE_NAME = os.getenv("PROFILE_NAME", "").strip()
    PROFILE_ROLE = os.getenv("PROFILE_ROLE", "").strip()
    PROFILE_PRIORITIES = os.getenv("PROFILE_PRIORITIES", "").strip()
    PROFILE_INTERESTS = os.getenv("PROFILE_INTERESTS", "").strip()
    PROFILE_EXTRA = os.getenv("PROFILE_EXTRA", "").strip()

    @property
    def gmail_enabled(self):
        return bool(self.GMAIL_USER and self.GMAIL_APP_PASSWORD)

    @property
    def telegram_enabled(self):
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID)

    @property
    def auth_enabled(self):
        return self.AUTH_ENABLED

    @property
    def llm_api_key(self):
        return {
            "openai": self.OPENAI_API_KEY,
            "anthropic": self.ANTHROPIC_API_KEY,
            "grok": self.GROK_API_KEY,
            "gemini": self.GEMINI_API_KEY,
        }.get(self.LLM_PROVIDER, "")

    @property
    def llm_enabled(self):
        return bool(self.LLM_PROVIDER and self.llm_api_key)

    @property
    def profile(self):
        return {
            "name": self.PROFILE_NAME,
            "role": self.PROFILE_ROLE,
            "priorities": self.PROFILE_PRIORITIES,
            "interests": self.PROFILE_INTERESTS,
            "extra": self.PROFILE_EXTRA,
        }


config = Config()
