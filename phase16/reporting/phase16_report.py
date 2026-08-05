from __future__ import annotations

import json
from pathlib import Path


def write_phase16_report(comparison_result: dict, output_path: str) -> dict:
    payload = {
        "phase": "16",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "selected_candidate_id": comparison_result.get("selected_candidate_id"),
        "pipeline_status": comparison_result.get("pipeline_status"),
        "comparison_result": comparison_result,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"status": "OK", "output_path": str(path)}
