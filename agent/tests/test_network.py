"""Tests del inventario de dispositivos (sin red real)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import Settings
from app.network import NetworkMonitor, parse_arp, update_registry

ARP = """IP address       HW type     Flags       HW address            Mask     Device
192.168.0.10     0x1         0x2         46:c3:7b:e1:a6:16     *        enp0s31f6
192.168.0.99     0x1         0x0         00:00:00:00:00:00     *        enp0s31f6
192.168.0.1      0x1         0x2         c0:25:2f:3a:9f:d1     *        enp0s31f6
172.18.0.2       0x1         0x2         02:42:ac:12:00:02     *        br-abc
"""


def test_parse_arp_filtra_incompletas() -> None:
    entries = parse_arp(ARP)
    assert [entry.ip for entry in entries] == ["192.168.0.10", "192.168.0.1", "172.18.0.2"]
    assert entries[0].mac == "46:c3:7b:e1:a6:16"
    assert entries[0].device == "enp0s31f6"


def test_registro_de_presencia_y_tiempos() -> None:
    now = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
    observed = {
        "46:c3:7b:e1:a6:16": {
            "ip": "192.168.0.10",
            "name": "Apple",
            "vendor": "Apple",
        }
    }

    registry = update_registry({}, observed, now, 60)
    entry = registry["46:c3:7b:e1:a6:16"]
    assert entry["online"] is True
    assert entry["first_seen"] == now.isoformat()
    assert entry["online_seconds"] == 0.0

    update_registry(registry, observed, now + timedelta(seconds=60), 60)
    assert 59 <= registry["46:c3:7b:e1:a6:16"]["online_seconds"] <= 61

    update_registry(registry, {}, now + timedelta(seconds=120), 60)
    entry = registry["46:c3:7b:e1:a6:16"]
    assert entry["online"] is False
    assert entry["online_seconds"] >= 119
    assert entry["last_seen"] == (now + timedelta(seconds=60)).isoformat()


def test_reconexion_incrementa_sesiones() -> None:
    now = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
    mac = "46:c3:7b:e1:a6:16"
    observed = {mac: {"ip": "192.168.0.10", "name": "Apple", "vendor": "Apple"}}

    registry = update_registry({}, observed, now, 60)
    update_registry(registry, {}, now + timedelta(seconds=60), 60)
    update_registry(registry, observed, now + timedelta(seconds=120), 60)

    assert registry[mac]["online"] is True
    assert registry[mac]["sessions"] == 2


def test_persistencia(tmp_path: Path) -> None:
    path = tmp_path / "devices.json"
    settings = Settings(
        network_monitor_enabled=False,
        network_history_path=str(path),
        network_name="Casa",
    )
    monitor = NetworkMonitor(settings)
    monitor._registry = {
        "46:c3:7b:e1:a6:16": {
            "mac": "46:c3:7b:e1:a6:16",
            "ip": "192.168.0.10",
            "name": "Apple",
            "online": True,
        }
    }
    monitor._save_registry(monitor._registry)

    reloaded = NetworkMonitor(settings)
    assert reloaded._registry["46:c3:7b:e1:a6:16"]["ip"] == "192.168.0.10"


def test_payload_deshabilitado() -> None:
    payload = NetworkMonitor(Settings(network_monitor_enabled=False)).payload()
    assert payload["status"] == "unknown"
    assert payload["detail"]["enabled"] is False


def test_top_consumer_y_consumo_disponible(tmp_path: Path) -> None:
    monitor = NetworkMonitor(
        Settings(
            network_monitor_enabled=False,
            network_history_path=str(tmp_path / "devices.json"),
        )
    )
    monitor._registry = {
        "aa:bb:cc:dd:ee:01": {
            "mac": "aa:bb:cc:dd:ee:01",
            "ip": "192.168.0.20",
            "name": "Equipo A",
            "vendor": "Apple",
            "online": True,
            "bytes": 120.0,
        },
        "aa:bb:cc:dd:ee:02": {
            "mac": "aa:bb:cc:dd:ee:02",
            "ip": "192.168.0.21",
            "name": "Equipo B",
            "vendor": "Samsung",
            "online": True,
            "bytes": 900.0,
        },
    }
    monitor._state["consumption_available"] = True
    monitor._state["router"] = {"enabled": True, "ssid": "Skynet", "model": "AC12", "error": None}

    snapshot = monitor.snapshot()
    assert snapshot["consumption_available"] is True
    assert snapshot["top_consumer"]["name"] == "Equipo B"
    assert snapshot["top_consumer"]["bytes"] == 900.0
    assert snapshot["warning"] == ""
    assert "estimado" in snapshot["consumption_note"]
