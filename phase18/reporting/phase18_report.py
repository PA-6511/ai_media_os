from __future__ import annotations

import json
from pathlib import Path


def write_phase18_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "18",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "apply_scope": "sandbox_only",
        "approval_decision": payload.get("approval_decision"),
        "execution_status": payload.get("execution_status"),
        "verify_status": payload.get("verify_status"),
        "can_promote_to_next": payload.get("can_promote_to_next", False),
        "details": payload,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"status": "PASS", "output_path": str(path)}
