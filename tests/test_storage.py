"""
tests/test_storage.py

Tests for utils/storage.py — the tracking layer. Uses a fresh temp DuckDB
file per test via monkeypatching DB_PATH, so tests don't collide with each
other or with real data/poc.duckdb.
"""

import pytest
from utils import storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point the storage module at a throwaway DuckDB file for each test."""
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.duckdb")
    yield


def test_record_and_list_artifacts():
    artifact_id = storage.record_artifact(
        artifact_type="code",
        source_kind="local_folder",
        source_ref="/tmp/fake",
        local_path="/tmp/fake/a.c",
        display_name="a.c",
        size_bytes=123,
        meta={"extension": ".c"},
    )
    assert artifact_id

    df = storage.list_artifacts("code")
    assert len(df) == 1
    assert df.iloc[0]["display_name"] == "a.c"
    assert df.iloc[0]["size_bytes"] == 123


def test_artifact_counts_groups_by_type():
    storage.record_artifact("code", "local_folder", "/tmp", "/tmp/a.c", "a.c", 10)
    storage.record_artifact("log", "local_folder", "/tmp", "/tmp/a.log", "a.log", 10)
    storage.record_artifact("log", "local_folder", "/tmp", "/tmp/b.log", "b.log", 10)

    counts = storage.artifact_counts()
    assert counts == {"code": 1, "log": 2}


def test_get_unindexed_artifacts_excludes_marked_ones():
    id1 = storage.record_artifact("log", "local_folder", "/tmp", "/tmp/a.log", "a.log", 10)
    id2 = storage.record_artifact("log", "local_folder", "/tmp", "/tmp/b.log", "b.log", 10)

    unindexed = storage.get_unindexed_artifacts("log", "log_signatures")
    assert len(unindexed) == 2

    storage.mark_indexed(id1, "log_signatures", "sig_001")
    unindexed = storage.get_unindexed_artifacts("log", "log_signatures")
    assert len(unindexed) == 1
    assert unindexed.iloc[0]["id"] == id2


def test_mark_indexed_is_idempotent():
    artifact_id = storage.record_artifact(
        "log", "local_folder", "/tmp", "/tmp/a.log", "a.log", 10
    )
    storage.mark_indexed(artifact_id, "log_signatures", "sig_001")
    storage.mark_indexed(artifact_id, "log_signatures", "sig_001_updated")  # re-mark

    unindexed = storage.get_unindexed_artifacts("log", "log_signatures")
    assert len(unindexed) == 0  # still excluded, not duplicated
