"""Turn uploaded files into page-aware text chunks."""

import io
import logging
import re
from dataclasses import dataclass

import pymupdf  # used only to rasterise scanned pages for OCR
import pytesseract
from docx import Document as DocxDocument
from PIL import Image
from pypdf import PdfReader

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

# A page with less text than this is assumed to be a scanned image and sent to OCR.
OCR_MIN_CHARS = 20
# Tried in order; Tesseract raises if a language's trained data isn't installed,
# so we fall back to whichever subset is actually available.
OCR_LANGUAGES = ("eng+rus+uzb", "eng+rus", "eng")


class UnsupportedFileError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


@dataclass
class ParsedDocument:
    pages: list[str]  # text per page (page 1 = index 0)


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\n(?=\w)", "", text)  # join words hyphenated across lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _join_pdf_lines(text: str) -> str:
    """PDFs break lines mid-sentence. Re-join them, but keep breaks after sentence endings,
    before numbered items ("8. ...") and around blank lines."""
    return re.sub(r"(?<![.:!?\n])\n(?!\n|\d+[.)]\s)", " ", text)


def _ocr_page(pdf_bytes: bytes, page_index: int) -> str:
    """Rasterise one PDF page and OCR it. Returns "" if OCR isn't available or fails,
    so a missing Tesseract install degrades to the old "no text found" behaviour
    instead of crashing the upload."""
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            pix = doc[page_index].get_pixmap(matrix=pymupdf.Matrix(2, 2))  # 2x zoom helps OCR accuracy
            image = Image.open(io.BytesIO(pix.tobytes("png")))
    except Exception:
        log.warning("Could not rasterise page %d for OCR", page_index + 1, exc_info=True)
        return ""

    for lang in OCR_LANGUAGES:
        try:
            return pytesseract.image_to_string(image, lang=lang)
        except pytesseract.TesseractError:
            continue  # that language pack isn't installed, try a smaller set
        except Exception:
            log.warning("Tesseract is not available; skipping OCR", exc_info=True)
            break
    return ""


def parse_file(filename: str, data: bytes) -> ParsedDocument:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported file type '{ext or filename}'. Use: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for i, p in enumerate(reader.pages):
            text = _clean(p.extract_text() or "")
            if len(text) < OCR_MIN_CHARS:
                text = _clean(_ocr_page(data, i)) or text
            pages.append(_join_pdf_lines(text))
    elif ext == ".docx":
        doc = DocxDocument(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs)
        pages = [_clean(text)]
    else:
        pages = [_clean(data.decode("utf-8", errors="replace"))]

    if not any(p.strip() for p in pages):
        raise EmptyDocumentError(
            "No text found in this file, even after trying OCR. The scan may be too low-quality to read."
        )
    return ParsedDocument(pages=pages)


def chunk_pages(pages: list[str], size: int = 900, overlap: int = 150) -> list[tuple[int, str]]:
    """Split each page into overlapping chunks, preferring paragraph and sentence boundaries.

    Returns a list of (page_number, chunk_text), page numbers starting at 1.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    chunks: list[tuple[int, str]] = []
    for page_no, text in enumerate(pages, start=1):
        text = text.strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                # Try to end on a paragraph, then sentence, then word boundary.
                window = text[start:end]
                for sep in ("\n\n", ". ", "? ", "! ", "\n", " "):
                    cut = window.rfind(sep)
                    if cut > size * 0.5:
                        end = start + cut + len(sep)
                        break
            piece = text[start:end].strip()
            if piece:
                chunks.append((page_no, piece))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
            # Don't start in the middle of a word.
            while start < len(text) and start > 0 and not text[start - 1].isspace():
                start += 1
    return chunks
