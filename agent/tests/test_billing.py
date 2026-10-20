"""Tests del ciclo de facturación y contadores."""

from datetime import UTC, datetime

from app.billing import counter_delta, cycle_window, get_timezone

TZ = UTC


def test_ciclo_antes_del_dia_10() -> None:
    now = datetime(2026, 10, 9, 23, 0, tzinfo=TZ)
    start, end = cycle_window(now, 10, TZ)
    assert start.isoformat() == "2026-09-10T00:00:00+00:00"
    assert end.isoformat() == "2026-10-10T00:00:00+00:00"


def test_ciclo_el_dia_10() -> None:
    now = datetime(2026, 10, 10, 0, 1, tzinfo=TZ)
    start, end = cycle_window(now, 10, TZ)
    assert start.isoformat() == "2026-10-10T00:00:00+00:00"
    assert end.isoformat() == "2026-11-10T00:00:00+00:00"


def test_ciclo_cambia_de_ano() -> None:
    start, end = cycle_window(datetime(2027, 1, 5, 12, 0, tzinfo=TZ), 10, TZ)
    assert start.isoformat() == "2026-12-10T00:00:00+00:00"
    assert end.isoformat() == "2027-01-10T00:00:00+00:00"

    start, end = cycle_window(datetime(2026, 12, 15, 12, 0, tzinfo=TZ), 10, TZ)
    assert start.isoformat() == "2026-12-10T00:00:00+00:00"
    assert end.isoformat() == "2027-01-10T00:00:00+00:00"


def test_zona_horaria_de_monterrey() -> None:
    tz = get_timezone("America/Monterrey")
    now = datetime(2026, 10, 10, 3, 0, tzinfo=UTC)  # 9 oct 21:00 en Monterrey
    start, end = cycle_window(now, 10, tz)
    assert start.date().isoformat() == "2026-09-10"
    assert end.date().isoformat() == "2026-10-10"


def test_counter_delta_normal() -> None:
    assert counter_delta(100, 250) == 150
    assert counter_delta(None, 250) == 0


def test_counter_delta_wrap_y_reinicio() -> None:
    assert counter_delta(2**32 - 10, 5) == 15
    assert counter_delta(2**32 - 10, 5, previous_uptime=1000, current_uptime=10) == 5
    assert counter_delta(0, 0) == 0
