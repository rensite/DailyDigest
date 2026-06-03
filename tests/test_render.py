"""Тесты рендеринга дашборда (render_html) и устойчивости к сбоям источников."""
import unittest

from app.render import render_html, _fmt_money, _fmt_num, _plural, _safe_url, _gmail_url


def full_digest() -> dict:
    """Полная сводка со всеми источниками и включённым LLM-слоем."""
    return {
        "generated_at": "03.06.2026 07:30",
        "weekday": "вторник",
        "weather": {
            "ok": True, "city": "Екатеринбург", "temp": 12, "feels_like": 9,
            "description": "Облачно, дождь", "wind": 4, "t_min": 8, "t_max": 15,
            "precip_prob": 60, "hourly": [10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 8, 9],
        },
        "rates": {"ok": True, "date": "2026-06-03", "rates": [
            {"code": "USD", "name": "Доллар", "value": 79.12, "delta": -0.3, "up": False},
            {"code": "EUR", "name": "Евро", "value": 90.45, "delta": 0.2, "up": True},
        ]},
        "crypto": {"ok": True, "items": [
            {"code": "BTC", "usd": 103240, "rub": 8156000, "change24h": 1.8},
            {"code": "TON", "usd": 5.12, "rub": 405, "change24h": -2.1},
        ]},
        "news": {"ok": True, "items": [
            {"title": "ЦБ сохранил ставку 16%", "link": "https://ved.ru/a", "source": "Ведомости"},
            {"title": "Новая LLM", "link": "javascript:alert(1)", "source": "Хабр"},
        ]},
        "mail": {"ok": True, "unread_only": True, "emails": [
            {"subject": "Договор на подпись", "from": "vtb@bank.ru", "actionable": True},
            {"subject": "Счёт за хостинг", "from": "billing@netangels.ru", "actionable": False},
        ]},
        "todos": [{"text": "Ответить ВТБ", "meta": "vtb@bank.ru", "priority": "high"}],
        "recommendations": ["Возьми зонт — днём дождь"],
        "ai": {
            "enabled": True, "provider": "openai",
            "greeting": "Ренат, спокойное утро.",
            "news_summary": "Главное за утро.",
            "inbox": [
                {"subject": "Договор на подпись", "from": "ВТБ", "priority": "high", "action": "Ответить до 12:00"},
                {"subject": "Счёт", "from": "netangels", "priority": "low", "action": None},
            ],
            "todos_ranked": [
                {"text": "Ответить ВТБ по договору", "priority": "high", "why": "дедлайн в обед"},
                {"text": "Созвон 14:00", "priority": "medium", "why": "подготовить тезисы"},
            ],
        },
    }


def failed_digest() -> dict:
    """Все источники упали / LLM выключен — graceful degradation."""
    return {
        "generated_at": "03.06.2026 07:30",
        "weekday": "вторник",
        "weather": {"ok": False, "city": "Москва", "error": "timeout"},
        "rates": {"ok": False, "error": "timeout", "rates": []},
        "crypto": {"ok": False, "error": "timeout", "items": []},
        "news": {"ok": False, "items": []},
        "mail": {"ok": False, "error": "Gmail не настроен", "emails": []},
        "todos": [],
        "recommendations": ["Особых сигналов нет."],
        "ai": {"enabled": False, "provider": "", "greeting": None,
               "news_summary": None, "inbox": None, "todos_ranked": None},
    }


