"""Clima y calidad del aire con Open-Meteo (sin API key).

Mantiene el estado actual, hourly, previsión diaria y un histórico diario
persistente. No requiere credenciales.
"""

import copy
import json
import logging
import threading
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

from app.billing import get_timezone
from app.config import Settings

logger = logging.getLogger(__name__)

WMO: dict[int, tuple[str, str]] = {
    0: ("Despejado", "sun"),
    1: ("Mayormente despejado", "sun"),
    2: ("Parcialmente nublado", "cloud-sun"),
    3: ("Nublado", "cloud"),
    45: ("Niebla", "cloud-fog"),
    48: ("Niebla helada", "cloud-fog"),
    51: ("Llovizna ligera", "cloud-drizzle"),
    53: ("Llovizna", "cloud-drizzle"),
    55: ("Llovizna intensa", "cloud-drizzle"),
    56: ("Llovizna helada", "cloud-drizzle"),
    57: ("Llovizna helada intensa", "cloud-drizzle"),
    61: ("Lluvia ligera", "cloud-rain"),
    63: ("Lluvia", "cloud-rain"),
    65: ("Lluvia fuerte", "cloud-rain"),
    66: ("Lluvia helada", "cloud-rain"),
    67: ("Lluvia helada fuerte", "cloud-rain"),
    71: ("Nieve ligera", "snowflake"),
    73: ("Nieve", "snowflake"),
    75: ("Nieve fuerte", "snowflake"),
    77: ("Granos de nieve", "snowflake"),
    80: ("Chubascos ligeros", "cloud-rain"),
    81: ("Chubascos", "cloud-rain"),
    82: ("Chubascos fuertes", "cloud-rain"),
    85: ("Chubascos de nieve", "snowflake"),
    86: ("Chubascos de nieve fuertes", "snowflake"),
    95: ("Tormenta", "cloud-lightning"),
    96: ("Tormenta con granizo", "cloud-lightning"),
    99: ("Tormenta fuerte con granizo", "cloud-lightning"),
}


def condition_for_code(code: int | float | None) -> tuple[str, str]:
    try:
        return WMO.get(int(code or 0), ("Desconocido", "cloud"))
    except (TypeError, ValueError):
        return ("Desconocido", "cloud")


def aqi_category(value: int | float | None) -> tuple[str, str]:
    if value is None:
        return ("Sin datos", "unknown")
    if value <= 50:
        return ("Buena", "good")
    if value <= 100:
        return ("Moderada", "moderate")
    if value <= 150:
        return ("Mala para sensibles", "unhealthy-sensitive")
    if value <= 200:
        return ("Mala", "unhealthy")
    if value <= 300:
        return ("Muy mala", "very-unhealthy")
    return ("Peligrosa", "hazardous")


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Any, digits: int = 1) -> float | None:
    number = _num(value)
    return round(number, digits) if number is not None else None


def _mean(values: list[float]) -> float | None:
    return round(mean(values), 1) if values else None


class WeatherMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._tz = get_timezone(settings.weather_timezone)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._history: dict[str, dict[str, Any]] = self._load_history()
        self._state: dict[str, Any] = {
            "enabled": settings.weather_enabled,
            "location": {
                "name": settings.weather_location,
                "latitude": settings.weather_latitude,
                "longitude": settings.weather_longitude,
                "timezone": settings.weather_timezone,
            },
            "current": {},
            "today": {},
            "forecast": [],
            "history": [],
            "hourly": [],
            "hourly_past": [],
            "air": {},
            "rain": {},
            "alerts": [],
            "status": "unknown",
            "summary": {
                "label": "Temperatura",
                "value": "—",
                "unit": "°C",
                "detail": "Recopilando datos…",
            },
            "updated_at": None,
            "error": None,
        }

    # --- ciclo de vida ---------------------------------------------------
    def start(self) -> None:
        if not self.settings.weather_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="weather-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._refresh()
            if self._stop.wait(max(60, self.settings.weather_poll_seconds)):
                break

    # --- API -------------------------------------------------------------
    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = httpx.get(
            url,
            params=params,
            timeout=httpx.Timeout(20),
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": "HomeLabDash-Agent/0.1"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("respuesta meteorológica inválida")
        return payload

    def _refresh(self) -> None:
        try:
            forecast = self._get(
                self.settings.weather_forecast_url,
                {
                    "latitude": self.settings.weather_latitude,
                    "longitude": self.settings.weather_longitude,
                    "timezone": self.settings.weather_timezone,
                    "past_days": 31,
                    "forecast_days": 7,
                    "current": (
                        "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
                        "precipitation,rain,weather_code,cloud_cover,pressure_msl,"
                        "wind_speed_10m,wind_direction_10m,wind_gusts_10m,uv_index"
                    ),
                    "hourly": (
                        "temperature_2m,relative_humidity_2m,precipitation_probability,"
                        "precipitation,rain,weather_code,wind_speed_10m,uv_index"
                    ),
                    "daily": (
                        "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,"
                        "uv_index_max,precipitation_sum,rain_sum,precipitation_hours,"
                        "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max"
                    ),
                },
            )
            air: dict[str, Any] = {}
            try:
                air = self._get(
                    self.settings.weather_air_url,
                    {
                        "latitude": self.settings.weather_latitude,
                        "longitude": self.settings.weather_longitude,
                        "timezone": self.settings.weather_timezone,
                        "past_days": 31,
                        "forecast_days": 2,
                        "current": (
                            "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,"
                            "nitrogen_dioxide,sulphur_dioxide,ozone"
                        ),
                        "hourly": "us_aqi,european_aqi,pm2_5,pm10",
                    },
                )
            except (httpx.HTTPError, ValueError):
                air = {}
            self._apply(forecast, air)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            with self._lock:
                self._state["error"] = f"clima no disponible ({type(exc).__name__})"
            logger.warning("no se pudo actualizar el clima: %s", type(exc).__name__)

    def _apply(self, forecast: dict[str, Any], air: dict[str, Any]) -> None:
        now_local = datetime.now(self._tz).replace(tzinfo=None)
        today = now_local.date().isoformat()
        current_raw = forecast.get("current") or {}
        code = current_raw.get("weather_code")
        condition, icon = condition_for_code(code)
        current: dict[str, Any] = {
            "at": current_raw.get("time"),
            "temperature": _round(current_raw.get("temperature_2m")),
            "apparent_temperature": _round(current_raw.get("apparent_temperature")),
            "humidity": _round(current_raw.get("relative_humidity_2m"), 0),
            "precipitation": _round(current_raw.get("precipitation")),
            "rain": _round(current_raw.get("rain")),
            "weather_code": code,
            "condition": condition,
            "icon": icon,
            "cloud_cover": _round(current_raw.get("cloud_cover"), 0),
            "wind_speed": _round(current_raw.get("wind_speed_10m")),
            "wind_gusts": _round(current_raw.get("wind_gusts_10m")),
            "wind_direction": _round(current_raw.get("wind_direction_10m"), 0),
            "pressure": _round(current_raw.get("pressure_msl")),
            "uv_index": _round(current_raw.get("uv_index")),
            "is_day": bool(current_raw.get("is_day")),
        }

        hourly_raw = forecast.get("hourly") or {}
        hourly_times = [str(item) for item in hourly_raw.get("time") or []]
        hourly_humidity = hourly_raw.get("relative_humidity_2m") or []
        hourly_precip = hourly_raw.get("precipitation") or []
        hourly_rain = hourly_raw.get("rain") or []
        hourly_prob = hourly_raw.get("precipitation_probability") or []
        hourly_temp = hourly_raw.get("temperature_2m") or []
        hourly_wind = hourly_raw.get("wind_speed_10m") or []
        hourly_code = hourly_raw.get("weather_code") or []

        humidity_by_date: dict[str, list[float]] = defaultdict(list)
        for index, time_value in enumerate(hourly_times):
            humidity = _num(hourly_humidity[index] if index < len(hourly_humidity) else None)
            if humidity is not None:
                humidity_by_date[time_value[:10]].append(humidity)

        air_hourly = air.get("hourly") or {}
        air_times = [str(item) for item in air_hourly.get("time") or []]
        air_aqi = air_hourly.get("us_aqi") or []
        air_pm25 = air_hourly.get("pm2_5") or []
        air_pm10 = air_hourly.get("pm10") or []
        aqi_by_time: dict[str, float] = {}
        aqi_by_date: dict[str, list[float]] = defaultdict(list)
        for index, time_value in enumerate(air_times):
            value = _num(air_aqi[index] if index < len(air_aqi) else None)
            if value is not None:
                aqi_by_time[time_value] = value
                aqi_by_date[time_value[:10]].append(value)

        upcoming: list[dict[str, Any]] = []
        past: list[dict[str, Any]] = []
        for index, time_value in enumerate(hourly_times):
            try:
                moment = datetime.fromisoformat(time_value)
            except ValueError:
                continue
            code_value = hourly_code[index] if index < len(hourly_code) else 0
            hour_condition, hour_icon = condition_for_code(code_value)
            entry = {
                "at": time_value,
                "temperature": _round(hourly_temp[index] if index < len(hourly_temp) else None),
                "humidity": _round(
                    hourly_humidity[index] if index < len(hourly_humidity) else None, 0
                ),
                "precipitation": _round(
                    hourly_precip[index] if index < len(hourly_precip) else None
                ),
                "rain": _round(hourly_rain[index] if index < len(hourly_rain) else None),
                "probability": _round(hourly_prob[index] if index < len(hourly_prob) else None, 0),
                "wind": _round(hourly_wind[index] if index < len(hourly_wind) else None),
                "weather_code": code_value,
                "condition": hour_condition,
                "icon": hour_icon,
                "aqi": _round(aqi_by_time.get(time_value), 0),
            }
            if now_local - timedelta(hours=24) <= moment < now_local:
                past.append(entry)
            elif now_local <= moment <= now_local + timedelta(hours=24):
                upcoming.append(entry)

        daily_raw = forecast.get("daily") or {}
        daily_times = [str(item) for item in daily_raw.get("time") or []]
        daily_code = daily_raw.get("weather_code") or []
        daily_max = daily_raw.get("temperature_2m_max") or []
        daily_min = daily_raw.get("temperature_2m_min") or []
        daily_sunrise = daily_raw.get("sunrise") or []
        daily_sunset = daily_raw.get("sunset") or []
        daily_uv = daily_raw.get("uv_index_max") or []
        daily_precip = daily_raw.get("precipitation_sum") or []
        daily_rain = daily_raw.get("rain_sum") or []
        daily_hours = daily_raw.get("precipitation_hours") or []
        daily_prob = daily_raw.get("precipitation_probability_max") or []
        daily_wind = daily_raw.get("wind_speed_10m_max") or []
        daily_gusts = daily_raw.get("wind_gusts_10m_max") or []

        records: list[dict[str, Any]] = []
        for index, date_value in enumerate(daily_times):
            code_value = daily_code[index] if index < len(daily_code) else 0
            day_condition, day_icon = condition_for_code(code_value)
            precip_mm = _num(daily_precip[index] if index < len(daily_precip) else None) or 0.0
            rain_mm = _num(daily_rain[index] if index < len(daily_rain) else None) or 0.0
            record = {
                "date": date_value,
                "weather_code": code_value,
                "condition": day_condition,
                "icon": day_icon,
                "temp_max": _round(daily_max[index] if index < len(daily_max) else None),
                "temp_min": _round(daily_min[index] if index < len(daily_min) else None),
                "precipitation_mm": round(precip_mm, 1),
                "rain_mm": round(rain_mm, 1),
                "precipitation_hours": _round(
                    daily_hours[index] if index < len(daily_hours) else None, 0
                ),
                "precipitation_probability": _round(
                    daily_prob[index] if index < len(daily_prob) else None, 0
                ),
                "wind_max": _round(daily_wind[index] if index < len(daily_wind) else None),
                "gusts_max": _round(daily_gusts[index] if index < len(daily_gusts) else None),
                "uv_max": _round(daily_uv[index] if index < len(daily_uv) else None),
                "sunrise": daily_sunrise[index] if index < len(daily_sunrise) else None,
                "sunset": daily_sunset[index] if index < len(daily_sunset) else None,
                "humidity_avg": _mean(humidity_by_date.get(date_value, [])),
                "aqi_max": (
                    round(max(aqi_by_date[date_value]))
                    if aqi_by_date.get(date_value)
                    else None
                ),
                "rained": precip_mm > 0 or rain_mm > 0,
                "forecast": date_value > today,
            }
            records.append(record)

        past_records = [record for record in records if record["date"] <= today]
        forecast_records = [record for record in records if record["date"] > today]
        today_record = next((record for record in records if record["date"] == today), {})
        self._merge_history(past_records)
        history = sorted(self._history.values(), key=lambda item: item.get("date", ""))
        history = [item for item in history if item.get("date", "") <= today]

        today_hourly = [entry for entry in past if str(entry.get("at", ""))[:10] == today]
        today_mm = round(
            sum(float(entry.get("precipitation", 0) or 0) for entry in today_hourly), 1
        )
        today_hours = sum(
            1 for entry in today_hourly if float(entry.get("precipitation", 0) or 0) > 0
        )

        last_rain = next(
            (
                record
                for record in reversed(history)
                if str(record.get("date", "")) < today
                and float(record.get("precipitation_mm", 0) or 0) > 0
            ),
            None,
        )
        if today_mm > 0:
            last_rain = {"date": today, "precipitation_mm": today_mm}
        last_rain_date = str(last_rain.get("date")) if last_rain else None
        days_since_rain = None
        if last_rain_date:
            try:
                days_since_rain = (
                    now_local.date() - datetime.fromisoformat(last_rain_date).date()
                ).days
            except ValueError:
                days_since_rain = None
        month_prefix = today[:7]
        month_records = [
            record
            for record in history
            if str(record.get("date", ""))[:7] == month_prefix
            and str(record.get("date", "")) < today
        ]
        month_rain = round(
            sum(float(record.get("precipitation_mm", 0) or 0) for record in month_records)
            + today_mm,
            1,
        )
        month_rain_days = sum(
            1 for record in month_records if float(record.get("precipitation_mm", 0) or 0) > 0
        ) + (1 if today_mm > 0 else 0)
        last_24h_rain = round(
            sum(float(entry.get("precipitation", 0) or 0) for entry in past), 1
        )
        rain: dict[str, Any] = {
            "today_mm": today_mm,
            "today_hours": today_hours,
            "rained_today": today_mm > 0,
            "last_rain_date": last_rain_date,
            "last_rain_mm": last_rain.get("precipitation_mm") if last_rain else None,
            "days_since_rain": days_since_rain,
            "month_mm": month_rain,
            "month_days": month_rain_days,
            "last_24h_mm": last_24h_rain,
        }

        current_air = air.get("current") or {}
        aqi = _round(current_air.get("us_aqi"), 0)
        category, category_key = aqi_category(aqi)
        air_hourly = [
            {
                "at": time_value,
                "us_aqi": _round(
                    air_aqi[index] if index < len(air_aqi) else None, 0
                ),
                "pm2_5": _round(air_pm25[index] if index < len(air_pm25) else None),
                "pm10": _round(air_pm10[index] if index < len(air_pm10) else None),
            }
            for index, time_value in enumerate(air_times)
            if now_local <= datetime.fromisoformat(time_value) <= now_local + timedelta(hours=24)
        ]
        air_data: dict[str, Any] = {
            "at": current_air.get("time"),
            "us_aqi": aqi,
            "european_aqi": _round(current_air.get("european_aqi"), 0),
            "pm2_5": _round(current_air.get("pm2_5")),
            "pm10": _round(current_air.get("pm10")),
            "ozone": _round(current_air.get("ozone")),
            "no2": _round(current_air.get("nitrogen_dioxide")),
            "so2": _round(current_air.get("sulphur_dioxide")),
            "co": _round(current_air.get("carbon_monoxide")),
            "category": category,
            "category_key": category_key,
            "hourly": air_hourly,
        }

        alerts: list[str] = []
        status = "ok"

        def alert(level: str, message: str) -> None:
            nonlocal status
            if level == "critical" or (level == "warn" and status == "ok"):
                status = level
            alerts.append(message)

        temperature = current.get("temperature")
        if temperature is not None:
            if temperature >= 42:
                alert("critical", f"Calor extremo: {temperature:.1f} °C")
            elif temperature >= 38:
                alert("warn", f"Calor alto: {temperature:.1f} °C")
            elif temperature <= -2:
                alert("critical", f"Frío extremo: {temperature:.1f} °C")
            elif temperature <= 2:
                alert("warn", f"Frío: {temperature:.1f} °C")
        if aqi is not None:
            if aqi >= 200:
                alert("critical", f"Calidad del aire muy mala (AQI {aqi:.0f})")
            elif aqi >= 100:
                alert("warn", f"Calidad del aire moderada/mala (AQI {aqi:.0f})")
        if rain["today_mm"] >= 50:
            alert("critical", f"Lluvia intensa hoy: {rain['today_mm']:.1f} mm")
        elif rain["today_mm"] >= 20:
            alert("warn", f"Lluvia considerable hoy: {rain['today_mm']:.1f} mm")
        uv = current.get("uv_index")
        if uv is not None:
            if uv >= 11:
                alert("critical", f"UV extremo: {uv:.1f}")
            elif uv >= 8:
                alert("warn", f"UV alto: {uv:.1f}")
        wind = current.get("wind_speed")
        if wind is not None:
            if wind >= 90:
                alert("critical", f"Viento muy fuerte: {wind:.0f} km/h")
            elif wind >= 60:
                alert("warn", f"Viento fuerte: {wind:.0f} km/h")

        humidity_text = f"{current['humidity']:.0f}%" if current.get("humidity") is not None else "—"
        aqi_text = f"{aqi:.0f}" if aqi is not None else "—"
        summary_detail = f"{condition} · Humedad {humidity_text} · AQI {aqi_text}"
        if rain["rained_today"]:
            summary_detail += f" · Lluvia {rain['today_mm']:.1f} mm"
        summary = {
            "label": "Temperatura",
            "value": current.get("temperature") if current.get("temperature") is not None else "—",
            "unit": "°C",
            "detail": summary_detail,
        }
        history_payload = history[-self.settings.weather_payload_history_days :]
        detail = {
            "location": self._state["location"],
            "current": current,
            "today": today_record,
            "forecast": forecast_records,
            "history": history_payload,
            "hourly": upcoming,
            "hourly_past": past,
            "air": air_data,
            "rain": rain,
            "alerts": alerts,
            "updated_at": datetime.now(UTC).isoformat(),
            "history_days": self.settings.weather_history_days,
            "error": None,
        }
        with self._lock:
            self._state.update(
                {
                    "current": current,
                    "today": today_record,
                    "forecast": forecast_records,
                    "history": history_payload,
                    "hourly": upcoming,
                    "hourly_past": past,
                    "air": air_data,
                    "rain": rain,
                    "alerts": alerts,
                    "status": status,
                    "summary": summary,
                    "updated_at": detail["updated_at"],
                    "error": None,
                }
            )

    # --- histórico persistente ------------------------------------------
    def _load_history(self) -> dict[str, dict[str, Any]]:
        path = Path(self.settings.weather_history_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        days = payload.get("days") if isinstance(payload, dict) else None
        if not isinstance(days, dict):
            return {}
        return {
            str(date): record
            for date, record in days.items()
            if isinstance(record, dict) and record.get("date")
        }

    def _merge_history(self, records: list[dict[str, Any]]) -> None:
        for record in records:
            date_value = str(record.get("date", ""))
            if date_value:
                self._history[date_value] = record
        cutoff = (
            datetime.now(self._tz).date()
            - timedelta(days=self.settings.weather_history_days)
        ).isoformat()
        self._history = {
            date: record for date, record in self._history.items() if date >= cutoff
        }
        self._save_history()

    def _save_history(self) -> None:
        path = Path(self.settings.weather_history_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    {"version": 1, "days": self._history},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError:
            logger.warning("no se puede guardar el histórico del clima en %s", path)

    # --- API -------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def payload(self) -> dict[str, Any]:
        snap = self.snapshot()
        if not snap["enabled"]:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Temperatura",
                    "value": "—",
                    "unit": "°C",
                    "detail": "Monitor deshabilitado",
                },
                "detail": snap,
            }
        if snap["error"] and not snap["current"]:
            return {
                "status": "critical",
                "summary": {
                    "label": "Temperatura",
                    "value": "—",
                    "unit": "°C",
                    "detail": snap["error"],
                },
                "detail": snap,
            }
        status = "warn" if snap["error"] else snap["status"]
        detail = dict(snap)
        detail["error"] = snap["error"]
        return {
            "status": status,
            "summary": snap["summary"],
            "detail": detail,
        }
