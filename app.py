"""
app.py

Streamlit MVP — data ingestion + investigation screen.

Provisions the three data types from the requirements spec (Section 4) into
local storage, each from either a local path or a remote source:

  Source code  -> local folder  OR  git URL (cloned)
  Logs         -> local folder  OR  Jira issue URL (attachments downloaded)
  Documents    -> uploaded PDF/Markdown files  OR  a URL (PDF/MD/HTML fetched)

The "Investigate" tab is the front door to the agent layer designed in the
High-Level Design (Section 3.5) — it calls the real agent.loop.investigate()
interface, which currently raises NotImplementedError until the indexing
and retrieval layers underneath it are built. This tab exists so the app's
visible shape matches its full intended scope, not just the ingestion slice
that happens to be implemented first.
"""

import streamlit as st
import pandas as pd

from ingestion.code_ingest import ingest_local_code_folder, ingest_code_from_git_url
from ingestion.log_ingest import ingest_local_log_folder, ingest_logs_from_jira
from ingestion.doc_ingest import ingest_uploaded_files, ingest_doc_from_url
from utils.storage import (
    list_artifacts,
    artifact_counts,
    tag_components,
    get_artifacts_by_component,
    list_known_components,
    component_cache_available,
)
from agent.tools import TOOL_DEFINITIONS
from agent.loop import investigate


def _parse_components(raw: str) -> list[str]:
    """Split a comma-separated component input into a clean list, e.g. 'Tuner, Wi-Fi' -> ['Tuner', 'Wi-Fi']."""
    return [c.strip() for c in raw.split(",") if c.strip()]


def _cached_artifacts_for_components(components: list[str], artifact_type: str) -> pd.DataFrame:
    """Union of existing artifacts across all given components, for displaying a cache hit."""
    frames = [get_artifacts_by_component(c, artifact_type) for c in components]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).drop_duplicates(subset="id")


def _all_components_cached(components: list[str], artifact_type: str) -> bool:
    """Cache hit only when every requested component already has data of this type."""
    return bool(components) and all(
        component_cache_available(c, artifact_type) for c in components
    )

st.set_page_config(page_title="Triage MVP", layout="wide")

st.title("Triage MVP")
st.caption(
    "Feed source code, logs, and documents from either a local path or a "
    "remote source, then ask a question and get an AI-proposed root cause "
    "with citations. Everything ingested is tracked in one place, "
    "regardless of where it came from."
)

counts = artifact_counts()
c1, c2, c3 = st.columns(3)
c1.metric("Code files", counts.get("code", 0))
c2.metric("Log files", counts.get("log", 0))
c3.metric("Documents", counts.get("document", 0))

tab_code, tab_logs, tab_docs, tab_components, tab_investigate, tab_browse = st.tabs(
    ["Source code", "Logs", "Documents", "Components", "Investigate", "Ingested artifacts"]
)

# ----------------------------------------------------------------------
# SOURCE CODE
# ----------------------------------------------------------------------
with tab_code:
    st.subheader("Add source code")

    code_components_raw = st.text_input(
        "Component name(s) — comma-separated if the code serves more than one "
        "(e.g. shared utility code used by both Tuner and Wi-Fi)",
        placeholder="Tuner, Wi-Fi",
        key="code_components_input",
    )
    code_components = _parse_components(code_components_raw)
    code_force_refresh = st.checkbox(
        "Force refresh (ignore cache and re-ingest even if this component is already cached)",
        key="code_force_refresh",
    )
    if code_components:
        st.caption(f"Will tag ingested files with: {', '.join(code_components)}")

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
            elif code_components and not code_force_refresh and _all_components_cached(code_components, "code"):
                cached = _cached_artifacts_for_components(code_components, "code")
                st.info(
                    f"Cache hit — {len(cached)} code file(s) already ingested for "
                    f"component(s) {', '.join(code_components)}. Skipping "
                    f"re-ingestion and reading from the tracking database "
                    f"instead. Check \"Force refresh\" above to re-ingest anyway."
                )
                st.dataframe(cached[["display_name", "source_kind", "ingested_at"]], use_container_width=True)
            else:
                try:
                    with st.spinner("Scanning folder..."):
                        artifact_ids = ingest_local_code_folder(folder)
                        if code_components:
                            for aid in artifact_ids:
                                tag_components(aid, code_components)
                    st.success(f"Registered {len(artifact_ids)} source files from {folder}.")
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
            elif code_components and not code_force_refresh and _all_components_cached(code_components, "code"):
                cached = _cached_artifacts_for_components(code_components, "code")
                st.info(
                    f"Cache hit — {len(cached)} code file(s) already ingested for "
                    f"component(s) {', '.join(code_components)}. Skipping the "
                    f"git clone and reading from the tracking database instead. "
                    f"Check \"Force refresh\" above to re-clone anyway."
                )
                st.dataframe(cached[["display_name", "source_kind", "ingested_at"]], use_container_width=True)
            else:
                try:
                    with st.spinner(f"Cloning {git_url}..."):
                        artifact_ids = ingest_code_from_git_url(git_url, branch or None)
                        if code_components:
                            for aid in artifact_ids:
                                tag_components(aid, code_components)
                    st.success(f"Cloned and registered {len(artifact_ids)} source files.")
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

    doc_components_raw = st.text_input(
        "Component name(s) — comma-separated if this document covers more than one "
        "(e.g. a shared platform spec)",
        placeholder="Tuner",
        key="doc_components_input",
    )
    doc_components = _parse_components(doc_components_raw)
    doc_force_refresh = st.checkbox(
        "Force refresh (ignore cache and re-ingest even if this component is already cached)",
        key="doc_force_refresh",
    )
    if doc_components:
        st.caption(f"Will tag ingested documents with: {', '.join(doc_components)}")

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
            elif doc_components and not doc_force_refresh and _all_components_cached(doc_components, "document"):
                cached = _cached_artifacts_for_components(doc_components, "document")
                st.info(
                    f"Cache hit — {len(cached)} document(s) already ingested for "
                    f"component(s) {', '.join(doc_components)}. Skipping "
                    f"re-processing and reading from the tracking database "
                    f"instead. Check \"Force refresh\" above to re-ingest anyway."
                )
                st.dataframe(cached[["display_name", "source_kind", "ingested_at"]], use_container_width=True)
            else:
                try:
                    with st.spinner("Extracting text..."):
                        artifact_ids = ingest_uploaded_files(uploaded)
                        if doc_components:
                            for aid in artifact_ids:
                                tag_components(aid, doc_components)
                    st.success(f"Registered {len(artifact_ids)} documents.")
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
            elif doc_components and not doc_force_refresh and _all_components_cached(doc_components, "document"):
                cached = _cached_artifacts_for_components(doc_components, "document")
                st.info(
                    f"Cache hit — {len(cached)} document(s) already ingested for "
                    f"component(s) {', '.join(doc_components)}. Skipping the "
                    f"fetch and reading from the tracking database instead. "
                    f"Check \"Force refresh\" above to re-fetch anyway."
                )
                st.dataframe(cached[["display_name", "source_kind", "ingested_at"]], use_container_width=True)
            else:
                try:
                    with st.spinner(f"Fetching {doc_url}..."):
                        artifact_ids = ingest_doc_from_url(doc_url)
                        if doc_components:
                            for aid in artifact_ids:
                                tag_components(aid, doc_components)
                    st.success("Document fetched, extracted, and registered.")
                except Exception as e:
                    st.error(str(e))

