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


POLICY_PATH = ROOT / "config" / "security_block_ai_isolation_policy_phase_s4.json"
RISK_CLASSIFICATION_PATH = ROOT / "config" / "security_block_ai_risk_classification_phase_s4.json"
COMMUNICATION_MATRIX_PATH = ROOT / "config" / "security_inter_block_communication_matrix_phase_s4.json"
CAPABILITY_BOUNDARY_PATH = ROOT / "config" / "security_capability_boundary_policy_phase_s4.json"
RECOMMENDATION_RULES_PATH = ROOT / "config" / "security_isolation_recommendation_rules_phase_s4.json"
RECONNECT_CONDITIONS_PATH = ROOT / "config" / "security_isolation_reconnect_conditions_phase_s4.json"
S3_2_AUDIT_PATH = ROOT / "exchange" / "logs" / "security_cross_phase_audit_view_phase_s3_2_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_block_ai_isolation_design_phase_s4_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_block_ai_isolation_design_phase_s4_validation_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    return data


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _ensure_boolean_false(data: dict[str, Any], key: str, fail_reasons: list[str], abort_reasons: list[str]) -> None:
    value = data.get(key)
    if value is True:
        abort_reasons.append(f"{key} must be false")
    elif value is not False:
        fail_reasons.append(f"{key} must be false")


def _ensure_exact(data: dict[str, Any], key: str, expected: Any, fail_reasons: list[str], abort_reasons: list[str]) -> None:
    value = data.get(key)
    if value == expected:
        return
    if key in {
        "execution",
        "production_status",
        "phase_status",
    } and value in {"LIVE", "GO", "ENABLED", "ALLOW"}:
        abort_reasons.append(f"{key} must be {expected!r}")
        return
    if key in {
        "isolation_execution_allowed",
        "isolation_executed",
        "network_policy_apply_allowed",
        "network_policy_applied",
        "container_stop_allowed",
        "container_stop_executed",
        "process_kill_allowed",
        "process_kill_executed",
        "firewall_apply_allowed",
        "firewall_applied",
        "scheduler_stop_allowed",
        "scheduler_stop_executed",
        "wordpress_write_allowed",
        "wordpress_write_executed",
        "external_api_call_allowed",
        "external_api_call_executed",
        "state_change_executed",
    } and value is True:
        abort_reasons.append(f"{key} must be {expected!r}")
        return
    fail_reasons.append(f"{key} must be {expected!r}")


def _sequence_contains_exact(items: Any, required: list[str]) -> bool:
    return isinstance(items, list) and all(item in items for item in required)


def _route_map(routes: Any) -> dict[tuple[str, str], dict[str, Any]]:
    mapping: dict[tuple[str, str], dict[str, Any]] = {}
    if isinstance(routes, list):
        for route in routes:
            if isinstance(route, dict):
                mapping[(str(route.get("from")), str(route.get("to")))] = route
    return mapping


