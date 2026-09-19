"""Normalisation and validation of the canonical bill.

Two rules govern this module, both from the specification:

* **Never invent a missing value.** A field with no evidence stays ``None``.
* **Never silently correct a suspicious value.** If the numbers do not add up,
  the value is left exactly as read and a finding is attached. The user decides
  what to do about it.

Normalisation only changes *presentation* — whitespace, case, a trailing ".0"
on a whole-number reading. It never changes a magnitude.
"""

from __future__ import annotations

import logging
import re

from app.schemas import CanonicalBill, ValidationFinding

log = logging.getLogger("smart_utility.validator")

# A domestic Indian tariff sits broadly in this band. Outside it, something was
# probably misread, but we still do not touch the number.
RATE_PER_KWH_BAND = (0.5, 40.0)

CONSUMER_NUMBER_BAND = (6, 20)
MAX_READING = 100_000_000


def normalise(bill: CanonicalBill) -> list[str]:
    """Tidy presentation. Returns notes about what was touched."""
    notes: list[str] = []

    for name in ("provider", "meter_type", "tariff_category", "connection_type"):
        value = getattr(bill, name)
        if isinstance(value, str):
            cleaned = re.sub(r"\s+", " ", value).strip(" -:.\t")
            if cleaned and cleaned != value:
                notes.append(f"{name} whitespace normalised")
            setattr(bill, name, cleaned or None)

    if bill.consumer_number:
        cleaned = re.sub(r"\s+", "", bill.consumer_number).upper()
        if cleaned != bill.consumer_number:
            notes.append("consumer number normalised")
        bill.consumer_number = cleaned

    if bill.sanctioned_load:
        bill.sanctioned_load = re.sub(r"\s+", " ", bill.sanctioned_load).strip()

    # A reading written as "1234.00" is an integer reading.
    for name in ("previous_reading", "current_reading"):
        value = getattr(bill, name)
        if isinstance(value, float) and value.is_integer():
            setattr(bill, name, float(int(value)))

    if isinstance(bill.units_consumed, float):
        bill.units_consumed = round(bill.units_consumed, 2)

    if isinstance(bill.total_amount, float):
        bill.total_amount = round(bill.total_amount, 2)

    bill.unit_label = bill.unit_label or "kWh"
    bill.currency_symbol = bill.currency_symbol or "₹"
    return notes


def _finding(
    code: str,
    severity: str,
    message: str,
    field_name: str | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        code=code, severity=severity, field=field_name, message=message
    )  # type: ignore[arg-type]