# ----------------------------------------------------------------------
# COMPONENTS  (the component -> code / document mapping lookup)
# ----------------------------------------------------------------------
with tab_components:
    st.subheader("Component map")
    st.caption(
        "Look up every code file and document tagged with a given component. "
        "This is the same mapping the cache-skip logic in the Source code and "
        "Documents tabs uses internally."
    )

    known = list_known_components()
    if not known:
        st.info(
            "No components tagged yet — enter a component name when ingesting "
            "source code or documents in the tabs above."
        )
    else:
        selected = st.selectbox("Component", known, key="component_lookup_select")
        if selected:
            code_df = get_artifacts_by_component(selected, "code")
            doc_df = get_artifacts_by_component(selected, "document")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Source code** ({len(code_df)})")
                if code_df.empty:
                    st.caption("None tagged with this component yet.")
                else:
                    st.dataframe(
                        code_df[["display_name", "source_kind", "ingested_at"]],
                        use_container_width=True,
                    )
            with col2:
                st.markdown(f"**Documents** ({len(doc_df)})")
                if doc_df.empty:
                    st.caption("None tagged with this component yet.")
                else:
                    st.dataframe(
                        doc_df[["display_name", "source_kind", "ingested_at"]],
                        use_container_width=True,
                    )



# ----------------------------------------------------------------------
# INVESTIGATE  (agent layer — designed, not yet built)
# ----------------------------------------------------------------------
with tab_investigate:
    st.subheader("Ask a question")
    st.caption(
        "This calls the real agent interface designed in the High-Level "
        "Design (Section 3.5) — it isn't wired up to working indexing and "
        "retrieval yet, so it will tell you that rather than return an "
        "answer. The shape below is what it will look like once built."
    )

    total_artifacts = sum(counts.values())
    if total_artifacts == 0:
        st.warning(
            "Nothing has been ingested yet — add source code, logs, or "
            "documents in the tabs above before running an investigation."
        )

    question = st.text_area(
        "Question",
        placeholder=(
            "Why does the XR400 reboot a few minutes after standby on "
            "firmware RDKV-4.2.118?"
        ),
        key="investigate_question",
    )

    if st.button("Run investigation", key="investigate_btn", type="primary"):
        if not question:
            st.warning("Enter a question first.")
        else:
            try:
                with st.spinner("Investigating..."):
                    result = investigate(question)
                # This branch is unreachable until agent.loop.investigate is
                # implemented, but is written now so wiring up real results
                # later is a matter of filling this in, not designing it.
                st.success("Proposed root cause")
                st.write(result.proposed_root_cause)
                st.caption(f"Cited artifacts: {result.cited_artifact_ids}")
            except NotImplementedError:
                st.info(
                    "The agent layer is designed but not yet built — see "
                    "`docs/design/Triage_MVP_High_Level_Design.docx`, "
                    "Section 3.5, and `agent/loop.py`. Once the indexing "
                    "and retrieval layers are implemented, this button "
                    "will run the full investigation loop below."
                )

    with st.expander("What this will do, once built"):
        st.markdown(
            "The agent runs a **reason → act → observe** loop against your "
            "question, calling these tools as needed and citing exactly "
            "what it used to reach its answer:"
        )
        for tool in TOOL_DEFINITIONS:
            st.markdown(f"- **{tool['name']}** — {tool['description']}")


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
