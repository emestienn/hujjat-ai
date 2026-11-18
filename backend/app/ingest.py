"""Turn uploaded files into page-aware text chunks."""

import io
import re
from dataclasses import dataclass

from docx import Document as DocxDocument
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


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


def parse_file(filename: str, data: bytes) -> ParsedDocument:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported file type '{ext or filename}'. Use: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = [_join_pdf_lines(_clean(p.extract_text() or "")) for p in reader.pages]
    elif ext == ".docx":
        doc = DocxDocument(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs)
        pages = [_clean(text)]
    else:
        pages = [_clean(data.decode("utf-8", errors="replace"))]

    if not any(p.strip() for p in pages):
        raise EmptyDocumentError("No text found in this file. If it is a scanned PDF, run OCR on it first.")
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
