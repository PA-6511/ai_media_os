"""GIB-alpha2 full validation report generator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_policy import assert_policy_safe
from generic_inference_block_ai.src.gib_alpha_tasks import load_and_validate_task_config
from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha2_templates import (
    load_template_config,
    validate_template_config,
)
from generic_inference_block_ai.src.gib_alpha2_adapter import TemplateValidatedAdapter

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
POLICY_PATH  = _ROOT / "config" / "gib_alpha_policy.json"
TASKS_PATH   = _ROOT / "config" / "gib_alpha_tasks.json"
SAMPLES_PATH = _ROOT / "samples" / "gib_alpha_sample_requests.json"
REPORTS_DIR  = _ROOT / "reports"


def validate_alpha2_contract() -> dict[str, Any]:
    policy = assert_policy_safe(POLICY_PATH)
    task_config = load_and_validate_task_config(TASKS_PATH)
    template_config = load_template_config()

    task_types = list(task_config["tasks"].keys())
    template_issues = validate_template_config(template_config)

    samples  = _load_json(SAMPLES_PATH)
    requests = samples.get("requests", [])
    adapter  = TemplateValidatedAdapter()

    sample_results = []
    for index, raw in enumerate(requests):
        request = GIBAlphaRequest(
            task_type=raw["task_type"],
            input=raw.get("input", {}),
        )
        result = adapter.generate_alpha2(request)
        sample_results.append({
            "index":                index,
            "task_type":            result.response.task_type,
            "status":               result.response.status,
            "blocked":              result.response.blocked,
            "schema_valid":         result.schema_valid,
            "template_rendered":    result.template_rendered,
            "fully_valid":          result.fully_valid,
            "template_render_error":result.template_render_error,
            "execution_effect":     result.response.execution_effect,
            "model_runtime":        result.response.model_runtime,
            "rendered_prompt_len":  len(result.rendered_user_prompt) if result.rendered_user_prompt else 0,
        })

    all_fully_valid = all(r["fully_valid"] for r in sample_results)

    return {
        "schema_version":           "gib.alpha2.validation_report.v0.1",
        "block_id":                 "GIB",
        "alpha_version":            "alpha2",
        "phase":                    policy["phase"],
        "final_status":             "PASS_DESIGN_ONLY_ALPHA2_TEMPLATE_RENDERED" if all_fully_valid else "FAIL_TEMPLATE_ISSUES_FOUND",
        "production_status":        policy["production_status"],
        "execution_allowed":        policy["execution_allowed"],
        "external_network_allowed": policy["external_network_allowed"],
        "credential_access_allowed":policy["credential_access_allowed"],
        "wordpress_write_allowed":  policy["wordpress_write_allowed"],
        "systemd_operation_allowed":policy["systemd_operation_allowed"],
        "model_runtime_enabled":    policy["model_runtime_enabled"],
        "real_llm_call_allowed":    policy["real_llm_call_allowed"],
        "template_config_valid":    not template_issues,
        "template_config_issues":   template_issues,
        "task_template_count":      len(template_config.get("task_templates", {})),
        "all_samples_fully_valid":  all_fully_valid,
        "sample_request_count":     len(sample_results),
        "sample_results":           sample_results,
    }


def write_alpha2_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_alpha2_contract()
    output_path = REPORTS_DIR / "gib_alpha2_validation_report.json"
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
