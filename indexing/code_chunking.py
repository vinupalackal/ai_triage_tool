"""
indexing/code_chunking.py  —  MVP scope, not yet implemented

Design reference: High-Level Design, Section 3.3.2.
Requirement references: AI-FR-012, AI-FR-016.

Chunks source files at function boundaries (tree-sitter is the intended
implementation basis, matching the embedded C/C++ codebases this system is
designed around) and extracts per-file/function commit history via
GitPython. Writes results to the `code_symbols` table via `utils.storage`.

Supports Generic Issue Triage Skill Steps 2–3 (Define & Classify):
Extracts code structure so functions and their recent changes can be
navigated when tracing from symptom to responsible code location.
"""

from .models import CodeChunk, Commit


def chunk_source_file(artifact_id: str) -> list[CodeChunk]:
    """
    Read the source file for the given artifact_id, parse it with tree-sitter,
    and return one CodeChunk per function/class definition found. Implementations
    should persist results to code_symbols and call utils.storage.mark_indexed()
    per chunk, per HLD Section 3.2.

    Raises:
        ValueError: if artifact_id does not correspond to a known code artifact.
    """
    raise NotImplementedError(
        "code_chunking.chunk_source_file is designed (HLD 3.3.2) but not yet "
        "implemented. See AI-FR-012 in the Requirements Specification."
    )


def extract_commit_history(repo_path: str, file_path: str) -> list[Commit]:
    """
    Return the ordered commit history for a given file within a git repository,
    most recent first, via GitPython (AI-FR-016).
    """
    raise NotImplementedError(
        "code_chunking.extract_commit_history is designed (HLD 3.3.2) but "
        "not yet implemented."
    )
