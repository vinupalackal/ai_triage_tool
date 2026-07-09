"""
utils/storage.py

A thin tracking layer over DuckDB that records every artifact ingested into
the POC, regardless of which module or source brought it in. This is the
POC-scale stand-in for the "shared identifier schema" (Section 8.2 of the
requirements spec) — every artifact gets a consistent record so later
retrieval/agent code has one place to look, whether the artifact is source
code, a log file, or a document.
"""

import duckdb
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "poc.duckdb"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Return a DuckDB connection, creating the tracking table if needed."""
    con = duckdb.connect(str(DB_PATH))
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            id VARCHAR PRIMARY KEY,
            artifact_type VARCHAR,      -- 'code' | 'log' | 'document'
            source_kind VARCHAR,        -- 'local_folder' | 'git_url' | 'jira' | 'upload' | 'url'
            source_ref VARCHAR,         -- original path / URL / issue key the user gave us
            local_path VARCHAR,         -- where it actually lives on disk now
            display_name VARCHAR,       -- filename or short label for the UI
            size_bytes BIGINT,
            ingested_at TIMESTAMP,
            meta_json VARCHAR           -- free-form extra metadata (component, build id, etc.)
        )
        """
    )
    return con


def record_artifact(
    artifact_type: str,
    source_kind: str,
    source_ref: str,
    local_path: str,
    display_name: str,
    size_bytes: int = 0,
    meta: dict | None = None,
) -> str:
    """Insert one artifact record and return its generated id."""
    artifact_id = str(uuid.uuid4())
    con = get_connection()
    con.execute(
        "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            artifact_id,
            artifact_type,
            source_kind,
            source_ref,
            local_path,
            display_name,
            size_bytes,
            datetime.now(timezone.utc),
            json.dumps(meta or {}),
        ],
    )
    con.close()
    return artifact_id


def list_artifacts(artifact_type: str | None = None):
    """Return all tracked artifacts, optionally filtered by type, newest first."""
    con = get_connection()
    if artifact_type:
        rows = con.execute(
            "SELECT * FROM artifacts WHERE artifact_type = ? ORDER BY ingested_at DESC",
            [artifact_type],
        ).fetchdf()
    else:
        rows = con.execute("SELECT * FROM artifacts ORDER BY ingested_at DESC").fetchdf()
    con.close()
    return rows


def artifact_counts():
    """Quick summary counts per artifact type, for the sidebar/dashboard."""
    con = get_connection()
    df = con.execute(
        "SELECT artifact_type, COUNT(*) AS n FROM artifacts GROUP BY artifact_type"
    ).fetchdf()
    con.close()
    return dict(zip(df["artifact_type"], df["n"])) if not df.empty else {}


def _ensure_index_state_table(con):
    """Internal: create the index-state tracking table if it doesn't exist yet."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS index_state (
            artifact_id VARCHAR,
            index_table VARCHAR,   -- e.g. 'log_signatures', 'code_symbols', 'doc_chunks'
            index_id VARCHAR,      -- the id of the resulting row in that table
            indexed_at TIMESTAMP,
            PRIMARY KEY (artifact_id, index_table)
        )
        """
    )


def get_unindexed_artifacts(artifact_type: str, index_table: str):
    """
    Return artifacts of the given type that do NOT yet have a row in index_state
    for the given index_table. Lets the indexing layer (HLD Section 3.3) run
    incrementally instead of reprocessing every artifact on every call.
    """
    con = get_connection()
    _ensure_index_state_table(con)
    df = con.execute(
        """
        SELECT a.* FROM artifacts a
        LEFT JOIN index_state s
          ON a.id = s.artifact_id AND s.index_table = ?
        WHERE a.artifact_type = ? AND s.artifact_id IS NULL
        ORDER BY a.ingested_at
        """,
        [index_table, artifact_type],
    ).fetchdf()
    con.close()
    return df


def mark_indexed(artifact_id: str, index_table: str, index_id: str):
    """
    Record that an artifact has been indexed into the given output table,
    making re-ingestion-triggered re-indexing idempotent (HLD Section 2 / 3.2).
    Safe to call multiple times for the same artifact_id + index_table pair —
    it upserts rather than duplicating.
    """
    con = get_connection()
    _ensure_index_state_table(con)
    con.execute(
        """
        INSERT INTO index_state VALUES (?, ?, ?, ?)
        ON CONFLICT (artifact_id, index_table)
        DO UPDATE SET index_id = excluded.index_id, indexed_at = excluded.indexed_at
        """,
        [artifact_id, index_table, index_id, datetime.now(timezone.utc)],
    )
    con.close()
