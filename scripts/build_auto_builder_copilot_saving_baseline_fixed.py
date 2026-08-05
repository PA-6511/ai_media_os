#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_copilot_saving_baseline_fixed_policy.json"
DEFAULT_AB_T2 = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
DEFAULT_AB_T3 = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
DEFAULT_AB_T4 = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
DEFAULT_AB_T5 = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"
DEFAULT_AB_T6 = ROOT / "exchange/logs/ab_t6_copilot_usage_saving_evidence_result.json"
DEFAULT_AB_T7 = ROOT / "exchange/logs/ab_t7_copilot_saving_integration_gate_result.json"
DEFAULT_AB_T8 = ROOT / "exchange/logs/ab_t8_copilot_saving_dry_run_result.json"
DEFAULT_AB_T9 = ROOT / "exchange/logs/ab_t9_copilot_saving_readiness_gate_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t10_copilot_saving_baseline_fixed_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t10_copilot_saving_baseline_fixed_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "baseline_targets",
    "baseline_rules",
    "allowed_outputs",
    "forbidden_outputs",
    "next_phase",
}

EXPECTED_PHASE_ORDER = ["AB-T2", "AB-T3", "AB-T4", "AB-T5", "AB-T6", "AB-T7", "AB-T8", "AB-T9"]
REQUIRED_ALLOWED_OUTPUTS = [
    "baseline_summary",
    "baseline_status_table",
    "pipeline_summary",
    "safety_summary",
    "baseline_readiness",
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
REQUIRED_BASELINE_RULES = {
    "verify_all_previous_phases": True,
    "freeze_baseline_design": True,
    "freeze_pipeline_order": True,
    "freeze_safety_constraints": True,
    "allow_future_extension": True,
    "allow_baseline_modification": False,
}


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
    parser.add_argument("--ab-t9-result", default=str(DEFAULT_AB_T9))
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

    if policy.get("phase") != "AB-T10":
        errors.append("phase must be AB-T10")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "copilot_saving_baseline_fixed":
        errors.append("purpose must be copilot_saving_baseline_fixed")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")

    if policy.get("baseline_targets") != EXPECTED_PHASE_ORDER:
        errors.append("baseline_targets mismatch")

    baseline_rules = policy.get("baseline_rules")
    if not isinstance(baseline_rules, dict):
        errors.append("baseline_rules must be object")
    else:
        for key, expected in REQUIRED_BASELINE_RULES.items():
            if baseline_rules.get(key) is not expected:
                errors.append(f"baseline_rules.{key} must be {str(expected).lower()}")

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
        if next_phase.get("phase") != "AB-T11":
            errors.append("next_phase.phase must be AB-T11")
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


def build_baseline_summary(verified_phase_count: int, baseline_fixed: bool) -> str:
    return (
        f"AB-T2 to AB-T9 fixed as baseline with {verified_phase_count} verified phases; "
        f"baseline_fixed={baseline_fixed}; future extension must not modify the saved baseline."
    )


def build_pipeline_summary(table: list[dict[str, Any]]) -> str:
    verified = sum(1 for item in table if item.get("verified") is True)
    return (
        f"Pipeline order preserved across {len(table)} phases; verified={verified}; "
        "all phases remain PASS_DESIGN_ONLY_NO_EXECUTION under the copilot saving baseline."
    )


def build_safety_summary() -> str:
    return (
        "DESIGN_ONLY / NO_EXECUTION / DRY_RUN_ONLY baseline frozen; "
        "Copilot send, LLM send, WordPress, external API, credential access, git commit/push, "
        "production write, and destructive operations remain blocked."
    )


def build_baseline_readiness(baseline_fixed: bool) -> str:
    return (
        f"Baseline readiness={baseline_fixed}; AB-T11 and later may extend around this baseline, but must not rewrite AB-T2 to AB-T10 design guarantees."
    )


def build_result(
    policy: dict[str, Any],
    table: list[dict[str, Any]],
    baseline_summary: str,
    pipeline_summary: str,
    safety_summary: str,
    baseline_readiness: str,
    errors: list[str],
) -> dict[str, Any]:
    phase_order_verified = [item.get("phase") for item in table] == EXPECTED_PHASE_ORDER
    all_verified = all(item.get("verified") is True for item in table)
    verified_phase_count = len(table)

    baseline_rules = policy.get("baseline_rules", {})
    frozen = (
        baseline_rules.get("freeze_baseline_design") is True
        and baseline_rules.get("freeze_pipeline_order") is True
        and baseline_rules.get("freeze_safety_constraints") is True
        and baseline_rules.get("allow_baseline_modification") is False
    )
    baseline_fixed = phase_order_verified and all_verified and frozen and not errors
    forbidden_operations_all_blocked = True
    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if baseline_fixed else "NOT_READY"

    return {
        "phase": "AB-T10",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "verified_phase_count": verified_phase_count,
        "baseline_fixed": baseline_fixed,
        "baseline_summary_generated": bool(baseline_summary),
        "pipeline_status_table_generated": True,
        "pipeline_summary_generated": bool(pipeline_summary),
        "safety_summary_generated": bool(safety_summary),
        "baseline_readiness_generated": bool(baseline_readiness),
        "forbidden_operations_all_blocked": forbidden_operations_all_blocked,
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t11": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "baseline_status_table": table,
        "baseline_summary": baseline_summary,
        "pipeline_summary": pipeline_summary,
        "safety_summary": safety_summary,
        "baseline_readiness": baseline_readiness,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# AB-T10 Copilot Saving Baseline Fixed Report",
        "",
        "## Baseline Overview",
        f"- final_status: {result['final_status']}",
        f"- verified_phase_count: {result['verified_phase_count']}",
        f"- baseline_fixed: {result['baseline_fixed']}",
        f"- ready_for_ab_t11: {result['ready_for_ab_t11']}",
        "",
        "## Pipeline Status",
        f"- {result['pipeline_summary']}",
        "",
        "## AB-T2 Summary",
        f"- verified: {result['baseline_status_table'][0]['verified']}",
        "",
        "## AB-T3 Summary",
        f"- verified: {result['baseline_status_table'][1]['verified']}",
        "",
        "## AB-T4 Summary",
        f"- verified: {result['baseline_status_table'][2]['verified']}",
        "",
        "## AB-T5 Summary",
        f"- verified: {result['baseline_status_table'][3]['verified']}",
        "",
        "## AB-T6 Summary",
        f"- verified: {result['baseline_status_table'][4]['verified']}",
        "",
        "## AB-T7 Summary",
        f"- verified: {result['baseline_status_table'][5]['verified']}",
        "",
        "## AB-T8 Summary",
        f"- verified: {result['baseline_status_table'][6]['verified']}",
        "",
        "## AB-T9 Summary",
        f"- verified: {result['baseline_status_table'][7]['verified']}",
        "",
        "## Baseline Decision",
        f"- {result['baseline_summary']}",
        f"- {result['baseline_readiness']}",
        "",
        "## Safety Summary",
        f"- {result['safety_summary']}",
        "",
        "## Future Extension Policy",
        "- Future phases may extend around the baseline but must not modify AB-T2 to AB-T10 guarantees.",
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
    ab_t9_path: Path,
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
        verify_phase_result("AB-T9", load_json(ab_t9_path), errors),
    ]

    phase_order_verified = [item.get("phase") for item in table] == EXPECTED_PHASE_ORDER
    all_verified = all(item.get("verified") is True for item in table)
    baseline_fixed = phase_order_verified and all_verified and not errors
    baseline_summary = build_baseline_summary(len(table), baseline_fixed)
    pipeline_summary = build_pipeline_summary(table)
    safety_summary = build_safety_summary()
    baseline_readiness = build_baseline_readiness(baseline_fixed)

    result = build_result(
        policy,
        table,
        baseline_summary,
        pipeline_summary,
        safety_summary,
        baseline_readiness,
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
        ab_t9_path=Path(args.ab_t9_result),
        output_path=Path(args.output),
        report_path=Path(args.report),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())