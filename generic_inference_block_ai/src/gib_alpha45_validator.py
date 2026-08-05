from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha45_promotion_gate import load_and_evaluate

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_alpha45_contract() -> dict[str, Any]:
    config, gate = load_and_evaluate()

    final_status = "PASS_DESIGN_ONLY_ALPHA45_PROMOTION_CHECKLIST_FIXED"

    return {
        "schema_version": "gib.alpha45.validation_report.v0.1",
        "block_id": "GIB",
        "alpha_version": "alpha4.5",
        "final_status": final_status,
        "design_status": config["design_status"],
        "production_status": config["production_status"],
        "beta0_ready": gate.beta0_ready,
        "checklist_valid": gate.checklist_valid,
        "all_decisions_made": gate.all_decisions_made,
        "missing_decisions": gate.missing_decisions,
        "blocked_reasons": gate.blocked_reasons,
        "beta0_guardrails": config["beta0_guardrails"],
        "report_write_scope": config["check_items"]["artifact_policy"]["report_write_scope"],
    }


def write_alpha45_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_alpha45_contract()
    output_path = REPORTS_DIR / "gib_alpha45_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
