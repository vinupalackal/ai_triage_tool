# Triage MVP — Data Ingestion, Correlation & AI Root-Cause Assistant

A Streamlit-based tool for triaging bugs in embedded video and broadband
devices (set-top boxes, gateways, cable modems, ONTs), and correlating
source code, logs, and documents so an AI agent can propose a root cause
with citations.

This repository is the MVP implementation described in the design documents
under [`docs/`](docs/). Start there for the *why*; this README covers the
*how to run it*.

## Status

| Layer | Status | Where |
|---|---|---|
| Ingestion (code, logs, docs — local and remote sources) | **Implemented** | [`ingestion/`](ingestion/) |
| Tracking (shared artifact schema over DuckDB) | **Implemented** | [`utils/storage.py`](utils/storage.py) |
| Investigate UI (question box, wired to the real agent interface) | **Implemented — UI only** | [`app.py`](app.py), "Investigate" tab |
| Indexing (log templating, code chunking, doc embedding) | Designed, not yet built | [`indexing/`](indexing/) — stubs raise `NotImplementedError` |
| Retrieval (hybrid vector + keyword + graph search) | Designed, not yet built | [`retrieval/`](retrieval/) — stubs raise `NotImplementedError` |
| Agent (Claude tool-calling investigation loop) | Designed, not yet built | [`agent/`](agent/) — stubs raise `NotImplementedError` |

The "Investigate" tab in the running app calls the real `agent.loop.investigate()`
interface today — it currently surfaces a clear "not yet built" message
instead of an answer, plus the six tools the agent will use once it's wired
up, so the app's visible shape already matches its full intended scope.

The stub modules aren't placeholders in the "TODO" sense — their function
signatures, inputs, and outputs are the actual interface contract defined in
the [High-Level Design](docs/design/Triage_MVP_High_Level_Design.docx).
Implementing one means filling in a function body against a spec that's
already been thought through, not inventing the interface from scratch.

## Quick start

```bash
git clone <this-repo-url>
cd triage-mvp
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints, and use the three tabs to ingest source
code, logs, and documents from either a local path or a remote source (git
URL, Jira issue, document URL). See [`ingestion/`](#repository-layout) below
for what each path supports.

### Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/                # fast tests only (default)
pytest tests/ -m network      # include the one test that needs internet (git clone)
```

CI (`.github/workflows/ci.yml`) runs the fast suite on every push and PR.

## Documentation

| Document | Covers |
|---|---|
| [Consolidated Requirements Specification](docs/requirements/Consolidated_Requirements_Specification.docx) | What the system must do — functional and non-functional requirements (`FR-xxx`, `AI-FR-xxx`, `NFR-xx`) |
| [Requirements Detail & Rationale](docs/requirements/Requirements_Detail_and_Rationale.docx) | Plain-language explanation and a worked example for every requirement |
| [Architecture Document](docs/architecture/Triage_MVP_Architecture_Document.docx) | System shape — technology choices per layer, deployment model, MVP vs. post-MVP boundary |
| [High-Level Design](docs/design/Triage_MVP_High_Level_Design.docx) | Module interfaces, data schemas, key workflows — the design this code implements |
| [AI Triage: A Beginner's Guide](docs/guides/AI_Triage_Beginners_Guide.pdf) | A plain-English, illustrated walkthrough of the whole approach, for anyone new to the project |

Read them in that order if you're new here: requirements → architecture →
design → code.

## Repository layout

```
app.py                  Streamlit entry point (3 ingestion tabs, Investigate tab, artifact browser)
ingestion/               Implemented — provisions code, logs, and docs
  code_ingest.py           local folder OR git URL (clones)
  log_ingest.py            local folder OR Jira issue URL (downloads attachments)
  doc_ingest.py            uploaded PDF/MD files OR a URL (PDF/MD/HTML)
utils/
  storage.py              DuckDB tracking layer — the shared schema every artifact goes through
indexing/                Designed, not yet built — see docs/design, Section 3.3
  models.py                shared dataclasses (LogTemplate, CodeChunk, DocChunk)
  log_templating.py        Drain3-based log templating (AI-FR-001/002)
  code_chunking.py         tree-sitter chunking + git blame (AI-FR-012/016)
  doc_embedding.py         sentence-transformers embedding (AI-FR-020)
retrieval/                Designed, not yet built — see docs/design, Section 3.4
  models.py                shared dataclasses (SearchResult, GraphPath)
  hybrid_search.py         vector + keyword + graph fusion (AI-FR-050/051)
  graph_query.py           fixed-shape graph traversal (AI-FR-030/031)
agent/                    Designed, not yet built — see docs/design, Section 3.5
  tools.py                 the 6-tool contract matching AI-FR-061 exactly
  loop.py                  the reason -> act -> observe investigation loop
tests/                   pytest suite for everything currently implemented
  test_app.py               AppTest-based smoke tests for the Streamlit UI itself
docs/                    the five documents listed above
.github/workflows/ci.yml  compile-check + test on every push/PR
```

## Contributing / picking up the next piece

The next implementation milestone is the **indexing layer** — nothing in
`retrieval/` or `agent/` can do real work until `indexing/` produces the
`log_signatures`, `code_symbols`, and `doc_chunks` tables they read from.
Each stub module's docstring points at the exact HLD section and requirement
IDs it implements; start there rather than re-deriving the design.

## License

Add your organization's license here.
