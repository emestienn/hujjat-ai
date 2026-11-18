import io
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.config import Settings
from app.main import create_app

SAMPLE_PDF = Path(__file__).resolve().parents[2] / "samples" / "student-handbook.pdf"


@pytest.fixture
def settings(tmp_path) -> Settings:
    # Demo provider + no embedding key: tests never touch the network.
    return Settings(
        _env_file=None,
        llm_provider="demo",
        anthropic_api_key=None,
        gemini_api_key=None,
        data_dir=tmp_path,
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def sample_pdf() -> bytes:
    return SAMPLE_PDF.read_bytes()


@pytest.fixture
def scanned_pdf() -> bytes:
    """A PDF with no text layer at all: a photo-like page image, same as a scanned document."""
    image = Image.new("RGB", (900, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 60), "Scanned handbook page, no embedded text.", fill="black", font=ImageFont.load_default(size=32))
    png = io.BytesIO()
    image.save(png, format="PNG")

    doc = pymupdf.open()
    page = doc.new_page(width=900, height=200)
    page.insert_image(page.rect, stream=png.getvalue())
    return doc.tobytes()


@pytest.fixture
def uploaded(client, sample_pdf) -> dict:
    r = client.post("/api/documents", files={"file": ("student-handbook.pdf", sample_pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    return r.json()
