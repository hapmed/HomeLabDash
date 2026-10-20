"""Esquemas de alertas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: str
    severity: str
    title: str
    message: str
    status: str
    started_at: datetime
    resolved_at: datetime | None = None
    acknowledged_at: datetime | None = None
