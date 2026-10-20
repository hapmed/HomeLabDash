"""Tests del monitor Docker (sin daemon)."""

from datetime import UTC, datetime

from app.config import Settings
from app.docker_monitor import (
    DockerMonitor,
    calculate_block_io,
    calculate_cpu_percent,
    calculate_memory,
    calculate_network,
    human_bytes,
    parse_docker_time,
)

STATS = {
    "cpu_stats": {
        "cpu_usage": {"total_usage": 200_000_000, "percpu_usage": [1, 2]},
        "system_cpu_usage": 2_000_000_000,
        "online_cpus": 2,
    },
    "precpu_stats": {
        "cpu_usage": {"total_usage": 100_000_000},
        "system_cpu_usage": 1_000_000_000,
    },
    "memory_stats": {
        "usage": 200 * 1024 * 1024,
        "limit": 1024 * 1024 * 1024,
        "stats": {"inactive_file": 50 * 1024 * 1024},
    },
    "networks": {"eth0": {"rx_bytes": 1000, "tx_bytes": 2000}},
    "blkio_stats": {
        "io_service_bytes_recursive": [
            {"op": "read", "value": 300},
            {"op": "write", "value": 400},
        ]
    },
}


def test_cpu() -> None:
    assert calculate_cpu_percent(STATS) == 20.0
    assert calculate_cpu_percent(None) == 0.0


def test_memoria() -> None:
    used, limit, percent = calculate_memory(STATS)
    assert used == 150 * 1024 * 1024
    assert limit == 1024 * 1024 * 1024
    assert percent == 14.6


def test_red_y_bloques() -> None:
    assert calculate_network(STATS) == (1000, 2000)
    assert calculate_block_io(STATS) == (300, 400)


def test_fechas() -> None:
    parsed = parse_docker_time("2026-10-20T10:00:00.123456789Z")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.year == 2026
    assert parse_docker_time("0001-01-01T00:00:00Z") is None


def test_human_bytes() -> None:
    assert human_bytes(512) == "512 B"
    assert human_bytes(1024) == "1.0 KB"
    assert human_bytes(1024**3) == "1.0 GB"


def test_payload_deshabilitado() -> None:
    payload = DockerMonitor(Settings(docker_monitor_enabled=False)).payload()
    assert payload["status"] == "unknown"
    assert payload["detail"]["enabled"] is False


def test_payload_con_datos() -> None:
    monitor = DockerMonitor(Settings(docker_monitor_enabled=True))
    monitor._state.update(
        {
            "system": {"containers": {"running": 2, "total": 3}},
            "totals": {"cpu_percent": 2.5, "memory_used": 1024},
            "containers": [
                {"name": "a", "state": "running", "health": None},
                {"name": "b", "state": "running", "health": None},
            ],
            "sampled_at": datetime.now(UTC).isoformat(),
        }
    )
    payload = monitor.payload()
    assert payload["status"] == "ok"
    assert payload["summary"]["value"] == "2/3"
