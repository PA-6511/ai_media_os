#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCES = {
    "validation_result": ROOT / "exchange/logs/validation_result.json",
    "wordpress_draft_candidate_result": ROOT / "exchange/logs/wordpress_draft_candidate_result.json",
    "wordpress_draft_candidate_review_result": ROOT / "exchange/logs/wordpress_draft_candidate_review_result.json",
    "draft_candidate_approval_evidence": ROOT / "exchange/logs/draft_candidate_approval_evidence.json",
}

DEFAULT_JSON_OUTPUT = ROOT / "exchange/logs/phase5_draft_candidate_flow_completion_report.json"
DEFAULT_MD_OUTPUT = ROOT / "exchange/logs/phase5_draft_candidate_flow_completion_report.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase5_draft_candidate_flow_report_result",
        "phase": "Phase 5-6",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _validate_no_production_flags(data: dict, source_name: str) -> dict | None:
    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{source_name}: {flag}=true is forbidden")

    for flag in ["wordpress_write_executed", "slack_notification_executed", "github_actions_triggered"]:
        if data.get(flag) is True:
            return abort_result(f"{source_name}: {flag}=true is forbidden")

    safety_flags = data.get("safety_flags")
    if isinstance(safety_flags, dict):
        for flag, value in safety_flags.items():
            if value is True:
                return abort_result(f"{source_name}: safety_flags.{flag}=true is forbidden")

    return None


def _validate_sources(sources_data: dict) -> dict | None:
    evidence = sources_data["draft_candidate_approval_evidence"]

    if evidence.get("mode") != "CONNECTION_TEST":
        return abort_result("draft_candidate_approval_evidence: mode must be CONNECTION_TEST")

    if evidence.get("execution") != "DRY_RUN":
        return abort_result("draft_candidate_approval_evidence: execution must be DRY_RUN")

    if evidence.get("status") != "PASS_DRY_RUN_ONLY":
        return abort_result("draft_candidate_approval_evidence: status must be PASS_DRY_RUN_ONLY")

    if evidence.get("decision") != "APPROVE_DRY_RUN_ONLY":
        return abort_result("draft_candidate_approval_evidence: decision must be APPROVE_DRY_RUN_ONLY")

    for source_name, data in sources_data.items():
        err = _validate_no_production_flags(data, source_name)
        if err:
            return err

    return None


def _normalize_source_paths(source_paths: dict) -> dict:
    normalized = {}
    for key, path in source_paths.items():
        p = Path(path)
        if p.is_absolute():
            try:
                normalized[key] = str(p.relative_to(ROOT))
            except ValueError:
                normalized[key] = str(p)
        else:
            normalized[key] = str(p)
    return normalized


def build_json_report(sources_data: dict, source_paths: dict) -> dict:
    validation = sources_data["validation_result"]
    draft_result = sources_data["wordpress_draft_candidate_result"]
    review_result = sources_data["wordpress_draft_candidate_review_result"]
    evidence = sources_data["draft_candidate_approval_evidence"]

    return {
        "package_type": "phase5_draft_candidate_flow_completion_report",
        "phase": "Phase 5",
        "title": "WordPress Draft Candidate Flow Completion Report",
        "completion_status": "PASS_DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "summary": {
            "validation_overall_status": validation.get("overall_status"),
            "draft_candidate_result_status": draft_result.get("status"),
            "review_result_status": review_result.get("status"),
            "review_decision": review_result.get("decision"),
            "approval_evidence_status": evidence.get("status"),
            "allowed_next_step": evidence.get("allowed_next_step"),
        },
        "safety_flags": {
            "wordpress_write_executed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "github_actions_triggered": False,
            "slack_notification_executed": False,
        },
        "source_files": _normalize_source_paths(source_paths),
        "decision": {
            "result": "Phase 5 draft candidate flow is complete for DRY_RUN only.",
            "production_release": "NOT_ALLOWED",
            "next_step": "Design limited unlock policy for real draft creation or continue dry-run hardening",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown_report(report: dict) -> str:
    s = report["summary"]
    f = report["safety_flags"]

    source_rows = "\n".join(
        f"| {key} | `{value}` |" for key, value in report["source_files"].items()
    )

    return f"""# Phase 5 Draft Candidate Flow Completion Report

## Result

- Completion status: `{report['completion_status']}`
- Production status: `{report['production_status']}`
- Mode: `{report['mode']}`
- Execution: `{report['execution']}`
- Human approval required: `{report['human_approval_required']}`

## Summary

- Validation overall status: `{s.get('validation_overall_status')}`
- Draft candidate result status: `{s.get('draft_candidate_result_status')}`
- Review result status: `{s.get('review_result_status')}`
- Review decision: `{s.get('review_decision')}`
- Approval evidence status: `{s.get('approval_evidence_status')}`
- Allowed next step: `{s.get('allowed_next_step')}`

## Safety Flags

| Flag | Value |
|---|---|
| wordpress_write_executed | `{f['wordpress_write_executed']}` |
| auto_post | `{f['auto_post']}` |
| auto_update | `{f['auto_update']}` |
| auto_delete | `{f['auto_delete']}` |
| auto_export | `{f['auto_export']}` |
| github_actions_triggered | `{f['github_actions_triggered']}` |
| slack_notification_executed | `{f['slack_notification_executed']}` |

## Source Files

| Evidence | Path |
|---|---|
{source_rows}

## Final Decision

`{report['decision']['result']}`

- Production release: `{report['decision']['production_release']}`
- Next step: `{report['decision']['next_step']}`

## Important Note

This report does not authorize WordPress REST API POST/PUT/PATCH, real draft creation, publish, update, deletion, external export, GitHub Actions trigger, Slack notification execution, cron changes, or secrets access.

Created at: `{report['created_at']}`
"""


def generate_phase5_draft_candidate_flow_report(
    source_paths: dict | None = None,
    json_output: Path | None = None,
    md_output: Path | None = None,
    overwrite: bool = False,
) -> dict:
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

    validation_error = _validate_sources(sources_data)
    if validation_error:
        return validation_error

    report = build_json_report(sources_data, source_paths)
    markdown = build_markdown_report(report)

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(markdown, encoding="utf-8")

    return {
        "package_type": "phase5_draft_candidate_flow_report_result",
        "phase": "Phase 5-6",
        "status": "PASS",
        "completion_status": "PASS_DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "report_generated": True,
        "json_output": str(json_output),
        "md_output": str(md_output),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    result = generate_phase5_draft_candidate_flow_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
