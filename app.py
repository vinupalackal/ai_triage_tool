"""
app.py

Streamlit POC — data ingestion screen.

Provisions the three data types from the requirements spec (Section 4) into
local storage, each from either a local path or a remote source:

  Source code  -> local folder  OR  git URL (cloned)
  Logs         -> local folder  OR  Jira issue URL (attachments downloaded)
  Documents    -> uploaded PDF/Markdown files  OR  a URL (PDF/MD/HTML fetched)

This screen only handles provisioning. Indexing (templating, embeddings,
the knowledge graph) and the agent are separate, later pieces that read
from what's tracked here via utils.storage.
"""

import streamlit as st

from ingestion.code_ingest import ingest_local_code_folder, ingest_code_from_git_url
from ingestion.log_ingest import ingest_local_log_folder, ingest_logs_from_jira
from ingestion.doc_ingest import ingest_uploaded_files, ingest_doc_from_url
from utils.storage import list_artifacts, artifact_counts

st.set_page_config(page_title="Triage POC — Data Ingestion", layout="wide")

st.title("Triage POC — data ingestion")
st.caption(
    "Feed source code, logs, and documents from either a local path or a "
    "remote source. Everything ingested here is tracked in one place, "
    "regardless of where it came from."
)

counts = artifact_counts()
c1, c2, c3 = st.columns(3)
c1.metric("Code files", counts.get("code", 0))
c2.metric("Log files", counts.get("log", 0))
c3.metric("Documents", counts.get("document", 0))

tab_code, tab_logs, tab_docs, tab_browse = st.tabs(
    ["Source code", "Logs", "Documents", "Ingested artifacts"]
)

# ----------------------------------------------------------------------
# SOURCE CODE
# ----------------------------------------------------------------------
with tab_code:
    st.subheader("Add source code")
    mode = st.radio(
        "Where is the code coming from?",
        ["Local folder", "Git URL"],
        horizontal=True,
        key="code_mode",
    )

    if mode == "Local folder":
        folder = st.text_input(
            "Local folder path",
            placeholder="/home/user/repos/rdk-tuner-driver",
            key="code_folder",
        )
        if st.button("Ingest code folder", key="code_folder_btn"):
            if not folder:
                st.warning("Enter a folder path first.")
            else:
                try:
                    with st.spinner("Scanning folder..."):
                        n = ingest_local_code_folder(folder)
                    st.success(f"Registered {n} source files from {folder}.")
                except Exception as e:
                    st.error(str(e))

    else:  # Git URL
        git_url = st.text_input(
            "Git repository URL",
            placeholder="https://github.com/org/rdk-tuner-driver.git",
            key="code_git_url",
        )
        branch = st.text_input(
            "Branch (optional)", placeholder="main", key="code_git_branch"
        )
        st.caption(
            "For private repos, include a token in the URL "
            "(https://<token>@github.com/org/repo.git) or configure a git "
            "credential helper before running this app."
        )
        if st.button("Clone and ingest", key="code_git_btn"):
            if not git_url:
                st.warning("Enter a git URL first.")
            else:
                try:
                    with st.spinner(f"Cloning {git_url}..."):
                        n = ingest_code_from_git_url(git_url, branch or None)
                    st.success(f"Cloned and registered {n} source files.")
                except Exception as e:
                    st.error(str(e))

# ----------------------------------------------------------------------
# LOGS
# ----------------------------------------------------------------------
with tab_logs:
    st.subheader("Add logs")
    mode = st.radio(
        "Where are the logs coming from?",
        ["Local folder", "Jira issue URL"],
        horizontal=True,
        key="log_mode",
    )

    if mode == "Local folder":
        folder = st.text_input(
            "Local folder path",
            placeholder="/home/user/device-logs/xr400-unit-07",
            key="log_folder",
        )
        if st.button("Ingest log folder", key="log_folder_btn"):
            if not folder:
                st.warning("Enter a folder path first.")
            else:
                try:
                    with st.spinner("Scanning folder..."):
                        n = ingest_local_log_folder(folder)
                    st.success(f"Registered {n} log files from {folder}.")
                except Exception as e:
                    st.error(str(e))

    else:  # Jira
        issue_url = st.text_input(
            "Jira issue URL",
            placeholder="https://yourcompany.atlassian.net/browse/PROJ-1234",
            key="log_jira_url",
        )
        col1, col2 = st.columns(2)
        email = col1.text_input("Jira account email", key="log_jira_email")
        api_token = col2.text_input(
            "Jira API token", type="password", key="log_jira_token"
        )
        st.caption(
            "Generate a token at "
            "https://id.atlassian.com/manage-profile/security/api-tokens — "
            "not stored anywhere beyond this session."
        )
        only_logs = st.checkbox(
            "Only download log-like attachments (.log, .txt, .gz, .zip, .json)",
            value=True,
            key="log_jira_filter",
        )
        if st.button("Fetch attachments from Jira", key="log_jira_btn"):
            if not (issue_url and email and api_token):
                st.warning("Issue URL, email, and API token are all required.")
            else:
                try:
                    with st.spinner("Fetching attachments from Jira..."):
                        n = ingest_logs_from_jira(
                            issue_url, email, api_token, only_log_like=only_logs
                        )
                    if n == 0:
                        st.info("No matching attachments found on that issue.")
                    else:
                        st.success(f"Downloaded and registered {n} log files.")
                except Exception as e:
                    st.error(str(e))

# ----------------------------------------------------------------------
# DOCUMENTS
# ----------------------------------------------------------------------
with tab_docs:
    st.subheader("Add documents")
    mode = st.radio(
        "Where are the documents coming from?",
        ["Upload files", "URL"],
        horizontal=True,
        key="doc_mode",
    )

    if mode == "Upload files":
        uploaded = st.file_uploader(
            "Upload PDF or Markdown files",
            type=["pdf", "md", "txt"],
            accept_multiple_files=True,
            key="doc_uploader",
        )
        if st.button("Ingest uploaded files", key="doc_upload_btn"):
            if not uploaded:
                st.warning("Upload at least one file first.")
            else:
                try:
                    with st.spinner("Extracting text..."):
                        n = ingest_uploaded_files(uploaded)
                    st.success(f"Registered {n} documents.")
                except Exception as e:
                    st.error(str(e))

    else:  # URL
        doc_url = st.text_input(
            "Document URL",
            placeholder="https://example.com/tuner-design-spec.pdf",
            key="doc_url",
        )
        st.caption("Handles PDF, Markdown, and plain HTML pages automatically.")
        if st.button("Fetch and ingest", key="doc_url_btn"):
            if not doc_url:
                st.warning("Enter a URL first.")
            else:
                try:
                    with st.spinner(f"Fetching {doc_url}..."):
                        ingest_doc_from_url(doc_url)
                    st.success("Document fetched, extracted, and registered.")
                except Exception as e:
                    st.error(str(e))

# ----------------------------------------------------------------------
# BROWSE WHAT'S BEEN INGESTED
# ----------------------------------------------------------------------
with tab_browse:
    st.subheader("Everything ingested so far")
    filter_type = st.selectbox(
        "Filter by type", ["All", "code", "log", "document"], key="browse_filter"
    )
    df = list_artifacts(None if filter_type == "All" else filter_type)
    if df.empty:
        st.info("Nothing ingested yet — use the tabs above to add code, logs, or documents.")
    else:
        st.dataframe(
            df[
                [
                    "artifact_type",
                    "source_kind",
                    "source_ref",
                    "display_name",
                    "size_bytes",
                    "ingested_at",
                ]
            ],
            use_container_width=True,
        )
