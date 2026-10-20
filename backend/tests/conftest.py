"""Fixtures de tests del backend (SQLite temporal, agente simulado)."""

import os
import tempfile
from collections.abc import Iterator
from typing import Any

import pytest

_TMP = tempfile.mkdtemp(prefix="homelabdash-backend-")
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "DATABASE_URL": f"sqlite+pysqlite:///{_TMP}/test.db",
        "JWT_SECRET": "test-jwt-secret-not-real-0123456789abcdef",
        "JWT_TTL_MINUTES": "60",
        "COOKIE_NAME": "hld_session",
        "COOKIE_SECURE": "false",
        "ADMIN_USER": "admin",
        "ADMIN_PASSWORD": "test-admin-password",
        "AGENT_URL": "http://agent.invalid:8001",
        "AGENT_TOKEN": "test-agent-token",
        "RATE_LIMIT_ENABLED": "false",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.core import rate_limit  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.agent import AgentUnavailable, get_agent_client  # noqa: E402


class FakeAgent:
    healthy_value = True

    def summary(self) -> dict[str, Any]:
        return {
            "generated_at": "2026-10-19T12:00:00+00:00",
            "modules": {
                "overview": {
                    "status": "ok",
                    "summary": {"label": "Carga 1m", "value": 0.4, "detail": "CPU 12% · RAM 30%"},
                    "detail": {"hostname": "HomeLab"},
                },
                "cpu": {
                    "status": "warn",
                    "summary": {"label": "uso", "value": 77.0, "unit": "%", "detail": "8 núcleos"},
                    "detail": {"cores": [{"index": 0, "percent": 77.0}]},
                },
                "memory": {
                    "status": "ok",
                    "summary": {"label": "RAM usada", "value": 30.0, "unit": "%"},
                    "detail": {"total": 1, "used": 0},
                },
                "storage": {
                    "status": "ok",
                    "summary": {"label": "Disco raíz", "value": 40.0, "unit": "%"},
                    "detail": {"mounts": []},
                },
            },
        }

    def module(self, module_id: str) -> dict[str, Any]:
        summary = self.summary()["modules"]
        payload = summary.get(module_id)
        if payload is None:
            raise AgentUnavailable("módulo inexistente")
        return {"generated_at": "2026-10-19T12:00:00+00:00", **payload}

    def healthy(self) -> bool:
        return self.healthy_value


class DownAgent:
    def summary(self) -> dict[str, Any]:
        raise AgentUnavailable("caído")

    def module(self, module_id: str) -> dict[str, Any]:
        raise AgentUnavailable("caído")

    def healthy(self) -> bool:
        return False


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> Iterator[None]:
    rate_limit.reset()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def fake_agent() -> FakeAgent:
    agent = FakeAgent()
    app.dependency_overrides[get_agent_client] = lambda: agent
    return agent


@pytest.fixture
def down_agent() -> None:
    app.dependency_overrides[get_agent_client] = lambda: DownAgent()


@pytest.fixture
def client() -> Iterator[TestClient]:
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    with TestClient(app) as test_client:
        yield test_client


def login_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test-admin-password"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
