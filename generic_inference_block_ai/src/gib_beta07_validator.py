from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta07_simulation import load_and_run

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta07_contract() -> dict[str, Any]:
    config, beta06_report, sim = load_and_run()

    final_status = (
        "PASS_DRY_RUN_BETA07_READY_SIM_NO_AUTOCONNECT"
        if sim.config_valid
        and sim.base_ready_conditions_ok is False
        and sim.simulated_ready_conditions_ok is True
        and sim.auto_connect_triggered is False
        and config["real_llm_call_allowed"] is False
        and config["execution_allowed"] is False
        and config["generate_call_allowed"] is False
        and config["chat_call_allowed"] is False
        else "FAIL_BETA07_READY_SIM"
    )

    return {
        "schema_version": "gib.beta07.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0.7",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "runtime_target": config["runtime_target"],
        "real_llm_call_allowed": config["real_llm_call_allowed"],
        "execution_allowed": config["execution_allowed"],
        "generate_call_allowed": config["generate_call_allowed"],
        "chat_call_allowed": config["chat_call_allowed"],
        "base_ready_conditions_ok": sim.base_ready_conditions_ok,
        "simulated_ready_conditions_ok": sim.simulated_ready_conditions_ok,
        "auto_connect_on_ready": config["auto_connect_on_ready"],
        "auto_connect_triggered": sim.auto_connect_triggered,
        "simulation_overrides": config["simulation_overrides"],
        "simulated_state": sim.simulated_state,
        "beta06_snapshot": {
            "final_status": beta06_report["final_status"],
            "ready_conditions_ok": beta06_report["ready_conditions_ok"],
            "ready_for_connecting_stage": beta06_report["ready_for_connecting_stage"],
            "production_status": beta06_report["production_status"],
        },
    }


def write_beta07_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta07_contract()
    output_path = REPORTS_DIR / "gib_beta07_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
