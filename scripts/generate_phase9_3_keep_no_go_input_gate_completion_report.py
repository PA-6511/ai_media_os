#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange" / "logs" / "phase9_2_publish_go_redecision_input_gate_result.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange" / "logs" / "phase9_3_keep_no_go_input_gate_completion_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange" / "logs" / "phase9_3_keep_no_go_input_gate_completion_report.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase9_3_keep_no_go_input_gate_completion_report_result",
        "phase": "Phase 9-3",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_phase9_2_result(data: dict) -> dict | None:
    """Validate Phase 9-2 output to ensure KEEP_NO_GO decision and safety constraints."""
    if data.get("phase") != "Phase 9-2":
        return abort_result("input phase must be 'Phase 9-2'")
    if data.get("package_type") != "phase9_2_publish_go_redecision_input_gate_result":
        return abort_result("input package_type mismatch")
    if data.get("decision") != "KEEP_NO_GO":
        return abort_result("decision must be KEEP_NO_GO")
    if data.get("publish_candidate_unlocked_for_operator") is not False:
        return abort_result("publish_candidate_unlocked_for_operator must be false")
    if data.get("wordpress_publish_execution") != "NO_GO":
        return abort_result("wordpress_publish_execution must be NO_GO")
    if data.get("wordpress_write_executed") is not False:
        return abort_result("wordpress_write_executed must be false")
    if data.get("production_status") != "NO_GO":
        return abort_result("production_status must be NO_GO")
    
    # Verify all execution prohibition flags are in place
    if data.get("publish_allowed") is not False:
        return abort_result("publish_allowed must be false")
    if data.get("update_allowed") is not False:
        return abort_result("update_allowed must be false")
    if data.get("delete_allowed") is not False:
        return abort_result("delete_allowed must be false")
    if data.get("export_allowed") is not False:
        return abort_result("export_allowed must be false")
    if data.get("auto_post") is not False:
        return abort_result("auto_post must be false")
    if data.get("auto_update") is not False:
        return abort_result("auto_update must be false")
    if data.get("auto_delete") is not False:
        return abort_result("auto_delete must be false")
    if data.get("auto_export") is not False:
        return abort_result("auto_export must be false")
    
    if data.get("status") != "PASS":
        return abort_result("input status must be PASS")

    return None


def build_completion_checks(source: dict) -> list[dict]:
    """Build validation checks for completion report."""
    checks = [
        {
            "check": "input_phase=Phase 9-2",
            "passed": source.get("phase") == "Phase 9-2",
            "actual": source.get("phase"),
        },
        {
            "check": "input_package_type=phase9_2_publish_go_redecision_input_gate_result",
            "passed": source.get("package_type") == "phase9_2_publish_go_redecision_input_gate_result",
            "actual": source.get("package_type"),
        },
        {
            "check": "decision=KEEP_NO_GO",
            "passed": source.get("decision") == "KEEP_NO_GO",
            "actual": source.get("decision"),
        },
        {
            "check": "publish_candidate_unlocked_for_operator=false",
            "passed": source.get("publish_candidate_unlocked_for_operator") is False,
            "actual": source.get("publish_candidate_unlocked_for_operator"),
        },
        {
            "check": "wordpress_publish_execution=NO_GO",
            "passed": source.get("wordpress_publish_execution") == "NO_GO",
            "actual": source.get("wordpress_publish_execution"),
        },
        {
            "check": "wordpress_write_executed=false",
            "passed": source.get("wordpress_write_executed") is False,
            "actual": source.get("wordpress_write_executed"),
        },
        {
            "check": "publish_allowed=false",
            "passed": source.get("publish_allowed") is False,
            "actual": source.get("publish_allowed"),
        },
        {
            "check": "update_allowed=false",
            "passed": source.get("update_allowed") is False,
            "actual": source.get("update_allowed"),
        },
        {
            "check": "delete_allowed=false",
            "passed": source.get("delete_allowed") is False,
            "actual": source.get("delete_allowed"),
        },
        {
            "check": "export_allowed=false",
            "passed": source.get("export_allowed") is False,
            "actual": source.get("export_allowed"),
        },
        {
            "check": "auto_post=false",
            "passed": source.get("auto_post") is False,
            "actual": source.get("auto_post"),
        },
        {
            "check": "auto_update=false",
            "passed": source.get("auto_update") is False,
            "actual": source.get("auto_update"),
        },
        {
            "check": "auto_delete=false",
            "passed": source.get("auto_delete") is False,
            "actual": source.get("auto_delete"),
        },
        {
            "check": "auto_export=false",
            "passed": source.get("auto_export") is False,
            "actual": source.get("auto_export"),
        },
        {
            "check": "input_status=PASS",
            "passed": source.get("status") == "PASS",
            "actual": source.get("status"),
        },
    ]
    return checks


