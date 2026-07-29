"""RETAINER FastAPI application.

Wires middleware (correlation id + audit), Clerk-based auth, plain-English error
handling, a public /health probe, and the firm-scoped v1 API under
/api/v1/retainer. Production must run in Clerk auth mode — enforced at startup.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(".env.local", override=True)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.v1 import router as v1_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.errors import install_error_handlers  # noqa: E402
from app.core.logging import get_logger  # noqa: E402
from app.core.middleware import audit_middleware, correlation_id_middleware  # noqa: E402

logger = get_logger("retainer.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_production and settings.auth_mode != "clerk":
        raise RuntimeError(
            "AUTH_MODE=local is forbidden in production. Set AUTH_MODE=clerk and CLERK_JWKS_URL."
        )
    logger.info(
        "RETAINER starting: env=%s auth_mode=%s db=%s",
        settings.environment,
        settings.auth_mode,
        "postgres" if settings.retainer_database_url else "sqlite(fallback)",
    )
    yield
    logger.info("RETAINER shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.middleware("http")(audit_middleware)
app.middleware("http")(correlation_id_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app)
app.include_router(v1_router, prefix="/api/v1/retainer")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "retainer",
        "version": settings.app_version,
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
