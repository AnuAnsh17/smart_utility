"""The analysis pipeline.

One function, ``run_pipeline(job_id)``, run as a FastAPI background task. It
moves a job through the stages declared in :mod:`app.services.job_service` and
writes the result to disk before the job is marked complete.

Three rules shape everything below:

* **Every number comes from the document or from arithmetic on it.** OCR reads
  text, rules pull fields out of that text, the validator checks them, and the
  tariff module prices units. No stage is permitted to invent a figure, and a
  field that could not be read stays ``None`` and is reported as missing.
* **The job row is committed as each stage is entered.** The SSE bus is
  in-memory, but ``GET /api/v1/bills/{job_id}`` reads SQLite. Without a commit
  per stage, a client that polls instead of streaming would see the job frozen
  at "saving" until the very end.
* **Nothing here is allowed to fail silently into sample data.** A document we
  cannot read is an error the user sees, not a demo result.

The optional agent step is folded into the `extraction` stage rather than
getting a stage of its own, because ``job_service.STAGES`` has no entry for it
and the stage machine is the UI's contract. It is timed and logged under
``[AGENT]`` so it stays visible, and it can only ever *confirm* a value that
already appears in the candidate list OCR produced.
"""

from __future__ import annotations

import json
import logging

from app.config import settings
from app.core.errors import ExtractionFailedError, SmartUtilityError
from app.core.logging import JobLogger
from app.db import session_scope
from app.models import BillAnalysis, ForecastResult
from app.schemas import AnalysisBundle, Provenance
from app.services import (
    agent_service,
    analysis_service,
    extraction_service,
    forecast_service,
    job_service,
    language_service,
    ocr_service,
    storage_service,
    weather_service,
)
from app.validators import bill_validator

log = logging.getLogger("smart_utility.pipeline")


def run_pipeline(job_id: str) -> None:
    """Entry point handed to ``BackgroundTasks``. Never raises."""
    logger = JobLogger(job_id)
    logger.info("[start] analysis pipeline")
    try:
        with session_scope() as session:
            _execute(session, job_id, logger)
    except SmartUtilityError as exc:
        # An expected, explainable failure: bad document, too many pages, a
        # document we could not read. The message is written for the user.
        logger.error(f"[error] {exc.code}: {exc.message}")
        _fail(job_id, logger, exc.code, exc.message)
    except Exception:
        log.exception("pipeline crashed for job %s", job_id)
        _fail(
            job_id,
            logger,
            "internal_error",
            "The analysis could not be completed because of an internal error.",
        )
    else:
        logger.finish("completed")


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def _fail(job_id: str, logger: JobLogger, code: str, message: str) -> None:
    """Record a failure on a *fresh* session.

    The session that hit the error is already rolled back, so the failure has
    to be written on a new one. This runs inside the background task, where an
    exception would be swallowed — hence the belt-and-braces try.
    """
    try:
        with session_scope() as session:
            job_service.set_timings(session, job_id, logger.timings())
            job_service.mark_failed(session, job_id, code=code, message=message)
    except Exception:
        log.exception("could not record failure state for job %s", job_id)
    logger.finish("failed", error=code)


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------


def _goto(session, job_id: str, stage: str, *, status: str | None = None) -> None:
    """Enter a stage and commit, so polling clients see it immediately."""
    job_service.transition(session, job_id, stage, status=status)
    session.commit()


def _dedupe(items: list[str]) -> list[str]:
    """Drop empty and repeated warnings.

    Per-page normalisation notes repeat once per page, so a ten-page bill would
    otherwise emit the same sentence ten times.
    """
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _refresh_missing(bill) -> list[str]:
    """Recompute the missing-field list after a mutating step."""
    missing = [
        name
        for name in extraction_service.TARGET_FIELDS
        if getattr(bill, name, None) in (None, "")
    ]
    bill.missing_fields = missing
    return missing


# ---------------------------------------------------------------------------
# Optional agent disambiguation
# ---------------------------------------------------------------------------


def _apply_agent_fields(bill, suggestion, logger: JobLogger) -> int:
    """Write an accepted suggestion onto the bill. Returns how many landed.

    A field the rules already read is never overwritten, whatever the agent
    says about it — the agent is here to fill gaps, not to revise.
    """
    if suggestion is None:
        return 0

    applied = 0
    for name, payload in suggestion.fields.items():
        if getattr(bill, name, None) is not None:
            continue
        setattr(bill, name, payload.get("value"))
        bill.provenance[name] = Provenance(
            source="agent",
            page=None,
            confidence=float(payload.get("confidence") or 0.0),
            flags=["agent_confirmed"],
        )
        applied += 1

    if suggestion.rejected:
        # Field names and reasons only — never the rejected values, which came
        # out of a document.
        logger.warning(
            f"[AGENT] rejected={len(suggestion.rejected)} "
            f"why={','.join(sorted(set(suggestion.rejected.values())))}"
        )
    if applied:
        logger.info(f"[AGENT] applied={applied} via={suggestion.cli}")
    return applied


