#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_copilot_saving_dry_run_policy.json"
DEFAULT_AB_T2 = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
DEFAULT_AB_T3 = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
DEFAULT_AB_T4 = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
DEFAULT_AB_T5 = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"
DEFAULT_AB_T6 = ROOT / "exchange/logs/ab_t6_copilot_usage_saving_evidence_result.json"
DEFAULT_AB_T7 = ROOT / "exchange/logs/ab_t7_copilot_saving_integration_gate_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t8_copilot_saving_dry_run_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t8_copilot_saving_dry_run_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "dry_run_rules",
    "allowed_outputs",
    "forbidden_outputs",
    "next_phase",
}

REQUIRED_DRY_RUN_RULES = {
    "simulate_pipeline",
    "simulate_prompt",
    "simulate_patch",
    "simulate_tests",
    "simulate_evidence",
    "send_to_copilot",
    "send_to_llm",
    "allow_git_operation",
    "allow_wordpress",
    "allow_external_api",
    "allow_credentials",
}

EXPECTED_PHASE_ORDER = ["AB-T2", "AB-T3", "AB-T4", "AB-T5", "AB-T6", "AB-T7"]
REQUIRED_ALLOWED_OUTPUTS = [
    "dry_run_summary",
    "simulated_prompt",
    "simulated_patch",
    "simulated_test_plan",
    "pipeline_summary",
    "safety_summary",
]
REQUIRED_FORBIDDEN_OUTPUTS = [
    "copilot_send",
    "llm_send",
    "git_commit",
    "git_push",
    "wordpress_command",
    "production_execution",
    "credential_contents",
    "secret_values",
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

    if policy.get("phase") != "AB-T8":
        errors.append("phase must be AB-T8")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "copilot_saving_dry_run_pack":
        errors.append("purpose must be copilot_saving_dry_run_pack")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")

    dry_run_rules = policy.get("dry_run_rules")
    if not isinstance(dry_run_rules, dict):
        errors.append("dry_run_rules must be object")
    else:
        missing_rules = sorted(REQUIRED_DRY_RUN_RULES - set(dry_run_rules.keys()))
        if missing_rules:
            errors.append(f"missing dry_run_rules keys: {missing_rules}")

        for key in [
            "simulate_pipeline",
            "simulate_prompt",
            "simulate_patch",
            "simulate_tests",
            "simulate_evidence",
        ]:
            if dry_run_rules.get(key) is not True:
                errors.append(f"dry_run_rules.{key} must be true")

        for key in [
            "send_to_copilot",
            "send_to_llm",
            "allow_git_operation",
            "allow_wordpress",
            "allow_external_api",
            "allow_credentials",
        ]:
            if dry_run_rules.get(key) is not False:
                errors.append(f"dry_run_rules.{key} must be false")

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
        if next_phase.get("phase") != "AB-T9":
            errors.append("next_phase.phase must be AB-T9")
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


def build_simulated_prompt(ab_t2: dict[str, Any], ab_t3: dict[str, Any], ab_t7: dict[str, Any]) -> str:
    lines = [
        "Copilot Saving Dry Run Input",
        f"- pipeline_ready: {ab_t7.get('pipeline_ready')}",
        "- mode: DESIGN_ONLY / NO_GO / DRY_RUN_ONLY",
        "- send_to_copilot: false",
        "",
        "Compressed Prompt:",
        str(ab_t2.get("compressed_prompt_template", "")).strip(),
        "",
        "Related Files:",
    ]
    for item in ab_t3.get("generated_related_file_list", []):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- {item.get('path')} ({item.get('selection_reason')}, score={item.get('selection_score')})"
        )
    return "\n".join(lines).strip()


def build_simulated_patch(ab_t4: dict[str, Any]) -> dict[str, Any]:
    patch_draft = ab_t4.get("patch_draft", [])
    target_files = []
    risk_notes = []
    for item in patch_draft:
        if not isinstance(item, dict):
            continue
        target = item.get("target_file")
        if isinstance(target, str) and target:
            target_files.append(target)
        risk = item.get("potential_risk")
        if isinstance(risk, str) and risk:
            risk_notes.append(risk)

    return {
        "target_file_count": len(target_files),
        "target_files": target_files,
        "change_scope": "minimal_diff_design_only",
        "draft_origin": "AB-T4 patch_draft",
        "no_apply_command": True,
        "no_git_command": True,
        "no_production_command": True,
        "risk_notes": risk_notes,
    }