def generate_markdown_report(source: dict, input_path: Path, output_json_path: Path) -> str:
    """Generate Markdown summary of Phase 9-3 completion."""
    wordpress_draft_id = source.get("wordpress_draft_id", "N/A")
    target_draft_status = source.get("target_draft_status", "N/A")
    decision = source.get("decision", "N/A")
    reason = source.get("reason", "")
    
    md_content = f"""# Phase 9-3: KEEP_NO_GO Input Gate Completion Report

## Status Summary

- **Phase**: Phase 9-3
- **Decision**: {decision}
- **Status**: PASS
- **Generated**: {datetime.now(timezone.utc).isoformat()}

## Target Draft Information

- **WordPress Draft ID**: {wordpress_draft_id}
- **Target Draft Status**: {target_draft_status}
- **Production Status**: NO_GO

## Decision Details

### KEEP_NO_GO Confirmation

- **Decision**: {decision}
- **Publish Candidate Unlocked**: {source.get('publish_candidate_unlocked_for_operator')}
- **WordPress Publish Execution**: {source.get('wordpress_publish_execution')}
- **WordPress Write Executed**: {source.get('wordpress_write_executed')}

### Execution Prohibition Verification

All execution permissions are **FALSE** (prohibited):

- publish_allowed: {source.get('publish_allowed')}
- update_allowed: {source.get('update_allowed')}
- delete_allowed: {source.get('delete_allowed')}
- export_allowed: {source.get('export_allowed')}
- auto_post: {source.get('auto_post')}
- auto_update: {source.get('auto_update')}
- auto_delete: {source.get('auto_delete')}
- auto_export: {source.get('auto_export')}

## Input Gate Validation Results

**All 15 validation checks PASSED:**

1. ✓ Input phase = Phase 9-2
2. ✓ Input package_type = phase9_2_publish_go_redecision_input_gate_result
3. ✓ Decision = KEEP_NO_GO
4. ✓ publish_candidate_unlocked_for_operator = false
5. ✓ wordpress_publish_execution = NO_GO
6. ✓ wordpress_write_executed = false
7. ✓ publish_allowed = false
8. ✓ update_allowed = false
9. ✓ delete_allowed = false
10. ✓ export_allowed = false
11. ✓ auto_post = false
12. ✓ auto_update = false
13. ✓ auto_delete = false
14. ✓ auto_export = false
15. ✓ Input status = PASS

## Decision Rationale

{reason}

### Why KEEP_NO_GO is Maintained

The WordPress draft (ID: {wordpress_draft_id}) remains in **draft status** with all publish/update/delete/export operations **prohibited**.

**Publish candidate is NOT unlocked** for operator action. No automatic posting will occur.

## Next Steps

**maintain_no_go_or_manual_publish_go_redecision**

The draft remains protected until:
1. Manual human approval explicitly changes this decision, OR
2. A new redecision cycle is triggered with explicit GO conditions

## Files

- Input: {normalize_path(input_path)}
- Output JSON: {normalize_path(output_json_path)}
- Output Markdown: (this file)

## Timestamp

- Created: {datetime.now(timezone.utc).isoformat()}
- UTC Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
    return md_content


def generate_phase9_3_report(input_path: Path, output_json_path: Path, output_md_path: Path) -> dict:
    """Generate Phase 9-3 KEEP_NO_GO input gate completion report."""
    if not input_path.exists():
        return abort_result(f"input file not found: {input_path}")

    input_data = load_json(input_path)
    
    # Validate Phase 9-2 output
    validation_error = validate_phase9_2_result(input_data)
    if validation_error:
        return validation_error

    # Build validation checks
    checks = build_completion_checks(input_data)
    all_passed = all(check["passed"] for check in checks)

    # Generate JSON report
    report = {
        "package_type": "phase9_3_keep_no_go_input_gate_completion_report",
        "phase": "Phase 9-3",
        "title": "Phase 9-3 KEEP_NO_GO Input Gate Completion Report",
        "status": "PASS" if all_passed else "ABORT",
        "keep_no_go_completion_status": "PASS" if all_passed else "ABORT",
        "source_report": normalize_path(input_path),
        "source_report_type": "phase9_2_publish_go_redecision_input_gate_result",
        "phase9_2_decision": input_data.get("decision"),
        "wordpress_draft_id": input_data.get("wordpress_draft_id"),
        "target_draft_status": input_data.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": input_data.get("publish_candidate_unlocked_for_operator"),
        "wordpress_publish_execution": input_data.get("wordpress_publish_execution"),
        "wordpress_write_executed": input_data.get("wordpress_write_executed"),
        "production_status": input_data.get("production_status"),
        "completion_validation_checks": checks,
        "validation_passed": all_passed,
        "execution_prohibitions": {
            "publish_allowed": input_data.get("publish_allowed"),
            "update_allowed": input_data.get("update_allowed"),
            "delete_allowed": input_data.get("delete_allowed"),
            "export_allowed": input_data.get("export_allowed"),
            "auto_post": input_data.get("auto_post"),
            "auto_update": input_data.get("auto_update"),
            "auto_delete": input_data.get("auto_delete"),
            "auto_export": input_data.get("auto_export"),
        },
        "next_step": "maintain_no_go_or_manual_publish_go_redecision",
        "reason": input_data.get("reason", "KEEP_NO_GO redecision recorded; publish candidate remains locked"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write JSON report
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate and write Markdown report
    md_content = generate_markdown_report(input_data, input_path, output_json_path)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(md_content, encoding="utf-8")

    return {
        "package_type": "phase9_3_keep_no_go_input_gate_completion_report_result",
        "phase": "Phase 9-3",
        "status": "PASS",
        "keep_no_go_completion_status": "PASS",
        "report_generated": True,
        "json_output": normalize_path(output_json_path),
        "markdown_output": normalize_path(output_md_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Phase 9-3 KEEP_NO_GO input gate completion report")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input Phase 9-2 result path")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="Output JSON report path")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Output Markdown report path")
    args = parser.parse_args()

    result = generate_phase9_3_report(args.input, args.output_json, args.output_md)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
