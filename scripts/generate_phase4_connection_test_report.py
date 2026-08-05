#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCES = {
    "validation_result": ROOT / "exchange/logs/validation_result.json",
    "review_required": ROOT / "exchange/human_review/review_required.json",
    "human_decision_result": ROOT / "exchange/logs/human_decision_result.json",
    "dry_run_approval_evidence": ROOT / "exchange/logs/dry_run_approval_evidence.json",
}

DEFAULT_JSON_OUTPUT = ROOT / "exchange/logs/phase4_connection_test_completion_report.json"
DEFAULT_MD_OUTPUT = ROOT / "exchange/logs/phase4_connection_test_completion_report.md"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str):
    return {
        "package_type": "phase4_connection_test_completion_report_result",
        "phase": "Phase 4 Completion Report",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_no_production_flags(data: dict, source_name: str):
    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{source_name}: {flag}=true is forbidden")

    for flag in [
        "wordpress_write_executed",
        "slack_notification_executed",
        "github_actions_triggered",
    ]:
        if data.get(flag) is True:
            return abort_result(f"{source_name}: {flag}=true is forbidden")

    return None


def validate_sources(sources_data: dict):
    evidence = sources_data["dry_run_approval_evidence"]

    if evidence.get("mode") != "CONNECTION_TEST":
        return abort_result("dry_run_approval_evidence: mode must be CONNECTION_TEST")

    if evidence.get("execution") != "DRY_RUN":
        return abort_result("dry_run_approval_evidence: execution must be DRY_RUN")

    if evidence.get("status") != "PASS":
        return abort_result("dry_run_approval_evidence: status must be PASS")

    if evidence.get("decision") != "APPROVE_DRY_RUN_ONLY":
        return abort_result("dry_run_approval_evidence: decision must be APPROVE_DRY_RUN_ONLY")

    for source_name, data in sources_data.items():
        flag_error = validate_no_production_flags(data, source_name)
        if flag_error:
            return flag_error

        safety_flags = data.get("safety_flags")
        if isinstance(safety_flags, dict):
            for flag, value in safety_flags.items():
                if value is True:
                    return abort_result(f"{source_name}: safety_flags.{flag}=true is forbidden")

    return {
        "status": "PASS",
        "reason": "all Phase 4 evidence files are safe for completion report",
    }


def build_json_report(sources_data: dict, source_paths: dict):
    validation = sources_data["validation_result"]
    human_decision = sources_data["human_decision_result"]
    evidence = sources_data["dry_run_approval_evidence"]

    source_files = {}
    for key, path in source_paths.items():
        p = Path(path)
        if p.is_absolute():
            try:
                source_files[key] = str(p.relative_to(ROOT))
            except ValueError:
                source_files[key] = str(p)
        else:
            source_files[key] = str(p)

    return {
        "package_type": "phase4_connection_test_completion_report",
        "phase": "Phase 4",
        "title": "Local Self-Builder x Ebook Affiliate Block AI Connection Test Completion Report",
        "completion_status": "PASS_DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "summary": {
            "validation_overall_status": validation.get("overall_status"),
            "human_decision": human_decision.get("decision"),
            "human_decision_status": human_decision.get("status"),
            "dry_run_evidence_status": evidence.get("status"),
            "allowed_next_step": evidence.get("allowed_next_step"),
        },
        "safety_flags": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_write_executed": False,
            "slack_notification_executed": False,
            "github_actions_triggered": False,
        },
        "source_files": source_files,
        "decision": {
            "result": "Phase 4 connection test is complete for DRY_RUN only.",
            "production_release": "NOT_ALLOWED",
            "next_step": "Phase 5 planning or additional dry-run hardening",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown_report(report: dict):
    safety = report["safety_flags"]
    summary = report["summary"]

    source_rows = "\n".join(
        f"| {key} | `{value}` |" for key, value in report["source_files"].items()
    )

    return f"""# Phase 4 Connection Test Completion Report

## Result

- Completion status: `{report['completion_status']}`
- Production status: `{report['production_status']}`
- Mode: `{report['mode']}`
- Execution: `{report['execution']}`
- Human approval required: `{report['human_approval_required']}`

## Summary

- Validation overall status: `{summary.get('validation_overall_status')}`
- Human decision: `{summary.get('human_decision')}`
- Human decision status: `{summary.get('human_decision_status')}`
- DRY_RUN evidence status: `{summary.get('dry_run_evidence_status')}`
- Allowed next step: `{summary.get('allowed_next_step')}`

## Safety Flags

| Flag | Value |
|---|---|
| auto_post | `{safety['auto_post']}` |
| auto_update | `{safety['auto_update']}` |
| auto_delete | `{safety['auto_delete']}` |
| auto_export | `{safety['auto_export']}` |
| wordpress_write_executed | `{safety['wordpress_write_executed']}` |
| slack_notification_executed | `{safety['slack_notification_executed']}` |
| github_actions_triggered | `{safety['github_actions_triggered']}` |

## Source Files

| Evidence | Path |
|---|---|
{source_rows}

## Final Decision

`{report['decision']['result']}`

- Production release: `{report['decision']['production_release']}`
- Next step: `{report['decision']['next_step']}`

## Important Note

This report does not authorize production posting, production updates, article deletion, external export, GitHub Actions triggering, Slack notification execution, cron changes, or secrets access.

Created at: `{report['created_at']}`
"""


def generate_phase4_connection_test_report(
    source_paths=None,
    json_output=None,
    md_output=None,
    overwrite=False,
):
    source_paths = source_paths or DEFAULT_SOURCES
    json_output = Path(json_output or DEFAULT_JSON_OUTPUT)
    md_output = Path(md_output or DEFAULT_MD_OUTPUT)

    if json_output.exists() and not overwrite:
        return abort_result(f"JSON report already exists: {json_output}")

    if md_output.exists() and not overwrite:
        return abort_result(f"Markdown report already exists: {md_output}")

    sources_data = {}
    for key, path in source_paths.items():
        p = Path(path)
        if not p.exists():
            return abort_result(f"required evidence file not found: {p}")
        sources_data[key] = load_json(p)

    validation = validate_sources(sources_data)
    if validation["status"] == "ABORT":
        return validation

    report = build_json_report(sources_data, source_paths)
    markdown = build_markdown_report(report)

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(markdown, encoding="utf-8")

    return {
        "package_type": "phase4_connection_test_completion_report_result",
        "phase": "Phase 4 Completion Report",
        "status": "PASS",
        "completion_status": "PASS_DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "report_generated": True,
        "json_output": str(json_output),
        "md_output": str(md_output),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    result = generate_phase4_connection_test_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
