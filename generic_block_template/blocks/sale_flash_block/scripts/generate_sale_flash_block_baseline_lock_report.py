#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
POLICY_JSON = CONFIG_DIR / "baseline_lock_policy.json"


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


def _phase_status_from_payload(payload: Dict[str, Any] | None) -> str:
    if payload is None:
        return "MISSING"
    return str(payload.get("status", "FAIL"))


def generate_baseline_lock_report(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)
    required_logs = policy.get("required_phase_logs", {})

    payloads: Dict[str, Dict[str, Any] | None] = {}
    missing_logs: List[str] = []
    phase_status_map: Dict[str, str] = {}

    for phase_key, rel_path in required_logs.items():
        target = BLOCK_DIR / str(rel_path)
        payload = _safe_read_json(target)
        payloads[phase_key] = payload
        if payload is None:
            missing_logs.append(phase_key)
        phase_status_map[phase_key] = _phase_status_from_payload(payload)

    final_gate_phase = "sfb6_wordpress_payload_validation"
    final_human_gate_status = "NOT_AVAILABLE"
    if payloads.get(final_gate_phase):
        final_human_gate_status = str(
            (payloads.get(final_gate_phase) or {}).get("final_human_gate", {}).get("status", "NOT_AVAILABLE")
        )

    phase_status_all_pass = all(status == "PASS" for status in phase_status_map.values())

    production_status_no_go = all(
        (payload or {}).get("production_status") == "NO_GO"
        for payload in payloads.values()
        if payload is not None
    ) and len(missing_logs) == 0

    no_external_and_no_write = all(
        _check_no_external_and_no_write(payload)
        for payload in payloads.values()
        if payload is not None
    ) and len(missing_logs) == 0

    human_approval_unconsumed = (
        (payloads.get("sfb4_human_handoff") or {}).get("human_approval_consumed", False) is False
        and (payloads.get("sfb6_wordpress_payload_validation") or {}).get("human_approval_consumed", False) is False
    )

    final_human_gate_ready = final_human_gate_status == str(policy.get("required_final_human_gate_status", "READY_FOR_FINAL_HUMAN_GATE"))

    checks = {
        "required_reports_present": len(missing_logs) == 0,
        "missing_reports": missing_logs,
        "phase_status_all_pass": phase_status_all_pass,
        "phase_statuses": phase_status_map,
        "production_status_no_go": production_status_no_go,
        "no_external_communication": no_external_and_no_write,
        "wordpress_write_executed": False,
        "human_approval_unconsumed": human_approval_unconsumed,
        "final_human_gate_status": final_human_gate_status,
        "final_human_gate_ready": final_human_gate_ready,
    }

    is_locked = all(
        [
            checks["required_reports_present"],
            checks["phase_status_all_pass"],
            checks["production_status_no_go"],
            checks["no_external_communication"],
            checks["human_approval_unconsumed"],
            checks["final_human_gate_ready"],
        ]
    )

    status = "PASS" if is_locked else "FAIL"

    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/sale_flash_block_baseline_lock_report.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/sale_flash_block_baseline_lock_report.md"))

    result: Dict[str, Any] = {
        "status": status,
        "phase": "SFB-6B",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": str(policy.get("block_name", "sale_flash_block")),
        "baseline_name": str(policy.get("baseline_name", "sale_flash_block_sfb1_sfb6_dry_run_no_go_locked")),
        "baseline_locked": is_locked,
        "production_status": "NO_GO",
        "mode": str(policy.get("mode", "DRY_RUN")),
        "checks": checks,
        "summary": {
            "validated_range": "SFB-1 to SFB-6",
            "next_recommended_phase": "SFB-7: Final human approval package (still NO_GO)",
            "final_human_gate_status": final_human_gate_status,
        },
        "source_reports": {
            key: str(BLOCK_DIR / str(path))
            for key, path in required_logs.items()
        },
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Sale Flash Block Baseline Lock Report",
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
        f"- human_approval_unconsumed: {checks['human_approval_unconsumed']}",
        f"- final_human_gate_status: {checks['final_human_gate_status']}",
        f"- final_human_gate_ready: {checks['final_human_gate_ready']}",
        "",
        "## Phase Statuses",
        "| phase_key | status |",
        "| --- | --- |",
    ]

    for phase_key, phase_status in phase_status_map.items():
        md_lines.append(f"| {phase_key} | {phase_status} |")

    md_lines.extend(
        [
            "",
            "## Summary",
            f"- validated_range: {result['summary']['validated_range']}",
            f"- final_human_gate_status: {result['summary']['final_human_gate_status']}",
            f"- next_recommended_phase: {result['summary']['next_recommended_phase']}",
        ]
    )

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    payload = generate_baseline_lock_report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
