from __future__ import annotations
import json
from pathlib import Path


def write_phase44_report(payload: dict, output_path: str) -> dict:
    required_keys = [
        "readiness_status",
        "can_execute",
        "next_step",
        "policy_result",
        "closure_package",
        "closure_controls",
        "closure_stop_conditions",
        "closure_evidence_requirements",
        "manual_gate_closure",
        "selected_decision",
    ]
    missing = [k for k in required_keys if k not in payload]
    if missing:
        return {"status": "FAIL", "reason": f"missing keys: {missing}"}

    report = {
        "phase": "44",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        **payload,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
