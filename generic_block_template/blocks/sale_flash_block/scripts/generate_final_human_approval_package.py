#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
POLICY_JSON = CONFIG_DIR / "final_human_approval_package_policy.json"


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


def generate_final_human_approval_package(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)

    baseline_path = BLOCK_DIR / str(policy.get("input_baseline_lock_log", "logs/sale_flash_block_baseline_lock_report.json"))
    validation_path = BLOCK_DIR / str(policy.get("input_payload_validation_log", "logs/wordpress_draft_payload_validation.json"))
    handoff_path = BLOCK_DIR / str(policy.get("input_wordpress_draft_handoff_log", "logs/wordpress_draft_handoff.json"))

    baseline = _safe_read(baseline_path)
    validation = _safe_read(validation_path)
    handoff = _safe_read(handoff_path)

    missing_inputs = []
    if baseline is None:
        missing_inputs.append("baseline_lock")
    if validation is None:
        missing_inputs.append("payload_validation")
    if handoff is None:
        missing_inputs.append("wordpress_draft_handoff")

    baseline_locked = bool((baseline or {}).get("baseline_locked", False))
    final_gate_status = str((validation or {}).get("final_human_gate", {}).get("status", "NOT_READY"))
    required_final_gate_status = str(policy.get("required_final_human_gate_status", "READY_FOR_FINAL_HUMAN_GATE"))
    final_gate_ready = final_gate_status == required_final_gate_status

    human_approval_unconsumed = (
        (validation or {}).get("human_approval_consumed", False) is False
        and (handoff or {}).get("human_approval_consumed", False) is False
    )

    no_external_or_write = (
        (validation or {}).get("external_api_called", False) is False
        and (validation or {}).get("external_network_called", False) is False
        and (validation or {}).get("wordpress_write_executed", False) is False
        and (validation or {}).get("publish_executed", False) is False
        and (validation or {}).get("update_executed", False) is False
        and (validation or {}).get("delete_executed", False) is False
        and (validation or {}).get("export_executed", False) is False
    )

    production_write_blocked = True
    wordpress_dry_run_execution_gate = (
        "READY_FOR_DRY_RUN_ONLY"
        if (len(missing_inputs) == 0 and baseline_locked and final_gate_ready and human_approval_unconsumed and no_external_or_write)
        else "BLOCKED"
    )

    status = "PASS" if wordpress_dry_run_execution_gate == "READY_FOR_DRY_RUN_ONLY" else "FAIL"

    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/final_human_approval_package.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/final_human_approval_package.md"))

    approval_template = dict(policy.get("approval_template", {}))
    approval_form = {
        "approved_by": "",
        "approved_at_utc": "",
        "approval_ticket": "",
        "approval_comment": "",
        "approved": False,
    }

    payload: Dict[str, Any] = {
        "status": status,
        "phase": "SFB-7",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": str(policy.get("block_name", "sale_flash_block")),
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "missing_inputs": missing_inputs,
        "baseline_locked": baseline_locked,
        "final_human_gate_status": final_gate_status,
        "required_final_human_gate_status": required_final_gate_status,
        "final_human_gate_ready": final_gate_ready,
        "human_approval_consumed": False,
        "human_approval_unconsumed": human_approval_unconsumed,
        "wordpress_dry_run_execution_gate": wordpress_dry_run_execution_gate,
        "production_write_blocked": production_write_blocked,
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "publish_executed": False,
        "update_executed": False,
        "delete_executed": False,
        "export_executed": False,
        "approval_template": approval_template,
        "approval_form": approval_form,
        "handoff_summary": {
            "draft_payload_count": int((handoff or {}).get("draft_payload_count", 0)),
            "validated_item_count": int((validation or {}).get("validated_item_count", 0)),
            "valid_item_count": int((validation or {}).get("valid_item_count", 0)),
            "needs_fix_item_count": int((validation or {}).get("needs_fix_item_count", 0)),
        },
        "decision": {
            "allow_wordpress_dry_run_execution": wordpress_dry_run_execution_gate == "READY_FOR_DRY_RUN_ONLY",
            "allow_production_wordpress_write": False,
            "reason": "NO_GO is enforced; production write is blocked by policy",
        },
        "next_recommended_phase": "SFB-8: Optional WordPress DRY_RUN execution evidence (still NO_GO)",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Final Human Approval Package",
        "",
        "## Summary",
        f"- status: {payload['status']}",
        f"- phase: {payload['phase']}",
        f"- mode: {payload['mode']}",
        f"- production_status: {payload['production_status']}",
        f"- baseline_locked: {payload['baseline_locked']}",
        f"- final_human_gate_status: {payload['final_human_gate_status']}",
        f"- wordpress_dry_run_execution_gate: {payload['wordpress_dry_run_execution_gate']}",
        f"- production_write_blocked: {payload['production_write_blocked']}",
        "",
        "## Safety",
        f"- external_api_called: {payload['external_api_called']}",
        f"- external_network_called: {payload['external_network_called']}",
        f"- wordpress_write_executed: {payload['wordpress_write_executed']}",
        f"- publish_executed: {payload['publish_executed']}",
        f"- update_executed: {payload['update_executed']}",
        f"- delete_executed: {payload['delete_executed']}",
        f"- export_executed: {payload['export_executed']}",
        f"- human_approval_consumed: {payload['human_approval_consumed']}",
        "",
        "## Approval Template",
        f"- title: {approval_template.get('title', '')}",
        f"- required_statement: {approval_template.get('required_statement', '')}",
        f"- forbidden_statement: {approval_template.get('forbidden_statement', '')}",
        "",
        "## Approval Form",
        "- approved_by:",
        "- approved_at_utc:",
        "- approval_ticket:",
        "- approval_comment:",
        "- approved: false",
        "",
        "## Handoff Summary",
        f"- draft_payload_count: {payload['handoff_summary']['draft_payload_count']}",
        f"- validated_item_count: {payload['handoff_summary']['validated_item_count']}",
        f"- valid_item_count: {payload['handoff_summary']['valid_item_count']}",
        f"- needs_fix_item_count: {payload['handoff_summary']['needs_fix_item_count']}",
        "",
        "## Decision",
        f"- allow_wordpress_dry_run_execution: {payload['decision']['allow_wordpress_dry_run_execution']}",
        f"- allow_production_wordpress_write: {payload['decision']['allow_production_wordpress_write']}",
        f"- reason: {payload['decision']['reason']}",
        "",
        "## Next",
        f"- next_recommended_phase: {payload['next_recommended_phase']}",
    ]

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = generate_final_human_approval_package()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
