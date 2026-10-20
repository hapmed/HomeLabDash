from fastapi.testclient import TestClient

from tests.conftest import login_headers


def test_alerts_empty(client: TestClient) -> None:
    headers = login_headers(client)
    response = client.get("/api/v1/alerts", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_alerts_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/alerts").status_code == 401
