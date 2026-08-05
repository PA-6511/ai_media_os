#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/logs/human_decision_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/dry_run_approval_evidence.json"

SOURCE_FILES = {
    "validation_result": "exchange/logs/validation_result.json",
    "review_required": "exchange/human_review/review_required.json",
    "human_decision_result": "exchange/logs/human_decision_result.json",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str):
    return {
        "package_type": "dry_run_approval_evidence_result",
        "phase": "Phase 4-7",
        "status": "ABORT",
        "reason": reason,
        "evidence_generated": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_human_decision_result(data: dict):
    if data.get("mode") != "CONNECTION_TEST":
        return abort_result("mode must be CONNECTION_TEST")

    if data.get("execution") != "DRY_RUN":
        return abort_result("execution must be DRY_RUN")

    if data.get("human_approval_required") is not True:
        return abort_result("human_approval_required must be true")

    if data.get("decision") != "APPROVE_DRY_RUN_ONLY":
        return abort_result("decision must be APPROVE_DRY_RUN_ONLY")

    if data.get("status") != "PASS":
        return abort_result("status must be PASS")

    if data.get("next_step") != "record_dry_run_evidence":
        return abort_result("next_step must be record_dry_run_evidence")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden")

    for flag in [
        "wordpress_write_executed",
        "slack_notification_executed",
        "github_actions_triggered",
    ]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden in DRY_RUN")

    return {
        "status": "PASS",
        "reason": "human decision result is safe for DRY_RUN evidence recording",
    }


def build_evidence(data: dict):
    return {
        "package_type": "dry_run_approval_evidence",
        "phase": "Phase 4-7",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "status": "PASS",
        "decision": data.get("decision"),
        "decision_status": data.get("status"),
        "decision_next_step": data.get("next_step"),
        "summary": "DRY_RUN接続試験としてのみ承認。本文番反映・投稿・更新・削除・外部出力は未許可。",
        "source_files": SOURCE_FILES,
        "safety_flags": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_write_executed": False,
            "slack_notification_executed": False,
            "github_actions_triggered": False,
        },
        "allowed_next_step": "record_only_no_production_action",
        "forbidden_actions": [
            "wordpress_production_post",
            "wordpress_production_update",
            "article_delete",
            "external_export",
            "github_actions_trigger",
            "slack_notification",
            "cron_change",
            "env_or_secret_access",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def record_dry_run_approval_evidence(input_path=None, output_path=None, overwrite=False):
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        return abort_result(f"human_decision_result not found: {input_path}")

    if output_path.exists() and not overwrite:
        return abort_result(f"dry_run_approval_evidence already exists: {output_path}")

    data = load_json(input_path)
    validation = validate_human_decision_result(data)
    if validation["status"] == "ABORT":
        return validation

    evidence = build_evidence(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "package_type": "dry_run_approval_evidence_result",
        "phase": "Phase 4-7",
        "status": "PASS",
        "reason": "dry_run_approval_evidence.json generated",
        "evidence_generated": True,
        "output_path": str(output_path),
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    result = record_dry_run_approval_evidence()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
