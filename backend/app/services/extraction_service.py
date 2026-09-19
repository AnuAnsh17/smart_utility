"""Hybrid bill-field extraction.

Order of operations, cheapest first:

1. **Anchor** — find a known label ("Total Amount", "बिल अवधि", "Units
   Consumed") in the normalised page text.
2. **Read** — pull candidate values out of the label's neighbourhood with
   deterministic patterns, and collect *every* candidate rather than the first
   one, so a later stage can arbitrate.
3. **Arbitrate** — rank candidates by how well anchored they are, whether they
   sit in a plausible range for that field, and whether the numbers are
   mutually consistent (previous + units == current).
4. **Ask the agent** — only if configured, only for fields still ambiguous, and
   only choosing from the candidate list assembled in step 2.

Nothing in this module fabricates a value. If no candidate survives, the field
stays ``None`` and is reported in ``missing_fields``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.schemas import CanonicalBill, Provenance
from app.services.language_service import LanguageReport, tidy_numbers

log = logging.getLogger("smart_utility.extraction")

NUM = r"\d[\d,]*(?:\.\d+)?"

# Plausibility envelopes. Deliberately wide — these exist to reject a date or a
# meter serial being mistaken for a reading, not to police real bills.
RANGES: dict[str, tuple[float, float]] = {
    "units_consumed": (1, 500_000),
    "total_amount": (1, 50_000_000),
    "previous_reading": (0, 100_000_000),
    "current_reading": (0, 100_000_000),
}

LABELS: dict[str, tuple[str, ...]] = {
    "consumer_number": (
        r"consumer\s*(?:no|number|id|code|account)",
        r"consumer\s*number",
        r"ca\s*no",
        r"account\s*(?:no|number)",
        r"customer\s*(?:no|number|id)",
        r"connection\s*(?:no|number)",
        r"service\s*(?:no|number)",
        r"ग्राहक\s*(?:क्रमांक|संख्या|नंबर)",
        r"उपभोक्ता\s*(?:संख्या|क्रमांक)",
    ),
    "meter_number": (
        r"meter\s*(?:no|number|sr|serial)",
        r"मीटर\s*(?:क्रमांक|नंबर)",
    ),
    "billing_period": (
        r"billing\s*period",
        r"bill\s*period",
        r"period\s*of\s*bill",
        r"बिल\s*अवधि",
        r"बिलिंग\s*अवधि",
    ),
    "bill_date": (
        r"bill\s*(?:date|dt)",
        r"invoice\s*date",
        r"issue\s*date",
        r"date\s*of\s*bill",
        r"बिल\s*दिनांक",
    ),
    "due_date": (
        r"due\s*(?:date|dt)",
        r"last\s*date\s*(?:of\s*payment|for\s*payment)?",
        r"pay(?:ment)?\s*by",
        r"payment\s*due",
        r"देय\s*दिनांक",
        r"अंतिम\s*तिथि",
    ),
    "previous_reading": (
        r"previous\s*reading",
        r"prev(?:ious)?\.?\s*rdg",
        r"last\s*reading",
        r"पिछली\s*रीडिंग",
    ),
    "current_reading": (
        r"current\s*reading",
        r"present\s*reading",
        r"curr\.?\s*rdg",
        r"वर्तमान\s*रीडिंग",
    ),
    "units_consumed": (
        r"(?:total\s*)?units?\s*(?:consumed|billed|used)?",
        r"(?:billed|consumption)\s*units?",
        r"energy\s*(?:consumed|charges?\s*units?)",
        r"consumption",
        r"kwh\s*(?:consumed|used|units)?",
        r"इकाई|युनिट",
        r"वापर",
    ),
    "total_amount": (
        r"total\s*(?:amount\s*)?(?:payable|due|amount)",
        r"grand\s*total",
        r"net\s*(?:amount|payable)",
        r"amount\s*(?:payable|due|after\s*due\s*date)",
        r"bill\s*amount",
        r"current\s*bill\s*amount",
        r"payable\s*amount",
        r"कुल\s*(?:राशि|रक्कम)",
        r"देय\s*रक्कम",
    ),
    "sanctioned_load": (
        r"sanctioned\s*load",
        r"connected\s*load",
        r"contract(?:ed)?\s*(?:load|demand)",
        r"स्वीकृत\s*भार",
    ),
    "tariff_category": (
        r"tariff\s*(?:category|code|type)?",
        r"category",
        r"श्रेणी",
    ),
}

DATE_PATTERNS = (
    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}",
    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}",
    r"\d{1,2}[\s-](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s-]\d{2,4}",
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s-]\d{4}",
    r"\d{4}-\d{2}-\d{2}",
)

MONTHS = {
    "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May",
    "jun": "Jun", "jul": "Jul", "aug": "Aug", "sep": "Sep", "oct": "Oct",
    "nov": "Nov", "dec": "Dec",
}

# Indian distribution utilities. Matching a known name beats guessing from
# "Electricity" alone, which appears on almost every bill.
KNOWN_PROVIDERS = (
    "TATA POWER", "ADANI ELECTRICITY", "ADANI POWER", "BSES RAJDHANI",
    "BSES YAMUNA", "BESCOM", "MESCOM", "HESCOM", "GESCOM", "CESC", "MSEDCL",
    "MAHADISCOM", "MAHARASHTRA STATE ELECTRICITY", "TORRENT POWER",
    "KARNATAKA POWER", "TAMIL NADU GENERATION", "TANGEDCO", "TNEB",
    "ANDHRA PRADESH SOUTHERN", "SOUTHERN POWER DISTRIBUTION", "TELANGANA STATE",
    "KERALA STATE ELECTRICITY", "KSEB", "GUJARAT URJA", "UGVCL", "DGVCL",
    "MGVCL", "PGVCL", "MADHYA PRADESH MADHYA KSHETRA", "MPPKVVCL",
    "UTTAR PRADESH POWER", "PASCHIMANCHAL VIDYUT", "PURVANCHAL VIDYUT",
    "DAKSHINANCHAL VIDYUT", "NORTH BIHAR POWER", "SOUTH BIHAR POWER",
    "WEST BENGAL STATE ELECTRICITY", "WBSEDCL", "PUNJAB STATE POWER",
    "HARYANA VIDYUT", "UTTARAKHAND POWER", "RAJASTHAN", "JVVNL", "AVVNL",
    "JODHPUR VIDYUT", "JAIPUR VIDYUT", "GOA ELECTRICITY", "CHHATTISGARH STATE",
    "ODISHA POWER", "TPCODL", "TPNODL", "TPWODL", "TPSODL", "ASSAM POWER",
    "RELIANCE ENERGY", "DAMODAR VALLEY", "NTPC", "BSES", "STATE ELECTRICITY",
    "VIDYUT VITRAN", "ELECTRICITY SUPPLY", "POWER DISTRIBUTION",
)

TARIFF_KEYWORDS = {
    "residential": "Residential (LT-I)",
    "domestic": "Residential (LT-I)",
    "lt-i ": "Residential (LT-I)",
    "lt-1": "Residential (LT-I)",
    "commercial": "Commercial (LT-II)",
    "lt-ii": "Commercial (LT-II)",
    "lt-2": "Commercial (LT-II)",
    "industrial": "Industrial (LT-III)",
    "lt-iii": "Industrial (LT-III)",
    "agricultural": "Agricultural (LT-V)",
    "agriculture": "Agricultural (LT-V)",
    "ht-i": "High Tension (HT-I)",
    "high tension": "High Tension (HT-I)",
}


@dataclass
class FieldCandidate:
    field: str
    value: Any
    raw: str
    page: int
    confidence: float
    pattern: str


@dataclass
class ExtractionResult:
    bill: CanonicalBill
    candidates: dict[str, list[str]] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _numbers(text: str) -> list[str]:
    return re.findall(NUM, text)


def _to_float(raw: str) -> float | None:
    cleaned = raw.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _looks_like_date(value: str) -> bool:
    return any(re.fullmatch(pattern, value.strip(), re.IGNORECASE) for pattern in DATE_PATTERNS)


def _in_range(field_name: str, value: float) -> bool:
    low, high = RANGES.get(field_name, (float("-inf"), float("inf")))
    return low <= value <= high


def _extract_dates(text: str) -> list[str]:
    found: list[str] = []
    for pattern in DATE_PATTERNS:
        found.extend(re.findall(pattern, text, re.IGNORECASE))
    return found


def _normalise_date(raw: str) -> str | None:
    """Render a matched date as a stable display string."""
    raw = raw.strip()
    for pattern in (r"^(\d{4})-(\d{2})-(\d{2})$",):
        match = re.fullmatch(pattern, raw)
        if match:
            year, month, day = match.groups()
            return f"{day}-{month}-{year}"
    match = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", raw)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = f"20{year}"
        return f"{int(day):02d}-{int(month):02d}-{year}"
    match = re.fullmatch(
        r"(\d{1,2})[\s-]([A-Za-z]{3})[a-z]*[\s-](\d{2,4})", raw, re.IGNORECASE
    )
    if match:
        day, month, year = match.groups()
        month_key = month.lower()[:3]
        if month_key in MONTHS:
            year = f"20{year}" if len(year) == 2 else year
            return f"{int(day):02d} {MONTHS[month_key]} {year}"
    match = re.fullmatch(r"([A-Za-z]{3})[a-z]*[\s-](\d{4})", raw, re.IGNORECASE)
    if match:
        month, year = match.groups()
        month_key = month.lower()[:3]
        if month_key in MONTHS:
            return f"{MONTHS[month_key]} {year}"
    return None


def _period_label(start: str | None, end: str | None) -> str | None:
    if start and end:
        return f"{start} - {end}"
    return start or end


def _line_window(text: str, index: int, *, before: int = 0, after: int = 140) -> str:
    start = max(0, index - before)
    return text[start : index + after]


def _value_window(
    text: str,
    index: int,
    *,
    after: int = 90,
    want: Callable[[str], bool] | None = None,
) -> str:
    """The slice of text a value for a label at ``index`` may occupy.

    Bounded to the label's own line whenever that line holds something the
    caller is looking for. Bills stack their readings, so on::

        Previous Reading        344554
        Current Reading         344906
        Units Consumed             352

    an unbounded window would offer all three numbers as candidates for the
    field on the first line. Falls through to the next line only for the
    label-above-value layouts some utilities print.
    """
    tail = text[index : index + after]
    first, separator, rest = tail.partition("\n")
    if not separator:
        return tail
    if want is None or want(first):
        return first
    second = rest.partition("\n")[0]
    return second if second.strip() else first


def _scrub_dates(text: str) -> str:
    for pattern in DATE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def _label_matches(text: str, patterns: tuple[str, ...]) -> list[re.Match]:
    matches: list[re.Match] = []
    for pattern in patterns:
        try:
            matches.extend(re.finditer(pattern, text, re.IGNORECASE))
        except re.error:  # pragma: no cover - patterns are static
            continue
    return matches


def _anchor_confidence(match: re.Match, text: str) -> float:
    """How much do we trust a label occurrence?

    A label followed immediately by a value separator is worth more than one
    that appears bare in a paragraph.
    """
    tail = text[match.end() : match.end() + 24]
    if re.match(r"^\s*[:.\-–]\s*", tail):
        return 0.9
    if re.match(r"^\s+\S", tail):
        return 0.75
    return 0.5


def _from_label(
    text: str,
    page: int,
    field_name: str,
    value_pattern: str,
    *,
    window: int = 140,
) -> list[FieldCandidate]:
    """Collect every candidate value sitting near a known label."""
    candidates: list[FieldCandidate] = []
    seen: set[str] = set()

    for match in _label_matches(text, LABELS[field_name]):
        anchor = _anchor_confidence(match, text)
        segment = _line_window(text, match.end(), after=window)
        value_match = re.search(value_pattern, segment)
        if not value_match:
            continue
        raw = value_match.group(0).strip()
        if raw in seen:
            continue
        seen.add(raw)
        candidates.append(
            FieldCandidate(
                field=field_name,
                value=raw,
                raw=raw,
                page=page,
                confidence=round(anchor * 0.85, 3),
                pattern="label",
            )
        )
    return candidates


def _provider_candidates(text: str, page: int) -> list[FieldCandidate]:
    upper = text.upper()
    found: list[FieldCandidate] = []
    for name in KNOWN_PROVIDERS:
        index = upper.find(name)
        if index == -1:
            continue
        # Prefer a longer, more specific match over a substring of it.
        if len(name) < 6 and any(name in other and other != name for other in KNOWN_PROVIDERS):
            continue
        found.append(
            FieldCandidate(
                field="provider",
                value=name.title(),
                raw=name,
                page=page,
                confidence=0.8 if index < 600 else 0.6,
                pattern="known_provider",
            )
        )
    if not found:
        match = re.search(
            r"^[ \t]*([A-Z][A-Za-z&.\s]{6,60}?(?:ELECTRICITY|POWER|ENERGY|VIDYUT|DISCOM|UTILITY))"
            r"[ \t]*(?:LIMITED|LTD\.?)?[ \t]*$",
            text,
            re.MULTILINE,
        )
        if match:
            found.append(
                FieldCandidate(
                    field="provider",
                    value=match.group(1).strip().title(),
                    raw=match.group(0).strip(),
                    page=page,
                    confidence=0.5,
                    pattern="name_shape",
                )
            )
    return found


def _billing_period_candidates(text: str, page: int) -> list[FieldCandidate]:
    found: list[FieldCandidate] = []
    for match in _label_matches(text, LABELS["billing_period"]):
        tail = text[match.end() : match.end() + 120]
        lines = tail.split("\n", 2)
        segment = lines[0]
        if len(_extract_dates(segment)) < 2 and len(lines) > 1:
            # A period label can sit above its range, or the range can wrap.
            segment = f"{lines[0]} {lines[1]}"
        dates = _extract_dates(segment)
        if len(dates) >= 2:
            start, end = _normalise_date(dates[0]), _normalise_date(dates[1])
            label = _period_label(start, end)
            if label:
                found.append(
                    FieldCandidate(
                        field="billing_period",
                        value=label,
                        raw=" ".join(dates[:2]),
                        page=page,
                        confidence=0.85,
                        pattern="label_range",
                    )
                )
        elif dates:
            label = _normalise_date(dates[0])
            if label:
                found.append(
                    FieldCandidate(
                        field="billing_period",
                        value=label,
                        raw=dates[0],
                        page=page,
                        confidence=0.6,
                        pattern="label_single",
                    )
                )

    if not found:
        # Fallback: the bare "01-10-2024 to 31-10-2024" range anywhere near the top.
        match = re.search(
            rf"({DATE_PATTERNS[0]}|{DATE_PATTERNS[1]})\s*(?:to|-|–|—)\s*"
            rf"({DATE_PATTERNS[0]}|{DATE_PATTERNS[1]})",
            text[:2500],
            re.IGNORECASE,
        )
        if match:
            start, end = _normalise_date(match.group(1)), _normalise_date(match.group(2))
            label = _period_label(start, end)
            if label:
                found.append(
                    FieldCandidate(
                        field="billing_period",
                        value=label,
                        raw=match.group(0),
                        page=page,
                        confidence=0.45,
                        pattern="bare_range",
                    )
                )
    return found


def _date_field_candidates(text: str, page: int, field_name: str) -> list[FieldCandidate]:
    found: list[FieldCandidate] = []
    for match in _label_matches(text, LABELS[field_name]):
        segment = _value_window(
            text, match.end(), after=60, want=lambda line: bool(_extract_dates(line))
        )
        dates = _extract_dates(segment)
        if not dates:
            continue
        label = _normalise_date(dates[0])
        if not label:
            continue
        found.append(
            FieldCandidate(
                field=field_name,
                value=label,
                raw=dates[0],
                page=page,
                confidence=round(_anchor_confidence(match, text) * 0.9, 3),
                pattern="label",
            )
        )
    return found


def _numeric_candidates(text: str, page: int, field_name: str) -> list[FieldCandidate]:
    found: list[FieldCandidate] = []
    pattern = rf"(?:{NUM}|\.\d+)"

    for match in _label_matches(text, LABELS[field_name]):
        segment = _value_window(
            text,
            match.end(),
            after=90,
            # A line holding only a date is not a value for a numeric field.
            want=lambda line: bool(_numbers(_scrub_dates(line))),
        )
        # Drop anything that looks like a date before scanning for numbers.
        scrubbed = _scrub_dates(segment)

        for raw in _numbers(scrubbed)[:3]:
            value = _to_float(raw)
            if value is None:
                continue
            # Readings and totals are rarely written with a decimal fraction
            # unless they are money.
            if field_name in ("previous_reading", "current_reading", "units_consumed") and "." in raw:
                if not _in_range(field_name, value):
                    continue
            found.append(
                FieldCandidate(
                    field=field_name,
                    value=value,
                    raw=raw,
                    page=page,
                    confidence=round(_anchor_confidence(match, text) * 0.9, 3),
                    pattern="label",
                )
            )
    return found


# Consumer numbers are long digit runs, sometimes with a prefix letter or
# internal spaces. Four or more digits, no date shapes.
CONSUMER_SHAPE = re.compile(r"\b([A-Z]{0,3}\s?\d[\d\s]{5,20}\d)\b")


def _consumer_candidates(text: str, page: int) -> list[FieldCandidate]:
    found: list[FieldCandidate] = []
    for match in _label_matches(text, LABELS["consumer_number"]):
        segment = _value_window(
            text,
            match.end(),
            after=60,
            want=lambda line: bool(CONSUMER_SHAPE.search(line)),
        )
        candidate = CONSUMER_SHAPE.search(segment)
        if not candidate:
            continue
        raw = re.sub(r"\s+", "", candidate.group(1))
        if not re.fullmatch(r"[A-Z]{0,3}\d{6,20}", raw):
            continue
        found.append(
            FieldCandidate(
                field="consumer_number",
                value=raw,
                raw=candidate.group(1).strip(),
                page=page,
                confidence=round(_anchor_confidence(match, text) * 0.9, 3),
                pattern="label",
            )
        )
    return found


def _load_candidates(text: str, page: int) -> list[FieldCandidate]:
    found: list[FieldCandidate] = []
    for match in _label_matches(text, LABELS["sanctioned_load"]):
        segment = _value_window(
            text, match.end(), after=50, want=lambda line: bool(_numbers(line))
        )
        value = re.search(rf"({NUM})\s*(kva|kw|hp|bhp|va)?", segment, re.IGNORECASE)
        if not value:
            continue
        unit = (value.group(2) or "kW").lower()
        rendered = f"{value.group(1)} {unit}"
        found.append(
            FieldCandidate(
                field="sanctioned_load",
                value=rendered,
                raw=value.group(0).strip(),
                page=page,
                confidence=round(_anchor_confidence(match, text) * 0.85, 3),
                pattern="label",
            )
        )
    return found


def _tariff_candidates(text: str, page: int) -> list[FieldCandidate]:
    found: list[FieldCandidate] = []
    lowered = text.lower()
    for keyword, canonical in TARIFF_KEYWORDS.items():
        if keyword in lowered:
            found.append(
                FieldCandidate(
                    field="tariff_category",
                    value=canonical,
                    raw=keyword.strip(),
                    page=page,
                    confidence=0.7,
                    pattern="keyword",
                )
            )
            break

    for match in _label_matches(text, LABELS["tariff_category"]):
        segment = _line_window(text, match.end(), after=40)
        # The separator is required, not optional. "Tariff Category" contains
        # the word "category", so an unanchored scan of the word after the
        # label happily returns the label's own tail as the value. Requiring
        # the colon forces the capture to start at the real value, and it also
        # steps over the English gloss the language layer appends to an Indic
        # label. Devanagari is allowed through because the category itself is
        # often written in the document's script ("श्रेणी: निवासी").
        value = re.search(
            r"[:.\-][ \t]*([A-Za-zऀ-ॿ][A-Za-z0-9ऀ-ॿ\- ]{1,30})",
            segment,
        )
        if not value:
            continue
        raw = value.group(1).strip().rstrip("-")
        if len(raw) < 2:
            continue
        found.append(
            FieldCandidate(
                field="tariff_category",
                value=raw,
                raw=raw,
                page=page,
                confidence=0.5,
                pattern="label",
            )
        )
        break
    return found


def _connection_type(tariff: str | None, text: str) -> str | None:
    haystack = f"{tariff or ''} {text[:1500]}".lower()
    if "high tension" in haystack or " ht " in haystack or "ht-i" in haystack:
        return "High Tension"
    if "industrial" in haystack:
        return "Industrial"
    if "commercial" in haystack:
        return "Commercial"
    if "agricultural" in haystack or "agriculture" in haystack:
        return "Agricultural"
    if "residential" in haystack or "domestic" in haystack:
        return "Residential"
    return None


def _rank(candidates: list[FieldCandidate]) -> list[FieldCandidate]:
    return sorted(candidates, key=lambda c: (-c.confidence, len(str(c.value))))


def _pick(candidates: list[FieldCandidate], field_name: str) -> FieldCandidate | None:
    """Choose the best candidate, preferring values with corroboration."""
    if not candidates:
        return None
    ranked = _rank(candidates)

    if field_name in RANGES:
        in_range = [c for c in ranked if isinstance(c.value, (int, float)) and _in_range(field_name, float(c.value))]
        if in_range:
            ranked = in_range

    scores: dict[str, tuple[float, int]] = {}
    for candidate in ranked:
        key = str(candidate.value)
        total, count = scores.get(key, (0.0, 0))
        scores[key] = (total + candidate.confidence, count + 1)

    best_value, (total, count) = max(
        scores.items(),
        key=lambda item: (item[1][0] / item[1][1] + 0.05 * (item[1][1] - 1)),
    )
    for candidate in ranked:
        if str(candidate.value) == best_value:
            corroborated = FieldCandidate(
                field=candidate.field,
                value=candidate.value,
                raw=candidate.raw,
                page=candidate.page,
                confidence=min(0.98, round(total / count + 0.05 * (count - 1), 3)),
                pattern=candidate.pattern if count == 1 else f"{candidate.pattern}+x{count}",
            )
            return corroborated
    return ranked[0]


def extract(
    pages: list[tuple[int, str]],
    language: LanguageReport,
) -> ExtractionResult:
    """Run rules over already-normalised page text."""
    notes: list[str] = list(language.notes)
    bill = CanonicalBill(
        detected_language=language.language,
        unit_label="kWh",
        currency_symbol="₹",
    )

    collected: dict[str, list[FieldCandidate]] = {name: [] for name in TARGET_FIELDS}
    joined = "\n".join(text for _, text in pages)

    for page_number, text in pages:
        text = tidy_numbers(text)
        collected["provider"].extend(_provider_candidates(text, page_number))
        collected["consumer_number"].extend(_consumer_candidates(text, page_number))
        collected["billing_period"].extend(_billing_period_candidates(text, page_number))
        collected["bill_date"].extend(_date_field_candidates(text, page_number, "bill_date"))
        collected["due_date"].extend(_date_field_candidates(text, page_number, "due_date"))
        collected["previous_reading"].extend(
            _numeric_candidates(text, page_number, "previous_reading")
        )
        collected["current_reading"].extend(
            _numeric_candidates(text, page_number, "current_reading")
        )
        collected["units_consumed"].extend(
            _numeric_candidates(text, page_number, "units_consumed")
        )
        collected["total_amount"].extend(
            _numeric_candidates(text, page_number, "total_amount")
        )
        collected["sanctioned_load"].extend(_load_candidates(text, page_number))
        collected["tariff_category"].extend(_tariff_candidates(text, page_number))

    chosen: dict[str, FieldCandidate] = {}
    for field_name, candidates in collected.items():
        picked = _pick(candidates, field_name)
        if picked is not None:
            chosen[field_name] = picked

    # --- arithmetic corroboration -----------------------------------------
    previous = chosen.get("previous_reading")
    current = chosen.get("current_reading")
    units = chosen.get("units_consumed")

    if previous and current and units:
        expected = float(current.value) - float(previous.value)
        actual = float(units.value)
        if expected > 0 and abs(expected - actual) / max(expected, 1) > 0.02:
            bill.flags.append("reading_mismatch")
            notes.append(
                f"units ({actual:g}) do not match reading difference ({expected:g})"
            )
    elif previous and current and not units:
        derived = float(current.value) - float(previous.value)
        if derived > 0:
            chosen["units_consumed"] = FieldCandidate(
                field="units_consumed",
                value=derived,
                raw=f"{current.value} - {previous.value}",
                page=current.page,
                confidence=0.65,
                pattern="derived_from_readings",
            )
            bill.flags.append("units_derived")

    # --- materialise -------------------------------------------------------
    provenance: dict[str, Provenance] = {}
    for field_name, candidate in chosen.items():
        numeric = isinstance(candidate.value, (int, float))
        source = "derived" if "derived" in candidate.pattern else "rule"
        provenance[field_name] = Provenance(
            source=source,
            page=candidate.page,
            confidence=candidate.confidence,
            raw_text=f"{candidate.raw} @p{candidate.page}",
            flags=["derived"] if source == "derived" else [],
        )
        setattr(bill, field_name, candidate.value)

    bill.tariff_category = bill.tariff_category or None
    bill.connection_type = _connection_type(bill.tariff_category, joined)
    bill.address_present = bool(
        re.search(r"\b(address|पता|पत्ता)\b", joined, re.IGNORECASE)
    )

    if bill.meter_type is None and re.search(r"\bsmart\s*meter\b", joined, re.IGNORECASE):
        bill.meter_type = "Smart Meter"

    missing = [
        name for name in TARGET_FIELDS if getattr(bill, name, None) in (None, "")
    ]
    bill.missing_fields = missing
    bill.provenance = provenance

    candidates_for_agent = {
        name: [c.raw for c in candidates]
        for name, candidates in collected.items()
        if candidates
    }

    return ExtractionResult(
        bill=bill,
        candidates=candidates_for_agent,
        unresolved=list(missing),
        notes=notes,
    )


TARGET_FIELDS: tuple[str, ...] = (
    "provider",
    "consumer_number",
    "billing_period",
    "bill_date",
    "due_date",
    "previous_reading",
    "current_reading",
    "units_consumed",
    "total_amount",
    "sanctioned_load",
    "tariff_category",
)
