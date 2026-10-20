from fastapi.testclient import TestClient

from tests.conftest import FakeAgent, login_headers


def test_modules_require_auth(client: TestClient, fake_agent: FakeAgent) -> None:
    assert client.get("/api/v1/modules").status_code == 401


def test_modules_returns_phase_one_cards(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert [card["id"] for card in cards] == [
        "overview",
        "cpu",
        "memory",
        "storage",
        "internet",
        "devices",
        "docker",
        "database",
        "weather",
        "opencode",
    ]
    assert all(card["enabled"] for card in cards)
    cpu = next(card for card in cards if card["id"] == "cpu")
    assert cpu["status"] == "warn"
    assert cpu["summary"]["value"] == 77.0
    assert cpu["icon"] == "cpu"
    assert cpu["updated_at"].startswith("2026-10-19T12:00:00")

    internet = next(card for card in cards if card["id"] == "internet")
    assert internet["summary"]["value"] == 512.3
    assert internet["summary"]["unit"] == "Mbps"


def test_module_detail(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules/cpu", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["detail"]["cores"][0]["percent"] == 77.0


def test_module_detail_unknown(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    assert client.get("/api/v1/modules/inventado", headers=headers).status_code == 404
    # Módulo del catálogo pero aún deshabilitado (fase posterior).
    assert client.get("/api/v1/modules/network", headers=headers).status_code == 404


def test_internet_detail(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules/internet", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["detail"]["public_ip"] == "203.0.113.7"
    assert body["detail"]["history"][0]["download_mbps"] == 512.3


def test_devices_detail(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules/devices", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["detail"]["counts"]["online"] == 7
    assert body["detail"]["devices"][0]["name"] == "Apple"
    assert body["detail"]["consumption_available"] is True
    assert body["detail"]["top_consumer"]["name"] == "Apple"


def test_docker_detail(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules/docker", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["detail"]["system"]["containers"]["running"] == 7
    assert body["detail"]["containers"][0]["name"] == "postgres"


def test_docker_logs(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get(
        "/api/v1/modules/docker/containers/postgres/logs?tail=10", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["container"] == "postgres"
    assert body["tail"] == 10
    assert len(body["lines"]) == 2

    assert client.get("/api/v1/modules/docker/containers/postgres/logs").status_code == 401


def test_database_detail(client: TestClient, fake_agent: FakeAgent, monkeypatch) -> None:
    headers = login_headers(client)
    stats = {
        "status": "ok",
        "summary": {
            "label": "Tamaño",
            "value": "12 MB",
            "detail": "8 tablas · 2/100 conexiones · caché 99.5%",
        },
        "detail": {
            "database": {
                "name": "homelabdash",
                "size_bytes": 12582912,
                "size_pretty": "12 MB",
                "tables": 8,
                "indexes": 12,
                "server_version": "17.4",
                "version": "PostgreSQL 17.4",
                "uptime_seconds": 3600,
                "started_at": "2026-10-20T11:00:00+00:00",
            },
            "connections": {"current": 2, "max": 100, "percent": 2.0},
            "activity": {"cache_hit_ratio": 99.5, "dead_tuples": 0},
            "tables": [],
            "indexes": [],
            "settings": {},
            "alerts": [],
        },
        "sampled_at": "2026-10-20T12:00:00+00:00",
    }
    monkeypatch.setattr("app.api.modules.collect_database_stats", lambda db: stats)
    monkeypatch.setattr(
        "app.api.modules.get_database_history",
        lambda db: [{"at": "2026-10-20T12:00:00+00:00", "size_bytes": 12582912}],
    )

    response = client.get("/api/v1/modules/database", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["summary"]["value"] == "12 MB"
    assert body["detail"]["database"]["name"] == "homelabdash"
    assert body["detail"]["history"][0]["size_bytes"] == 12582912


def test_weather_detail(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules/weather", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["value"] == 24.5
    assert body["detail"]["air"]["category"] == "Buena"


def test_opencode_detail(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules/opencode", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["value"] == "running"
    assert body["detail"]["container"]["name"] == "opencode"


def test_modules_degrade_when_agent_is_down(client: TestClient, down_agent: None) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 10
    assert {card["status"] for card in cards} <= {"unknown", "critical"}
    assert all(card["summary"]["value"] == "—" for card in cards)

    detail = client.get("/api/v1/modules/cpu", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["available"] is False
    assert detail.json()["status"] == "unknown"
