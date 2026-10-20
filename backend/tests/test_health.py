from fastapi.testclient import TestClient

from tests.conftest import FakeAgent


def test_liveness(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_with_agent(client: TestClient, fake_agent: FakeAgent) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["agent"] is True


def test_health_degraded_without_agent(client: TestClient, down_agent: None) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["agent"] is False
