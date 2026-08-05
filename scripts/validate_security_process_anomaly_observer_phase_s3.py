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


CONFIG_PATH = ROOT / "config" / "security_process_anomaly_observer_phase_s3.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_process_anomaly_observer_phase_s3_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_process_anomaly_observer_phase_s3_validation_result.md"


def validate_security_process_anomaly_observer_phase_s3(data: dict) -> dict:
    result = build_base_result(data, "validate_security_process_anomaly_observer_phase_s3")
    result["abort_reasons"].extend(evaluate_s3_abort_conditions(data))

    actions = data.get("actions", {})
    if actions.get("process_kill_execute") is True:
        result["abort_reasons"].append("actions.process_kill_execute=true is prohibited")
    if actions.get("systemctl_execute") is True:
        result["abort_reasons"].append("actions.systemctl_execute=true is prohibited")
    if actions.get("cron_stop_execute") is True:
        result["abort_reasons"].append("actions.cron_stop_execute=true is prohibited")

    sample_intent = data.get("sample_intent", "normal")
    if sample_intent == "unexpected_python_worker":
        result["warnings"].append("unexpected python worker intent detected")
        result["human_review_recommendation"] = True
    elif sample_intent == "duplicated_runner":
        result["fail_reasons"].append("duplicated runner intent detected")
        result["freeze_recommendation"] = True
        result["human_review_recommendation"] = True
    elif sample_intent == "unknown_long_running_process":
        result["warnings"].append("unknown long running process intent detected")
        result["human_review_recommendation"] = True
    elif sample_intent == "unexpected_shell_command":
        result["fail_reasons"].append("unexpected shell command intent detected")
        result["human_review_recommendation"] = True
    elif sample_intent == "unexpected_network_tool_intent":
        result["warnings"].append("unexpected network tool intent detected")
        result["human_review_recommendation"] = True

    return finalize_result(result)


def main() -> int:
    try:
        data = load_json(CONFIG_PATH)
        result = validate_security_process_anomaly_observer_phase_s3(data)
    except Exception as exc:
        result = build_base_result({}, "validate_security_process_anomaly_observer_phase_s3")
        result["abort_reasons"] = [f"validator_exception: {exc}"]
        result = finalize_result(result)

    write_result(
        OUTPUT_JSON_PATH,
        OUTPUT_MD_PATH,
        result,
        "Security Process Anomaly Observer Phase S-3 Validation",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
