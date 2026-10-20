"""Contrato de módulos (widget del dashboard y detalle)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ModuleStatus = Literal["ok", "warn", "critical", "unknown"]


class ModuleSummary(BaseModel):
    label: str
    value: str | float | int
    unit: str | None = None
    detail: str | None = None


class ModuleCard(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    order: int
    enabled: bool
    status: ModuleStatus = "unknown"
    summary: ModuleSummary = Field(
        default_factory=lambda: ModuleSummary(label="Sin datos", value="—", detail="El agente no responde")
    )
    updated_at: datetime | None = None


class ModuleDetail(ModuleCard):
    available: bool = True
    detail: dict[str, Any] | None = None
    error: str | None = None
