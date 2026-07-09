"""
tests/test_doc_ingest.py

Tests for ingestion/doc_ingest.py. Uses reportlab to generate a real PDF at
test time so PDF extraction is verified end-to-end without a fixture binary
committed to the repo.
"""

import io

import pytest
from ingestion import doc_ingest
from utils import storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.duckdb")
    yield


def _make_test_pdf_bytes(text: str) -> bytes:
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.save()
    return buf.getvalue()


def test_extract_pdf_text_returns_expected_content():
    pdf_bytes = _make_test_pdf_bytes("Tuner Retry Design Spec")
    text = doc_ingest._extract_pdf_text(pdf_bytes)
    assert "Tuner Retry Design Spec" in text


def test_extract_html_text_strips_tags_and_scripts():
    html = b"""
    <html><body>
      <script>ignoreThis();</script>
      <h1>Tuner Spec</h1>
      <p>Retry backoff controls signal lock retries.</p>
    </body></html>
    """
    text = doc_ingest._extract_html_text(html)
    assert "Tuner Spec" in text
    assert "Retry backoff" in text
    assert "ignoreThis" not in text


class _FakeUploadedFile:
    """Minimal stand-in for Streamlit's UploadedFile, for testing without a live app."""

    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content

    def read(self):
        return self._content


def test_ingest_uploaded_files_registers_and_extracts(monkeypatch, tmp_path):
    monkeypatch.setattr(doc_ingest, "DATA_DIR", tmp_path)
    pdf_bytes = _make_test_pdf_bytes("Hello from a test PDF")
    uploaded = [_FakeUploadedFile("spec.pdf", pdf_bytes)]

    artifact_ids = doc_ingest.ingest_uploaded_files(uploaded)
    assert len(artifact_ids) == 1

    df = storage.list_artifacts("document")
    assert len(df) == 1
    assert df.iloc[0]["display_name"] == "spec.pdf"
