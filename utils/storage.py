"""
utils/storage.py

A thin tracking layer over DuckDB that records every artifact ingested into
the POC, regardless of which module or source brought it in. This is the
POC-scale stand-in for the "shared identifier schema" (Section 8.2 of the
requirements spec) — every artifact gets a consistent record so later
retrieval/agent code has one place to look, whether the artifact is source
code, a log file, or a document.

Supports Generic Issue Triage Skill Step 1 (Orient to Artifacts):
Builds and maintains the unified artifact index used to navigate logs, code,
and documents as a cohesive corpus during investigation. Component tagging
enables Step 1's "organize by component" substep.
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


# ---------------------------------------------------------------------------
# Component tagging, component -> artifact mapping, and the ingestion cache
# ---------------------------------------------------------------------------
#
# A "component" here is the same concept as the `component` field in the
# shared identifier schema (Requirements Specification, Section 8.2) — a
# subsystem name like "Tuner" or "Wi-Fi". Source code and documents are
# tagged with one or more components at ingestion time. This mapping serves
# two purposes:
#
#   1. It IS the component -> documents (and component -> code) lookup —
#      get_artifacts_by_component() answers "what do we have for Tuner?"
#      across both code and documents with the same function.
#   2. It backs the ingestion cache: if a component already has code (or
#      document) artifacts tracked, ingestion for that component/type can be
#      skipped entirely and the caller reads the existing rows instead of
#      re-cloning a repo or re-fetching documents.

def _ensure_component_table(con):
    """Internal: create the artifact<->component mapping table if needed."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS artifact_components (
            artifact_id VARCHAR,
            component VARCHAR,
            tagged_at TIMESTAMP,
            PRIMARY KEY (artifact_id, component)
        )
        """
    )


def tag_components(artifact_id: str, components: list[str]):
    """
    Associate an artifact (a code file or a document) with one or more
    components. Safe to call repeatedly — re-tagging with the same
    component is a no-op, not a duplicate row.
    """
    con = get_connection()
    _ensure_component_table(con)
    now = datetime.now(timezone.utc)
    for component in components:
        component = component.strip()
        if not component:
            continue
        con.execute(
            """
            INSERT INTO artifact_components VALUES (?, ?, ?)
            ON CONFLICT (artifact_id, component) DO NOTHING
            """,
            [artifact_id, component, now],
        )
    con.close()


def get_components_for_artifact(artifact_id: str) -> list[str]:
    """Return every component a given artifact has been tagged with."""
    con = get_connection()
    _ensure_component_table(con)
    df = con.execute(
        "SELECT component FROM artifact_components WHERE artifact_id = ? ORDER BY component",
        [artifact_id],
    ).fetchdf()
    con.close()
    return list(df["component"]) if not df.empty else []


def get_artifacts_by_component(component: str, artifact_type: str | None = None):
    """
    The component -> artifact mapping lookup. Returns every artifact (code
    file or document, or both) tagged with the given component, newest first.
    This is what a UI or the retrieval layer calls to answer "what code and
    documents do we have for the Tuner component?"
    """
    con = get_connection()
    _ensure_component_table(con)
    query = """
        SELECT a.* FROM artifacts a
        JOIN artifact_components c ON a.id = c.artifact_id
        WHERE c.component = ?
    """
    params = [component]
    if artifact_type:
        query += " AND a.artifact_type = ?"
        params.append(artifact_type)
    query += " ORDER BY a.ingested_at DESC"
    df = con.execute(query, params).fetchdf()
    con.close()
    return df


def list_known_components() -> list[str]:
    """All distinct component names tagged so far, for populating a picker."""
    con = get_connection()
    _ensure_component_table(con)
    df = con.execute(
        "SELECT DISTINCT component FROM artifact_components ORDER BY component"
    ).fetchdf()
    con.close()
    return list(df["component"]) if not df.empty else []


def component_cache_available(component: str, artifact_type: str) -> bool:
    """
    The cache check: does this component already have at least one artifact
    of the given type tracked? If True, the caller should skip re-running
    ingestion (re-cloning a repo, re-downloading/re-extracting a document)
    and instead read the existing rows via get_artifacts_by_component() —
    the "respective database" the cached data already lives in.
    """
    df = get_artifacts_by_component(component, artifact_type)
    return not df.empty

