#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = ROOT / "config/x_fb_manual_operation_policy.json"
SCHEMA_PATH = ROOT / "config/x_post_wording_feedback_schema.json"
MANAGER_PATH = ROOT / "scripts/manage_x_feedback_record.py"
VALIDATOR_PATH = ROOT / "scripts/build_x_fb_0.py"

RESULT_PATH = ROOT / "exchange/logs/x_fb_1_result.json"
REPORT_PATH = ROOT / "reports/x_fb_1_manual_operation_report.md"

REQUEST_PATHS = [
    ROOT / "exchange/examples/x_fb_1_initialize_request.example.json",
    ROOT / "exchange/examples/x_fb_1_review_request.example.json",
    ROOT / "exchange/examples/x_fb_1_post_request.example.json",
    ROOT / "exchange/examples/x_fb_1_metrics_request.example.json",
]


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"required file missing: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValidationError(f"JSON root must be object: {path}")

    return data


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise ValidationError(f"failed to load module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    policy = load_json(POLICY_PATH)
    schema = load_json(SCHEMA_PATH)
    manager = load_module(MANAGER_PATH, "x_fb_1_manager")
    validator = load_module(VALIDATOR_PATH, "x_fb_0_validator_for_x_fb_1")

    if policy.get("phase_id") != "X-FB-1":
        raise ValidationError("policy phase mismatch")

    if (
        policy.get("feedback_schema_id")
        != schema.get("schema_id")
    ):
        raise ValidationError("schema reference mismatch")

    current = None
    stages: list[str] = []
    versions: list[int] = []
    actions: list[str] = []

    for request_path in REQUEST_PATHS:
        request = load_json(request_path)

        current = manager.apply_request(
            current=current,
            request=request,
            schema=schema,
            validator=validator,
        )

        stages.append(current["record_stage"])
        versions.append(current["record_version"])
        actions.append(request["action"])

    expected_stages = [
        "DRAFT_GENERATED",
        "HUMAN_REVIEWED",
        "POSTED",
        "METRICS_RECORDED",
    ]

    if stages != expected_stages:
        raise ValidationError(
            f"stage sequence mismatch: {stages}"
        )

    if versions != [1, 2, 3, 4]:
        raise ValidationError(
            f"version sequence mismatch: {versions}"
        )

    result = {
        "phase_id": "X-FB-1",
        "status": "PASS_MANUAL_OPERATION_BASELINE_NO_LIVE_POST",
        "decision": "VERSIONED_MANUAL_FEEDBACK_ROUTINE_READY",
        "policy_id": policy["policy_id"],
        "feedback_schema_id": schema["schema_id"],
        "verified_actions": actions,
        "verified_stage_sequence": stages,
        "verified_version_sequence": versions,
        "archive_required": True,
        "atomic_write_required": True,
        "silent_overwrite_allowed": False,
        "x_api_call_allowed": False,
        "x_post_allowed": False,
        "wordpress_write_allowed": False,
        "external_api_call_allowed": False,
        "automatic_rule_update_allowed": False,
        "algorithm_research_handoff_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "MANUAL_RECORDING_ONLY",
        "ready_for_real_manual_feedback_records": True,
        "ready_for_ls_new_batch_2": True,
        "next_phase_execution_allowed": False
    }

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    REPORT_PATH.write_text(
        f"""# X-FB-1 Manual Feedback Operation Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Policy: `{result["policy_id"]}`
- Schema: `{result["feedback_schema_id"]}`

## Verified Sequence

- Actions: `{" -> ".join(actions)}`
- Stages: `{" -> ".join(stages)}`
- Versions: `{" -> ".join(str(v) for v in versions)}`

## Version Control

- Previous version archive required: `true`
- Atomic write required: `true`
- Silent overwrite allowed: `false`

## Safety Boundary

- X API call allowed: `false`
- X posting allowed: `false`
- WordPress write allowed: `false`
- External API call allowed: `false`
- Automatic rule update allowed: `false`
- Production status: `NO_GO`
- Safety state: `MANUAL_RECORDING_ONLY`

## Next State

実際の新刊記事ごとに、INITIALIZE、REVIEW、POST、METRICSの
順で手動フィードバック記録を残せる状態です。

X投稿自体、WordPress更新、文言ルールの自動昇格は実行しません。
""",
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
