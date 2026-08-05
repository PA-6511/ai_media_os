#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
POLICY_JSON = CONFIG_DIR / "governance_boundary_review_policy.json"


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


def generate_governance_boundary_review(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)

    signoff_path = BLOCK_DIR / str(policy.get("input_final_signoff_archive", "logs/final_signoff_archive.json"))
    baseline_path = BLOCK_DIR / str(
        policy.get("input_dry_run_execution_baseline_lock", "logs/sale_flash_block_dry_run_execution_baseline_lock_report.json")
    )
    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/governance_boundary_review.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/governance_boundary_review.md"))

    signoff = _safe_read(signoff_path)
    baseline = _safe_read(baseline_path)

    missing_inputs: List[str] = []
    if signoff is None:
        missing_inputs.append("final_signoff_archive")
    if baseline is None:
        missing_inputs.append("dry_run_execution_baseline_lock")

    signoff_ready = bool((signoff or {}).get("signoff_ready", False))
    baseline_locked = bool((baseline or {}).get("baseline_locked", False))

    production_write_boundary_inventory = {
        "wordpress_create_post": "BLOCKED",
        "wordpress_update_post": "BLOCKED",
        "wordpress_delete_post": "BLOCKED",
        "wordpress_publish_post": "BLOCKED",
        "external_api_calls": "BLOCKED",
        "external_network_calls": "BLOCKED",
    }

    approval_label_consumption_conditions = [
        "governance committee explicit approval",
        "separate production boundary change ticket approved",
        "rollback plan approved and tested",
        "dry-run evidence revalidated within current release window",
    ]

    wordpress_write_allow_conditions = [
        "production_status changed from NO_GO to GO by governance",
        "approval token is intentionally consumed in dedicated phase",
        "approval label is intentionally consumed in dedicated phase",
        "write audit logger enabled and validated",
    ]

    ng_conditions = [
        "approval token consumed unexpectedly",
        "approval label consumed unexpectedly",
        "human approval consumed unexpectedly",
        "wordpress_write_executed=true before governance release",
        "external_api_called=true or external_network_called=true",
    ]

    rollback_conditions = [
        "if any NG condition occurs, revert to NO_GO immediately",
        "invalidate active approvals and regenerate sign-off package",
        "re-run SFB-8 evidence and SFB-8B lock before any next action",
    ]

    execution_blocked = bool(policy.get("execution_blocked", True))
    policy_no_go = str(policy.get("production_status", "NO_GO")) == "NO_GO"

    governance_ready = (
        len(missing_inputs) == 0
        and signoff_ready
        and baseline_locked
        and execution_blocked
        and policy_no_go
    )

    status = "PASS" if governance_ready else "FAIL"

    payload: Dict[str, Any] = {
        "status": status,
        "phase": "SFB-10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": str(policy.get("block_name", "sale_flash_block")),
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "missing_inputs": missing_inputs,
        "signoff_ready": signoff_ready,
        "baseline_locked": baseline_locked,
        "execution_blocked": execution_blocked,
        "allow_wordpress_production_write": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "human_approval_consumed": False,
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "publish_executed": False,
        "update_executed": False,
        "delete_executed": False,
        "export_executed": False,
        "production_write_boundary_inventory": production_write_boundary_inventory,
        "approval_label_consumption_conditions": approval_label_consumption_conditions,
        "wordpress_write_allow_conditions": wordpress_write_allow_conditions,
        "ng_conditions": ng_conditions,
        "rollback_conditions": rollback_conditions,
        "governance_boundary_review_ready": governance_ready,
        "next_recommended_phase": "STOP_POINT: SFB complete to pre-production, boundary remains closed",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Governance Boundary Review",
        "",
        "## Summary",
        f"- status: {payload['status']}",
        f"- phase: {payload['phase']}",
        f"- mode: {payload['mode']}",
        f"- production_status: {payload['production_status']}",
        f"- governance_boundary_review_ready: {payload['governance_boundary_review_ready']}",
        f"- execution_blocked: {payload['execution_blocked']}",
        f"- allow_wordpress_production_write: {payload['allow_wordpress_production_write']}",
        "",
        "## Boundary Inventory",
    ]

    for k, v in production_write_boundary_inventory.items():
        md_lines.append(f"- {k}: {v}")

    md_lines.extend(
        [
            "",
            "## Approval Label Consumption Conditions",
        ]
    )
    for item in approval_label_consumption_conditions:
        md_lines.append(f"- {item}")

    md_lines.extend(
        [
            "",
            "## WordPress Write Allow Conditions",
        ]
    )
    for item in wordpress_write_allow_conditions:
        md_lines.append(f"- {item}")

    md_lines.extend(
        [
            "",
            "## NG Conditions",
        ]
    )
    for item in ng_conditions:
        md_lines.append(f"- {item}")

    md_lines.extend(
        [
            "",
            "## Rollback Conditions",
        ]
    )
    for item in rollback_conditions:
        md_lines.append(f"- {item}")

    md_lines.extend(
        [
            "",
            "## Safety",
            f"- approval_token_consumed: {payload['approval_token_consumed']}",
            f"- approval_label_consumed: {payload['approval_label_consumed']}",
            f"- human_approval_consumed: {payload['human_approval_consumed']}",
            f"- external_api_called: {payload['external_api_called']}",
            f"- external_network_called: {payload['external_network_called']}",
            f"- wordpress_write_executed: {payload['wordpress_write_executed']}",
            "",
            "## Next",
            f"- next_recommended_phase: {payload['next_recommended_phase']}",
        ]
    )

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = generate_governance_boundary_review()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
