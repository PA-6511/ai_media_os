#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
POLICY_JSON = CONFIG_DIR / "final_signoff_archive_policy.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_read(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def generate_final_signoff_archive(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)

    baseline_path = BLOCK_DIR / str(
        policy.get("input_dry_run_execution_baseline_lock", "logs/sale_flash_block_dry_run_execution_baseline_lock_report.json")
    )
    final_approval_path = BLOCK_DIR / str(
        policy.get("input_final_human_approval_package", "logs/final_human_approval_package.json")
    )
    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/final_signoff_archive.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/final_signoff_archive.md"))

    baseline = _safe_read(baseline_path)
    final_approval = _safe_read(final_approval_path)

    missing_inputs = []
    if baseline is None:
        missing_inputs.append("dry_run_execution_baseline_lock")
    if final_approval is None:
        missing_inputs.append("final_human_approval_package")

    baseline_locked = bool((baseline or {}).get("baseline_locked", False))
    final_human_gate_status = str((final_approval or {}).get("final_human_gate_status", "NOT_READY"))
    required_final_human_gate_status = str(policy.get("required_final_human_gate_status", "READY_FOR_FINAL_HUMAN_GATE"))
    final_human_gate_ready = final_human_gate_status == required_final_human_gate_status

    dry_run_execution_gate = str((final_approval or {}).get("wordpress_dry_run_execution_gate", "BLOCKED"))
    required_dry_run_execution_gate = str(policy.get("required_dry_run_execution_gate", "READY_FOR_DRY_RUN_ONLY"))
    dry_run_execution_gate_ready = dry_run_execution_gate == required_dry_run_execution_gate

    approval_token_consumed = False
    approval_label_consumed = False
    human_approval_consumed = (
        (final_approval or {}).get("human_approval_consumed", False) is True
    )

    production_write_blocked = True
    allow_production_write = False

    safe_no_write_state = (
        (final_approval or {}).get("production_status") == "NO_GO"
        and (final_approval or {}).get("wordpress_write_executed", False) is False
        and (final_approval or {}).get("external_api_called", False) is False
        and (final_approval or {}).get("external_network_called", False) is False
        and not human_approval_consumed
    )

    signoff_ready = (
        len(missing_inputs) == 0
        and baseline_locked
        and final_human_gate_ready
        and dry_run_execution_gate_ready
        and safe_no_write_state
        and approval_token_consumed is False
        and approval_label_consumed is False
    )

    signoff_statements = {
        "human_signoff_primary": "SFB-1..SFB-9 artifacts reviewed. DRY_RUN rehearsal is complete. Production WordPress write remains BLOCKED.",
        "human_signoff_secondary": "Approval token/label are intentionally NOT consumed in SFB-9.",
        "human_signoff_no_go_clause": "NO_GO is maintained until a separate production-governance phase approves write boundary change.",
    }

    status = "PASS" if signoff_ready else "FAIL"

    payload: Dict[str, Any] = {
        "status": status,
        "phase": "SFB-9",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": str(policy.get("block_name", "sale_flash_block")),
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "missing_inputs": missing_inputs,
        "baseline_locked": baseline_locked,
        "final_human_gate_status": final_human_gate_status,
        "required_final_human_gate_status": required_final_human_gate_status,
        "final_human_gate_ready": final_human_gate_ready,
        "wordpress_dry_run_execution_gate": dry_run_execution_gate,
        "required_dry_run_execution_gate": required_dry_run_execution_gate,
        "dry_run_execution_gate_ready": dry_run_execution_gate_ready,
        "approval_token_consumed": approval_token_consumed,
        "approval_label_consumed": approval_label_consumed,
        "human_approval_consumed": False,
        "production_write_blocked": production_write_blocked,
        "allow_production_write": allow_production_write,
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "publish_executed": False,
        "update_executed": False,
        "delete_executed": False,
        "export_executed": False,
        "signoff_ready": signoff_ready,
        "signoff_statements": signoff_statements,
        "approval_template": {
            "token_label": "UNCONSUMED",
            "approval_label": "UNCONSUMED",
            "operator": "",
            "ticket": "",
            "comment": "",
        },
        "decision": {
            "allow_wordpress_dry_run_execution": True,
            "allow_wordpress_production_write": False,
            "reason": "SFB-9 is sign-off wording design only; write boundary remains blocked",
        },
        "next_recommended_phase": "SFB-10: Governance-only production boundary review",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Final Sign-off Archive",
        "",
        "## Summary",
        f"- status: {payload['status']}",
        f"- phase: {payload['phase']}",
        f"- mode: {payload['mode']}",
        f"- production_status: {payload['production_status']}",
        f"- baseline_locked: {payload['baseline_locked']}",
        f"- signoff_ready: {payload['signoff_ready']}",
        f"- production_write_blocked: {payload['production_write_blocked']}",
        "",
        "## Gates",
        f"- final_human_gate_status: {payload['final_human_gate_status']}",
        f"- final_human_gate_ready: {payload['final_human_gate_ready']}",
        f"- wordpress_dry_run_execution_gate: {payload['wordpress_dry_run_execution_gate']}",
        f"- dry_run_execution_gate_ready: {payload['dry_run_execution_gate_ready']}",
        "",
        "## Approval Consumption",
        f"- approval_token_consumed: {payload['approval_token_consumed']}",
        f"- approval_label_consumed: {payload['approval_label_consumed']}",
        f"- human_approval_consumed: {payload['human_approval_consumed']}",
        "",
        "## Safety",
        f"- external_api_called: {payload['external_api_called']}",
        f"- external_network_called: {payload['external_network_called']}",
        f"- wordpress_write_executed: {payload['wordpress_write_executed']}",
        f"- publish_executed: {payload['publish_executed']}",
        f"- update_executed: {payload['update_executed']}",
        f"- delete_executed: {payload['delete_executed']}",
        f"- export_executed: {payload['export_executed']}",
        "",
        "## Sign-off Statements",
        f"- human_signoff_primary: {signoff_statements['human_signoff_primary']}",
        f"- human_signoff_secondary: {signoff_statements['human_signoff_secondary']}",
        f"- human_signoff_no_go_clause: {signoff_statements['human_signoff_no_go_clause']}",
        "",
        "## Decision",
        f"- allow_wordpress_dry_run_execution: {payload['decision']['allow_wordpress_dry_run_execution']}",
        f"- allow_wordpress_production_write: {payload['decision']['allow_wordpress_production_write']}",
        f"- reason: {payload['decision']['reason']}",
        "",
        "## Next",
        f"- next_recommended_phase: {payload['next_recommended_phase']}",
    ]

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = generate_final_signoff_archive()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
