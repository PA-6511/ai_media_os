from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta095_evidence_gate import load_and_evaluate

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta095_contract() -> dict[str, Any]:
    config, beta09, result = load_and_evaluate()

    final_status = (
        "PASS_DRY_RUN_BETA095_APPROVAL_EVIDENCE_FORMAT_ONLY"
        if result.config_valid
        and result.beta09_prereq_ok
        and result.token_format_valid
        and result.change_id_format_valid
        and result.secret_handling_allowed is False
        and config["real_llm_call_allowed"] is False
        and config["execution_allowed"] is False
        and config["generate_call_allowed"] is False
        and config["chat_call_allowed"] is False
        else "FAIL_BETA095_APPROVAL_EVIDENCE_FORMAT"
    )

    return {
        "schema_version": "gib.beta095.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0.95",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "manual_approval_required": config["manual_approval_required"],
        "real_llm_call_allowed": config["real_llm_call_allowed"],
        "execution_allowed": config["execution_allowed"],
        "generate_call_allowed": config["generate_call_allowed"],
        "chat_call_allowed": config["chat_call_allowed"],
        "token_format_valid": result.token_format_valid,
        "change_id_format_valid": result.change_id_format_valid,
        "secret_value_handling_allowed": result.secret_handling_allowed,
        "beta09_prereq_ok": result.beta09_prereq_ok,
        "beta09_prereq_issues": result.beta09_prereq_issues,
        "beta09_snapshot": {
            "final_status": beta09["final_status"],
            "production_status": beta09["production_status"],
            "can_execute_now": beta09["can_execute_now"],
            "target_runtime": beta09["target_runtime"],
            "target_model": beta09["target_model"],
        },
    }


def write_beta095_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta095_contract()
    output_path = REPORTS_DIR / "gib_beta095_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