def _apply_agent_suggestions(
    bill,
    extraction,
    ocr_text: str,
    logger: JobLogger,
    warnings: list[str],
) -> None:
    """Let the configured agent resolve unresolved fields, if it can.

    Two providers, tried in order of how much they are trusted with. The CLI
    provider is shown candidate strings OCR already found and may only *choose
    between them*. The hosted provider reads the document itself, so it can
    recover a field no rule located — it is the one that sends text off this
    machine, and it is off unless an operator turned it on.

    Both are held to the same rule: a value the agent cannot substantiate is
    dropped rather than applied with a caveat, and a field a rule already read
    is never touched. Neither is a dependency — if both decline, the pipeline
    carries on with what the rules found.
    """
    if not agent_service.is_available():
        return

    requested = [
        name
        for name in bill.missing_fields
        if name in agent_service.SUGGESTIBLE_FIELDS
    ]
    if not requested:
        return

    applied = 0
    try:
        with logger.stage("AGENT", fields=len(requested)):
            # The local chooser first: it costs nothing and sends nothing. It
            # declines outright when the hosted provider is the configured one.
            applied += _apply_agent_fields(
                bill,
                agent_service.suggest(extraction.candidates, requested=requested),
                logger,
            )

            # Whatever is still missing, ask the provider that can read the
            # document. Recomputed rather than assumed, so the second request
            # does not ask for a field the first one just filled.
            remaining = [
                name
                for name in _refresh_missing(bill)
                if name in agent_service.SUGGESTIBLE_FIELDS
            ]
            if remaining and ocr_text.strip():
                applied += _apply_agent_fields(
                    bill,
                    agent_service.suggest_from_text(ocr_text, requested=remaining),
                    logger,
                )
    except Exception:
        log.exception("agent step failed for job")
        warnings.append(
            "The optional assistant step did not finish. Anything read from the "
            "document by the usual rules is unaffected."
        )
        return

    if applied:
        _refresh_missing(bill)


# ---------------------------------------------------------------------------
# The pipeline body
# ---------------------------------------------------------------------------


