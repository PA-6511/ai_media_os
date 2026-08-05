#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
POLICY_JSON = CONFIG_DIR / "pre_production_baseline_lock_policy.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_read_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _check_no_external_and_no_write(payload: Dict[str, Any]) -> bool:
    return (
        payload.get("external_api_called", False) is False
        and payload.get("external_network_called", False) is False
        and payload.get("wordpress_write_executed", False) is False
        and payload.get("publish_executed", False) is False
        and payload.get("update_executed", False) is False
        and payload.get("delete_executed", False) is False
        and payload.get("export_executed", False) is False
        and payload.get("creators_api_called", False) is False
        and payload.get("amazon_scraping_called", False) is False
    )


def generate_pre_production_baseline_lock_report(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)
    required_logs = policy.get("required_phase_logs", {})

    payloads: Dict[str, Dict[str, Any] | None] = {}
    phase_statuses: Dict[str, str] = {}
    missing: List[str] = []

    for key, rel in required_logs.items():
        p = BLOCK_DIR / str(rel)
        payload = _safe_read_json(p)
        payloads[key] = payload
        if payload is None:
            missing.append(key)
            phase_statuses[key] = "MISSING"
        else:
            phase_statuses[key] = str(payload.get("status", "FAIL"))

    phase_status_all_pass = all(v == "PASS" for v in phase_statuses.values())

    production_status_no_go = all(
        (p or {}).get("production_status") == "NO_GO"
        for p in payloads.values()
        if p is not None
    ) and len(missing) == 0

    no_external_and_no_write = all(
        _check_no_external_and_no_write(p)
        for p in payloads.values()
        if p is not None
    ) and len(missing) == 0

    final_human_gate_status = str((payloads.get("sfb6_wordpress_payload_validation") or {}).get("final_human_gate", {}).get("status", "NOT_AVAILABLE"))
    final_human_gate_ready = final_human_gate_status == str(policy.get("required_final_human_gate_status", "READY_FOR_FINAL_HUMAN_GATE"))

    execution_gate_status = str((payloads.get("sfb7_final_human_approval") or {}).get("wordpress_dry_run_execution_gate", "BLOCKED"))
    execution_gate_ready = execution_gate_status == str(policy.get("required_execution_gate", "READY_FOR_DRY_RUN_ONLY"))

    simulated_execution_count = int((payloads.get("sfb8_dry_run_evidence") or {}).get("simulated_execution_count", 0))
    simulated_execution_ready = simulated_execution_count >= int(policy.get("required_simulated_execution_count_min", 1))

    governance_ready = bool((payloads.get("sfb10_governance_boundary_review") or {}).get("governance_boundary_review_ready", False))

    approval_token_consumed = bool((payloads.get("sfb9_final_signoff_archive") or {}).get("approval_token_consumed", False))
    approval_label_consumed = bool((payloads.get("sfb9_final_signoff_archive") or {}).get("approval_label_consumed", False))
    human_approval_consumed = any(
        bool((p or {}).get("human_approval_consumed", False))
        for p in payloads.values()
        if p is not None
    )

    checks = {
        "required_reports_present": len(missing) == 0,
        "missing_reports": missing,
        "phase_status_all_pass": phase_status_all_pass,
        "phase_statuses": phase_statuses,
        "production_status_no_go": production_status_no_go,
        "no_external_communication": no_external_and_no_write,
        "final_human_gate_status": final_human_gate_status,
        "final_human_gate_ready": final_human_gate_ready,
        "wordpress_dry_run_execution_gate": execution_gate_status,
        "wordpress_dry_run_execution_gate_ready": execution_gate_ready,
        "simulated_execution_count": simulated_execution_count,
        "simulated_execution_count_ready": simulated_execution_ready,
        "governance_boundary_review_ready": governance_ready,
        "approval_token_consumed": approval_token_consumed,
        "approval_label_consumed": approval_label_consumed,
        "human_approval_consumed": human_approval_consumed,
        "wordpress_write_executed": False,
    }

    baseline_locked = all(
        [
            checks["required_reports_present"],
            checks["phase_status_all_pass"],
            checks["production_status_no_go"],
            checks["no_external_communication"],
            checks["final_human_gate_ready"],
            checks["wordpress_dry_run_execution_gate_ready"],
            checks["simulated_execution_count_ready"],
            checks["governance_boundary_review_ready"],
            checks["approval_token_consumed"] is False,
            checks["approval_label_consumed"] is False,
            checks["human_approval_consumed"] is False,
        ]
    )

    status = "PASS" if baseline_locked else "FAIL"

    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/sale_flash_block_v1_pre_production_baseline_lock_report.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/sale_flash_block_v1_pre_production_baseline_lock_report.md"))

    result: Dict[str, Any] = {
        "status": status,
        "phase": "SFB-10B",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": str(policy.get("block_name", "sale_flash_block")),
        "baseline_name": str(policy.get("baseline_name", "sale_flash_block_v1_pre_production_baseline_locked")),
        "baseline_locked": baseline_locked,
        "production_status": "NO_GO",
        "mode": str(policy.get("mode", "DRY_RUN")),
        "checks": checks,
        "summary": {
            "validated_range": "SFB-1 to SFB-10",
            "stop_point": "SFB complete to pre-production, boundary remains closed",
            "next_recommended_phase": "HOLD",
        },
        "source_reports": {k: str(BLOCK_DIR / str(v)) for k, v in required_logs.items()},
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# SFB v1 Pre-Production Baseline Lock Report",
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
        f"- phase_status_all_pass: {checks['phase_status_all_pass']}",
        f"- production_status_no_go: {checks['production_status_no_go']}",
        f"- no_external_communication: {checks['no_external_communication']}",
        f"- final_human_gate_status: {checks['final_human_gate_status']}",
        f"- final_human_gate_ready: {checks['final_human_gate_ready']}",
        f"- wordpress_dry_run_execution_gate: {checks['wordpress_dry_run_execution_gate']}",
        f"- wordpress_dry_run_execution_gate_ready: {checks['wordpress_dry_run_execution_gate_ready']}",
        f"- simulated_execution_count: {checks['simulated_execution_count']}",
        f"- simulated_execution_count_ready: {checks['simulated_execution_count_ready']}",
        f"- governance_boundary_review_ready: {checks['governance_boundary_review_ready']}",
        f"- approval_token_consumed: {checks['approval_token_consumed']}",
        f"- approval_label_consumed: {checks['approval_label_consumed']}",
        f"- human_approval_consumed: {checks['human_approval_consumed']}",
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
    payload = generate_pre_production_baseline_lock_report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
