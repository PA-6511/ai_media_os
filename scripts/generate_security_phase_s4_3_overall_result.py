#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


AUDIT_RESULT_PATH = ROOT / "exchange" / "logs" / "security_isolation_audit_design_review_phase_s4_3_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_3_overall_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_3_overall_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def generate_security_phase_s4_3_overall_result(
    audit_result_path: Path = AUDIT_RESULT_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    audit = _load_json(Path(audit_result_path))
    audit_result = str(audit.get("audit_result", ""))

    if audit_result == "ABORT":
        final_status = "ABORT"
    elif (
        audit_result == "PASS"
        and int(audit.get("missing_evidence_count", 0)) == 0
        and int(audit.get("required_evidence_count", 0)) == int(audit.get("found_evidence_count", 0))
    ):
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "ISOLATION_AUDIT_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S4_3",
        "phase_name": "isolation_audit_design_review",
        "phase_status": "DESIGN_ONLY",
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "audit_view_only": True,
        "simulation_only": True,
        "recommendation_only": True,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "network_policy_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "firewall_applied": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "required_evidence_count": int(audit.get("required_evidence_count", 0)),
        "found_evidence_count": int(audit.get("found_evidence_count", 0)),
        "missing_evidence_count": int(audit.get("missing_evidence_count", 0)),
        "timestamp": _now_iso(),
        "next_step": "phase_s4_3_human_design_review_signoff_keep_no_go",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Phase S-4.3 Overall Result",
        "",
        f"- final_status: {result.get('final_status')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- audit_view_only: {result.get('audit_view_only')}",
        f"- simulation_only: {result.get('simulation_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- required_evidence_count: {result.get('required_evidence_count')}",
        f"- found_evidence_count: {result.get('found_evidence_count')}",
        f"- missing_evidence_count: {result.get('missing_evidence_count')}",
        f"- isolation_execution_allowed: {result.get('isolation_execution_allowed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- network_policy_applied: {result.get('network_policy_applied')}",
        f"- container_stop_executed: {result.get('container_stop_executed')}",
        f"- process_kill_executed: {result.get('process_kill_executed')}",
        f"- firewall_applied: {result.get('firewall_applied')}",
        f"- scheduler_stop_executed: {result.get('scheduler_stop_executed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- external_api_call_executed: {result.get('external_api_call_executed')}",
        f"- state_change_executed: {result.get('state_change_executed')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
    ]
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_phase_s4_3_overall_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] in {"PASS_DRY_RUN_ONLY", "ISOLATION_AUDIT_REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
