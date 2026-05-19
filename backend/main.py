"""InfiniDex API — FastAPI entry point."""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from secrets import compare_digest

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Import all models so SQLAlchemy registers them with Base
import backend.db.models  # noqa: F401

from backend.routes import (
    ability_route,
    ai_route,
    creator_route,
    fusion_route,
    generation_route,
    item_route,
    move_route,
    pokemon_route,
    sprite_route,
    stats_route,
    triple_fusion_route,
    type_route,
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

_is_prod = os.getenv("FUSIONDEX_ENV") == "production"


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Log every request: method, path, status, duration (ms).

    Skips /health to avoid log noise from the Docker healthcheck.
    Structured as key=value pairs for easy parsing by log aggregators.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        t0 = time.monotonic()
        response = await call_next(request)
        ms = round((time.monotonic() - t0) * 1000)
        LOGGER.info(
            "method=%s path=%s status=%d duration_ms=%d",
            request.method,
            request.url.path,
            response.status_code,
            ms,
        )
        return response


class StaticCacheMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control and security headers to responses.

    - Cache-Control: public, max-age=3600 on successful GET (excl. /ai, /health)
    - CSP, X-Frame-Options, X-Content-Type-Options on every response
    """

    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' https://raw.githubusercontent.com https://projectpokemon.org; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if (
            request.method == "GET"
            and response.status_code == 200
            and not request.url.path.startswith("/ai")
            and request.url.path != "/health"
        ):
            response.headers["Cache-Control"] = "public, max-age=3600"
        response.headers["Content-Security-Policy"] = self._CSP
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class SlidingWindowRateLimitMiddleware(BaseHTTPMiddleware):
    """Generic sliding-window rate limiter keyed by client IP.

    Parameters
    ----------
    rpm:
        Maximum requests per minute per IP. 0 = disabled.
    trusted_proxy:
        If True, read the client IP from the leftmost X-Forwarded-For value
        (set TRUSTED_PROXY=1 when behind a reverse proxy).  Otherwise use
        request.client.host directly to prevent header spoofing.
    match:
        Callable ``(method, path) -> bool`` — return True when this request
        should be rate-limited.  Called only when rpm > 0.
    """

    def __init__(self, app, rpm: int, trusted_proxy: bool, match) -> None:
        super().__init__(app)
        self._rpm = rpm
        self._trusted_proxy = trusted_proxy
        self._match = match
        self._window: dict[str, list[float]] = {}
        self._request_count = 0

    def _get_ip(self, request: Request) -> str:
        if self._trusted_proxy:
            fwd = request.headers.get("x-forwarded-for", "")
            ip = fwd.split(",")[0].strip()
            if ip:
                return ip
        return (request.client.host or "unknown") if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if self._rpm <= 0 or not self._match(request.method, request.url.path):
            return await call_next(request)

        ip = self._get_ip(request)
        now = time.monotonic()
        cutoff = now - 60.0

        hits = [t for t in self._window.get(ip, []) if t > cutoff]
        if len(hits) >= self._rpm:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"detail": "Trop de requêtes. Réessaie dans une minute."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        hits.append(now)
        self._window[ip] = hits

        self._request_count += 1
        if self._request_count >= 500:
            self._request_count = 0
            self._window = {k: v for k, v in self._window.items() if v and v[-1] > cutoff}
        return await call_next(request)


def _match_search(method: str, path: str) -> bool:
    return method == "GET" and (path.endswith("/search") or path == "/fusion/random")


def _match_ai(method: str, path: str) -> bool:
    return method == "POST" and path == "/ai/ask"


class InternalKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests that don't carry the shared internal secret.

    Active only when INTERNAL_API_KEY is set in the environment.
    The key is injected server-side by the Next.js proxy — the browser
    never sees it. /health is always allowed (Docker healthcheck).
    """

    def __init__(self, app, key: str) -> None:
        super().__init__(app)
        self._key = key

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        if not compare_digest(request.headers.get("X-Internal-Key", ""), self._key):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
        return await call_next(request)


_cors_raw = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:53000,http://localhost:58000",
)
cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
if not cors_origins:
    raise RuntimeError(
        "CORS_ALLOWED_ORIGINS is empty — set it to one or more comma-separated origins "
        "(e.g. 'https://fusiondex.example.com') or '*' to allow all."
    )

_ai_rpm     = int(os.getenv("RATE_LIMIT_AI_RPM",     "0"))
_search_rpm = int(os.getenv("RATE_LIMIT_SEARCH_RPM", "0"))
_internal_key  = os.getenv("INTERNAL_API_KEY", "")
_trusted_proxy = os.getenv("TRUSTED_PROXY", "0") == "1"


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan — runs startup tasks before yielding to serve requests."""
    from backend.db.session import SessionLocal
    from backend.services.fusion_service import load_pokemon_with_types

    def _warm() -> int:
        db = SessionLocal()
        try:
            from backend.db.models import Pokemon
            ids = [row[0] for row in db.query(Pokemon.id).all()]
            for pid in ids:
                load_pokemon_with_types(db, pid)
            return len(ids)
        finally:
            db.close()

    loop = asyncio.get_running_loop()
    count = await loop.run_in_executor(None, _warm)
    LOGGER.info("cache_warmup count=%d", count)
    yield


app = FastAPI(
    title="InfiniDex API",
    description="Pokédex API for Pokémon Infinite Fusion — EN/FR",
    version="0.3.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

app.add_middleware(RequestLogMiddleware)
app.add_middleware(StaticCacheMiddleware)
if _search_rpm > 0:
    app.add_middleware(
        SlidingWindowRateLimitMiddleware,
        rpm=_search_rpm,
        trusted_proxy=_trusted_proxy,
        match=_match_search,
    )
if _ai_rpm > 0:
    app.add_middleware(
        SlidingWindowRateLimitMiddleware,
        rpm=_ai_rpm,
        trusted_proxy=_trusted_proxy,
        match=_match_ai,
    )
if _internal_key:
    app.add_middleware(InternalKeyMiddleware, key=_internal_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Internal-Key"],
)


@app.get("/health", tags=["health"], response_model=dict[str, str])
def healthcheck():
    """Liveness endpoint — used by Docker healthcheck and CI smoke tests."""
    return {"status": "healthy"}


app.include_router(pokemon_route.router)
app.include_router(move_route.router)
app.include_router(move_route.tms_router)
app.include_router(ability_route.router)
app.include_router(type_route.router)
app.include_router(fusion_route.router)
app.include_router(fusion_route.plural_router)
app.include_router(generation_route.router)
app.include_router(creator_route.router)
app.include_router(sprite_route.router)
app.include_router(triple_fusion_route.router)
app.include_router(stats_route.router)
app.include_router(item_route.router)
app.include_router(ai_route.router)
