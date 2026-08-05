#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REPLAY_RESULT_PATH = ROOT / "exchange" / "logs" / "security_isolation_policy_dry_run_phase_s4_1_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.md"


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def generate_security_phase_s4_1_overall_result(
    replay_result_path: Path = REPLAY_RESULT_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict:
    replay = _load_json(Path(replay_result_path))
    replay_result = replay.get("replay_result")
    mismatched = int(replay.get("mismatched_expected_count", 0))
    request_count = int(replay.get("request_count", 0))

    if replay_result == "ABORT":
        final_status = "ABORT"
    elif mismatched > 0 or request_count <= 0:
        final_status = "ISOLATION_POLICY_REVIEW_REQUIRED"
    else:
        final_status = "PASS_DRY_RUN_ONLY"

    result = {
        "phase_id": "PHASE_S4_1",
        "phase_name": "isolation_policy_dry_run_validation",
        "phase_status": "DESIGN_ONLY",
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "isolation_recommendation_only": True,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "executor_action_allowed": False,
        "request_count": request_count,
        "matched_expected_count": int(replay.get("matched_expected_count", 0)),
        "mismatched_expected_count": mismatched,
        "isolation_recommendation_detected": bool(replay.get("isolation_recommendation_detected", False)),
        "human_review_recommendation_detected": bool(replay.get("human_review_recommendation_detected", False)),
        "s4_design_verified": bool(replay.get("s4_design_verified", False)),
        "network_policy_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "firewall_applied": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "next_step": "phase_s4_2_isolation_event_simulation",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Security Phase S-4.1 Overall Result",
        "",
        f"- final_status: {result.get('final_status')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- isolation_recommendation_only: {result.get('isolation_recommendation_only')}",
        f"- isolation_execution_allowed: {result.get('isolation_execution_allowed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- request_count: {result.get('request_count')}",
        f"- matched_expected_count: {result.get('matched_expected_count')}",
        f"- mismatched_expected_count: {result.get('mismatched_expected_count')}",
        f"- isolation_recommendation_detected: {result.get('isolation_recommendation_detected')}",
        f"- human_review_recommendation_detected: {result.get('human_review_recommendation_detected')}",
        f"- s4_design_verified: {result.get('s4_design_verified')}",
        f"- next_step: {result.get('next_step')}",
    ]
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_phase_s4_1_overall_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] in {"PASS_DRY_RUN_ONLY", "ISOLATION_POLICY_REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
