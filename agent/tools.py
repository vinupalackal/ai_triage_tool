"""
agent/tools.py  —  MVP scope, not yet implemented

Design reference: High-Level Design, Section 3.5 and 6.2.
Requirement reference: AI-FR-061.

Defines the six tools the agent loop (agent/loop.py) registers with the
Claude API, and dispatches a tool-call request to the right underlying
module. This tool set is deliberately identical to AI-FR-061 in the
Requirements Specification — see the HLD's note in Section 3.5 on why this
is a direct implementation of that contract, not a simplified variant.

These tools implement the Generic Issue Triage Skill (docs/guides/Generic_Issue_Triage_Skill.md)
Steps 4–5 (Correlate and Navigate to Code):
  - search_logs    → Skill Step 4: Correlate logs with anomaly window
  - search_code    → Skill Step 5: Navigate to potentially responsible code
  - search_docs    → Skill Step 4: Correlate with design specs and past incidents
  - graph_query    → Skill Step 4: Trace artifact relationships and dependencies
  - blame_history  → Skill Step 5: Find commits touching affected code
  - symbolicate_crash → Skill Step 5: Resolve crash to precise function/line
"""

# Tool definitions in Claude API tool-use schema shape. Each "input_schema"
# is intentionally minimal here — fill in full JSON Schema detail (types,
# required fields, descriptions) when implementing loop.investigate.
TOOL_DEFINITIONS = [
    {
        "name": "search_logs",
        "description": "Query log signatures by frequency, device, or firmware build. [Skill Step 4: Correlate] Identify patterns in logs within the anomaly window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "device_model": {"type": "string"},
                "firmware_build_id": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "symbolicate_crash",
        "description": "Resolve a crash address to function/file/line for an exact firmware build. [Skill Step 5: Navigate] Pinpoint the exact location of a crash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "crash_address": {"type": "string"},
                "firmware_build_id": {"type": "string"},
            },
            "required": ["crash_address", "firmware_build_id"],
        },
    },
    {
        "name": "search_code",
        "description": "Hybrid search over code symbols by meaning or exact symbol name. [Skill Step 5: Navigate] Find potentially responsible functions and their context.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "graph_query",
        "description": "Traverse the knowledge graph using one of the supported query shapes. [Skill Step 4: Correlate] Follow relationships: commit→file→component→log signature→document.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_shape": {"type": "string"},
                "args": {"type": "object"},
            },
            "required": ["query_shape"],
        },
    },
    {
        "name": "search_docs",
        "description": "Hybrid search over document chunks (specs, past incidents). [Skill Step 4: Correlate] Find design intent, past similar issues, and documented anomalies.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "blame_history",
        "description": "Return commit history for a file or function. [Skill Step 5: Navigate] Trace recent changes to identify potential root-cause commit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "function_name": {"type": "string"},
            },
            "required": ["file_path"],
        },
    },
]


def dispatch(tool_name: str, tool_args: dict) -> dict:
    """
    Route a tool-call request from the agent loop to the underlying
    retrieval/indexing module, and return a plain-dict result suitable for
    passing back to the model as the next turn's context.

    Raises:
        ValueError: if tool_name is not one of TOOL_DEFINITIONS.
    """
    known = {t["name"] for t in TOOL_DEFINITIONS}
    if tool_name not in known:
        raise ValueError(f"Unknown tool '{tool_name}'. Known tools: {sorted(known)}")

    raise NotImplementedError(
        f"agent.tools.dispatch('{tool_name}', ...) is designed (HLD 3.5 / "
        "6.2) but not yet implemented. Depends on the retrieval layer "
        "(retrieval/) being implemented first."
    )
