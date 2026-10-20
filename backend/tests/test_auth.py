from fastapi.testclient import TestClient


def test_login_rejects_bad_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "incorrecta"},
    )
    assert response.status_code == 401


def test_login_rejects_unknown_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nadie", "password": "x"},
    )
    assert response.status_code == 401


def test_login_and_me(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test-admin-password"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["user"]["username"] == "admin"
    assert body["user"]["is_admin"] is True
    assert body["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_me_accepts_session_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test-admin-password"},
    )
    token = response.json()["access_token"]
    client.cookies.set("hld_session", token)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert response.status_code == 401
