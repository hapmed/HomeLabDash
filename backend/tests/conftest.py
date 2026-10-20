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
        "SNAPSHOT_MONITOR_ENABLED": "false",
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
                "internet": {
                    "status": "ok",
                    "summary": {
                        "label": "Bajada",
                        "value": 512.3,
                        "unit": "Mbps",
                        "detail": "Subida 300.1 Mbps · 12.4 ms · IP 203.0.113.7",
                    },
                    "detail": {
                        "online": True,
                        "public_ip": "203.0.113.7",
                        "history": [
                            {
                                "at": "2026-10-19T12:00:00+00:00",
                                "download_mbps": 512.3,
                                "upload_mbps": 300.1,
                                "latency_ms": 12.4,
                            }
                        ],
                    },
                },
                "devices": {
                    "status": "ok",
                    "summary": {
                        "label": "En línea",
                        "value": 7,
                        "detail": "8 conocidos · Red local 192.168.0.0/24",
                    },                    "detail": {
                        "network_name": "Red local 192.168.0.0/24",
                        "cidr": "192.168.0.0/24",
                        "gateway": "192.168.0.1",
                        "counts": {"online": 7, "total": 8},
                        "devices": [
                            {
                                "mac": "46:c3:7b:e1:a6:16",
                                "ip": "192.168.0.10",
                                "name": "Apple",
                                "vendor": "Apple",
                                "online": True,
                                "online_seconds": 3600,
                                "first_seen": "2026-10-19T09:00:00+00:00",
                                "last_seen": "2026-10-19T12:00:00+00:00",
                                "connection": "5 GHz",
                                "rate_up_bps": 440,
                                "rate_down_bps": 343,
                                "bytes": 104857600,
                            }
                        ],
                        "top_consumer": {
                            "name": "Apple",
                            "mac": "46:c3:7b:e1:a6:16",
                            "ip": "192.168.0.10",
                            "bytes": 104857600,
                        },
                        "consumption_available": True,
                        "consumption_note": "Consumo estimado por muestreo.",
                    },
                },
                "docker": {
                    "status": "ok",
                    "summary": {
                        "label": "Contenedores",
                        "value": "7/14",
                        "detail": "0 con problemas · CPU 2.1% · RAM 1.2 GB",
                    },
                    "detail": {
                        "containers": [
                            {
                                "id": "abc123",
                                "name": "postgres",
                                "image": "postgres:17-alpine",
                                "state": "running",
                                "health": "healthy",
                                "cpu_percent": 0.3,
                                "memory_used": 104857600,
                                "memory_limit": 2147483648,
                                "memory_percent": 4.9,
                                "net_rx": 1000,
                                "net_tx": 2000,
                                "restart_count": 0,
                                "uptime_seconds": 3600,
                            }
                        ],
                        "system": {"containers": {"running": 7, "total": 14}},
                        "totals": {"cpu_percent": 2.1, "memory_used": 1288490188},
                        "top_cpu": {"name": "postgres", "cpu_percent": 0.3},
                        "top_memory": {"name": "postgres", "memory_used": 104857600},
                        "sampled_at": "2026-10-19T12:00:00+00:00",
                        "error": None,
                    },
                },
                "weather": {
                    "status": "ok",
                    "summary": {
                        "label": "Temperatura",
                        "value": 24.5,
                        "unit": "°C",
                        "detail": "Parcialmente nublado · Humedad 60% · AQI 42",
                    },
                    "detail": {
                        "current": {"temperature": 24.5, "humidity": 60},
                        "rain": {"rained_today": False, "today_mm": 0},
                        "air": {"us_aqi": 42, "category": "Buena"},
                        "alerts": [],
                    },
                },
                "opencode": {
                    "status": "ok",
                    "summary": {
                        "label": "OpenCode",
                        "value": "running",
                        "detail": "CPU 2.0% · RAM 1.3 GB · up 4d",
                    },
                    "detail": {
                        "container": {
                            "name": "opencode",
                            "state": "running",
                            "cpu_percent": 2.0,
                            "memory_used": 1312976896,
                            "uptime_seconds": 345600,
                        },
                        "error": None,
                    },
                },
                "network": {
                    "status": "ok",
                    "summary": {
                        "label": "Bajada",
                        "value": 12.5,
                        "unit": "Mbps",
                        "detail": "Subida 2.1 Mbps · 2 interfaces",
                    },
                    "detail": {
                        "interfaces": [
                            {
                                "name": "enp0s31f6",
                                "type": "ethernet",
                                "state": "up",
                                "up": True,
                                "speed_mbps": 1000,
                                "mac": "aa:bb:cc:dd:ee:ff",
                                "rx_bps": 12_500_000,
                                "tx_bps": 2_100_000,
                                "rx_bytes": 123456,
                                "tx_bytes": 654321,
                            }
                        ],
                        "total_rx_bps": 12_500_000,
                        "total_tx_bps": 2_100_000,
                        "total_rx_errors": 0,
                        "total_tx_errors": 0,
                        "interface_count": 1,
                    },
                },
                "temperature": {
                    "status": "ok",
                    "summary": {
                        "label": "Máxima",
                        "value": 48.0,
                        "unit": "°C",
                        "detail": "4 sensores",
                    },
                    "detail": {
                        "sensors": [
                            {
                                "id": "hwmon0:temp1",
                                "chip": "coretemp",
                                "label": "Package id 0",
                                "temp_c": 48.0,
                                "max_c": 80.0,
                                "crit_c": 100.0,
                                "source": "hwmon",
                            }
                        ],
                        "fans": [],
                        "max_c": 48.0,
                        "sensor_count": 1,
                        "fan_count": 0,
                        "warn_c": 75.0,
                        "critical_c": 85.0,
                    },
                },
                "hardware": {
                    "status": "ok",
                    "summary": {
                        "label": "Batería",
                        "value": 100,
                        "unit": "%",
                        "detail": "Full · 12.2 V · 0 ciclos",
                    },
                    "detail": {
                        "host": {"vendor": "Dell Inc.", "model": "Latitude 5490"},
                        "disks": [
                            {
                                "name": "nvme0n1",
                                "model": "PC SN520 NVMe WDC 256GB",
                                "serial": "123",
                                "size_bytes": 256060514304,
                                "rotational": False,
                                "mountpoints": [],
                                "smart": {"available": False, "status": "unknown"},
                            }
                        ],
                        "disk_count": 1,
                        "battery": {"percent": 100, "status": "Full", "voltage_v": 12.2},
                        "ac": {"online": True},
                        "ups": {"detected": False, "devices": []},
                        "root_inodes_percent": 4.0,
                        "updates": {"reboot_required": False, "available": None},
                    },
                },
            },
        }

    def module(self, module_id: str) -> dict[str, Any]:
        summary = self.summary()["modules"]
        payload = summary.get(module_id)
        if payload is None:
            raise AgentUnavailable("módulo inexistente")
        return {"generated_at": "2026-10-19T12:00:00+00:00", **payload}

    def container_logs(self, container_id: str, tail: int = 100) -> dict[str, Any]:
        return {
            "container": container_id,
            "id": "abc123",
            "lines": ["2026-10-19T12:00:00Z linea 1", "2026-10-19T12:00:01Z linea 2"],
            "tail": tail,
        }

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
