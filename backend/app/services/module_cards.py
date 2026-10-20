"""Composición de tarjetas y detalles a partir del registro y del agente."""

from datetime import UTC, datetime
from typing import Any, cast

from app.schemas.module import ModuleCard, ModuleDetail, ModuleStatus, ModuleSummary
from app.services.modules import ModuleMeta, enabled_modules, get_module

UNKNOWN_SUMMARY = ModuleSummary(
    label="Sin datos", value="—", detail="El agente no responde"
)


def _parse_datetime(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _summary_from(payload: dict[str, Any] | None) -> ModuleSummary:
    if not payload:
        return UNKNOWN_SUMMARY
    raw = payload.get("summary")
    if not isinstance(raw, dict):
        return UNKNOWN_SUMMARY
    try:
        return ModuleSummary.model_validate(raw)
    except ValueError:
        return UNKNOWN_SUMMARY


def _card(
    meta: ModuleMeta,
    payload: dict[str, Any] | None,
    generated_at: Any = None,
) -> ModuleCard:
    status = payload.get("status") if payload else "unknown"
    if status not in {"ok", "warn", "critical", "unknown"}:
        status = "unknown"
    return ModuleCard(
        id=meta.id,
        name=meta.name,
        description=meta.description,
        icon=meta.icon,
        order=meta.order,
        enabled=meta.enabled,
        status=cast(ModuleStatus, status),
        summary=_summary_from(payload),
        updated_at=_parse_datetime(payload.get("generated_at")) if payload else None,
    )


def build_cards(summary_payload: dict[str, Any] | None) -> list[ModuleCard]:
    modules_payload: dict[str, Any] = {}
    if summary_payload and isinstance(summary_payload.get("modules"), dict):
        modules_payload = summary_payload["modules"]
    generated_at = summary_payload.get("generated_at") if summary_payload else None

    cards: list[ModuleCard] = []
    for meta in enabled_modules():
        payload = modules_payload.get(meta.id)
        card = _card(meta, payload if isinstance(payload, dict) else None)
        if card.updated_at is None:
            card.updated_at = _parse_datetime(generated_at)
        cards.append(card)
    return sorted(cards, key=lambda card: card.order)


def build_detail(meta: ModuleMeta, payload: dict[str, Any] | None) -> ModuleDetail:
    card = _card(meta, payload)
    detail = payload.get("detail") if payload else None
    return ModuleDetail(
        **card.model_dump(),
        available=payload is not None,
        detail=detail if isinstance(detail, dict) else None,
        error=None if payload is not None else "agente no disponible",
    )


def module_meta(module_id: str) -> ModuleMeta | None:
    meta = get_module(module_id)
    return meta if meta and meta.enabled else None


def now_utc() -> datetime:
    return datetime.now(UTC)
