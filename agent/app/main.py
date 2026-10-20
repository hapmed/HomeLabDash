"""Arranque y rutas del agente (solo lectura, token interno)."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import get_settings
from app.internet import InternetMonitor
from app.metrics import HostMetrics
from app.network import NetworkMonitor


@lru_cache
def get_metrics() -> HostMetrics:
    return HostMetrics(get_settings())


@lru_cache
def get_internet_monitor() -> InternetMonitor:
    return InternetMonitor(get_settings())


@lru_cache
def get_network_monitor() -> NetworkMonitor:
    return NetworkMonitor(get_settings())


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    internet = get_internet_monitor()
    network = get_network_monitor()
    internet.start()
    network.start()
    yield
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
    return payload


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
    try:
        return metrics.module(module_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="módulo no encontrado"
        ) from None
