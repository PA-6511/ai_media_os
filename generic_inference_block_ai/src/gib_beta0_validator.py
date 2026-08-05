from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha3_adapter_blueprint import RuntimeDesignOnlyAdapter
from generic_inference_block_ai.src.gib_alpha45_promotion_gate import load_and_evaluate
from generic_inference_block_ai.src.gib_beta0_harness import (
    build_probe_plan,
    load_and_validate_beta0_config,
)

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
SAMPLES_PATH = _ROOT / "samples" / "gib_alpha_sample_requests.json"
REPORTS_DIR = _ROOT / "reports"


def validate_beta0_contract() -> dict[str, Any]:
    config = load_and_validate_beta0_config()
    alpha45_config, alpha45_gate = load_and_evaluate()

    if not alpha45_gate.all_decisions_made:
        raise RuntimeError("alpha4.5 decisions are not complete; cannot run beta0 harness validation")

    probe_plan = build_probe_plan(config)

    samples = _load_json(SAMPLES_PATH)
    requests = samples.get("requests", [])
    if not isinstance(requests, list):
        raise RuntimeError("sample requests must be a list")

    adapter = RuntimeDesignOnlyAdapter()
    sample_results = []

    for index, raw in enumerate(requests):
        request = GIBAlphaRequest(task_type=raw["task_type"], input=raw.get("input", {}))
        result = adapter.generate_alpha3(request)
        sample_results.append(
            {
                "index": index,
                "task_type": result.response.task_type,
                "status": result.response.status,
                "blocked": result.response.blocked,
                "fully_valid": result.fully_valid,
                "runtime_plan_would_call": result.runtime_plan.would_call,
                "probe_would_call": probe_plan.would_call,
                "probe_blocked_reason": probe_plan.blocked_reason,
                "fallback_runtime": probe_plan.fallback_runtime,
                "execution_effect": result.response.execution_effect,
                "model_runtime": result.response.model_runtime,
            }
        )

    all_fully_valid = all(item["fully_valid"] for item in sample_results)
    all_probe_blocked = all(item["probe_would_call"] is False for item in sample_results)
    all_runtime_non_exec = all(item["runtime_plan_would_call"] is False for item in sample_results)

    final_status = (
        "PASS_DRY_RUN_BETA0_LOCAL_OLLAMA_HARNESS"
        if all_fully_valid and all_probe_blocked and all_runtime_non_exec
        else "FAIL_BETA0_HARNESS_CONTRACT"
    )

    return {
        "schema_version": "gib.beta0.validation_report.v0.1",
        "block_id": "GIB",
        "beta_version": "beta0",
        "final_status": final_status,
        "status": config["status"],
        "production_status": config["production_status"],
        "runtime_target": config["runtime_target"],
        "probe_endpoint": probe_plan.endpoint,
        "probe_would_call": probe_plan.would_call,
        "probe_blocked_reason": probe_plan.blocked_reason,
        "fallback_runtime": probe_plan.fallback_runtime,
        "alpha45_all_decisions_made": alpha45_gate.all_decisions_made,
        "alpha45_beta0_ready": alpha45_gate.beta0_ready,
        "safety_flags": config["safety_flags"],
        "all_samples_fully_valid": all_fully_valid,
        "all_samples_probe_blocked": all_probe_blocked,
        "all_samples_runtime_non_exec": all_runtime_non_exec,
        "sample_request_count": len(sample_results),
        "sample_results": sample_results,
    }


def write_beta0_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_beta0_contract()
    output_path = REPORTS_DIR / "gib_beta0_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return data
