from __future__ import annotations

import json
from pathlib import Path


def write_phase28_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "28",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "readiness_status": payload.get("readiness_status"),
        "can_execute": payload.get("can_execute", False),
        "next_step": payload.get("next_step"),
        "policy_result": payload.get("policy_result"),
        "manual_dry_run_gate": payload.get("manual_dry_run_gate"),
        "approval_input_schema": payload.get("approval_input_schema"),
        "evidence_storage_spec": payload.get("evidence_storage_spec"),
        "selected_decision": payload.get("selected_decision"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
