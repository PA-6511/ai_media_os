from __future__ import annotations

import json
from pathlib import Path


REQUIRED_KEYS = [
    "review_status",
    "go_no_go",
    "can_execute",
    "execute_allowed",
    "next_step",
    "reasons",
    "selected_decision",
]


def write_phase66_go_no_go_report(payload: dict, output_path: str) -> dict:
    missing = [k for k in REQUIRED_KEYS if k not in payload]
    if missing:
        return {"status": "FAIL", "reason": f"missing keys: {missing}"}

    if payload.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "can_execute must be False"}
    if payload.get("execute_allowed") is not False:
        return {"status": "FAIL", "reason": "execute_allowed must be False"}

    report = {
        "phase": "66",
        "review_type": "go_no_go_for_limited_dry_run_preparation_only",
        "human_approval_required": True,
        **payload,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
