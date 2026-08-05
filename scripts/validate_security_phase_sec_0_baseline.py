#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "security_phase_sec_0_baseline.json"
OUTPUT_PATH = ROOT / "exchange" / "logs" / "security_phase_sec_0_validation_result.json"


REQUIRED_TRUE_FLAGS = [
    "human_approval_required",
    "emergency_freeze_required",
    "block_isolation_required",
    "external_write_stop_required",
    "secret_rotation_required",
    "backup_protection_required",
    "recovery_core_design_only",
    "evidence_lock_required",
]

REQUIRED_PROHIBITED_ACTIONS = [
    "wordpress_write",
    "wordpress_update",
    "wordpress_delete",
    "github_push",
    "external_api_execution",
    "production_deployment",
    "automatic_recovery_execution",
    "automatic_rollback_execution",
    "automatic_connector_switching",
    "vps_migration",
    "modify_env",
    "modify_secrets",
    "enable_production_mode",
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("baseline config must be a JSON object")
    return data


def require_equal(data: Dict[str, Any], key: str, expected: Any, reasons: List[str]) -> None:
    actual = data.get(key)
    if actual != expected:
        reasons.append(f"{key} must be {expected!r}, got {actual!r}")


def require_true(data: Dict[str, Any], key: str, reasons: List[str]) -> None:
    if data.get(key) is not True:
        reasons.append(f"{key} must be true")


def require_list_contains(
    data: Dict[str, Any],
    key: str,
    required_values: List[str],
    reasons: List[str],
) -> None:
    values = data.get(key)
    if not isinstance(values, list):
        reasons.append(f"{key} must be a list")
        return

    missing = [value for value in required_values if value not in values]
    if missing:
        reasons.append(f"{key} missing required values: {missing}")


def require_non_empty_list(data: Dict[str, Any], key: str, reasons: List[str]) -> None:
    values = data.get(key)
    if not isinstance(values, list) or not values:
        reasons.append(f"{key} must be a non-empty list")


def validate_baseline(data: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []

    require_equal(data, "phase_id", "PHASE_SEC_0", reasons)
    require_equal(data, "status", "DESIGN_ONLY", reasons)
    require_equal(data, "execution", "DRY_RUN", reasons)
    require_equal(data, "production_status", "NO_GO", reasons)

    for flag in REQUIRED_TRUE_FLAGS:
        require_true(data, flag, reasons)

    require_list_contains(data, "prohibited_actions", REQUIRED_PROHIBITED_ACTIONS, reasons)
    require_list_contains(data, "assumed_threats", ["ransomware"], reasons)
    require_non_empty_list(data, "abort_conditions", reasons)
    require_non_empty_list(data, "allowed_next_steps", reasons)

    status = "PASS" if not reasons else "FAIL"

    return {
        "phase_id": "PHASE_SEC_0",
        "validator": "validate_security_phase_sec_0_baseline",
        "status": status,
        "production_status": data.get("production_status"),
        "execution": data.get("execution"),
        "human_approval_required": data.get("human_approval_required"),
        "emergency_freeze_required": data.get("emergency_freeze_required"),
        "block_isolation_required": data.get("block_isolation_required"),
        "external_write_stop_required": data.get("external_write_stop_required"),
        "secret_rotation_required": data.get("secret_rotation_required"),
        "backup_protection_required": data.get("backup_protection_required"),
        "recovery_core_design_only": data.get("recovery_core_design_only"),
        "evidence_lock_required": data.get("evidence_lock_required"),
        "reasons": reasons,
        "next_step": "phase_sec_1_or_manual_review" if status == "PASS" else "fix_baseline_config",
    }


def write_result(result: Dict[str, Any], output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    try:
        data = load_json(CONFIG_PATH)
        result = validate_baseline(data)
    except Exception as exc:
        result = {
            "phase_id": "PHASE_SEC_0",
            "validator": "validate_security_phase_sec_0_baseline",
            "status": "ABORT",
            "production_status": "NO_GO",
            "execution": "DRY_RUN",
            "reasons": [f"validator_exception: {exc}"],
            "next_step": "manual_review",
        }

    write_result(result)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
