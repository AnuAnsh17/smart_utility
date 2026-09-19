"""Render synthetic electricity bills for local testing.

Run with the backend venv:

    .venv/bin/python scripts/generate_sample_bills.py

Output lands in ``backend/samples/``. Nothing here is derived from a real
document: every value is invented, and every page carries a footer saying so.
That is deliberate — a test corpus built from genuine bills would put somebody's
consumer number and consumption history into the repository.

The layout is a uniform block of left-aligned ``Label: value`` lines because the
OCR stage reads pages with Tesseract's ``--psm 6`` (a single uniform text
block). A bill laid out as a widely spaced multi-column table fragments under
that mode; this one does not. Every label is followed immediately by a colon,
which is also what the extractor's anchor scoring looks for.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BACKEND_DIR / "samples"

# A4 at 200 DPI. The long edge (2339) sits inside the OCR stage's resize window,
# so the page reaches Tesseract at the resolution it was drawn at.
DPI = 200
PAGE_W = 1654
PAGE_H = 2339
MARGIN = 130
LINE_HEIGHT = 62

DEJAVU = Path("/usr/share/fonts/truetype/dejavu")
NOTO = Path("/usr/share/fonts/truetype/noto")
DEJAVU_SANS = DEJAVU / "DejaVuSans.ttf"
DEJAVU_BOLD = DEJAVU / "DejaVuSans-Bold.ttf"
NOTO_DEVANAGARI = NOTO / "NotoSansDevanagari-Regular.ttf"
NOTO_DEVANAGARI_BOLD = NOTO / "NotoSansDevanagari-Bold.ttf"

FOOTER = "Synthetic test document. Not a real bill. Generated locally for testing."


@lru_cache(maxsize=32)
def _font(path: Path, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(str(path), size)


def _require_fonts() -> None:
    missing = [
        str(path)
        for path in (DEJAVU_SANS, DEJAVU_BOLD, NOTO_DEVANAGARI, NOTO_DEVANAGARI_BOLD)
        if not path.exists()
    ]
    if missing:
        print("missing font files:", *missing, sep="\n  ", file=sys.stderr)
        raise SystemExit(1)


def _blank_page() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("L", (PAGE_W, PAGE_H), color=255)
    return image, ImageDraw.Draw(image)


def draw_segments(draw, y: int, segments, *, size: int = 32) -> None:
    """Draw ``[(text, font_path), ...]`` left to right on one line.

    Mixed-script lines need this: DejaVu has no Devanagari coverage and the Noto
    Devanagari face is not the right choice for Latin digits, so a line that
    contains both is drawn segment by segment.
    """
    x = MARGIN
    for text, path in segments:
        font = _font(path, size)
        draw.text((x, y), text, font=font, fill=0)
        x += draw.textlength(text, font=font)


def _has_devanagari(text: str) -> bool:
    return any("ऀ" <= char <= "ॿ" for char in text)


def draw_field(draw, y: int, label: str, value: str, *, devanagari: bool = False) -> None:
    """One ``Label: value`` line. The colon is what the extractor anchors on.

    Each side is drawn with the font that can actually render it — DejaVu for
    Latin and digits, Noto Devanagari otherwise. Handing Devanagari to DejaVu
    produces a row of tofu boxes, which OCR faithfully reports as ``OOOO``.
    """
    if devanagari:
        segments = [
            (f"{label}: ", NOTO_DEVANAGARI),
            (value, NOTO_DEVANAGARI if _has_devanagari(value) else DEJAVU_SANS),
        ]
    else:
        segments = [(f"{label}: {value}", DEJAVU_SANS)]
    draw_segments(draw, y, segments)


def draw_footer(draw) -> None:
    draw_segments(draw, PAGE_H - 170, [(FOOTER, DEJAVU_SANS)], size=22)


def draw_header(draw, y: int, provider: str, tagline: str) -> int:
    draw_segments(draw, y, [(provider, DEJAVU_BOLD)], size=52)
    y += 84
    draw_segments(draw, y, [(tagline, DEJAVU_SANS)], size=26)
    y += 62
    draw_segments(draw, y, [("ELECTRICITY BILL", DEJAVU_BOLD)], size=30)
    return y + 96


def save_png(image: Image.Image, name: str) -> Path:
    path = SAMPLES_DIR / name
    image.save(path, "PNG")
    return path


def save_pdf(lines: list[tuple[int, str]], name: str) -> Path:
    """A real PDF, with vector text rather than a wrapped bitmap.

    The pipeline rasterises this with PyMuPDF, so the sample exercises the PDF
    branch end to end instead of only the image branch.
    """
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 in points
    for y, text in lines:
        page.insert_text((46, y), text, fontsize=13, fontname="helv")
    path = SAMPLES_DIR / name
    doc.save(path)
    doc.close()
    return path


# ---------------------------------------------------------------------------
# Bill definitions
# ---------------------------------------------------------------------------

# Four consecutive months for one connection. Each row satisfies
# ``previous + units == current``, so the validator's arithmetic cross-check
# passes and the extraction is corroborated rather than merely plausible.
#
# October repeats the demo narrative's 352 kWh / Rs 2,430 so that live output
# and the frontend's sample data agree where they overlap.
ENGLISH_MONTHS = (
    # month, period, bill_date, due_date, prev, curr, units, amount
    ("2024_07", "01 Jul 2024 to 31 Jul 2024", "05 Aug 2024", "25 Aug 2024", 344236, 344554, 318, "2215.00"),
    ("2024_08", "01 Aug 2024 to 31 Aug 2024", "05 Sep 2024", "25 Sep 2024", 344554, 344906, 352, "2430.00"),
    ("2024_09", "01 Sep 2024 to 30 Sep 2024", "05 Oct 2024", "25 Oct 2024", 344906, 345247, 341, "2365.00"),
    ("2024_10", "01 Oct 2024 to 31 Oct 2024", "05 Nov 2024", "25 Nov 2024", 345247, 345599, 352, "2430.00"),
)

# Ten digits with no leading zero: the PNG pass and the PDF pass rasterise at
# different resolutions, and a leading zero is exactly the kind of glyph that
# two resolutions can disagree about. The connection has to read the same way
# every time or the four bills would not group into one history.
CONSUMER_NUMBER = "2819481920"
METER_NUMBER = "MH04E1234567"

MARATHI_CONSUMER = "5051239876"


def english_lines(row) -> list[tuple[str, str]]:
    _, period, bill_date, due_date, prev, curr, units, amount = row
    return [
        ("Consumer Number", CONSUMER_NUMBER),
        ("Meter Number", METER_NUMBER),
        ("Billing Period", period),
        ("Bill Date", bill_date),
        ("Due Date", due_date),
        ("Previous Reading", str(prev)),
        ("Current Reading", str(curr)),
        ("Units Consumed", str(units)),
        ("Total Amount", f"Rs. {amount}"),
        ("Sanctioned Load", "4 kW"),
        ("Tariff Category", "Residential LT-I"),
        ("Meter Type", "Smart Meter"),
    ]


def build_english(row) -> Path:
    image, draw = _blank_page()
    y = draw_header(
        draw, MARGIN, "TATA POWER", "MUMBAI DISTRIBUTION LIMITED"
    )
    for label, value in english_lines(row):
        draw_field(draw, y, label, value)
        y += LINE_HEIGHT
    draw_footer(draw)
    return save_png(image, f"bill_{row[0]}.png")


def build_english_pdf(row) -> Path:
    """The August bill again, this time as a vector PDF.

    Text is placed at PDF points directly, with a leading well clear of the
    glyph height. Setting the lines any closer makes them overlap, and
    overlapping text is the one thing OCR cannot recover from.
    """
    lines: list[tuple[int, str]] = [(70, "TATA POWER")]
    y = 70
    for label, value in english_lines(row):
        y += 26
        lines.append((y, f"{label}: {value}"))
    y += 40
    lines.append((y, FOOTER))
    return save_pdf(lines, f"bill_{row[0]}.pdf")


def build_marathi() -> Path:
    """Devanagari labels, ASCII digits, Latin provider name.

    Digits stay ASCII because that is what the extractor's numeric rules read;
    the language layer transliterates Devanagari digits anyway, but there is no
    reason to make OCR do extra work. The label wording carries distinctly
    Marathi vocabulary (``वीज``, ``वापर``, ``देय``, ``ग्राहक``) so the language
    detector can tell Marathi from Hindi.
    """
    image, draw = _blank_page()
    y = draw_header(draw, MARGIN, "ADANI ELECTRICITY", "MUMBAI LIMITED")
    fields = [
        ("ग्राहक क्रमांक", MARATHI_CONSUMER),
        ("मीटर क्रमांक", "AD9F5523110"),
        ("बिल अवधि", "01 Mar 2025 to 31 Mar 2025"),
        ("बिल दिनांक", "04 Apr 2025"),
        ("देय दिनांक", "24 Apr 2025"),
        ("पिछली रीडिंग", "77120"),
        ("वर्तमान रीडिंग", "77488"),
        ("वीज वापर (इकाई)", "368"),
        ("एकूण देय रक्कम", "Rs. 2545.00"),
        ("स्वीकृत भार", "5 kVA"),
        ("श्रेणी", "निवासी"),
    ]
    for label, value in fields:
        draw_field(draw, y, label, value, devanagari=True)
        y += LINE_HEIGHT
    draw_footer(draw)
    return save_png(image, "bill_marathi_2025_03.png")


def build_sparse() -> Path:
    """A bill missing most optional fields, and with no consumer number.

    This one is here to exercise the honest paths: fields that cannot be read
    stay null and are listed as missing, and without a consumer number there is
    no history to join, so no forecast is produced.
    """
    image, draw = _blank_page()
    y = draw_header(draw, MARGIN, "MESCOM", "MANGALORE ELECTRICITY SUPPLY COMPANY")
    fields = [
        ("Billing Period", "01 Sep 2024 to 30 Sep 2024"),
        ("Bill Date", "03 Oct 2024"),
        ("Previous Reading", "12004"),
        ("Current Reading", "12318"),
        ("Units Consumed", "314"),
        ("Total Amount", "Rs. 2280.00"),
    ]
    for label, value in fields:
        draw_field(draw, y, label, value)
        y += LINE_HEIGHT
    draw_footer(draw)
    return save_png(image, "bill_sparse_2024_09.png")


def main() -> int:
    _require_fonts()
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for row in ENGLISH_MONTHS:
        written.append(build_english(row))
    written.append(build_english_pdf(ENGLISH_MONTHS[1]))
    written.append(build_marathi())
    written.append(build_sparse())

    for path in written:
        print(f"{path.relative_to(BACKEND_DIR)}  {path.stat().st_size // 1024} KB")
    print(f"\n{len(written)} synthetic bills in {SAMPLES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
