"""FusionDex API — FastAPI entry point."""

import os

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

app = FastAPI(
    title="FusionDex API",
    description="Pokédex API for Pokémon Infinite Fusion — EN/FR",
    version="0.3.0",
)


class StaticCacheMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control headers to successful GET responses on read-only data.

    Excludes /ai/* (streaming + dynamic) and /health.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if (
            request.method == "GET"
            and response.status_code == 200
            and not request.url.path.startswith("/ai")
            and request.url.path != "/health"
        ):
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response

_cors_raw = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:53000,http://localhost:58000",
)
cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

# En temps normal, le browser ne tape jamais le backend directement : les
# requêtes passent par le proxy Next.js (même origine). Ce CORS sert de
# defense in depth pour les appels directs (Swagger, Postman, intégrations).
app.add_middleware(StaticCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", tags=["health"])
def healthcheck():
    """Endpoint de liveness — utilisé par Docker healthcheck + CI smoke."""
    return {"status": "healthy"}


app.include_router(pokemon_route.router)
app.include_router(move_route.router)
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
