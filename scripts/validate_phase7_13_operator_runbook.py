#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNBOOK = ROOT / "docs/runbooks/phase7_13_first_controlled_wordpress_draft_creation_operator_runbook.md"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_13_operator_runbook_validation_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_13_operator_runbook_validation_result.md"

REQUIRED_SECTIONS = [
    "## 1. Purpose",
    "## 2. Current Status",
    "## 3. Absolute NO-GO Until Explicit Approval",
    "## 4. Required Preconditions",
    "## 5. Human Approval Requirements",
    "## 6. Allowed Scope After Future Approval",
    "## 7. Blocked Operations",
    "## 8. Single Item Execution Checklist",
    "## 9. Pre-execution Verification",
    "## 10. Execution Command Placeholder",
    "## 11. Evidence Checklist",
    "## 12. Freeze Conditions",
    "## 13. Rollback / Manual Cleanup",
    "## 14. Post-run Review",
    "## 15. Final Judgment",
    "## 16. Next Step",
]

REQUIRED_FIXED_LINES = [
    "Production status: NO_GO",
    "Current phase does not execute WordPress write.",
    "WordPress REST API POST is not allowed in Phase 7-13.",
    "APPROVE_DRAFT_CREATE_ONLY is not active in Phase 7-13.",
    "HUMAN_APPROVAL_REQUIRED=true",
    "target_item_count=1",
    "AUTO_POST=false",
    "AUTO_UPDATE=false",
    "AUTO_DELETE=false",
    "AUTO_EXPORT=false",
    "publish_allowed=false",
    "wordpress_write_executed=false",
    "wordpress_api_call_allowed=false",
    "If any mismatch is detected, immediately freeze and stop.",
    "Do not publish.",
    "Do not update existing posts.",
    "Do not delete posts.",
    "Do not run bulk execution.",
    "DRY_RUN_PLACEHOLDER_ONLY: future command must be reviewed in Phase 8 before execution.",
]

DANGEROUS_PATTERNS = [
    "AUTO_POST=true",
    "publish_allowed=true",
    "wordpress_write_executed=true",
    "wordpress_api_call_allowed=true",
    "curl -X POST",
    "requests.post(",
    "wp-json/wp/v2/posts",
    "bulk run allowed",
    "auto delete enabled",
    "auto update enabled",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_runbook(
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
    missing_required_lines: list[str] = []
    dangerous_hits: list[str] = []

    if not runbook_path.exists():
        errors.append(f"missing_runbook: {runbook_path}")
        content = ""
    else:
        content = runbook_path.read_text(encoding="utf-8")

    for section in REQUIRED_SECTIONS:
        if section not in content:
            missing_sections.append(section)

    for line in REQUIRED_FIXED_LINES:
        if line not in content:
            missing_required_lines.append(line)

    for pattern in DANGEROUS_PATTERNS:
        if pattern in content:
            dangerous_hits.append(pattern)

    if dangerous_hits:
        status = "ABORT"
    elif missing_sections or missing_required_lines or errors:
        status = "FAIL"
    else:
        status = "PASS_RUNBOOK_ONLY"

    try:
        runbook_path_display = str(runbook_path.relative_to(ROOT))
    except ValueError:
        runbook_path_display = str(runbook_path)

    result = {
        "phase": "Phase 7-13",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "runbook_is_execution_permission": False,
        "runbook_path": runbook_path_display,
        "missing_sections": missing_sections,
        "missing_required_lines": missing_required_lines,
        "dangerous_hits": dangerous_hits,
        "errors": errors,
        "warnings": warnings,
        "allowed_next_step": "Phase 7-14 pre-live unlock final freeze/go report",
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-13 Operator Runbook Validation Report",
        "",
        "## Purpose",
        "- Validate operator runbook completeness while keeping write operations blocked.",
        "",
        "## Runbook Summary",
        f"- runbook_path: {result.get('runbook_path')}",
        f"- status: {result.get('status')}",
        "",
        "## Missing Sections",
    ]
    if result.get("missing_sections"):
        for section in result["missing_sections"]:
            lines.append(f"- {section}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
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
    result = validate_runbook()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_RUNBOOK_ONLY", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
