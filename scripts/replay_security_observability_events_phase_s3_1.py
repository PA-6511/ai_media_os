#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_phase_s3_1_common import (  # noqa: E402
    evaluate_external_api_event,
    evaluate_env_event,
    evaluate_process_event,
    evaluate_scheduler_event,
    evaluate_wordpress_event,
    load_json,
    now_iso,
    write_result,
)


CONFIG_PATH = ROOT / "config" / "security_observability_event_replay_phase_s3_1.json"
BATCH_PATH = ROOT / "exchange" / "examples" / "security_observability_phase_s3_event_batch.example.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_observability_event_replay_phase_s3_1_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_observability_event_replay_phase_s3_1_result.md"


def _worst(results: list[str]) -> str:
    order = {"PASS": 0, "WARN": 1, "FAIL": 2, "ABORT": 3}
    return max(results, key=lambda item: order[item]) if results else "PASS"


def replay_security_observability_events_phase_s3_1(
    config_path: Path = CONFIG_PATH,
    batch_path: Path = BATCH_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict:
    config = load_json(Path(config_path))
    batch = load_json(Path(batch_path))

    event_results: list[dict[str, object]] = []
    matched_expected_count = 0
    mismatched_expected_count = 0
    freeze_recommendation_detected = False
    human_review_recommendation_detected = False

    events = batch.get("events", [])
    if not isinstance(events, list):
        raise ValueError("event batch events must be a list")

    thresholds = config.get("thresholds", {})
    known_intents = set(config.get("known_api_intents", []))
    denied_api_intents = set(config.get("denied_api_intents", []))
    observe_intents = set(config.get("observe_intents", []))
    denied_env_intents = set(config.get("denied_intents", []))

    results: list[str] = []
    abort_reasons: list[str] = []
    fail_reasons: list[str] = []
    warnings: list[str] = []

    for event in events:
        if not isinstance(event, dict):
            raise ValueError("event must be an object")
        event_id = str(event.get("event_id", "unknown_event"))
        event_type = str(event.get("event_type", ""))
        expected = str(event.get("expected_result", "PASS"))
        actual = "PASS"
        freeze_recommendation = False
        human_review_recommendation = False
        reasons: list[str] = []

        if event_type == "scheduler_anomaly":
            actual, freeze_recommendation, human_review_recommendation, reasons = evaluate_scheduler_event(event, thresholds)
        elif event_type == "wordpress_write_intent":
            actual, freeze_recommendation, human_review_recommendation, reasons = evaluate_wordpress_event(event)
        elif event_type == "external_api_intent":
            actual, freeze_recommendation, human_review_recommendation, reasons = evaluate_external_api_event(event, known_intents, denied_api_intents)
        elif event_type == "env_access_intent":
            actual, freeze_recommendation, human_review_recommendation, reasons = evaluate_env_event(event, denied_env_intents, observe_intents)
        elif event_type == "process_anomaly":
            actual, freeze_recommendation, human_review_recommendation, reasons = evaluate_process_event(event)
        else:
            actual = "WARN"
            human_review_recommendation = True
            reasons = [f"unknown event_type: {event_type}"]

        if expected == actual:
            matched_expected_count += 1
        else:
            mismatched_expected_count += 1

        freeze_recommendation_detected = freeze_recommendation_detected or freeze_recommendation
        human_review_recommendation_detected = human_review_recommendation_detected or human_review_recommendation
        results.append(actual)
        event_results.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "expected_result": expected,
                "actual_result": actual,
                "freeze_recommendation": freeze_recommendation,
                "human_review_recommendation": human_review_recommendation,
                "reasons": reasons,
            }
        )

    event_count = len(events)
    if any(result == "ABORT" for result in results):
        replay_result = "ABORT"
    elif any(result == "FAIL" for result in results):
        replay_result = "FAIL"
    elif any(result == "WARN" for result in results):
        replay_result = "WARN"
    else:
        replay_result = "PASS"

    if any(result == "ABORT" for result in results):
        abort_reasons.append("abort event detected in replay")
    if any(result == "FAIL" for result in results):
        fail_reasons.append("failure event detected in replay")
    if any(result == "WARN" for result in results):
        warnings.append("warning event detected in replay")

    if mismatched_expected_count > 0:
        fail_reasons.append("expected result mismatch detected")

    if replay_result in {"FAIL", "ABORT", "WARN"} and not freeze_recommendation_detected:
        # keep recommendation semantics explicit when replay detects issues.
        freeze_recommendation_detected = any(item["freeze_recommendation"] for item in event_results)
    if replay_result in {"FAIL", "WARN", "ABORT"} and not human_review_recommendation_detected:
        human_review_recommendation_detected = any(item["human_review_recommendation"] for item in event_results)

    result = {
        "phase_id": "PHASE_S3_1",
        "phase_name": "dry_run_observability_event_replay",
        "replay_result": replay_result,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "detector_only": True,
        "recommendation_only": True,
        "executor_action_allowed": False,
        "event_count": event_count,
        "matched_expected_count": matched_expected_count,
        "mismatched_expected_count": mismatched_expected_count,
        "event_results": event_results,
        "freeze_recommendation_detected": freeze_recommendation_detected,
        "human_review_recommendation_detected": human_review_recommendation_detected,
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
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
    write_result(output_json_path, output_md_path, result, "Security Observability Event Replay Phase S-3.1 Result")
    return result


def main() -> int:
    result = replay_security_observability_events_phase_s3_1()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["replay_result"] in {"PASS", "WARN", "FAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
