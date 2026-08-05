#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_limited_test_selector_policy.json"
DEFAULT_AB_T4_RESULT = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t5_limited_test_selector_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "test_selection_rules",
    "allowed_test_command_patterns",
    "forbidden_test_command_patterns",
    "output_mode",
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

REQUIRED_RULES = {
    "max_test_commands",
    "prefer_targeted_pytest",
    "prefer_json_tool_for_policy",
    "prefer_py_compile_for_scripts",
    "allow_full_pytest",
    "allow_network_tests",
    "allow_production_tests",
    "allow_wordpress_tests",
    "allow_credential_tests",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--ab-t4-result", default=str(DEFAULT_AB_T4_RESULT))
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

    if policy.get("phase") != "AB-T5":
        errors.append("phase must be AB-T5")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "limited_test_selector":
        errors.append("purpose must be limited_test_selector")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")

    rules = policy.get("test_selection_rules")
    if not isinstance(rules, dict):
        errors.append("test_selection_rules must be object")
    else:
        missing_rules = sorted(REQUIRED_RULES - set(rules.keys()))
        if missing_rules:
            errors.append(f"missing test_selection_rules keys: {missing_rules}")

        if rules.get("max_test_commands") != 3:
            errors.append("test_selection_rules.max_test_commands must be 3")
        for key in [
            "allow_full_pytest",
            "allow_network_tests",
            "allow_production_tests",
            "allow_wordpress_tests",
            "allow_credential_tests",
        ]:
            if rules.get(key) is not False:
                errors.append(f"test_selection_rules.{key} must be false")

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

    next_phase = policy.get("next_phase")
    if not isinstance(next_phase, dict):
        errors.append("next_phase must be object")
    else:
        if next_phase.get("phase") != "AB-T6":
            errors.append("next_phase.phase must be AB-T6")
        if next_phase.get("execution_allowed") is not False:
            errors.append("next_phase.execution_allowed must be false")

    return errors


def pick_target_files(ab_t4_result: dict[str, Any], limit: int) -> list[str]:
    patch_draft = ab_t4_result.get("patch_draft", [])
    files: list[str] = []
    if isinstance(patch_draft, list):
        for item in patch_draft:
            if not isinstance(item, dict):
                continue
            path = item.get("target_file")
            if isinstance(path, str) and path:
                files.append(path)
            if len(files) >= limit:
                break
    return files


def derive_test_file(target_files: list[str]) -> str:
    for path in target_files:
        p = Path(path)
        if p.parts and p.parts[0] == "scripts" and p.suffix == ".py":
            return f"tests/test_{p.stem}.py"
        if p.parts and p.parts[0] == "tests" and p.name.startswith("test_"):
            return path
    return "tests/test_build_auto_builder_patch_draft_generator.py"


def build_limited_commands(target_files: list[str], policy_file: str, script_file: str, max_commands: int) -> list[str]:
    commands: list[str] = [
        f"python3 -m json.tool {policy_file} >/dev/null",
        f"python3 -m py_compile {script_file}",
        f"pytest -q {derive_test_file(target_files)}",
    ]
    return commands[:max_commands]


def build_result(policy: dict[str, Any], target_files: list[str], commands: list[str], errors: list[str]) -> dict[str, Any]:
    rules = policy["test_selection_rules"]
    selected_count = len(commands)

    full_pytest_blocked = rules.get("allow_full_pytest") is False
    network_tests_blocked = rules.get("allow_network_tests") is False
    wordpress_tests_blocked = rules.get("allow_wordpress_tests") is False
    credential_tests_blocked = rules.get("allow_credential_tests") is False
    git_operations_blocked = policy.get("git_commit_allowed") is False and policy.get("git_push_allowed") is False

    forbidden_operations_all_blocked = all(
        [
            policy.get("copilot_send_allowed") is False,
            policy.get("external_api_call_allowed") is False,
            policy.get("wordpress_api_call_allowed") is False,
            policy.get("credential_read_allowed") is False,
            policy.get("credential_output_allowed") is False,
            policy.get("production_write_allowed") is False,
            policy.get("destructive_operation_allowed") is False,
            git_operations_blocked,
            full_pytest_blocked,
            network_tests_blocked,
            wordpress_tests_blocked,
            credential_tests_blocked,
        ]
    )

    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if not errors and selected_count <= 3 and forbidden_operations_all_blocked else "NOT_READY"

    limited_test_plan = {
        "target_files": target_files,
        "selected_tests": commands,
        "why_these_tests": "Policy json validation, script compile validation, and one targeted pytest only.",
        "blocked_commands": [
            "full pytest sweep",
            "network commands",
            "wordpress commands",
            "credential/env reads",
            "git commit/push",
        ],
        "safety_confirmation": {
            "no_full_pytest": True,
            "no_network": True,
            "no_wordpress": True,
            "no_credential_read": True,
            "no_git_operation": True,
        },
    }

    return {
        "phase": "AB-T5",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "test_selection_rules_loaded": isinstance(policy.get("test_selection_rules"), dict),
        "limited_test_plan_generated": True,
        "target_test_files": [derive_test_file(target_files)],
        "selected_test_commands": commands,
        "selected_test_command_count": selected_count,
        "full_pytest_blocked": full_pytest_blocked,
        "network_tests_blocked": network_tests_blocked,
        "wordpress_tests_blocked": wordpress_tests_blocked,
        "credential_tests_blocked": credential_tests_blocked,
        "git_operations_blocked": git_operations_blocked,
        "forbidden_operations_all_blocked": forbidden_operations_all_blocked,
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t6": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "limited_test_plan": limited_test_plan,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    plan = result["limited_test_plan"]
    lines = [
        "# AB-T5 Limited Test Selector Report",
        "",
        f"- phase: {result['phase']}",
        f"- final_status: {result['final_status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- safety_state: {result['safety_state']}",
        f"- selected_test_command_count: {result['selected_test_command_count']}",
        f"- ready_for_ab_t6: {result['ready_for_ab_t6']}",
        "",
        "## Limited Test Plan",
        "- Target Files:",
    ]
    lines.extend(f"  - {item}" for item in plan["target_files"])
    lines.append("- Selected Tests:")
    lines.extend(f"  - {item}" for item in plan["selected_tests"])
    lines.append(f"- Why These Tests: {plan['why_these_tests']}")
    lines.append("- Blocked Commands:")
    lines.extend(f"  - {item}" for item in plan["blocked_commands"])
    lines.append("- Safety Confirmation:")
    lines.append(f"  - No Full Pytest: {plan['safety_confirmation']['no_full_pytest']}")
    lines.append(f"  - No Network: {plan['safety_confirmation']['no_network']}")
    lines.append(f"  - No WordPress: {plan['safety_confirmation']['no_wordpress']}")
    lines.append(f"  - No Credential Read: {plan['safety_confirmation']['no_credential_read']}")
    lines.append(f"  - No Git Operation: {plan['safety_confirmation']['no_git_operation']}")
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

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run(policy_path: Path, ab_t4_result_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)
    ab_t4 = load_json(ab_t4_result_path)

    max_cmd = int(policy.get("test_selection_rules", {}).get("max_test_commands", 3) or 3)
    target_files = pick_target_files(ab_t4, limit=5)
    commands = build_limited_commands(
        target_files=target_files,
        policy_file="config/auto_builder_limited_test_selector_policy.json",
        script_file="scripts/select_auto_builder_limited_tests.py",
        max_commands=max_cmd,
    )

    result = build_result(policy, target_files, commands, errors)
    write_json(output_path, result)
    write_report(result, report_path)
    return result


def main() -> int:
    args = parse_args()
    result = run(Path(args.policy), Path(args.ab_t4_result), Path(args.output), Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
