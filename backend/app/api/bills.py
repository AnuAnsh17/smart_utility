"""Bill upload, job status, and the progress event stream."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.errors import FileTooLargeError, SmartUtilityError
from app.core.logging import JobLogger, redact
from app.core.security import validate_upload
from app.config import settings
from app.db import get_session
from app.schemas import (
    AnalysisResponse,
    DocumentListResponse,
    DocumentSummary,
    JobStatusResponse,
    UploadAcceptedResponse,
    to_frontend_analysis,
)
from app.services import job_service, storage_service
from app.services.job_service import event_bus
from app.workers import pipeline

router = APIRouter(prefix="/api/v1/bills", tags=["bills"])
log = logging.getLogger("smart_utility.api")


async def _read_capped(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an upload, aborting as soon as it exceeds the cap.

    Reading the whole body first would let a client exhaust memory before the
    size check ever runs.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLargeError()
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/upload", response_model=UploadAcceptedResponse, status_code=202)
async def upload_bill(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> UploadAcceptedResponse:
    data = await _read_capped(file, settings.max_upload_bytes)
    safe_name, mime_type = validate_upload(file.filename, data, settings.max_upload_bytes)

    job_id = storage_service.new_job_id()
    job_log = JobLogger(job_id)
    job_log.info(f"[upload] received {safe_name} {len(data)} bytes")

    document = storage_service.save_upload(
        session,
        job_id=job_id,
        raw_filename=file.filename,
        data=data,
        mime_type=mime_type,
        safe_filename=safe_name,
    )
    job_service.create_job(session, job_id)
    job_service.transition(
        session, job_id, "saving", status="processing",
        message="Saving your document",
    )
    session.commit()

    # Give the pipeline a way to push live progress to any SSE subscriber.
    try:
        event_bus.bind_loop(job_id, asyncio.get_running_loop())
    except RuntimeError:
        pass

    background.add_task(pipeline.run_pipeline, job_id)

    return UploadAcceptedResponse(
        job_id=job_id,
        document_id=document.document_id,
        file_name=document.safe_filename,
        size_bytes=document.size_bytes,
        status="queued",
        events_url=f"/api/v1/bills/{job_id}/events",
        status_url=f"/api/v1/bills/{job_id}",
    )


def _decode_bill_json(value: object) -> dict:
    """Read a persisted ``bill_json`` column, tolerating either encoding."""
    if not value:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


@router.get("", response_model=DocumentListResponse)
def list_documents(
    session: Session = Depends(get_session),
    limit: int = 50,
) -> DocumentListResponse:
    """The local library of uploaded bills, newest first.

    Joins through to the job so a document that failed before extraction still
    appears, carrying its real status and error rather than disappearing.
    Extracted figures are read back out of ``BillAnalysis.bill_json``; a row
    that cannot be decoded simply contributes nulls.
    """
    from app.models import BillAnalysis, Document, Job

    capped = max(1, min(limit, 200))
    rows = (
        session.query(Document, Job, BillAnalysis)
        .outerjoin(Job, Job.id == Document.job_id)
        .outerjoin(BillAnalysis, BillAnalysis.job_id == Document.job_id)
        .order_by(Document.created_at.desc())
        .limit(capped)
        .all()
    )

    documents: list[DocumentSummary] = []
    for document, job, analysis in rows:
        stored = _decode_bill_json(analysis.bill_json) if analysis else {}
        documents.append(
            DocumentSummary(
                id=document.id,
                job_id=document.job_id,
                file_name=document.safe_filename or document.original_filename,
                provider=stored.get("provider"),
                billing_period=stored.get("billing_period"),
                units=stored.get("units_consumed"),
                amount=stored.get("total_amount"),
                unit_label=stored.get("unit_label") or "kWh",
                currency_symbol=stored.get("currency_symbol") or "₹",
                status=(job.status if job else "queued"),  # type: ignore[arg-type]
                uploaded_at=document.created_at,
                size_bytes=document.size_bytes,
                detected_language=(job.detected_language if job else None),
                error_message=(job.error_message if job else None),
            )
        )

    return DocumentListResponse(documents=documents, total=len(documents))


def _status_payload(job) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,  # type: ignore[arg-type]
        stage=job.stage,
        ui_step=job.ui_step,  # type: ignore[arg-type]
        ui_step_index=job_service.ui_step_index(job.ui_step),
        progress=job.progress,
        message=job.message,
        error_code=job.error_code,
        error_message=job.error_message,
        warnings=job_service.read_warnings(job),
        timings=job_service.read_timings(job),  # type: ignore[arg-type]
        created_at=job.created_at,
        updated_at=job.updated_at,
        finished_at=job.finished_at,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str, session: Session = Depends(get_session)
) -> JobStatusResponse:
    return _status_payload(job_service.get_job(session, job_id))


@router.get("/{job_id}/analysis", response_model=AnalysisResponse)
def get_job_analysis(
    job_id: str, session: Session = Depends(get_session)
) -> AnalysisResponse:
    """Return the full structured analysis for a completed job."""
    job = job_service.get_job(session, job_id)
    if job.status != "completed":
        raise SmartUtilityError(
            job.error_message or "This analysis is still running.",
            detail=f"status={job.status}",
        )

    stored = storage_service.read_result(job_id)
    if not stored:
        raise SmartUtilityError("The analysis result for this job is missing.")

    from app.schemas import AnalysisBundle

    bundle = AnalysisBundle.model_validate(stored["bundle"])
    analysis = to_frontend_analysis(bundle)

    return AnalysisResponse(
        job_id=job_id,
        status=job.status,  # type: ignore[arg-type]
        stage=job.stage,
        ui_step=job.ui_step,  # type: ignore[arg-type]
        progress=job.progress,
        message=job.message,
        warnings=job_service.read_warnings(job),
        timings=job_service.read_timings(job),  # type: ignore[arg-type]
        analysis=analysis,
        provenance=stored.get("provenance", {}),
        validation=stored.get("validation", []),
        missing_fields=stored.get("missing_fields", []),
        detected_language=bundle.bill.detected_language,
        ocr_engine=bundle.bill.ocr_engine,
        ocr_mean_confidence=bundle.bill.ocr_mean_confidence,
    )


@router.get("/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Server-sent progress events, with heartbeats while work continues."""

    async def generator():
        try:
            async for event in job_service.stream_events(job_id):
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/debug/ocr")
def get_ocr_preview(
    job_id: str, session: Session = Depends(get_session)
) -> dict[str, object]:
    """Developer helper: character count and detected language, never the text.

    OCR text can contain a consumer's name, address and account number, so it
    is not exposed over HTTP even in a local deployment.
    """
    job = job_service.get_job(session, job_id)
    stored = storage_service.read_result(job_id) or {}
    text_path = settings.processed_dir / job_id / "ocr.txt"
    return {
        "job_id": job_id,
        "detected_language": job.detected_language,
        "ocr_engine": job.ocr_engine,
        "text_available": text_path.exists(),
        "text_char_count": len(text_path.read_text(encoding="utf-8")) if text_path.exists() else 0,
        "stage": job.stage,
        "status": job.status,
        "model_hint": redact(stored.get("model_hint", "")),
    }
