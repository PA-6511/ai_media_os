#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_token_efficiency_policy.json"

REQUIRED_KEYS = {
    "phase",
    "name",
    "status",
    "production_status",
    "execution_status",
    "dry_run_only",
    "external_api_call_allowed",
    "wordpress_write_allowed",
    "production_write_allowed",
    "credential_output_allowed",
    "live_execution_allowed",
    "copilot_agent_default_allowed",
    "max_files_per_ai_context",
    "max_lines_per_file_excerpt",
    "git_diff_full_paste_allowed",
    "pytest_full_log_paste_allowed",
    "evidence_index_full_paste_allowed",
    "report_full_regeneration_allowed",
    "allowed_ai_context_inputs",
    "forbidden_ai_context_inputs",
    "safety_rule_pack_id",
    "safety_rule_pack",
}

REQUIRED_FALSE_FLAGS = [
    "external_api_call_allowed",
    "wordpress_write_allowed",
    "production_write_allowed",
    "credential_output_allowed",
    "live_execution_allowed",
    "copilot_agent_default_allowed",
]

REQUIRED_FULL_PASTE_FALSE = [
    "git_diff_full_paste_allowed",
    "pytest_full_log_paste_allowed",
    "evidence_index_full_paste_allowed",
]

REQUIRED_SAFETY_RULE_PACK = {
    "production_write_allowed": False,
    "wordpress_write_allowed": False,
    "external_api_call_allowed": False,
    "credential_output_allowed": False,
    "live_execution_allowed": False,
    "dry_run_only": True,
    "evidence_only": True,
    "next_phase_forward_execution": False,
    "secret_reading_allowed": False,
    "secret_printing_allowed": False,
}


class PolicyValidationError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_policy_data(policy: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_KEYS - set(policy.keys()))
    if missing:
        raise PolicyValidationError(f"missing required keys: {missing}")

    if policy.get("phase") != "AB-T0":
        raise PolicyValidationError("phase must be AB-T0")

    if policy.get("production_status") != "NO_GO":
        raise PolicyValidationError("production_status must be NO_GO")

    if policy.get("execution_status") != "NO_EXECUTION":
        raise PolicyValidationError("execution_status must be NO_EXECUTION")

    if policy.get("dry_run_only") is not True:
        raise PolicyValidationError("dry_run_only must be true")

    for key in REQUIRED_FALSE_FLAGS:
        if policy.get(key) is not False:
            raise PolicyValidationError(f"{key} must be false")

    max_files = policy.get("max_files_per_ai_context")
    if not isinstance(max_files, int):
        raise PolicyValidationError("max_files_per_ai_context must be int")
    if max_files > 5:
        raise PolicyValidationError("max_files_per_ai_context must be <= 5")

    for key in REQUIRED_FULL_PASTE_FALSE:
        if policy.get(key) is not False:
            raise PolicyValidationError(f"{key} must be false")

    if policy.get("safety_rule_pack_id") != "SAFETY_RULE_PACK_AB_V1":
        raise PolicyValidationError("safety_rule_pack_id must be SAFETY_RULE_PACK_AB_V1")

    rule_pack = policy.get("safety_rule_pack")
    if not isinstance(rule_pack, dict):
        raise PolicyValidationError("safety_rule_pack must be an object")

    for key, expected in REQUIRED_SAFETY_RULE_PACK.items():
        if rule_pack.get(key) is not expected:
            raise PolicyValidationError(f"safety_rule_pack.{key} must be {str(expected).lower()}")

    return {
        "phase": policy["phase"],
        "name": policy["name"],
        "status": "PASS",
        "validated_keys": sorted(REQUIRED_KEYS),
    }


def validate_policy_file(policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    path = Path(policy_path)
    if not path.exists():
        raise PolicyValidationError(f"policy file not found: {path}")
    payload = _load_json(path)
    return validate_policy_data(payload)


def main() -> None:
    try:
        result = validate_policy_file(DEFAULT_POLICY)
    except PolicyValidationError as exc:
        raise SystemExit(f"AB-T0 policy validation failed: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
