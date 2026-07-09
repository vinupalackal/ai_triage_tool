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


def test_tag_components_supports_multiple_components_on_one_artifact():
    artifact_id = storage.record_artifact(
        "code", "git_url", "https://x/repo.git", "/tmp/lock.c", "lock.c", 100
    )
    storage.tag_components(artifact_id, ["Tuner", "Wi-Fi"])

    assert storage.get_components_for_artifact(artifact_id) == ["Tuner", "Wi-Fi"]


def test_tag_components_is_idempotent():
    artifact_id = storage.record_artifact(
        "code", "local_folder", "/tmp", "/tmp/a.c", "a.c", 10
    )
    storage.tag_components(artifact_id, ["Tuner"])
    storage.tag_components(artifact_id, ["Tuner"])  # re-tag, should not duplicate

    assert storage.get_components_for_artifact(artifact_id) == ["Tuner"]


def test_get_artifacts_by_component_maps_code_and_documents_separately():
    code_id = storage.record_artifact(
        "code", "git_url", "https://x/repo.git", "/tmp/lock.c", "lock.c", 100
    )
    doc_id = storage.record_artifact(
        "document", "upload", "spec.pdf", "/tmp/spec.pdf", "spec.pdf", 200
    )
    storage.tag_components(code_id, ["Tuner"])
    storage.tag_components(doc_id, ["Tuner"])

    tuner_code = storage.get_artifacts_by_component("Tuner", "code")
    tuner_docs = storage.get_artifacts_by_component("Tuner", "document")
    wifi_docs = storage.get_artifacts_by_component("Wi-Fi", "document")

    assert len(tuner_code) == 1
    assert len(tuner_docs) == 1
    assert len(wifi_docs) == 0  # untagged component returns nothing, not an error


def test_list_known_components_returns_distinct_sorted_names():
    id1 = storage.record_artifact("code", "local_folder", "/tmp", "/tmp/a.c", "a.c", 10)
    id2 = storage.record_artifact("code", "local_folder", "/tmp", "/tmp/b.c", "b.c", 10)
    storage.tag_components(id1, ["Wi-Fi"])
    storage.tag_components(id2, ["Tuner", "Wi-Fi"])  # Wi-Fi repeated on purpose

    assert storage.list_known_components() == ["Tuner", "Wi-Fi"]


def test_component_cache_available_reflects_actual_data():
    assert storage.component_cache_available("Tuner", "code") is False

    artifact_id = storage.record_artifact(
        "code", "local_folder", "/tmp", "/tmp/a.c", "a.c", 10
    )
    storage.tag_components(artifact_id, ["Tuner"])

    assert storage.component_cache_available("Tuner", "code") is True
    assert storage.component_cache_available("Tuner", "document") is False  # type-specific
