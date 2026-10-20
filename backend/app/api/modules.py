"""Módulos: widgets del dashboard y detalle."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.module import ModuleCard, ModuleDetail
from app.services.agent import AgentClient, AgentUnavailable, get_agent_client
from app.services.module_cards import build_cards, build_detail, module_meta

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ModuleCard])
def list_modules(
    agent: AgentClient = Depends(get_agent_client),
    _user: User = Depends(get_current_user),
) -> list[ModuleCard]:
    try:
        summary = agent.summary()
    except AgentUnavailable:
        summary = None
    return build_cards(summary)


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
    _user: User = Depends(get_current_user),
) -> ModuleDetail:
    meta = module_meta(module_id)
    if meta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="módulo no encontrado")

    payload = None
    try:
        payload = agent.module(module_id)
    except AgentUnavailable:
        payload = None
    return build_detail(meta, payload)
