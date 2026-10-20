from fastapi.testclient import TestClient

from tests.conftest import FakeAgent, login_headers


def test_modules_require_auth(client: TestClient, fake_agent: FakeAgent) -> None:
    assert client.get("/api/v1/modules").status_code == 401


def test_modules_returns_phase_one_cards(client: TestClient, fake_agent: FakeAgent) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert [card["id"] for card in cards] == ["overview", "cpu", "memory", "storage"]
    assert all(card["enabled"] for card in cards)
    cpu = next(card for card in cards if card["id"] == "cpu")
    assert cpu["status"] == "warn"
    assert cpu["summary"]["value"] == 77.0
    assert cpu["icon"] == "cpu"
    assert cpu["updated_at"].startswith("2026-10-19T12:00:00")


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
    assert client.get("/api/v1/modules/docker", headers=headers).status_code == 404


def test_modules_degrade_when_agent_is_down(client: TestClient, down_agent: None) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/modules", headers=headers)
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 4
    assert {card["status"] for card in cards} == {"unknown"}
    assert all(card["summary"]["value"] == "—" for card in cards)

    detail = client.get("/api/v1/modules/cpu", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["available"] is False
    assert detail.json()["status"] == "unknown"
