#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCES = {
    "phase5_1_connection_config": ROOT / "config/self_builder_connection.json",
    "phase5_1_decision_schema": ROOT / "exchange/incoming/decision_package.realdata.schema.json",
    "phase5_2_validation_result": ROOT / "exchange/logs/validation_result.json",
    "phase5_3_draft_candidate_result": ROOT / "exchange/logs/wordpress_draft_candidate_result.json",
    "phase5_4_review_result": ROOT / "exchange/logs/wordpress_draft_candidate_review_result.json",
    "phase5_5_approval_evidence": ROOT / "exchange/logs/draft_candidate_approval_evidence.json",
    "phase5_6_flow_report": ROOT / "exchange/logs/phase5_draft_candidate_flow_completion_report.json",
    "phase5_7_quality_validation": ROOT / "exchange/logs/wordpress_draft_candidate_validation_result.json",
}

DEFAULT_JSON_OUTPUT = ROOT / "exchange/logs/phase5_overall_completion_report.json"
DEFAULT_MD_OUTPUT = ROOT / "exchange/logs/phase5_overall_completion_report.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase5_overall_completion_report_result",
        "phase": "Phase 5 Overall",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _check_flag_false(data: dict, source_name: str) -> dict | None:
    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{source_name}: {flag}=true is forbidden")

    for flag in ["wordpress_write_executed", "slack_notification_executed", "github_actions_triggered"]:
        if data.get(flag) is True:
            return abort_result(f"{source_name}: {flag}=true is forbidden")

    safety = data.get("safety_flags")
    if isinstance(safety, dict):
        for key, value in safety.items():
            if value is True:
                return abort_result(f"{source_name}: safety_flags.{key}=true is forbidden")

    return None


def _normalize_source_paths(source_paths: dict) -> dict:
    out = {}
    for key, path in source_paths.items():
        p = Path(path)
        if p.is_absolute():
            try:
                out[key] = str(p.relative_to(ROOT))
            except ValueError:
                out[key] = str(p)
        else:
            out[key] = str(p)
    return out


def validate_sources(sources_data: dict) -> dict | None:
    cfg = sources_data["phase5_1_connection_config"]
    schema = sources_data["phase5_1_decision_schema"]
    validation = sources_data["phase5_2_validation_result"]
    draft = sources_data["phase5_3_draft_candidate_result"]
    review = sources_data["phase5_4_review_result"]
    evidence = sources_data["phase5_5_approval_evidence"]
    flow = sources_data["phase5_6_flow_report"]
    quality = sources_data["phase5_7_quality_validation"]

    # Phase 5-1: connector safety baseline
    if cfg.get("active_connector") != "LOCAL_SELF_BUILDER":
        return abort_result("phase5_1_connection_config: active_connector must be LOCAL_SELF_BUILDER")
    if cfg.get("vps_connector_enabled") is not False:
        return abort_result("phase5_1_connection_config: vps_connector_enabled must be false")
    if str(cfg.get("execution", "")).upper() != "DRY_RUN":
        return abort_result("phase5_1_connection_config: execution must be DRY_RUN")
    if cfg.get("human_approval_required") is not True:
        return abort_result("phase5_1_connection_config: human_approval_required must be true")
    if cfg.get("auto_execute") is not False:
        return abort_result("phase5_1_connection_config: auto_execute must be false")

    # Phase 5-1: schema existence/shape sanity
    required_schema_keys = {"$schema", "title", "properties", "required"}
    if not required_schema_keys.issubset(set(schema.keys())):
        return abort_result("phase5_1_decision_schema: missing required schema keys")

    # Phase 5-2/3/4/5/6/7: mode/execution and decision status checks
    for name, data in {
        "phase5_2_validation_result": validation,
        "phase5_3_draft_candidate_result": draft,
        "phase5_4_review_result": review,
        "phase5_5_approval_evidence": evidence,
        "phase5_6_flow_report": flow,
        "phase5_7_quality_validation": quality,
    }.items():
        if data.get("mode") != "CONNECTION_TEST":
            return abort_result(f"{name}: mode must be CONNECTION_TEST")
        if data.get("execution") != "DRY_RUN":
            return abort_result(f"{name}: execution must be DRY_RUN")

    if draft.get("status") != "PASS":
        return abort_result("phase5_3_draft_candidate_result: status must be PASS")

    if review.get("decision") != "APPROVE_DRY_RUN_ONLY" or review.get("status") != "PASS":
        return abort_result("phase5_4_review_result: requires decision=APPROVE_DRY_RUN_ONLY and status=PASS")

    if evidence.get("status") != "PASS_DRY_RUN_ONLY":
        return abort_result("phase5_5_approval_evidence: status must be PASS_DRY_RUN_ONLY")

    if flow.get("completion_status") != "PASS_DRY_RUN_ONLY":
        return abort_result("phase5_6_flow_report: completion_status must be PASS_DRY_RUN_ONLY")

    if quality.get("status") not in {"PASS", "WARN"}:
        return abort_result("phase5_7_quality_validation: status must be PASS or WARN")

    # No production flags anywhere
    for source_name, data in {
        "phase5_2_validation_result": validation,
        "phase5_3_draft_candidate_result": draft,
        "phase5_4_review_result": review,
        "phase5_5_approval_evidence": evidence,
        "phase5_6_flow_report": flow,
        "phase5_7_quality_validation": quality,
    }.items():
        flag_err = _check_flag_false(data, source_name)
        if flag_err:
            return flag_err

    return None


