"""FastAPI application.

Loopback-bound by default. Nothing here talks to the network unless weather
enrichment is explicitly enabled, and nothing leaves the machine.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import assistant, bills, health
from app.config import settings
from app.core.errors import SmartUtilityError
from app.core.logging import configure_logging
from app.db import init_db

log = logging.getLogger("smart_utility.app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    settings.ensure_directories()
    init_db()
    log.info(
        "%s ready on %s:%s (data=%s, ocr=%s, agent=%s, weather=%s)",
        settings.app_name,
        settings.host,
        settings.port,
        settings.data_dir,
        "on" if settings.tesseract_available() else "missing",
        "on" if settings.agent_enabled else "off",
        "on" if settings.weather_enabled else "off",
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Local bill-intelligence backend. Upload an electricity bill, get a "
        "structured analysis. Everything is processed and stored on this machine."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    expose_headers=["Content-Type"],
)


@app.exception_handler(SmartUtilityError)
async def domain_error_handler(_request: Request, exc: SmartUtilityError) -> JSONResponse:
    if exc.code not in ("job_not_found", "analysis_not_ready"):
        log.warning("domain error %s: %s", exc.code, exc.detail or exc.message)
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


app.include_router(health.router)
app.include_router(bills.router)
app.include_router(assistant.router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "health": "/api/v1/health",
        "docs": "/docs",
    }