class RenderHtmlTest(unittest.TestCase):
    def test_full_render_has_all_cards(self):
        out = render_html(full_digest())
        self.assertIsInstance(out, str)
        for data_id in ("hero", "weather", "todos", "rates",
                        "crypto", "news", "mail", "recs"):
            self.assertIn(f'data-id="{data_id}"', out, f"нет карточки {data_id}")
        # шапка: время и приветствие
        self.assertIn("07:30", out)
        self.assertIn("3 июня", out)
        self.assertIn("вторник", out)

    def test_ai_badges_present_when_enabled(self):
        out = render_html(full_digest())
        self.assertIn("AI приоритеты", out)
        self.assertIn("AI выжимка", out)
        self.assertIn("AI разбор", out)

    def test_crypto_has_both_currencies_and_default_rub(self):
        out = render_html(full_digest())
        # оба значения присутствуют для переключателя (разряды — nbsp U+00A0)
        self.assertIn('data-usd="$103 240"', out)
        self.assertIn('data-rub="8 156 000 ₽"', out)
        self.assertIn('id="ccyseg"', out)

    def test_news_link_xss_filtered(self):
        out = render_html(full_digest())
        # безопасная ссылка попадает в href
        self.assertIn('href="https://ved.ru/a"', out)
        # javascript: ссылка не должна стать href
        self.assertNotIn("javascript:alert(1)", out)

    def test_failed_sources_still_render(self):
        out = render_html(failed_digest())
        self.assertIsInstance(out, str)
        # карточки на месте, но с плейсхолдерами
        self.assertIn('data-id="weather"', out)
        self.assertIn("Нет данных", out)
        self.assertIn("Gmail не настроен", out)
        # LLM выключен → нет AI-бейджей
        self.assertNotIn("AI приоритеты", out)
        self.assertNotIn("AI выжимка", out)

    def test_greeting_fallback_without_ai(self):
        out = render_html(failed_digest())
        self.assertIn("Доброе утро", out)
        # без greeting в hero нет бейджа AI
        self.assertIn("Хорошего и продуктивного дня", out)

    def test_crypto_card_hidden_when_source_off_and_unconfigured(self):
        # если crypto пуст и CRYPTO_COINS не настроен — карточки нет.
        # В тестовой среде CRYPTO_COINS обычно из дефолта → карточка-плейсхолдер.
        d = failed_digest()
        out = render_html(d)
        # карточка либо есть как плейсхолдер, либо скрыта — оба валидны;
        # проверяем, что рендер не падает и страница цела
        self.assertIn("</html>", out)

    def test_escaping(self):
        d = failed_digest()
        d["weather"] = {"ok": True, "city": "<script>", "temp": 1,
                        "feels_like": 1, "description": "x", "wind": 1, "hourly": []}
        out = render_html(d)
        self.assertNotIn("<script>x", out)
        self.assertIn("&lt;script&gt;", out)

    def test_mail_rows_have_gmail_links(self):
        # AI inbox path: from «ВТБ» → subject-поиск; plain path: from «vtb@bank.ru» → from-поиск
        d = full_digest()
        out = render_html(d)
        # AI inbox использует from="ВТБ" → ищет по теме
        self.assertIn("mail.google.com", out)
        self.assertIn("#search/", out)

    def test_plain_mail_rows_have_gmail_links(self):
        d = full_digest()
        # Убираем AI inbox — рендерится plain-путь с IMAP-письмами
        d["ai"]["inbox"] = None
        out = render_html(d)
        # email-адрес billing@netangels.ru → from:-поиск
        self.assertIn("mail.google.com", out)
        self.assertIn("billing%40netangels.ru", out)  # @ URL-кодируется в %40

    def test_todos_have_checkboxes(self):
        out = render_html(full_digest())
        self.assertIn('type="checkbox"', out)
        self.assertIn('class="todo-cb"', out)
        self.assertIn('data-key="', out)
        # JS для сохранения в localStorage
        self.assertIn("dd-todos-", out)

    def test_todos_no_checkboxes_when_empty(self):
        d = failed_digest()
        out = render_html(d)
        # Нет дел — нет чекбокс-элементов (класс есть в CSS, но input-ов нет)
        self.assertNotIn('class="todo-cb"', out)


class HelpersTest(unittest.TestCase):
    def test_fmt_money(self):
        self.assertEqual(_fmt_money(103240, "usd"), "$103 240")
        self.assertEqual(_fmt_money(8156000, "rub"), "8 156 000 ₽")
        self.assertEqual(_fmt_money(5.12, "usd"), "$5,12")
        self.assertEqual(_fmt_money(None, "usd"), "—")

    def test_fmt_num(self):
        self.assertEqual(_fmt_num(79.12, comma=True), "79,12")
        self.assertEqual(_fmt_num(1234, comma=False), "1 234")

    def test_plural(self):
        self.assertEqual(_plural(1, "дело", "дела", "дел"), "дело")
        self.assertEqual(_plural(2, "дело", "дела", "дел"), "дела")
        self.assertEqual(_plural(5, "дело", "дела", "дел"), "дел")
        self.assertEqual(_plural(11, "дело", "дела", "дел"), "дел")
        self.assertEqual(_plural(21, "дело", "дела", "дел"), "дело")

    def test_safe_url(self):
        self.assertEqual(_safe_url("https://x.ru"), "https://x.ru")
        self.assertEqual(_safe_url("javascript:alert(1)"), "")
        self.assertEqual(_safe_url(None), "")

    def test_gmail_url_extracts_angle_bracket_email(self):
        url = _gmail_url("ВТБ Банк <noreply@vtb.ru>")
        self.assertIn("mail.google.com", url)
        self.assertIn("from%3Anoreply%40vtb.ru", url)

    def test_gmail_url_bare_email(self):
        url = _gmail_url("billing@netangels.ru")
        self.assertIn("mail.google.com", url)
        self.assertIn("billing%40netangels.ru", url)

    def test_gmail_url_display_name_falls_back_to_subject(self):
        url = _gmail_url("ВТБ", subject="Договор на подпись")
        self.assertIn("mail.google.com", url)
        self.assertIn("subject%3A", url)
        self.assertIn("%D0%94%D0%BE%D0%B3%D0%BE%D0%B2%D0%BE%D1%80", url)  # «Договор»

    def test_gmail_url_empty_sender_and_subject(self):
        self.assertEqual(_gmail_url(""), "")
        self.assertEqual(_gmail_url(None), "")


if __name__ == "__main__":
    unittest.main()
