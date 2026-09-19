"""Domain errors.

Every error carries a stable machine-readable ``code`` and a human-facing
``message``. The message is the only part ever shown to a user, and it must
stay free of file paths, OCR text and personal data.
"""

from __future__ import annotations


class SmartUtilityError(Exception):
    code = "internal_error"
    http_status = 500
    message = "Something went wrong while processing this document."

    def __init__(self, message: str | None = None, *, detail: str | None = None):
        self.message = message or type(self).message
        # Developer-facing only. Never serialised into an API response.
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str]:
        return {"error_code": self.code, "error_message": self.message}


class UnsupportedFileTypeError(SmartUtilityError):
    code = "unsupported_file_type"
    http_status = 415
    message = "Unsupported file type. Upload a PDF, JPG, JPEG, PNG or WEBP file."


class FileTooLargeError(SmartUtilityError):
    code = "file_too_large"
    http_status = 413
    message = "That file is too large. The limit is 10 MB."


class EmptyFileError(SmartUtilityError):
    code = "empty_file"
    http_status = 400
    message = "That file appears to be empty."


class CorruptUploadError(SmartUtilityError):
    code = "corrupt_upload"
    http_status = 400
    message = "Unable to read this document. Try a clearer image or PDF."


class UnreadableDocumentError(SmartUtilityError):
    """OCR produced nothing usable."""

    code = "unreadable_document"
    http_status = 422
    message = "Unable to read this document. Try a clearer image or PDF."


class TooManyPagesError(SmartUtilityError):
    code = "too_many_pages"
    http_status = 413
    message = "This PDF has too many pages to analyse."


class JobNotFoundError(SmartUtilityError):
    code = "job_not_found"
    http_status = 404
    message = "That analysis job does not exist."


class AnalysisNotReadyError(SmartUtilityError):
    code = "analysis_not_ready"
    http_status = 409
    message = "This analysis is still running."


class PathEscapeError(SmartUtilityError):
    code = "path_escape"
    http_status = 400
    message = "Invalid file reference."


class ExtractionFailedError(SmartUtilityError):
    code = "extraction_failed"
    http_status = 422
    message = "Some information could not be extracted."


class InsufficientHistoryError(SmartUtilityError):
    code = "insufficient_history"
    http_status = 422
    message = "Not enough historical data to generate a reliable forecast."
