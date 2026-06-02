"""Отправка сводки в Telegram."""
import requests


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    """Отправляет сообщение. Telegram ограничивает длину 4096 символами."""
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Разбиваем длинный текст на части
    chunks = _split(text, 4000)
    ok = True
    for chunk in chunks:
        try:
            r = requests.post(url, data={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }, timeout=20)
            if r.status_code != 200:
                ok = False
        except Exception:
            ok = False
    return ok


def _split(text: str, limit: int) -> list:
    if len(text) <= limit:
        return [text]
    parts, buf = [], ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > limit:
            parts.append(buf)
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        parts.append(buf)
    return parts
