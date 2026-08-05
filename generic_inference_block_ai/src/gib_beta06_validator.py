from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta05_validator import validate_beta05_contract
from generic_inference_block_ai.src.gib_beta06_readiness_gate import load_and_evaluate

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta06_contract() -> dict[str, Any]:
    beta05_report = validate_beta05_contract()
    config, gate = load_and_evaluate(beta05_report)

    final_status = (
        "PASS_DRY_RUN_BETA06_ENV_PREP_CHECK_NO_GENERATE"
        if gate.config_valid and gate.guardrails_ok and (len(gate.violated_false_conditions) == 0)
        else "FAIL_BETA06_ENV_PREP_GATE"
    )

    return {
        "schema_version": "gib.beta06.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0.6",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "runtime_target": config["runtime_target"],
        "guardrails_ok": gate.guardrails_ok,
        "guardrail_issues": gate.guardrail_issues,
        "ready_conditions_ok": gate.ready_conditions_ok,
        "missing_true_conditions": gate.missing_true_conditions,
        "violated_false_conditions": gate.violated_false_conditions,
        "ready_for_connecting_stage": gate.ready_for_connecting_stage,
        "no_generate_call_required": config["no_generate_call_required"],
        "localhost_only_required": config["localhost_only_required"],
        "allowlist_enforced": config["allowlist_enforced"],
        "beta05_snapshot": {
            "final_status": beta05_report["final_status"],
            "ollama_binary_found": beta05_report["ollama_binary_found"],
            "all_endpoints_valid": beta05_report["all_endpoints_valid"],
            "model_allowed": beta05_report["model_allowed"],
            "forbidden_host_rejected": beta05_report["forbidden_host_rejected"],
            "generate_api_called": beta05_report["generate_api_called"],
            "chat_api_called": beta05_report["chat_api_called"],
            "real_llm_call_allowed": beta05_report["real_llm_call_allowed"],
            "execution_allowed": beta05_report["execution_allowed"],
            "production_status": beta05_report["production_status"],
        },
    }


def write_beta06_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta06_contract()
    output_path = REPORTS_DIR / "gib_beta06_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
