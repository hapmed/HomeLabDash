"""Esquemas de salud."""

from typing import Literal

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: bool
    agent: bool