def build_pipeline_summary(
    ab_t6: dict[str, Any], ab_t7: dict[str, Any], verified_phase_count: int
) -> str:
    return (
        f"Verified {verified_phase_count} phases across AB-T2 to AB-T7. "
        f"{ab_t7.get('integration_summary', '')} "
        f"{ab_t7.get('token_saving_pipeline_summary', '')} "
        f"{ab_t6.get('readiness_summary', '')}"
    ).strip()


def build_safety_summary(policy: dict[str, Any], ab_t6: dict[str, Any], ab_t7: dict[str, Any]) -> str:
    blocked = policy.get("dry_run_rules", {})
    return (
        "Dry run only; Copilot send, LLM send, git operations, WordPress, external API, and credential access remain blocked. "
        f"Policy blocks: send_to_copilot={blocked.get('send_to_copilot')}, send_to_llm={blocked.get('send_to_llm')}, "
        f"allow_git_operation={blocked.get('allow_git_operation')}, allow_wordpress={blocked.get('allow_wordpress')}, "
        f"allow_external_api={blocked.get('allow_external_api')}, allow_credentials={blocked.get('allow_credentials')}. "
        f"{ab_t6.get('safety_summary', '')} {ab_t7.get('safety_summary', '')}"
    ).strip()


def build_dry_run_summary(
    *,
    verified_phase_count: int,
    pipeline_ready: bool,
    simulated_patch: dict[str, Any],
    selected_test_commands: list[str],
) -> str:
    return (
        f"AB-T8 dry run pack assembled with {verified_phase_count} verified phases; "
        f"pipeline_ready={pipeline_ready}; "
        f"simulated_patch_targets={simulated_patch.get('target_file_count', 0)}; "
        f"simulated_test_commands={len(selected_test_commands)}; "
        "Copilot and all execution paths remain blocked."
    )


def build_evidence_summary(ab_t6: dict[str, Any], ab_t7: dict[str, Any]) -> str:
    return (
        f"Evidence source: {ab_t6.get('token_saving_summary', '')} "
        f"Integration source: {ab_t7.get('integration_summary', '')}"
    ).strip()


