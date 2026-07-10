"""
indexing/log_templating.py  —  MVP scope, not yet implemented

Design reference: High-Level Design, Section 3.3.1.
Requirement references: AI-FR-001, AI-FR-002, AI-FR-005.

Turns raw log lines into a compact set of structured templates (a Drain-
family streaming parser, e.g. the `drain3` package, is the intended
implementation basis) and writes them to the `log_signatures` table via
`utils.storage`.

This module intentionally has no implementation yet — the function
signatures below are the interface contract other modules (retrieval,
agent) are designed against, per the HLD. Implementing this module is
the next milestone toward completing the MVP.

Supports Generic Issue Triage Skill Steps 2–3 (Define Anomaly Window & Classify Anomaly):
Extracts log patterns so anomaly windows can be identified by searching for
template frequency spikes and correlating with anomalies observed in other logs.
"""

from .models import LogTemplate


def template_log_file(artifact_id: str) -> list[LogTemplate]:
    """
    Read the log file for the given artifact_id (via utils.storage), run it
    through a Drain-family templating parser, and return the resulting
    templates. Implementations should also persist results to the
    log_signatures table and call utils.storage.mark_indexed(artifact_id,
    "log_signatures", signature_id) for each one, per HLD Section 3.2.

    Raises:
        ValueError: if artifact_id does not correspond to a known log artifact.
    """
    raise NotImplementedError(
        "log_templating.template_log_file is designed (HLD 3.3.1) but not "
        "yet implemented. See AI-FR-001/AI-FR-002 in the Requirements "
        "Specification for the target behavior."
    )


def get_signature_frequency(signature_id: str, group_by: list[str] | None = None):
    """
    Return occurrence counts for a given log signature over time, optionally
    grouped by fields such as device_model or firmware_build_id (AI-FR-005).

    Returns:
        A pandas DataFrame of counts — shape depends on `group_by`.
    """
    raise NotImplementedError(
        "log_templating.get_signature_frequency is designed (HLD 3.3.1) but "
        "not yet implemented."
    )
