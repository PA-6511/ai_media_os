from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta099_final_gate import load_and_evaluate

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta099_contract() -> dict[str, Any]:
    config, beta095, result = load_and_evaluate()

    final_status = (
        "PASS_DRY_RUN_BETA099_FINAL_APPROVAL_GATE_NO_EXECUTION"
        if result.config_valid
        and result.beta095_prereq_ok
        and result.target_valid
        and result.switch_conditions_ok
        and result.denied_scenario.call_allowed is False
        and result.approved_sim_scenario.call_allowed is False
        and config["current_guardrails"]["real_llm_call_allowed"] is False
        and config["current_guardrails"]["execution_allowed"] is False
        and config["current_guardrails"]["generate_call_allowed"] is False
        and config["current_guardrails"]["chat_call_allowed"] is False
        else "FAIL_BETA099_FINAL_APPROVAL_GATE"
    )

    return {
        "schema_version": "gib.beta099.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0.99",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "handoff_ready": config["handoff_ready"],
        "final_approval_required": config["final_approval_required"],
        "final_approval_granted": config["final_approval_granted"],
        "final_approval_statement": config["final_approval_statement"],
        "target_runtime": config["first_call_target"]["runtime"],
        "target_host": config["first_call_target"]["host"],
        "target_port": config["first_call_target"]["port"],
        "target_model": config["first_call_target"]["model"],
        "target_valid": result.target_valid,
        "target_issues": result.target_issues,
        "switch_conditions_ok": result.switch_conditions_ok,
        "switch_condition_issues": result.switch_condition_issues,
        "real_llm_call_switch_conditions_documented": config["real_llm_call_switch_conditions_documented"],
        "denied_scenario": {
            "scenario_name": result.denied_scenario.scenario_name,
            "approval_granted": result.denied_scenario.approval_granted,
            "call_allowed": result.denied_scenario.call_allowed,
            "blocked_reason": result.denied_scenario.blocked_reason,
        },
        "approved_sim_scenario": {
            "scenario_name": result.approved_sim_scenario.scenario_name,
            "approval_granted": result.approved_sim_scenario.approval_granted,
            "call_allowed": result.approved_sim_scenario.call_allowed,
            "blocked_reason": result.approved_sim_scenario.blocked_reason,
        },
        "current_guardrails": config["current_guardrails"],
        "beta095_snapshot": {
            "final_status": beta095["final_status"],
            "token_format_valid": beta095["token_format_valid"],
            "change_id_format_valid": beta095["change_id_format_valid"],
            "production_status": beta095["production_status"],
            "real_llm_call_allowed": beta095["real_llm_call_allowed"],
            "execution_allowed": beta095["execution_allowed"],
        },
        "can_execute_now": False,
    }


def write_beta099_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta099_contract()
    output_path = REPORTS_DIR / "gib_beta099_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
