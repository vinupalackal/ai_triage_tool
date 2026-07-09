"""
ingestion/code_ingest.py

Provisions source code into the POC from either:
  1. A local folder path already on disk (e.g. a repo checked out by the user)
  2. A git URL, which this module clones locally

Every ingested file is recorded via utils.storage so downstream indexing
(AI-FR-010 style precise indexing, or a simple embedding pass) has a
consistent list to work from, regardless of how the code arrived.
"""

import shutil
import subprocess
from pathlib import Path

from utils.storage import record_artifact

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "code"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Extensions we care about for an embedded C/C++ firmware codebase.
# Extend this list as needed for other languages.
CODE_EXTENSIONS = {".c", ".h", ".cpp", ".hpp", ".cc", ".py", ".js", ".ts", ".java"}


def _walk_and_record(root: Path, source_kind: str, source_ref: str) -> list[str]:
    """Walk a directory tree, recording each recognized source file. Returns the new artifact ids."""
    artifact_ids = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in CODE_EXTENSIONS:
            artifact_id = record_artifact(
                artifact_type="code",
                source_kind=source_kind,
                source_ref=source_ref,
                local_path=str(path),
                display_name=str(path.relative_to(root)),
                size_bytes=path.stat().st_size,
                meta={"extension": path.suffix.lower()},
            )
            artifact_ids.append(artifact_id)
    return artifact_ids


def ingest_local_code_folder(folder_path: str) -> list[str]:
    """
    Register a local folder that already contains source code.
    Returns the list of newly created artifact ids (len() gives the file count).
    """
    root = Path(folder_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"'{folder_path}' is not a valid, accessible directory.")
    return _walk_and_record(root, source_kind="local_folder", source_ref=str(root))


def ingest_code_from_git_url(git_url: str, branch: str | None = None) -> list[str]:
    """
    Clone a git repository into the local data directory, then register its files.
    Returns the list of newly created artifact ids (len() gives the file count).

    Requires `git` to be available on PATH. For private repos, embed credentials
    in the URL (https://<token>@github.com/org/repo.git) or configure a local
    git credential helper before running the app — this POC does not manage
    secrets for you here.
    """
    repo_name = git_url.rstrip("/").split("/")[-1].removesuffix(".git")
    dest = DATA_DIR / repo_name

    if dest.exists():
        shutil.rmtree(dest)  # simple POC behavior: always re-clone fresh

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [git_url, str(dest)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed:\n{result.stderr}")

    return _walk_and_record(dest, source_kind="git_url", source_ref=git_url)
