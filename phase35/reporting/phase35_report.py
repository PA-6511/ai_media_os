from __future__ import annotations

import json
from pathlib import Path


def write_phase35_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "35",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "readiness_status": payload.get("readiness_status"),
        "can_execute": payload.get("can_execute", False),
        "next_step": payload.get("next_step"),
        "policy_result": payload.get("policy_result"),
        "manual_dry_run_execution_readiness_package": payload.get(
            "manual_dry_run_execution_readiness_package"
        ),
        "readiness_controls": payload.get("readiness_controls"),
        "readiness_stop_conditions": payload.get("readiness_stop_conditions"),
        "readiness_evidence_requirements": payload.get("readiness_evidence_requirements"),
        "manual_gate_readiness": payload.get("manual_gate_readiness"),
        "selected_decision": payload.get("selected_decision"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
