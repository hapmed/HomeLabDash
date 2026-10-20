"""Tests del monitor de Internet (sin red)."""

from pathlib import Path

from app.config import Settings
from app.internet import (
    InternetMonitor,
    adaptive_bytes,
    internet_status,
    mbps,
    parse_trace,
)


def test_parse_trace() -> None:
    trace = parse_trace(
        "fl=123\nh=www.cloudflare.com\nip=203.0.113.7\nloc=ES\ncolo=MAD\nhttp=http/2\n"
    )
    assert trace["ip"] == "203.0.113.7"
    assert trace["loc"] == "ES"
    assert trace["colo"] == "MAD"


def test_mbps() -> None:
    assert mbps(1_000_000, 1.0) == 8.0
    assert mbps(0, 1.0) == 0.0
    assert mbps(1_000_000, 0) == 0.0


def test_adaptive_bytes() -> None:
    assert adaptive_bytes(10_000_000, None) == 10_000_000
    assert adaptive_bytes(10_000_000, 8.0, target_seconds=5) == 5_000_000
    # Nunca baja del mínimo.
    assert adaptive_bytes(10_000_000, 0.5, target_seconds=5, minimum=1_000_000) == 1_000_000
    # Nunca supera el máximo configurado.
    assert adaptive_bytes(10_000_000, 10_000, target_seconds=5) == 10_000_000


def test_estado_de_internet() -> None:
    kwargs = dict(warn_ms=150, critical_ms=400)
    assert internet_status(online=True, latency_ms=20, failures=0, **kwargs) == "ok"
    assert internet_status(online=True, latency_ms=200, failures=0, **kwargs) == "warn"
    assert internet_status(online=True, latency_ms=450, failures=0, **kwargs) == "critical"
    assert internet_status(online=True, latency_ms=20, failures=2, **kwargs) == "warn"
    assert internet_status(online=True, latency_ms=20, failures=3, **kwargs) == "critical"
    assert internet_status(online=False, latency_ms=None, failures=0, **kwargs) == "critical"


def test_historial_persistente(tmp_path: Path) -> None:
    path = tmp_path / "historial.json"
    settings = Settings(
        internet_monitor_enabled=False,
        internet_history_path=str(path),
        internet_history_size=3,
    )
    monitor = InternetMonitor(settings)
    monitor._history = [
        {"at": "2026-10-20T10:00:00+00:00", "download_mbps": 100.0, "upload_mbps": 20.0},
        {"at": "2026-10-20T11:00:00+00:00", "download_mbps": 120.0, "upload_mbps": 22.0},
    ]
    monitor._save_history()

    reloaded = InternetMonitor(settings)
    assert [sample["download_mbps"] for sample in reloaded._history] == [100.0, 120.0]
    snapshot = reloaded.snapshot()
    assert snapshot["history"][1]["upload_mbps"] == 22.0
    assert snapshot["history_limit"] == 3


def test_payload_deshabilitado() -> None:
    settings = Settings(internet_monitor_enabled=False)
    payload = InternetMonitor(settings).payload()
    assert payload["status"] == "unknown"
    assert payload["detail"]["enabled"] is False
