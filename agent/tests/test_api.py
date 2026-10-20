"""Tests de las rutas del agente."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"X-Agent-Token": "test-agent-token"}


def test_healthz_es_publico() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_summary_requiere_token() -> None:
    assert client.get("/v1/summary").status_code == 401
    assert client.get("/v1/summary", headers={"X-Agent-Token": "malo"}).status_code == 401


def test_summary_devuelve_metricas_del_host() -> None:
    response = client.get("/v1/summary", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert set(body["modules"]) == {
        "overview",
        "cpu",
        "memory",
        "storage",
        "internet",
        "devices",
        "docker",
        "weather",
        "opencode",
        "network",
        "temperature",
        "hardware",
    }
    assert body["modules"]["cpu"]["summary"]["unit"] == "%"
    assert body["modules"]["overview"]["detail"]["hostname"]
    assert body["modules"]["overview"]["detail"]["load"]["1m"] >= 0
    # En tests los monitores están deshabilitados; el contrato sigue presente.
    assert body["modules"]["internet"]["status"] == "unknown"
    assert body["modules"]["devices"]["status"] == "unknown"
    assert body["modules"]["docker"]["status"] == "unknown"
    assert body["modules"]["weather"]["status"] == "unknown"
    assert body["modules"]["opencode"]["status"] == "unknown"
    assert body["modules"]["network"]["status"] == "unknown"
    assert body["modules"]["temperature"]["status"] == "unknown"
    assert body["modules"]["hardware"]["status"] == "unknown"


def test_detalle_de_modulo() -> None:
    response = client.get("/v1/modules/cpu", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "cpu"
    assert body["detail"]["cores"]


def test_detalle_de_internet() -> None:
    response = client.get("/v1/modules/internet", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "internet"
    assert body["detail"]["enabled"] is False


def test_detalle_de_dispositivos() -> None:
    response = client.get("/v1/modules/devices", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "devices"
    assert body["detail"]["enabled"] is False


def test_detalle_de_docker() -> None:
    response = client.get("/v1/modules/docker", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "docker"
    assert body["detail"]["enabled"] is False


def test_detalle_de_weather() -> None:
    response = client.get("/v1/modules/weather", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "weather"
    assert body["detail"]["enabled"] is False


def test_detalle_de_opencode() -> None:
    response = client.get("/v1/modules/opencode", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "opencode"
    assert body["detail"]["error"] == "deshabilitado"


def test_detalle_de_red() -> None:
    response = client.get("/v1/modules/network", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "network"
    assert body["detail"]["enabled"] is False


def test_detalle_de_temperatura() -> None:
    response = client.get("/v1/modules/temperature", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "temperature"
    assert body["detail"]["enabled"] is False


def test_detalle_de_hardware() -> None:
    response = client.get("/v1/modules/hardware", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "hardware"
    assert body["detail"]["enabled"] is False


def test_modulo_desconocido() -> None:
    assert client.get("/v1/modules/inventado", headers=AUTH).status_code == 404
