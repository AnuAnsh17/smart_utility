"""Script detection and the normalisation that makes non-English bills readable.

Detection is Unicode-range counting — deterministic, offline, no model to
download. Normalisation does two things and nothing more:

* transliterates non-ASCII **digits** to ASCII, so ``१२३`` becomes ``123``;
* maps known bill **labels** in Indian scripts to their English equivalents,
  so the keyword anchor in the extractor has something to match.

Neither step invents a value. A label mapping only tells the extractor where to
look; the number itself still has to be read off the page.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

log = logging.getLogger("smart_utility.language")

# script key -> (unicode range, default language name)
SCRIPT_RANGES: dict[str, tuple[tuple[int, int], str]] = {
    "devanagari": ((0x0900, 0x097F), "Hindi"),
    "bengali": ((0x0980, 0x09FF), "Bengali"),
    "gurmukhi": ((0x0A00, 0x0A7F), "Punjabi"),
    "gujarati": ((0x0A80, 0x0AFF), "Gujarati"),
    "oriya": ((0x0B00, 0x0B7F), "Odia"),
    "tamil": ((0x0B80, 0x0BFF), "Tamil"),
    "telugu": ((0x0C00, 0x0C7F), "Telugu"),
    "kannada": ((0x0C80, 0x0CFF), "Kannada"),
    "malayalam": ((0x0D00, 0x0D7F), "Malayalam"),
}

# Digits per script. Indic numerals are positional like ASCII, so this is a
# straight code-point offset for every script here.
DIGIT_BLOCKS: dict[str, int] = {
    "devanagari": 0x0966,
    "bengali": 0x09E6,
    "gurmukhi": 0x0A66,
    "gujarati": 0x0AE6,
    "oriya": 0x0B66,
    "tamil": 0x0BE6,
    "telugu": 0x0C66,
    "kannada": 0x0CE6,
    "malayalam": 0x0D66,
}

# Marathi shares Devanagari with Hindi. ळ (U+0933) is close to a shibboleth.
MARATHI_MARKERS = "ळ"
MARATHI_WORDS = ("वीज", "देय", "वापर", "ग्राहक")

# Share of script characters that has to be Devanagari before the document is
# treated as Devanagari-script. A real Devanagari bill lands near half; an
# English bill quoting one Hindi word lands near zero.
DEVANAGARI_SHARE = 0.15

# Tesseract emits these inside Devanagari clusters. They are invisible, they
# carry no meaning for a printed bill, and they split a label so that a literal
# match on it fails — ``देय रक्‍कम`` is not the string ``देय रक्कम``.
ZERO_WIDTH = dict.fromkeys(
    (0x200B, 0x200C, 0x200D, 0xFEFF)  # ZWSP, ZWNJ, ZWJ, BOM
)

# Label vocabulary. Keys are lowercase normalised script words; values are the
# canonical English label the extractor anchors on. Kept deliberately small and
# unambiguous — a wrong mapping here would be worse than no mapping.
LABEL_GLOSSARY: dict[str, dict[str, str]] = {
    "devanagari": {
        "ग्राहक": "consumer",
        "ग्राहक क्रमांक": "consumer number",
        "ग्राहक संख्या": "consumer number",
        "उपभोक्ता": "consumer",
        "उपभोक्ता संख्या": "consumer number",
        "मीटर": "meter",
        "मीटर क्रमांक": "meter number",
        "बिल": "bill",
        "बिल अवधि": "billing period",
        "बिल दिनांक": "bill date",
        "देय दिनांक": "due date",
        "अंतिम तिथि": "due date",
        "पिछली रीडिंग": "previous reading",
        "वर्तमान रीडिंग": "current reading",
        "इकाई": "units",
        "युनिट": "units",
        "वापर": "consumption",
        "एकूण रक्कम": "total amount",
        "कुल राशि": "total amount",
        "कुल रक्कम": "total amount",
        "राशि": "amount",
        "देय रक्कम": "amount payable",
        "लोड": "load",
        "स्वीकृत भार": "sanctioned load",
        "दर": "tariff",
        "श्रेणी": "category",
        "विद्युत": "electricity",
        "वीज": "electricity",
        "बकाया": "arrears",
        "जमा": "credit",
    },
    "tamil": {
        "நுகர்வோர்": "consumer",
        "மீட்டர்": "meter",
        "மின்சாரம்": "electricity",
        "மொத்தம்": "total",
        "தொகை": "amount",
        "தேதி": "date",
        "அலகு": "units",
    },
    "telugu": {
        "వినియోగదారు": "consumer",
        "మీటర్": "meter",
        "విద్యుత్": "electricity",
        "మొత్తం": "total",
        "తేదీ": "date",
        "యూనిట్లు": "units",
    },
    "kannada": {
        "ಗ್ರಾಹಕ": "consumer",
        "ಮೀಟರ್": "meter",
        "ವಿದ್ಯುತ್": "electricity",
        "ಒಟ್ಟು": "total",
        "ದಿನಾಂಕ": "date",
        "ಘಟಕಗಳು": "units",
    },
    "malayalam": {
        "ഉപഭോക്താവ്": "consumer",
        "മീറ്റർ": "meter",
        "വൈദ്യുതി": "electricity",
        "ആകെ": "total",
        "തീയതി": "date",
    },
    "gujarati": {
        "ગ્રાહક": "consumer",
        "મીટર": "meter",
        "વીજળી": "electricity",
        "કુલ": "total",
        "તારીખ": "date",
        "એકમ": "units",
    },
    "bengali": {
        "গ্রাহক": "consumer",
        "মিটার": "meter",
        "বিদ্যুৎ": "electricity",
        "মোট": "total",
        "তারিখ": "date",
    },
    "gurmukhi": {
        "ਖਪਤਕਾਰ": "consumer",
        "ਮੀਟਰ": "meter",
        "ਬਿਜਲੀ": "electricity",
        "ਕੁੱਲ": "total",
        "ਤਾਰੀਖ": "date",
    },
    "oriya": {
        "ଗ୍ରାହକ": "consumer",
        "ମିଟର": "meter",
        "ବିଦ୍ୟୁତ": "electricity",
        "ମୋଟ": "total",
        "ତାରିଖ": "date",
    },
}

@dataclass
class LanguageReport:
    language: str = "English"
    script: str = "latin"
    coverage: float = 1.0
    mixed: bool = False
    scripts_seen: dict[str, int] = field(default_factory=dict)
    translation_applied: bool = False
    notes: list[str] = field(default_factory=list)


def _classify_char(char: str) -> str | None:
    point = ord(char)
    if 0x0041 <= point <= 0x024F:
        return "latin"
    for script, ((low, high), _) in SCRIPT_RANGES.items():
        if low <= point <= high:
            return script
    return None


def detect(text: str) -> LanguageReport:
    """Identify the dominant script in a body of OCR text."""
    counts: dict[str, int] = {}
    total = 0

    for char in text:
        if char.isspace() or unicodedata.category(char).startswith("P"):
            continue
        if char.isdigit() and ord(char) < 128:
            continue
        script = _classify_char(char)
        if script is None:
            continue
        counts[script] = counts.get(script, 0) + 1
        total += 1

    if not total:
        return LanguageReport(
            language="English",
            script="latin",
            coverage=0.0,
            notes=["no script characters found; defaulting to English"],
        )

    dominant = max(counts, key=lambda key: counts[key])
    coverage = round(counts[dominant] / total, 4)
    report = LanguageReport(
        script=dominant,
        coverage=coverage,
        mixed=len(counts) > 1 and coverage < 0.9,
        scripts_seen=counts,
    )

    # A bill is written in the language of its labels, and a page can carry
    # more Latin than Devanagari while still being an Indic document: the
    # provider name, the footer, and the ASCII digits all count towards Latin,
    # while the Devanagari is concentrated in the field labels that matter.
    # So a substantial Devanagari block decides the language even when Latin
    # has the larger count. A stray Devanagari word in an English document
    # stays below the threshold and does not.
    devanagari = counts.get("devanagari", 0)
    if devanagari and devanagari >= total * DEVANAGARI_SHARE:
        report.script = "devanagari"
        if MARATHI_MARKERS in text or any(word in text for word in MARATHI_WORDS):
            report.language = "Marathi"
        else:
            report.language = SCRIPT_RANGES["devanagari"][1]
    elif dominant == "latin":
        report.language = "English"
    else:
        report.language = SCRIPT_RANGES[dominant][1]

    if report.mixed:
        report.notes.append("document mixes scripts; Latin field labels preferred")
    return report


def transliterate_digits(text: str) -> str:
    """Map Indic digits to ASCII. Sign and separators are left alone."""
    out = []
    for char in text:
        mapped = None
        for script, base in DIGIT_BLOCKS.items():
            if base <= ord(char) <= base + 9:
                mapped = str(ord(char) - base)
                break
        out.append(mapped if mapped is not None else char)
    return "".join(out)


def glossary_for(script: str) -> dict[str, str]:
    return LABEL_GLOSSARY.get(script, {})


def normalise_text(text: str, report: LanguageReport | None = None) -> tuple[str, list[str]]:
    """Return ``(normalised_text, notes)``.

    Digit transliteration always runs (it is lossless and reversible in
    meaning). Label glossing appends the English equivalent next to the Indic
    label rather than replacing it, so the original text stays intact for
    provenance and only the anchor becomes matchable.
    """
    notes: list[str] = []

    # Zero-width characters first. They are invisible, so stripping them cannot
    # change what a human reads, and they would otherwise break the label match
    # below. ``एकूण देय रक्‍कम`` has to become ``एकूण देय रक्कम`` or the
    # extractor never finds the total.
    stripped = text.translate(ZERO_WIDTH)
    if stripped != text:
        notes.append("zero-width characters removed")

    result = transliterate_digits(stripped)

    if result != stripped:
        notes.append("indic digits transliterated to ascii")

    script = (report or detect(text)).script
    glossary = glossary_for(script)

    if glossary:
        appended = 0
        # Longest term first. The glossary contains both ``ग्राहक`` (consumer)
        # and ``ग्राहक क्रमांक`` (consumer number); glossing the short one first
        # would push text between the two words and leave the longer label
        # unmatchable. Once the longer term is glossed, the "already glossed"
        # guard below stops the shorter one from firing again.
        for term in sorted(glossary, key=len, reverse=True):
            english = glossary[term]
            if term in result and english.lower() not in result.lower():
                result = result.replace(term, f"{term} {english}")
                appended += 1
        if appended:
            notes.append(f"{appended} label(s) glossed to english")

    return result, notes


def summarise(text: str) -> LanguageReport:
    return detect(text)


_DIGIT_GROUP = re.compile(r"(?<=\d)[\s_](?=\d)")


def tidy_numbers(text: str) -> str:
    """Collapse digit-group separators that OCR inserts inside a number."""
    return _DIGIT_GROUP.sub("", text)
