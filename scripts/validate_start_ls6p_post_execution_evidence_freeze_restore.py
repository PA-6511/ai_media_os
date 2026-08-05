#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"
STATUS_NOT_READY = "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATION_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_result(status: str, verification: dict[str, Any], rerun_lock: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    ok = status == STATUS_VALIDATED
    return {
        "phase": "LS-6P",
        "status": status,
        "execution_mode": "POST_EXECUTION_VERIFICATION_AND_FREEZE_RESTORE_ONLY",
        "production_status": "POST_EXECUTION_DRAFT_VERIFIED_AND_LOCKED" if ok else "POST_EXECUTION_VALIDATION_NOT_READY",
        "post_id": int(verification.get("post_id", 0)),
        "draft_verified": bool(ok),
        "returned_post_status": verification.get("returned_post_status", ""),
        "runtime_freeze_restored": True if ok else False,
        "rerun_prevention_finalized": bool(ok),
        "rerun_allowed": bool(rerun_lock.get("rerun_allowed")) if not ok else False,
        "wordpress_get_executed": bool(verification.get("wordpress_get_executed")),
        "wordpress_write_executed_by_this_phase": bool(verification.get("wordpress_write_executed_by_this_phase")),
        "wordpress_draft_creation_executed_by_this_phase": bool(verification.get("wordpress_draft_creation_executed_by_this_phase")),
        "publish_executed": bool(verification.get("publish_executed")),
        "future_schedule_executed": bool(verification.get("future_schedule_executed")),
        "delete_executed": bool(verification.get("delete_executed")),
        "credential_env_read_executed": bool(verification.get("credential_env_read_executed")),
        "credential_value_output": bool(verification.get("credential_value_output")),
        "credential_value_persisted": bool(verification.get("credential_value_persisted")),
        "credential_secret_output": bool(verification.get("credential_secret_output")),
        "secret_length_output": bool(verification.get("secret_length_output")),
        "secret_hash_output": bool(verification.get("secret_hash_output")),
        "authorization_header_output": bool(verification.get("authorization_header_output")),
        "next_phase": {
            "phase": "LS-6Q",
            "manual_review_required": True,
            "manual_publish_allowed_by_this_phase": False,
            "execution_allowed": False,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6P Post-execution Evidence Freeze Restore Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- rerun_prevention_finalized: {result['rerun_prevention_finalized']}",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6p_post_execution_evidence_freeze_restore_policy.json")
    parser.add_argument("--wordpress-draft-verification-result", default="exchange/runtime/start_ls6p_wordpress_draft_verification_result.json")
    parser.add_argument("--runtime-freeze-restore-result", default="exchange/runtime/start_ls6p_runtime_freeze_restore_result.json")
    parser.add_argument("--rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6p_post_execution_evidence_freeze_restore_result.json")
    parser.add_argument("--ls6oc1-execution-result", default="exchange/runtime/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--ls6oc1-validation-result", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_validation_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6p_post_execution_evidence_freeze_restore_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6p_post_execution_evidence_freeze_restore_validation_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_json(Path(args.policy))
    verification = load_json(Path(args.wordpress_draft_verification_result))
    freeze_restore = load_json(Path(args.runtime_freeze_restore_result))
    rerun_lock = load_json(Path(args.rerun_prevention_lock))
    run_result = load_json(Path(args.run_result))
    ls6oc1_execution = load_json(Path(args.ls6oc1_execution_result))
    ls6oc1_consumption = load_json(Path(args.ls6oc1_consumption_lock))
    ls6oc1_validation = load_json(Path(args.ls6oc1_validation_result))
    errors: list[str] = []

    require(run_result.get("status") == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_PASSED", "run result status mismatch", errors)
    require(verification.get("status") == "WORDPRESS_DRAFT_VERIFIED", "wordpress draft verification status mismatch", errors)
    require(int(verification.get("post_id", 0)) == 183, "post_id mismatch", errors)
    require(verification.get("returned_post_status") == "draft", "returned_post_status mismatch", errors)
    require(verification.get("wordpress_get_executed") is True, "wordpress_get_executed must be true", errors)
    require(int(verification.get("wordpress_get_post_id", 0)) == 183, "wordpress_get_post_id mismatch", errors)
    require(verification.get("wordpress_post_executed") is False, "wordpress_post_executed must be false", errors)
    require(verification.get("wordpress_put_executed") is False, "wordpress_put_executed must be false", errors)
    require(verification.get("wordpress_patch_executed") is False, "wordpress_patch_executed must be false", errors)
    require(verification.get("wordpress_delete_executed") is False, "wordpress_delete_executed must be false", errors)
    require(verification.get("wordpress_write_executed_by_this_phase") is False, "wordpress_write_executed_by_this_phase must be false", errors)
    require(verification.get("wordpress_draft_creation_executed_by_this_phase") is False, "wordpress_draft_creation_executed_by_this_phase must be false", errors)
    require(verification.get("publish_executed") is False, "publish_executed must be false", errors)
    require(verification.get("future_schedule_executed") is False, "future_schedule_executed must be false", errors)
    require(verification.get("delete_executed") is False, "delete_executed must be false", errors)
    require(verification.get("credential_env_read_executed") is True, "credential_env_read_executed must be true", errors)
    require(verification.get("credential_value_output") is False, "credential_value_output must be false", errors)
    require(verification.get("credential_value_persisted") is False, "credential_value_persisted must be false", errors)
    require(verification.get("credential_secret_output") is False, "credential_secret_output must be false", errors)
    require(verification.get("secret_length_output") is False, "secret_length_output must be false", errors)
    require(verification.get("secret_hash_output") is False, "secret_hash_output must be false", errors)
    require(verification.get("authorization_header_output") is False, "authorization_header_output must be false", errors)

    require(freeze_restore.get("status") == "RUNTIME_FREEZE_RESTORE_RECORDED", "runtime freeze restore status mismatch", errors)
    require(freeze_restore.get("runtime_freeze_was_active") is True, "runtime_freeze_was_active must be true", errors)
    require(freeze_restore.get("runtime_freeze_restored") is True, "runtime_freeze_restored must be true", errors)
    require(freeze_restore.get("runtime_freeze_state_deleted") is False, "runtime_freeze_state_deleted must be false", errors)
    require(freeze_restore.get("runtime_freeze_lock_deleted") is False, "runtime_freeze_lock_deleted must be false", errors)

    require(rerun_lock.get("status") == "RERUN_PREVENTION_FINALIZED", "rerun prevention status mismatch", errors)
    require(rerun_lock.get("locked") is True, "locked must be true", errors)
    require(rerun_lock.get("rerun_allowed") is False, "rerun_allowed must be false", errors)
    require(rerun_lock.get("ls6oc1_rerun_allowed") is False, "ls6oc1_rerun_allowed must be false", errors)
    require(rerun_lock.get("ls6oc1_rerun_executed") is False, "ls6oc1_rerun_executed must be false", errors)
    require(int(rerun_lock.get("target_post_id", 0)) == 183, "target_post_id mismatch", errors)
    require(int(rerun_lock.get("created_count", 0)) == 1, "created_count mismatch", errors)

    require(int(ls6oc1_execution.get("created_count", 0)) == 1, "LS-6O-C-1 created_count mismatch", errors)
    require(ls6oc1_execution.get("returned_post_status") == "draft", "LS-6O-C-1 returned_post_status mismatch", errors)
    require(ls6oc1_execution.get("publish_executed") is False, "LS-6O-C-1 publish_executed must be false", errors)
    require(ls6oc1_execution.get("delete_executed") is False, "LS-6O-C-1 delete_executed must be false", errors)
    require(ls6oc1_consumption.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)
    require(ls6oc1_validation.get("status") == safe_value(policy, "required_previous_phase", "ls6oc1", "required_validation_status"), "LS-6O-C-1 validation status mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY
    result = build_result(status, verification, rerun_lock, errors)
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def safe_value(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    raise SystemExit(main())