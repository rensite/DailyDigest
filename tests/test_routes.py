"""Тесты HTTP-роутов: редирект на логин, health, страница входа."""
import unittest

import main
from app.login_page import render_login


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.c = main.app.test_client()

    def test_index_redirects_to_login_when_unauthed(self):
        # AUTH_ENABLED по умолчанию true, сессии нет → 302 на /login
        r = self.c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers.get("Location", ""))

    def test_health_ok(self):
        r = self.c.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json().get("status"), "ok")

    def test_login_without_bot_returns_503(self):
        # имя бота определяется в рантайме (getMe); в тестах пусто → 503
        main.BOT_USERNAME["value"] = ""
        r = self.c.get("/login")
        self.assertEqual(r.status_code, 503)

    def test_login_renders_when_bot_set(self):
        main.BOT_USERNAME["value"] = "test_bot"
        try:
            r = self.c.get("/login")
            self.assertEqual(r.status_code, 200)
            body = r.get_data(as_text=True)
            self.assertIn("Утренняя сводка", body)
            self.assertIn("id=\"qr\"", body)
        finally:
            main.BOT_USERNAME["value"] = ""


class LoginPageTest(unittest.TestCase):
    def test_render_login_has_deeplink_and_theme(self):
        html = render_login("tok123", "my_bot")
        self.assertIn("https://t.me/my_bot?start=tok123", html)
        self.assertIn("tok123", html)
        # тёмная тема подключена
        self.assertIn("html.dark", html)
        self.assertIn("dd-theme", html)


if __name__ == "__main__":
    unittest.main()
