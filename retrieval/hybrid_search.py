"""
retrieval/hybrid_search.py  —  MVP scope, not yet implemented

Design reference: High-Level Design, Section 3.4.
Requirement references: AI-FR-050, AI-FR-051.

Combines three retrieval strategies and merges results with reciprocal rank
fusion: a Chroma similarity search over doc_chunks and code_symbols, a
rank_bm25 keyword search over the same text, and — where the query names a
known artifact — a one-hop graph_edges lookup. See design_decisions in the
High-Level Design (Section 8) for why RRF was chosen over weighted score
averaging.
"""

from .models import SearchResult


def hybrid_search(
    query: str,
    artifact_type: str | None = None,
    top_k: int = 10,
) -> list[SearchResult]:
    """
    Run vector + keyword + graph retrieval in parallel and return a single
    ranked, merged result list (AI-FR-050). Exact-match identifiers (error
    codes, symbol names) should not be diluted by semantic similarity
    (AI-FR-051) — the keyword path is what guarantees this.

    Args:
        query: free-text or exact-identifier query string.
        artifact_type: restrict to "code" or "document", or None for both.
        top_k: maximum number of results to return.
    """
    raise NotImplementedError(
        "retrieval.hybrid_search is designed (HLD 3.4) but not yet "
        "implemented. Depends on the indexing layer (indexing/) being "
        "implemented first, since it reads from code_symbols and doc_chunks."
    )
