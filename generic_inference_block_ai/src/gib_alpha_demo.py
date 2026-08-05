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


def run_demo_no_execution() -> dict[str, Any]:
    policy = assert_policy_safe(POLICY_PATH)
    load_and_validate_task_config(TASKS_PATH)

    samples = _load_json(SAMPLES_PATH)
    adapter = StubInferenceAdapter()
    responses = []

    for raw_request in samples["requests"]:
        request = GIBAlphaRequest(
            task_type=raw_request["task_type"],
            input=raw_request.get("input", {}),
        )
        response = adapter.generate(request)
        responses.append({
            "task_type": response.task_type,
            "status": response.status,
            "model_runtime": response.model_runtime,
            "execution_effect": response.execution_effect,
            "blocked": response.blocked,
            "block_reason": response.block_reason,
            "output": response.output,
        })

    return {
        "schema_version": "gib.alpha.demo_report.v0.1",
        "block_id": "GIB",
        "phase": policy["phase"],
        "final_status": "PASS_DRY_RUN_STUB_DEMO_ONLY",
        "production_status": "NO_GO",
        "execution_allowed": False,
        "real_llm_call_allowed": False,
        "credential_access_allowed": False,
        "wordpress_write_allowed": False,
        "responses": responses,
    }


def write_demo_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = run_demo_no_execution()
    output_path = REPORTS_DIR / "gib_alpha_demo_report.json"
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
