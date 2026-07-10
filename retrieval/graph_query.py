"""
retrieval/graph_query.py  —  MVP scope, not yet implemented

Design reference: High-Level Design, Section 3.4.
Requirement references: AI-FR-030, AI-FR-031, AI-FR-032.

Wraps a NetworkX in-memory graph built from the graph_edges table, exposing
a small, fixed set of traversal shapes rather than an arbitrary query
language — sufficient for the MVP's needs per the design decision recorded
in HLD Section 8 (NetworkX vs. embedding graph edges directly in DuckDB).

Supports Generic Issue Triage Skill Step 4 (Correlate Logs & External Events):
Traverses relationships (commit→file→component, component→log signature,
document→component, etc.) to identify correlations and validate root-cause
hypotheses against the artifact dependency graph.
"""

from .models import GraphPath

# The fixed set of traversal shapes this module supports at MVP scope.
# Extend this list (and the dispatch logic in graph_query) as new
# relationship questions come up during real investigations.
SUPPORTED_QUERY_SHAPES = [
    "commits_touching_component",   # args: component, since_days
    "components_for_log_signature", # args: signature_id
    "documents_for_component",      # args: component
    "incidents_for_commit",         # args: commit_sha
]


def graph_query(query_shape: str, **kwargs) -> list[GraphPath]:
    """
    Run one of the fixed traversal shapes in SUPPORTED_QUERY_SHAPES against
    the in-memory graph built from graph_edges.

    Example:
        graph_query("commits_touching_component", component="Tuner", since_days=7)

    Raises:
        ValueError: if query_shape is not in SUPPORTED_QUERY_SHAPES.
    """
    if query_shape not in SUPPORTED_QUERY_SHAPES:
        raise ValueError(
            f"Unsupported query shape '{query_shape}'. "
            f"Supported: {SUPPORTED_QUERY_SHAPES}"
        )
    raise NotImplementedError(
        "retrieval.graph_query is designed (HLD 3.4) but not yet "
        "implemented. Depends on graph_edges being populated by the "
        "indexing layer first."
    )
