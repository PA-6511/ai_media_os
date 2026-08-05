#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_copilot_usage_saving_evidence_policy.json"
DEFAULT_AB_T2 = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
DEFAULT_AB_T3 = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
DEFAULT_AB_T4 = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
DEFAULT_AB_T5 = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t6_copilot_usage_saving_evidence_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t6_copilot_usage_saving_evidence_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "collect_from",
    "evidence_rules",
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

    if policy.get("phase") != "AB-T6":
        errors.append("phase must be AB-T6")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "copilot_usage_saving_evidence_pack":
        errors.append("purpose must be copilot_usage_saving_evidence_pack")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")

    expected_collect = ["AB-T2", "AB-T3", "AB-T4", "AB-T5"]
    if policy.get("collect_from") != expected_collect:
        errors.append("collect_from must be [AB-T2, AB-T3, AB-T4, AB-T5]")

    evidence_rules = policy.get("evidence_rules")
    if not isinstance(evidence_rules, dict):
        errors.append("evidence_rules must be object")
    else:
        for key in [
            "verify_previous_phase_results",
            "verify_safety_state",
            "verify_execution_mode",
            "verify_no_execution",
            "verify_no_external_api",
            "verify_no_wordpress",
            "verify_no_git_operation",
            "verify_no_credentials",
            "build_summary_report",
        ]:
            if evidence_rules.get(key) is not True:
                errors.append(f"evidence_rules.{key} must be true")

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
        if next_phase.get("phase") != "AB-T7":
            errors.append("next_phase.phase must be AB-T7")
        if next_phase.get("execution_allowed") is not False:
            errors.append("next_phase.execution_allowed must be false")

    return errors


def verify_phase_result(name: str, payload: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    required_status = "PASS_DESIGN_ONLY_NO_EXECUTION"
    ok = True

    if payload.get("final_status") != required_status:
        errors.append(f"{name} final_status must be {required_status}")
        ok = False
    if payload.get("execution_mode") != "DESIGN_ONLY":
        errors.append(f"{name} execution_mode must be DESIGN_ONLY")
        ok = False
    if payload.get("production_status") != "NO_GO":
        errors.append(f"{name} production_status must be NO_GO")
        ok = False
    if payload.get("safety_state") != "DRY_RUN_ONLY":
        errors.append(f"{name} safety_state must be DRY_RUN_ONLY")
        ok = False
    if payload.get("forbidden_operations_all_blocked") is not True:
        errors.append(f"{name} forbidden_operations_all_blocked must be true")
        ok = False

    return {
        "phase": name,
        "final_status": payload.get("final_status"),
        "execution_mode": payload.get("execution_mode"),
        "production_status": payload.get("production_status"),
        "safety_state": payload.get("safety_state"),
        "verified": ok,
    }


def build_result(policy: dict[str, Any], table: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    all_verified = all(item.get("verified") is True for item in table)
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

    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if not errors and all_verified and blocked else "NOT_READY"

    return {
        "phase": "AB-T6",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "previous_phase_count": len(table),
        "all_previous_phases_verified": all_verified,
        "evidence_pack_generated": True,
        "phase_status_table_generated": True,
        "token_saving_summary_generated": True,
        "safety_summary_generated": True,
        "readiness_summary_generated": True,
        "forbidden_operations_all_blocked": blocked,
        "phase_status_table": table,
        "token_saving_summary": "AB-T2 to AB-T5 progressively constrain context scope, patch drafting, and test scope for token savings.",
        "safety_summary": "All phases remain DESIGN_ONLY/NO_GO/DRY_RUN_ONLY with execution and sensitive operations blocked.",
        "readiness_summary": "Evidence pack complete and ready for AB-T7 integration gate review.",
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t7": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# AB-T6 Copilot Usage Saving Evidence Report",
        "",
        "## AB-T2 Summary",
        f"- verified: {result['phase_status_table'][0]['verified']}",
        "",
        "## AB-T3 Summary",
        f"- verified: {result['phase_status_table'][1]['verified']}",
        "",
        "## AB-T4 Summary",
        f"- verified: {result['phase_status_table'][2]['verified']}",
        "",
        "## AB-T5 Summary",
        f"- verified: {result['phase_status_table'][3]['verified']}",
        "",
        "## Overall Safety",
        f"- {result['safety_summary']}",
        "",
        "## Overall Token Saving Strategy",
        f"- {result['token_saving_summary']}",
        "",
        "## Execution Boundary",
        "- DESIGN_ONLY / NO_EXECUTION / DRY_RUN_ONLY",
        "- No Copilot send, no external API, no WordPress, no credential read/output",
        "",
        "## Readiness",
        f"- final_status: {result['final_status']}",
        f"- ready_for_ab_t7: {result['ready_for_ab_t7']}",
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
    output_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)

    ab_t2 = load_json(ab_t2_path)
    ab_t3 = load_json(ab_t3_path)
    ab_t4 = load_json(ab_t4_path)
    ab_t5 = load_json(ab_t5_path)

    table = [
        verify_phase_result("AB-T2", ab_t2, errors),
        verify_phase_result("AB-T3", ab_t3, errors),
        verify_phase_result("AB-T4", ab_t4, errors),
        verify_phase_result("AB-T5", ab_t5, errors),
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
        output_path=Path(args.output),
        report_path=Path(args.report),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
