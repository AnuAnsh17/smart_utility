"""Local document storage.

The original upload is written once and never modified. Every path is derived
from the job id, which we generate — never from anything the client sent — and
is re-confined to the data directory before use.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import JobNotFoundError, PathEscapeError
from app.core.security import is_within, resolve_within, sanitize_filename
from app.models import Document, Job


def new_job_id() -> str:
    return uuid.uuid4().hex[:16]


def new_document_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass(frozen=True)
class StoredDocument:
    document_id: str
    job_id: str
    path: Path
    safe_filename: str
    original_filename: str
    mime_type: str
    extension: str
    size_bytes: int
    sha256: str


def job_dir(job_id: str) -> Path:
    """Return ``data/uploads/<job_id>/``, creating it if needed."""
    path = resolve_within(settings.uploads_dir, job_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def processed_dir(job_id: str) -> Path:
    path = resolve_within(settings.processed_dir, job_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def results_path(job_id: str) -> Path:
    return resolve_within(settings.results_dir, f"{job_id}.json")


def save_upload(
    session: Session,
    *,
    job_id: str,
    raw_filename: str | None,
    data: bytes,
    mime_type: str,
    safe_filename: str,
) -> StoredDocument:
    """Persist the original bytes and record a ``documents`` row."""
    directory = job_dir(job_id)
    destination = resolve_within(directory, safe_filename)
    if not is_within(settings.uploads_dir, destination):
        raise PathEscapeError()

    # Written with O_EXCL semantics via a temp name so a re-run for the same
    # job id can never clobber an existing original.
    if destination.exists():
        stem = destination.stem
        ext = destination.suffix
        destination = resolve_within(directory, f"{stem}-{uuid.uuid4().hex[:6]}{ext}")

    tmp = destination.with_suffix(destination.suffix + ".part")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(destination)

    digest = hashlib.sha256(data).hexdigest()
    document_id = new_document_id()

    record = Document(
        id=document_id,
        job_id=job_id,
        original_filename=(raw_filename or safe_filename)[:255],
        safe_filename=destination.name,
        stored_path=str(destination),
        sha256=digest,
        mime_type=mime_type,
        extension=destination.suffix.lstrip(".").lower(),
        size_bytes=len(data),
    )
    session.add(record)
    session.flush()

    return StoredDocument(
        document_id=document_id,
        job_id=job_id,
        path=destination,
        safe_filename=destination.name,
        original_filename=record.original_filename,
        mime_type=mime_type,
        extension=record.extension,
        size_bytes=len(data),
        sha256=digest,
    )


def load_document(session: Session, job_id: str) -> Document:
    document = session.execute(
        select(Document).where(Document.job_id == job_id).order_by(Document.created_at.desc())
    ).scalars().first()
    if document is None:
        raise JobNotFoundError()
    return document


def document_path(document: Document) -> Path:
    """Resolve a stored document path, refusing anything outside the root."""
    path = Path(document.stored_path).resolve()
    if not is_within(settings.uploads_dir, path):
        raise PathEscapeError()
    if not path.exists():
        raise JobNotFoundError("The stored document for this job is missing.")
    return path


def write_result(job_id: str, payload: dict[str, Any]) -> Path:
    """Persist the structured analysis result beside the processed artefacts."""
    path = results_path(job_id)
    tmp = path.with_suffix(".json.part")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    tmp.replace(path)
    return path


def read_result(job_id: str) -> dict[str, Any] | None:
    path = results_path(job_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def write_processed_text(job_id: str, text: str, *, name: str = "ocr.txt") -> Path:
    """Store derived OCR text. Never the original image."""
    path = resolve_within(processed_dir(job_id), f"{Path(name).stem}.txt")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def delete_job_artifacts(job_id: str) -> None:
    """Remove a job's stored files. Used by tests and explicit cleanup only."""
    import shutil

    for base in (settings.uploads_dir, settings.processed_dir):
        target = (base / job_id).resolve()
        if is_within(base, target) and target.exists():
            shutil.rmtree(target, ignore_errors=True)
    result = results_path(job_id)
    if result.exists():
        result.unlink(missing_ok=True)


def find_job(session: Session, job_id: str) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise JobNotFoundError()
    return job


def normalized_name(raw: str | None) -> str:
    """Best-effort readable name for display, never used for paths."""
    safe, _ = sanitize_filename(raw)
    return safe
