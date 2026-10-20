"""Arranque y rutas del agente (solo lectura, token interno)."""

import secrets
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import get_settings
from app.metrics import HostMetrics


@lru_cache
def get_metrics() -> HostMetrics:
    return HostMetrics(get_settings())


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


app = FastAPI(title="HomeLabDash Agent", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/summary", dependencies=[Depends(require_agent_token)])
def summary(metrics: HostMetrics = Depends(get_metrics)) -> dict[str, object]:
    return metrics.summary()


@app.get("/v1/modules/{module_id}", dependencies=[Depends(require_agent_token)])
def module(module_id: str, metrics: HostMetrics = Depends(get_metrics)) -> dict[str, object]:
    try:
        return metrics.module(module_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="módulo no encontrado"
        ) from None
