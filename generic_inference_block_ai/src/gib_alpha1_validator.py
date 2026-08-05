"""GIB-alpha1 full validation report generator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_policy import assert_policy_safe, load_json
from generic_inference_block_ai.src.gib_alpha_tasks import load_and_validate_task_config
from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha1_schema import (
    load_input_schemas,
    load_output_schemas,
    validate_task_input,
)
from generic_inference_block_ai.src.gib_alpha1_adapter import ValidatedInferenceAdapter

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
POLICY_PATH   = _ROOT / "config" / "gib_alpha_policy.json"
TASKS_PATH    = _ROOT / "config" / "gib_alpha_tasks.json"
SAMPLES_PATH  = _ROOT / "samples" / "gib_alpha_sample_requests.json"
REPORTS_DIR   = _ROOT / "reports"


def validate_alpha1_contract() -> dict[str, Any]:
    policy = assert_policy_safe(POLICY_PATH)
    task_config = load_and_validate_task_config(TASKS_PATH)

    input_schemas  = load_input_schemas()
    output_schemas = load_output_schemas()

    # Verify schema coverage matches task list
    task_types = list(task_config["tasks"].keys())
    input_covered  = list(input_schemas.get("task_schemas", {}).keys())
    output_covered = list(output_schemas.get("task_schemas", {}).keys())
    missing_input  = sorted(set(task_types) - set(input_covered))
    missing_output = sorted(set(task_types) - set(output_covered))

    samples  = _load_json(SAMPLES_PATH)
    requests = samples.get("requests", [])
    adapter  = ValidatedInferenceAdapter()

    sample_results = []
    for index, raw in enumerate(requests):
        request = GIBAlphaRequest(
            task_type=raw["task_type"],
            input=raw.get("input", {}),
        )
        result = adapter.generate_validated(request)
        sample_results.append({
            "index":               index,
            "task_type":           result.response.task_type,
            "status":              result.response.status,
            "blocked":             result.response.blocked,
            "schema_valid":        result.schema_valid,
            "input_schema_issues": result.input_schema_issues,
            "output_schema_issues":result.output_schema_issues,
            "execution_effect":    result.response.execution_effect,
            "model_runtime":       result.response.model_runtime,
        })

    all_schema_valid = all(r["schema_valid"] for r in sample_results)

    return {
        "schema_version":         "gib.alpha1.validation_report.v0.1",
        "block_id":               "GIB",
        "alpha_version":          "alpha1",
        "phase":                  policy["phase"],
        "final_status":           "PASS_DESIGN_ONLY_ALPHA1_SCHEMA_STRICT" if all_schema_valid else "FAIL_SCHEMA_VIOLATIONS_FOUND",
        "production_status":      policy["production_status"],
        "execution_allowed":      policy["execution_allowed"],
        "external_network_allowed": policy["external_network_allowed"],
        "credential_access_allowed": policy["credential_access_allowed"],
        "wordpress_write_allowed":   policy["wordpress_write_allowed"],
        "systemd_operation_allowed": policy["systemd_operation_allowed"],
        "model_runtime_enabled":     policy["model_runtime_enabled"],
        "real_llm_call_allowed":     policy["real_llm_call_allowed"],
        "schema_coverage": {
            "task_count":       len(task_types),
            "input_schemas":    len(input_covered),
            "output_schemas":   len(output_covered),
            "missing_input":    missing_input,
            "missing_output":   missing_output,
            "coverage_complete": (not missing_input) and (not missing_output),
        },
        "all_samples_schema_valid": all_schema_valid,
        "sample_request_count":     len(sample_results),
        "sample_results":           sample_results,
    }


def write_alpha1_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_alpha1_contract()
    output_path = REPORTS_DIR / "gib_alpha1_validation_report.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return data
