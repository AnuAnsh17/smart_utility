"""Strip personal identifiers out of document text before it leaves the host.

The agent reads OCR text, and OCR text is a picture of a household's post: the
consumer's name, their address, their consumer number, sometimes a phone number
and an email. None of that is needed to extract a meter reading, so it is
removed before the request is built.

What this deliberately keeps
    Measurements. A consumer number and a meter reading are both digit runs, so
    the rule cannot simply be "mask every number" — that would blind the agent
    to the very fields it exists to read. The discriminator is length: amounts,
    units and readings on an Indian domestic bill run to at most seven digits,
    while consumer and account numbers run to nine or more. Runs of nine or
    more digits are masked; shorter runs are left exactly as they are.

What this does not catch
    An unlabelled name and an address that carries no PIN code survive into the
    request. A name is masked only where a label introduces it; detecting one
    in free text reliably needs a model, and using a model to decide what to
    hide from a model is not a control worth trusting. Treat this as reducing
    exposure, not as anonymisation. If a document is too sensitive to send even
    reduced, leave ``agent_enabled`` off — the pipeline completes on rules
    alone.

Every substitution is a fixed token rather than a blank, so the agent can see
that something was removed and will not try to reconstruct it from context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Consumer / account numbers written as one unbroken run, or in groups.
_LONG_DIGITS = re.compile(r"\d{9,}")
# Three or more groups of three-to-four digits, e.g. "1234 5678 9012". The
# three-group floor and the word anchors both matter: two five-digit groups on
# one line is a pair of meter readings ("45210 45738"), not an identifier, and
# masking it would hide the fields the agent is being asked to read.
_GROUPED_DIGITS = re.compile(r"\b\d{3,4}(?:[ -]\d{3,4}){2,3}\b")

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Permanent Account Number: five letters, four digits, one letter.
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

# Postal address lines: a six-digit PIN standing as its own token, next to
# something that reads like a place. Kept narrow on purpose — a bare six-digit
# number is more likely to be a reading than a PIN.
_PIN = re.compile(r"(?<![\d.])\d{6}(?![\d.])")
_ADDRESS_HINT = re.compile(
    r"\b(pin|pincode|pin code|post|postal|district|distt?|taluk|tehsil|village|"
    r"mouza|street|road|marg|nagar|colony|sector|plot|house|flat|block|lane|"
    r"apartment|society|layout|state)\b",
    re.IGNORECASE,
)

# A labelled field whose value is a person's name. The word *before* "name" is
# captured whatever it is, because only these ones introduce a person:
# "Tariff Name: LT I Residential" and "Biller Name: MSEDCL" also end in
# "Name:", and both carry values the agent is meant to read.
_NAME_LABEL_WORDS = frozenset(
    {
        "consumer",
        "customer",
        "account",
        "connection",
        "subscriber",
        "holder",
        "applicant",
        "user",
    }
)
_NAME_FIELD = re.compile(
    r"(?P<label>(?:(?P<lead>[A-Za-z]+)[^\S\n]+)?name\b[^\S\n]*[:\-][^\S\n]*)"
    r"(?P<value>[^\n]+)",
    re.IGNORECASE,
)

# Words that make a value an organisation rather than a person, so that a line
# like "Biller Name: MSEDCL" keeps the provider name readable.
_ORG_WORDS = frozenset(
    {
        "ltd", "limited", "pvt", "private", "co", "company", "corp",
        "corporation", "inc", "llp", "power", "electricity", "electric",
        "energy", "gas", "water", "board", "nigam", "vidyut", "department",
        "dept", "utility", "services", "supply", "distribution", "municipal",
        "authority",
    }
)
_PERSON_TOKEN = re.compile(r"^[A-Za-z][A-Za-z'’.-]*$")

# Anything that could terminate the token and be read as instruction.
_TOKENS = {
    "number": "[REDACTED-NUMBER]",
    "email": "[REDACTED-EMAIL]",
    "pan": "[REDACTED-PAN]",
    "address": "[REDACTED-ADDRESS]",
    "name": "[REDACTED-NAME]",
}


@dataclass
class RedactionResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def summary(self) -> str:
        """Counts only — never the values that were removed."""
        if not self.counts:
            return "none"
        return ",".join(f"{name}={count}" for name, count in sorted(self.counts.items()))


def _count_digits(text: str) -> int:
    return sum(character.isdigit() for character in text)


def _reads_like_a_person(value: str) -> bool:
    """Whether a labelled value is plausibly a person rather than an entity.

    Short and alphabetic, with no word that names a kind of organisation. A
    false negative here leaves a name in the request; a false positive would
    hide a field the agent was asked to read, so both tests are deliberately
    permissive in the direction of *keeping* the text.
    """
    tokens = value.split()
    if not 1 <= len(tokens) <= 4:
        return False
    if not all(_PERSON_TOKEN.match(token) for token in tokens):
        return False
    return not any(token.strip(".").lower() in _ORG_WORDS for token in tokens)


def redact(text: str) -> RedactionResult:
    """Return a copy of ``text`` with personal identifiers replaced by tokens."""
    if not text:
        return RedactionResult(text=text)

    counts: dict[str, int] = {}
    working = text

    def tally(name: str, hits: int) -> None:
        if hits:
            counts[name] = counts.get(name, 0) + hits

    working, hits = _EMAIL.subn(_TOKENS["email"], working)
    tally("email", hits)

    working, hits = _PAN.subn(_TOKENS["pan"], working)
    tally("pan", hits)

    # Grouped runs first, so "1234 5678 9012" is caught as one identifier
    # rather than left alone by the unbroken-run rule below.
    def mask_grouped(match: re.Match[str]) -> str:
        return _TOKENS["number"] if _count_digits(match.group(0)) >= 9 else match.group(0)

    working, hits = _GROUPED_DIGITS.subn(mask_grouped, working)
    tally("number", hits)

    working, hits = _LONG_DIGITS.subn(_TOKENS["number"], working)
    tally("number", hits)

    # Names, but only where a label introduces one and the value reads like a
    # person. Runs after the digit rules so that a line carrying both a number
    # and a name is already reduced to "Consumer No: [REDACTED-NUMBER]
    # Consumer Name: <name>" before this looks at it.
    def mask_name(match: re.Match[str]) -> str:
        lead = match.group("lead")
        if lead is not None and lead.lower() not in _NAME_LABEL_WORDS:
            return match.group(0)
        if not _reads_like_a_person(match.group("value").strip()):
            return match.group(0)
        return match.group("label") + _TOKENS["name"]

    working, hits = _NAME_FIELD.subn(mask_name, working)
    tally("name", hits)

    # Addresses: only when a PIN and a place-word appear on the same line.
    lines = working.splitlines()
    masked_lines = 0
    for index, line in enumerate(lines):
        if _PIN.search(line) and _ADDRESS_HINT.search(line):
            lines[index] = _TOKENS["address"]
            masked_lines += 1
    if masked_lines:
        working = "\n".join(lines)
        tally("address", masked_lines)

    return RedactionResult(text=working, counts=counts)
