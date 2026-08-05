from __future__ import annotations
import json
from pathlib import Path


def write_phase58_report(payload: dict, output_path: str) -> dict:
    required_keys = [
        "readiness_status",
        "can_execute",
        "next_step",
        "policy_result",
        "execution_plan_package",
        "execution_plan_controls",
        "execution_plan_stop_conditions",
        "execution_plan_evidence_requirements",
        "manual_gate_execution_plan",
        "selected_decision",
    ]
    missing = [k for k in required_keys if k not in payload]
    if missing:
        return {"status": "FAIL", "reason": f"missing keys: {missing}"}

    report = {
        "phase": "58",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        **payload,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
