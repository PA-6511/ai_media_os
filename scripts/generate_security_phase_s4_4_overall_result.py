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


GATE_RESULT_PATH = ROOT / "exchange" / "logs" / "security_final_isolation_design_gate_phase_s4_4_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_4_overall_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_4_overall_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def generate_security_phase_s4_4_overall_result(
    gate_result_path: Path = GATE_RESULT_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    gate = _load_json(Path(gate_result_path))
    gate_result = str(gate.get("gate_result", ""))

    if gate_result == "ABORT":
        final_status = "ABORT"
    elif gate_result == "PASS" and gate.get("s4_completion_verified") is True and gate.get("isolation_design_ready") is True:
        final_status = "PASS_DESIGN_GATE_ONLY"
    else:
        final_status = "DESIGN_GATE_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S4_4",
        "phase_name": "final_isolation_design_gate",
        "phase_status": "DESIGN_ONLY",
        "gate_result": gate_result,
        "final_status": final_status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "final_gate_only": True,
        "s4_completion_verified": bool(gate.get("s4_completion_verified", False)),
        "required_evidence_count": int(gate.get("required_evidence_count", 0)),
        "found_evidence_count": int(gate.get("found_evidence_count", 0)),
        "missing_evidence_count": int(gate.get("missing_evidence_count", 0)),
        "isolation_design_ready": bool(gate.get("isolation_design_ready", False)),
        "future_execution_allowed": False,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "network_policy_applied": False,
        "firewall_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "executor_action_allowed": False,
        "next_step": "pause_before_execution_or_prepare_s5_design_only",
        "created_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Phase S-4.4 Overall Result",
        "",
        f"- gate_result: {result.get('gate_result')}",
        f"- final_status: {result.get('final_status')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- production_status: {result.get('production_status')}",
        f"- execution: {result.get('execution')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- final_gate_only: {result.get('final_gate_only')}",
        f"- s4_completion_verified: {result.get('s4_completion_verified')}",
        f"- required_evidence_count: {result.get('required_evidence_count')}",
        f"- found_evidence_count: {result.get('found_evidence_count')}",
        f"- missing_evidence_count: {result.get('missing_evidence_count')}",
        f"- isolation_design_ready: {result.get('isolation_design_ready')}",
        f"- future_execution_allowed: {result.get('future_execution_allowed')}",
        f"- isolation_execution_allowed: {result.get('isolation_execution_allowed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- network_policy_applied: {result.get('network_policy_applied')}",
        f"- firewall_applied: {result.get('firewall_applied')}",
        f"- container_stop_executed: {result.get('container_stop_executed')}",
        f"- process_kill_executed: {result.get('process_kill_executed')}",
        f"- scheduler_stop_executed: {result.get('scheduler_stop_executed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- external_api_call_executed: {result.get('external_api_call_executed')}",
        f"- state_change_executed: {result.get('state_change_executed')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- next_step: {result.get('next_step')}",
        f"- created_at: {result.get('created_at')}",
    ]
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_phase_s4_4_overall_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] == "PASS_DESIGN_GATE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
