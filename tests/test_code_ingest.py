"""
tests/test_code_ingest.py

Tests for ingestion/code_ingest.py. The git-clone path is marked
'network' and skipped by default (see pytest.ini / -m "not network") since
it requires outbound internet access.
"""

import pytest
from ingestion import code_ingest
from utils import storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.duckdb")
    yield


def test_ingest_local_code_folder_registers_recognized_files(tmp_path):
    (tmp_path / "lock.c").write_text(
        "int tuner_lock_retry(int freq) { return retry_timer(freq); }\n"
    )
    (tmp_path / "lock.h").write_text("int tuner_lock_retry(int freq);\n")
    (tmp_path / "notes.docx").write_bytes(b"not a source file")  # should be skipped

    artifact_ids = code_ingest.ingest_local_code_folder(str(tmp_path))
    assert len(artifact_ids) == 2
    assert all(isinstance(a, str) for a in artifact_ids)

    df = storage.list_artifacts("code")
    names = set(df["display_name"])
    assert names == {"lock.c", "lock.h"}


def test_ingest_local_code_folder_rejects_invalid_path():
    with pytest.raises(ValueError):
        code_ingest.ingest_local_code_folder("/definitely/does/not/exist")


@pytest.mark.network
def test_ingest_code_from_git_url_clones_and_registers():
    # A small, stable public repo used only to verify the clone+walk mechanics.
    artifact_ids = code_ingest.ingest_code_from_git_url(
        "https://github.com/octocat/Hello-World.git"
    )
    # This particular repo has no matching source extensions — the assertion
    # that matters is that the clone succeeded without raising.
    assert isinstance(artifact_ids, list)
