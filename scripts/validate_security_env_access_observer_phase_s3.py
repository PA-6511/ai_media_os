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


CONFIG_PATH = ROOT / "config" / "security_env_access_observer_phase_s3.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_env_access_observer_phase_s3_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_env_access_observer_phase_s3_validation_result.md"


def validate_security_env_access_observer_phase_s3(data: dict) -> dict:
    result = build_base_result(data, "validate_security_env_access_observer_phase_s3")
    result["abort_reasons"].extend(evaluate_s3_abort_conditions(data))

    sample_intent = data.get("sample_intent", "")
    observe_intents = set(data.get("observe_intents", []))
    denied_intents = set(data.get("denied_intents", []))

    actions = data.get("actions", {})
    if actions.get("secret_output_execute") is True:
        result["abort_reasons"].append("actions.secret_output_execute=true is prohibited")
    if actions.get("secret_read_execute") is True:
        result["abort_reasons"].append("actions.secret_read_execute=true is prohibited")
    if actions.get("auto_revoke_execute") is True:
        result["abort_reasons"].append("actions.auto_revoke_execute=true is prohibited")

    if sample_intent in denied_intents:
        result["fail_reasons"].append(f"denied env access intent detected: {sample_intent}")
        if sample_intent == "secret_value_echo":
            result["freeze_recommendation"] = True
        if sample_intent == "prod_secret_usage_without_human_approval":
            result["human_review_recommendation"] = True
        if sample_intent in {"env_file_content_read", "token_value_echo", "plaintext_secret_logging"}:
            result["human_review_recommendation"] = True
    elif sample_intent in observe_intents:
        pass
    elif sample_intent:
        result["warnings"].append(f"unknown env access intent detected: {sample_intent}")
        result["human_review_recommendation"] = True

    return finalize_result(result)


def main() -> int:
    try:
        data = load_json(CONFIG_PATH)
        result = validate_security_env_access_observer_phase_s3(data)
    except Exception as exc:
        result = build_base_result({}, "validate_security_env_access_observer_phase_s3")
        result["abort_reasons"] = [f"validator_exception: {exc}"]
        result = finalize_result(result)

    write_result(
        OUTPUT_JSON_PATH,
        OUTPUT_MD_PATH,
        result,
        "Security Env Access Observer Phase S-3 Validation",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
