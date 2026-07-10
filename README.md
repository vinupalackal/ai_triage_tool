# Triage MVP — Data Ingestion, Correlation & AI Root-Cause Assistant

A Streamlit-based tool for triaging bugs in embedded video and broadband
devices (set-top boxes, gateways, cable modems, ONTs), and correlating
source code, logs, and documents so an AI agent can propose a root cause
with citations.

The system implements the **Generic Issue Triage Skill** (see [docs/guides/Generic_Issue_Triage_Skill.md](docs/guides/Generic_Issue_Triage_Skill.md))
— a systematic 7-step framework for investigating any behavioral anomaly by correlating
evidence, classifying the issue, and navigating to root cause. Each system layer supports
one or more skill steps, as shown in the Status table below.

This repository is the MVP implementation described in the design documents
under [`docs/`](docs/). Start there for the *why*; this README covers the
*how to run it*.

## Status and Skill Alignment

| Layer | Status | Where | Supports Skill Steps |
|---|---|---|---|
| Ingestion (code, logs, docs — local and remote sources) | **Implemented** | [`ingestion/`](ingestion/) | **Step 1** — Orient to artifacts (collect logs, code, docs) |
| Tracking (shared artifact schema over DuckDB) | **Implemented** | [`utils/storage.py`](utils/storage.py) | **Step 1** — Build unified artifact index |
| Component tagging + component → code/document map + ingestion cache | **Implemented** | [`utils/storage.py`](utils/storage.py), "Components" tab | **Step 1** — Organize artifacts by component |
| Indexing (log templating, code chunking, doc embedding) | Designed, not yet built | [`indexing/`](indexing/) — stubs raise `NotImplementedError` | **Steps 2–3** — Extract patterns; enable window/anomaly classification |
| Retrieval (hybrid vector + keyword + graph search) | Designed, not yet built | [`retrieval/`](retrieval/) — stubs raise `NotImplementedError` | **Step 4** — Correlate logs, code, docs; traverse relationships |
| Agent (Claude tool-calling investigation loop) | Designed, not yet built | [`agent/`](agent/) — stubs raise `NotImplementedError` | **Steps 5–7** — Navigate code, characterize cause, validate against design |

The "Investigate" tab in the running app calls the real `agent.loop.investigate()`
interface today — it currently surfaces a clear "not yet built" message
instead of an answer, plus the six tools the agent will use once it's wired
up, so the app's visible shape already matches its full intended scope.

### Component tagging and the ingestion cache

When ingesting source code or documents, you can tag what you're ingesting
with one or more component names (comma-separated, e.g. `Tuner, Wi-Fi` for
shared code). This does two things:

1. **It's the component → document/code map.** The "Components" tab lets
   you pick a component and see every code file and document tagged with
   it, in one place.
2. **It backs a real ingestion cache.** If every component you enter already
   has data of that type tracked (e.g. you already ingested code tagged
   `Tuner`), a second ingestion attempt for `Tuner` skips the actual git
   clone / folder scan / document fetch entirely and reads the existing
   rows straight from the tracking database instead — visible in the UI as
   a "Cache hit" message. Check "Force refresh" to bypass the cache and
   re-ingest anyway (e.g. after the underlying repo has new commits).

This is optional — leaving the component field blank ingests and tags
nothing, exactly as before this feature was added.

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
| [Generic Issue Triage Skill](docs/guides/Generic_Issue_Triage_Skill.md) | Systematic 7-step framework for investigating **any** behavioral anomaly (hangs, crashes, resource spikes, race conditions, etc.) |
| [AI Triage: A Beginner's Guide](docs/guides/AI_Triage_Beginners_Guide.pdf) | A plain-English, illustrated walkthrough of the whole approach, for anyone new to the project |

Read them in that order if you're new here: requirements → architecture →
design → code.

## Repository layout

```
app.py                  Streamlit entry point — tabs: Investigate, Source code, Logs, Documents, Components, Ingested artifacts
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

### Grounded response checklist (avoid over-claiming)

Before describing system capabilities in docs, PRs, or AI responses:

1. Classify each claim as **Implemented now**, **Designed/planned**, or **Deferred/post-MVP**.
2. Treat runnable code as source of truth over aspirational architecture text.
3. Do not describe `NotImplementedError` paths as operational.
4. If answering "does it do X?", lead with a direct yes/no status and classification.
5. For AI responses, follow the repo rules in `.github/copilot-instructions.md`.

Grounding reference: `docs/guides/Agent_Grounded_Context.md`.

## License

Add your organization's license here.
