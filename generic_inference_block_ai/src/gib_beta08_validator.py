from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta08_manual_approval_gate import load_and_run

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta08_contract() -> dict[str, Any]:
    config, beta07_report, gate = load_and_run()

    final_status = (
        "PASS_DRY_RUN_BETA08_MANUAL_APPROVAL_GATE_NO_REAL_CALL"
        if gate.config_valid
        and gate.denied_scenario.call_allowed is False
        and gate.approved_sim_scenario.call_allowed is False
        and gate.auto_connect_triggered is False
        and config["real_llm_call_allowed"] is False
        and config["execution_allowed"] is False
        and config["generate_call_allowed"] is False
        and config["chat_call_allowed"] is False
        else "FAIL_BETA08_MANUAL_APPROVAL_GATE"
    )

    return {
        "schema_version": "gib.beta08.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0.8",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "runtime_target": config["runtime_target"],
        "manual_approval_required": config["manual_approval_required"],
        "approval_granted": config["approval_granted"],
        "first_real_call_approval_text": config["first_real_call_approval_text"],
        "real_llm_call_allowed": config["real_llm_call_allowed"],
        "execution_allowed": config["execution_allowed"],
        "generate_call_allowed": config["generate_call_allowed"],
        "chat_call_allowed": config["chat_call_allowed"],
        "denied_scenario": {
            "scenario_name": gate.denied_scenario.scenario_name,
            "approval_granted": gate.denied_scenario.approval_granted,
            "ready_source": gate.denied_scenario.ready_source,
            "call_allowed": gate.denied_scenario.call_allowed,
            "blocked_reason": gate.denied_scenario.blocked_reason,
        },
        "approved_sim_scenario": {
            "scenario_name": gate.approved_sim_scenario.scenario_name,
            "approval_granted": gate.approved_sim_scenario.approval_granted,
            "ready_source": gate.approved_sim_scenario.ready_source,
            "call_allowed": gate.approved_sim_scenario.call_allowed,
            "blocked_reason": gate.approved_sim_scenario.blocked_reason,
        },
        "auto_connect_on_ready": config["auto_connect_on_ready"],
        "auto_connect_triggered": gate.auto_connect_triggered,
        "beta07_snapshot": {
            "final_status": beta07_report["final_status"],
            "simulated_ready_conditions_ok": beta07_report["simulated_ready_conditions_ok"],
            "auto_connect_triggered": beta07_report["auto_connect_triggered"],
            "production_status": beta07_report["production_status"],
        },
    }


def write_beta08_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta08_contract()
    output_path = REPORTS_DIR / "gib_beta08_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
