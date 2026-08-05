#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
POLICY_JSON = CONFIG_DIR / "real_data_import_dry_run_baseline_lock_policy.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_read_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def generate_real_data_import_dry_run_baseline_lock_report(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)
    required_logs = dict(policy.get("required_phase_logs", {}))

    payloads: Dict[str, Dict[str, Any] | None] = {}
    missing_logs: List[str] = []
    phase_statuses: Dict[str, str] = {}

    for phase_key, rel_path in required_logs.items():
        target = BLOCK_DIR / str(rel_path)
        payload = _safe_read_json(target)
        payloads[phase_key] = payload
        if payload is None:
            missing_logs.append(phase_key)
            phase_statuses[phase_key] = "MISSING"
        else:
            phase_statuses[phase_key] = str(payload.get("status", "FAIL"))

    import_payload = payloads.get("sfb11_real_data_import") or {}
    evidence_payload = payloads.get("sfb11b_real_data_evidence") or {}
    sfb10b_payload = payloads.get("sfb10b_pre_production_baseline_lock") or {}

    required_import_status = set(policy.get("required_import_status", ["PASS"]))
    required_evidence_status = set(policy.get("required_evidence_status", ["PASS"]))

    import_status_ok = str(import_payload.get("status", "FAIL")) in required_import_status
    evidence_status_ok = str(evidence_payload.get("status", "FAIL")) in required_evidence_status
    sfb10b_locked = bool(sfb10b_payload.get("baseline_locked", False))

    no_go_maintained = (
        evidence_payload.get("no_go_maintained") is True
        and evidence_payload.get("production_status") == "NO_GO"
        and (evidence_payload.get("pipeline_dry_run") or {}).get("production_status") == "NO_GO"
        and (evidence_payload.get("pipeline_dry_run") or {}).get("wordpress_write_executed") is False
        and (evidence_payload.get("pipeline_dry_run") or {}).get("external_api_called") is False
        and (evidence_payload.get("pipeline_dry_run") or {}).get("external_network_called") is False
    )

    require_fixture_changed = bool(policy.get("require_fixture_changed", True))
    fixture_changed = bool((evidence_payload.get("fixture_diff") or {}).get("changed", False))
    fixture_changed_ok = fixture_changed if require_fixture_changed else True

    checks = {
        "required_reports_present": len(missing_logs) == 0,
        "missing_reports": missing_logs,
        "phase_statuses": phase_statuses,
        "import_status_ok": import_status_ok,
        "evidence_status_ok": evidence_status_ok,
        "sfb10b_baseline_locked": sfb10b_locked,
        "no_go_maintained": no_go_maintained,
        "fixture_changed": fixture_changed,
        "fixture_changed_ok": fixture_changed_ok,
        "wordpress_write_executed": False,
    }

    baseline_locked = all(
        [
            checks["required_reports_present"],
            checks["import_status_ok"],
            checks["evidence_status_ok"],
            checks["sfb10b_baseline_locked"],
            checks["no_go_maintained"],
            checks["fixture_changed_ok"],
        ]
    )

    status = "PASS" if baseline_locked else "FAIL"

    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/real_data_import_dry_run_baseline_lock_report.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/real_data_import_dry_run_baseline_lock_report.md"))

    result: Dict[str, Any] = {
        "status": status,
        "phase": "SFB-11C",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": str(policy.get("block_name", "sale_flash_block")),
        "baseline_name": str(policy.get("baseline_name", "sale_flash_block_real_data_import_dry_run_locked")),
        "baseline_locked": baseline_locked,
        "production_status": "NO_GO",
        "mode": str(policy.get("mode", "DRY_RUN")),
        "checks": checks,
        "summary": {
            "validated_range": "SFB-11 to SFB-11B with SFB-1 to SFB-10B evidence chain",
            "stop_point": "real-data DRY_RUN locked, production write boundary remains closed",
            "next_recommended_phase": "HOLD",
        },
        "source_reports": {k: str(BLOCK_DIR / str(v)) for k, v in required_logs.items()},
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Real-Data Import DRY_RUN Baseline Lock Report",
        "",
        f"- status: {result['status']}",
        f"- phase: {result['phase']}",
        f"- generated_at: {result['generated_at']}",
        f"- block_name: {result['block_name']}",
        f"- baseline_name: {result['baseline_name']}",
        f"- baseline_locked: {result['baseline_locked']}",
        f"- production_status: {result['production_status']}",
        f"- mode: {result['mode']}",
        "",
        "## Checks",
        f"- required_reports_present: {checks['required_reports_present']}",
        f"- missing_reports: {', '.join(checks['missing_reports']) or 'none'}",
        f"- import_status_ok: {checks['import_status_ok']}",
        f"- evidence_status_ok: {checks['evidence_status_ok']}",
        f"- sfb10b_baseline_locked: {checks['sfb10b_baseline_locked']}",
        f"- no_go_maintained: {checks['no_go_maintained']}",
        f"- fixture_changed: {checks['fixture_changed']}",
        f"- fixture_changed_ok: {checks['fixture_changed_ok']}",
        "",
        "## Phase Statuses",
        "| phase_key | status |",
        "| --- | --- |",
    ]

    for phase_key, phase_status in phase_statuses.items():
        md_lines.append(f"| {phase_key} | {phase_status} |")

    md_lines.extend(
        [
            "",
            "## Summary",
            f"- validated_range: {result['summary']['validated_range']}",
            f"- stop_point: {result['summary']['stop_point']}",
            f"- next_recommended_phase: {result['summary']['next_recommended_phase']}",
        ]
    )

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    payload = generate_real_data_import_dry_run_baseline_lock_report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
