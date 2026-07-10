"""
agent/loop.py  —  MVP scope, not yet implemented

Design reference: High-Level Design, Section 3.5, 5.3, and 7.
Requirement references: AI-FR-060, AI-FR-062, AI-FR-063, AI-FR-065.

Implements the reason -> act -> observe investigation loop: calls the
Claude API with the tools from agent/tools.py registered, dispatches each
requested tool call, appends the result to the conversation, and repeats
until the model returns a final answer or a bounded step limit is reached
(HLD Section 7 — proposed default of 15 steps, not yet validated against a
real investigation; see HLD Section 10, Open Design Questions).

Every call and result should be appended to the trace this function
returns, which the caller persists to the agent_investigations table
(HLD Section 4.2) — this is what makes citations machine-checkable
(AI-FR-063) rather than free text, and what the confirmed/rejected
feedback (AI-FR-065) attaches to.

This loop implements the Generic Issue Triage Skill (docs/guides/Generic_Issue_Triage_Skill.md)
Steps 3–7 via the reason → act → observe pattern:
  - Step 3 (Classify Anomaly): Agent reasoning over log/code/doc patterns
  - Step 4 (Correlate): Tool calls to search_logs, search_docs, graph_query
  - Step 5 (Navigate to Code): Tool calls to search_code, blame_history, symbolicate_crash
  - Step 6 (Characterize): Agent synthesis of evidence into root-cause hypothesis
  - Step 7 (Validate): Agent cross-checks against design docs via search_docs
"""

from dataclasses import dataclass, field

MAX_TOOL_CALLS = 15  # see HLD Section 10 — not yet validated


@dataclass
class Investigation:
    """The full result of one agent investigation (HLD Section 4.2)."""
    investigation_id: str
    question_text: str
    tool_call_log: list[dict] = field(default_factory=list)
    proposed_root_cause: str | None = None
    cited_artifact_ids: list[str] = field(default_factory=list)
    feedback: str | None = None  # "confirmed" | "rejected" | "corrected" | None


def investigate(question: str, initial_context: dict | None = None) -> Investigation:
    """
    Run the full reason -> act -> observe loop against `question`, using the
    six tools in agent.tools.TOOL_DEFINITIONS, and return the resulting
    Investigation record (not yet persisted — the caller is responsible for
    writing it to agent_investigations via utils.storage, once that table
    exists per HLD Section 4.2).

    Args:
        question: the engineer's natural-language question.
        initial_context: optional pre-known facts (e.g. a crash address and
            firmware_build_id already extracted from an attached crash dump),
            to save the agent's first tool call.

    Raises:
        RuntimeError: if MAX_TOOL_CALLS is reached without a final answer —
            per HLD Section 7, this should return the best partial evidence
            labeled inconclusive rather than raise, once implemented; raising
            here is a placeholder for the stub.
    """
    raise NotImplementedError(
        "agent.loop.investigate is designed (HLD 3.5 / 5.3 / 7) but not yet "
        "implemented. Depends on agent/tools.py and the full retrieval and "
        "indexing layers being implemented first — this is the last piece "
        "of the MVP to build, since it composes everything else."
    )
