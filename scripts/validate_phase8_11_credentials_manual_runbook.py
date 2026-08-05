#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNBOOK = ROOT / "docs/runbooks/phase8_11_wordpress_credentials_manual_provisioning_runbook.md"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.md"

REQUIRED_SECTIONS = [
    "## 1. Purpose",
    "## 2. Current Status",
    "## 3. Why This Runbook Exists",
    "## 4. Absolute Prohibitions",
    "## 5. Required Environment Variables",
    "## 6. Safe Manual Provisioning Guidance",
    "## 7. No-Secret-Leak Rules",
    "## 8. Operator Checklist",
    "## 9. Verification Without Revealing Values",
    "## 10. What Not To Do",
    "## 11. Expected Next Step",
    "## 12. Freeze Conditions",
    "## 13. Evidence Requirements",
    "## 14. Final Judgment",
]

REQUIRED_FIXED_STATEMENTS = [
    "RERUN_NOT_EXECUTED_CONFIRMED",
    "WordPress API must not be called in Phase 8-11.",
    "This runbook must not contain secret values.",
    "Do not write secrets into this repository.",
    "Do not create or edit .env automatically.",
    "Do not print WORDPRESS_APP_PASSWORD.",
    "Do not print credential lengths.",
    "Do not print credential prefixes or suffixes.",
    "Do not hash credentials for logging.",
    "Allowed output is exists=true/false only.",
    "HUMAN_APPROVAL_REQUIRED",
    "target_item_count",
    "publish_allowed",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
    "If any secret value is detected in logs, freeze immediately.",
]

DANGEROUS_PATTERNS = [
    r"WORDPRESS_APP_PASSWORD\s*=\s*\S",
    r"export\s+WORDPRESS_APP_PASSWORD\s*=",
    r"password\s*=\s*\S",
    r"example_password",
    r"sample_password",
    r"your_password_here",
    r"Authorization:\s*Basic",
    r"curl\s+-u\b",
    r"curl\s+-X\s+POST",
    r"requests\.post\(",
    r"wp-json/wp/v2/posts",
]

ALLOWED_ENV_SUBSTRINGS = [
    "Do not",
    "do not",
    "must not",
    "must Never",
    "must never",
    "prohibited",
    "Prohibited",
    "Do NOT",
    ".env files containing actual credentials",
    "DRY_RUN_PLACEHOLDER",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_credentials_manual_runbook(
    runbook_path: Path = DEFAULT_RUNBOOK,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    runbook_path = Path(runbook_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    if not runbook_path.exists():
        errors.append(f"runbook not found: {runbook_path}")
        status = "FAIL"
        result = _build_result(status, [], [], errors, warnings, safety_violations)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    content = runbook_path.read_text(encoding="utf-8")

    missing_sections: list[str] = []
    for section in REQUIRED_SECTIONS:
        if section not in content:
            missing_sections.append(section)

    missing_fixed: list[str] = []
    for stmt in REQUIRED_FIXED_STATEMENTS:
        if stmt not in content:
            missing_fixed.append(stmt)

    dangerous_found: list[str] = []
    for pattern in DANGEROUS_PATTERNS:
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if _is_allowed_context(line, ALLOWED_ENV_SUBSTRINGS):
                continue
            if re.search(pattern, line, re.IGNORECASE):
                dangerous_found.append(f"pattern={pattern!r} in line={line[:80]!r}")

    if dangerous_found:
        for d in dangerous_found:
            safety_violations.append(f"dangerous_pattern: {d}")
        status = "ABORT"
    elif missing_sections or missing_fixed:
        for s in missing_sections:
            errors.append(f"missing_section: {s}")
        for s in missing_fixed:
            errors.append(f"missing_fixed_statement: {s}")
        status = "FAIL"
    else:
        status = "PASS_RUNBOOK_ONLY"

    result = _build_result(status, missing_sections, missing_fixed, errors, warnings, safety_violations)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _is_allowed_context(line: str, allowed_substrings: list[str]) -> bool:
    for s in allowed_substrings:
        if s.lower() in line.lower():
            return True
    return False


def _build_result(
    status: str,
    missing_sections: list[str],
    missing_fixed: list[str],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-11",
        "status": status,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "secret_values_written": False,
        "runbook_is_execution_permission": False,
        "missing_sections": missing_sections,
        "missing_fixed_statements": missing_fixed,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": "Phase 8-12 no-secret-leak credential handling audit",
        "checked_at": _now_iso(),
    }


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-11 Credentials Manual Runbook Validation Report",
        "",
        "## Purpose",
        "Validate that the manual provisioning runbook is structurally correct and contains no dangerous patterns.",
        "",
        "## Runbook Summary",
        f"- status: {result.get('status')}",
        f"- runbook_is_execution_permission: {result.get('runbook_is_execution_permission')}",
        "",
        "## Missing Sections",
    ]
    for s in result.get("missing_sections", []):
        lines.append(f"- {s}")
    if not result.get("missing_sections"):
        lines.append("- none")

    lines.extend(["", "## Secret Leak Check"])
    for v in result.get("safety_violations", []):
        lines.append(f"- VIOLATION: {v}")
    if not result.get("safety_violations"):
        lines.append("- no dangerous patterns found")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
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


def main() -> int:
    result = validate_credentials_manual_runbook()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS_RUNBOOK_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
