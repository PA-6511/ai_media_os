from __future__ import annotations

import json
from pathlib import Path


def write_phase25_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "25",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "readiness_status": payload.get("readiness_status"),
        "can_execute": payload.get("can_execute", False),
        "next_step": payload.get("next_step"),
        "policy_result": payload.get("policy_result"),
        "execution_plan": payload.get("execution_plan"),
        "evidence_format": payload.get("evidence_format"),
        "execution_checklist": payload.get("execution_checklist"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
