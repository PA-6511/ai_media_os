#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_abort_conditions_shared_s2 import evaluate_shared_abort_conditions  # noqa: E402
from scripts.security_phase_s3_1_common import load_json, now_iso, write_result  # noqa: E402


CONFIG_PATH = ROOT / "config" / "security_observability_event_replay_phase_s3_1.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_observability_event_replay_phase_s3_1_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_observability_event_replay_phase_s3_1_validation_result.md"


def validate_security_observability_event_replay_phase_s3_1(data: dict) -> dict:
    abort_reasons = evaluate_shared_abort_conditions(data)
    fail_reasons: list[str] = []
    warnings: list[str] = []

    if data.get("detector_only") is False:
        abort_reasons.append("detector_only=false is prohibited")
    if data.get("recommendation_only") is False:
        abort_reasons.append("recommendation_only=false is prohibited")
    if data.get("executor_action_allowed") is True:
        abort_reasons.append("executor_action_allowed=true is prohibited")

    if data.get("event_replay_enabled") is not True:
        fail_reasons.append("event_replay_enabled must be true")
    if data.get("event_replay_mode") == "LIVE":
        abort_reasons.append("event_replay_mode=LIVE is prohibited")
    elif data.get("event_replay_mode") != "DRY_RUN_ONLY":
        fail_reasons.append("event_replay_mode must be DRY_RUN_ONLY")

    if data.get("freeze_recommendation_allowed") is not True:
        fail_reasons.append("freeze_recommendation_allowed must be true")
    if data.get("human_review_recommendation_allowed") is not True:
        fail_reasons.append("human_review_recommendation_allowed must be true")
    if data.get("executor_action_recommendation_allowed") is True:
        abort_reasons.append("executor_action_recommendation_allowed=true is prohibited")

    if data.get("phase_id") != "PHASE_S3_1":
        fail_reasons.append("phase_id must be PHASE_S3_1")
    if data.get("phase_name") != "dry_run_observability_event_replay":
        fail_reasons.append("phase_name must be dry_run_observability_event_replay")
    if data.get("execution") != "DRY_RUN":
        fail_reasons.append("execution must be DRY_RUN")
    if data.get("production_status") != "NO_GO":
        fail_reasons.append("production_status must be NO_GO")
    if data.get("human_approval_required") is not True:
        fail_reasons.append("human_approval_required must be true")
    for key in [
        "freeze_execution_allowed",
        "revoke_execution_allowed",
        "isolation_execution_allowed",
        "process_kill_allowed",
        "scheduler_stop_allowed",
        "wordpress_write_allowed",
        "external_api_call_allowed",
        "freeze_executed",
        "revoke_executed",
        "isolation_executed",
        "process_kill_executed",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
    ]:
        if data.get(key) is not False:
            fail_reasons.append(f"{key} must be false")

    for key in [
        "freeze_executed",
        "revoke_executed",
        "isolation_executed",
        "process_kill_executed",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
    ]:
        if data.get(key) is True:
            abort_reasons.append(f"{key}=true is prohibited")

    if not isinstance(data.get("expected_event_results"), dict):
        fail_reasons.append("expected_event_results must exist as object")
    if not isinstance(data.get("expected_recommendations"), dict):
        fail_reasons.append("expected_recommendations must exist as object")

    if abort_reasons:
        validator_result = "ABORT"
    elif fail_reasons:
        validator_result = "FAIL"
    elif warnings:
        validator_result = "WARN"
    else:
        validator_result = "PASS"

    result = {
        "phase_id": "PHASE_S3_1",
        "phase_name": "dry_run_observability_event_replay",
        "validator_result": validator_result,
        "phase_status": "DESIGN_ONLY",
        "execution": data.get("execution"),
        "production_status": data.get("production_status"),
        "human_approval_required": data.get("human_approval_required"),
        "detector_only": data.get("detector_only"),
        "recommendation_only": data.get("recommendation_only"),
        "executor_action_allowed": data.get("executor_action_allowed"),
        "event_replay_enabled": data.get("event_replay_enabled"),
        "event_replay_mode": data.get("event_replay_mode"),
        "freeze_recommendation_allowed": data.get("freeze_recommendation_allowed"),
        "human_review_recommendation_allowed": data.get("human_review_recommendation_allowed"),
        "executor_action_recommendation_allowed": data.get("executor_action_recommendation_allowed"),
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "state_change_executed": bool(data.get("state_change_executed", False)),
        "freeze_executed": bool(data.get("freeze_executed", False)),
        "revoke_executed": bool(data.get("revoke_executed", False)),
        "isolation_executed": bool(data.get("isolation_executed", False)),
        "process_kill_executed": bool(data.get("process_kill_executed", False)),
        "scheduler_stop_executed": bool(data.get("scheduler_stop_executed", False)),
        "wordpress_write_executed": bool(data.get("wordpress_write_executed", False)),
        "external_api_call_executed": bool(data.get("external_api_call_executed", False)),
        "timestamp": now_iso(),
        "next_step": "prepare_cross_phase_security_audit_view",
    }
    return result


def main() -> int:
    try:
        data = load_json(CONFIG_PATH)
        result = validate_security_observability_event_replay_phase_s3_1(data)
    except Exception as exc:
        result = {
            "phase_id": "PHASE_S3_1",
            "phase_name": "dry_run_observability_event_replay",
            "validator_result": "ABORT",
            "phase_status": "DESIGN_ONLY",
            "execution": "DRY_RUN",
            "production_status": "NO_GO",
            "human_approval_required": True,
            "detector_only": True,
            "recommendation_only": True,
            "executor_action_allowed": False,
            "event_replay_enabled": True,
            "event_replay_mode": "DRY_RUN_ONLY",
            "freeze_recommendation_allowed": True,
            "human_review_recommendation_allowed": True,
            "executor_action_recommendation_allowed": False,
            "abort_reasons": [f"validator_exception: {exc}"],
            "fail_reasons": [],
            "warnings": [],
            "state_change_executed": False,
            "freeze_executed": False,
            "revoke_executed": False,
            "isolation_executed": False,
            "process_kill_executed": False,
            "scheduler_stop_executed": False,
            "wordpress_write_executed": False,
            "external_api_call_executed": False,
            "timestamp": now_iso(),
            "next_step": "prepare_cross_phase_security_audit_view",
        }

    write_result(
        OUTPUT_JSON_PATH,
        OUTPUT_MD_PATH,
        result,
        "Security Observability Event Replay Phase S-3.1 Validation",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
