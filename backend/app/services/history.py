"""Histórico genérico de módulos a partir de `module_snapshots`."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.snapshot import ModuleSnapshot


def _downsample(
    rows: list[ModuleSnapshot], max_points: int
) -> list[ModuleSnapshot]:
    if len(rows) <= max_points:
        return rows
    step = len(rows) / max_points
    selected = [rows[min(len(rows) - 1, int(index * step))] for index in range(max_points)]
    if selected[-1] is not rows[-1]:
        selected[-1] = rows[-1]
    return selected


def get_history(
    db: Session,
    module_id: str,
    hours: int = 24,
    max_points: int = 600,
) -> list[dict[str, Any]]:
    """Devuelve muestras compactas `{at, metrics}` para un módulo."""
    hours = max(1, min(24 * 30, hours))
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    try:
        rows = list(
            db.scalars(
                select(ModuleSnapshot)
                .where(
                    ModuleSnapshot.module_id == module_id,
                    ModuleSnapshot.captured_at >= cutoff,
                )
                .order_by(ModuleSnapshot.captured_at.asc())
                .limit(20000)
            ).all()
        )
    except Exception:  # noqa: BLE001 - el histórico no debe romper el detalle
        return []

    history: list[dict[str, Any]] = []
    for row in _downsample(rows, max(10, min(2000, max_points))):
        payload = row.payload if isinstance(row.payload, dict) else {}
        raw_metrics = payload.get("metrics")
        if isinstance(raw_metrics, dict):
            metrics = raw_metrics
        else:
            # Compatibilidad con los snapshots antiguos de la base de datos.
            metrics = {
                key: value
                for key, value in payload.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            }
        history.append(
            {
                "at": row.captured_at.isoformat() if row.captured_at else None,
                "status": row.status,
                "metrics": metrics,
            }
        )
    return history
