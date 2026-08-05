from __future__ import annotations

import json
from pathlib import Path


def write_phase22_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "22",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "readiness_status": payload.get("readiness_status"),
        "can_apply": payload.get("can_apply", False),
        "next_step": payload.get("next_step"),
        "policy_result": payload.get("policy_result"),
        "approval_format": payload.get("approval_format"),
        "checklist": payload.get("checklist"),
        "stop_conditions": payload.get("stop_conditions"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
