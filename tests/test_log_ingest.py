"""
tests/test_log_ingest.py

Tests for ingestion/log_ingest.py. Jira attachment download itself requires
real credentials and is not tested here — only the pure URL-parsing logic
and the local-folder path, which don't need network access or secrets.
"""

import pytest
from ingestion import log_ingest
from utils import storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.duckdb")
    yield


def test_ingest_local_log_folder_registers_all_files(tmp_path):
    (tmp_path / "syslog.txt").write_text("some log content\n")
    (tmp_path / "crash.bin").write_bytes(b"\x00\x01\x02")

    count = log_ingest.ingest_local_log_folder(str(tmp_path))
    assert count == 2


@pytest.mark.parametrize(
    "url,expected_key",
    [
        ("https://yourcompany.atlassian.net/browse/PROJ-1234", "PROJ-1234"),
        (
            "https://yourcompany.atlassian.net/jira/software/projects/PROJ/"
            "issues/PROJ-1234?filter=allissues",
            "PROJ-1234",
        ),
    ],
)
def test_parse_jira_issue_url(url, expected_key):
    base_url, issue_key = log_ingest._parse_jira_issue_url(url)
    assert issue_key == expected_key
    assert base_url == "https://yourcompany.atlassian.net"


def test_parse_jira_issue_url_raises_without_a_key():
    with pytest.raises(ValueError):
        log_ingest._parse_jira_issue_url("https://yourcompany.atlassian.net/browse/")
