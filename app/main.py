"""FastAPI application entry point."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analytics, batches, leads, webhooks
from app.config import get_settings
from app.utils.observability import configure_logging, configure_otel

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    logger.info("LOCE starting up", env=settings.app_env)
    configure_otel(settings.otel_service_name, settings.otel_exporter_otlp_endpoint)
    yield
    logger.info("LOCE shutting down")


app = FastAPI(
    title="Lead Orchestration & Communication Engine (LOCE)",
    description=(
        "Scalable orchestration system for lead ingestion, NBFC dedupe routing, "
        "multi-channel communication, and end-to-end funnel tracking."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(batches.router, prefix="/batches", tags=["Batches"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "loce"}


# ── Global Exception Handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=str(request.url), error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
