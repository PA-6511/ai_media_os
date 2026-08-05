#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_copilot_saving_integration_gate_policy.json"
DEFAULT_AB_T2 = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
DEFAULT_AB_T3 = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
DEFAULT_AB_T4 = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
DEFAULT_AB_T5 = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"
DEFAULT_AB_T6 = ROOT / "exchange/logs/ab_t6_copilot_usage_saving_evidence_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t7_copilot_saving_integration_gate_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t7_copilot_saving_integration_gate_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "integration_targets",
    "integration_rules",
    "pipeline_order",
    "allowed_outputs",
    "forbidden_outputs",
    "copilot_send_allowed",
    "llm_send_allowed",
    "external_api_call_allowed",
    "wordpress_api_call_allowed",
    "credential_read_allowed",
    "credential_output_allowed",
    "production_write_allowed",
    "destructive_operation_allowed",
    "git_commit_allowed",
    "git_push_allowed",
    "next_phase",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--ab-t2-result", default=str(DEFAULT_AB_T2))
    parser.add_argument("--ab-t3-result", default=str(DEFAULT_AB_T3))
    parser.add_argument("--ab-t4-result", default=str(DEFAULT_AB_T4))
    parser.add_argument("--ab-t5-result", default=str(DEFAULT_AB_T5))
    parser.add_argument("--ab-t6-result", default=str(DEFAULT_AB_T6))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(policy.keys()))
    if missing:
        errors.append(f"missing required keys: {missing}")

    if policy.get("phase") != "AB-T7":
        errors.append("phase must be AB-T7")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "copilot_saving_integration_gate":
        errors.append("purpose must be copilot_saving_integration_gate")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")

    expected_order = ["AB-T2", "AB-T3", "AB-T4", "AB-T5", "AB-T6"]
    if policy.get("integration_targets") != expected_order:
        errors.append("integration_targets mismatch")
    if policy.get("pipeline_order") != expected_order:
        errors.append("pipeline_order mismatch")

    rules = policy.get("integration_rules")
    if not isinstance(rules, dict):
        errors.append("integration_rules must be object")
    else:
        for key in [
            "verify_all_previous_phases",
            "verify_execution_mode",
            "verify_production_status",
            "verify_safety_state",
            "verify_pipeline_order",
            "verify_forbidden_operations",
            "verify_pipeline_readiness",
        ]:
            if rules.get(key) is not True:
                errors.append(f"integration_rules.{key} must be true")

    for key in [
        "copilot_send_allowed",
        "llm_send_allowed",
        "external_api_call_allowed",
        "wordpress_api_call_allowed",
        "credential_read_allowed",
        "credential_output_allowed",
        "production_write_allowed",
        "destructive_operation_allowed",
        "git_commit_allowed",
        "git_push_allowed",
    ]:
        if policy.get(key) is not False:
            errors.append(f"{key} must be false")

    next_phase = policy.get("next_phase")
    if not isinstance(next_phase, dict):
        errors.append("next_phase must be object")
    else:
        if next_phase.get("phase") != "AB-T8":
            errors.append("next_phase.phase must be AB-T8")
        if next_phase.get("execution_allowed") is not False:
            errors.append("next_phase.execution_allowed must be false")

    return errors


