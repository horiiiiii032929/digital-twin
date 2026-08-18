"""Small security middleware kept independent from product-domain logic."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from threading import RLock
from uuid import uuid4

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.observability import OperationalMetrics


LOGGER = logging.getLogger("digital_twin.api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class OriginGuardMiddleware(BaseHTTPMiddleware):
    """Reject unsafe cookie-authenticated cross-origin requests in staging."""

    _SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, app, *, settings: AppSettings) -> None:
        super().__init__(app)
        self.settings = settings
        self.allowed_origins = set(settings.allowed_origins)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if (
            self.settings.mode == RuntimeMode.STAGING
            and request.method not in self._SAFE_METHODS
        ):
            origin = request.headers.get("origin", "").rstrip("/")
            if origin not in self.allowed_origins:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": {
                            "code": "origin_not_allowed",
                            "message": "The request origin is not allowed.",
                        }
                    },
                )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if self.settings.mode == RuntimeMode.STAGING:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, metrics: OperationalMetrics) -> None:
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            self._record(request, request_id, status_code, started)
            raise
        self._record(request, request_id, status_code, started)
        response.headers["X-Request-ID"] = request_id
        return response

    def _record(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        started: float,
    ) -> None:
        duration_ms = (time.perf_counter() - started) * 1000
        route = getattr(request.scope.get("route"), "path", "unmatched")
        self.metrics.observe_request(
            method=request.method,
            route=route,
            status_code=status_code,
            duration_ms=duration_ms,
        )
        LOGGER.info(
            json.dumps(
                {
                    "event": "http-request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 3),
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Bounded single-node fixed-window limiter for staging protection."""

    def __init__(self, app, *, settings: AppSettings) -> None:
        super().__init__(app)
        self.settings = settings
        self._lock = RLock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if self.settings.mode != RuntimeMode.STAGING:
            return await call_next(request)
        if request.url.path == "/api/auth/login":
            key = f"login:{request.client.host if request.client else 'unknown'}"
            limit = self.settings.login_attempts_per_minute
        else:
            token = request.cookies.get(self.settings.session_cookie_name)
            if not token:
                return await call_next(request)
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
            key = f"session:{digest}"
            limit = self.settings.authenticated_requests_per_minute
        if not self._allow(key, limit):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"},
                content={
                    "detail": {
                        "code": "rate_limit_exceeded",
                        "message": "Request rate limit exceeded. Try again shortly.",
                    }
                },
            )
        return await call_next(request)

    def _allow(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        cutoff = now - 60
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            if len(self._events) > 10_000:
                self._events = defaultdict(
                    deque,
                    {name: values for name, values in self._events.items() if values},
                )
            return True


class UploadSizeGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: AppSettings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method == "PUT" and "/sources/" in request.url.path:
            raw_length = request.headers.get("content-length")
            if raw_length is not None:
                try:
                    too_large = int(raw_length) > self.settings.max_upload_bytes
                except ValueError:
                    too_large = True
                if too_large:
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={
                            "detail": {
                                "code": "source_too_large",
                                "message": "The upload exceeds the configured size limit.",
                            }
                        },
                    )
        return await call_next(request)
