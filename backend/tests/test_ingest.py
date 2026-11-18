import io

import pytest
from docx import Document

from app.ingest import EmptyDocumentError, UnsupportedFileError, chunk_pages, parse_file


def test_parse_pdf_keeps_pages(sample_pdf):
    parsed = parse_file("handbook.pdf", sample_pdf)
    assert len(parsed.pages) == 4
    assert "Tuition payment" in parsed.pages[0]
    assert "Stipendiya" in parsed.pages[2]


def test_parse_docx():
    doc = Document()
    doc.add_paragraph("Birinchi paragraf.")
    doc.add_paragraph("Second paragraph.")
    buf = io.BytesIO()
    doc.save(buf)
    parsed = parse_file("notes.docx", buf.getvalue())
    assert parsed.pages == ["Birinchi paragraf.\nSecond paragraph."]


def test_parse_txt_and_cleanup():
    parsed = parse_file("a.txt", b"hello   world\n\n\n\nnext")
    assert parsed.pages == ["hello world\n\nnext"]


def test_unsupported_extension():
    with pytest.raises(UnsupportedFileError):
        parse_file("image.png", b"\x89PNG")


def test_empty_document():
    with pytest.raises(EmptyDocumentError):
        parse_file("empty.txt", b"   \n  ")


def test_chunks_respect_size_overlap_and_pages():
    text = " ".join(f"Sentence number {i} is here." for i in range(200))
    chunks = chunk_pages([text, "Short second page."], size=300, overlap=50)
    assert all(len(c) <= 300 for _, c in chunks)
    assert chunks[-1] == (2, "Short second page.")
    page1 = [c for p, c in chunks if p == 1]
    # Consecutive chunks overlap, so no text is lost at the boundaries.
    assert page1[0][-20:].split()[-1] in page1[1]
    # Chunks never start mid-word.
    for c in page1:
        idx = text.find(c)
        assert idx == 0 or text[idx - 1].isspace()


def test_chunk_rejects_bad_overlap():
    with pytest.raises(ValueError):
        chunk_pages(["x"], size=100, overlap=100)
