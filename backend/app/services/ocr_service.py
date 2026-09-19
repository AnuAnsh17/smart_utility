"""Document rasterisation and OCR.

Two engines' worth of work, one dependency chain:

* **PyMuPDF** rasterises PDF pages to in-memory images. This matters beyond
  convenience — the alternative is shelling out to ``pdftoppm``, and this
  backend does not start processes derived from user input.
* **Tesseract** (via ``pytesseract``) reads text from those images.

Nothing here writes the document anywhere new unless
``ocr_keep_page_images`` is on, and nothing leaves the machine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.core.errors import TooManyPagesError, UnreadableDocumentError

log = logging.getLogger("smart_utility.ocr")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
PDF_SUFFIXES = {".pdf"}

# Tesseract refuses very large images; keep the long edge within reason. Big
# enough that a 300 DPI A4 page passes through unmodified.
MAX_LONG_EDGE = 4000


@dataclass
class OcrPage:
    number: int
    text: str
    mean_confidence: float
    word_count: int


@dataclass
class OcrDocument:
    pages: list[OcrPage] = field(default_factory=list)
    engine: str = "tesseract"
    languages_used: str = "eng"
    page_count: int = 0
    passes: int = 0

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text.strip())

    @property
    def mean_confidence(self) -> float:
        scored = [p.mean_confidence for p in self.pages if p.word_count]
        if not scored:
            return 0.0
        return round(sum(scored) / len(scored), 2)

    @property
    def word_count(self) -> int:
        return sum(p.word_count for p in self.pages)


def _preprocess(image):
    """Light, reversible cleanup. Anything aggressive risks destroying digits."""
    from PIL import Image, ImageOps

    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    if image.mode == "RGB":
        image = image.convert("L")

    image = ImageOps.autocontrast(image, cutoff=1)

    width, height = image.size
    longest = max(width, height)
    if longest < 1000:
        # Small scans are the common cause of missing decimal points.
        factor = min(3.0, 2000 / max(longest, 1))
        image = image.resize(
            (int(width * factor), int(height * factor)), Image.LANCZOS
        )
    elif longest > MAX_LONG_EDGE:
        factor = MAX_LONG_EDGE / longest
        image = image.resize(
            (int(width * factor), int(height * factor)), Image.LANCZOS
        )
    return image


def _rasterize_pdf(path: Path, dpi: int, max_pages: int) -> list:
    import pymupdf

    images = []
    with pymupdf.open(path) as doc:
        if doc.page_count > max_pages:
            raise TooManyPagesError(
                detail=f"{doc.page_count} pages exceeds limit of {max_pages}"
            )
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        for page in doc:
            pixmap = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csGRAY)
            images.append((page.number + 1, pixmap))
    return images


def _pixmap_to_image(pixmap):
    from PIL import Image

    return Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)


def _rasterize_image(path: Path) -> list:
    from PIL import Image

    with Image.open(path) as img:
        img.load()
        return [(1, img.copy())]


def rasterize(path: Path, *, dpi: int | None = None, max_pages: int | None = None):
    """Return ``[(page_number, PIL.Image), ...]`` for a PDF or an image."""
    dpi = dpi or settings.ocr_dpi
    max_pages = max_pages or settings.ocr_max_pages
    suffix = path.suffix.lower()

    try:
        if suffix in PDF_SUFFIXES:
            raw = _rasterize_pdf(path, dpi, max_pages)
        else:
            raw = _rasterize_image(path)
    except TooManyPagesError:
        raise
    except Exception as exc:
        log.warning("rasterisation failed (%s)", type(exc).__name__)
        raise UnreadableDocumentError(detail=f"rasterise: {type(exc).__name__}") from exc

    images = []
    for number, payload in raw:
        if isinstance(payload, int):  # pragma: no cover - defensive
            continue
        if hasattr(payload, "samples"):
            image = _pixmap_to_image(payload)
        else:
            image = payload
        images.append((number, _preprocess(image)))

    if not images:
        raise UnreadableDocumentError(detail="no pages produced")
    return images


def _ocr_image(image, lang: str) -> OcrPage:
    import pytesseract
    from pytesseract import Output

    try:
        data = pytesseract.image_to_data(
            image, lang=lang, output_type=Output.DICT, config="--psm 6"
        )
    except pytesseract.TesseractError as exc:
        raise UnreadableDocumentError(detail=str(exc)) from exc

    words: list[str] = []
    confidences: list[float] = []
    for token, conf in zip(data.get("text", []), data.get("conf", [])):
        token = (token or "").strip()
        if not token:
            continue
        try:
            score = float(conf)
        except (TypeError, ValueError):
            score = -1.0
        words.append(token)
        if score >= 0:
            confidences.append(score)

    text = pytesseract.image_to_string(image, lang=lang, config="--psm 6")

    return OcrPage(
        number=0,
        text=text,
        mean_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
        word_count=len(words),
    )


def _run_pass(images, lang: str) -> list[OcrPage]:
    pages = []
    for number, image in images:
        page = _ocr_image(image, lang)
        page.number = number
        pages.append(page)
    return pages


def _mean(pages: list[OcrPage]) -> float:
    scored = [p.mean_confidence for p in pages if p.word_count]
    return sum(scored) / len(scored) if scored else 0.0


def run_ocr_on_images(
    images: list[tuple[int, "Image.Image"]],
    *,
    languages: list[str] | None = None,
    widen_below: float | None = None,
) -> OcrDocument:
    """Read already-rasterised pages. Does not touch the filesystem.

    Tesseract degrades when too many language models are loaded at once, so we
    read the document with a single well-chosen language first and only widen
    the set if that reading looks poor. Two passes at most, whatever the
    document.

    The widened reading is adopted only when it beats the first one, so a
    second pass costs time and never accuracy. That asymmetry is why the
    threshold here is high: read a Devanagari page with ``eng`` alone and
    Tesseract transliterates the labels into confident-looking nonsense, which
    clears any low bar while leaving nothing the extractor can anchor on.
    """
    languages = languages or list(settings.ocr_languages)
    widen_below = settings.ocr_widen_below if widen_below is None else widen_below
    if not languages:
        languages = ["eng"]

    if not images:
        raise UnreadableDocumentError(detail="no pages to read")

    primary = "eng" if "eng" in languages else languages[0]
    pages = _run_pass(images, primary)
    passes = 1

    widening = [lang for lang in languages if lang != primary]
    if widening and _mean(pages) < widen_below:
        joined = "+".join([primary, *widening])
        log.info("primary OCR pass weak (%.1f); retrying as %s", _mean(pages), joined)
        try:
            candidate = _run_pass(images, joined)
        except UnreadableDocumentError:
            candidate = []
        passes = 2
        if candidate and _mean(candidate) > _mean(pages):
            pages = candidate
            primary = joined

    document = OcrDocument(
        pages=pages,
        engine=settings.ocr_engine,
        languages_used=primary,
        page_count=len(images),
        passes=passes,
    )

    if document.word_count == 0:
        # A real, honest failure. We do not fall back to sample text.
        raise UnreadableDocumentError(detail="ocr produced no tokens")

    return document


def run_ocr(
    path: Path,
    *,
    languages: list[str] | None = None,
    dpi: int | None = None,
    max_pages: int | None = None,
    widen_below: float | None = None,
) -> OcrDocument:
    """Rasterise a document and read it. Convenience wrapper.

    The pipeline rasterises once in its own stage and calls
    :func:`run_ocr_on_images` directly, so that a multi-page PDF is not
    rendered twice at full DPI. This wrapper exists for callers that only have
    a path — tests, the debug endpoint — where the extra render is not paid.
    """
    images = rasterize(path, dpi=dpi, max_pages=max_pages)
    return run_ocr_on_images(
        images, languages=languages, widen_below=widen_below
    )


def describe() -> dict[str, object]:
    import shutil

    return {
        "engine": settings.ocr_engine,
        "binary": shutil.which(settings.ocr_engine),
        "languages": list(settings.ocr_languages),
        "dpi": settings.ocr_dpi,
        "max_pages": settings.ocr_max_pages,
    }
