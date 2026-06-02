"""Курсы валют через ЦБ РФ (без API-ключа)."""
import requests


def get_rates(currencies: list) -> dict:
    """Возвращает курсы указанных валют к рублю, с дельтой к предыдущему дню."""
    try:
        r = requests.get(
            "https://www.cbr-xml-daily.ru/daily_json.js", timeout=15
        )
        r.raise_for_status()
        data = r.json()
        valute = data.get("Valute", {})
        out = []
        for code in currencies:
            v = valute.get(code.upper())
            if not v:
                continue
            value = v["Value"] / v["Nominal"]
            prev = v["Previous"] / v["Nominal"]
            delta = value - prev
            out.append({
                "code": code.upper(),
                "name": v.get("Name", code),
                "value": round(value, 4),
                "delta": round(delta, 4),
                "up": delta > 0,
            })
        return {"ok": True, "date": data.get("Date", ""), "rates": out}
    except Exception as e:
        return {"ok": False, "error": str(e), "rates": []}
