from __future__ import annotations

REQUIRED_PACKAGE_KEYS = [
    "phase",
    "mode",
    "human_approval_required",
    "selected_candidate_id",
    "risks",
    "reject_reasons",
    "approve_instructions",
    "comparison_result",
]


def validate_decision_package(package: dict) -> dict:
    missing_keys = [key for key in REQUIRED_PACKAGE_KEYS if key not in package]
    if missing_keys:
        return {"status": "FAIL", "missing_keys": missing_keys}
    return {"status": "PASS", "missing_keys": []}