def verify_result(phase_name: str, payload: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    ok = True
    if payload.get("final_status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append(f"{phase_name} final_status mismatch")
        ok = False
    if payload.get("execution_mode") != "DESIGN_ONLY":
        errors.append(f"{phase_name} execution_mode mismatch")
        ok = False
    if payload.get("production_status") != "NO_GO":
        errors.append(f"{phase_name} production_status mismatch")
        ok = False
    if payload.get("safety_state") != "DRY_RUN_ONLY":
        errors.append(f"{phase_name} safety_state mismatch")
        ok = False
    if payload.get("forbidden_operations_all_blocked") is not True:
        errors.append(f"{phase_name} forbidden_operations_all_blocked must be true")
        ok = False

    return {
        "phase": phase_name,
        "final_status": payload.get("final_status"),
        "execution_mode": payload.get("execution_mode"),
        "production_status": payload.get("production_status"),
        "safety_state": payload.get("safety_state"),
        "verified": ok,
    }


def build_result(policy: dict[str, Any], table: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    expected_order = policy.get("pipeline_order", [])
    actual_order = [item.get("phase") for item in table]
    pipeline_order_verified = expected_order == actual_order
    if not pipeline_order_verified:
        errors.append("pipeline order verification failed")

    blocked = all(
        policy.get(key) is False
        for key in [
            "copilot_send_allowed",
            "llm_send_allowed",
            "external_api_call_allowed",
            "wordpress_api_call_allowed",
            "credential_read_allowed",
            "credential_output_allowed",
            "production_write_allowed",
            "destructive_operation_allowed",
            "git_commit_allowed",
            "git_push_allowed",
        ]
    )

    pipeline_ready = pipeline_order_verified and all(item.get("verified") is True for item in table) and blocked
    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if pipeline_ready and not errors else "NOT_READY"

    return {
        "phase": "AB-T7",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "verified_phase_count": len(table),
        "pipeline_order_verified": pipeline_order_verified,
        "pipeline_ready": pipeline_ready,
        "integration_summary_generated": True,
        "pipeline_status_table_generated": True,
        "token_saving_pipeline_summary_generated": True,
        "safety_summary_generated": True,
        "forbidden_operations_all_blocked": blocked,
        "pipeline_status_table": table,
        "integration_summary": "AB-T2 to AB-T6 are connected in order and verified under design-only constraints.",
        "token_saving_pipeline_summary": "Pipeline narrows context, targets related files, drafts minimal patches, limits tests, and consolidates evidence.",
        "safety_summary": "All stages remain NO_GO / DRY_RUN_ONLY with external, WordPress, credential, and git operations blocked.",
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t8": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# AB-T7 Copilot Saving Integration Gate Report",
        "",
        "## Pipeline Overview",
        f"- verified_phase_count: {result['verified_phase_count']}",
        f"- pipeline_ready: {result['pipeline_ready']}",
        "",
        "## AB-T2 Summary",
        f"- verified: {result['pipeline_status_table'][0]['verified']}",
        "",
        "## AB-T3 Summary",
        f"- verified: {result['pipeline_status_table'][1]['verified']}",
        "",
        "## AB-T4 Summary",
        f"- verified: {result['pipeline_status_table'][2]['verified']}",
        "",
        "## AB-T5 Summary",
        f"- verified: {result['pipeline_status_table'][3]['verified']}",
        "",
        "## AB-T6 Summary",
        f"- verified: {result['pipeline_status_table'][4]['verified']}",
        "",
        "## Pipeline Order Verification",
        f"- pipeline_order_verified: {result['pipeline_order_verified']}",
        "",
        "## Safety Verification",
        f"- forbidden_operations_all_blocked: {result['forbidden_operations_all_blocked']}",
        f"- {result['safety_summary']}",
        "",
        "## Token Saving Strategy Summary",
        f"- {result['token_saving_pipeline_summary']}",
        "",
        "## Readiness Summary",
        f"- final_status: {result['final_status']}",
        f"- ready_for_ab_t8: {result['ready_for_ab_t8']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase'].get('phase')}",
        f"- name: {result['next_phase'].get('name')}",
        f"- execution_allowed: {result['next_phase'].get('execution_allowed')}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run(
    policy_path: Path,
    ab_t2_path: Path,
    ab_t3_path: Path,
    ab_t4_path: Path,
    ab_t5_path: Path,
    ab_t6_path: Path,
    output_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)

    table = [
        verify_result("AB-T2", load_json(ab_t2_path), errors),
        verify_result("AB-T3", load_json(ab_t3_path), errors),
        verify_result("AB-T4", load_json(ab_t4_path), errors),
        verify_result("AB-T5", load_json(ab_t5_path), errors),
        verify_result("AB-T6", load_json(ab_t6_path), errors),
    ]

    result = build_result(policy, table, errors)
    write_json(output_path, result)
    write_report(result, report_path)
    return result


def main() -> int:
    args = parse_args()
    result = run(
        policy_path=Path(args.policy),
        ab_t2_path=Path(args.ab_t2_result),
        ab_t3_path=Path(args.ab_t3_result),
        ab_t4_path=Path(args.ab_t4_result),
        ab_t5_path=Path(args.ab_t5_result),
        ab_t6_path=Path(args.ab_t6_result),
        output_path=Path(args.output),
        report_path=Path(args.report),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
