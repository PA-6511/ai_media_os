from __future__ import annotations

import json
from pathlib import Path


def write_phase30_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "30",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "readiness_status": payload.get("readiness_status"),
        "can_execute": payload.get("can_execute", False),
        "next_step": payload.get("next_step"),
        "policy_result": payload.get("policy_result"),
        "limited_dry_run_design": payload.get("limited_dry_run_design"),
        "sandbox_execution_constraints": payload.get("sandbox_execution_constraints"),
        "manual_approval_gate": payload.get("manual_approval_gate"),
        "selected_decision": payload.get("selected_decision"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
