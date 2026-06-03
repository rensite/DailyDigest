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
                     todos: list, mail: dict, news: dict = None,
                     crypto: dict = None) -> str:
    """Персональная AI-сводка дня: самое интересное из всех источников."""
    if not llm or not llm.enabled:
        return None

    # --- собираем контекст ---
    ctx_parts = []

    w = _safe_weather(weather)
    if w:
        ctx_parts.append(f"Погода: {w.get('описание')}, {w.get('температура')}°C "
                         f"(день {w.get('день')}), осадки {w.get('осадки_%')}%")

    r = _safe_rates(rates)
    if r:
        rate_str = ", ".join(f"{x['код']} {x['значение']} ₽ "
                             f"({'▲' if x['дельта'] > 0 else '▼'}{abs(x['дельта'])})"
                             for x in r)
        ctx_parts.append(f"Курсы ЦБ: {rate_str}")

    if crypto and crypto.get("ok") and crypto.get("items"):
        cr_str = ", ".join(
            f"{it['code']} ${it['usd']} "
            f"({'▲' if (it.get('change24h') or 0) > 0 else '▼'}{abs(it.get('change24h') or 0):.1f}%)"
            for it in crypto["items"]
        )
        ctx_parts.append(f"Крипто: {cr_str}")

    if news and news.get("items"):
        top = news["items"][:5]
        headlines = "\n".join(f"  • {i['title']} ({i['source']})" for i in top)
        ctx_parts.append(f"Топ новостей:\n{headlines}")

    if todos:
        todo_str = "; ".join(t.get("text", "") for t in todos[:4])
        ctx_parts.append(f"Дел на сегодня ({len(todos)}): {todo_str}")

    urgent = []
    if mail.get("ok"):
        urgent = [e for e in mail.get("emails", []) if e.get("actionable")]
    if urgent:
        mail_str = "; ".join(e.get("subject", "") for e in urgent[:3])
        ctx_parts.append(f"Срочных писем {len(urgent)}: {mail_str}")
    elif mail.get("ok"):
        ctx_parts.append("Срочных писем нет.")

    context = "\n".join(ctx_parts) or "Данных нет."

    system = PERSONA
    user = (
        f"Профиль пользователя:\n{_profile_block(profile)}\n\n"
        f"Данные на это утро:\n{context}\n\n"
        "Напиши персональную утреннюю сводку для пользователя (5-8 предложений): "
        "обратись по имени, упомяни самое интересное или важное из новостей, "
        "предупреди о погоде если есть повод, отметь ключевое дело или срочное письмо, "
        "коротко скажи о примечательных движениях курсов или крипты если есть. "
        "Пиши живым разговорным языком, без списков — связный абзац-сводка. "
        "Не пересказывай все данные подряд — выбери самое важное."
    )
    return llm.complete(system, user, max_tokens=500, temperature=0.7)


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
