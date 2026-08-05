#!/usr/bin/env python3
"""Validate Phase 7-1 VPS connection test policy."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/vps_connection_test_policy.json"
OUTPUT = ROOT / "exchange/logs/phase7_1_vps_connection_policy_validation_result.json"

ALLOWED_CHECKS = {
    "ping",
    "tcp_22",
    "ssh_banner",
    "ssh_auth_dry_run",
    "latency_sample",
}
FORBIDDEN_TERMS = ("password", "token", "secret", "private_key")


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_1_vps_connection_policy_validation_result",
        "phase": "Phase 7-1",
        "status": "ABORT",
        "reason": reason,
        "policy_valid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _scan_forbidden(obj, path: str = "root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()
            if any(term in key_lower for term in FORBIDDEN_TERMS):
                return f"forbidden term detected in key: {path}.{key}"
            found = _scan_forbidden(value, f"{path}.{key}")
            if found:
                return found
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            found = _scan_forbidden(value, f"{path}[{idx}]")
            if found:
                return found
    elif isinstance(obj, str):
        value_lower = obj.lower()
        if any(term in value_lower for term in FORBIDDEN_TERMS):
            return f"forbidden term detected in value: {path}"
    return None


def run_validation(config_path: Path = CONFIG, output_path: Path = OUTPUT) -> dict:
    if not config_path.exists():
        return _abort(f"config not found: {config_path}")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _abort(f"invalid JSON: {exc}")

    forbidden = _scan_forbidden(data)
    if forbidden:
        return _abort(forbidden)

    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("human_review_required") is not True:
        return _abort("human_review_required must be true")
    if data.get("auto_execute") is not False:
        return _abort("auto_execute must be false")
    if data.get("allow_remote_write") is not False:
        return _abort("allow_remote_write must be false")
    if data.get("allow_remote_delete") is not False:
        return _abort("allow_remote_delete must be false")
    if data.get("allow_remote_command_exec") is not False:
        return _abort("allow_remote_command_exec must be false")

    allowed_checks = data.get("allowed_checks")
    if not isinstance(allowed_checks, list):
        return _abort("allowed_checks must be a list")
    if set(allowed_checks) != ALLOWED_CHECKS:
        return _abort("allowed_checks must exactly match the approved checks")

    result = {
        "package_type": "phase7_1_vps_connection_policy_validation_result",
        "phase": "Phase 7-1",
        "status": "PASS",
        "reason": "vps connection test policy is valid and safe",
        "policy_valid": True,
        "mode": data.get("mode"),
        "execution": data.get("execution"),
        "production_status": data.get("production_status"),
        "human_review_required": data.get("human_review_required"),
        "auto_execute": data.get("auto_execute"),
        "allow_remote_write": data.get("allow_remote_write"),
        "allow_remote_delete": data.get("allow_remote_delete"),
        "allow_remote_command_exec": data.get("allow_remote_command_exec"),
        "allowed_checks": allowed_checks,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())