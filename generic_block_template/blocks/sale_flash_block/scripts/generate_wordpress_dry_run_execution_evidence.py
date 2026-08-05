#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
POLICY_JSON = CONFIG_DIR / "wordpress_dry_run_execution_evidence_policy.json"


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


def _build_simulated_events(draft_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for i, item in enumerate(draft_candidates, start=1):
        wp = item.get("wordpress_draft_candidate", {})
        body = wp.get("post_body_candidate", {}) if isinstance(wp, dict) else {}
        link = body.get("link_candidate", {}) if isinstance(body, dict) else {}

        events.append(
            {
                "event_id": f"sfb8-sim-{i:03d}",
                "event_type": "wordpress_dry_run_simulation",
                "draft_handoff_id": item.get("draft_handoff_id", ""),
                "candidate_id": item.get("candidate_id", ""),
                "title": item.get("title", ""),
                "simulated_endpoint": "/wp-json/wp/v2/posts",
                "simulated_method": "POST",
                "simulated_request": {
                    "post_type": wp.get("post_type", "post"),
                    "post_status": "draft",
                    "title": wp.get("post_title", ""),
                    "slug": wp.get("post_slug_candidate", ""),
                    "excerpt": wp.get("post_excerpt", ""),
                    "link_candidate_url": link.get("url", ""),
                },
                "simulated_result": {
                    "http_status": 202,
                    "accepted": True,
                    "message": "simulated only; no outbound request",
                },
                "network_called": False,
                "wordpress_write_executed": False,
            }
        )
    return events


def generate_wordpress_dry_run_execution_evidence(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)

    final_package_path = BLOCK_DIR / str(policy.get("input_final_human_approval_package", "logs/final_human_approval_package.json"))
    draft_handoff_path = BLOCK_DIR / str(policy.get("input_wordpress_draft_handoff", "logs/wordpress_draft_handoff.json"))
    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/wordpress_dry_run_execution_evidence.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/wordpress_dry_run_execution_evidence.md"))

    final_package = _safe_read(final_package_path)
    draft_handoff = _safe_read(draft_handoff_path)

    missing_inputs = []
    if final_package is None:
        missing_inputs.append("final_human_approval_package")
    if draft_handoff is None:
        missing_inputs.append("wordpress_draft_handoff")

    gate_value = str((final_package or {}).get("wordpress_dry_run_execution_gate", "BLOCKED"))
    required_gate = str(policy.get("required_execution_gate", "READY_FOR_DRY_RUN_ONLY"))
    gate_ready = gate_value == required_gate

    draft_candidates = list((draft_handoff or {}).get("draft_candidates", []))
    events = _build_simulated_events(draft_candidates) if gate_ready and not missing_inputs else []

    result: Dict[str, Any] = {
        "status": "PASS" if gate_ready and len(missing_inputs) == 0 else "FAIL",
        "phase": "SFB-8",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": str(policy.get("block_name", "sale_flash_block")),
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "missing_inputs": missing_inputs,
        "wordpress_dry_run_execution_gate": gate_value,
        "required_execution_gate": required_gate,
        "gate_ready": gate_ready,
        "simulated_execution_count": len(events),
        "simulated_execution_events": events,
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "publish_executed": False,
        "update_executed": False,
        "delete_executed": False,
        "export_executed": False,
        "human_approval_consumed": False,
        "production_write_blocked": True,
        "execution_summary": {
            "candidate_count": len(draft_candidates),
            "simulated_success_count": len(events),
            "simulated_failure_count": 0 if events else len(draft_candidates) if gate_ready else 0,
            "note": "simulation only; no outbound request or WordPress write",
        },
        "next_recommended_phase": "SFB-9: Human sign-off archive (still NO_GO)",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# WordPress DRY_RUN Execution Evidence",
        "",
        "## Summary",
        f"- status: {result['status']}",
        f"- phase: {result['phase']}",
        f"- mode: {result['mode']}",
        f"- production_status: {result['production_status']}",
        f"- wordpress_dry_run_execution_gate: {result['wordpress_dry_run_execution_gate']}",
        f"- gate_ready: {result['gate_ready']}",
        f"- simulated_execution_count: {result['simulated_execution_count']}",
        "",
        "## Safety",
        f"- external_api_called: {result['external_api_called']}",
        f"- external_network_called: {result['external_network_called']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- update_executed: {result['update_executed']}",
        f"- delete_executed: {result['delete_executed']}",
        f"- export_executed: {result['export_executed']}",
        f"- human_approval_consumed: {result['human_approval_consumed']}",
        f"- production_write_blocked: {result['production_write_blocked']}",
        "",
        "## Simulated Events",
        "| event_id | draft_handoff_id | title | endpoint | accepted |",
        "| --- | --- | --- | --- | --- |",
    ]

    if events:
        for event in events:
            md_lines.append(
                "| "
                + f"{event.get('event_id', '')} | "
                + f"{event.get('draft_handoff_id', '')} | "
                + f"{event.get('title', '')} | "
                + f"{event.get('simulated_endpoint', '')} | "
                + f"{event.get('simulated_result', {}).get('accepted', False)} |"
            )
    else:
        md_lines.append("| - | - | - | - | False |")

    md_lines.extend(
        [
            "",
            "## Next",
            f"- next_recommended_phase: {result['next_recommended_phase']}",
        ]
    )

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    payload = generate_wordpress_dry_run_execution_evidence()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
