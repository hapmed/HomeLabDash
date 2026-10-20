"""Tests del agente."""

from pathlib import Path

from app.config import Settings
from app.metrics import HostMetrics, format_uptime, status_for, worst


def test_helpers_de_estado() -> None:
    assert status_for(10, 75, 90) == "ok"
    assert status_for(80, 75, 90) == "warn"
    assert status_for(95, 75, 90) == "critical"
    assert worst(["ok", "warn"]) == "warn"
    assert worst(["warn", "critical", "ok"]) == "critical"
    assert worst([]) == "unknown"


def test_format_uptime() -> None:
    assert format_uptime(4 * 86400 + 3 * 3600 + 12 * 60) == "4d 3h 12m"
    assert format_uptime(2 * 3600 + 5 * 60) == "2h 5m"
    assert format_uptime(90) == "1m"


def _fake_host(tmp_path: Path) -> Settings:
    root = tmp_path / "root"
    proc = tmp_path / "proc"
    (root / "etc").mkdir(parents=True)
    (root / "etc" / "hostname").write_text("HomeLab\n")
    (root / "boot" / "efi").mkdir(parents=True)
    (root / "mnt" / "mi disco").mkdir(parents=True)
    (proc / "1").mkdir(parents=True)
    (proc / "1" / "mounts").write_text(
        "/dev/nvme0n1p2 / ext4 rw,relatime 0 0\n"
        "tmpfs /run tmpfs rw 0 0\n"
        "/dev/nvme0n1p1 /boot/efi vfat rw 0 0\n"
        "/dev/nvme0n1p2 /mnt/mi\\040disco ext4 rw 0 0\n"
        "overlay /var/lib/docker/overlay2/x ext4 rw 0 0\n"
    )
    return Settings(host_root=str(root), host_proc=str(proc), host_sys=str(root / "sys"))


def test_lee_hostname_del_host(tmp_path: Path) -> None:
    metrics = HostMetrics(_fake_host(tmp_path))
    assert metrics._hostname() == "HomeLab"


def test_lista_montajes_reales_y_decodifica_espacios(tmp_path: Path) -> None:
    metrics = HostMetrics(_fake_host(tmp_path))
    mounts = metrics._mounts()
    mountpoints = [mount["mountpoint"] for mount in mounts]

    assert mountpoints[0] == "/"
    assert "/boot/efi" in mountpoints
    assert "/mnt/mi disco" in mountpoints
    assert "/run" not in mountpoints  # tmpfs
    assert not any("docker" in point for point in mountpoints)  # overlay
    assert all(mount["percent"] >= 0 for mount in mounts)


def test_storage_usa_el_disco_raiz(tmp_path: Path) -> None:
    metrics = HostMetrics(_fake_host(tmp_path))
    storage = metrics.storage()
    assert storage["summary"]["label"] == "Disco raíz"
    assert isinstance(storage["summary"]["value"], float)
    assert storage["detail"]["mounts"]
