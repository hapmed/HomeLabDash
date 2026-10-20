"""Rate limiting en memoria para rutas sensibles (una sola instancia)."""

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
WINDOW_SECONDS = 60


def reset() -> None:
    _WINDOWS.clear()


def rate_limit(scope: str) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        limit = settings.rate_limit_auth_per_minute
        client = request.client.host if request.client else "unknown"
        key = f"{scope}:{client}"
        now = time.monotonic()
        window = _WINDOWS[key]
        while window and window[0] <= now - WINDOW_SECONDS:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="demasiadas solicitudes; inténtalo más tarde",
            )
        window.append(now)

    return dependency
