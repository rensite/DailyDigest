"""Погода через Open-Meteo (без API-ключа)."""
import requests

WMO = {
    0: "Ясно", 1: "Преим. ясно", 2: "Переменная облачность", 3: "Пасмурно",
    45: "Туман", 48: "Изморозь", 51: "Морось слабая", 53: "Морось",
    55: "Морось сильная", 61: "Дождь слабый", 63: "Дождь", 65: "Дождь сильный",
    66: "Ледяной дождь", 67: "Ледяной дождь сильный", 71: "Снег слабый",
    73: "Снег", 75: "Снег сильный", 77: "Снежная крупа", 80: "Ливень",
    81: "Ливень", 82: "Сильный ливень", 85: "Снегопад", 86: "Сильный снегопад",
    95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза с градом",
}


def get_weather(lat: float, lon: float, tz: str, city: str) -> dict:
    """Возвращает текущую погоду и прогноз на день."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "timezone": tz,
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "precipitation_probability_max,weather_code",
                "forecast_days": 1,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        cur = data.get("current", {})
        daily = data.get("daily", {})
        code = cur.get("weather_code", 0)
        return {
            "ok": True,
            "city": city,
            "temp": round(cur.get("temperature_2m", 0)),
            "feels_like": round(cur.get("apparent_temperature", 0)),
            "description": WMO.get(code, "—"),
            "wind": round(cur.get("wind_speed_10m", 0)),
            "t_max": round(daily.get("temperature_2m_max", [0])[0]),
            "t_min": round(daily.get("temperature_2m_min", [0])[0]),
            "precip_prob": daily.get("precipitation_probability_max", [0])[0],
        }
    except Exception as e:
        return {"ok": False, "city": city, "error": str(e)}
