"""Liveness and capability report.

The frontend calls this once at startup to decide whether to use the live
backend or stay in demo mode, so it must answer without touching a document.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.schemas import HealthResponse
from app.services import agent_service

router = APIRouter(prefix="/api/v1", tags=["health"])


def _ocr_report() -> dict[str, object]:
    binary = shutil.which(settings.ocr_engine)
    languages: list[str] = []
    if binary:
        import subprocess

        try:
            proc = subprocess.run(
                [binary, "--list-langs"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            languages = [
                line.strip()
                for line in proc.stdout.splitlines()[1:]
                if line.strip() and " " not in line.strip()
            ]
        except (OSError, subprocess.SubprocessError):
            languages = []

    requested = list(settings.ocr_languages)
    missing = [lang for lang in requested if lang not in languages]

    return {
        "engine": settings.ocr_engine,
        "available": bool(binary),
        "binary": binary,
        "requested_languages": requested,
        "installed_languages": languages,
        "missing_languages": missing,
        "dpi": settings.ocr_dpi,
        "max_pages": settings.ocr_max_pages,
        "pdf_rasteriser": "pymupdf" if _pymupdf_available() else "unavailable",
    }


def _pymupdf_available() -> bool:
    try:
        import pymupdf  # noqa: F401

        return True
    except ImportError:
        return False


def _database_report(session: Session) -> dict[str, object]:
    try:
        session.execute(text("SELECT 1"))
        writable = True
        try:
            probe = settings.data_dir / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            writable = False
        return {
            "available": True,
            "path": str(settings.db_path),
            "writable": writable,
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"available": False, "error": type(exc).__name__}


def _weather_report() -> dict[str, object]:
    return {
        "enabled": settings.weather_enabled,
        "status": "available" if settings.weather_enabled else "unavailable",
        "provider": settings.weather_api_base if settings.weather_enabled else None,
    }


@router.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    ocr = _ocr_report()
    database = _database_report(session)
    agent = agent_service.capabilities()

    problems = []
    if not ocr["available"]:
        problems.append("ocr")
    if not database.get("available"):
        problems.append("database")

    return HealthResponse(
        status="ok" if not problems else "degraded",
        ocr=ocr,
        agent=agent,
        database=database,
        weather=_weather_report(),
    )


@router.get("/storage")
def storage_report() -> dict[str, object]:
    """Where the local corpus lives. Paths only — never document contents."""
    return {
        "data_dir": str(settings.data_dir),
        "uploads": str(settings.uploads_dir),
        "processed": str(settings.processed_dir),
        "results": str(settings.results_dir),
        "logs": str(settings.log_dir),
        "database": str(settings.db_path),
        "local_only": True,
        "max_upload_bytes": settings.max_upload_bytes,
        "directories_exist": {
            name: Path(path).exists()
            for name, path in (
                ("uploads", settings.uploads_dir),
                ("processed", settings.processed_dir),
                ("results", settings.results_dir),
                ("logs", settings.log_dir),
            )
        },
    }