def validate(
    bill: CanonicalBill,
    *,
    ocr_mean_confidence: float | None = None,
    min_confidence: float = 40.0,
) -> list[ValidationFinding]:
    """Cross-check the extracted values. Findings, never mutations."""
    findings: list[ValidationFinding] = []

    previous = bill.previous_reading
    current = bill.current_reading
    units = bill.units_consumed
    amount = bill.total_amount

    # --- readings ----------------------------------------------------------
    for name, value in (("previous_reading", previous), ("current_reading", current)):
        if value is None:
            continue
        if value < 0:
            findings.append(
                _finding(
                    "negative_reading",
                    "error",
                    f"{name.replace('_', ' ')} is negative ({value:g}).",
                    name,
                )
            )
        elif value > MAX_READING:
            findings.append(
                _finding(
                    "implausible_reading",
                    "warning",
                    f"{name.replace('_', ' ')} looks too large ({value:g}).",
                    name,
                )
            )

    if previous is not None and current is not None and current < previous:
        findings.append(
            _finding(
                "reading_regression",
                "warning",
                "Current reading is lower than the previous reading. This can "
                "happen after a meter replacement, but the units figure should "
                "be checked against the bill.",
                "current_reading",
            )
        )

    if previous is not None and current is not None and units is not None:
        expected = current - previous
        if expected > 0:
            drift = abs(expected - units) / expected
            if drift > 0.02:
                findings.append(
                    _finding(
                        "reading_mismatch",
                        "warning",
                        f"Readings differ by {expected:g} but the bill states "
                        f"{units:g} units. The bill's own figure has been kept.",
                        "units_consumed",
                    )
                )

    # --- units -------------------------------------------------------------
    if units is not None:
        if units <= 0:
            findings.append(
                _finding(
                    "non_positive_units",
                    "error",
                    f"Units consumed is {units:g}. A consumption figure should be "
                    "greater than zero.",
                    "units_consumed",
                )
            )
        elif units > 100_000:
            findings.append(
                _finding(
                    "implausible_units",
                    "warning",
                    f"{units:g} units is unusually high for a single billing "
                    "period. Confirm the reading was captured in full.",
                    "units_consumed",
                )
            )

    # --- amount ------------------------------------------------------------
    if amount is not None:
        if amount <= 0:
            findings.append(
                _finding(
                    "non_positive_amount",
                    "error",
                    f"Total amount is {amount:g}.",
                    "total_amount",
                )
            )
        if units and units > 0 and amount > 0:
            rate = amount / units
            low, high = RATE_PER_KWH_BAND
            if not (low <= rate <= high):
                findings.append(
                    _finding(
                        "implied_rate_out_of_band",
                        "warning",
                        f"The bill implies ₹{rate:.2f} per unit, which is outside "
                        "the usual range. One of the two figures may have been "
                        "read incorrectly.",
                        "total_amount",
                    )
                )

    # --- dates -------------------------------------------------------------
    bill_date = _parse_display_date(bill.bill_date)
    due_date = _parse_display_date(bill.due_date)

    if bill.bill_date and bill_date is None:
        findings.append(
            _finding("unparsed_date", "info", f"Bill date '{bill.bill_date}' could not be interpreted.", "bill_date")
        )
    if bill.due_date and due_date is None:
        findings.append(
            _finding("unparsed_date", "info", f"Due date '{bill.due_date}' could not be interpreted.", "due_date")
        )
    if bill_date and due_date and due_date < bill_date:
        findings.append(
            _finding(
                "due_before_bill",
                "warning",
                "The due date falls before the bill date, so at least one was "
                "read incorrectly.",
                "due_date",
            )
        )

    # --- identifiers -------------------------------------------------------
    if bill.consumer_number:
        length = len(bill.consumer_number)
        low, high = CONSUMER_NUMBER_BAND
        if not (low <= length <= high):
            findings.append(
                _finding(
                    "consumer_number_length",
                    "info",
                    f"Consumer number is {length} characters, which is unusual.",
                    "consumer_number",
                )
            )
    else:
        findings.append(
            _finding(
                "consumer_number_missing",
                "info",
                "No consumer number was found on the document.",
                "consumer_number",
            )
        )

    # --- document quality --------------------------------------------------
    if ocr_mean_confidence is not None and ocr_mean_confidence < min_confidence:
        findings.append(
            _finding(
                "low_ocr_confidence",
                "warning",
                f"Text recognition confidence was low ({ocr_mean_confidence:.0f}%). "
                "Extracted values may be inaccurate.",
            )
        )

    if bill.address_present:
        findings.append(
            _finding(
                "address_present",
                "info",
                "The document contains a service address. It is stored with the "
                "document and is not used in analysis.",
            )
        )

    return findings


def is_usable(bill: CanonicalBill) -> tuple[bool, str]:
    """Decide whether enough was read to analyse at all.

    We require at least one of the two figures the whole dashboard depends on.
    A document with neither has not been read successfully, and we say so
    rather than showing an empty dashboard.
    """
    if bill.units_consumed is None and bill.total_amount is None:
        return False, "neither consumption nor amount could be read"
    return True, ""


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_display_date(value: str | None) -> tuple[int, int, int] | None:
    """Parse the display date formats the extractor emits into a sortable tuple."""
    if not value:
        return None
    match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", value.strip())
    if match:
        day, month, year = (int(part) for part in match.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return (year, month, day)
    match = re.fullmatch(r"(\d{2})\s+([A-Za-z]{3})\s+(\d{4})", value.strip())
    if match:
        day, month_name, year = match.groups()
        month = _MONTHS.get(month_name.lower())
        if month:
            return (int(year), month, int(day))
    match = re.fullmatch(r"([A-Za-z]{3})\s+(\d{4})", value.strip())
    if match:
        month_name, year = match.groups()
        month = _MONTHS.get(month_name.lower())
        if month:
            return (int(year), month, 1)
    return None
