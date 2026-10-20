"""Módulos: widgets del dashboard y detalle."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.module import ModuleCard, ModuleDetail
from app.services.agent import AgentClient, AgentUnavailable, get_agent_client
from app.services.database import (
    build_card as build_database_card,
)
from app.services.database import (
    build_detail as build_database_detail,
)
from app.services.database import (
    collect_stats as collect_database_stats,
)
from app.services.database import (
    get_history as get_database_history,
)
from app.services.database import (
    unavailable_stats as unavailable_database_stats,
)
from app.services.module_cards import build_cards, build_detail, module_meta
from app.services.modules import get_module

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ModuleCard])
def list_modules(
    agent: AgentClient = Depends(get_agent_client),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[ModuleCard]:
    try:
        summary = agent.summary()
    except AgentUnavailable:
        summary = None
    cards = build_cards(summary)
    meta = get_module("database")
    if meta is not None:
        try:
            stats = collect_database_stats(db)
        except Exception as exc:  # noqa: BLE001 - la BD no debe romper el dashboard
            stats = unavailable_database_stats(exc)
        database_card = build_database_card(meta, stats)
        cards = [database_card if card.id == "database" else card for card in cards]
        cards.sort(key=lambda card: card.order)
    return cards


@router.get("/docker/containers/{container_id}/logs")
def docker_container_logs(
    container_id: str,
    tail: int = 100,
    agent: AgentClient = Depends(get_agent_client),
    _user: User = Depends(get_current_user),
) -> dict[str, object]:
    tail = max(1, min(500, tail))
    try:
        return agent.container_logs(container_id, tail)
    except AgentUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no se pudieron leer los logs",
        ) from None


@router.get("/{module_id}", response_model=ModuleDetail)
def module_detail(
    module_id: str,
    agent: AgentClient = Depends(get_agent_client),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ModuleDetail:
    meta = module_meta(module_id)
    if meta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="módulo no encontrado")

    if module_id == "database":
        try:
            stats = collect_database_stats(db)
        except Exception as exc:  # noqa: BLE001 - se devuelve estado degradado
            stats = unavailable_database_stats(exc)
        history = get_database_history(db) if stats["status"] != "critical" else []
        return build_database_detail(meta, stats, history)

    payload = None
    try:
        payload = agent.module(module_id)
    except AgentUnavailable:
        payload = None
    return build_detail(meta, payload)