def build_result(
    policy: dict[str, Any],
    verification_table: list[dict[str, Any]],
    dry_run_summary: str,
    simulated_prompt: str,
    simulated_patch: dict[str, Any],
    simulated_test_plan: dict[str, Any],
    pipeline_summary: str,
    safety_summary: str,
    evidence_summary: str,
    errors: list[str],
) -> dict[str, Any]:
    verified_phase_count = len(verification_table)
    phase_order_verified = [item.get("phase") for item in verification_table] == EXPECTED_PHASE_ORDER
    all_verified = all(item.get("verified") is True for item in verification_table)

    dry_run_rules = policy.get("dry_run_rules", {})
    forbidden_operations_all_blocked = all(
        dry_run_rules.get(key) is False
        for key in [
            "send_to_copilot",
            "send_to_llm",
            "allow_git_operation",
            "allow_wordpress",
            "allow_external_api",
            "allow_credentials",
        ]
    )

    pipeline_ready = (
        phase_order_verified
        and all_verified
        and forbidden_operations_all_blocked
        and verification_table[-1].get("verified") is True
    )
    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if pipeline_ready and not errors else "NOT_READY"

    return {
        "phase": "AB-T8",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "verified_phase_count": verified_phase_count,
        "pipeline_ready": pipeline_ready,
        "dry_run_summary_generated": bool(dry_run_summary),
        "simulated_prompt_generated": bool(simulated_prompt),
        "simulated_patch_generated": bool(simulated_patch),
        "simulated_test_plan_generated": bool(simulated_test_plan),
        "pipeline_summary_generated": bool(pipeline_summary),
        "safety_summary_generated": bool(safety_summary),
        "evidence_summary_generated": bool(evidence_summary),
        "forbidden_operations_all_blocked": forbidden_operations_all_blocked,
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t9": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "phase_order_verified": phase_order_verified,
        "verification_table": verification_table,
        "dry_run_summary": dry_run_summary,
        "simulated_prompt": simulated_prompt,
        "simulated_patch": simulated_patch,
        "simulated_test_plan": simulated_test_plan,
        "pipeline_summary": pipeline_summary,
        "safety_summary": safety_summary,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# AB-T8 Copilot Saving Dry Run Report",
        "",
        "## Dry Run Status",
        f"- phase: {result['phase']}",
        f"- final_status: {result['final_status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- safety_state: {result['safety_state']}",
        f"- verified_phase_count: {result['verified_phase_count']}",
        f"- pipeline_ready: {result['pipeline_ready']}",
        f"- ready_for_ab_t9: {result['ready_for_ab_t9']}",
        "",
        "## Simulated Input",
        "```text",
        result["simulated_prompt"],
        "```",
        "",
        "## Simulated Patch",
        f"- target_file_count: {result['simulated_patch']['target_file_count']}",
        "- target_files:",
    ]
    lines.extend(f"  - {item}" for item in result["simulated_patch"]["target_files"])
    lines.extend(
        [
            f"- change_scope: {result['simulated_patch']['change_scope']}",
            f"- no_apply_command: {result['simulated_patch']['no_apply_command']}",
            f"- no_git_command: {result['simulated_patch']['no_git_command']}",
            f"- no_production_command: {result['simulated_patch']['no_production_command']}",
            "",
            "## Simulated Test Plan",
            "- selected_tests:",
        ]
    )
    lines.extend(f"  - {item}" for item in result["simulated_test_plan"]["selected_tests"])
    lines.extend(
        [
            f"- why: {result['simulated_test_plan']['why_these_tests']}",
            "",
            "## Evidence Summary",
            f"- {result['evidence_summary']}",
            "",
            "## Pipeline Summary",
            f"- {result['pipeline_summary']}",
            "",
            "## Safety Summary",
            f"- {result['safety_summary']}",
            "",
            "## Next Phase",
            f"- phase: {result['next_phase'].get('phase')}",
            f"- name: {result['next_phase'].get('name')}",
            f"- execution_allowed: {result['next_phase'].get('execution_allowed')}",
            "",
            "## Errors",
        ]
    )
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
    output_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)

    ab_t2 = load_json(ab_t2_path)
    ab_t3 = load_json(ab_t3_path)
    ab_t4 = load_json(ab_t4_path)
    ab_t5 = load_json(ab_t5_path)
    ab_t6 = load_json(ab_t6_path)
    ab_t7 = load_json(ab_t7_path)

    verification_table = [
        verify_phase_result("AB-T2", ab_t2, errors),
        verify_phase_result("AB-T3", ab_t3, errors),
        verify_phase_result("AB-T4", ab_t4, errors),
        verify_phase_result("AB-T5", ab_t5, errors),
        verify_phase_result("AB-T6", ab_t6, errors),
        verify_phase_result("AB-T7", ab_t7, errors),
    ]

    simulated_prompt = build_simulated_prompt(ab_t2, ab_t3, ab_t7)
    simulated_patch = build_simulated_patch(ab_t4)
    simulated_test_plan = dict(ab_t5.get("limited_test_plan", {}))
    pipeline_summary = build_pipeline_summary(ab_t6, ab_t7, len(verification_table))
    safety_summary = build_safety_summary(policy, ab_t6, ab_t7)
    evidence_summary = build_evidence_summary(ab_t6, ab_t7)
    dry_run_summary = build_dry_run_summary(
        verified_phase_count=len(verification_table),
        pipeline_ready=ab_t7.get("pipeline_ready") is True,
        simulated_patch=simulated_patch,
        selected_test_commands=list(ab_t5.get("selected_test_commands", [])),
    )

    result = build_result(
        policy,
        verification_table,
        dry_run_summary,
        simulated_prompt,
        simulated_patch,
        simulated_test_plan,
        pipeline_summary,
        safety_summary,
        evidence_summary,
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
        output_path=Path(args.output),
        report_path=Path(args.report),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())