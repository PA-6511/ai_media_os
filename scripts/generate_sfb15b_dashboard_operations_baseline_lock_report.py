#!/usr/bin/env python3
"""SFB-15B: Dashboard operations baseline lock report generator."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/sfb_15b_dashboard_operations_baseline_lock_policy.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def _safe_read_json(path: Path) -> tuple[bool, dict[str, Any]]:
    if not path.exists():
        return False, {}
    try:
        return True, _read_json(path)
    except Exception:
        return False, {}


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    checks = result["checks"]
    lines = [
        "# SFB-15B Dashboard Operations Baseline Lock Report",
        "",
        f"- status: {result['status']}",
        f"- phase: {result['phase']}",
        f"- generated_at: {result['generated_at']}",
        f"- baseline_locked: {str(result['baseline_locked']).lower()}",
        f"- hold_state: {result['hold_state']}",
        f"- production_status: {result['production_status']}",
        f"- mode: {result['mode']}",
        "",
        "## Checks",
        f"- required_json_reports_present: {str(checks['required_json_reports_present']).lower()}",
        f"- expected_statuses_ok: {str(checks['expected_statuses_ok']).lower()}",
        f"- required_test_files_present: {str(checks['required_test_files_present']).lower()}",
        f"- phase_mapping_lock_ok: {str(checks['phase_mapping_lock_ok']).lower()}",
        f"- undefined_mapping_guard_configured: {str(checks['undefined_mapping_guard_configured']).lower()}",
        f"- no_go_invariants_ok: {str(checks['no_go_invariants_ok']).lower()}",
        "",
        "## Missing",
        f"- missing_json_reports: {', '.join(checks['missing_json_reports']) if checks['missing_json_reports'] else 'none'}",
        f"- missing_test_files: {', '.join(checks['missing_test_files']) if checks['missing_test_files'] else 'none'}",
        "",
        "## Summary",
        f"- locked_scope: {result['summary']['locked_scope']}",
        f"- hold_recommendation: {result['summary']['hold_recommendation']}",
        f"- next_action: {result['summary']['next_action']}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate(policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = _read_json(policy_path)

    required_json_reports = dict(policy.get("required_json_reports", {}))
    expected_status = {k: list(v) for k, v in dict(policy.get("expected_status", {})).items()}
    required_files = dict(policy.get("required_files", {}))

    report_json = _resolve(policy.get("output", {}).get("report_json", "logs/sfb_15b_dashboard_operations_baseline_lock_report.json"))
    report_md = _resolve(policy.get("output", {}).get("report_md", "logs/sfb_15b_dashboard_operations_baseline_lock_report.md"))

    json_payloads: dict[str, dict[str, Any]] = {}
    json_found: dict[str, bool] = {}
    missing_json_reports: list[str] = []

    for key, raw_path in required_json_reports.items():
        path = _resolve(raw_path)
        ok, payload = _safe_read_json(path)
        json_found[key] = ok
        if not ok:
            missing_json_reports.append(key)
        json_payloads[key] = payload

    status_check_results: dict[str, bool] = {}
    for key, accepted in expected_status.items():
        current = str((json_payloads.get(key) or {}).get("status", ""))
        status_check_results[key] = current in set(accepted)

    missing_test_files: list[str] = []
    file_presence: dict[str, bool] = {}
    for key, raw_path in required_files.items():
        path = _resolve(raw_path)
        exists = path.exists()
        file_presence[key] = exists
        if not exists:
            missing_test_files.append(key)

    sfb14 = json_payloads.get("sfb14_dashboard", {})
    sfb14_artifacts = list(sfb14.get("artifacts", [])) if isinstance(sfb14.get("artifacts", []), list) else []
    sfb10b = next((a for a in sfb14_artifacts if a.get("id") == "sfb_10b_baseline"), {})

    phase_mapping_lock_ok = sfb10b.get("phase") == "SFB-10B" and bool(sfb10b.get("phase_raw"))
    undefined_mapping_guard_configured = (
        bool(sfb14.get("undefined_phase_mapping_count") is not None)
        and isinstance(sfb14.get("warn_list", []), list)
    )

    no_go_invariants_ok = True
    for key in ["sfb13_diff_report", "sfb14_dashboard", "sfb15_operations_readiness"]:
        payload = json_payloads.get(key, {})
        no_go_invariants_ok = no_go_invariants_ok and payload.get("production_status") == "NO_GO"
        no_go_invariants_ok = no_go_invariants_ok and payload.get("mode") == "DRY_RUN"
        no_go_invariants_ok = no_go_invariants_ok and payload.get("external_api_called") is False
        no_go_invariants_ok = no_go_invariants_ok and payload.get("external_network_called") is False
        no_go_invariants_ok = no_go_invariants_ok and payload.get("wordpress_write_executed") is False
        no_go_invariants_ok = no_go_invariants_ok and payload.get("approval_token_consumed") is False

    checks = {
        "required_json_reports_present": len(missing_json_reports) == 0,
        "missing_json_reports": missing_json_reports,
        "expected_statuses_ok": all(status_check_results.values()) if status_check_results else False,
        "status_check_results": status_check_results,
        "required_test_files_present": len(missing_test_files) == 0,
        "missing_test_files": missing_test_files,
        "file_presence": file_presence,
        "phase_mapping_lock_ok": phase_mapping_lock_ok,
        "undefined_mapping_guard_configured": undefined_mapping_guard_configured,
        "no_go_invariants_ok": no_go_invariants_ok,
    }

    baseline_locked = all(
        [
            checks["required_json_reports_present"],
            checks["expected_statuses_ok"],
            checks["required_test_files_present"],
            checks["phase_mapping_lock_ok"],
            checks["undefined_mapping_guard_configured"],
            checks["no_go_invariants_ok"],
        ]
    )

    status = "PASS" if baseline_locked else "FAIL"

    result: dict[str, Any] = {
        "phase": "SFB-15B",
        "phase_name": "Dashboard Operations Baseline Lock",
        "generated_at": _now_iso(),
        "status": status,
        "baseline_locked": baseline_locked,
        "hold_state": str(policy.get("hold_state", "HOLD")),
        "production_status": "NO_GO",
        "mode": "DRY_RUN",
        "wordpress_write_executed": False,
        "external_api_called": False,
        "external_network_called": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "human_approval_consumed": False,
        "checks": checks,
        "source_reports": {k: str(_resolve(v)) for k, v in required_json_reports.items()},
        "summary": {
            "locked_scope": "SFB-13T / SFB-14 / SFB-14B / SFB-14C / SFB-15",
            "hold_recommendation": "HOLD",
            "next_action": "KEEP_HOLD_AND_MONITOR" if baseline_locked else "STOP_AND_FIX",
        },
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(result, report_md)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="policy json path")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = ROOT / policy_path

    result = generate(policy_path=policy_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
