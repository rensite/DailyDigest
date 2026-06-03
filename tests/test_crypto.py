"""Тесты источника крипты (CoinGecko) — парсинг и graceful degradation."""
import unittest
from unittest import mock

from app.sources import crypto


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class CryptoTest(unittest.TestCase):
    def test_empty_coins_returns_not_ok(self):
        out = crypto.get_crypto([])
        self.assertFalse(out["ok"])
        self.assertEqual(out["items"], [])

    def test_parse_success(self):
        payload = {
            "bitcoin": {"usd": 103240, "rub": 8156000, "usd_24h_change": 1.83},
            "the-open-network": {"usd": 5.12, "rub": 405, "usd_24h_change": -2.1},
        }
        with mock.patch.object(crypto.requests, "get",
                               return_value=FakeResp(payload)) as g:
            out = crypto.get_crypto(["bitcoin", "the-open-network"])
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["items"]), 2)
        btc = out["items"][0]
        self.assertEqual(btc["code"], "BTC")
        self.assertEqual(btc["usd"], 103240)
        self.assertEqual(btc["rub"], 8156000)
        self.assertAlmostEqual(btc["change24h"], 1.83)
        self.assertEqual(out["items"][1]["code"], "TON")
        # запросили оба значения валют
        _, kwargs = g.call_args
        self.assertEqual(kwargs["params"]["vs_currencies"], "usd,rub")

    def test_unknown_coin_skipped(self):
        payload = {"bitcoin": {"usd": 100, "rub": 8000, "usd_24h_change": 0.5}}
        with mock.patch.object(crypto.requests, "get",
                               return_value=FakeResp(payload)):
            out = crypto.get_crypto(["bitcoin", "doesnotexist"])
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["items"]), 1)

    def test_network_error_graceful(self):
        with mock.patch.object(crypto.requests, "get",
                               side_effect=Exception("boom")):
            out = crypto.get_crypto(["bitcoin"])
        self.assertFalse(out["ok"])
        self.assertIn("boom", out["error"])
        self.assertEqual(out["items"], [])


if __name__ == "__main__":
    unittest.main()
