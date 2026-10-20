"""Tests del módulo de clima (sin red)."""

from app.config import Settings
from app.weather import WeatherMonitor, aqi_category, condition_for_code


def test_condiciones_wmo() -> None:
    assert condition_for_code(0)[0] == "Despejado"
    assert condition_for_code(61)[1] == "cloud-rain"
    assert condition_for_code(95)[1] == "cloud-lightning"
    assert condition_for_code(None)[0] == "Despejado"


def test_categorias_aqi() -> None:
    assert aqi_category(20)[0] == "Buena"
    assert aqi_category(75)[0] == "Moderada"
    assert aqi_category(175)[1] == "unhealthy"
    assert aqi_category(400)[1] == "hazardous"
    assert aqi_category(None)[0] == "Sin datos"


def test_payload_deshabilitado() -> None:
    payload = WeatherMonitor(Settings(weather_enabled=False)).payload()
    assert payload["status"] == "unknown"
    assert payload["detail"]["enabled"] is False


def test_payload_sin_datos() -> None:
    payload = WeatherMonitor(Settings(weather_enabled=True)).payload()
    # Aún no se ha ejecutado el primer fetch: estado desconocido, no error.
    assert payload["status"] == "unknown"
    assert payload["summary"]["value"] == "—"
