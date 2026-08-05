#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATION_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6s_manual_publish_final_preflight_policy.json")
    parser.add_argument("--wordpress-current-draft-status-result", default="exchange/runtime/start_ls6s_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--manual-publish-final-preflight-result", default="exchange/runtime/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--manual-publish-final-preflight-lock", default="exchange/locks/start_ls6s_manual_publish_final_preflight.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-validation-result", default="exchange/logs/start_ls6p_post_execution_evidence_freeze_restore_validation_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6s_manual_publish_final_preflight_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6s_manual_publish_final_preflight_validation_report.md")
    return parser.parse_args()


def build_result(status: str, run_result: dict[str, Any], preflight_result: dict[str, Any], lock: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6S",
        "status": status,
        "execution_mode": "FINAL_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(run_result.get("post_id", preflight_result.get("post_id"))),
        "draft_verified": bool(run_result.get("draft_verified", False)),
        "returned_post_status": run_result.get("returned_post_status", ""),
        "wordpress_get_executed": bool(run_result.get("wordpress_get_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(run_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_draft_creation_executed_by_this_phase": bool(run_result.get("wordpress_draft_creation_executed_by_this_phase", False)),
        "wordpress_publish_executed": bool(run_result.get("wordpress_publish_executed", False)),
        "publish_executed": bool(run_result.get("publish_executed", False)),
        "future_schedule_executed": bool(run_result.get("future_schedule_executed", False)),
        "delete_executed": bool(run_result.get("delete_executed", False)),
        "post119_update_executed": bool(run_result.get("post119_update_executed", False)),
        "approval_label": run_result.get("approval_label", ""),
        "approval_label_consumed": bool(run_result.get("approval_label_consumed", False)),
        "manual_publish_allowed_by_this_phase": bool(run_result.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(run_result.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(run_result.get("manual_publish_executed", False)),
        "separate_execute_now_confirmation_required": bool(run_result.get("separate_execute_now_confirmation_required", False)),
        "publish_execution_still_blocked": bool(run_result.get("publish_execution_still_blocked", False)),
        "credential_env_read_executed": bool(run_result.get("credential_env_read_executed", False)),
        "credential_value_output": bool(run_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(run_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(run_result.get("credential_secret_output", False)),
        "secret_length_output": bool(run_result.get("secret_length_output", False)),
        "secret_hash_output": bool(run_result.get("secret_hash_output", False)),
        "authorization_header_output": bool(run_result.get("authorization_header_output", False)),
        "locked": bool(lock.get("locked", False)),
        "rerun_allowed": bool(lock.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(lock.get("ls6oc1_rerun_executed", False)),
        "next_phase": {
            "phase": "LS-6T",
            "execution_allowed": False,
            "requires_separate_execute_now_confirmation": True,
            "manual_publish_execution_allowed_by_this_phase": False,
            "publish_execution_still_blocked": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6S Manual Publish Final Preflight Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- approval_label: {result['approval_label']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- manual_publish_executed: {result['manual_publish_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- locked: {result['locked']}",
        f"- rerun_allowed: {result['rerun_allowed']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    policy = load_json(Path(args.policy))
    wp_result = load_json(Path(args.wordpress_current_draft_status_result))
    preflight_result = load_json(Path(args.manual_publish_final_preflight_result))
    lock = load_json(Path(args.manual_publish_final_preflight_lock))
    run_result = load_json(Path(args.run_result))
    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6r_approval = load_json(Path(args.ls6r_approval_result))
    ls6p_validation = load_json(Path(args.ls6p_validation_result))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    post_id = to_int(safe_get(policy, "target_post", "post_id"), 183)
    expected_label = safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label")
    errors: list[str] = []

    require(run_result.get("status") == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "run result status mismatch", errors)

    require(wp_result.get("status") == "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED", "wordpress verification status mismatch", errors)
    require(to_int(wp_result.get("post_id")) == post_id, "wordpress verification post_id mismatch", errors)
    require(wp_result.get("returned_post_status") == "draft", "wordpress returned_post_status mismatch", errors)
    require(wp_result.get("wordpress_get_executed") is True, "wordpress_get_executed must be true", errors)
    require(to_int(wp_result.get("wordpress_get_post_id")) == post_id, "wordpress_get_post_id mismatch", errors)
    for key in [
        "wordpress_post_executed",
        "wordpress_put_executed",
        "wordpress_patch_executed",
        "wordpress_delete_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_draft_creation_executed_by_this_phase",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
    ]:
        require(wp_result.get(key) is False, f"{key} must be false", errors)

    require(preflight_result.get("status") == "MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "preflight status mismatch", errors)
    require(preflight_result.get("current_post_status_verified") is True, "current_post_status_verified must be true", errors)
    require(preflight_result.get("ls6r_approval_verified") is True, "ls6r_approval_verified must be true", errors)
    require(preflight_result.get("approval_label") == expected_label, "preflight approval_label mismatch", errors)
    require(preflight_result.get("approval_label_consumed") is False, "preflight approval_label_consumed must be false", errors)
    require(preflight_result.get("manual_publish_allowed_by_this_phase") is False, "preflight manual_publish_allowed_by_this_phase must be false", errors)
    require(preflight_result.get("manual_publish_execution_allowed_by_this_phase") is False, "preflight manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(preflight_result.get("manual_publish_executed") is False, "preflight manual_publish_executed must be false", errors)
    require(preflight_result.get("separate_execute_now_confirmation_required") is True, "preflight separate_execute_now_confirmation_required must be true", errors)
    require(preflight_result.get("publish_execution_still_blocked") is True, "preflight publish_execution_still_blocked must be true", errors)

    require(lock.get("locked") is True, "lock.locked must be true", errors)
    require(lock.get("rerun_allowed") is False, "lock.rerun_allowed must be false", errors)
    require(lock.get("ls6oc1_rerun_executed") is False, "lock.ls6oc1_rerun_executed must be false", errors)
    require(lock.get("requires_next_phase") == "LS-6T", "lock.requires_next_phase mismatch", errors)

    for key in [
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
    ]:
        require(run_result.get(key) is False, f"run_result.{key} must be false", errors)
    require(run_result.get("credential_env_read_executed") is True, "run_result.credential_env_read_executed must be true", errors)

    require(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must remain false", errors)
    require(ls6r_ready.get("manual_publish_executed") is False, "LS-6R manual_publish_executed must remain false", errors)
    require(safe_get(ls6r_approval, "approval", "approval_label_consumed") is False, "LS-6R approval result label_consumed must remain false", errors)

    require(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must remain false", errors)
    require(ls6p_validation.get("status") == safe_get(policy, "required_previous_phase", "ls6p", "required_validation_status"), "LS-6P validation status mismatch", errors)

    require(run_result.get("returned_post_status") == "draft", "run result returned_post_status mismatch", errors)
    require(run_result.get("approval_label") == expected_label, "run result approval_label mismatch", errors)
    require(run_result.get("approval_label_consumed") is False, "run result approval_label_consumed must be false", errors)
    require(run_result.get("manual_publish_allowed_by_this_phase") is False, "run result manual_publish_allowed_by_this_phase must be false", errors)
    require(run_result.get("manual_publish_execution_allowed_by_this_phase") is False, "run result manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(run_result.get("manual_publish_executed") is False, "run result manual_publish_executed must be false", errors)
    require(run_result.get("wordpress_write_executed_by_this_phase") is False, "run result wordpress_write_executed_by_this_phase must be false", errors)
    require(run_result.get("wordpress_publish_executed") is False, "run result wordpress_publish_executed must be false", errors)
    require(run_result.get("publish_executed") is False, "run result publish_executed must be false", errors)
    require(run_result.get("separate_execute_now_confirmation_required") is True, "run result separate_execute_now_confirmation_required must be true", errors)
    require(run_result.get("publish_execution_still_blocked") is True, "run result publish_execution_still_blocked must be true", errors)
    require(safe_get(run_result, "next_phase", "phase") == "LS-6T", "run result next_phase mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY
    result = build_result(status, run_result, preflight_result, lock, errors)
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
