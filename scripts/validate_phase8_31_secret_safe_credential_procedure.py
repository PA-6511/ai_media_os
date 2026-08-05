#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNBOOK = ROOT / "docs/runbooks/phase8_31_secret_safe_credential_provisioning_operator_procedure.md"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_31_secret_safe_credential_procedure_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_31_secret_safe_credential_procedure_result.md"

REQUIRED_SECTIONS = [
    "## 1. Purpose",
    "## 2. Current Status",
    "## 3. Secret Handling Boundary",
    "## 4. Repository Boundary",
    "## 5. Environment Variable Names",
    "## 6. Manual Provisioning Guidance",
    "## 7. What The Operator Must Not Do",
    "## 8. Verification Without Revealing Values",
    "## 9. No API Execution In This Phase",
    "## 10. No Phase 8-6 To 8-10 Execution In This Phase",
    "## 11. Freeze Conditions",
    "## 12. Evidence Requirements",
    "## 13. Final Judgment",
    "## 14. Next Step",
]

REQUIRED_FIXED_LINES = [
    "Current status: OPERATOR_HANDOFF_BLOCKED_CREDENTIALS_MISSING",
    "This procedure is not execution permission.",
    "WordPress API must not be called in Phase 8-31.",
    "WordPress draft creation must not occur in Phase 8-31.",
    "Phase 8-6 to Phase 8-10 must not be executed in Phase 8-31.",
    "Do not write secrets into this repository.",
    "Do not create or edit .env automatically.",
    "Do not print WORDPRESS_APP_PASSWORD.",
    "Do not print credential lengths.",
    "Do not print credential prefixes or suffixes.",
    "Do not hash credentials for logging.",
    "Do not mask credential values for logging.",
    "Allowed output is exists=true/false only.",
    "HUMAN_APPROVAL_REQUIRED=true",
    "target_item_count=1",
    "publish_allowed=false",
    "auto_post=false",
    "auto_update=false",
    "auto_delete=false",
    "auto_export=false",
    "commands_executed_in_this_phase=false",
    "secret_values_written=false",
    "If any secret value is detected in logs, freeze immediately.",
]

REQUIRED_ENV_LINES = [
    "- WORDPRESS_BASE_URL",
    "- WORDPRESS_USERNAME",
    "- WORDPRESS_APP_PASSWORD",
]

FORBIDDEN_PATTERNS = [
    "WORDPRESS_APP_PASSWORD=",
    "export WORDPRESS_APP_PASSWORD=",
    "example_password",
    "sample_password",
    "your_password_here",
    "Authorization: Basic",
    "curl -u",
    "curl -X POST",
    "requests.post(",
    "wp-json/wp/v2/posts",
    "auto-edit .env",
    "automatically edit .env",
    "create .env automatically",
    "commands_executed_in_this_phase=true",
]

PHASE8_6_TO_8_10_COMMANDS = [
    "python3 scripts/validate_phase8_6_wordpress_credentials_readiness.py",
    "python3 scripts/validate_phase8_7_rerun_approval_review.py",
    "python3 scripts/validate_phase8_8_final_credentialed_live_preflight.py",
    "python3 scripts/run_phase8_9_first_one_item_wordpress_draft_create_rerun.py",
    "python3 scripts/generate_phase8_10_post_rerun_closure_report.py",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_secret_safe_credential_procedure(
    runbook_path: Path = DEFAULT_RUNBOOK,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    runbook_path = Path(runbook_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    missing_sections: list[str] = []
    missing_fixed_lines: list[str] = []
    forbidden_hits: list[str] = []
    command_boundary_violations: list[str] = []

    if not runbook_path.exists():
        errors.append(f"missing_runbook: {runbook_path}")
        result = _build_result(
            "FAIL",
            missing_sections,
            missing_fixed_lines,
            forbidden_hits,
            command_boundary_violations,
            errors,
            warnings,
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    content = runbook_path.read_text(encoding="utf-8")

    for section in REQUIRED_SECTIONS:
        if section not in content:
            missing_sections.append(section)

    for line in REQUIRED_FIXED_LINES:
        if line not in content:
            missing_fixed_lines.append(line)

    for env_line in REQUIRED_ENV_LINES:
        if env_line not in content:
            missing_fixed_lines.append(env_line)

    for pattern in FORBIDDEN_PATTERNS:
        if pattern in content:
            forbidden_hits.append(pattern)

    for cmd in PHASE8_6_TO_8_10_COMMANDS:
        if cmd in content:
            command_boundary_violations.append(cmd)

    if forbidden_hits or command_boundary_violations:
        status = "ABORT"
    elif missing_sections or missing_fixed_lines:
        status = "FAIL"
    else:
        status = "PASS_PROCEDURE_ONLY"

    result = _build_result(
        status,
        missing_sections,
        missing_fixed_lines,
        forbidden_hits,
        command_boundary_violations,
        errors,
        warnings,
    )
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    missing_sections: list[str],
    missing_fixed_lines: list[str],
    forbidden_hits: list[str],
    command_boundary_violations: list[str],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-31",
        "status": status,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "procedure_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": 1,
        "secret_values_written": False,
        "missing_sections": missing_sections,
        "missing_fixed_lines": missing_fixed_lines,
        "forbidden_hits": forbidden_hits,
        "command_boundary_violations": command_boundary_violations,
        "errors": errors,
        "warnings": warnings,
        "allowed_next_step": "Phase 8-32 provisioned declaration overlay package",
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-31 Secret-Safe Credential Procedure Validation Report",
        "",
        "## Purpose",
        "Validate secret-safe manual provisioning procedure boundaries with no execution.",
        "",
        "## Procedure Summary",
        f"- status: {result.get('status')}",
        f"- missing_sections_count: {len(result.get('missing_sections', []))}",
        f"- missing_fixed_lines_count: {len(result.get('missing_fixed_lines', []))}",
        "",
        "## Missing Sections",
    ]
    for item in result.get("missing_sections", []):
        lines.append(f"- {item}")
    if not result.get("missing_sections"):
        lines.append("- none")

    lines.extend([
        "",
        "## Secret Leak Check",
    ])
    for item in result.get("forbidden_hits", []):
        lines.append(f"- forbidden: {item}")
    if not result.get("forbidden_hits"):
        lines.append("- no forbidden secret patterns detected")

    lines.extend([
        "",
        "## Command Boundary",
    ])
    for item in result.get("command_boundary_violations", []):
        lines.append(f"- disallowed command present: {item}")
    if not result.get("command_boundary_violations"):
        lines.append("- no rerun execution commands detected")

    lines.extend([
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- procedure_is_execution_permission: {result.get('procedure_is_execution_permission')}",
        f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
        f"- phase8_6_to_8_10_executed: {result.get('phase8_6_to_8_10_executed')}",
        f"- secret_values_written: {result.get('secret_values_written')}",
        "",
        "## Final Judgment",
        f"- {result.get('status')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ])
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = validate_secret_safe_credential_procedure()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS_PROCEDURE_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
