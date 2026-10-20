"""Snapshots genéricos de los módulos para el histórico y las gráficas.

Cada cinco minutos se guarda una muestra compacta de cada módulo en
`module_snapshots`. El detalle de la base de datos se guarda con la misma
estructura (`payload.metrics`) para que las gráficas funcionen igual en todos
los módulos.
"""

import logging
import math
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.models.snapshot import ModuleSnapshot
from app.services.agent import AgentUnavailable, get_agent_client
from app.services.database import collect_stats

logger = logging.getLogger(__name__)


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        return value
    return None


def _get(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _put(metrics: dict[str, Any], key: str, value: Any) -> None:
    number = _number(value)
    if number is not None:
        metrics[key] = number


def compact_metrics(module_id: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Extrae solo las métricas numéricas que alimentan las gráficas."""
    if not isinstance(payload, dict):
        return {}
    detail_raw = payload.get("detail")
    detail: dict[str, Any] = detail_raw if isinstance(detail_raw, dict) else {}
    summary_raw = payload.get("summary")
    summary: dict[str, Any] = summary_raw if isinstance(summary_raw, dict) else {}
    metrics: dict[str, Any] = {}

    if module_id == "overview":
        _put(metrics, "cpu_percent", detail.get("cpu_percent"))
        _put(metrics, "memory_percent", detail.get("memory_percent"))
        _put(metrics, "disk_percent", detail.get("disk_percent"))
        _put(metrics, "load1", _get(detail, "load", "1m"))
    elif module_id == "cpu":
        _put(metrics, "percent", summary.get("value"))
        _put(metrics, "load1", _get(detail, "load", "1m"))
        _put(metrics, "load5", _get(detail, "load", "5m"))
        _put(metrics, "frequency_mhz", detail.get("frequency_mhz"))
    elif module_id == "memory":
        _put(metrics, "percent", summary.get("value"))
        _put(metrics, "used_bytes", detail.get("used_bytes"))
        _put(metrics, "available_bytes", detail.get("available_bytes"))
        _put(metrics, "swap_percent", _get(detail, "swap", "percent"))
    elif module_id == "storage":
        _put(metrics, "percent", summary.get("value"))
        mounts = detail.get("mounts")
        if isinstance(mounts, list):
            root = next(
                (
                    item
                    for item in mounts
                    if isinstance(item, dict) and item.get("mountpoint") == "/"
                ),
                None,
            )
            if root:
                _put(metrics, "root_used_bytes", root.get("used_bytes"))
                _put(metrics, "root_inodes_percent", root.get("inodes_percent"))
    elif module_id == "internet":
        _put(metrics, "download_mbps", detail.get("download_mbps"))
        _put(metrics, "upload_mbps", detail.get("upload_mbps"))
        _put(metrics, "latency_ms", detail.get("latency_ms"))
        _put(metrics, "jitter_ms", detail.get("jitter_ms"))
    elif module_id == "devices":
        _put(metrics, "online", _get(detail, "counts", "online"))
        _put(metrics, "total", _get(detail, "counts", "total"))
        _put(metrics, "wan_bytes", _get(detail, "billing", "current", "wan_bytes"))
        _put(metrics, "device_bytes", _get(detail, "billing", "current", "device_bytes"))
    elif module_id == "docker":
        _put(metrics, "running", _get(detail, "system", "containers", "running"))
        _put(metrics, "total", _get(detail, "system", "containers", "total"))
        _put(metrics, "cpu_percent", _get(detail, "totals", "cpu_percent"))
        _put(metrics, "memory_used", _get(detail, "totals", "memory_used"))
    elif module_id == "weather":
        _put(metrics, "temperature", _get(detail, "current", "temperature"))
        _put(metrics, "humidity", _get(detail, "current", "humidity"))
        _put(metrics, "aqi", _get(detail, "air", "us_aqi"))
        _put(metrics, "rain_mm", _get(detail, "rain", "today_mm"))
        _put(metrics, "uv_index", _get(detail, "current", "uv_index"))
    elif module_id == "opencode":
        _put(metrics, "cpu_percent", _get(detail, "container", "cpu_percent"))
        _put(metrics, "memory_used", _get(detail, "container", "memory_used"))
        _put(metrics, "sessions", _get(detail, "app", "stats", "sessions"))
        _put(metrics, "cost", _get(detail, "app", "stats", "cost"))
        tokens = _get(detail, "app", "stats", "tokens")
        if isinstance(tokens, dict):
            _put(metrics, "tokens_input", tokens.get("input"))
            _put(metrics, "tokens_output", tokens.get("output"))
    elif module_id == "network":
        _put(metrics, "rx_bps", detail.get("total_rx_bps"))
        _put(metrics, "tx_bps", detail.get("total_tx_bps"))
        _put(metrics, "rx_errors", detail.get("rx_error_delta"))
        _put(metrics, "tx_errors", detail.get("tx_error_delta"))
        _put(metrics, "interfaces", detail.get("interface_count"))
    elif module_id == "temperature":
        _put(metrics, "max_c", detail.get("max_c"))
        _put(metrics, "sensors", detail.get("sensor_count"))
        _put(metrics, "fans", detail.get("fan_count"))
    elif module_id == "hardware":
        _put(metrics, "battery_percent", _get(detail, "battery", "percent"))
        _put(metrics, "battery_power_w", _get(detail, "battery", "power_w"))
        _put(metrics, "root_inodes_percent", _get(detail, "root_inodes_percent"))
        _put(metrics, "disks", detail.get("disk_count"))
    return metrics


def _database_metrics(stats: dict[str, Any]) -> dict[str, Any]:
    raw_detail = stats.get("detail")
    detail: dict[str, Any] = raw_detail if isinstance(raw_detail, dict) else {}
    metrics: dict[str, Any] = {}
    _put(metrics, "size_bytes", _get(detail, "database", "size_bytes"))
    _put(metrics, "connections", _get(detail, "connections", "current"))
    _put(metrics, "max_connections", _get(detail, "connections", "max"))
    _put(metrics, "cache_hit_ratio", _get(detail, "activity", "cache_hit_ratio"))
    _put(metrics, "dead_tuples", _get(detail, "activity", "dead_tuples"))
    _put(metrics, "tables", _get(detail, "database", "tables"))
    return metrics


class SnapshotMonitor:
    """Guarda una muestra compacta de todos los módulos cada N segundos."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_cleanup = 0.0

    def start(self) -> None:
        if not self.settings.snapshot_monitor_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="snapshot-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample()
            if self._stop.wait(max(30, self.settings.snapshot_interval_seconds)):
                break

    def _sample(self) -> None:
        now = datetime.now(UTC)
        modules: dict[str, Any] = {}
        try:
            summary = get_agent_client().summary()
            raw_modules = summary.get("modules") if isinstance(summary, dict) else None
            if isinstance(raw_modules, dict):
                modules = raw_modules
        except AgentUnavailable:
            logger.debug("agente no disponible; solo se guardará el snapshot de base de datos")
        except Exception:  # noqa: BLE001 - el monitor nunca debe tumbar el backend
            logger.exception("no se pudo leer el resumen del agente para el histórico")

        rows: list[ModuleSnapshot] = []
        for module_id, payload in modules.items():
            if not isinstance(payload, dict):
                continue
            metrics = compact_metrics(module_id, payload)
            if not metrics:
                continue
            status = payload.get("status")
            rows.append(
                ModuleSnapshot(
                    module_id=module_id,
                    status=status if isinstance(status, str) else "unknown",
                    payload={"metrics": metrics},
                )
            )

        try:
            with get_session_factory()() as session:
                try:
                    stats = collect_stats(session)
                except Exception as exc:  # noqa: BLE001 - BD caída no impide el resto
                    logger.warning("no se pudo muestrear la base de datos: %s", exc)
                else:
                    metrics = _database_metrics(stats)
                    if metrics:
                        rows.append(
                            ModuleSnapshot(
                                module_id="database",
                                status=str(stats.get("status", "unknown")),
                                payload={"metrics": metrics},
                            )
                        )

                for row in rows:
                    session.add(row)
                session.commit()

                monotonic = time.monotonic()
                if monotonic - self._last_cleanup >= 3600:
                    cutoff = now - timedelta(days=self.settings.snapshot_history_days)
                    session.execute(
                        delete(ModuleSnapshot).where(ModuleSnapshot.captured_at < cutoff)
                    )
                    session.commit()
                    self._last_cleanup = monotonic
        except Exception:  # noqa: BLE001 - el monitor no debe tumbar el backend
            logger.exception("no se pudieron guardar los snapshots de módulos")

        if rows:
            logger.debug("snapshots guardados: %s", ", ".join(row.module_id for row in rows))
