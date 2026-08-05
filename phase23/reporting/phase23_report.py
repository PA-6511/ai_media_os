from __future__ import annotations

import json
from pathlib import Path


def write_phase23_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "23",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "readiness_status": payload.get("readiness_status"),
        "can_execute": payload.get("can_execute", False),
        "next_step": payload.get("next_step"),
        "policy_result": payload.get("policy_result"),
        "execution_design": payload.get("execution_design"),
        "final_manual_gate": payload.get("final_manual_gate"),
        "stop_condition_verify": payload.get("stop_condition_verify"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
