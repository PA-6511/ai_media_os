from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha3_adapter_blueprint import RuntimeDesignOnlyAdapter
from generic_inference_block_ai.src.gib_alpha3_runtime_design import load_and_validate_runtime_design

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
SAMPLES_PATH = _ROOT / "samples" / "gib_alpha_sample_requests.json"
REPORTS_DIR = _ROOT / "reports"


def validate_alpha3_contract() -> dict[str, Any]:
    runtime_design = load_and_validate_runtime_design()

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
                "template_rendered": result.alpha2_result.template_rendered,
                "runtime": result.runtime_plan.runtime,
                "runtime_would_call": result.runtime_plan.would_call,
                "runtime_reason": result.runtime_plan.reason,
                "runtime_endpoint": result.runtime_plan.endpoint,
                "model_placeholder": result.runtime_plan.model_placeholder,
                "execution_effect": result.response.execution_effect,
                "model_runtime": result.response.model_runtime,
            }
        )

    all_fully_valid = all(x["fully_valid"] for x in sample_results)
    no_runtime_call = all(x["runtime_would_call"] is False for x in sample_results)

    return {
        "schema_version": "gib.alpha3.validation_report.v0.1",
        "block_id": "GIB",
        "alpha_version": "alpha3",
        "final_status": "PASS_DESIGN_ONLY_ALPHA3_RUNTIME_BLUEPRINT" if all_fully_valid and no_runtime_call else "FAIL_ALPHA3_CONTRACT",
        "production_status": runtime_design["production_status"],
        "execution_allowed": runtime_design["execution_allowed"],
        "external_network_allowed": runtime_design["external_network_allowed"],
        "credential_access_allowed": runtime_design["credential_access_allowed"],
        "wordpress_write_allowed": runtime_design["wordpress_write_allowed"],
        "systemd_operation_allowed": runtime_design["systemd_operation_allowed"],
        "model_runtime_enabled": runtime_design["model_runtime_enabled"],
        "real_llm_call_allowed": runtime_design["real_llm_call_allowed"],
        "active_runtime_locked": runtime_design["runtime_selection"]["active_runtime_locked"],
        "all_samples_fully_valid": all_fully_valid,
        "all_samples_no_runtime_call": no_runtime_call,
        "sample_request_count": len(sample_results),
        "sample_results": sample_results,
    }


def write_alpha3_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_alpha3_contract()
    output_path = REPORTS_DIR / "gib_alpha3_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return data
