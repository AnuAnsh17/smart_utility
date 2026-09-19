"""Upload validation and filesystem containment.

Two rules drive everything here:

* Never trust a filename, an extension, or a client-supplied content type.
  Decide what a file is from its magic bytes.
* Never build a path from user input without re-confining it to the storage
  root afterwards.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.core.errors import (
    EmptyFileError,
    FileTooLargeError,
    PathEscapeError,
    UnsupportedFileTypeError,
)

ALLOWED_EXTENSIONS: dict[str, str] = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

# Extension implied by the sniffed content type. Used when a client sends a
# mismatched or missing extension.
MIME_TO_EXTENSION: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_STEM = 80


def sniff_mime(head: bytes) -> str | None:
    """Identify a file from its leading bytes. Returns None if unrecognised."""
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    # WEBP is a RIFF container: "RIFF" <4-byte size> "WEBP"
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def sanitize_filename(raw: str | None) -> tuple[str, str]:
    """Return ``(safe_name, extension)`` for an untrusted filename.

    Directory components are discarded, unicode is folded to ASCII, and any
    character outside ``[A-Za-z0-9._-]`` becomes an underscore.
    """
    candidate = (raw or "").strip()

    # Drop any path the client tried to smuggle in, on either separator.
    candidate = candidate.replace("\\", "/").split("/")[-1]

    # Strip control characters and normalise unicode before filtering.
    candidate = "".join(ch for ch in candidate if ch.isprintable())
    candidate = unicodedata.normalize("NFKD", candidate)
    candidate = candidate.encode("ascii", "ignore").decode("ascii")

    stem, dot, ext = candidate.rpartition(".")
    if not dot:
        stem, ext = candidate, ""

    stem = _UNSAFE_CHARS.sub("_", stem).strip("._-") or "document"
    stem = stem[:_MAX_STEM]
    ext = ext.lower().strip()

    if ext and ext not in ALLOWED_EXTENSIONS:
        # Unknown extension: keep the stem and let the sniffer decide.
        ext = ""

    return (f"{stem}.{ext}" if ext else stem), ext


def validate_upload(raw_filename: str | None, data: bytes, max_bytes: int) -> tuple[str, str]:
    """Validate an upload and return ``(safe_filename, mime_type)``.

    Raises a domain error for anything rejected, so the API layer can map it
    to a status code without inspecting the reason itself.
    """
    if not data:
        raise EmptyFileError()
    if len(data) > max_bytes:
        raise FileTooLargeError()

    sniffed = sniff_mime(data[:32])
    if sniffed is None:
        raise UnsupportedFileTypeError()

    safe_name, ext = sanitize_filename(raw_filename)

    # The declared extension must not contradict the sniffed content. If the
    # client lied (or sent no extension at all) we trust the bytes and correct
    # the extension rather than rejecting outright.
    expected_ext = MIME_TO_EXTENSION[sniffed]
    if ext and ext != expected_ext and not (ext == "jpeg" and expected_ext == "jpg"):
        stem = safe_name.rsplit(".", 1)[0] if "." in safe_name else safe_name
        safe_name = f"{stem}.{expected_ext}"
    elif not ext:
        safe_name = f"{safe_name}.{expected_ext}"

    return safe_name, sniffed


def resolve_within(base: Path, *parts: str) -> Path:
    """Join ``parts`` onto ``base`` and refuse anything that escapes it."""
    base = base.resolve()
    candidate = base.joinpath(*parts).resolve()
    if candidate != base and base not in candidate.parents:
        raise PathEscapeError()
    return candidate


def is_within(base: Path, target: Path) -> bool:
    base = base.resolve()
    target = target.resolve()
    return target == base or base in target.parents


def redact_consumer_number(value: str | None) -> str:
    """Mask all but the last four characters of an identifier."""
    if not value:
        return ""
    cleaned = str(value).strip()
    if len(cleaned) <= 4:
        return "*" * len(cleaned)
    return "*" * (len(cleaned) - 4) + cleaned[-4:]
