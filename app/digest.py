"""Сбор всех источников в единую сводку + список дел и рекомендации."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import config
from .sources.weather import get_weather
from .sources.currency import get_rates
from .sources.news import get_news
from .sources.mail import get_emails
from .llm import LLMClient
from . import intelligence

log = logging.getLogger("digest.build")


def build_digest() -> dict:
    """Собирает все данные и формирует структуру сводки."""
    tz = ZoneInfo(config.WEATHER_TZ)
    now = datetime.now(tz)

    weather = get_weather(
        config.WEATHER_LAT, config.WEATHER_LON,
        config.WEATHER_TZ, config.WEATHER_CITY,
    )
    rates = get_rates(config.CURRENCIES)
    news = get_news(config.NEWS_FEEDS, config.NEWS_MAX_ITEMS)

    if config.gmail_enabled:
        mail = get_emails(
            config.GMAIL_USER, config.GMAIL_APP_PASSWORD,
            config.GMAIL_MAX_EMAILS, config.GMAIL_UNREAD_ONLY,
        )
    else:
        mail = {"ok": False, "error": "Gmail не настроен", "emails": []}

    todos = _build_todos(mail)
    recommendations = _build_recommendations(weather, rates, mail)

    # --- Умный слой (LLM) ---
    ai = _build_intelligence(weather, rates, news, mail, todos)

    return {
        "generated_at": now.strftime("%d.%m.%Y %H:%M"),
        "weekday": _weekday_ru(now),
        "weather": weather,
        "rates": rates,
        "news": news,
        "mail": mail,
        "todos": todos,
        "recommendations": recommendations,
        "ai": ai,
    }


def _build_intelligence(weather, rates, news, mail, todos) -> dict:
    """Прогоняет данные через LLM. При недоступности — пустые поля."""
    ai = {
        "enabled": False,
        "provider": config.LLM_PROVIDER,
        "greeting": None,
        "news_summary": None,
        "inbox": None,
        "todos_ranked": None,
    }
    if not config.llm_enabled:
        return ai

    llm = LLMClient(config.LLM_PROVIDER, config.llm_api_key, config.LLM_MODEL)
    if not llm.enabled:
        return ai

    ai["enabled"] = True
    profile = config.profile

    try:
        ai["greeting"] = intelligence.morning_greeting(
            llm, profile, weather, rates, todos, mail)
    except Exception as e:
        log.warning("greeting failed: %s", e)

    try:
        if news.get("items"):
            ai["news_summary"] = intelligence.summarize_news(
                llm, profile, news["items"])
    except Exception as e:
        log.warning("news summary failed: %s", e)

    try:
        if mail.get("ok") and mail.get("emails"):
            ai["inbox"] = intelligence.analyze_inbox(
                llm, profile, mail["emails"])
    except Exception as e:
        log.warning("inbox analysis failed: %s", e)

    try:
        if todos:
            ai["todos_ranked"] = intelligence.prioritize_todos(
                llm, profile, todos)
    except Exception as e:
        log.warning("todo prioritization failed: %s", e)

    return ai


def _weekday_ru(dt: datetime) -> str:
    days = ["понедельник", "вторник", "среда", "четверг",
            "пятница", "суббота", "воскресенье"]
    return days[dt.weekday()]


def _build_todos(mail: dict) -> list:
    """Список дел: письма, помеченные как требующие действия."""
    todos = []
    if mail.get("ok"):
        for e in mail.get("emails", []):
            if e.get("actionable"):
                todos.append({
                    "text": f"Ответить/обработать: «{e['subject']}»",
                    "meta": e.get("from", ""),
                    "priority": "high",
                })
    return todos


def _build_recommendations(weather: dict, rates: dict, mail: dict) -> list:
    """Простые эвристические рекомендации из текущей картины."""
    recs = []

    # Погода
    if weather.get("ok"):
        if weather.get("precip_prob", 0) >= 50:
            recs.append("Возьмите зонт — высокая вероятность осадков.")
        if weather.get("t_min", 99) <= 0:
            recs.append("Минусовая температура — оденьтесь теплее.")
        elif weather.get("temp", 0) >= 25:
            recs.append("Жарко — пейте больше воды.")

    # Курсы
    if rates.get("ok"):
        for r in rates.get("rates", []):
            if r["up"] and abs(r["delta"]) >= 0.5:
                recs.append(
                    f"{r['code']} заметно вырос (+{r['delta']} ₽) — "
                    f"учтите при валютных операциях."
                )

    # Почта
    if mail.get("ok"):
        action_count = sum(1 for e in mail.get("emails", []) if e.get("actionable"))
        if action_count >= 3:
            recs.append(
                f"Накопилось {action_count} писем, требующих ответа — "
                f"запланируйте время на разбор почты."
            )
        elif action_count == 0 and mail.get("emails"):
            recs.append("Срочных писем нет — можно сфокусироваться на главной задаче дня.")

    if not recs:
        recs.append("Особых сигналов нет. Хорошего продуктивного дня!")
    return recs
