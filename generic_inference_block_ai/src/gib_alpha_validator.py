from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_policy import assert_policy_safe
from generic_inference_block_ai.src.gib_alpha_tasks import load_and_validate_task_config
from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest, StubInferenceAdapter

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
POLICY_PATH = _ROOT / "config" / "gib_alpha_policy.json"
TASKS_PATH = _ROOT / "config" / "gib_alpha_tasks.json"
SAMPLES_PATH = _ROOT / "samples" / "gib_alpha_sample_requests.json"
REPORTS_DIR = _ROOT / "reports"


def validate_alpha_contract() -> dict[str, Any]:
    policy = assert_policy_safe(POLICY_PATH)
    task_config = load_and_validate_task_config(TASKS_PATH)

    samples = _load_json(SAMPLES_PATH)
    requests = samples.get("requests", [])
    if not isinstance(requests, list):
        raise RuntimeError("sample requests must be a list")

    adapter = StubInferenceAdapter()
    sample_results = []

    for index, raw_request in enumerate(requests):
        request = GIBAlphaRequest(
            task_type=raw_request["task_type"],
            input=raw_request.get("input", {}),
        )
        response = adapter.generate(request)
        sample_results.append({
            "index": index,
            "task_type": response.task_type,
            "status": response.status,
            "blocked": response.blocked,
            "execution_effect": response.execution_effect,
            "model_runtime": response.model_runtime,
        })

    return {
        "schema_version": "gib.alpha.validation_report.v0.1",
        "block_id": "GIB",
        "phase": policy["phase"],
        "final_status": "PASS_DESIGN_ONLY_ALPHA_TEMPLATE",
        "production_status": policy["production_status"],
        "execution_allowed": policy["execution_allowed"],
        "external_network_allowed": policy["external_network_allowed"],
        "credential_access_allowed": policy["credential_access_allowed"],
        "wordpress_write_allowed": policy["wordpress_write_allowed"],
        "systemd_operation_allowed": policy["systemd_operation_allowed"],
        "model_runtime_enabled": policy["model_runtime_enabled"],
        "real_llm_call_allowed": policy["real_llm_call_allowed"],
        "task_count": len(task_config["tasks"]),
        "sample_request_count": len(sample_results),
        "sample_results": sample_results,
    }


def write_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_alpha_contract()
    output_path = REPORTS_DIR / "gib_alpha_validation_report.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return data
