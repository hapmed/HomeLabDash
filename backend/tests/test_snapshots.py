"""Tests del histórico compacto de módulos."""

from app.services.snapshot_monitor import compact_metrics


def test_compact_metrics_cpu() -> None:
    metrics = compact_metrics(
        "cpu",
        {
            "status": "warn",
            "summary": {"label": "uso", "value": 77.0, "unit": "%"},
            "detail": {"load": {"1m": 1.2, "5m": 0.8}, "frequency_mhz": 2400},
        },
    )
    assert metrics == {"percent": 77.0, "load1": 1.2, "load5": 0.8, "frequency_mhz": 2400}


def test_compact_metrics_ignora_texto() -> None:
    metrics = compact_metrics(
        "docker",
        {
            "detail": {
                "system": {"containers": {"running": 7, "total": 14}},
                "totals": {"cpu_percent": 2.1, "memory_used": "mucho"},
            }
        },
    )
    assert metrics == {"running": 7, "total": 14, "cpu_percent": 2.1}


def test_compact_metrics_red_y_hardware() -> None:
    network = compact_metrics(
        "network",
        {
            "detail": {
                "total_rx_bps": 12_500_000,
                "total_tx_bps": 2_100_000,
                "rx_error_delta": 0,
                "tx_error_delta": 1,
                "interface_count": 2,
            }
        },
    )
    assert network["rx_bps"] == 12_500_000
    assert network["tx_errors"] == 1

    hardware = compact_metrics(
        "hardware",
        {
            "detail": {
                "battery": {"percent": 80, "power_w": 12.3},
                "root_inodes_percent": 4.0,
                "disk_count": 1,
            }
        },
    )
    assert hardware == {
        "battery_percent": 80,
        "battery_power_w": 12.3,
        "root_inodes_percent": 4.0,
        "disks": 1,
    }
