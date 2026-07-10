"""
indexing/doc_embedding.py  —  MVP scope, not yet implemented

Design reference: High-Level Design, Section 3.3.3.
Requirement reference: AI-FR-020.

Chunks documents at semantic (paragraph/section) boundaries with overlap and
embeds each chunk with a local sentence-transformers model — no external API
call, keeping indexing free and offline-capable. Writes results to the
`doc_chunks` table via `utils.storage`.

Supports Generic Issue Triage Skill Steps 2–4 (Define, Classify, Correlate):
Extracts semantic chunks so design intent, past incidents, and documented
anomalies can be retrieved and cross-checked when characterizing root cause.
"""

from .models import DocChunk


def embed_document(artifact_id: str) -> list[DocChunk]:
    """
    Read the extracted text for the given document artifact_id (see
    ingestion/doc_ingest.py, which already produces a <file>.extracted.txt
    alongside every ingested document), chunk it at semantic boundaries with
    overlap, embed each chunk, and return the resulting DocChunks.
    Implementations should persist results to doc_chunks and call
    utils.storage.mark_indexed() per chunk, per HLD Section 3.2.

    Raises:
        ValueError: if artifact_id does not correspond to a known document artifact.
    """
    raise NotImplementedError(
        "doc_embedding.embed_document is designed (HLD 3.3.3) but not yet "
        "implemented. See AI-FR-020 in the Requirements Specification."
    )