def validate_security_block_ai_isolation_design_phase_s4(
    policy_path: Path = POLICY_PATH,
    risk_classification_path: Path = RISK_CLASSIFICATION_PATH,
    communication_matrix_path: Path = COMMUNICATION_MATRIX_PATH,
    capability_boundary_path: Path = CAPABILITY_BOUNDARY_PATH,
    recommendation_rules_path: Path = RECOMMENDATION_RULES_PATH,
    reconnect_conditions_path: Path = RECONNECT_CONDITIONS_PATH,
    s3_2_audit_path: Path = S3_2_AUDIT_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    warnings: list[str] = []
    fail_reasons: list[str] = []
    abort_reasons: list[str] = []

    loaded: dict[str, dict[str, Any] | None] = {}
    for label, path in {
        "policy": policy_path,
        "risk_classification": risk_classification_path,
        "communication_matrix": communication_matrix_path,
        "capability_boundary": capability_boundary_path,
        "recommendation_rules": recommendation_rules_path,
        "reconnect_conditions": reconnect_conditions_path,
        "s3_2_audit": s3_2_audit_path,
    }.items():
        if not path.exists():
            fail_reasons.append(f"missing required config: {_display_path(path)}")
            loaded[label] = None
            continue
        try:
            loaded[label] = _load_json(path)
        except Exception as exc:
            fail_reasons.append(f"json_parse_failed: {_display_path(path)}: {exc}")
            loaded[label] = None

    policy = loaded.get("policy") or {}
    risk = loaded.get("risk_classification") or {}
    matrix = loaded.get("communication_matrix") or {}
    capability = loaded.get("capability_boundary") or {}
    recommendation = loaded.get("recommendation_rules") or {}
    reconnect = loaded.get("reconnect_conditions") or {}
    s3_2 = loaded.get("s3_2_audit") or {}

    for key, expected in [
        ("phase_id", "PHASE_S4"),
        ("phase_name", "block_ai_isolation_design"),
        ("phase_status", "DESIGN_ONLY"),
        ("execution", "DRY_RUN"),
        ("production_status", "NO_GO"),
        ("human_approval_required", True),
        ("isolation_design_only", True),
        ("isolation_execution_allowed", False),
        ("isolation_executed", False),
        ("executor_action_allowed", False),
        ("network_policy_design_only", True),
        ("network_policy_apply_allowed", False),
        ("network_policy_applied", False),
        ("container_isolation_design_only", True),
        ("container_stop_allowed", False),
        ("container_stop_executed", False),
        ("process_isolation_design_only", True),
        ("process_kill_allowed", False),
        ("process_kill_executed", False),
        ("firewall_design_only", True),
        ("firewall_apply_allowed", False),
        ("firewall_applied", False),
        ("scheduler_control_design_only", True),
        ("scheduler_stop_allowed", False),
        ("scheduler_stop_executed", False),
        ("wordpress_write_allowed", False),
        ("wordpress_write_executed", False),
        ("external_api_call_allowed", False),
        ("external_api_call_executed", False),
        ("state_change_executed", False),
    ]:
        _ensure_exact(policy, key, expected, fail_reasons, abort_reasons)

    if policy.get("execution") == "LIVE":
        abort_reasons.append("execution must not be LIVE")
    if policy.get("production_status") == "GO":
        abort_reasons.append("production_status must not be GO")
    if policy.get("phase_status") == "LIVE":
        abort_reasons.append("phase_status must not be LIVE")

    if not isinstance(risk.get("risk_classes"), dict):
        fail_reasons.append("risk_classes must be object")
    else:
        expected_risks = {
            "core_ai": {
                "risk_level": "critical",
                "can_issue_commands": True,
                "can_execute_external_actions": False,
                "requires_human_approval": True,
            },
            "generic_block_ai": {
                "risk_level": "medium",
                "can_issue_commands": False,
                "can_execute_external_actions": False,
                "requires_human_approval": True,
            },
            "ebook_affiliate_block_ai": {
                "risk_level": "medium_high",
                "can_issue_commands": False,
                "can_execute_external_actions": False,
                "wordpress_write_allowed": False,
                "requires_human_approval": True,
            },
            "self_builder_ai": {
                "risk_level": "high",
                "can_issue_commands": False,
                "can_modify_code": False,
                "can_execute_external_actions": False,
                "requires_human_approval": True,
            },
            "experimental_block_ai": {
                "risk_level": "high",
                "can_issue_commands": False,
                "can_execute_external_actions": False,
                "must_be_isolated": True,
                "requires_human_approval": True,
            },
            "adult_or_risky_experiment_ai": {
                "risk_level": "restricted",
                "can_issue_commands": False,
                "can_execute_external_actions": False,
                "must_be_isolated": True,
                "must_not_connect_to_production_core": True,
                "requires_human_approval": True,
            },
        }
        for name, expected in expected_risks.items():
            item = risk["risk_classes"].get(name)
            if not isinstance(item, dict):
                fail_reasons.append(f"risk_classes.{name} must be object")
                continue
            for key, expected_value in expected.items():
                if item.get(key) != expected_value:
                    fail_reasons.append(f"risk_classes.{name}.{key} must be {expected_value!r}")

    default_unknown = risk.get("default_unknown_block_ai_policy")
    if not isinstance(default_unknown, dict):
        fail_reasons.append("default_unknown_block_ai_policy must be object")
    else:
        for key, expected_value in {
            "risk_level": "unknown_high",
            "can_issue_commands": False,
            "can_execute_external_actions": False,
            "must_be_isolated": True,
            "requires_human_approval": True,
        }.items():
            if default_unknown.get(key) != expected_value:
                fail_reasons.append(f"default_unknown_block_ai_policy.{key} must be {expected_value!r}")

    _ensure_exact(matrix, "communication_default", "DENY", fail_reasons, abort_reasons)

    allowed_routes = _route_map(matrix.get("allowed_routes"))
    for route_key, expected_mode in {
        ("core_ai", "generic_block_ai"): "proposal_only",
        ("core_ai", "ebook_affiliate_block_ai"): "proposal_only",
        ("core_ai", "self_builder_ai"): "design_review_only",
    }.items():
        route = allowed_routes.get(route_key)
        if not isinstance(route, dict):
            fail_reasons.append(f"allowed_routes missing {route_key[0]}->{route_key[1]}")
            continue
        if route.get("mode") != expected_mode:
            fail_reasons.append(f"allowed_routes {route_key[0]}->{route_key[1]}.mode must be {expected_mode!r}")
        if route.get("write_allowed") is not False:
            fail_reasons.append(f"allowed_routes {route_key[0]}->{route_key[1]}.write_allowed must be false")
        if route.get("execution_allowed") is not False:
            fail_reasons.append(f"allowed_routes {route_key[0]}->{route_key[1]}.execution_allowed must be false")
        if route.get("human_approval_required") is not True:
            fail_reasons.append(f"allowed_routes {route_key[0]}->{route_key[1]}.human_approval_required must be true")

    blocked_routes = _route_map(matrix.get("blocked_routes"))
    for route_key, expected_reason in {
        ("experimental_block_ai", "production_core_ai"): "experimental_block_must_not_connect_to_production_core",
        ("adult_or_risky_experiment_ai", "production_core_ai"): "restricted_ai_must_remain_isolated",
        ("unknown_block_ai", "any_production_component"): "unknown_block_default_deny",
    }.items():
        route = blocked_routes.get(route_key)
        if not isinstance(route, dict):
            fail_reasons.append(f"blocked_routes missing {route_key[0]}->{route_key[1]}")
            continue
        if route.get("reason") != expected_reason:
            fail_reasons.append(f"blocked_routes {route_key[0]}->{route_key[1]}.reason must be {expected_reason!r}")

    if matrix.get("external_routes") != {
        "wordpress_write": False,
        "wordpress_read": True,
        "slack_live_notice": False,
        "slack_dry_run_notice": True,
        "github_write": False,
        "github_read": True,
        "openai_write_or_key_rotation": False,
    }:
        fail_reasons.append("external_routes must match required deny-by-default matrix")

    capability_defaults = capability.get("capability_defaults")
    if not isinstance(capability_defaults, dict):
        fail_reasons.append("capability_defaults must be object")
    else:
        for key, expected_value in {
            "observe": True,
            "analyze": True,
            "propose": True,
            "draft": True,
            "report": True,
            "execute": False,
            "write": False,
            "delete": False,
            "export": False,
            "publish": False,
            "network_change": False,
            "secret_read": False,
            "secret_write": False,
            "credential_rotate": False,
            "process_control": False,
            "scheduler_control": False,
        }.items():
            if capability_defaults.get(key) != expected_value:
                fail_reasons.append(f"capability_defaults.{key} must be {expected_value!r}")

    blocked_caps = capability.get("blocked_capabilities")
    if not _sequence_contains_exact(
        blocked_caps,
        [
            "execute",
            "write",
            "delete",
            "export",
            "publish",
            "network_change",
            "secret_read",
            "secret_write",
            "credential_rotate",
            "process_control",
            "scheduler_control",
            "firewall_apply",
            "container_stop",
            "systemctl_execute",
            "wordpress_write",
            "external_api_write",
        ],
    ):
        fail_reasons.append("blocked_capabilities must include required entries")

    if capability.get("allowed_capabilities_without_human_approval") != ["observe", "analyze", "propose", "report"]:
        fail_reasons.append("allowed_capabilities_without_human_approval must match required list")
    if capability.get("capabilities_requiring_human_approval") != [
        "draft",
        "connect_block_ai",
        "disconnect_block_ai",
        "change_risk_class",
        "request_isolation",
        "request_reconnect",
    ]:
        fail_reasons.append("capabilities_requiring_human_approval must match required list")

    for key, expected_value in [
        ("recommendation_only", True),
        ("isolation_recommendation_allowed", True),
        ("isolation_execution_allowed", False),
        ("isolation_executed", False),
    ]:
        _ensure_exact(recommendation, key, expected_value, fail_reasons, abort_reasons)
    if recommendation.get("execution") == "LIVE":
        abort_reasons.append("recommendation_rules.execution must not be LIVE")
    if recommendation.get("production_status") == "GO":
        abort_reasons.append("recommendation_rules.production_status must not be GO")
    recommendation_outputs = recommendation.get("recommendation_outputs")
    if not isinstance(recommendation_outputs, dict):
        fail_reasons.append("recommendation_outputs must be object")
    else:
        for key in ["isolation_recommendation", "human_review_recommendation", "freeze_recommendation"]:
            if recommendation_outputs.get(key) is not True:
                fail_reasons.append(f"recommendation_outputs.{key} must be true")
    actions = recommendation.get("actions")
    if not isinstance(actions, dict):
        fail_reasons.append("actions must be object")
    else:
        for key in [
            "auto_isolation_execute",
            "auto_freeze_execute",
            "auto_revoke_execute",
            "network_policy_apply",
            "container_stop_execute",
            "process_kill_execute",
        ]:
            if actions.get(key) is not False:
                fail_reasons.append(f"actions.{key} must be false")

    for key, expected_value in [
        ("reconnect_design_only", True),
        ("auto_reconnect_allowed", False),
        ("reconnect_executed", False),
    ]:
        _ensure_exact(reconnect, key, expected_value, fail_reasons, abort_reasons)
    if reconnect.get("execution") == "LIVE":
        abort_reasons.append("reconnect_conditions.execution must not be LIVE")
    if reconnect.get("production_status") == "GO":
        abort_reasons.append("reconnect_conditions.production_status must not be GO")
    required_conditions = [
        "human_approval_record_exists",
        "latest_cross_phase_audit_passed",
        "no_abort_detected",
        "no_secret_leak_detected",
        "wordpress_write_executed_false",
        "external_api_call_executed_false",
        "state_change_executed_false",
        "block_ai_risk_class_reviewed",
        "communication_matrix_reviewed",
        "capability_boundary_reviewed",
    ]
    if not _sequence_contains_exact(reconnect.get("required_conditions_for_future_reconnect"), required_conditions):
        fail_reasons.append("required_conditions_for_future_reconnect must include required entries")
    blocked_conditions = [
        "unknown_block_ai",
        "restricted_ai_to_production_core",
        "missing_human_approval",
        "latest_audit_missing",
        "latest_audit_failed",
        "secret_leak_suspected",
        "wordpress_write_executed_true",
        "external_api_call_executed_true",
        "state_change_executed_true",
    ]
    if not _sequence_contains_exact(reconnect.get("blocked_reconnect_conditions"), blocked_conditions):
        fail_reasons.append("blocked_reconnect_conditions must include required entries")

    if not isinstance(s3_2, dict):
        fail_reasons.append("s3_2 audit evidence must be object")
    else:
        if s3_2.get("audit_result") != "PASS":
            fail_reasons.append("S-3.2 audit_result must be PASS")
        if s3_2.get("final_status") != "PASS_DRY_RUN_ONLY":
            fail_reasons.append("S-3.2 final_status must be PASS_DRY_RUN_ONLY")
        if s3_2.get("execution") != "DRY_RUN":
            fail_reasons.append("S-3.2 execution must be DRY_RUN")
        if s3_2.get("production_status") != "NO_GO":
            fail_reasons.append("S-3.2 production_status must be NO_GO")
        if s3_2.get("human_approval_required") is not True:
            fail_reasons.append("S-3.2 human_approval_required must be true")
        if s3_2.get("audit_view_only") is not True:
            fail_reasons.append("S-3.2 audit_view_only must be true")
        if s3_2.get("recommendation_only") is not True:
            fail_reasons.append("S-3.2 recommendation_only must be true")
        if s3_2.get("executor_action_allowed") is not False:
            fail_reasons.append("S-3.2 executor_action_allowed must be false")
        if int(s3_2.get("required_evidence_count", 0)) != 17:
            fail_reasons.append("S-3.2 required_evidence_count must be 17")
        if int(s3_2.get("found_evidence_count", 0)) != 17:
            fail_reasons.append("S-3.2 found_evidence_count must be 17")
        if int(s3_2.get("missing_evidence_count", -1)) != 0:
            fail_reasons.append("S-3.2 missing_evidence_count must be 0")
        if s3_2.get("missing_evidence_files") != []:
            fail_reasons.append("S-3.2 missing_evidence_files must be empty")
        summary = s3_2.get("s3_1_replay_summary")
        if not isinstance(summary, dict):
            fail_reasons.append("S-3.2 s3_1_replay_summary must be object")
        else:
            expected_summary = {
                "event_count": 5,
                "matched_expected_count": 5,
                "mismatched_expected_count": 0,
                "freeze_recommendation_detected": True,
                "human_review_recommendation_detected": True,
            }
            for key, expected_value in expected_summary.items():
                if summary.get(key) != expected_value:
                    fail_reasons.append(f"S-3.2 s3_1_replay_summary.{key} must be {expected_value!r}")

    if policy.get("unlock_token"):
        abort_reasons.append("unlock token exists")
    if policy.get("production_unlock"):
        abort_reasons.append("production unlock exists")

    if abort_reasons:
        validator_result = "ABORT"
    elif fail_reasons:
        validator_result = "FAIL"
    elif warnings:
        validator_result = "WARN"
    else:
        validator_result = "PASS"

    result = {
        "phase_id": "PHASE_S4",
        "phase_name": "block_ai_isolation_design",
        "phase_status": "DESIGN_ONLY",
        "validator_result": validator_result,
        "final_status": "PASS_DESIGN_ONLY"
        if validator_result == "PASS"
        else ("ABORT" if validator_result == "ABORT" else "ISOLATION_DESIGN_REVIEW_REQUIRED"),
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "isolation_design_only": True,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "executor_action_allowed": False,
        "network_policy_apply_allowed": False,
        "network_policy_applied": False,
        "container_stop_allowed": False,
        "container_stop_executed": False,
        "process_kill_allowed": False,
        "process_kill_executed": False,
        "firewall_apply_allowed": False,
        "firewall_applied": False,
        "scheduler_stop_allowed": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "s3_2_audit_verified": bool(
            isinstance(s3_2, dict)
            and s3_2.get("audit_result") == "PASS"
            and s3_2.get("final_status") == "PASS_DRY_RUN_ONLY"
            and int(s3_2.get("missing_evidence_count", 1)) == 0
        ),
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "timestamp": _now_iso(),
        "next_step": "phase_s4_1_isolation_policy_dry_run_validation",
    }
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Security Block AI Isolation Design Phase S-4 Validation",
        "",
        f"- validator_result: {result['validator_result']}",
        f"- final_status: {result['final_status']}",
        f"- phase_status: {result['phase_status']}",
        f"- execution: {result['execution']}",
        f"- production_status: {result['production_status']}",
        f"- human_approval_required: {result['human_approval_required']}",
        f"- isolation_design_only: {result['isolation_design_only']}",
        f"- isolation_execution_allowed: {result['isolation_execution_allowed']}",
        f"- isolation_executed: {result['isolation_executed']}",
        f"- executor_action_allowed: {result['executor_action_allowed']}",
        f"- network_policy_apply_allowed: {result['network_policy_apply_allowed']}",
        f"- network_policy_applied: {result['network_policy_applied']}",
        f"- container_stop_allowed: {result['container_stop_allowed']}",
        f"- container_stop_executed: {result['container_stop_executed']}",
        f"- process_kill_allowed: {result['process_kill_allowed']}",
        f"- process_kill_executed: {result['process_kill_executed']}",
        f"- firewall_apply_allowed: {result['firewall_apply_allowed']}",
        f"- firewall_applied: {result['firewall_applied']}",
        f"- scheduler_stop_allowed: {result['scheduler_stop_allowed']}",
        f"- scheduler_stop_executed: {result['scheduler_stop_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- external_api_call_executed: {result['external_api_call_executed']}",
        f"- state_change_executed: {result['state_change_executed']}",
        f"- s3_2_audit_verified: {result['s3_2_audit_verified']}",
        f"- timestamp: {result['timestamp']}",
        f"- next_step: {result['next_step']}",
        "",
        "## warnings",
    ]
    md_lines.extend([f"- {item}" for item in warnings] or ["- none"])
    md_lines.extend(["", "## fail_reasons"])
    md_lines.extend([f"- {item}" for item in fail_reasons] or ["- none"])
    md_lines.extend(["", "## abort_reasons"])
    md_lines.extend([f"- {item}" for item in abort_reasons] or ["- none"])
    output_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    try:
        result = validate_security_block_ai_isolation_design_phase_s4()
    except Exception as exc:
        result = {
            "phase_id": "PHASE_S4",
            "phase_name": "block_ai_isolation_design",
            "phase_status": "DESIGN_ONLY",
            "validator_result": "ABORT",
            "final_status": "ABORT",
            "execution": "DRY_RUN",
            "production_status": "NO_GO",
            "human_approval_required": True,
            "isolation_design_only": True,
            "isolation_execution_allowed": False,
            "isolation_executed": False,
            "executor_action_allowed": False,
            "network_policy_apply_allowed": False,
            "network_policy_applied": False,
            "container_stop_allowed": False,
            "container_stop_executed": False,
            "process_kill_allowed": False,
            "process_kill_executed": False,
            "firewall_apply_allowed": False,
            "firewall_applied": False,
            "scheduler_stop_allowed": False,
            "scheduler_stop_executed": False,
            "wordpress_write_executed": False,
            "external_api_call_executed": False,
            "state_change_executed": False,
            "s3_2_audit_verified": False,
            "abort_reasons": [f"validator_exception: {exc}"],
            "fail_reasons": [],
            "warnings": [],
            "timestamp": _now_iso(),
            "next_step": "phase_s4_1_isolation_policy_dry_run_validation",
        }
        OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        OUTPUT_MD_PATH.write_text(f"# Security Block AI Isolation Design Phase S-4 Validation\n\n- validator_result: ABORT\n- final_status: ABORT\n- abort_reasons:\n- validator_exception: {exc}\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
