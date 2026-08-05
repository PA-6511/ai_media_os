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


CONFIG_PATH = ROOT / "config" / "security_wordpress_write_observer_phase_s3.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_wordpress_write_observer_phase_s3_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_wordpress_write_observer_phase_s3_validation_result.md"


def validate_security_wordpress_write_observer_phase_s3(data: dict) -> dict:
    result = build_base_result(data, "validate_security_wordpress_write_observer_phase_s3")
    result["abort_reasons"].extend(evaluate_s3_abort_conditions(data))

    if data.get("wordpress_mode") != "READ_ONLY":
        result["fail_reasons"].append("wordpress_mode must be READ_ONLY")

    actions = data.get("actions", {})
    if actions.get("wordpress_api_call_execute") is True:
        result["abort_reasons"].append("actions.wordpress_api_call_execute=true is prohibited")
    if actions.get("auto_freeze_execute") is True:
        result["abort_reasons"].append("actions.auto_freeze_execute=true is prohibited")
    if actions.get("auto_revoke_execute") is True:
        result["abort_reasons"].append("actions.auto_revoke_execute=true is prohibited")

    sample_intent = data.get("sample_intent", "none")
    fail_intents = {
        "draft_create_intent",
        "publish_intent",
        "update_intent",
        "delete_intent",
        "bulk_write_intent",
    }
    if sample_intent in fail_intents:
        result["fail_reasons"].append(f"unexpected wordpress write intent detected: {sample_intent}")
        result["freeze_recommendation"] = True
        result["human_review_recommendation"] = True
    elif sample_intent != "none":
        result["warnings"].append(f"unknown wordpress intent observed: {sample_intent}")
        result["human_review_recommendation"] = True

    return finalize_result(result)


def main() -> int:
    try:
        data = load_json(CONFIG_PATH)
        result = validate_security_wordpress_write_observer_phase_s3(data)
    except Exception as exc:
        result = build_base_result({}, "validate_security_wordpress_write_observer_phase_s3")
        result["abort_reasons"] = [f"validator_exception: {exc}"]
        result = finalize_result(result)

    write_result(
        OUTPUT_JSON_PATH,
        OUTPUT_MD_PATH,
        result,
        "Security WordPress Write Observer Phase S-3 Validation",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
