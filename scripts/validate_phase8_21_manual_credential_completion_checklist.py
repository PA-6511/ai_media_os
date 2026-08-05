#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = ROOT / "docs/runbooks/phase8_21_manual_credential_provisioning_completion_checklist.md"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_21_manual_credential_completion_checklist_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_21_manual_credential_completion_checklist_result.md"

REQUIRED_SECTIONS = [
    "## 1. Purpose",
    "## 2. Current Status",
    "## 3. Credential Provisioning Boundary",
    "## 4. What The Operator Must Confirm",
    "## 5. What Must Not Be Written",
    "## 6. No-Secret-Leak Rules",
    "## 7. Environment Variable Names",
    "## 8. Manual Completion Checklist",
    "## 9. Verification Boundary",
    "## 10. WordPress API Prohibition",
    "## 11. Rerun Boundary",
    "## 12. Freeze Conditions",
    "## 13. Evidence Requirements",
    "## 14. Final Judgment",
]

REQUIRED_FIXED_LINES = [
    "Current status: NOT_READY_FOR_RERUN_CREDENTIALS_MISSING",
    "This checklist is not execution permission.",
    "WordPress API must not be called in Phase 8-21.",
    "WordPress draft creation must not occur in Phase 8-21.",
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
    "If any secret value is detected in logs, freeze immediately.",
]

REQUIRED_ENV_NAMES = [
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_manual_credential_completion_checklist(
    checklist_path: Path = DEFAULT_CHECKLIST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    checklist_path = Path(checklist_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    missing_sections: list[str] = []
    missing_fixed_lines: list[str] = []
    forbidden_hits: list[str] = []

    if not checklist_path.exists():
        errors.append(f"missing_checklist: {checklist_path}")
        result = _build_result(
            "FAIL",
            missing_sections,
            missing_fixed_lines,
            forbidden_hits,
            errors,
            warnings,
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    content = checklist_path.read_text(encoding="utf-8")

    for section in REQUIRED_SECTIONS:
        if section not in content:
            missing_sections.append(section)

    for line in REQUIRED_FIXED_LINES:
        if line not in content:
            missing_fixed_lines.append(line)

    for name_line in REQUIRED_ENV_NAMES:
        if name_line not in content:
            missing_fixed_lines.append(name_line)

    for pattern in FORBIDDEN_PATTERNS:
        if pattern in content:
            forbidden_hits.append(pattern)

    if forbidden_hits:
        status = "ABORT"
    elif missing_sections or missing_fixed_lines:
        status = "FAIL"
    else:
        status = "PASS_CHECKLIST_ONLY"

    result = _build_result(
        status,
        missing_sections,
        missing_fixed_lines,
        forbidden_hits,
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
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-21",
        "status": status,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "checklist_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "secret_values_written": False,
        "missing_sections": missing_sections,
        "missing_fixed_lines": missing_fixed_lines,
        "forbidden_hits": forbidden_hits,
        "errors": errors,
        "warnings": warnings,
        "allowed_next_step": "Phase 8-22 credential-ready path switch validation",
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-21 Manual Credential Completion Checklist Validation Report",
        "",
        "## Purpose",
        "Validate checklist completeness and secret-safety boundaries for Phase 8-21.",
        "",
        "## Checklist Summary",
        f"- status: {result.get('status')}",
        f"- missing_sections_count: {len(result.get('missing_sections', []))}",
        f"- missing_fixed_lines_count: {len(result.get('missing_fixed_lines', []))}",
        "",
        "## Missing Sections",
    ]
    for item in result.get("missing_sections", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Secret Leak Check"])
    for hit in result.get("forbidden_hits", []):
        lines.append(f"- forbidden: {hit}")
    if not result.get("forbidden_hits"):
        lines.append("- no forbidden patterns detected")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- checklist_is_execution_permission: {result.get('checklist_is_execution_permission')}",
            f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
            f"- secret_values_written: {result.get('secret_values_written')}",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = validate_manual_credential_completion_checklist()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS_CHECKLIST_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
