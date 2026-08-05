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


CONFIG_PATH = ROOT / "config" / "security_observability_policy_phase_s3.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_observability_policy_phase_s3_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_observability_policy_phase_s3_validation_result.md"


def validate_security_observability_policy_phase_s3(data: dict) -> dict:
    result = build_base_result(data, "validate_security_observability_policy_phase_s3")
    result["abort_reasons"].extend(evaluate_s3_abort_conditions(data))

    if data.get("execution") != "DRY_RUN":
        result["fail_reasons"].append("execution must be DRY_RUN")
    if data.get("production_status") != "NO_GO":
        result["fail_reasons"].append("production_status must be NO_GO")
    if data.get("detector_only") is not True:
        result["fail_reasons"].append("detector_only must be true")
    if data.get("recommendation_only") is not True:
        result["fail_reasons"].append("recommendation_only must be true")
    if data.get("executor_action_allowed") is not False:
        result["fail_reasons"].append("executor_action_allowed must be false")

    for key in [
        "freeze_execution_allowed",
        "revoke_execution_allowed",
        "isolation_execution_allowed",
        "process_kill_allowed",
        "scheduler_stop_allowed",
        "wordpress_write_allowed",
        "external_api_call_allowed",
        "state_change_executed",
        "freeze_executed",
        "revoke_executed",
        "isolation_executed",
        "process_kill_executed",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
    ]:
        if data.get(key) is not False:
            result["fail_reasons"].append(f"{key} must be false")

    if data.get("freeze_recommendation_allowed") is not True:
        result["fail_reasons"].append("freeze_recommendation_allowed must be true")

    targets = data.get("observability_targets")
    if not isinstance(targets, list) or len(targets) != 5:
        result["fail_reasons"].append("observability_targets must include 5 required entries")

    return finalize_result(result)


def main() -> int:
    try:
        data = load_json(CONFIG_PATH)
        result = validate_security_observability_policy_phase_s3(data)
    except Exception as exc:
        result = build_base_result({}, "validate_security_observability_policy_phase_s3")
        result["abort_reasons"] = [f"validator_exception: {exc}"]
        result = finalize_result(result)

    write_result(
        OUTPUT_JSON_PATH,
        OUTPUT_MD_PATH,
        result,
        "Security Observability Policy Phase S-3 Validation",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