def build_json_report(sources_data: dict, source_paths: dict) -> dict:
    quality = sources_data["phase5_7_quality_validation"]
    flow = sources_data["phase5_6_flow_report"]
    review = sources_data["phase5_4_review_result"]

    quality_status = quality.get("status")
    completion_status = "PASS_DRY_RUN_ONLY_WITH_WARN" if quality_status == "WARN" else "PASS_DRY_RUN_ONLY"

    return {
        "package_type": "phase5_overall_completion_report",
        "phase": "Phase 5",
        "title": "Phase 5 Overall Completion Report (Draft Candidate Flow)",
        "completion_status": completion_status,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "summary": {
            "phase5_6_completion_status": flow.get("completion_status"),
            "phase5_7_quality_status": quality_status,
            "phase5_7_warnings": quality.get("warnings", []),
            "review_decision": review.get("decision"),
            "review_status": review.get("status"),
        },
        "safety_flags": {
            "wordpress_write_executed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "github_actions_triggered": False,
            "slack_notification_executed": False,
            "vps_self_builder_execution_enabled": False,
        },
        "source_files": _normalize_source_paths(source_paths),
        "decision": {
            "result": "Phase 5 is complete under DRY_RUN with safety gates enforced.",
            "production_release": "NOT_ALLOWED",
            "next_step": "Phase 6 実下書き作成の限定解放設計",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown_report(report: dict) -> str:
    summary = report["summary"]
    safety = report["safety_flags"]
    source_rows = "\n".join(
        f"| {k} | `{v}` |" for k, v in report["source_files"].items()
    )
    warns = summary.get("phase5_7_warnings", [])
    warn_lines = "\n".join(f"- {w}" for w in warns) if warns else "- なし"

    return f"""# Phase 5 Overall Completion Report

## Final Status

- Completion status: `{report['completion_status']}`
- Production status: `{report['production_status']}`
- WordPress draft creation: `{report['wordpress_draft_creation']}`
- Mode: `{report['mode']}`
- Execution: `{report['execution']}`
- Human approval required: `{report['human_approval_required']}`

## Summary

- Phase 5-6 completion status: `{summary.get('phase5_6_completion_status')}`
- Phase 5-7 quality status: `{summary.get('phase5_7_quality_status')}`
- Review decision: `{summary.get('review_decision')}`
- Review status: `{summary.get('review_status')}`

Phase 5-7 warnings:
{warn_lines}

## Safety Flags

| Flag | Value |
|---|---|
| wordpress_write_executed | `{safety['wordpress_write_executed']}` |
| auto_post | `{safety['auto_post']}` |
| auto_update | `{safety['auto_update']}` |
| auto_delete | `{safety['auto_delete']}` |
| auto_export | `{safety['auto_export']}` |
| github_actions_triggered | `{safety['github_actions_triggered']}` |
| slack_notification_executed | `{safety['slack_notification_executed']}` |
| vps_self_builder_execution_enabled | `{safety['vps_self_builder_execution_enabled']}` |

## Evidence Sources

| Evidence | Path |
|---|---|
{source_rows}

## Decision

`{report['decision']['result']}`

- Production release: `{report['decision']['production_release']}`
- Next step: `{report['decision']['next_step']}`

## Important Note

This report does not authorize WordPress REST API write, real draft creation, publish, update, deletion, external export, GitHub Actions trigger, Slack notification execution, cron changes, secrets access, or VPS_SELF_BUILDER execution.

Created at: `{report['created_at']}`
"""


def generate_phase5_overall_completion_report(
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

    validation_error = validate_sources(sources_data)
    if validation_error:
        return validation_error

    report = build_json_report(sources_data, source_paths)
    markdown = build_markdown_report(report)

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(markdown, encoding="utf-8")

    return {
        "package_type": "phase5_overall_completion_report_result",
        "phase": "Phase 5 Overall",
        "status": "PASS",
        "completion_status": report["completion_status"],
        "production_status": "NO_GO",
        "report_generated": True,
        "json_output": str(json_output),
        "md_output": str(md_output),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    result = generate_phase5_overall_completion_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
