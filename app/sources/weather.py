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


def _next_hours(hourly: dict, current_time, count: int) -> list:
    """Температуры на ближайшие `count` часов начиная с текущего часа.

    Open-Meteo отдаёт почасовой ряд от начала суток; находим индекс текущего
    часа и берём следующие `count` значений. Если что-то пошло не так —
    возвращаем пустой список (карточка просто не рисует график)."""
    times = hourly.get("time", []) or []
    temps = hourly.get("temperature_2m", []) or []
    if not times or not temps:
        return []
    start = 0
    if current_time:
        # current_time вида "2026-06-03T07:00"; почасовые тоже до минут
        cur_hour = current_time[:13]  # "2026-06-03T07"
        for i, t in enumerate(times):
            if t[:13] >= cur_hour:
                start = i
                break
    return [round(t) for t in temps[start:start + count] if t is not None]


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
                "hourly": "temperature_2m",
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "precipitation_probability_max,weather_code",
                "forecast_days": 2,
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
            "hourly": _next_hours(data.get("hourly", {}), cur.get("time"), 12),
        }
    except Exception as e:
        return {"ok": False, "city": city, "error": str(e)}
