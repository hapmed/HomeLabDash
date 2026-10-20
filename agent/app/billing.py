"""Ciclo de facturación y contadores de 32 bits."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

COUNTER_MODULUS = 2**32


def get_timezone(name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        # México centro/sur sin horario de verano desde 2022.
        return timezone(timedelta(hours=-6))


def _add_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _clamp_day(day: int) -> int:
    return max(1, min(28, day))


def cycle_window(now: datetime, day: int, tz: ZoneInfo | timezone) -> tuple[datetime, datetime]:
    """Devuelve (inicio, fin) del ciclo que contiene `now`.

    Un ciclo empieza el día `day` a las 00:00 local y termina el día `day` del
    mes siguiente. Ejemplo con day=10: 2026-10-10 → 2026-11-10.
    """
    day = _clamp_day(day)
    local = now.astimezone(tz)
    year, month = local.year, local.month
    if local.day < day:
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    start = datetime(year, month, day, tzinfo=tz)
    next_year, next_month = _add_month(year, month)
    end = datetime(next_year, next_month, day, tzinfo=tz)
    return start, end


def counter_delta(
    previous: int | None,
    current: int | None,
    previous_uptime: int | None = None,
    current_uptime: int | None = None,
) -> int:
    """Diferencia de un contador, tolerando wrap de 32 bits y reinicios."""
    if previous is None or current is None or previous < 0 or current < 0:
        return 0
    if current >= previous:
        return current - previous
    if (
        previous_uptime is not None
        and current_uptime is not None
        and current_uptime < previous_uptime
    ):
        # El router se reinició (o reconectó) y el contador volvió a cero.
        return current
    delta = (COUNTER_MODULUS - previous) + current
    return delta if 0 <= delta < COUNTER_MODULUS else 0
