"""Arranque y rutas del agente (solo lectura, token interno)."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import get_settings
from app.docker_monitor import (
    DockerLogsError,
    DockerMonitor,
    DockerNotFoundError,
    format_uptime,
    human_bytes,
)
from app.internet import InternetMonitor
from app.metrics import HostMetrics
from app.network import NetworkMonitor
from app.weather import WeatherMonitor


@lru_cache
def get_metrics() -> HostMetrics:
    return HostMetrics(get_settings())


@lru_cache
def get_internet_monitor() -> InternetMonitor:
    return InternetMonitor(get_settings())


@lru_cache
def get_network_monitor() -> NetworkMonitor:
    return NetworkMonitor(get_settings())


@lru_cache
def get_docker_monitor() -> DockerMonitor:
    return DockerMonitor(get_settings())


@lru_cache
def get_weather_monitor() -> WeatherMonitor:
    return WeatherMonitor(get_settings())


def opencode_payload() -> dict[str, object]:
    settings = get_settings()
    if not settings.opencode_enabled:
        return {
            "status": "unknown",
            "summary": {
                "label": "OpenCode",
                "value": "—",
                "detail": "Módulo deshabilitado",
            },
            "detail": {"error": "deshabilitado"},
        }
    try:
        container = get_docker_monitor().container_detail(settings.opencode_container)
    except DockerNotFoundError:
        return {
            "status": "critical",
            "summary": {
                "label": "OpenCode",
                "value": "—",
                "detail": "Contenedor no encontrado",
            },
            "detail": {"error": "contenedor no encontrado"},
        }
    except DockerLogsError:
        return {
            "status": "critical",
            "summary": {
                "label": "OpenCode",
                "value": "—",
                "detail": "Docker no disponible",
            },
            "detail": {"error": "docker no disponible"},
        }

    state = str(container.get("state") or "unknown")
    health = container.get("health")
    state_ok = state == "running" and health != "unhealthy"
    cpu = float(container.get("cpu_percent", 0) or 0)
    memory = int(container.get("memory_used", 0) or 0)
    uptime = int(container.get("uptime_seconds", 0) or 0)
    return {
        "status": "ok" if state_ok else "warn",
        "summary": {
            "label": "OpenCode",
            "value": state,
            "detail": (
                f"CPU {cpu:.1f}% · RAM {human_bytes(memory)} · up {format_uptime(uptime)}"
            ),
        },
        "detail": {"container": container, "error": None},
    }


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    internet = get_internet_monitor()
    network = get_network_monitor()
    docker_monitor = get_docker_monitor()
    weather = get_weather_monitor()
    internet.start()
    network.start()
    docker_monitor.start()
    weather.start()
    yield
    weather.stop()
    docker_monitor.stop()
    network.stop()
    internet.stop()


def require_agent_token(
    x_agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> None:
    expected = get_settings().agent_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGENT_TOKEN no configurado",
        )
    if not x_agent_token or not secrets.compare_digest(x_agent_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token de agente inválido",
        )


app = FastAPI(title="HomeLabDash Agent", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/summary", dependencies=[Depends(require_agent_token)])
def summary(metrics: HostMetrics = Depends(get_metrics)) -> dict[str, object]:
    payload = metrics.summary()
    modules = payload.setdefault("modules", {})
    if isinstance(modules, dict):
        modules["internet"] = get_internet_monitor().payload()
        modules["devices"] = get_network_monitor().payload()
        modules["docker"] = get_docker_monitor().payload()
        modules["weather"] = get_weather_monitor().payload()
        modules["opencode"] = opencode_payload()
    return payload


@app.get("/v1/docker/containers/{container_id}/logs", dependencies=[Depends(require_agent_token)])
def docker_logs(container_id: str, tail: int = 100) -> dict[str, object]:
    tail = max(1, min(500, tail))
    try:
        return get_docker_monitor().logs(container_id, tail)
    except DockerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="contenedor no encontrado"
        ) from None
    except DockerLogsError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="docker no disponible"
        ) from None


@app.get("/v1/modules/{module_id}", dependencies=[Depends(require_agent_token)])
def module(module_id: str, metrics: HostMetrics = Depends(get_metrics)) -> dict[str, object]:
    if module_id == "internet":
        return {
            "id": "internet",
            "generated_at": datetime.now(UTC).isoformat(),
            **get_internet_monitor().payload(),
        }
    if module_id == "devices":
        return {
            "id": "devices",
            "generated_at": datetime.now(UTC).isoformat(),
            **get_network_monitor().payload(),
        }
    if module_id == "docker":
        return {
            "id": "docker",
            "generated_at": datetime.now(UTC).isoformat(),
            **get_docker_monitor().payload(),
        }
    if module_id == "weather":
        return {
            "id": "weather",
            "generated_at": datetime.now(UTC).isoformat(),
            **get_weather_monitor().payload(),
        }
    if module_id == "opencode":
        return {
            "id": "opencode",
            "generated_at": datetime.now(UTC).isoformat(),
            **opencode_payload(),
        }
    try:
        return metrics.module(module_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="módulo no encontrado"
        ) from None
