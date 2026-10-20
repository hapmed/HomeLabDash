"""Interfaces de red del host (solo lectura).

Lee `/sys/class/net` del host montado en `/host/sys`. Calcula tasas por
diferencia de contadores; no abre sockets ni modifica interfaces.
"""

import copy
import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.metrics import worst

logger = logging.getLogger(__name__)

SKIP_PREFIXES = (
    "lo",
    "docker",
    "veth",
    "br-",
    "virbr",
    "tun",
    "tap",
    "wg",
    "zt",
    "tailscale",
    "dummy",
)
COUNTERS = (
    "rx_bytes",
    "tx_bytes",
    "rx_packets",
    "tx_packets",
    "rx_errors",
    "tx_errors",
    "rx_dropped",
    "tx_dropped",
)


def _read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return default


def _int(path: Path, default: int = 0) -> int:
    raw = _read(path)
    try:
        return int(raw)
    except ValueError:
        return default


def _wifi(name: str, base: Path) -> bool:
    return (base / name / "wireless").exists() or name.startswith(("wl", "wlan", "wlp"))


def _delta(current: int, previous: int) -> int:
    return max(0, current - previous) if current >= previous else 0


class HostNetworkMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._previous: dict[str, tuple[float, dict[str, int]]] = {}
        self._state: dict[str, Any] = {
            "enabled": settings.host_network_enabled,
            "interfaces": [],
            "total_rx_bps": 0.0,
            "total_tx_bps": 0.0,
            "total_rx_errors": 0,
            "total_tx_errors": 0,
            "total_rx_dropped": 0,
            "total_tx_dropped": 0,
            "rx_error_delta": 0,
            "tx_error_delta": 0,
            "rx_dropped_delta": 0,
            "tx_dropped_delta": 0,
            "interface_count": 0,
            "sampled_at": None,
            "error": None,
        }

    def start(self) -> None:
        if not self.settings.host_network_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="host-network", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample()
            if self._stop.wait(max(2, self.settings.host_network_poll_seconds)):
                break

    def _sample(self) -> None:
        base = Path(self.settings.sysfs) / "class" / "net"
        if not base.is_dir():
            with self._lock:
                self._state["error"] = "no se puede leer /sys/class/net del host"
            return

        now = time.monotonic()
        interfaces: list[dict[str, Any]] = []
        totals = {key: 0 for key in COUNTERS}
        error_deltas = {"rx_errors": 0, "tx_errors": 0, "rx_dropped": 0, "tx_dropped": 0}

        for entry in sorted(base.iterdir(), key=lambda item: item.name):
            name = entry.name
            if not entry.is_dir() or name.startswith(SKIP_PREFIXES):
                continue
            stats = entry / "statistics"
            counters = {key: _int(stats / key) for key in COUNTERS}
            previous = self._previous.get(name)
            rx_bps = tx_bps = 0.0
            if previous is not None:
                elapsed, old = previous
                if now > elapsed:
                    rx_bps = _delta(counters["rx_bytes"], old["rx_bytes"]) / (now - elapsed)
                    tx_bps = _delta(counters["tx_bytes"], old["tx_bytes"]) / (now - elapsed)
                    for key in error_deltas:
                        error_deltas[key] += _delta(counters[key], old[key])
            self._previous[name] = (now, counters)
            for key in COUNTERS:
                totals[key] += counters[key]

            operstate = _read(entry / "operstate", "unknown")
            speed_raw = _read(entry / "speed")
            try:
                speed = int(speed_raw)
            except ValueError:
                speed = None
            interfaces.append(
                {
                    "name": name,
                    "type": "wifi" if _wifi(name, base) else "ethernet",
                    "state": operstate,
                    "up": operstate == "up",
                    "speed_mbps": speed if speed and speed > 0 else None,
                    "mtu": _int(entry / "mtu"),
                    "mac": _read(entry / "address") or None,
                    "rx_bytes": counters["rx_bytes"],
                    "tx_bytes": counters["tx_bytes"],
                    "rx_packets": counters["rx_packets"],
                    "tx_packets": counters["tx_packets"],
                    "rx_errors": counters["rx_errors"],
                    "tx_errors": counters["tx_errors"],
                    "rx_dropped": counters["rx_dropped"],
                    "tx_dropped": counters["tx_dropped"],
                    "rx_bps": round(rx_bps, 1),
                    "tx_bps": round(tx_bps, 1),
                }
            )

        interfaces.sort(key=lambda item: (not item["up"], item["name"]))
        up = [item for item in interfaces if item["up"]]
        total_rx = sum(float(item["rx_bps"]) for item in up)
        total_tx = sum(float(item["tx_bps"]) for item in up)

        status = "ok"
        if not interfaces:
            status = "unknown"
        elif not up:
            status = "warn"
        if any(value > 0 for value in error_deltas.values()):
            status = worst([status, "warn"])

        with self._lock:
            self._state.update(
                {
                    "interfaces": interfaces,
                    "total_rx_bps": round(total_rx, 1),
                    "total_tx_bps": round(total_tx, 1),
                    "total_rx_errors": sum(item["rx_errors"] for item in interfaces),
                    "total_tx_errors": sum(item["tx_errors"] for item in interfaces),
                    "total_rx_dropped": sum(item["rx_dropped"] for item in interfaces),
                    "total_tx_dropped": sum(item["tx_dropped"] for item in interfaces),
                    "rx_error_delta": error_deltas["rx_errors"],
                    "tx_error_delta": error_deltas["tx_errors"],
                    "rx_dropped_delta": error_deltas["rx_dropped"],
                    "tx_dropped_delta": error_deltas["tx_dropped"],
                    "interface_count": len(interfaces),
                    "sampled_at": datetime.now(UTC).isoformat(),
                    "error": None if interfaces else "sin interfaces visibles",
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def payload(self) -> dict[str, Any]:
        snap = self.snapshot()
        if not snap["enabled"]:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Red",
                    "value": "—",
                    "detail": "Monitor deshabilitado",
                },
                "detail": snap,
            }
        interfaces = snap["interfaces"]
        if not interfaces:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Red",
                    "value": "—",
                    "detail": snap.get("error") or "Sin interfaces",
                },
                "detail": snap,
            }
        up = [item for item in interfaces if item.get("up")]
        status = "warn" if not up else "ok"
        if any(
            int(snap.get(key, 0) or 0) > 0
            for key in ("rx_error_delta", "tx_error_delta", "rx_dropped_delta", "tx_dropped_delta")
        ):
            status = worst([status, "warn"])
        rx_mbps = round(float(snap["total_rx_bps"]) / 1_000_000, 2)
        tx_mbps = round(float(snap["total_tx_bps"]) / 1_000_000, 2)
        return {
            "status": status,
            "summary": {
                "label": "Bajada",
                "value": rx_mbps,
                "unit": "Mbps",
                "detail": f"Subida {tx_mbps:.2f} Mbps · {len(interfaces)} interfaces",
            },
            "detail": snap,
        }
