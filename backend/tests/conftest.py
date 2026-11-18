from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
def uploaded(client, sample_pdf) -> dict:
    r = client.post("/api/documents", files={"file": ("student-handbook.pdf", sample_pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    return r.json()
