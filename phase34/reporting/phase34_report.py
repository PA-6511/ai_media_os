from __future__ import annotations

import json
from pathlib import Path


def write_phase34_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "34",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "readiness_status": payload.get("readiness_status"),
        "can_execute": payload.get("can_execute", False),
        "next_step": payload.get("next_step"),
        "policy_result": payload.get("policy_result"),
        "manual_dry_run_execution_final_pre_execution_review": payload.get(
            "manual_dry_run_execution_final_pre_execution_review"
        ),
        "final_review_controls": payload.get("final_review_controls"),
        "final_review_stop_conditions": payload.get("final_review_stop_conditions"),
        "final_review_evidence_requirements": payload.get(
            "final_review_evidence_requirements"
        ),
        "manual_gate_final_pre_execution_review": payload.get(
            "manual_gate_final_pre_execution_review"
        ),
        "selected_decision": payload.get("selected_decision"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
