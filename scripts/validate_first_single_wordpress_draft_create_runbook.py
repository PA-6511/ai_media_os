#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs/runbooks/first_single_wordpress_draft_create_runbook.md"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_8_runbook_validation_result.json"

REQUIRED_SECTIONS = [
    "## 1. Purpose",
    "## 2. Current Status",
    "## 3. Absolute NO-GO",
    "## 4. Required Preconditions",
    "## 5. GO Conditions",
    "## 6. NO-GO Conditions",
    "## 7. Execution Scope",
    "## 8. Operator Checklist",
    "## 9. Evidence Checklist",
    "## 10. Freeze / Rollback",
    "## 11. Post-run Review",
    "## 12. Next Step",
]

REQUIRED_FIXED_LINES = [
    "Production status: NO_GO",
    "Current phase does not allow WordPress write execution.",
    "AUTO_POST=false",
    "AUTO_UPDATE=false",
    "AUTO_DELETE=false",
    "AUTO_EXPORT=false",
    "HUMAN_APPROVAL_REQUIRED=true",
    "execution=DRY_RUN",
    "publish_allowed=false",
    "wordpress_write_executed=false",
    "max_items=1",
    "APPROVE_DRAFT_CREATE_ONLY is reserved for future controlled unlock only.",
    "If any mismatch is detected, immediately freeze and stop.",
]

REQUIRED_PRECONDITIONS_LINES = [
    "Phase 6-5 execution spec PASS",
    "Phase 6-6 quality gate PASS or acceptable WARN reviewed by human",
    "Phase 6-7 Slack approval DRY_RUN PASS",
    "Phase 6-9 preflight gate PASS",
    "Target item count equals 1",
    "Duplicate check passed",
    "PR notice exists",
    "CTA URL exists",
    "affiliate link uses https",
    "rollback/freeze path exists",
    "human approval evidence exists",
]

REQUIRED_SCOPE_LINES = [
    "Only one item",
    "Draft creation only in future unlock",
    "No publish",
    "No update",
    "No delete",
    "No export",
    "No bulk run",
    "No retry storm",
    "No automatic escalation",
]

REQUIRED_FREEZE_LINES = [
    "freeze flag を立てる",
    "Slack通知はDRY_RUNまたは手動",
    "証跡JSONを保存",
    "該当候補を再実行不可にする",
    "人間レビューまで停止",
]

DANGEROUS_PHRASES = [
    "AUTO_POST=true",
    "publish_allowed=true",
    "wordpress_write_executed=true",
    "bulk run allowed",
    "auto delete enabled",
    "auto update enabled",
]


def validate_runbook_text(text: str) -> dict:
    errors = []

    if "# Phase 6-8 初回1件限定 WordPress実下書き作成ランブック" not in text:
        errors.append("missing required title")

    for item in REQUIRED_SECTIONS:
        if item not in text:
            errors.append(f"missing required section: {item}")

    for item in REQUIRED_FIXED_LINES:
        if item not in text:
            errors.append(f"missing required fixed line: {item}")

    for item in REQUIRED_PRECONDITIONS_LINES:
        if item not in text:
            errors.append(f"missing Required Preconditions entry: {item}")

    for item in REQUIRED_SCOPE_LINES:
        if item not in text:
            errors.append(f"missing Execution Scope entry: {item}")

    for item in REQUIRED_FREEZE_LINES:
        if item not in text:
            errors.append(f"missing Freeze / Rollback entry: {item}")

    lower = text.lower()
    for phrase in DANGEROUS_PHRASES:
        if phrase.lower() in lower:
            return {
                "phase": "Phase 6-8",
                "status": "ABORT",
                "errors": [f"dangerous phrase detected: {phrase}"],
                "warnings": [],
                "next_step": "remove_dangerous_phrase"
            }

    status = "PASS_DRY_RUN_ONLY" if not errors else "FAIL"
    return {
        "phase": "Phase 6-8",
        "status": status,
        "errors": errors,
        "warnings": [],
        "next_step": "phase6_9_hardening_preflight" if status == "PASS_DRY_RUN_ONLY" else "fix_runbook_content"
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = {
            "phase": "Phase 6-8",
            "status": "FAIL",
            "errors": [f"runbook not found: {input_path}"],
            "warnings": [],
            "next_step": "create_runbook"
        }
    else:
        result = validate_runbook_text(input_path.read_text(encoding="utf-8"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS_DRY_RUN_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
