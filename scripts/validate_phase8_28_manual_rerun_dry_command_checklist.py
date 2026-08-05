#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = ROOT / "docs/runbooks/phase8_28_manual_rerun_dry_command_checklist.md"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_28_manual_rerun_dry_command_checklist_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_28_manual_rerun_dry_command_checklist_result.md"

REQUIRED_SECTIONS = [
    "## 1. Purpose",
    "## 2. Current Status",
    "## 3. Why Commands Are Not Executed Here",
    "## 4. Required Prior Evidence",
    "## 5. Manual Rerun Command Sequence",
    "## 6. One-Time Execution Boundary",
    "## 7. WordPress API Boundary",
    "## 8. Secret Safety Rules",
    "## 9. Publish/Update/Delete Prohibitions",
    "## 10. Operator Checklist",
    "## 11. Freeze Conditions",
    "## 12. Evidence Requirements",
    "## 13. Final Judgment",
]

REQUIRED_FIXED_LINES = [
    "This checklist is not execution permission.",
    "Commands must not be executed in Phase 8-28.",
    "WordPress API must not be called in Phase 8-28.",
    "WordPress draft creation must not occur in Phase 8-28.",
    "HUMAN_APPROVAL_REQUIRED=true",
    "target_item_count=1",
    "publish_allowed=false",
    "auto_post=false",
    "auto_update=false",
    "auto_delete=false",
    "auto_export=false",
    "commands_executed_in_this_phase=false",
    "secret_values_written=false",
    "Do not print WORDPRESS_APP_PASSWORD.",
    "Do not write secrets into this repository.",
    "Do not create or edit .env automatically.",
]

ALLOWED_COMMANDS = [
    "python3 scripts/validate_phase8_6_wordpress_credentials_readiness.py",
    "python3 scripts/validate_phase8_7_rerun_approval_review.py",
    "python3 scripts/validate_phase8_8_final_credentialed_live_preflight.py",
    "python3 scripts/run_phase8_9_first_one_item_wordpress_draft_create_rerun.py",
    "python3 scripts/generate_phase8_10_post_rerun_closure_report.py",
]

FORBIDDEN_PATTERNS = [
    "curl -X POST",
    "curl -u",
    "requests.post(",
    "wp-json/wp/v2/posts",
    "export WORDPRESS_APP_PASSWORD=",
    "WORDPRESS_APP_PASSWORD=",
]

ALLOWED_CONTEXT_SUBSTRINGS = [
    "Forbidden command patterns include",
    "must not",
    "Do not",
    "do not",
    "prohibited",
    "prohibition",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_manual_rerun_dry_command_checklist(
    checklist_path: Path = DEFAULT_CHECKLIST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    checklist_path = Path(checklist_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    missing_sections: list[str] = []
    missing_fixed_lines: list[str] = []
    planned_manual_commands: list[str] = []

    if not checklist_path.exists():
        errors.append(f"missing_checklist: {checklist_path}")
        result = _build_result(
            "FAIL", planned_manual_commands, missing_sections, missing_fixed_lines, errors, warnings, safety_violations
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

    in_command_section = False
    for raw in content.splitlines():
        line = raw.strip()
        if line == "## 5. Manual Rerun Command Sequence":
            in_command_section = True
            continue
        if in_command_section and line.startswith("## "):
            in_command_section = False

        for pattern in FORBIDDEN_PATTERNS:
            if pattern in line and not _is_allowed_context(line):
                safety_violations.append(f"forbidden_command_pattern_detected: {pattern}")

        if line.startswith("- "):
            cmd = line[2:].strip().strip("`")
            if cmd.startswith("python3 "):
                if in_command_section:
                    planned_manual_commands.append(cmd)
                if cmd not in ALLOWED_COMMANDS:
                    safety_violations.append(f"command_not_allowed: {cmd}")

    allowed = set(ALLOWED_COMMANDS)
    for cmd in planned_manual_commands:
        if cmd not in allowed:
            safety_violations.append(f"command_not_allowed: {cmd}")

    if len(planned_manual_commands) != len(ALLOWED_COMMANDS):
        errors.append("manual_command_count_must_be_5")

    if "commands_executed_in_this_phase=true" in content:
        safety_violations.append("commands_executed_in_this_phase=true detected")

    secret_like = re.findall(r"(?i)(password|secret|token)\s*[:=]\s*\S+", content)
    for matched in secret_like:
        if "WORDPRESS_APP_PASSWORD=" in matched:
            safety_violations.append("secret_assignment_detected")

    if safety_violations:
        status = "ABORT"
    elif missing_sections or missing_fixed_lines:
        status = "FAIL"
    elif errors:
        status = "FAIL"
    else:
        status = "PASS_DRY_COMMAND_CHECKLIST_ONLY"

    result = _build_result(
        status, planned_manual_commands, missing_sections, missing_fixed_lines, errors, warnings, safety_violations
    )
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    planned_manual_commands: list[str],
    missing_sections: list[str],
    missing_fixed_lines: list[str],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-28",
        "status": status,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "checklist_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "target_item_count": 1,
        "secret_values_written": False,
        "planned_manual_commands": planned_manual_commands,
        "missing_sections": missing_sections,
        "missing_fixed_lines": missing_fixed_lines,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": "Phase 8-29 one-time rerun execution guard validation",
        "checked_at": _now_iso(),
    }


def _is_allowed_context(line: str) -> bool:
    lower = line.lower()
    for s in ALLOWED_CONTEXT_SUBSTRINGS:
        if s.lower() in lower:
            return True
    return False


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-28 Manual Rerun Dry Command Checklist Validation Report",
        "",
        "## Purpose",
        "Validate dry checklist structure and safety boundaries with no execution.",
        "",
        "## Checklist Summary",
        f"- status: {result.get('status')}",
        f"- missing_sections_count: {len(result.get('missing_sections', []))}",
        f"- missing_fixed_lines_count: {len(result.get('missing_fixed_lines', []))}",
        "",
        "## Command Sequence",
    ]
    for cmd in result.get("planned_manual_commands", []):
        lines.append(f"- {cmd}")
    if not result.get("planned_manual_commands"):
        lines.append("- none")

    lines.extend([
        "",
        "## Forbidden Command Check",
    ])
    for v in result.get("safety_violations", []):
        lines.append(f"- {v}")
    if not result.get("safety_violations"):
        lines.append("- no forbidden patterns detected")

    lines.extend([
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
    ])
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = validate_manual_rerun_dry_command_checklist()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS_DRY_COMMAND_CHECKLIST_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
