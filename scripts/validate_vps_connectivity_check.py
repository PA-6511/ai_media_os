#!/usr/bin/env python3
"""Validate Phase 7-2 VPS connectivity check record."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "exchange/logs/vps_connectivity_check.example.json"

TCP_ALLOWED = {"PASS", "WARN", "FAIL"}
SSH_BANNER_ALLOWED = {"PASS", "WARN", "FAIL", "SKIP"}
SSH_AUTH_ALLOWED = {"PASS", "WARN", "FAIL", "SKIP"}


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_2_vps_connectivity_check_validation_result",
        "phase": "Phase 7-2",
        "status": "ABORT",
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path = INPUT) -> dict:
    if not input_path.exists():
        return _abort(f"input not found: {input_path}")

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _abort(f"invalid JSON: {exc}")

    for required in ("check_id", "target_host_alias", "timestamp_utc", "reason"):
        if not data.get(required):
            return _abort(f"{required} is required")

    if data.get("tcp_22_result") not in TCP_ALLOWED:
        return _abort("tcp_22_result must be PASS/WARN/FAIL")
    if data.get("ssh_banner_result") not in SSH_BANNER_ALLOWED:
        return _abort("ssh_banner_result must be PASS/WARN/FAIL/SKIP")
    if data.get("ssh_auth_dry_run_result") not in SSH_AUTH_ALLOWED:
        return _abort("ssh_auth_dry_run_result must be PASS/WARN/FAIL/SKIP")

    latency_ms = data.get("latency_ms")
    if not isinstance(latency_ms, (int, float)) or latency_ms < 0:
        return _abort("latency_ms must be >= 0")

    packet_loss = data.get("packet_loss_percent")
    if not isinstance(packet_loss, (int, float)) or packet_loss < 0 or packet_loss > 100:
        return _abort("packet_loss_percent must be between 0 and 100")

    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("remote_write_executed") is not False:
        return _abort("remote_write_executed must be false")
    if data.get("remote_command_executed") is not False:
        return _abort("remote_command_executed must be false")

    if data.get("secrets_exposed") is True:
        return _abort("secrets_exposed=true is forbidden")
    if data.get("secrets_exposed") is not False:
        return _abort("secrets_exposed must be false")

    return {
        "package_type": "phase7_2_vps_connectivity_check_validation_result",
        "phase": "Phase 7-2",
        "status": "PASS",
        "reason": "connectivity check record is valid",
        "check_id": data.get("check_id"),
        "target_host_alias": data.get("target_host_alias"),
        "production_status": data.get("production_status"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())