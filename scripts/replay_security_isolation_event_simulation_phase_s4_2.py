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


CONFIG_PATH = ROOT / "config" / "security_isolation_event_simulation_phase_s4_2.json"
S4_1_OVERALL_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_isolation_event_simulation_phase_s4_2_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_isolation_event_simulation_phase_s4_2_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def _evaluate_simulation_event(event: str) -> tuple[str, bool, bool, bool, list[str]]:
    reasons: list[str] = []

    if event == "unknown_block_ai_requests_production_core_connection":
        reasons.append("unknown_block_to_production_core_default_deny")
        return "BLOCK_ROUTE", True, True, True, reasons

    if event == "restricted_or_adult_risky_ai_requests_production_core_connection":
        reasons.append("restricted_or_adult_risky_route_blocked")
        return "BLOCK_ROUTE", True, True, True, reasons

    if event == "experimental_block_ai_requests_wordpress_write":
        reasons.append("experimental_wordpress_write_denied")
        return "DENY_CAPABILITY", True, True, True, reasons

    if event == "self_builder_ai_requests_code_modify":
        reasons.append("self_builder_code_modify_denied")
        return "DENY_CAPABILITY", True, True, True, reasons

    if event == "ebook_affiliate_block_ai_emits_publish_intent":
        reasons.append("ebook_affiliate_publish_intent_denied")
        return "DENY_CAPABILITY", True, True, True, reasons

    if event == "duplicate_runner_and_unknown_external_api_intent_detected_together":
        reasons.append("duplicate_runner_detected")
        reasons.append("unknown_external_api_intent_detected")
        return "FREEZE_RECOMMEND", True, True, True, reasons

    if event == "secret_echo_intent_and_reconnect_request_detected_together":
        reasons.append("secret_echo_intent_detected")
        reasons.append("unsafe_reconnect_request_detected")
        return "FREEZE_RECOMMEND", True, True, True, reasons

    reasons.append("unmapped_simulation_event")
    return "FREEZE_RECOMMEND", True, True, True, reasons


