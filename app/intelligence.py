"""
Умный слой: превращает сырые данные в персональную сводку через LLM.

Четыре функции:
  - morning_greeting   — личное утреннее обращение «под тебя»
  - summarize_news     — выжимка главного из новостей
  - analyze_inbox      — приоритеты и конкретные действия по почте
  - prioritize_todos   — умная сортировка дел по важности

Каждая функция при недоступном LLM возвращает None — вызывающий код
использует обычную (не-LLM) логику как запасной вариант.
"""
import json
import logging

log = logging.getLogger("digest.intelligence")

PERSONA = (
    "Ты — личный утренний ассистент пользователя. Обращайся на «ты», "
    "тепло и по-человечески, но без лишней воды и без канцелярита. "
    "Пиши живым русским языком. Не используй эмодзи в избытке — максимум "
    "один-два там, где это уместно. Будь конкретным и полезным."
)


def _profile_block(profile: dict) -> str:
    if not profile or not any(profile.values()):
        return "О пользователе ничего не известно."
    parts = []
    if profile.get("name"):
        parts.append(f"Имя: {profile['name']}")
    if profile.get("role"):
        parts.append(f"Чем занимается: {profile['role']}")
    if profile.get("priorities"):
        parts.append(f"Главные приоритеты сейчас: {profile['priorities']}")
    if profile.get("interests"):
        parts.append(f"Интересы: {profile['interests']}")
    if profile.get("extra"):
        parts.append(f"Дополнительно: {profile['extra']}")
    return "\n".join(parts)


def morning_greeting(llm, profile: dict, weather: dict, rates: dict,
                     todos: list, mail: dict) -> str:
    """Личное утреннее обращение, связывающее всю картину дня."""
    if not llm or not llm.enabled:
        return None

    ctx = {
        "погода": _safe_weather(weather),
        "курсы": _safe_rates(rates),
        "дел_всего": len(todos),
        "срочных_писем": sum(1 for e in mail.get("emails", [])
                             if e.get("actionable")) if mail.get("ok") else 0,
        "новых_писем": mail.get("count", 0) if mail.get("ok") else 0,
    }
    system = PERSONA
    user = (
        f"Профиль пользователя:\n{_profile_block(profile)}\n\n"
        f"Данные на это утро:\n{json.dumps(ctx, ensure_ascii=False)}\n\n"
        "Напиши короткое (3-4 предложения) тёплое утреннее обращение лично "
        "для пользователя. Учти погоду, загрузку по делам и почте, и его "
        "приоритеты. Задай настрой на день, мягко подскажи, на чём "
        "сфокусироваться. Без списков, просто живой абзац."
    )
    return llm.complete(system, user, max_tokens=350, temperature=0.7)


def summarize_news(llm, profile: dict, news_items: list) -> str:
    """Выжимка главного из новостей с учётом интересов пользователя."""
    if not llm or not llm.enabled or not news_items:
        return None

    titles = "\n".join(
        f"- {i['title']} ({i['source']})" for i in news_items
    )
    system = PERSONA
    user = (
        f"Профиль пользователя:\n{_profile_block(profile)}\n\n"
        f"Заголовки новостей за сегодня:\n{titles}\n\n"
        "Сделай короткую выжимку (2-4 предложения): что действительно важно "
        "и стоит внимания, особенно с учётом интересов пользователя. "
        "Не пересказывай все заголовки — выдели суть и тренды. "
        "Пиши связным текстом, без списка."
    )
    return llm.complete(system, user, max_tokens=400, temperature=0.5)


def analyze_inbox(llm, profile: dict, emails: list) -> list:
    """Разбор почты: для каждого важного письма — приоритет и действие.

    Возвращает список dict: {subject, from, priority, action}
    priority ∈ {high, medium, low}.
    """
    if not llm or not llm.enabled or not emails:
        return None

    compact = [{"subject": e["subject"], "from": e.get("from", "")}
               for e in emails]
    system = PERSONA
    user = (
        f"Профиль пользователя:\n{_profile_block(profile)}\n\n"
        f"Список писем (тема и отправитель):\n"
        f"{json.dumps(compact, ensure_ascii=False)}\n\n"
        "Проанализируй и верни JSON-массив объектов вида:\n"
        '{"subject": "...", "from": "...", "priority": "high|medium|low", '
        '"action": "короткое конкретное действие в 3-6 слов"}\n'
        "Расставь приоритеты с учётом срочности и важности для пользователя. "
        "Спам/рассылки помечай low. Верни только письма, по которым реально "
        "нужно что-то сделать или знать (можно опустить явный мусор)."
    )
    result = llm.complete_json(system, user, max_tokens=900, temperature=0.3)
    if isinstance(result, dict):
        # Иногда модель оборачивает в {"emails": [...]}
        for v in result.values():
            if isinstance(v, list):
                return v
        return None
    return result if isinstance(result, list) else None


def prioritize_todos(llm, profile: dict, todos: list) -> list:
    """Умная сортировка дел по важности с пояснением.

    Возвращает список dict: {text, priority, why}
    """
    if not llm or not llm.enabled or not todos:
        return None

    compact = [t["text"] for t in todos]
    system = PERSONA
    user = (
        f"Профиль пользователя:\n{_profile_block(profile)}\n\n"
        f"Список дел на сегодня:\n{json.dumps(compact, ensure_ascii=False)}\n\n"
        "Отсортируй дела от самого важного к менее важному с учётом "
        "приоритетов пользователя. Верни JSON-массив:\n"
        '{"text": "...", "priority": "high|medium|low", '
        '"why": "почему именно так, 3-7 слов"}'
    )
    result = llm.complete_json(system, user, max_tokens=700, temperature=0.3)
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                return v
        return None
    return result if isinstance(result, list) else None


def _safe_weather(w: dict) -> dict:
    if not w or not w.get("ok"):
        return {}
    return {"город": w.get("city"), "температура": w.get("temp"),
            "описание": w.get("description"),
            "осадки_%": w.get("precip_prob"),
            "день": f"{w.get('t_min')}…{w.get('t_max')}"}


def _safe_rates(r: dict) -> list:
    if not r or not r.get("ok"):
        return []
    return [{"код": x["code"], "значение": x["value"],
             "дельта": x["delta"]} for x in r.get("rates", [])]
