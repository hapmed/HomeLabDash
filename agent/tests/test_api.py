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
    }
    assert body["modules"]["cpu"]["summary"]["unit"] == "%"
    assert body["modules"]["overview"]["detail"]["hostname"]
    assert body["modules"]["overview"]["detail"]["load"]["1m"] >= 0
    # En tests los monitores están deshabilitados; el contrato sigue presente.
    assert body["modules"]["internet"]["status"] == "unknown"
    assert body["modules"]["devices"]["status"] == "unknown"


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


def test_modulo_desconocido() -> None:
    assert client.get("/v1/modules/docker", headers=AUTH).status_code == 404
