#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_copilot_prompt_compression_policy.json"
DEFAULT_RESULT = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t2_copilot_prompt_compression_report.md"

REQUIRED_KEYS = {
    "phase",
    "status",
    "purpose",
    "max_files_per_ai_context",
    "max_lines_per_file_excerpt",
    "copilot_agent_default_allowed",
    "external_api_call_allowed",
    "credential_read_allowed",
    "credential_output_allowed",
    "wordpress_write_allowed",
    "production_write_allowed",
    "destructive_operation_allowed",
    "execution_mode",
    "production_status",
    "safety_state",
    "output_mode",
    "allowed_outputs",
    "forbidden_outputs",
    "next_phase",
}

REQUIRED_ALLOWED_OUTPUTS = [
    "compressed_prompt_template",
    "target_file_list",
    "bounded_diff_instruction",
    "limited_pytest_instruction",
    "safety_constraints_summary",
]

REQUIRED_FORBIDDEN_OUTPUTS = [
    "secret_values",
    "credential_env_contents",
    "live_api_payload",
    "production_execution_command",
    "wordpress_publish_command",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--output", default=str(DEFAULT_RESULT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_prompt_template(max_files: int, max_lines: int, relevant_files: list[str]) -> str:
    lines = [
        "---",
        "Task:",
        "Implement only the smallest safe design-only patch for the requested phase.",
        "",
        "Context Budget:",
        f"- Max files: {max_files}",
        f"- Max lines per file excerpt: {max_lines}",
        "",
        "Safety Constraints:",
        "- DRY_RUN only",
        "- NO_GO production status",
        "- No WordPress write",
        "- No credential read/output",
        "- No external API call",
        "- No destructive operation",
        "",
        "Relevant Files:",
    ]
    lines.extend(f"- {item}" for item in relevant_files)
    lines.extend(
        [
            "",
            "Instructions:",
            "- Use minimal diff only",
            "- Do not refactor unrelated code",
            "- Do not modify production execution gates",
            "- Do not read or output secrets",
            "- Return patch proposal only",
            "- Include limited pytest command suggestion",
            "",
            "Expected Output:",
            "- Changed files",
            "- Patch summary",
            "- Safety confirmation",
            "- Suggested limited tests",
            "---",
        ]
    )
    return "\n".join(lines)


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(policy.keys()))
    if missing:
        errors.append(f"missing required keys: {missing}")

    if policy.get("phase") != "AB-T2":
        errors.append("phase must be AB-T2")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "copilot_prompt_context_compression_gate":
        errors.append("purpose mismatch")

    if policy.get("max_files_per_ai_context") != 5:
        errors.append("max_files_per_ai_context must be 5")
    if policy.get("max_lines_per_file_excerpt") != 120:
        errors.append("max_lines_per_file_excerpt must be 120")

    for key in [
        "copilot_agent_default_allowed",
        "external_api_call_allowed",
        "credential_read_allowed",
        "credential_output_allowed",
        "wordpress_write_allowed",
        "production_write_allowed",
        "destructive_operation_allowed",
    ]:
        if policy.get(key) is not False:
            errors.append(f"{key} must be false")

    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")
    if policy.get("output_mode") != "PROMPT_TEMPLATE_ONLY":
        errors.append("output_mode must be PROMPT_TEMPLATE_ONLY")

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
        if next_phase.get("phase") != "AB-T3":
            errors.append("next_phase.phase must be AB-T3")
        if next_phase.get("execution_allowed") is not False:
            errors.append("next_phase.execution_allowed must be false")

    return errors


def build_result(policy: dict[str, Any], prompt_template: str, errors: list[str]) -> dict[str, Any]:
    forbidden_operations_all_blocked = all(
        policy.get(key) is False
        for key in [
            "copilot_agent_default_allowed",
            "external_api_call_allowed",
            "credential_read_allowed",
            "credential_output_allowed",
            "wordpress_write_allowed",
            "production_write_allowed",
            "destructive_operation_allowed",
        ]
    )

    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if not errors and forbidden_operations_all_blocked else "NOT_READY"
    relevant_files = [
        "config/auto_builder_copilot_prompt_compression_policy.json",
        "scripts/build_auto_builder_copilot_prompt_compression.py",
        "tests/test_build_auto_builder_copilot_prompt_compression.py",
        "scripts/validate_auto_builder_token_efficiency_policy.py",
        "scripts/validate_auto_builder_token_budget_and_snapshot_digest.py",
    ]

    return {
        "phase": "AB-T2",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "max_files_per_ai_context": policy.get("max_files_per_ai_context"),
        "max_lines_per_file_excerpt": policy.get("max_lines_per_file_excerpt"),
        "generated_prompt_template_exists": bool(prompt_template.strip()),
        "forbidden_operations_all_blocked": forbidden_operations_all_blocked,
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t3": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "target_file_list": relevant_files,
        "bounded_diff_instruction": "Use minimal diff only and avoid unrelated refactors.",
        "limited_pytest_instruction": "pytest -q tests/test_build_auto_builder_copilot_prompt_compression.py",
        "compressed_prompt_template": prompt_template,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# AB-T2 Copilot Prompt Compression Report",
        "",
        f"- phase: {result['phase']}",
        f"- final_status: {result['final_status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- safety_state: {result['safety_state']}",
        f"- max_files_per_ai_context: {result['max_files_per_ai_context']}",
        f"- max_lines_per_file_excerpt: {result['max_lines_per_file_excerpt']}",
        f"- generated_prompt_template_exists: {result['generated_prompt_template_exists']}",
        f"- forbidden_operations_all_blocked: {result['forbidden_operations_all_blocked']}",
        f"- ready_for_ab_t3: {result['ready_for_ab_t3']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase'].get('phase')}",
        f"- name: {result['next_phase'].get('name')}",
        f"- execution_allowed: {result['next_phase'].get('execution_allowed')}",
        "",
        "## Prompt Template",
        "```text",
        result["compressed_prompt_template"],
        "```",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(policy_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)

    relevant_files = [
        "config/auto_builder_copilot_prompt_compression_policy.json",
        "scripts/build_auto_builder_copilot_prompt_compression.py",
        "tests/test_build_auto_builder_copilot_prompt_compression.py",
        "scripts/validate_auto_builder_token_efficiency_policy.py",
        "scripts/validate_auto_builder_token_budget_and_snapshot_digest.py",
        "tests/test_validate_auto_builder_token_budget_and_snapshot_digest.py",
    ]
    max_files = int(policy.get("max_files_per_ai_context", 5) or 5)
    bounded_files = relevant_files[:max_files]

    prompt_template = build_prompt_template(
        max_files=max_files,
        max_lines=int(policy.get("max_lines_per_file_excerpt", 120) or 120),
        relevant_files=bounded_files,
    )

    result = build_result(policy, prompt_template, errors)
    write_json(output_path, result)
    write_report(result, report_path)
    return result


def main() -> int:
    args = parse_args()
    result = run(Path(args.policy), Path(args.output), Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
