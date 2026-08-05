#!/usr/bin/env python3
"""Phase8-40A: Adapter route overall NO_GO re-aggregation validator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/phase8_40a_adapter_route_overall_no_go_reaggregation_policy.json"
REQUEST = ROOT / "exchange/examples/phase8_40a_adapter_route_overall_no_go_reaggregation_request.example.json"
OUTPUT = ROOT / "exchange/logs/phase8_40a_adapter_route_overall_no_go_reaggregation_result.json"


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
        "phase": "8-40A",
        "phase_name": "Adapter Route Overall NO_GO Report Re-Aggregation",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "decision_now": "NO_GO_KEEP_HOLD",
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
        "status": "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_ABORT_NO_EXECUTION",
        "policy_violations": [],
        "missing_sources": [],
        "status_mismatch_sources": [],
        "invariant_failures": [],
        "errors": [],
        "warnings": [],
        "source_reports": {},
        "summary": {
            "adapter_route_pack_completed": False,
            "publish_execution_unlocked": False,
            "safety_violations_empty": False
        },
        "evidence_summary": [],
    }

    try:
        policy = _load_json(policy_path)
        request = _load_json(request_path)
    except Exception as exc:
        result = {**base, "policy_violations": [f"input_load_error: {exc}"]}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    policy_violations: list[str] = []
    missing_sources: list[str] = []
    status_mismatch_sources: list[str] = []
    invariant_failures: list[str] = []
    source_reports: dict[str, str] = {}
    evidence_summary: list[dict[str, Any]] = []

    if request.get("mode") != "CONNECTION_TEST":
        policy_violations.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        policy_violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        policy_violations.append("request.production_status must be NO_GO")
    if request.get("decision_now") != "NO_GO_KEEP_HOLD":
        policy_violations.append("request.decision_now must be NO_GO_KEEP_HOLD")
    if request.get("reaggregation_requested") is not True:
        policy_violations.append("request.reaggregation_requested must be true")

    required_false_flags = [str(x) for x in policy.get("required_false_flags", [])]
    for flag in required_false_flags:
        if request.get(flag) is not False:
            policy_violations.append(f"request.{flag} must be false")

    root = _resolve_root(policy_path)
    loaded: dict[str, dict[str, Any]] = {}
    for key, rel in policy.get("required_reports", {}).items():
        rel_path = str(rel)
        source_reports[key] = rel_path
        p = root / rel_path
        exists = p.exists()
        payload: dict[str, Any] = {}
        status = None
        if exists:
            try:
                payload = _load_json(p)
                loaded[key] = payload
                status = payload.get("status")
            except Exception:
                missing_sources.append(f"{key}_unreadable")
                exists = False
        else:
            missing_sources.append(key)

        evidence_summary.append({
            "key": key,
            "path": rel_path,
            "exists": exists,
            "status": status,
        })

    for key, expected in policy.get("required_statuses", {}).items():
        payload = loaded.get(key)
        if not isinstance(payload, dict):
            continue
        actual = str(payload.get("status"))
        if actual != str(expected):
            status_mismatch_sources.append(f"{key}: expected={expected}, actual={actual}")

    for report_key in ("adapter6", "phase8_38a", "phase8_39a", "phase8_38_from_adapter5", "adapter5_result"):
        payload = loaded.get(report_key, {})
        if isinstance(payload, dict):
            for flag in required_false_flags:
                if flag in payload and payload.get(flag) is not False:
                    invariant_failures.append(f"{report_key}.{flag}")

    if invariant_failures:
        policy_violations.append("invariant_failure_detected")

    adapter_route_pack_completed = not missing_sources and not status_mismatch_sources
    safety_violations_empty = not invariant_failures

    status = "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_FIXED"
    if missing_sources:
        status = "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_ABORT_MISSING_EVIDENCE_NO_EXECUTION"
    elif status_mismatch_sources:
        status = "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_ABORT_STATUS_MISMATCH_NO_EXECUTION"
    elif policy_violations:
        status = "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_ABORT_POLICY_VIOLATION_NO_EXECUTION"

    result = {
        **base,
        "status": status,
        "policy_violations": policy_violations,
        "missing_sources": missing_sources,
        "status_mismatch_sources": status_mismatch_sources,
        "invariant_failures": invariant_failures,
        "source_reports": source_reports,
        "summary": {
            "adapter_route_pack_completed": adapter_route_pack_completed,
            "publish_execution_unlocked": False,
            "safety_violations_empty": safety_violations_empty
        },
        "evidence_summary": evidence_summary,
        "next_step": "KEEP_HOLD_AND_MONITOR" if status == "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_FIXED" else "FIX_EVIDENCE_AND_REAGGREGATE",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_FIXED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
