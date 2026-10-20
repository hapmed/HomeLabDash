"""Tests del cliente TDDP del Mercusys AC12."""

from app.router import (
    SALT,
    org_auth_pwd,
    parse_blocks,
    parse_devices,
    parse_model,
    parse_ssid,
    security_encode,
)

DEVICES = """00000
id 13
ip 0 192.168.0.10
ip 1 192.168.0.14
ip 2 0.0.0.0
mac 0 46-c3-7b-e1-a6-16
mac 1 e4-b9-7a-77-71-95
mac 2 00-00-00-00-00-00
type 0 3
type 1 0
online 0 1
online 1 1
online 2 0
blocked 0 0
blocked 1 0
blocked 2 0
up 0 440
up 1 2446
down 0 343
down 1 3830
name 0 Galaxy%20A20s
name 1 HomeLab
name 2
"""

WIRELESS = """00000
id 33
bEnable 1
cSsid Skynet
cPskSecret no-debe-salir
id 53
bEnable 1
cSsid Skynet
cPskSecret no-debe-salir
"""


def test_security_encode() -> None:
    assert security_encode("abc", "abc", "0123456789") == "000"
    assert security_encode("abc", "abd", "0123456789") == "007"


def test_org_auth_pwd_es_determinista() -> None:
    first = org_auth_pwd("test-password")
    assert first == org_auth_pwd("test-password")
    assert len(first) == len(SALT)


def test_parse_blocks() -> None:
    blocks = parse_blocks(DEVICES)
    assert 13 in blocks
    assert blocks[13]["arrays"]["ip"][0] == "192.168.0.10"


def test_parse_devices() -> None:
    devices = parse_devices(DEVICES)
    assert len(devices) == 2
    galaxy, server = devices
    assert galaxy.mac == "46:c3:7b:e1:a6:16"
    assert galaxy.name == "Galaxy A20s"
    assert galaxy.connection == "5 GHz"
    assert galaxy.online is True
    assert galaxy.up_bps == 440
    assert galaxy.down_bps == 343
    assert server.connection == "Cable"
    assert server.name == "HomeLab"


def test_parse_ssid_y_modelo() -> None:
    assert parse_ssid(WIRELESS) == "Skynet"
    info = "00000\nid 0\nmodelName AC12\n"
    assert parse_model(info) == "AC12"


def test_parse_wan() -> None:
    from app.router import parse_wan

    text = (
        "00000\nid 23\nip 192.168.1.2\ninOctets 1670783140\n"
        "outOctets 1963985017\nupTime 9332520\n"
    )
    assert parse_wan(text) == (1670783140, 1963985017, 9332520)
    assert parse_wan("00000\nid 13\n") == (None, None, None)


def test_parse_devices_rechaza_sin_autorizacion() -> None:
    import pytest

    from app.router import RouterSessionError

    with pytest.raises(RouterSessionError):
        parse_blocks("00007\nid 13\n")
