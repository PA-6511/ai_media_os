from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

_ALLOWED_DECISIONS = {"APPROVE", "REJECT", "NEEDS_REVISION"}


def read_approval_file(path: str) -> dict:
    approval_path = Path(path)
    if not approval_path.exists():
        return {
            "status": "WARN",
            "decision": "PENDING",
            "next_step": "wait_for_human_review",
        }

    try:
        data = json.loads(approval_path.read_text(encoding="utf-8"))
    except (OSError, JSONDecodeError):
        return {
            "status": "FAIL",
            "decision": "INVALID",
            "next_step": "fix_approval_file",
        }

    decision = str(data.get("decision", "")).strip().upper()
    if decision in _ALLOWED_DECISIONS:
        return {
            "status": "PASS",
            "decision": decision,
            "next_step": "evaluate_approval_gate",
        }

    return {
        "status": "FAIL",
        "decision": "INVALID",
        "next_step": "fix_approval_decision",
    }
