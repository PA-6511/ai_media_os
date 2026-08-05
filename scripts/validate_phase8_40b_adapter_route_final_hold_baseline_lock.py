#!/usr/bin/env python3
"""Phase8-40B: Adapter route final HOLD baseline lock validator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/phase8_40b_adapter_route_final_hold_baseline_lock_policy.json"
REQUEST = ROOT / "exchange/examples/phase8_40b_adapter_route_final_hold_baseline_lock_request.example.json"
OUTPUT = ROOT / "exchange/logs/phase8_40b_adapter_route_final_hold_baseline_lock_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def validate(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_path = Path(output_path)

    base = {
        "phase": "8-40B",
        "phase_name": "Adapter Route Final HOLD Baseline Lock",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "hold_state": "HOLD",
        "baseline_locked": False,
        "approval_token_consumed": False,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "executed_external_changes": 0,
        "checked_at": _now_iso(),
        "status": "PHASE8_40B_FINAL_HOLD_BASELINE_LOCK_ABORT_NO_EXECUTION",
        "policy_violations": [],
        "missing_reports": [],
        "status_mismatches": [],
        "invariant_failures": [],
        "source_reports": {},
        "no_go_invariants_ok": False
    }

    try:
        policy = _load_json(policy_path)
        request = _load_json(request_path)
    except Exception as exc:
        result = {**base, "policy_violations": [f"input_load_error: {exc}"]}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    violations: list[str] = []
    missing_reports: list[str] = []
    status_mismatches: list[str] = []
    invariant_failures: list[str] = []
    source_reports: dict[str, str] = {}

    if request.get("mode") != "CONNECTION_TEST":
        violations.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        violations.append("request.production_status must be NO_GO")
    if request.get("hold_state") != "HOLD":
        violations.append("request.hold_state must be HOLD")
    if request.get("baseline_lock_requested") is not True:
        violations.append("request.baseline_lock_requested must be true")
    if request.get("approval_token_consumed") is not False:
        violations.append("request.approval_token_consumed must be false")

    required_false_flags = [str(x) for x in policy.get("required_false_flags", [])]
    for flag in required_false_flags:
        if request.get(flag) is not False:
            violations.append(f"request.{flag} must be false")

    root = _resolve_root(policy_path)
    loaded_reports: dict[str, dict[str, Any]] = {}
    for key, rel in policy.get("required_reports", {}).items():
        rel_path = str(rel)
        source_reports[key] = rel_path
        p = root / rel_path
        if not p.exists():
            missing_reports.append(key)
            continue
        try:
            loaded_reports[key] = _load_json(p)
        except Exception:
            missing_reports.append(f"{key}_unreadable")

    for key, expected in policy.get("required_statuses", {}).items():
        payload = loaded_reports.get(key)
        if not isinstance(payload, dict):
            continue
        actual = str(payload.get("status"))
        if actual != str(expected):
            status_mismatches.append(f"{key}: expected={expected}, actual={actual}")

    for report_key, payload in loaded_reports.items():
        if not isinstance(payload, dict):
            continue
        for flag in required_false_flags:
            if flag in payload and payload.get(flag) is not False:
                invariant_failures.append(f"{report_key}.{flag}")
        if "approval_token_consumed" in payload and payload.get("approval_token_consumed") is not False:
            invariant_failures.append(f"{report_key}.approval_token_consumed")

    if invariant_failures:
        violations.append("invariant_failure_detected")

    status = "PHASE8_40B_ADAPTER_ROUTE_FINAL_HOLD_BASELINE_LOCK_PASS_NO_EXECUTION"
    if missing_reports:
        status = "PHASE8_40B_FINAL_HOLD_BASELINE_LOCK_ABORT_MISSING_EVIDENCE_NO_EXECUTION"
    elif status_mismatches:
        status = "PHASE8_40B_FINAL_HOLD_BASELINE_LOCK_ABORT_STATUS_MISMATCH_NO_EXECUTION"
    elif violations:
        status = "PHASE8_40B_FINAL_HOLD_BASELINE_LOCK_ABORT_POLICY_VIOLATION_NO_EXECUTION"

    result = {
        **base,
        "status": status,
        "baseline_locked": status == "PHASE8_40B_ADAPTER_ROUTE_FINAL_HOLD_BASELINE_LOCK_PASS_NO_EXECUTION",
        "policy_violations": violations,
        "missing_reports": missing_reports,
        "status_mismatches": status_mismatches,
        "invariant_failures": invariant_failures,
        "source_reports": source_reports,
        "no_go_invariants_ok": len(invariant_failures) == 0,
        "next_action": "KEEP_HOLD_AND_MONITOR" if status.endswith("PASS_NO_EXECUTION") else "FIX_EVIDENCE_OR_POLICY_AND_REVALIDATE"
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PHASE8_40B_ADAPTER_ROUTE_FINAL_HOLD_BASELINE_LOCK_PASS_NO_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
