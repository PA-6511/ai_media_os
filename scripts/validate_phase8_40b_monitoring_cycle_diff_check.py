#!/usr/bin/env python3
"""MONITOR-1: Phase8-40B monitoring cycle drift detector."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/phase8_40b_monitoring_cycle_diff_check_policy.json"
REQUEST = ROOT / "exchange/examples/phase8_40b_monitoring_cycle_diff_check_request.example.json"
OUTPUT = ROOT / "exchange/logs/phase8_40b_monitoring_cycle_diff_check_result.json"


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
        "phase": "MONITOR-1",
        "phase_name": "Phase8-40B Monitoring Cycle Diff Check",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "hold_state": "HOLD",
        "checked_at": _now_iso(),
        "status": "MONITOR_1_ABORT_NO_EXECUTION",
        "policy_violations": [],
        "missing_reports": [],
        "status_mismatches": [],
        "drift_items": [],
        "source_reports": {},
        "checks": {
            "phase8_40b_baseline_locked": False,
            "phase8_40b_hold_state_is_hold": False,
            "no_go_maintained": False,
            "dry_run_maintained": False,
            "no_execution_maintained": False,
            "evidence_index_no_missing": False,
            "readiness_pack_updated": False,
            "credential_non_secret_pass": False,
            "creators_not_auto_eligible": False,
            "wordpress_write_false": False,
            "publish_false": False,
            "approval_token_consumed_false": False,
        },
        "all_checks_passed": False,
        "next_action": "INVESTIGATE_DRIFT_AND_RELOCK"
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
    drift_items: list[str] = []
    source_reports: dict[str, str] = {}

    if request.get("mode") != "CONNECTION_TEST":
        violations.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        violations.append("request.production_status must be NO_GO")
    if request.get("hold_state") != "HOLD":
        violations.append("request.hold_state must be HOLD")
    if request.get("monitoring_cycle_requested") is not True:
        violations.append("request.monitoring_cycle_requested must be true")

    root = _resolve_root(policy_path)
    loaded_reports: dict[str, Any] = {}
    for key, rel in policy.get("required_reports", {}).items():
        rel_path = str(rel)
        source_reports[key] = rel_path
        p = root / rel_path
        if not p.exists():
            missing_reports.append(key)
            continue

        if p.suffix.lower() == ".json":
            try:
                loaded_reports[key] = _load_json(p)
            except Exception:
                missing_reports.append(f"{key}_unreadable")
        else:
            loaded_reports[key] = p.read_text(encoding="utf-8")

    for key, expected in policy.get("required_statuses", {}).items():
        payload = loaded_reports.get(key)
        if not isinstance(payload, dict):
            continue
        actual = str(payload.get("status"))
        if actual != str(expected):
            status_mismatches.append(f"{key}: expected={expected}, actual={actual}")

    checks = dict(base["checks"])
    phase8_40b = loaded_reports.get("phase8_40b")
    credential = loaded_reports.get("credential_non_secret")
    creators = loaded_reports.get("creators_tracking")
    adapter_index = loaded_reports.get("adapter_route_index")
    evidence_index = loaded_reports.get("evidence_index")
    readiness_pack = loaded_reports.get("readiness_pack")

    if isinstance(phase8_40b, dict):
        checks["phase8_40b_baseline_locked"] = phase8_40b.get("baseline_locked") is True
        checks["phase8_40b_hold_state_is_hold"] = phase8_40b.get("hold_state") == "HOLD"
        checks["no_go_maintained"] = phase8_40b.get("production_status") == "NO_GO"
        checks["dry_run_maintained"] = phase8_40b.get("execution") == "DRY_RUN"
        checks["no_execution_maintained"] = phase8_40b.get("executed_external_changes") == 0

        required_false_flags = [str(x) for x in policy.get("required_false_flags", [])]
        for flag in required_false_flags:
            if phase8_40b.get(flag) is not False:
                drift_items.append(f"phase8_40b.{flag}")

        checks["wordpress_write_false"] = phase8_40b.get("wordpress_write_allowed") is False
        checks["publish_false"] = phase8_40b.get("publish_allowed") is False
        checks["approval_token_consumed_false"] = phase8_40b.get("approval_token_consumed") is False

    if isinstance(adapter_index, dict):
        checks["evidence_index_no_missing"] = len(adapter_index.get("missing", [])) == 0
        if adapter_index.get("next_action") != "KEEP_HOLD_AND_MONITOR":
            drift_items.append("adapter_route_index.next_action")

    if isinstance(credential, dict):
        checks["credential_non_secret_pass"] = credential.get("status") == "READY_NON_SECRET_CHECK_PASS"
        if credential.get("secret_values_output") is not False:
            drift_items.append("credential_non_secret.secret_values_output")

    if isinstance(creators, dict):
        checks["creators_not_auto_eligible"] = creators.get("status") == "EXTERNAL_TRACKING_REQUIRED"

    if isinstance(evidence_index, dict):
        names = {str(x.get("name")) for x in evidence_index.get("entries", []) if isinstance(x, dict)}
        for required_name in policy.get("required_evidence_index_names", []):
            if str(required_name) not in names:
                drift_items.append(f"evidence_index.missing_entry:{required_name}")

    if isinstance(readiness_pack, str):
        missing_strings: list[str] = []
        for needle in policy.get("required_readiness_pack_strings", []):
            if str(needle) not in readiness_pack:
                missing_strings.append(str(needle))
        checks["readiness_pack_updated"] = len(missing_strings) == 0
        for needle in missing_strings:
            drift_items.append(f"readiness_pack.missing_string:{needle}")

    for name, passed in checks.items():
        if not passed:
            drift_items.append(f"check_failed:{name}")

    all_checks_passed = len(drift_items) == 0

    status = "MONITOR_1_PHASE8_40B_HOLD_DIFF_CHECK_PASS"
    if missing_reports:
        status = "MONITOR_1_ABORT_MISSING_EVIDENCE"
    elif status_mismatches:
        status = "MONITOR_1_ABORT_STATUS_MISMATCH"
    elif violations:
        status = "MONITOR_1_ABORT_POLICY_VIOLATION"
    elif not all_checks_passed:
        status = "MONITOR_1_DRIFT_DETECTED_KEEP_HOLD"

    result = {
        **base,
        "status": status,
        "policy_violations": violations,
        "missing_reports": missing_reports,
        "status_mismatches": status_mismatches,
        "drift_items": drift_items,
        "source_reports": source_reports,
        "checks": checks,
        "all_checks_passed": all_checks_passed,
        "next_action": "KEEP_HOLD_AND_MONITOR" if status == "MONITOR_1_PHASE8_40B_HOLD_DIFF_CHECK_PASS" else "INVESTIGATE_DRIFT_AND_RELOCK"
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "MONITOR_1_PHASE8_40B_HOLD_DIFF_CHECK_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())