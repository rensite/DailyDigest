"""Чтение почты Gmail через IMAP (app password)."""
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone

IMAP_HOST = "imap.gmail.com"

# Ключевые слова, по которым письмо считаем требующим действия
ACTION_KEYWORDS = [
    "срочно", "asap", "deadline", "дедлайн", "до завтра", "сегодня до",
    "просьба", "пожалуйста", "ожидаю", "жду ответ", "оплат", "счёт", "счет",
    "invoice", "payment", "подтверд", "согласуй", "review", "approve",
    "action required", "требуется", "напоминание", "reminder",
]


def _decode(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out += text.decode(enc or "utf-8", errors="replace")
            except (LookupError, TypeError):
                out += text.decode("utf-8", errors="replace")
        else:
            out += text
    return out.strip()


def _is_actionable(subject: str) -> bool:
    s = subject.lower()
    return any(k in s for k in ACTION_KEYWORDS)


def get_emails(user: str, app_password: str, max_emails: int,
               unread_only: bool) -> dict:
    """Возвращает список последних писем с пометкой 'требует действия'."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(user, app_password)
        mail.select("INBOX")

        criteria = "UNSEEN" if unread_only else "ALL"
        status, data = mail.search(None, criteria)
        if status != "OK":
            mail.logout()
            return {"ok": False, "error": "search failed", "emails": []}

        ids = data[0].split()
        ids = ids[-max_emails:]  # последние N
        ids.reverse()  # новые сверху

        emails = []
        for eid in ids:
            status, msg_data = mail.fetch(eid, "(RFC822.HEADER)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode(msg.get("Subject", ""))
            sender = _decode(msg.get("From", ""))
            date_raw = msg.get("Date", "")
            emails.append({
                "subject": subject or "(без темы)",
                "from": sender,
                "date": date_raw,
                "actionable": _is_actionable(subject),
            })

        mail.logout()
        return {
            "ok": True,
            "emails": emails,
            "unread_only": unread_only,
            "count": len(emails),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "emails": []}
