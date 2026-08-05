#!/usr/bin/env python3
"""Generate Phase 9-1 runbook for GO redecision and one-time manual publish."""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUT_8_11 = LOG_DIR / "phase8_11_pre_publish_no_go_overall_completion_report.json"
OUT_RUNBOOK_JSON = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook.json"
OUT_RUNBOOK_MD = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook.md"
OUT_RESULT_JSON = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result.json"

REQUIRED_FALSE_FLAGS = [
    "publish_allowed",
    "update_allowed",
    "delete_allowed",
    "export_allowed",
    "wordpress_write_executed",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(reason: str) -> int:
    result = {
        "package_type": "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result",
        "phase": "Phase 9-1",
        "status": "ABORT",
        "reason": reason,
        "runbook_generated": False,
        "publish_execution_started": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(OUT_RESULT_JSON, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1


def _build_runbook(p811: dict) -> dict:
    target_id = p811.get("target_draft_id")
    return {
        "package_type": "phase9_1_publish_go_redecision_manual_publish_runbook",
        "phase": "Phase 9-1",
        "status": "PASS",
        "purpose": "Prepare manual-only runbook from GO redecision to one-time publish execution without executing publish in this phase",
        "phase8_overall_status": p811.get("phase8_overall_status"),
        "phase8_final_decision": p811.get("decision"),
        "target_draft_id": target_id,
        "target_draft_status": p811.get("target_draft_status"),
        "manual_publish_executable_now": False,
        "publish_execution_started": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "go_redecision_definition": {
            "decision_choices": [
                "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
                "KEEP_NO_GO",
                "REQUEST_FIX",
                "ABORT",
            ],
            "approval_token_name": "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY",
            "approval_token_required_only_when_go": True,
            "token_expiry_minutes": 30,
            "publish_count_limit": 1,
            "human_reviewer_required": True,
        },
        "fixed_manual_procedure": [
            "confirm phase8_11 status is PASS and decision is KEEP_NO_GO",
            "confirm target draft id and status are unchanged",
            "prepare manual redecision sheet with all confirmations",
            "record redecision result to exchange/human_review for phase9",
            "if decision is GO, verify token and timebox constraints",
            "prepare one-time manual publish command and operator assignment",
            "dry-run command review only; do not execute publish in phase9_1",
            "define rollback and abort criteria before any future execution",
            "define post-execution evidence list for future manual publish",
            "close phase9_1 with NO_GO maintained and runbook frozen",
        ],
        "forbidden_in_phase9_1": [
            "wordpress_publish_execute",
            "update_existing_post",
            "delete_post",
            "external_export",
            "bulk_publish",
            "cron_registration",
            "github_actions_trigger",
            "slack_production_notification",
            "vps_self_builder_execute",
            "env_or_secrets_auto_edit",
        ],
        "required_evidence_files": [
            "exchange/logs/phase8_11_pre_publish_no_go_overall_completion_report.json",
            "exchange/logs/phase9_1_publish_go_redecision_manual_publish_runbook.json",
            "exchange/logs/phase9_1_publish_go_redecision_manual_publish_runbook_generation_result.json",
        ],
        "next_step": "phase9_2_validate_go_redecision_input_and_manual_publish_gate",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _render_md(runbook: dict) -> str:
    lines = [
        "# Phase 9-1 Runbook",
        "",
        f"generated_at: {runbook['created_at']}",
        "",
        "## Status",
        "",
        f"- status: {runbook['status']}",
        f"- phase8_overall_status: {runbook['phase8_overall_status']}",
        f"- phase8_final_decision: {runbook['phase8_final_decision']}",
        f"- target_draft_id: {runbook['target_draft_id']}",
        f"- target_draft_status: {runbook['target_draft_status']}",
        f"- wordpress_publish_execution: {runbook['wordpress_publish_execution']}",
        f"- wordpress_write_executed: {runbook['wordpress_write_executed']}",
        "",
        "## GO Redecision Rules",
        "",
    ]

    rules = runbook["go_redecision_definition"]
    lines.append(f"- decision_choices: {', '.join(rules['decision_choices'])}")
    lines.append(f"- approval_token_name: {rules['approval_token_name']}")
    lines.append(f"- token_expiry_minutes: {rules['token_expiry_minutes']}")
    lines.append(f"- publish_count_limit: {rules['publish_count_limit']}")
    lines.append(f"- human_reviewer_required: {rules['human_reviewer_required']}")

    lines += ["", "## Fixed Manual Procedure", ""]
    for i, step in enumerate(runbook["fixed_manual_procedure"], start=1):
        lines.append(f"{i}. {step}")

    lines += ["", "## Forbidden In Phase 9-1", ""]
    for item in runbook["forbidden_in_phase9_1"]:
        lines.append(f"- {item}")

    lines += ["", "## Evidence Files", ""]
    for item in runbook["required_evidence_files"]:
        lines.append(f"- {item}")

    lines += ["", "## Next Step", "", runbook["next_step"], ""]
    return "\n".join(lines)


def main() -> int:
    if not INPUT_8_11.exists():
        return _abort(f"required log not found: {INPUT_8_11}")

    p811 = _load(INPUT_8_11)

    if p811.get("status") != "PASS":
        return _abort("phase8_11 status must be PASS")
    if p811.get("phase8_overall_status") != "PASS":
        return _abort("phase8_overall_status must be PASS")
    if p811.get("decision") != "KEEP_NO_GO":
        return _abort("phase8_11 decision must be KEEP_NO_GO")
    if p811.get("target_draft_id") != 110:
        return _abort("target_draft_id must be 110")
    if p811.get("target_draft_status") != "draft":
        return _abort("target_draft_status must be draft")
    if p811.get("wordpress_publish_execution") != "NO_GO":
        return _abort("phase8_11 wordpress_publish_execution must be NO_GO")

    for flag in REQUIRED_FALSE_FLAGS:
        if p811.get(flag) is not False:
            return _abort(f"phase8_11 {flag} must be false")

    runbook = _build_runbook(p811)
    _write_json(OUT_RUNBOOK_JSON, runbook)
    OUT_RUNBOOK_MD.write_text(_render_md(runbook), encoding="utf-8")

    result = {
        "package_type": "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result",
        "phase": "Phase 9-1",
        "status": "PASS",
        "reason": "phase9_1 runbook generated while maintaining no-go and no-write",
        "runbook_generated": True,
        "runbook_json": str(OUT_RUNBOOK_JSON),
        "runbook_md": str(OUT_RUNBOOK_MD),
        "phase8_reference": str(INPUT_8_11),
        "target_draft_id": runbook["target_draft_id"],
        "target_draft_status": runbook["target_draft_status"],
        "decision": "KEEP_NO_GO",
        "publish_execution_started": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "fixed_manual_procedure_count": len(runbook["fixed_manual_procedure"]),
        "forbidden_in_phase9_1_count": len(runbook["forbidden_in_phase9_1"]),
        "next_step": runbook["next_step"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(OUT_RESULT_JSON, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