def replay_security_isolation_event_simulation_phase_s4_2(
    config_path: Path = CONFIG_PATH,
    s4_1_overall_path: Path = S4_1_OVERALL_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    config = _load_json(Path(config_path))
    s4_1_overall = _load_json(Path(s4_1_overall_path))

    abort_reasons: list[str] = []
    fail_reasons: list[str] = []
    warnings: list[str] = []

    if config.get("phase_status") != "DESIGN_ONLY":
        fail_reasons.append("config.phase_status must be DESIGN_ONLY")
    if config.get("execution") != "DRY_RUN":
        abort_reasons.append("config.execution must be DRY_RUN")
    if config.get("production_status") != "NO_GO":
        abort_reasons.append("config.production_status must be NO_GO")
    if config.get("simulation_status") != "SIMULATION_ONLY":
        fail_reasons.append("config.simulation_status must be SIMULATION_ONLY")
    if config.get("recommendation_mode") != "RECOMMENDATION_ONLY":
        fail_reasons.append("config.recommendation_mode must be RECOMMENDATION_ONLY")
    if config.get("isolation_execution_policy") != "NO_ISOLATION_EXECUTION":
        fail_reasons.append("config.isolation_execution_policy must be NO_ISOLATION_EXECUTION")

    for key in [
        "isolation_execution_allowed",
        "isolation_executed",
        "executor_action_allowed",
        "freeze_execution_allowed",
        "freeze_executed",
    ]:
        if config.get(key) is not False:
            abort_reasons.append(f"config.{key} must be false")

    if s4_1_overall.get("final_status") != "PASS_DRY_RUN_ONLY":
        fail_reasons.append("S-4.1 overall final_status must be PASS_DRY_RUN_ONLY")
    if s4_1_overall.get("execution") != "DRY_RUN":
        fail_reasons.append("S-4.1 overall execution must be DRY_RUN")
    if s4_1_overall.get("production_status") != "NO_GO":
        fail_reasons.append("S-4.1 overall production_status must be NO_GO")

    actions = config.get("actions", {})
    for key in [
        "auto_isolation_execute",
        "auto_freeze_execute",
        "network_policy_apply",
        "container_stop_execute",
        "process_kill_execute",
        "firewall_apply",
        "scheduler_stop_execute",
        "wordpress_write_execute",
        "external_api_call_execute",
        "state_change_execute",
    ]:
        if actions.get(key) is True:
            abort_reasons.append(f"config.actions.{key} must be false")

    simulation_scenarios = config.get("simulation_scenarios", [])
    if not isinstance(simulation_scenarios, list):
        raise ValueError("simulation_scenarios must be list")

    scenario_results: list[dict[str, Any]] = []
    matched_expected_count = 0
    mismatched_expected_count = 0
    isolation_recommendation_detected = False
    freeze_recommendation_detected = False
    human_review_recommendation_detected = False

    for scenario in simulation_scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("scenario must be object")
        scenario_id = str(scenario.get("id", "unknown_scenario"))
        event = str(scenario.get("event", ""))
        expected = scenario.get("expected", {})
        if not isinstance(expected, dict):
            raise ValueError("scenario expected must be object")

        (
            actual_decision,
            actual_isolation_recommendation,
            actual_freeze_recommendation,
            actual_human_review_recommendation,
            reasons,
        ) = _evaluate_simulation_event(event)

        scenario_match = True
        if actual_decision != str(expected.get("decision", "")):
            scenario_match = False
        if actual_isolation_recommendation is not bool(expected.get("isolation_recommendation", False)):
            scenario_match = False
        if actual_freeze_recommendation is not bool(expected.get("freeze_recommendation", False)):
            scenario_match = False
        if actual_human_review_recommendation is not bool(expected.get("human_review_recommendation", False)):
            scenario_match = False

        execution_flags_all_false = all(
            item is False
            for item in [
                config.get("isolation_execution_allowed"),
                config.get("isolation_executed"),
                config.get("executor_action_allowed"),
                config.get("freeze_execution_allowed"),
                config.get("freeze_executed"),
                actions.get("network_policy_apply"),
                actions.get("container_stop_execute"),
                actions.get("process_kill_execute"),
                actions.get("firewall_apply"),
                actions.get("scheduler_stop_execute"),
                actions.get("wordpress_write_execute"),
                actions.get("external_api_call_execute"),
                actions.get("state_change_execute"),
            ]
        )
        if execution_flags_all_false is not bool(expected.get("execution_flags_all_false", False)):
            scenario_match = False

        if scenario_match:
            matched_expected_count += 1
        else:
            mismatched_expected_count += 1

        isolation_recommendation_detected = isolation_recommendation_detected or actual_isolation_recommendation
        freeze_recommendation_detected = freeze_recommendation_detected or actual_freeze_recommendation
        human_review_recommendation_detected = human_review_recommendation_detected or actual_human_review_recommendation

        scenario_results.append(
            {
                "scenario_id": scenario_id,
                "event": event,
                "expected_decision": expected.get("decision"),
                "actual_decision": actual_decision,
                "isolation_recommendation": actual_isolation_recommendation,
                "freeze_recommendation": actual_freeze_recommendation,
                "human_review_recommendation": actual_human_review_recommendation,
                "execution_flags_all_false": execution_flags_all_false,
                "expected_matched": scenario_match,
                "reasons": reasons,
            }
        )

    scenario_count = len(simulation_scenarios)
    expected_scenario_count = int(config.get("validation_targets", {}).get("scenario_count", 0))
    if scenario_count <= 0:
        fail_reasons.append("simulation_scenarios must not be empty")
    if expected_scenario_count > 0 and scenario_count != expected_scenario_count:
        fail_reasons.append("scenario_count mismatch against validation target")

    if mismatched_expected_count > 0:
        fail_reasons.append("expected scenario result mismatch detected")

    if abort_reasons:
        replay_result = "ABORT"
    elif fail_reasons:
        replay_result = "FAIL"
    elif warnings:
        replay_result = "WARN"
    else:
        replay_result = "PASS"

    result = {
        "phase_id": "PHASE_S4_2",
        "phase_name": "isolation_event_simulation",
        "phase_status": "DESIGN_ONLY",
        "replay_result": replay_result,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "simulation_status": "SIMULATION_ONLY",
        "recommendation_mode": "RECOMMENDATION_ONLY",
        "isolation_execution_policy": "NO_ISOLATION_EXECUTION",
        "simulation_only": True,
        "recommendation_only": True,
        "human_approval_required": True,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "executor_action_allowed": False,
        "freeze_execution_allowed": False,
        "freeze_executed": False,
        "scenario_count": scenario_count,
        "matched_expected_count": matched_expected_count,
        "mismatched_expected_count": mismatched_expected_count,
        "scenario_results": scenario_results,
        "isolation_recommendation_detected": isolation_recommendation_detected,
        "freeze_recommendation_detected": freeze_recommendation_detected,
        "human_review_recommendation_detected": human_review_recommendation_detected,
        "s4_1_verified": s4_1_overall.get("final_status") == "PASS_DRY_RUN_ONLY",
        "network_policy_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "firewall_applied": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "timestamp": _now_iso(),
        "next_step": "phase_s4_3_isolation_audit_or_design_review",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Isolation Event Simulation Phase S-4.2 Result",
        "",
        f"- replay_result: {result.get('replay_result')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- simulation_status: {result.get('simulation_status')}",
        f"- recommendation_mode: {result.get('recommendation_mode')}",
        f"- isolation_execution_policy: {result.get('isolation_execution_policy')}",
        f"- scenario_count: {result.get('scenario_count')}",
        f"- matched_expected_count: {result.get('matched_expected_count')}",
        f"- mismatched_expected_count: {result.get('mismatched_expected_count')}",
        f"- simulation_only: {result.get('simulation_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- isolation_recommendation_detected: {result.get('isolation_recommendation_detected')}",
        f"- freeze_recommendation_detected: {result.get('freeze_recommendation_detected')}",
        f"- human_review_recommendation_detected: {result.get('human_review_recommendation_detected')}",
        f"- s4_1_verified: {result.get('s4_1_verified')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## scenario_results",
    ]
    for row in scenario_results:
        lines.append(
            f"- {row.get('scenario_id')}: actual={row.get('actual_decision')} expected={row.get('expected_decision')} isolation_recommendation={row.get('isolation_recommendation')} freeze_recommendation={row.get('freeze_recommendation')} human_review_recommendation={row.get('human_review_recommendation')} matched={row.get('expected_matched')}"
        )
    lines.extend(["", "## warnings"])
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    lines.extend(["", "## fail_reasons"])
    lines.extend([f"- {item}" for item in fail_reasons] or ["- none"])
    lines.extend(["", "## abort_reasons"])
    lines.extend([f"- {item}" for item in abort_reasons] or ["- none"])
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = replay_security_isolation_event_simulation_phase_s4_2()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["replay_result"] in {"PASS", "WARN", "FAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
