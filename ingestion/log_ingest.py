"""
ingestion/log_ingest.py

Provisions logs into the POC from either:
  1. A local folder path containing log files
  2. A Jira issue URL, from which this module downloads matching attachments
     (e.g. a customer/field report ticket with a device log bundle attached)

This intentionally mirrors the "standalone mode" requirement from the spec
(AI-FR-007 / A.1.1): no fleet telemetry pipeline is assumed. You point it at
whatever handful of log sources you have for a given investigation.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from utils.storage import record_artifact

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_EXTENSIONS = {".log", ".txt", ".gz", ".tar", ".tgz", ".zip", ".json", ".bin"}


def ingest_local_log_folder(folder_path: str) -> int:
    """
    Register every file in a local folder as a log artifact.
    Returns the number of files recorded.
    """
    root = Path(folder_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"'{folder_path}' is not a valid, accessible directory.")

    count = 0
    for path in root.rglob("*"):
        if path.is_file():
            record_artifact(
                artifact_type="log",
                source_kind="local_folder",
                source_ref=str(root),
                local_path=str(path),
                display_name=str(path.relative_to(root)),
                size_bytes=path.stat().st_size,
            )
            count += 1
    return count


def _parse_jira_issue_url(issue_url: str) -> tuple[str, str]:
    """
    Given a Jira issue URL like https://yourcompany.atlassian.net/browse/PROJ-123,
    return (base_url, issue_key).
    """
    parsed = urlparse(issue_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    match = re.search(r"([A-Z][A-Z0-9]+-\d+)", issue_url)
    if not match:
        raise ValueError(
            "Could not find a Jira issue key (e.g. PROJ-123) in the URL provided."
        )
    return base_url, match.group(1)


def ingest_logs_from_jira(
    issue_url: str,
    email: str,
    api_token: str,
    only_log_like: bool = True,
) -> int:
    """
    Fetch attachments from a Jira issue and register the log-like ones.
    Uses Jira Cloud REST API v2 with basic auth (email + API token) —
    generate a token at https://id.atlassian.com/manage-profile/security/api-tokens

    Returns the number of files downloaded and recorded.
    """
    base_url, issue_key = _parse_jira_issue_url(issue_url)
    api_url = f"{base_url}/rest/api/2/issue/{issue_key}"

    resp = requests.get(
        api_url,
        params={"fields": "attachment"},
        auth=(email, api_token),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    attachments = resp.json().get("fields", {}).get("attachment", [])

    if not attachments:
        return 0

    dest_dir = DATA_DIR / issue_key
    dest_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for att in attachments:
        filename = att["filename"]
        ext = Path(filename).suffix.lower()
        if only_log_like and ext not in LOG_EXTENSIONS:
            continue

        file_resp = requests.get(
            att["content"], auth=(email, api_token), timeout=60
        )
        file_resp.raise_for_status()

        local_path = dest_dir / filename
        local_path.write_bytes(file_resp.content)

        record_artifact(
            artifact_type="log",
            source_kind="jira",
            source_ref=issue_url,
            local_path=str(local_path),
            display_name=filename,
            size_bytes=len(file_resp.content),
            meta={"jira_issue_key": issue_key, "jira_attachment_id": att.get("id")},
        )
        count += 1

    return count
