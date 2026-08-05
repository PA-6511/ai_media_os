from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta1_prep_b import load_and_evaluate

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta1_prep_b_contract() -> dict[str, Any]:
    config, prep, prep_a, result = load_and_evaluate()

    final_status = (
        "PASS_REPORTS_ONLY_BETA1_PREP_B_APPROVAL_PROTOCOL_FIXED"
        if result.config_valid
        and result.prerequisites_ok
        and result.protocol_ok
        and result.non_execution_ok
        and result.can_execute_now is False
        and config["real_llm_call_allowed"] is False
        and config["execution_allowed"] is False
        and config["generate_call_allowed"] is False
        and config["chat_call_allowed"] is False
        else "FAIL_BETA1_PREP_B_APPROVAL_PROTOCOL"
    )

    return {
        "schema_version": "gib.beta1.prep_b.validation_report.v0.1",
        "block_id": "GIB",
        "phase": "beta1_prep_b",
        "report_type": "BETA1_PREP_B_APPROVAL_PROTOCOL_REPORTS_ONLY",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "output_scope": config["output_scope"],
        "real_llm_call_allowed": config["real_llm_call_allowed"],
        "execution_allowed": config["execution_allowed"],
        "generate_call_allowed": config["generate_call_allowed"],
        "chat_call_allowed": config["chat_call_allowed"],
        "can_execute_now": result.can_execute_now,
        "prerequisites_ok": result.prerequisites_ok,
        "prerequisite_issues": result.prerequisite_issues,
        "protocol_ok": result.protocol_ok,
        "protocol_issues": result.protocol_issues,
        "non_execution_ok": result.non_execution_ok,
        "non_execution_issues": result.non_execution_issues,
        "approval_protocol": {
            "required_identifiers": config["approval_protocol"]["required_identifiers"],
            "identifier_reference_rules": config["approval_protocol"]["identifier_reference_rules"],
            "manual_only": config["approval_protocol"]["manual_only"],
            "auto_execute_after_approval": config["approval_protocol"]["auto_execute_after_approval"],
        },
        "pre_beta1_references": {
            "beta1_prep_final_status": prep["final_status"],
            "beta1_prep_a_final_status": prep_a["final_status"],
        },
    }


def write_beta1_prep_b_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = validate_beta1_prep_b_contract()
    output_path = REPORTS_DIR / "gib_beta1_prep_b_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
