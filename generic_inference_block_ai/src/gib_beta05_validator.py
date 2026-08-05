from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta05_preflight import load_and_run

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_beta05_contract() -> dict[str, Any]:
    config, result = load_and_run()

    final_status = (
        "PASS_DRY_RUN_BETA05_LOCAL_OLLAMA_PREFLIGHT_NO_GENERATE_CALL"
        if result.config_valid
        and result.all_endpoints_valid
        and result.model_allowed
        and result.forbidden_host_rejected
        and (result.generate_api_called is False)
        and (result.chat_api_called is False)
        else "FAIL_BETA05_PREFLIGHT"
    )

    return {
        "schema_version": "gib.beta05.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0.5",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "real_llm_call_allowed": config["real_llm_call_allowed"],
        "execution_allowed": config["execution_allowed"],
        "generate_call_allowed": config["generate_call_allowed"],
        "chat_call_allowed": config["chat_call_allowed"],
        "ollama_binary_found": result.ollama_binary_found,
        "ollama_binary_path": result.ollama_binary_path,
        "all_endpoints_valid": result.all_endpoints_valid,
        "model_allowed": result.model_allowed,
        "forbidden_host_rejected": result.forbidden_host_rejected,
        "generate_api_called": result.generate_api_called,
        "chat_api_called": result.chat_api_called,
        "ready_for_connecting_stage": result.ready_for_connecting_stage,
        "endpoint_checks": [
            {
                "endpoint": item.endpoint,
                "host_allowed": item.host_allowed,
                "port_allowed": item.port_allowed,
                "valid_scheme": item.valid_scheme,
                "valid": item.valid,
            }
            for item in result.endpoint_checks
        ],
    }


def write_beta05_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta05_contract()
    output_path = REPORTS_DIR / "gib_beta05_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
