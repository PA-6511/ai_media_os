#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_patch_draft_generator_policy.json"
DEFAULT_AB_T3_RESULT = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t4_patch_draft_generator_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "draft_rules",
    "allowed_outputs",
    "forbidden_outputs",
    "copilot_send_allowed",
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

REQUIRED_DRAFT_RULES = {
    "generate_patch_template",
    "generate_unified_diff",
    "generate_apply_command",
    "generate_git_command",
    "max_patch_targets",
    "patch_style",
    "include_change_summary",
    "include_reason",
    "include_risk_note",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--ab-t3-result", default=str(DEFAULT_AB_T3_RESULT))
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

    if policy.get("phase") != "AB-T4":
        errors.append("phase must be AB-T4")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "patch_draft_generator":
        errors.append("purpose must be patch_draft_generator")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")

    for key in [
        "copilot_send_allowed",
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

    draft_rules = policy.get("draft_rules")
    if not isinstance(draft_rules, dict):
        errors.append("draft_rules must be object")
        return errors

    missing_rules = sorted(REQUIRED_DRAFT_RULES - set(draft_rules.keys()))
    if missing_rules:
        errors.append(f"missing draft_rules keys: {missing_rules}")

    if draft_rules.get("generate_patch_template") is not True:
        errors.append("draft_rules.generate_patch_template must be true")
    if draft_rules.get("generate_unified_diff") is not False:
        errors.append("draft_rules.generate_unified_diff must be false")
    if draft_rules.get("generate_apply_command") is not False:
        errors.append("draft_rules.generate_apply_command must be false")
    if draft_rules.get("generate_git_command") is not False:
        errors.append("draft_rules.generate_git_command must be false")
    if draft_rules.get("max_patch_targets") != 5:
        errors.append("draft_rules.max_patch_targets must be 5")
    if draft_rules.get("patch_style") != "minimal_diff":
        errors.append("draft_rules.patch_style must be minimal_diff")

    next_phase = policy.get("next_phase")
    if not isinstance(next_phase, dict):
        errors.append("next_phase must be object")
    else:
        if next_phase.get("phase") != "AB-T5":
            errors.append("next_phase.phase must be AB-T5")
        if next_phase.get("execution_allowed") is not False:
            errors.append("next_phase.execution_allowed must be false")

    return errors


def load_targets(ab_t3_result: dict[str, Any], max_targets: int) -> list[str]:
    items = ab_t3_result.get("generated_related_file_list", [])
    if not isinstance(items, list):
        return []
    targets: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str) and path:
            targets.append(path)
        if len(targets) >= max_targets:
            break
    return targets


def build_patch_draft(targets: list[str]) -> list[dict[str, Any]]:
    draft: list[dict[str, Any]] = []
    for path in targets:
        draft.append(
            {
                "target_file": path,
                "purpose": "Prepare a design-only minimal patch draft without applying changes.",
                "minimal_changes": [
                    "Keep current behavior unchanged unless required by target phase.",
                    "Limit edits to the smallest necessary block.",
                    "Avoid unrelated refactor or formatting-only churn.",
                ],
                "expected_effect": "Patch plan becomes explicit and bounded for later execution phases.",
                "potential_risk": "Over-selection may dilute patch focus if unrelated files are included.",
                "validation_items": [
                    "No apply command generated",
                    "No git command generated",
                    "No production command generated",
                    "Scope limited to design-only output",
                ],
                "no_apply_command": True,
                "no_git_command": True,
                "no_production_command": True,
            }
        )
    return draft


def build_result(policy: dict[str, Any], patch_draft: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    blocked = all(
        policy.get(key) is False
        for key in [
            "copilot_send_allowed",
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

    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if not errors and blocked else "NOT_READY"

    return {
        "phase": "AB-T4",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "draft_rules_loaded": isinstance(policy.get("draft_rules"), dict),
        "generated_patch_draft": len(patch_draft) > 0,
        "target_file_count": len(patch_draft),
        "patch_draft": patch_draft,
        "change_summary_generated": len(patch_draft) > 0,
        "risk_summary_generated": len(patch_draft) > 0,
        "validation_checklist_generated": len(patch_draft) > 0,
        "forbidden_operations_all_blocked": blocked,
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t5": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# AB-T4 Patch Draft Generator Report",
        "",
        f"- phase: {result['phase']}",
        f"- final_status: {result['final_status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- safety_state: {result['safety_state']}",
        f"- target_file_count: {result['target_file_count']}",
        f"- generated_patch_draft: {result['generated_patch_draft']}",
        f"- forbidden_operations_all_blocked: {result['forbidden_operations_all_blocked']}",
        f"- ready_for_ab_t5: {result['ready_for_ab_t5']}",
        "",
        "## Patch Draft",
    ]
    for entry in result["patch_draft"]:
        lines.extend(
            [
                f"- Target File: {entry['target_file']}",
                f"  Purpose: {entry['purpose']}",
                f"  Expected Effect: {entry['expected_effect']}",
                f"  Potential Risk: {entry['potential_risk']}",
            ]
        )

    lines.extend(
        [
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

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(policy_path: Path, ab_t3_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)
    ab_t3 = load_json(ab_t3_path)

    max_targets = int(policy.get("draft_rules", {}).get("max_patch_targets", 5) or 5)
    targets = load_targets(ab_t3, max_targets)
    patch_draft = build_patch_draft(targets)

    result = build_result(policy, patch_draft, errors)
    write_json(output_path, result)
    write_report(result, report_path)
    return result


def main() -> int:
    args = parse_args()
    result = run(Path(args.policy), Path(args.ab_t3_result), Path(args.output), Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
