from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_validator import validate_alpha_contract
from generic_inference_block_ai.src.gib_alpha1_validator import validate_alpha1_contract
from generic_inference_block_ai.src.gib_alpha2_validator import validate_alpha2_contract
from generic_inference_block_ai.src.gib_alpha3_validator import validate_alpha3_contract
from generic_inference_block_ai.src.gib_alpha4_validator import validate_alpha4_contract
from generic_inference_block_ai.src.gib_alpha45_validator import validate_alpha45_contract
from generic_inference_block_ai.src.gib_beta0_validator import validate_beta0_contract
from generic_inference_block_ai.src.gib_beta05_validator import validate_beta05_contract
from generic_inference_block_ai.src.gib_beta06_validator import validate_beta06_contract
from generic_inference_block_ai.src.gib_beta07_validator import validate_beta07_contract
from generic_inference_block_ai.src.gib_beta08_validator import validate_beta08_contract
from generic_inference_block_ai.src.gib_beta09_validator import validate_beta09_contract
from generic_inference_block_ai.src.gib_beta095_validator import validate_beta095_contract
from generic_inference_block_ai.src.gib_beta099_validator import validate_beta099_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"

_EXPECTED_STATUS = {
    "alpha0": "PASS_DESIGN_ONLY_ALPHA_TEMPLATE",
    "alpha1": "PASS_DESIGN_ONLY_ALPHA1_SCHEMA_STRICT",
    "alpha2": "PASS_DESIGN_ONLY_ALPHA2_TEMPLATE_RENDERED",
    "alpha3": "PASS_DESIGN_ONLY_ALPHA3_RUNTIME_BLUEPRINT",
    "alpha4": "PASS_DESIGN_ONLY_ALPHA4_RUNTIME_GATE_FIXED",
    "alpha4_5": "PASS_DESIGN_ONLY_ALPHA45_PROMOTION_CHECKLIST_FIXED",
    "beta0": "PASS_DRY_RUN_BETA0_LOCAL_OLLAMA_HARNESS",
    "beta0_5": "PASS_DRY_RUN_BETA05_LOCAL_OLLAMA_PREFLIGHT_NO_GENERATE_CALL",
    "beta0_6": "PASS_DRY_RUN_BETA06_ENV_PREP_CHECK_NO_GENERATE",
    "beta0_7": "PASS_DRY_RUN_BETA07_READY_SIM_NO_AUTOCONNECT",
    "beta0_8": "PASS_DRY_RUN_BETA08_MANUAL_APPROVAL_GATE_NO_REAL_CALL",
    "beta0_9": "PASS_DRY_RUN_BETA09_FIRST_CALL_HANDOFF_NO_EXECUTION",
    "beta0_95": "PASS_DRY_RUN_BETA095_APPROVAL_EVIDENCE_FORMAT_ONLY",
    "beta0_99": "PASS_DRY_RUN_BETA099_FINAL_APPROVAL_GATE_NO_EXECUTION",
}


def build_freeze_report() -> dict[str, Any]:
    runs: dict[str, dict[str, Any]] = {
        "alpha0": validate_alpha_contract(),
        "alpha1": validate_alpha1_contract(),
        "alpha2": validate_alpha2_contract(),
        "alpha3": validate_alpha3_contract(),
        "alpha4": validate_alpha4_contract(),
        "alpha4_5": validate_alpha45_contract(),
        "beta0": validate_beta0_contract(),
        "beta0_5": validate_beta05_contract(),
        "beta0_6": validate_beta06_contract(),
        "beta0_7": validate_beta07_contract(),
        "beta0_8": validate_beta08_contract(),
        "beta0_9": validate_beta09_contract(),
        "beta0_95": validate_beta095_contract(),
        "beta0_99": validate_beta099_contract(),
    }

    phase_results: list[dict[str, Any]] = []
    failures: list[str] = []

    for phase, report in runs.items():
        expected = _EXPECTED_STATUS[phase]
        actual = report.get("final_status")
        status_ok = actual == expected
        production_status = report.get("production_status")
        production_ok = production_status == "NO_GO"
        if not status_ok:
            failures.append(f"{phase}: expected final_status={expected}, actual={actual}")
        if not production_ok:
            failures.append(f"{phase}: production_status must be NO_GO, actual={production_status}")

        phase_results.append(
            {
                "phase": phase,
                "expected_final_status": expected,
                "actual_final_status": actual,
                "final_status_ok": status_ok,
                "production_status": production_status,
                "production_status_ok": production_ok,
            }
        )

    all_pass = len(failures) == 0

    return {
        "schema_version": "gib.freeze.report.v0.1",
        "block_id": "GIB",
        "report_type": "BETA099_FINAL_FREEZE_REPORT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "range": {
            "from": "alpha0",
            "to": "beta0.99",
        },
        "all_pass": all_pass,
        "phase_count": len(phase_results),
        "phase_results": phase_results,
        "failures": failures,
        "safety_summary": {
            "real_llm_call_allowed": runs["beta0_99"]["current_guardrails"]["real_llm_call_allowed"],
            "execution_allowed": runs["beta0_99"]["current_guardrails"]["execution_allowed"],
            "generate_call_allowed": runs["beta0_99"]["current_guardrails"]["generate_call_allowed"],
            "chat_call_allowed": runs["beta0_99"]["current_guardrails"]["chat_call_allowed"],
            "production_status": runs["beta0_99"]["production_status"],
            "can_execute_now": runs["beta0_99"]["can_execute_now"],
        },
        "release_recommendation": "HOLD_BETA1_UNTIL_EXPLICIT_APPROVAL_AND_FLAG_SWITCH",
    }


def write_freeze_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_freeze_report()
    out = REPORTS_DIR / "gib_beta099_freeze_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
