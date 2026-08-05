from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta09_handoff import load_and_evaluate

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta09_contract() -> dict[str, Any]:
    config, beta08, result = load_and_evaluate()

    final_status = (
        "PASS_DRY_RUN_BETA09_FIRST_CALL_HANDOFF_NO_EXECUTION"
        if result.config_valid
        and result.beta08_prereq_ok
        and result.target_valid
        and result.promotion_conditions_documented
        and result.can_execute_now is False
        else "FAIL_BETA09_FIRST_CALL_HANDOFF"
    )

    return {
        "schema_version": "gib.beta09.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0.9",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "handoff_ready": config["handoff_ready"],
        "manual_approval_required": config["manual_approval"]["required"],
        "manual_approval_granted": config["manual_approval"]["granted"],
        "approval_statement": config["manual_approval"]["approval_statement"],
        "target_runtime": config["first_call_target"]["runtime"],
        "target_host": config["first_call_target"]["host"],
        "target_port": config["first_call_target"]["port"],
        "target_model": config["first_call_target"]["model"],
        "target_valid": result.target_valid,
        "target_issues": result.target_issues,
        "promotion_conditions_documented": result.promotion_conditions_documented,
        "promotion_issues": result.promotion_issues,
        "can_execute_now": result.can_execute_now,
        "blocked_reasons": result.blocked_reasons,
        "current_guardrails": config["current_guardrails"],
        "beta08_snapshot": {
            "final_status": beta08["final_status"],
            "manual_approval_required": beta08["manual_approval_required"],
            "approval_granted": beta08["approval_granted"],
            "auto_connect_triggered": beta08["auto_connect_triggered"],
            "real_llm_call_allowed": beta08["real_llm_call_allowed"],
        },
    }


def write_beta09_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta09_contract()
    output_path = REPORTS_DIR / "gib_beta09_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
