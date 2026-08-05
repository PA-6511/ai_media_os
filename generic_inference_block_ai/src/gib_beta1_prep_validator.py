from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta1_prep import load_and_evaluate

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta1_prep_contract() -> dict[str, Any]:
    config, beta099, result = load_and_evaluate()

    final_status = (
        "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED"
        if result.config_valid
        and result.beta099_prereq_ok
        and result.constraints_ok
        and result.can_execute_now is False
        and config["real_llm_call_allowed"] is False
        and config["execution_allowed"] is False
        else "FAIL_BETA1_PREP_RUNBOOK"
    )

    return {
        "schema_version": "gib.beta1.prep.validation_report.v0.1",
        "block_id": "GIB",
        "phase": "beta1_prep",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "target_runtime": config["target_runtime"],
        "target_host": config["target_host"],
        "target_model": config["target_model"],
        "constraints_ok": result.constraints_ok,
        "constraints_issues": result.constraints_issues,
        "beta099_prereq_ok": result.beta099_prereq_ok,
        "beta099_prereq_issues": result.beta099_prereq_issues,
        "execution_allowed": config["execution_allowed"],
        "real_llm_call_allowed": config["real_llm_call_allowed"],
        "can_execute_now": result.can_execute_now,
        "release_gate": config["release_gate"],
        "beta099_snapshot": {
            "final_status": beta099["final_status"],
            "production_status": beta099["production_status"],
            "can_execute_now": beta099["can_execute_now"],
            "target_runtime": beta099["target_runtime"],
            "target_model": beta099["target_model"],
        },
    }


def write_beta1_prep_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta1_prep_contract()
    output_path = REPORTS_DIR / "gib_beta1_prep_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
