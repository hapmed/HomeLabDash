"""Tests de los monitores de red, temperatura y hardware."""

from pathlib import Path

from app.config import Settings
from app.hardware import HardwareMonitor, compare_versions
from app.host_network import HostNetworkMonitor
from app.temperature import TemperatureMonitor


def _network_sysfs(tmp_path: Path) -> Path:
    sysfs = tmp_path / "sys"
    stats = sysfs / "class" / "net" / "eth0" / "statistics"
    stats.mkdir(parents=True)
    (sysfs / "class" / "net" / "eth0" / "operstate").write_text("up\n")
    (sysfs / "class" / "net" / "eth0" / "speed").write_text("1000\n")
    (sysfs / "class" / "net" / "eth0" / "mtu").write_text("1500\n")
    (sysfs / "class" / "net" / "eth0" / "address").write_text("aa:bb:cc:dd:ee:ff\n")
    for name in (
        "rx_bytes",
        "tx_bytes",
        "rx_packets",
        "tx_packets",
        "rx_errors",
        "tx_errors",
        "rx_dropped",
        "tx_dropped",
    ):
        (stats / name).write_text("0\n")
    return sysfs


def test_host_network_calcula_tasas(tmp_path: Path) -> None:
    sysfs = _network_sysfs(tmp_path)
    monitor = HostNetworkMonitor(Settings(host_sys=str(sysfs), host_network_enabled=True))
    monitor._sample()
    assert monitor.payload()["summary"]["value"] == 0

    stats = sysfs / "class" / "net" / "eth0" / "statistics"
    (stats / "rx_bytes").write_text("1000000\n")
    (stats / "tx_bytes").write_text("500000\n")
    monitor._sample()
    payload = monitor.payload()
    assert payload["status"] == "ok"
    assert payload["summary"]["unit"] == "Mbps"
    assert payload["detail"]["interfaces"][0]["name"] == "eth0"
    assert payload["detail"]["interfaces"][0]["rx_bps"] > 0


def test_temperature_lee_hwmon(tmp_path: Path) -> None:
    sysfs = tmp_path / "sys"
    hwmon = sysfs / "class" / "hwmon" / "hwmon0"
    hwmon.mkdir(parents=True)
    (hwmon / "name").write_text("coretemp\n")
    (hwmon / "temp1_label").write_text("Package id 0\n")
    (hwmon / "temp1_input").write_text("45000\n")
    (hwmon / "temp1_max").write_text("80000\n")
    (hwmon / "temp1_crit").write_text("90000\n")
    (hwmon / "fan1_input").write_text("1200\n")

    monitor = TemperatureMonitor(Settings(host_sys=str(sysfs), temperature_enabled=True))
    payload = monitor.payload()
    assert payload["status"] == "ok"
    assert payload["summary"]["value"] == 45.0
    assert payload["detail"]["sensors"][0]["label"] == "Package id 0"
    assert payload["detail"]["fans"][0]["rpm"] == 1200


def test_hardware_lee_discos_y_bateria(tmp_path: Path) -> None:
    root = tmp_path / "root"
    proc = tmp_path / "proc"
    sysfs = tmp_path / "sys"
    (root / "etc").mkdir(parents=True)
    (root / "etc" / "hostname").write_text("HomeLab\n")
    (proc / "1").mkdir(parents=True)
    (proc / "1" / "mounts").write_text("/dev/nvme0n1p2 / ext4 rw 0 0\n")

    disk = sysfs / "block" / "nvme0n1"
    (disk / "device").mkdir(parents=True)
    (disk / "queue").mkdir(parents=True)
    (disk / "size").write_text("1000\n")
    (disk / "queue" / "rotational").write_text("0\n")
    (disk / "device" / "model").write_text("Test NVMe\n")
    (disk / "device" / "serial").write_text("SERIAL123\n")
    (disk / "device" / "firmware_rev").write_text("1.0\n")

    hwmon = sysfs / "class" / "hwmon" / "hwmon0"
    hwmon.mkdir(parents=True)
    (hwmon / "name").write_text("nvme\n")
    (hwmon / "temp1_input").write_text("40000\n")

    bat = sysfs / "class" / "power_supply" / "BAT0"
    bat.mkdir(parents=True)
    (bat / "type").write_text("Battery\n")
    (bat / "capacity").write_text("20\n")
    (bat / "status").write_text("Discharging\n")
    (bat / "voltage_now").write_text("12000000\n")
    (bat / "cycle_count").write_text("10\n")
    (bat / "model_name").write_text("Test Battery\n")
    ac = sysfs / "class" / "power_supply" / "AC"
    ac.mkdir()
    (ac / "type").write_text("Mains\n")
    (ac / "online").write_text("1\n")

    dmi = sysfs / "devices" / "virtual" / "dmi" / "id"
    dmi.mkdir(parents=True)
    (dmi / "sys_vendor").write_text("Dell Inc.\n")
    (dmi / "product_name").write_text("Latitude 5490\n")

    dpkg = root / "var" / "lib" / "dpkg"
    dpkg.mkdir(parents=True)
    (dpkg / "status").write_text(
        "Package: foo\nStatus: install ok installed\nVersion: 1.0-1\nArchitecture: amd64\n\n"
        "Package: bar\nStatus: install ok installed\nVersion: 3.0-1\nArchitecture: amd64\n\n"
    )
    apt = root / "var" / "lib" / "apt" / "lists"
    apt.mkdir(parents=True)
    packages = apt / "repo_binary-amd64_Packages"
    packages.write_text(
        "Package: foo\nVersion: 2.0-1\nArchitecture: amd64\n\n"
        "Package: bar\nVersion: 3.0-1\nArchitecture: amd64\n\n"
    )

    settings = Settings(
        host_root=str(root),
        host_proc=str(proc),
        host_sys=str(sysfs),
        hardware_enabled=True,
    )
    payload = HardwareMonitor(settings).payload()
    assert payload["detail"]["battery"]["percent"] == 20
    assert payload["detail"]["battery"]["status"] == "Discharging"
    assert payload["detail"]["disk_count"] == 1
    assert payload["detail"]["disks"][0]["model"] == "Test NVMe"
    assert payload["detail"]["disks"][0]["temperature_c"] == 40.0
    assert payload["detail"]["disks"][0]["smart"]["available"] is False
    assert payload["detail"]["updates"]["available"] == 1
    assert payload["status"] == "warn"

    smart_dir = root / "opt" / "apps" / "HomeLabDash" / "data"
    smart_dir.mkdir(parents=True)
    (smart_dir / "smart.json").write_text(
        '{"devices": {"nvme0n1": {"smart_status": {"passed": true}, '
        '"temperature": {"current": 42}, "power_on_time": {"hours": 1234}, '
        '"nvme_smart_health_information_log": {"percentage_used": 3, "media_errors": 0}}}}'
    )
    smart_payload = HardwareMonitor(settings).payload()
    disk = smart_payload["detail"]["disks"][0]
    assert disk["smart"]["available"] is True
    assert disk["smart"]["status"] == "passed"
    assert disk["temperature_c"] == 42.0
    assert disk["smart"]["power_on_hours"] == 1234
    assert smart_payload["detail"]["smart_available"] is True


def test_compara_versiones_debian() -> None:
    assert compare_versions("2.0-1", "1.0-1") > 0
    assert compare_versions("1.0-1", "1.0-1") == 0
    assert compare_versions("1:1.0", "2.0") > 0
    assert compare_versions("1.0~rc1", "1.0") < 0
