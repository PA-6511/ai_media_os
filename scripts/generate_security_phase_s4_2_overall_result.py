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


REPLAY_RESULT_PATH = ROOT / "exchange" / "logs" / "security_isolation_event_simulation_phase_s4_2_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_2_overall_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_2_overall_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def generate_security_phase_s4_2_overall_result(
    replay_result_path: Path = REPLAY_RESULT_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    replay = _load_json(Path(replay_result_path))

    replay_result = str(replay.get("replay_result", ""))
    scenario_count = int(replay.get("scenario_count", 0))
    matched_expected_count = int(replay.get("matched_expected_count", 0))
    mismatched_expected_count = int(replay.get("mismatched_expected_count", 0))

    terminal_state_ok = (
        replay.get("phase_status") == "DESIGN_ONLY"
        and replay.get("execution") == "DRY_RUN"
        and replay.get("production_status") == "NO_GO"
        and replay.get("simulation_status") == "SIMULATION_ONLY"
        and replay.get("recommendation_mode") == "RECOMMENDATION_ONLY"
        and replay.get("isolation_execution_policy") == "NO_ISOLATION_EXECUTION"
    )

    flags_ok = all(
        replay.get(key) is False
        for key in [
            "isolation_execution_allowed",
            "isolation_executed",
            "network_policy_applied",
            "container_stop_executed",
            "process_kill_executed",
            "firewall_applied",
            "scheduler_stop_executed",
            "wordpress_write_executed",
            "external_api_call_executed",
            "state_change_executed",
        ]
    )

    recommendation_ok = (
        replay.get("simulation_only") is True
        and replay.get("recommendation_only") is True
        and replay.get("isolation_recommendation_detected") is True
        and replay.get("freeze_recommendation_detected") is True
        and replay.get("human_review_recommendation_detected") is True
    )

    if replay_result == "ABORT":
        final_status = "ABORT"
    elif (
        scenario_count == 7
        and matched_expected_count == 7
        and mismatched_expected_count == 0
        and terminal_state_ok
        and flags_ok
        and recommendation_ok
    ):
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "ISOLATION_SIMULATION_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S4_2",
        "phase_name": "isolation_event_simulation",
        "phase_status": "DESIGN_ONLY",
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "simulation_status": "SIMULATION_ONLY",
        "recommendation_mode": "RECOMMENDATION_ONLY",
        "isolation_execution_policy": "NO_ISOLATION_EXECUTION",
        "simulation_only": True,
        "recommendation_only": True,
        "human_approval_required": True,
        "scenario_count": scenario_count,
        "matched_expected_count": matched_expected_count,
        "mismatched_expected_count": mismatched_expected_count,
        "isolation_recommendation_detected": bool(replay.get("isolation_recommendation_detected", False)),
        "freeze_recommendation_detected": bool(replay.get("freeze_recommendation_detected", False)),
        "human_review_recommendation_detected": bool(replay.get("human_review_recommendation_detected", False)),
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "executor_action_allowed": False,
        "freeze_execution_allowed": False,
        "freeze_executed": False,
        "network_policy_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "firewall_applied": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "timestamp": _now_iso(),
        "next_step": "phase_s4_3_isolation_audit_or_design_review",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Phase S-4.2 Overall Result",
        "",
        f"- final_status: {result.get('final_status')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- simulation_status: {result.get('simulation_status')}",
        f"- recommendation_mode: {result.get('recommendation_mode')}",
        f"- isolation_execution_policy: {result.get('isolation_execution_policy')}",
        f"- simulation_only: {result.get('simulation_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- scenario_count: {result.get('scenario_count')}",
        f"- matched_expected_count: {result.get('matched_expected_count')}",
        f"- mismatched_expected_count: {result.get('mismatched_expected_count')}",
        f"- isolation_recommendation_detected: {result.get('isolation_recommendation_detected')}",
        f"- freeze_recommendation_detected: {result.get('freeze_recommendation_detected')}",
        f"- human_review_recommendation_detected: {result.get('human_review_recommendation_detected')}",
        f"- isolation_execution_allowed: {result.get('isolation_execution_allowed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- freeze_execution_allowed: {result.get('freeze_execution_allowed')}",
        f"- freeze_executed: {result.get('freeze_executed')}",
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
    result = generate_security_phase_s4_2_overall_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] in {"PASS_DRY_RUN_ONLY", "ISOLATION_SIMULATION_REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
