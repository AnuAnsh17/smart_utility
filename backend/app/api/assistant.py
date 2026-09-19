"""Electricity-scoped assistant endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import AnalysisBundle, ChatRequest, ChatResponse
from app.services import assistant_service, storage_service

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
log = logging.getLogger("smart_utility.api")


def _load_bundle(job_id: str | None) -> AnalysisBundle | None:
    """Read the stored analysis for a job, if one exists.

    The assistant is grounded on this and nothing else: if there is no result
    on disk it answers with the insufficient-information message rather than
    speculating.
    """
    if not job_id:
        return None
    stored = storage_service.read_result(job_id)
    if not stored:
        return None
    try:
        return AnalysisBundle.model_validate(stored.get("bundle"))
    except Exception:  # noqa: BLE001 - a corrupt result simply yields no context
        log.warning("assistant: unreadable analysis bundle for job %s", job_id)
        return None


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, session: Session = Depends(get_session)) -> ChatResponse:
    result = assistant_service.respond(
        session,
        message=payload.message,
        job_id=payload.job_id,
        session_id=payload.session_id,
        bundle=_load_bundle(payload.job_id),
    )
    return ChatResponse(**result)
