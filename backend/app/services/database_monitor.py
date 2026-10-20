"""Muestreo periódico de la base de datos para el histórico."""

import logging
import threading
import time
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.models.snapshot import ModuleSnapshot
from app.services.database import cleanup_history, collect_stats, snapshot_payload

logger = logging.getLogger(__name__)


class DatabaseMonitor:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_cleanup = 0.0

    def start(self) -> None:
        if not self.settings.database_monitor_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="database-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample()
            if self._stop.wait(max(30, self.settings.database_snapshot_seconds)):
                break

    def _sample(self) -> None:
        try:
            with get_session_factory()() as session:
                stats = collect_stats(session)
                session.add(
                    ModuleSnapshot(
                        module_id="database",
                        status=stats["status"],
                        payload=snapshot_payload(stats),
                    )
                )
                session.commit()

                now = time.monotonic()
                if now - self._last_cleanup >= 3600:
                    cleanup_history(session, self.settings.database_history_days)
                    self._last_cleanup = now
                logger.debug(
                    "snapshot de base de datos: %s", stats["detail"]["database"]["size_pretty"]
                )
        except Exception:  # noqa: BLE001 - el monitor no debe tumbar el backend
            logger.exception(
                "no se pudo guardar el snapshot de base de datos (%s)",
                datetime.now(UTC).isoformat(),
            )
