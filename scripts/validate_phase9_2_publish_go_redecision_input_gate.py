#!/usr/bin/env python3
"""Phase 9-2 公開GO再判断 入力検証ゲート

Phase 9-1 のランブックを前提に、human_review の入力（GO/KEEP_NO_GO/REQUEST_FIX/ABORT）を
受け取り、公開候補を解放してよいかを検証する。
このフェーズでは publish を実行しない。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"
HR_DIR = ROOT / "exchange" / "human_review"

INPUT_DEFAULT = HR_DIR / "phase9_2_publish_go_redecision_input_gate.json"
INPUT_FALLBACK = HR_DIR / "phase9_2_publish_go_redecision_input_gate.example.json"
INPUT_RUNBOOK = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result.json"
OUTPUT = LOG_DIR / "phase9_2_publish_go_redecision_input_gate_result.json"

VALID_DECISIONS = {
    "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
    "KEEP_NO_GO",
    "REQUEST_FIX",
    "ABORT",
}

VALID_GO_TOKEN = "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY"

CONFIRMATION_KEYS = [
    "phase9_1_runbook_reviewed_confirmed",
    "target_draft_id_confirmed",
    "target_status_draft_confirmed",
    "human_reviewer_confirmed",
    "token_constraints_confirmed",
    "no_go_scope_understood_confirmed",
    "manual_publish_only_confirmed",
    "publish_not_executed_in_phase9_2_confirmed",
]

FORBIDDEN_TRUE_FLAGS = [
    "publish_allowed",
    "update_allowed",
    "delete_allowed",
    "export_allowed",
    "wordpress_post_enabled",
    "real_write_enabled",
    "wordpress_write_executed",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
    "github_actions_triggered",
    "slack_notification_executed",
    "vps_self_builder_executed",
    "env_or_secrets_modified",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(reason: str, output_path: Path) -> dict:
    result = {
        "package_type": "phase9_2_publish_go_redecision_input_gate_result",
        "phase": "Phase 9-2",
        "status": "ABORT",
        "decision": "ABORT",
        "reason": reason,
        "manual_decision_recorded": False,
        "publish_candidate_unlocked_for_operator": False,
        "production_status": "NO_GO",
        "wordpress_publish_execution": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(output_path, result)
    return result


def _all_confirmations_true(data: dict) -> bool:
    conf = data.get("manual_confirmation", {})
    return all(conf.get(k) is True for k in CONFIRMATION_KEYS)


def _validate_safety_flags(data: dict) -> str | None:
    flags = data.get("safety_flags", {})
    if not isinstance(flags, dict):
        return "safety_flags must be an object"
    for flag in FORBIDDEN_TRUE_FLAGS:
        if flags.get(flag) is True or data.get(flag) is True:
            return f"{flag}=true is forbidden in Phase 9-2"
    return None


def run_validation(input_path=None, output_path=None) -> dict:
    output_path = Path(output_path or OUTPUT)

    if not INPUT_RUNBOOK.exists():
        return _abort(f"phase9_1 runbook result not found: {INPUT_RUNBOOK}", output_path)

    p91 = _load(INPUT_RUNBOOK)
    if p91.get("status") != "PASS":
        return _abort("phase9_1 status must be PASS", output_path)
    if p91.get("decision") != "KEEP_NO_GO":
        return _abort("phase9_1 decision must be KEEP_NO_GO", output_path)

    expected_draft_id = p91.get("target_draft_id")

    if input_path is None:
        input_path = INPUT_DEFAULT if INPUT_DEFAULT.exists() else INPUT_FALLBACK

    input_path = Path(input_path)
    if not input_path.exists():
        return _abort(f"input file not found: {input_path}", output_path)

    data = _load(input_path)

    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST", output_path)
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN", output_path)
    if data.get("reviewer_is_human") is not True:
        return _abort("reviewer_is_human must be true", output_path)

    flag_err = _validate_safety_flags(data)
    if flag_err:
        return _abort(flag_err, output_path)

    decision = data.get("decision")
    if decision not in VALID_DECISIONS:
        return _abort(f"unknown decision: {decision!r}", output_path)

    provided_draft_id = data.get("wordpress_draft_id")
    if provided_draft_id != expected_draft_id:
        return _abort(
            f"wordpress_draft_id mismatch: expected={expected_draft_id} actual={provided_draft_id}",
            output_path,
        )

    all_confirmed = _all_confirmations_true(data)
    fix_requests = data.get("review_notes", {}).get("fix_requests", [])

    base = {
        "package_type": "phase9_2_publish_go_redecision_input_gate_result",
        "phase": "Phase 9-2",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "decision": decision,
        "reviewer": data.get("reviewer"),
        "reviewer_is_human": True,
        "manual_decision_recorded": True,
        "all_manual_confirmation_passed": all_confirmed,
        "wordpress_draft_id": expected_draft_id,
        "target_draft_status": "draft",
        "production_status": "NO_GO",
        "wordpress_publish_execution": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "fix_requests": fix_requests,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if decision == "GO_PUBLISH_ONE_TIME_MANUAL_ONLY":
        if data.get("approval_token") != VALID_GO_TOKEN:
            result = _abort(
                f"approval_token must be {VALID_GO_TOKEN!r} for GO decision",
                output_path,
            )
            result["decision"] = decision
            return result
        if not all_confirmed:
            result = _abort(
                "all manual_confirmation items must be true for GO decision",
                output_path,
            )
            result["decision"] = decision
            return result
        result = {
            **base,
            "status": "PASS",
            "reason": "GO redecision recorded; publish_candidate_unlocked but publish not yet executed",
            "publish_candidate_unlocked_for_operator": True,
            "next_step": "phase9_3_execute_one_time_manual_publish",
        }
    elif decision == "KEEP_NO_GO":
        result = {
            **base,
            "status": "PASS",
            "reason": "KEEP_NO_GO redecision recorded; publish candidate remains locked",
            "publish_candidate_unlocked_for_operator": False,
            "next_step": "maintain_no_go",
        }
    elif decision == "REQUEST_FIX":
        result = {
            **base,
            "status": "WARN",
            "reason": "operator requested fixes before publish candidate unlock",
            "publish_candidate_unlocked_for_operator": False,
            "next_step": "request_fix",
        }
    else:  # ABORT
        result = {
            **base,
            "status": "ABORT",
            "reason": "operator selected ABORT",
            "publish_candidate_unlocked_for_operator": False,
            "next_step": "abort",
        }

    _write(output_path, result)
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") not in {"ABORT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
