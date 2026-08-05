#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_phase_s3_common import (  # noqa: E402
    build_base_result,
    evaluate_s3_abort_conditions,
    finalize_result,
    load_json,
    write_result,
)


CONFIG_PATH = ROOT / "config" / "security_scheduler_anomaly_detector_phase_s3.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_scheduler_anomaly_detector_phase_s3_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_scheduler_anomaly_detector_phase_s3_validation_result.md"


def validate_security_scheduler_anomaly_detector_phase_s3(data: dict) -> dict:
    result = build_base_result(data, "validate_security_scheduler_anomaly_detector_phase_s3")
    result["abort_reasons"].extend(evaluate_s3_abort_conditions(data))

    thresholds = data.get("thresholds")
    sample_event = data.get("sample_event")
    actions = data.get("actions")

    if not isinstance(thresholds, dict):
        result["fail_reasons"].append("thresholds must be object")
        return finalize_result(result)
    if not isinstance(sample_event, dict):
        result["fail_reasons"].append("sample_event must be object")
        return finalize_result(result)
    if not isinstance(actions, dict):
        result["fail_reasons"].append("actions must be object")
        return finalize_result(result)

    for action_key in ["auto_freeze_execute", "auto_scheduler_stop_execute", "auto_retry_disable_execute", "process_kill_execute"]:
        if actions.get(action_key) is True:
            result["abort_reasons"].append(f"actions.{action_key}=true is prohibited")

    def eval_metric(name: str, value: int) -> None:
        warn_v = thresholds.get(f"{name}_warn")
        fail_v = thresholds.get(f"{name}_fail")
        abort_v = thresholds.get(f"{name}_abort")
        if not all(isinstance(v, int) for v in [warn_v, fail_v, abort_v]):
            result["fail_reasons"].append(f"{name} thresholds must be int")
            return
        if value >= abort_v:
            result["abort_reasons"].append(f"{name} exceeds abort threshold: {value}>={abort_v}")
            if name in {"retry_count", "queue_depth", "cron_runs_per_hour"}:
                result["freeze_recommendation"] = True
        elif value >= fail_v:
            result["fail_reasons"].append(f"{name} exceeds fail threshold: {value}>={fail_v}")
            if name in {"retry_count", "queue_depth", "cron_runs_per_hour"}:
                result["freeze_recommendation"] = True
            if name == "duplicate_run":
                result["human_review_recommendation"] = True
        elif value >= warn_v:
            result["warnings"].append(f"{name} exceeds warn threshold: {value}>={warn_v}")
            if name in {"retry_count", "queue_depth", "cron_runs_per_hour"}:
                result["freeze_recommendation"] = True
            if name == "duplicate_run":
                result["human_review_recommendation"] = True

    eval_metric("retry_count", int(sample_event.get("retry_count", 0)))
    eval_metric("queue_depth", int(sample_event.get("queue_depth", 0)))
    eval_metric("cron_runs_per_hour", int(sample_event.get("cron_runs_per_hour", 0)))
    eval_metric("duplicate_run", int(sample_event.get("duplicate_runs", 0)))

    return finalize_result(result)


def main() -> int:
    try:
        data = load_json(CONFIG_PATH)
        result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    except Exception as exc:
        result = build_base_result({}, "validate_security_scheduler_anomaly_detector_phase_s3")
        result["abort_reasons"] = [f"validator_exception: {exc}"]
        result = finalize_result(result)

    write_result(
        OUTPUT_JSON_PATH,
        OUTPUT_MD_PATH,
        result,
        "Security Scheduler Anomaly Detector Phase S-3 Validation",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
