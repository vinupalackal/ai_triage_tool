"""
indexing/models.py

Shared dataclasses for the indexing layer's outputs, matching the return
types specified in the High-Level Design, Section 3.3. Defined once here so
log_templating.py, code_chunking.py, and doc_embedding.py (and the retrieval
layer that reads their output) all agree on shape.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LogTemplate:
    """One templated log pattern extracted from a log file (HLD 3.3.1)."""
    signature_id: str
    template_text: str
    occurrence_count: int
    artifact_id: str
    component: Optional[str] = None


@dataclass
class Commit:
    """One commit touching a file/function, from git history (HLD 3.3.2)."""
    sha: str
    author: str
    date: str
    message: str


@dataclass
class CodeChunk:
    """One function-level chunk of source code (HLD 3.3.2)."""
    symbol_id: str
    artifact_id: str
    function_name: str
    file_path: str
    line_start: int
    line_end: int
    commit_sha: Optional[str] = None
    embedding_vector: Optional[list[float]] = None


@dataclass
class DocChunk:
    """One semantic chunk of a document, embedded (HLD 3.3.3)."""
    chunk_id: str
    artifact_id: str
    chunk_text: str
    embedding_vector: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)
