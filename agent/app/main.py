"""Arranque y rutas del agente (solo lectura, token interno)."""

import secrets
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any

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
from app.opencode_app import OpenCodeClient, OpenCodeError
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


@lru_cache
def get_opencode_client() -> OpenCodeClient:
    settings = get_settings()
    return OpenCodeClient(
        base_url=settings.opencode_api_url,
        username=settings.opencode_api_username,
        password=settings.opencode_api_password,
        timezone=settings.weather_timezone,
        session_limit=settings.opencode_session_limit,
    )


_opencode_lock = threading.Lock()
_opencode_cache: dict[str, Any] | None = None
_opencode_cache_at = 0.0
_opencode_error: str | None = None


def _opencode_app() -> tuple[dict[str, Any] | None, str | None]:
    global _opencode_cache, _opencode_cache_at, _opencode_error

    settings = get_settings()
    if not settings.opencode_api_password:
        return None, None

    with _opencode_lock:
        if (
            _opencode_cache is not None
            and time.monotonic() - _opencode_cache_at < settings.opencode_app_poll_seconds
        ):
            return _opencode_cache, _opencode_error

    try:
        data = get_opencode_client().fetch_app()
    except OpenCodeError as exc:
        with _opencode_lock:
            _opencode_error = str(exc)
            return _opencode_cache, _opencode_error

    with _opencode_lock:
        _opencode_cache = data
        _opencode_cache_at = time.monotonic()
        _opencode_error = None
    return data, None


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

    app_data, app_error = _opencode_app()

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
            "detail": {
                "error": "contenedor no encontrado",
                "app": app_data,
                "app_error": app_error,
            },
        }
    except DockerLogsError:
        return {
            "status": "critical",
            "summary": {
                "label": "OpenCode",
                "value": "—",
                "detail": "Docker no disponible",
            },
            "detail": {"error": "docker no disponible", "app": app_data, "app_error": app_error},
        }

    state = str(container.get("state") or "unknown")
    health = container.get("health")
    state_ok = state == "running" and health != "unhealthy"
    cpu = float(container.get("cpu_percent", 0) or 0)
    memory = int(container.get("memory_used", 0) or 0)
    uptime = int(container.get("uptime_seconds", 0) or 0)

    detail_parts = [
        f"CPU {cpu:.1f}%",
        f"RAM {human_bytes(memory)}",
        f"up {format_uptime(uptime)}",
    ]
    stats = (app_data or {}).get("stats") or {}
    if isinstance(stats, dict):
        sessions = stats.get("sessions")
        cost = stats.get("cost")
        if sessions:
            detail_parts.append(f"{sessions} sesiones")
        if cost:
            detail_parts.append(f"${float(cost):.2f}")

    status_value = "ok"
    if not state_ok:
        status_value = "warn"
    elif app_error:
        status_value = "warn"

    return {
        "status": status_value,
        "summary": {
            "label": "OpenCode",
            "value": state,
            "detail": " · ".join(detail_parts),
        },
        "detail": {
            "container": container,
            "app": app_data,
            "app_error": app_error,
            "error": None if state_ok else f"contenedor en estado {state}",
        },
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
