"""
ingestion/doc_ingest.py

Provisions documents into the POC from either:
  1. Uploaded files (PDF or Markdown) via the Streamlit file uploader
  2. A URL, which this module fetches and extracts text from — handling
     PDF, Markdown, and plain HTML pages

Extracted text is saved alongside the original so a later embedding/RAG
step (AI-FR-020) has clean text to chunk, without needing to re-parse
PDFs or HTML every time.
"""

from pathlib import Path
from urllib.parse import urlparse

import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup

from utils.storage import record_artifact

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_html_text(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def ingest_uploaded_files(uploaded_files) -> int:
    """
    Register Streamlit UploadedFile objects (PDF or Markdown).
    Returns the number of files recorded.
    """
    count = 0
    for uf in uploaded_files:
        raw_bytes = uf.read()
        suffix = Path(uf.name).suffix.lower()
        dest_path = DATA_DIR / uf.name
        dest_path.write_bytes(raw_bytes)

        if suffix == ".pdf":
            text = _extract_pdf_text(raw_bytes)
        else:  # treat everything else (e.g. .md, .txt) as plain text
            text = raw_bytes.decode("utf-8", errors="ignore")

        text_path = dest_path.with_suffix(dest_path.suffix + ".extracted.txt")
        text_path.write_text(text, encoding="utf-8")

        record_artifact(
            artifact_type="document",
            source_kind="upload",
            source_ref=uf.name,
            local_path=str(dest_path),
            display_name=uf.name,
            size_bytes=len(raw_bytes),
            meta={"extracted_text_path": str(text_path), "extension": suffix},
        )
        count += 1
    return count


def ingest_doc_from_url(url: str) -> int:
    """
    Fetch a document from a URL and register it, extracting text based on
    content type (PDF, Markdown, or HTML). Returns 1 on success.
    """
    resp = requests.get(url, timeout=30, headers={"User-Agent": "triage-poc/0.1"})
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "").lower()
    filename = Path(urlparse(url).path).name or "downloaded_document"

    is_pdf = "application/pdf" in content_type or filename.lower().endswith(".pdf")
    is_markdown = filename.lower().endswith(".md") or "text/markdown" in content_type

    dest_path = DATA_DIR / filename
    dest_path.write_bytes(resp.content)

    if is_pdf:
        text = _extract_pdf_text(resp.content)
    elif is_markdown or "text/plain" in content_type:
        text = resp.text
    else:
        text = _extract_html_text(resp.content)  # assume HTML otherwise

    text_path = dest_path.with_suffix(dest_path.suffix + ".extracted.txt")
    text_path.write_text(text, encoding="utf-8")

    record_artifact(
        artifact_type="document",
        source_kind="url",
        source_ref=url,
        local_path=str(dest_path),
        display_name=filename,
        size_bytes=len(resp.content),
        meta={
            "extracted_text_path": str(text_path),
            "content_type": content_type,
            "detected_as": "pdf" if is_pdf else ("markdown" if is_markdown else "html"),
        },
    )
    return 1
