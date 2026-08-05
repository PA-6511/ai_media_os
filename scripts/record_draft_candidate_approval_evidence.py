#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/logs/wordpress_draft_candidate_review_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/draft_candidate_approval_evidence.json"

SOURCE_FILES = {
    "draft_candidate": "exchange/outgoing/wordpress_draft_candidate.example.json",
    "draft_candidate_review": "exchange/human_review/wordpress_draft_candidate_review.example.json",
    "draft_candidate_review_result": "exchange/logs/wordpress_draft_candidate_review_result.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str) -> dict:
    return {
        "package_type": "draft_candidate_approval_evidence_result",
        "phase": "Phase 5-5",
        "status": "ABORT",
        "reason": reason,
        "evidence_generated": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_review_result(data: dict) -> dict | None:
    if data.get("mode") != "CONNECTION_TEST":
        return abort_result("mode must be CONNECTION_TEST")

    if data.get("execution") != "DRY_RUN":
        return abort_result("execution must be DRY_RUN")

    if data.get("human_approval_required") is not True:
        return abort_result("human_approval_required must be true")

    if data.get("status") != "PASS":
        return abort_result("status must be PASS")

    if data.get("decision") != "APPROVE_DRY_RUN_ONLY":
        return abort_result("decision must be APPROVE_DRY_RUN_ONLY")

    if data.get("next_step") != "record_draft_candidate_approval_evidence":
        return abort_result("next_step must be record_draft_candidate_approval_evidence")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden")

    for flag in ["wordpress_write_executed", "slack_notification_executed", "github_actions_triggered"]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden in DRY_RUN")

    return None


def build_evidence(data: dict) -> dict:
    return {
        "package_type": "draft_candidate_approval_evidence",
        "phase": "Phase 5-5",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "status": "PASS_DRY_RUN_ONLY",
        "decision": data.get("decision"),
        "review_status": data.get("status"),
        "review_next_step": data.get("next_step"),
        "summary": "WordPress下書き候補の承認証跡。実下書き作成・投稿・更新・削除・Exportは未許可。",
        "source_files": SOURCE_FILES,
        "safety_flags": {
            "wordpress_write_executed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "github_actions_triggered": False,
            "slack_notification_executed": False,
        },
        "allowed_next_step": "record_only_no_wordpress_write",
        "forbidden_actions": [
            "wordpress_rest_post",
            "wordpress_rest_put_patch",
            "publish_post",
            "create_real_draft",
            "update_existing_post",
            "delete_post",
            "github_actions_trigger",
            "slack_notification",
            "cron_change",
            "env_or_secret_access",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def record_draft_candidate_approval_evidence(
    input_path: Path | None = None,
    output_path: Path | None = None,
    overwrite: bool = False,
) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        return abort_result(f"review_result not found: {input_path}")

    if output_path.exists() and not overwrite:
        return abort_result(f"draft_candidate_approval_evidence already exists: {output_path}")

    data = load_json(input_path)
    validation_error = validate_review_result(data)
    if validation_error:
        return validation_error

    evidence = build_evidence(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "package_type": "draft_candidate_approval_evidence_result",
        "phase": "Phase 5-5",
        "status": "PASS",
        "reason": "draft_candidate_approval_evidence.json generated",
        "evidence_generated": True,
        "output_path": str(output_path),
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    result = record_draft_candidate_approval_evidence()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
