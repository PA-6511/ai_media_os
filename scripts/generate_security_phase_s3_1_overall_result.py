#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_phase_s3_1_common import load_json, now_iso  # noqa: E402


CONFIG_PATH = ROOT / "config" / "security_observability_event_replay_phase_s3_1.json"
REPLAY_RESULT_PATH = ROOT / "exchange" / "logs" / "security_observability_event_replay_phase_s3_1_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s3_1_overall_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s3_1_overall_result.md"


def generate_security_phase_s3_1_overall_result(
    config_path: Path = CONFIG_PATH,
    replay_result_path: Path = REPLAY_RESULT_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict:
    config = load_json(Path(config_path))
    replay = load_json(Path(replay_result_path))

    any_abort = any(replay.get("abort_reasons", [])) or replay.get("replay_result") == "ABORT"
    any_fail = any(replay.get("fail_reasons", [])) or replay.get("replay_result") == "FAIL"
    any_warning = any(replay.get("warnings", [])) or replay.get("replay_result") == "WARN"
    matched_expected = int(replay.get("matched_expected_count", 0))
    mismatched_expected = int(replay.get("mismatched_expected_count", 0))
    event_count = int(replay.get("event_count", 0))
    freeze_recommendation = bool(replay.get("freeze_recommendation_detected", False))
    human_review_recommendation = bool(replay.get("human_review_recommendation_detected", False))

    if any_abort:
        final_status = "ABORT"
    elif mismatched_expected > 0:
        final_status = "OBSERVABILITY_REVIEW_REQUIRED"
    elif replay.get("replay_result") in {"PASS", "WARN", "FAIL"} and event_count > 0:
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "OBSERVABILITY_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S3_1",
        "phase_name": "dry_run_observability_event_replay",
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "detector_only": True,
        "recommendation_only": True,
        "executor_action_allowed": False,
        "event_replay_completed": True,
        "event_count": event_count,
        "matched_expected_count": matched_expected,
        "mismatched_expected_count": mismatched_expected,
        "any_abort_detected": any_abort,
        "any_fail_detected": any_fail,
        "any_warning_detected": any_warning,
        "freeze_recommendation_detected": freeze_recommendation,
        "human_review_recommendation_detected": human_review_recommendation,
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
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Phase S-3.1 Overall Result",
        "",
        f"- final_status: {result.get('final_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- detector_only: {result.get('detector_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- event_replay_completed: {result.get('event_replay_completed')}",
        f"- event_count: {result.get('event_count')}",
        f"- matched_expected_count: {result.get('matched_expected_count')}",
        f"- mismatched_expected_count: {result.get('mismatched_expected_count')}",
        f"- any_abort_detected: {result.get('any_abort_detected')}",
        f"- any_fail_detected: {result.get('any_fail_detected')}",
        f"- any_warning_detected: {result.get('any_warning_detected')}",
        f"- freeze_recommendation_detected: {result.get('freeze_recommendation_detected')}",
        f"- human_review_recommendation_detected: {result.get('human_review_recommendation_detected')}",
        f"- state_change_executed: {result.get('state_change_executed')}",
        f"- freeze_executed: {result.get('freeze_executed')}",
        f"- revoke_executed: {result.get('revoke_executed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- process_kill_executed: {result.get('process_kill_executed')}",
        f"- scheduler_stop_executed: {result.get('scheduler_stop_executed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- external_api_call_executed: {result.get('external_api_call_executed')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## replay_result",
        f"- {replay.get('replay_result')}",
        "",
        "## validator_results",
    ]
    for item in replay.get("event_results", []):
        lines.append(
            f"- {item.get('event_id')}: actual={item.get('actual_result')} expected={item.get('expected_result')} freeze_recommendation={item.get('freeze_recommendation')} human_review_recommendation={item.get('human_review_recommendation')}"
        )
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_phase_s3_1_overall_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] in {"PASS_DRY_RUN_ONLY", "OBSERVABILITY_REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
