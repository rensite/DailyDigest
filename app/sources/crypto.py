"""Курсы криптовалют через CoinGecko (без API-ключа)."""
import requests

# id монеты в CoinGecko -> тикер для отображения
TICKERS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "the-open-network": "TON",
    "tether": "USDT",
    "solana": "SOL",
    "the-open-network-ton": "TON",
}


def get_crypto(coin_ids: list) -> dict:
    """Цены монет в USD и RUB + изменение за 24ч.

    coin_ids — список id CoinGecko (например ["bitcoin","ethereum"]).
    Пустой список → карточка крипты не показывается (ok=False, items=[]).
    """
    if not coin_ids:
        return {"ok": False, "error": "не настроено", "items": []}
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": ",".join(coin_ids),
                "vs_currencies": "usd,rub",
                "include_24hr_change": "true",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        items = []
        for cid in coin_ids:
            v = data.get(cid)
            if not v:
                continue
            items.append({
                "code": TICKERS.get(cid, cid[:4].upper()),
                "usd": v.get("usd"),
                "rub": v.get("rub"),
                "change24h": v.get("usd_24h_change"),
            })
        if not items:
            return {"ok": False, "error": "нет данных", "items": []}
        return {"ok": True, "items": items}
    except Exception as e:
        return {"ok": False, "error": str(e), "items": []}
