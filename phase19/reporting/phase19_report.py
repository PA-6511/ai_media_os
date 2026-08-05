from __future__ import annotations

import json
from pathlib import Path


def write_phase19_report(payload: dict, output_path: str) -> dict:
    report = {
        "phase": "19",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "promotion_status": payload.get("promotion_status"),
        "can_promote": payload.get("can_promote", False),
        "next_step": payload.get("next_step"),
        "quality_result": payload.get("quality_result"),
        "safety_result": payload.get("safety_result"),
        "rollback_result": payload.get("rollback_result"),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
