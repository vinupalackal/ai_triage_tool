"""
retrieval/models.py

Shared dataclasses for the retrieval layer's outputs, matching the High-
Level Design, Section 3.4.
"""

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """One ranked hit from hybrid_search, tagged with which method(s) matched it."""
    artifact_id: str
    chunk_or_symbol_id: str
    text_snippet: str
    score: float
    matched_by: list[str] = field(default_factory=list)  # e.g. ["vector", "keyword"]


@dataclass
class GraphPath:
    """One traversal result from graph_query — a chain of connected artifacts."""
    nodes: list[str]          # artifact_ids in path order
    relationships: list[str]  # relationship labels between consecutive nodes
