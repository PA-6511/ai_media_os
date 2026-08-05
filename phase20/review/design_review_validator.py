from __future__ import annotations

_REQUIRED_KEYS = [
    "phase",
    "mode",
    "human_approval_required",
    "source_phase19_result",
    "review_checklist",
    "risk_summary",
    "status",
]


def validate_design_review_package(package: dict) -> dict:
    missing_keys = [key for key in _REQUIRED_KEYS if key not in package]
    if missing_keys:
        return {"status": "FAIL", "missing_keys": missing_keys}
    return {"status": "PASS", "missing_keys": []}
