"""Salud del backend: liveness y estado de dependencias."""

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine
from app.schemas.health import HealthOut
from app.services.agent import AgentClient, get_agent_client

router = APIRouter()


@router.get("/healthz")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/health", response_model=HealthOut)
def health(agent: AgentClient = Depends(get_agent_client)) -> HealthOut:
    database_ok = True
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - el healthcheck no debe romper por la BD
        database_ok = False

    agent_ok = agent.healthy()
    return HealthOut(
        status="ok" if database_ok and agent_ok else "degraded",
        version=get_settings().version,
        database=database_ok,
        agent=agent_ok,
    )