def _execute(session, job_id: str, logger: JobLogger) -> None:
    """Run every stage. Raises ``SmartUtilityError`` for explainable failures."""
    warnings: list[str] = []

    job = job_service.get_job(session, job_id)
    document = storage_service.load_document(session, job_id)
    path = storage_service.document_path(document)

    # --- preprocessing: render the document once --------------------------
    with logger.stage("PREPROCESS", kind=document.extension.lstrip(".")):
        images = ocr_service.rasterize(path)

    document.page_count = len(images)
    _goto(session, job_id, "preprocessing")

    # --- ocr ---------------------------------------------------------------
    with logger.stage("OCR", pages=len(images)):
        ocr_document = ocr_service.run_ocr_on_images(images)

    # Up to a dozen 300 DPI bitmaps; release them before the text analysis.
    del images

    storage_service.write_processed_text(job_id, ocr_document.text)
    job.ocr_engine = ocr_document.engine
    _goto(session, job_id, "ocr")

    # --- language detection ------------------------------------------------
    with logger.stage("LANGUAGE", chars=len(ocr_document.text)):
        report = language_service.detect(ocr_document.text)

    job.detected_language = report.language
    _goto(session, job_id, "language_detection")

    # --- extraction --------------------------------------------------------
    with logger.stage("EXTRACT", language=report.script):
        normalised_pages = [
            (page.number, language_service.normalise_text(page.text, report)[0])
            for page in ocr_document.pages
        ]
        extraction = extraction_service.extract(normalised_pages, report)

    bill = extraction.bill
    bill.ocr_engine = ocr_document.engine
    bill.ocr_mean_confidence = ocr_document.mean_confidence
    bill.source_file_name = document.original_filename

    # The same text the rules were given, so the agent and the rules are
    # reading one document rather than two transcriptions of one.
    _apply_agent_suggestions(
        bill, extraction, "\n".join(text for _, text in normalised_pages), logger, warnings
    )
    _goto(session, job_id, "extraction")

    # --- normalisation -----------------------------------------------------
    with logger.stage("NORMALISE"):
        bill_validator.normalise(bill)
    _refresh_missing(bill)
    _goto(session, job_id, "normalization")

    # --- validation --------------------------------------------------------
    with logger.stage("VALIDATE"):
        findings = bill_validator.validate(
            bill,
            ocr_mean_confidence=ocr_document.mean_confidence,
            min_confidence=settings.ocr_min_confidence,
        )
        usable, reason = bill_validator.is_usable(bill)

    if not usable:
        # Nothing worth showing. Say so rather than assembling a dashboard of
        # blanks and calling it an analysis.
        log.info("job %s unusable: %s", job_id, reason)
        raise ExtractionFailedError()

    _goto(session, job_id, "validation")

    # --- analysis ----------------------------------------------------------
    # History must be read *before* this job's own row is written, or the job
    # would match itself and contribute its period twice.
    with logger.stage("ANALYSIS", category=bill.tariff_category or "unspecified"):
        history = forecast_service.collect_history(
            session, bill, current_job_id=job_id
        )
    _goto(session, job_id, "analysis")

    # --- weather (optional, degrades) --------------------------------------
    with logger.stage("WEATHER", enabled=settings.weather_enabled):
        weather = weather_service.fetch()

    if settings.weather_enabled and weather.status == "unavailable":
        # Only worth surfacing when the operator asked for weather. With it off
        # by default, warning on every job would read as a permanent fault.
        warnings.append(
            analysis_service.weather_note(weather)
            or "Weather context was unavailable."
        )
    _goto(session, job_id, "weather_enrichment")

    # --- forecast ----------------------------------------------------------
    with logger.stage("FORECAST", periods=len(history)):
        canonical = forecast_service.forecast(history, bill)

    if canonical is None:
        # No history at all for this connection: the forecast is not merely
        # unreliable, it does not exist.
        canonical = analysis_service.placeholder_forecast()

    if not canonical.reliable:
        # Also reachable with one or two periods, where a projection is
        # produced but is a point rather than a trend. The user is told either
        # way; the distinction is carried by `reliable` on the forecast itself.
        warnings.append(
            "Not enough historical data to generate a reliable forecast."
        )

    _goto(session, job_id, "forecast")

    # --- assembling --------------------------------------------------------
    _goto(session, job_id, "assembling")

    with logger.stage("ASSEMBLE", fields=len(bill.provenance)):
        insights = analysis_service.build_insights(bill, canonical, findings)
        recommendations = analysis_service.build_recommendations(bill, canonical)

        bundle = AnalysisBundle(
            job_id=job_id,
            bill=bill,
            forecast=canonical,
            weather=weather,
            insights=insights,
            recommendations=recommendations,
            validation=findings,
            warnings=_dedupe(warnings),
        )

        # Dump once, then derive the sibling keys from the dump. One
        # serialisation, so the API's top-level provenance can never disagree
        # with the provenance inside the bundle.
        payload = bundle.model_dump(mode="json")
        storage_service.write_result(
            job_id,
            {
                "bundle": payload,
                "provenance": payload["bill"]["provenance"],
                "validation": payload["validation"],
                "missing_fields": payload["bill"]["missing_fields"],
            },
        )

        session.add(
            BillAnalysis(
                job_id=job_id,
                document_id=document.id,
                bill_json=json.dumps(payload["bill"], ensure_ascii=False),
                provenance_json=json.dumps(
                    payload["bill"]["provenance"], ensure_ascii=False
                ),
                validation_json=json.dumps(payload["validation"], ensure_ascii=False),
                flags_json=json.dumps(bill.flags, ensure_ascii=False),
                missing_fields_json=json.dumps(
                    bill.missing_fields, ensure_ascii=False
                ),
                detected_language=bill.detected_language,
                ocr_engine=bill.ocr_engine,
                ocr_mean_confidence=bill.ocr_mean_confidence,
            )
        )

        # Only record a forecast that is actually one. The placeholder is a
        # forecast-shaped object, and letting it into this table would corrupt
        # the history the next job reads.
        if canonical.method == forecast_service.METHOD:
            session.add(
                ForecastResult(
                    job_id=job_id,
                    forecast_json=json.dumps(
                        canonical.model_dump(mode="json"), ensure_ascii=False
                    ),
                    method=canonical.method,
                    horizon_months=forecast_service.FORECAST_HORIZON,
                    reliable=1 if canonical.reliable else 0,
                )
            )

    # Timings are read after the block closes so ASSEMBLE is included.
    job_service.set_timings(session, job_id, logger.timings())
    job_service.add_warnings(session, job_id, _dedupe(warnings))
    job_service.transition(session, job_id, "completed", status="completed")
    session.commit()

    logger.info(
        "[done] fields=%d/%d warnings=%d insights=%d reliable=%s"
        % (
            len(extraction_service.TARGET_FIELDS) - len(bill.missing_fields),
            len(extraction_service.TARGET_FIELDS),
            len(_dedupe(warnings)),
            len(insights),
            canonical.reliable,
        )
    )


def describe() -> dict[str, object]:
    return {
        "entrypoint": "run_pipeline(job_id)",
        "stages": list(job_service.STAGES),
        "agent_stage": "folded into extraction",
        "forecast_method": forecast_service.METHOD,
    }
