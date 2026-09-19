"""Job lifecycle, UI-step mapping, and the in-process event bus.

The database is the source of truth for job state; the event bus is a fast
path that lets the dashboard update without polling. If a subscriber misses
an event (page reload, reconnect) it falls back to
``GET /api/v1/bills/{job_id}``, so nothing depends on the bus being reliable.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import JobNotFoundError
from app.models import Job

# Fine-grained backend stages, in execution order.
STAGES: tuple[str, ...] = (
    "queued",
    "saving",
    "preprocessing",
    "ocr",
    "language_detection",
    "extraction",
    "normalization",
    "validation",
    "analysis",
    "weather_enrichment",
    "forecast",
    "assembling",
    "completed",
    "failed",
)

UI_STEPS: tuple[str, ...] = (
    "upload",
    "language",
    "extract",
    "patterns",
    "weather",
    "dashboard",
)

# The frontend's checklist labels are fixed. Backend stages map onto them
# without reordering; the real sub-stage text rides along in `detail`.
STAGE_TO_UI_STEP: dict[str, str] = {
    "queued": "upload",
    "saving": "upload",
    "preprocessing": "language",
    "ocr": "language",
    "language_detection": "language",
    "extraction": "extract",
    "normalization": "extract",
    "validation": "extract",
    "analysis": "patterns",
    "weather_enrichment": "weather",
    "forecast": "dashboard",
    "assembling": "dashboard",
    "completed": "dashboard",
    "failed": "dashboard",
}

STAGE_PROGRESS: dict[str, float] = {
    "queued": 0.02,
    "saving": 0.08,
    "preprocessing": 0.18,
    "ocr": 0.40,
    "language_detection": 0.48,
    "extraction": 0.60,
    "normalization": 0.68,
    "validation": 0.74,
    "analysis": 0.82,
    "weather_enrichment": 0.88,
    "forecast": 0.94,
    "assembling": 0.98,
    "completed": 1.0,
    "failed": 1.0,
}

STAGE_MESSAGES: dict[str, str] = {
    "queued": "Queued for analysis",
    "saving": "Saving your document",
    "preprocessing": "Preparing pages for reading",
    "ocr": "Reading text from the document",
    "language_detection": "Detecting the bill language",
    "extraction": "Extracting bill fields",
    "normalization": "Normalising values",
    "validation": "Checking the numbers add up",
    "analysis": "Analysing consumption patterns",
    "weather_enrichment": "Adding weather context",
    "forecast": "Preparing your forecast",
    "assembling": "Building your dashboard",
    "completed": "Analysis complete",
    "failed": "Analysis could not be completed",
}


def ui_step_index(step: str) -> int:
    try:
        return UI_STEPS.index(step)
    except ValueError:
        return 0


def create_job(session: Session, job_id: str, *, message: str = "") -> Job:
    job = Job(
        id=job_id,
        status="queued",
        stage="queued",
        ui_step="upload",
        progress=STAGE_PROGRESS["queued"],
        message=message or STAGE_MESSAGES["queued"],
        created_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, job_id: str) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise JobNotFoundError()
    return job


def transition(
    session: Session,
    job_id: str,
    stage: str,
    *,
    message: str | None = None,
    progress: float | None = None,
    status: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> Job:
    """Move a job to ``stage`` and persist the change."""
    job = get_job(session, job_id)

    job.stage = stage
    job.ui_step = STAGE_TO_UI_STEP.get(stage, job.ui_step)
    job.progress = progress if progress is not None else STAGE_PROGRESS.get(stage, job.progress)
    job.message = message or STAGE_MESSAGES.get(stage, job.message)
    job.updated_at = datetime.now(timezone.utc)

    if status:
        job.status = status
        if status == "processing" and job.started_at is None:
            job.started_at = job.updated_at
        if status in ("completed", "failed"):
            job.finished_at = job.updated_at

    if error_code:
        job.error_code = error_code
    if error_message:
        job.error_message = error_message

    session.flush()

    event_bus.publish_threadsafe(
        job_id,
        {
            "type": "progress",
            "job_id": job_id,
            "status": job.status,
            "stage": job.stage,
            "ui_step": job.ui_step,
            "ui_step_index": ui_step_index(job.ui_step),
            "progress": job.progress,
            "message": job.message,
            "error_code": job.error_code,
            "error_message": job.error_message,
        },
    )
    return job


def set_timings(session: Session, job_id: str, timings: list[dict[str, Any]]) -> None:
    job = get_job(session, job_id)
    job.timings_json = json.dumps(timings)
    session.flush()


def add_warnings(session: Session, job_id: str, warnings: list[str]) -> None:
    if not warnings:
        return
    job = get_job(session, job_id)
    existing = json.loads(job.warnings_json or "[]")
    for warning in warnings:
        if warning not in existing:
            existing.append(warning)
    job.warnings_json = json.dumps(existing)
    session.flush()


def read_warnings(job: Job) -> list[str]:
    try:
        return json.loads(job.warnings_json or "[]")
    except json.JSONDecodeError:
        return []


def read_timings(job: Job) -> list[dict[str, Any]]:
    # Older rows were inserted with the column default ``"{}"``, so a decode
    # that succeeds can still hand back a dict. The response model wants a
    # list, and an empty list is the honest reading of "no timings recorded".
    try:
        value = json.loads(job.timings_json or "[]")
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def mark_failed(
    session: Session, job_id: str, *, code: str, message: str
) -> Job:
    return transition(
        session,
        job_id,
        "failed",
        status="failed",
        error_code=code,
        error_message=message,
        message=message,
    )


# ---------------------------------------------------------------------------
# Event bus (single-process pub/sub)
# ---------------------------------------------------------------------------

_QUEUE_MAXSIZE = 256


class EventBus:
    """Fan-out of job progress events to any number of live SSE subscribers.

    Single-process by design: this deployment is one uvicorn worker with local
    storage. If that ever changes, replace this with a real broker and keep the
    DB polling fallback as the contract.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._loops: dict[str, asyncio.AbstractEventLoop] = {}
        self._recent: dict[str, deque] = defaultdict(lambda: deque(maxlen=32))

    def bind_loop(self, job_id: str, loop: asyncio.AbstractEventLoop) -> None:
        self._loops[job_id] = loop

    def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._subscribers[job_id].add(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(job_id)
        if subscribers:
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(job_id, None)

    def publish(self, job_id: str, event: dict[str, Any]) -> None:
        """Publish from within the event loop."""
        self._recent[job_id].append(event)
        for queue in list(self._subscribers.get(job_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # A stalled subscriber must not block the pipeline; it will
                # recover via the polling fallback.
                pass

    def publish_threadsafe(self, job_id: str, event: dict[str, Any]) -> None:
        """Publish from a worker thread or a threadpool-run background task."""
        loop = self._loops.get(job_id)
        if loop is None or loop.is_closed():
            # No live stream for this job (e.g. a synchronous test run); the
            # row is already committed, so polling still sees the update.
            self._recent[job_id].append(event)
            return
        try:
            loop.call_soon_threadsafe(self.publish, job_id, event)
        except RuntimeError:
            self._recent[job_id].append(event)

    def replay(self, job_id: str) -> list[dict[str, Any]]:
        return list(self._recent.get(job_id, ()))

    def clear(self, job_id: str) -> None:
        self._recent.pop(job_id, None)
        self._loops.pop(job_id, None)


event_bus = EventBus()


async def stream_events(job_id: str) -> AsyncIterator[dict[str, Any]]:
    """Yield progress events for a job until it reaches a terminal state."""
    queue = event_bus.subscribe(job_id)
    try:
        for past in event_bus.replay(job_id):
            yield past
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # Keep-alive: lets the client distinguish "still working" from
                # "connection dropped" without hammering the API.
                yield {"type": "heartbeat", "job_id": job_id}
                continue
            yield event
            if event.get("status") in ("completed", "failed"):
                return
    finally:
        event_bus.unsubscribe(job_id, queue)


def recent_jobs(session: Session, limit: int = 20) -> list[Job]:
    return list(
        session.execute(select(Job).order_by(Job.created_at.desc()).limit(limit))
        .scalars()
        .all()
    )
