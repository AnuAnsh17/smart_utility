"""Job-scoped logging with redaction.

What we log: job id, stage, durations, counts, error codes.
What we never log: OCR text, consumer numbers, addresses, phone numbers,
emails, document images, raw extracted values.

``RedactingFilter`` is a backstop on top of that: if a long digit run or a
PII-shaped string ever reaches a log record, it is masked before it is
written. It is not a licence to log sensitive data — it is a second line of
defence for the first one being forgotten.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings

_CONFIGURED = False

# Consumer numbers, account numbers, meter serials: 6+ consecutive digits.
_LONG_DIGITS = re.compile(r"\b\d{6,}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Indian mobile numbers, with or without +91 / 0 prefix and spaces.
_PHONE = re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b")


class RedactingFilter(logging.Filter):
    """Mask PII-shaped substrings anywhere in a log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not settings.log_redact:
            return True
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _redact_text(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def _redact_text(text: str) -> str:
    text = _EMAIL.sub("[redacted-email]", text)
    text = _PHONE.sub("[redacted-phone]", text)
    text = _LONG_DIGITS.sub("[redacted-id]", text)
    return text


def redact(value: object) -> str:
    """Public helper for building log messages from possibly-sensitive values."""
    return _redact_text(str(value))


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings.ensure_directories()

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redactor = RedactingFilter()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    stream.addFilter(redactor)

    handlers: list[logging.Handler] = [stream]
    try:
        file_handler = logging.FileHandler(settings.log_dir / "backend.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redactor)
        handlers.append(file_handler)
    except OSError:
        # A read-only data dir must not stop the service from starting.
        pass

    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    for handler in handlers:
        root.addHandler(handler)

    # uvicorn's access log prints full query strings; keep it but at WARNING.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _CONFIGURED = True


class JobLogger:
    """Accumulates per-stage timings for a single job and formats them.

    Typical output for one document::

        [JOB 3f9a1c] [start] bill.pdf (412 KB)
        [JOB 3f9a1c] [ocr] 1.82s pages=1 conf=91.2 lang=eng
        [JOB 3f9a1c] [extract] 0.11s fields=9/12
        [JOB 3f9a1c] [total] 4.48s status=completed
    """

    def __init__(self, job_id: str, logger: logging.Logger | None = None):
        self.job_id = job_id
        self._log = logger or logging.getLogger("smart_utility.pipeline")
        self._started = time.perf_counter()
        self._stages: dict[str, float] = {}
        self._order: list[str] = []
        self._open: dict[str, float] = {}

    def _prefix(self) -> str:
        return f"[JOB {self.job_id}]"

    def info(self, message: str) -> None:
        self._log.info("%s %s", self._prefix(), message)

    def warning(self, message: str) -> None:
        self._log.warning("%s %s", self._prefix(), message)

    def error(self, message: str) -> None:
        self._log.error("%s %s", self._prefix(), message)

    @contextmanager
    def stage(self, name: str, **fields: object):
        """Time a stage and emit one line when it finishes, even on failure."""
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - started
            self.record(name, elapsed)
            suffix = " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
            line = f"[{name}] {elapsed:.2f}s"
            if suffix:
                line = f"{line} {suffix}"
            self.info(line)

    def record(self, name: str, seconds: float) -> None:
        if name not in self._stages:
            self._order.append(name)
        self._stages[name] = self._stages.get(name, 0.0) + seconds

    @property
    def total_seconds(self) -> float:
        return time.perf_counter() - self._started

    def timings(self) -> list[dict[str, object]]:
        return [
            {"stage": name, "duration_ms": int(self._stages[name] * 1000)}
            for name in self._order
        ]

    def finish(self, status: str, **fields: object) -> None:
        suffix = " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
        line = f"[total] {self.total_seconds:.2f}s status={status}"
        if suffix:
            line = f"{line} {suffix}"
        self.info(line)


def stage_summary(timings: Iterable[dict[str, object]]) -> str:
    parts = [f"{t['stage']}={int(t['duration_ms']) / 1000:.2f}s" for t in timings]
    return " ".join(parts)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
