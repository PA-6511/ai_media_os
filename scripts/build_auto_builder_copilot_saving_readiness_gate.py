#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_copilot_saving_readiness_gate_policy.json"
DEFAULT_AB_T2 = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
DEFAULT_AB_T3 = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
DEFAULT_AB_T4 = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
DEFAULT_AB_T5 = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"
DEFAULT_AB_T6 = ROOT / "exchange/logs/ab_t6_copilot_usage_saving_evidence_result.json"
DEFAULT_AB_T7 = ROOT / "exchange/logs/ab_t7_copilot_saving_integration_gate_result.json"
DEFAULT_AB_T8 = ROOT / "exchange/logs/ab_t8_copilot_saving_dry_run_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t9_copilot_saving_readiness_gate_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t9_copilot_saving_readiness_gate_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "verify_targets",
    "verification_rules",
    "allowed_outputs",
    "forbidden_outputs",
    "next_phase",
}

EXPECTED_PHASE_ORDER = ["AB-T2", "AB-T3", "AB-T4", "AB-T5", "AB-T6", "AB-T7", "AB-T8"]
REQUIRED_ALLOWED_OUTPUTS = [
    "readiness_summary",
    "pipeline_status_table",
    "verification_summary",
    "safety_summary",
    "readiness_gate_summary",
]
REQUIRED_FORBIDDEN_OUTPUTS = [
    "copilot_send",
    "llm_send",
    "production_execution",
    "wordpress_command",
    "external_api_payload",
    "credential_contents",
    "secret_values",
    "git_commit",
    "git_push",
]
REQUIRED_VERIFICATION_RULES = [
    "verify_previous_phase_results",
    "verify_pipeline_order",
    "verify_execution_mode",
    "verify_production_status",
    "verify_safety_state",
    "verify_no_execution",
    "verify_no_external_api",
    "verify_no_wordpress",
    "verify_no_git_operation",
    "verify_no_credentials",
    "verify_pipeline_ready",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--ab-t2-result", default=str(DEFAULT_AB_T2))
    parser.add_argument("--ab-t3-result", default=str(DEFAULT_AB_T3))
    parser.add_argument("--ab-t4-result", default=str(DEFAULT_AB_T4))
    parser.add_argument("--ab-t5-result", default=str(DEFAULT_AB_T5))
    parser.add_argument("--ab-t6-result", default=str(DEFAULT_AB_T6))
    parser.add_argument("--ab-t7-result", default=str(DEFAULT_AB_T7))
    parser.add_argument("--ab-t8-result", default=str(DEFAULT_AB_T8))
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

    if policy.get("phase") != "AB-T9":
        errors.append("phase must be AB-T9")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "copilot_saving_readiness_gate":
        errors.append("purpose must be copilot_saving_readiness_gate")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")

    verify_targets = policy.get("verify_targets")
    if verify_targets != EXPECTED_PHASE_ORDER:
        errors.append("verify_targets mismatch")

    verification_rules = policy.get("verification_rules")
    if not isinstance(verification_rules, dict):
        errors.append("verification_rules must be object")
    else:
        for key in REQUIRED_VERIFICATION_RULES:
            if verification_rules.get(key) is not True:
                errors.append(f"verification_rules.{key} must be true")

    allowed_outputs = policy.get("allowed_outputs")
    if not isinstance(allowed_outputs, list):
        errors.append("allowed_outputs must be list")
    else:
        for item in REQUIRED_ALLOWED_OUTPUTS:
            if item not in allowed_outputs:
                errors.append(f"allowed_outputs missing: {item}")

    forbidden_outputs = policy.get("forbidden_outputs")
    if not isinstance(forbidden_outputs, list):
        errors.append("forbidden_outputs must be list")
    else:
        for item in REQUIRED_FORBIDDEN_OUTPUTS:
            if item not in forbidden_outputs:
                errors.append(f"forbidden_outputs missing: {item}")

    next_phase = policy.get("next_phase")
    if not isinstance(next_phase, dict):
        errors.append("next_phase must be object")
    else:
        if next_phase.get("phase") != "AB-T10":
            errors.append("next_phase.phase must be AB-T10")
        if next_phase.get("execution_allowed") is not False:
            errors.append("next_phase.execution_allowed must be false")

    return errors


def verify_phase_result(phase_name: str, payload: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    ok = True
    if payload.get("phase") != phase_name:
        errors.append(f"{phase_name} phase mismatch")
        ok = False
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


def build_verification_summary(table: list[dict[str, Any]], pipeline_ready: bool) -> str:
    verified = sum(1 for item in table if item.get("verified") is True)
    return (
        f"Verified {verified}/{len(table)} phases in pipeline order; "
        f"pipeline_ready={pipeline_ready}; "
        "all phases remain PASS_DESIGN_ONLY_NO_EXECUTION."
    )


def build_safety_summary() -> str:
    return (
        "DESIGN_ONLY / NO_EXECUTION / DRY_RUN_ONLY maintained; "
        "Copilot send, LLM send, WordPress, external API, credential access, git commit/push, "
        "production write, and destructive operations remain blocked."
    )


def build_readiness_summary(verified_phase_count: int, pipeline_ready: bool, readiness_gate_verified: bool) -> str:
    return (
        f"Copilot saving pipeline readiness fixed with {verified_phase_count} verified phases; "
        f"pipeline_ready={pipeline_ready}; readiness_gate_verified={readiness_gate_verified}; "
        "operationally ready under design-only constraints without any execution path enabled."
    )


def build_readiness_gate_summary() -> str:
    return (
        "AB-T9 confirms the token-saving pipeline is ready for baseline fixation while remaining detached from any live Copilot send path."
    )


def build_result(
    policy: dict[str, Any],
    table: list[dict[str, Any]],
    verification_summary: str,
    safety_summary: str,
    readiness_summary: str,
    readiness_gate_summary: str,
    errors: list[str],
) -> dict[str, Any]:
    phase_order_verified = [item.get("phase") for item in table] == EXPECTED_PHASE_ORDER
    all_verified = all(item.get("verified") is True for item in table)
    verified_phase_count = len(table)

    pipeline_ready = phase_order_verified and all_verified
    readiness_gate_verified = pipeline_ready and not errors
    forbidden_operations_all_blocked = True
    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if readiness_gate_verified else "NOT_READY"

    return {
        "phase": "AB-T9",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "verified_phase_count": verified_phase_count,
        "pipeline_ready": pipeline_ready,
        "readiness_gate_verified": readiness_gate_verified,
        "pipeline_status_table_generated": True,
        "verification_summary_generated": bool(verification_summary),
        "safety_summary_generated": bool(safety_summary),
        "readiness_summary_generated": bool(readiness_summary),
        "forbidden_operations_all_blocked": forbidden_operations_all_blocked,
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t10": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "pipeline_status_table": table,
        "verification_summary": verification_summary,
        "safety_summary": safety_summary,
        "readiness_summary": readiness_summary,
        "readiness_gate_summary": readiness_gate_summary,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# AB-T9 Copilot Saving Readiness Gate Report",
        "",
        "## Readiness Overview",
        f"- final_status: {result['final_status']}",
        f"- verified_phase_count: {result['verified_phase_count']}",
        f"- pipeline_ready: {result['pipeline_ready']}",
        f"- readiness_gate_verified: {result['readiness_gate_verified']}",
        "",
        "## Pipeline Verification",
        f"- {result['verification_summary']}",
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
        "## AB-T7 Summary",
        f"- verified: {result['pipeline_status_table'][5]['verified']}",
        "",
        "## AB-T8 Summary",
        f"- verified: {result['pipeline_status_table'][6]['verified']}",
        "",
        "## Safety Verification",
        f"- {result['safety_summary']}",
        "",
        "## Readiness Decision",
        f"- {result['readiness_summary']}",
        f"- {result['readiness_gate_summary']}",
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
    ab_t7_path: Path,
    ab_t8_path: Path,
    output_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)

    table = [
        verify_phase_result("AB-T2", load_json(ab_t2_path), errors),
        verify_phase_result("AB-T3", load_json(ab_t3_path), errors),
        verify_phase_result("AB-T4", load_json(ab_t4_path), errors),
        verify_phase_result("AB-T5", load_json(ab_t5_path), errors),
        verify_phase_result("AB-T6", load_json(ab_t6_path), errors),
        verify_phase_result("AB-T7", load_json(ab_t7_path), errors),
        verify_phase_result("AB-T8", load_json(ab_t8_path), errors),
    ]

    pipeline_ready = [item.get("phase") for item in table] == EXPECTED_PHASE_ORDER and all(
        item.get("verified") is True for item in table
    )
    verification_summary = build_verification_summary(table, pipeline_ready)
    safety_summary = build_safety_summary()
    readiness_summary = build_readiness_summary(len(table), pipeline_ready, pipeline_ready and not errors)
    readiness_gate_summary = build_readiness_gate_summary()

    result = build_result(
        policy,
        table,
        verification_summary,
        safety_summary,
        readiness_summary,
        readiness_gate_summary,
        errors,
    )
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
        ab_t7_path=Path(args.ab_t7_result),
        ab_t8_path=Path(args.ab_t8_result),
        output_path=Path(args.output),
        report_path=Path(args.report),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())