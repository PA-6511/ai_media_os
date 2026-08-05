#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


STATUS_PASSED = "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_PASSED"
STATUS_FAILED = "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_FAILED"
STATUS_NOT_READY = "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"
STATUS_NOT_READY_MISSING_VERIFY_FLAG = "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY_MISSING_VERIFY_FLAG"
STATUS_NOT_READY_MISSING_RESTORE_FLAG = "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY_MISSING_RESTORE_FLAG"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def safe_value(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_wordpress_draft_verification_result(
    *,
    status: str,
    post_id: int,
    expected_status: str,
    returned_post_status: str,
    post_link: str,
    payload_title: str,
    payload_asin: str,
    credential_env_read_executed: bool,
    title_match_warning: str,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6P",
        "document_type": "WORDPRESS_DRAFT_VERIFICATION_RESULT",
        "status": status,
        "post_id": post_id,
        "expected_status": expected_status,
        "returned_post_status": returned_post_status,
        "post_link": post_link,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "wordpress_get_executed": True,
        "wordpress_get_post_id": post_id,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "credential_env_read_executed": credential_env_read_executed,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "title_match_warning": title_match_warning,
        "errors": errors,
    }


def build_runtime_freeze_restore_result(policy: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6P",
        "document_type": "RUNTIME_FREEZE_RESTORE_RESULT",
        "status": "RUNTIME_FREEZE_RESTORE_RECORDED",
        "runtime_freeze_was_active": True,
        "runtime_freeze_restored": True,
        "runtime_freeze_restore_method": "EVIDENCE_RECORD_ONLY_DO_NOT_DELETE_ORIGINAL_STATE",
        "original_runtime_freeze_state": safe_value(policy, "required_previous_phase", "runtime_freeze", "active_state"),
        "original_runtime_freeze_lock": safe_value(policy, "required_previous_phase", "runtime_freeze", "active_lock"),
        "runtime_freeze_state_deleted": False,
        "runtime_freeze_lock_deleted": False,
        "errors": errors,
    }


def build_rerun_prevention_final_lock(policy: dict[str, Any], post_id: int, status: str, created_count: int) -> dict[str, Any]:
    return {
        "phase": "LS-6P",
        "document_type": "RERUN_PREVENTION_FINAL_LOCK",
        "status": "RERUN_PREVENTION_FINALIZED",
        "locked": True,
        "rerun_allowed": False,
        "ls6oc1_rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "target_post_id": post_id,
        "target_post_status": status,
        "created_count": created_count,
        "reason": "One-shot WordPress draft creation already completed and validated.",
        "next_phase": {
            "phase": safe_value(policy, "next_phase", "phase"),
            "manual_review_required": safe_value(policy, "next_phase", "manual_review_required"),
            "manual_publish_allowed_by_this_phase": safe_value(policy, "next_phase", "manual_publish_allowed_by_this_phase"),
        },
    }


def build_run_result(
    *,
    status: str,
    production_status: str,
    post_id: int,
    draft_verified: bool,
    returned_post_status: str,
    post_link: str,
    runtime_freeze_restored: bool,
    rerun_prevention_finalized: bool,
    credential_env_read_executed: bool,
    wordpress_get_executed: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6P",
        "status": status,
        "execution_mode": "POST_EXECUTION_VERIFICATION_AND_FREEZE_RESTORE_ONLY",
        "production_status": production_status,
        "post_id": post_id,
        "draft_verified": draft_verified,
        "returned_post_status": returned_post_status,
        "post_link": post_link,
        "runtime_freeze_restored": runtime_freeze_restored,
        "rerun_prevention_finalized": rerun_prevention_finalized,
        "rerun_allowed": False,
        "wordpress_get_executed": wordpress_get_executed,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "credential_env_read_executed": credential_env_read_executed,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
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
        "# LS-6P Post-execution Evidence Freeze Restore Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- post_link: {result['post_link']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- rerun_prevention_finalized: {result['rerun_prevention_finalized']}",
        f"- rerun_allowed: {result['rerun_allowed']}",
        f"- wordpress_get_executed: {result['wordpress_get_executed']}",
        f"- wordpress_write_executed_by_this_phase: {result['wordpress_write_executed_by_this_phase']}",
        f"- wordpress_draft_creation_executed_by_this_phase: {result['wordpress_draft_creation_executed_by_this_phase']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- credential_value_output: {result['credential_value_output']}",
        f"- authorization_header_output: {result['authorization_header_output']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- manual_review_required: {result['next_phase']['manual_review_required']}",
        f"- manual_publish_allowed_by_this_phase: {result['next_phase']['manual_publish_allowed_by_this_phase']}",
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
    parser.add_argument("--ls6oc1-execution-result", default="exchange/runtime/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--ls6oc1-run-result", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--ls6oc1-validation-result", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_validation_result.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--runtime-freeze-lock", default="exchange/locks/start_ls6m_runtime_freeze_active.lock.json")
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--wordpress-draft-verification-output", default="exchange/runtime/start_ls6p_wordpress_draft_verification_result.json")
    parser.add_argument("--runtime-freeze-restore-output", default="exchange/runtime/start_ls6p_runtime_freeze_restore_result.json")
    parser.add_argument("--rerun-prevention-lock-output", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6p_post_execution_evidence_freeze_restore_result.json")
    parser.add_argument("--report", default="reports/start_ls6p_post_execution_evidence_freeze_restore_report.md")
    parser.add_argument("--verify-wordpress-draft", action="store_true")
    parser.add_argument("--restore-runtime-freeze", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_json(Path(args.policy))
    target_post = policy.get("target_post", {})
    post_id = int(target_post.get("post_id", 0) or 0)
    post_link = str(target_post.get("expected_link", ""))
    payload_title = str(target_post.get("title", ""))
    payload_asin = str(target_post.get("asin", ""))
    expected_status = str(target_post.get("expected_status", "draft"))
    created_count = int(target_post.get("created_count", 1) or 1)
    max_items = int(target_post.get("max_items", 1) or 1)

    if not args.verify_wordpress_draft:
        result = build_run_result(
            status=STATUS_NOT_READY_MISSING_VERIFY_FLAG,
            production_status="POST_EXECUTION_NOT_READY",
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            post_link=post_link,
            runtime_freeze_restored=False,
            rerun_prevention_finalized=False,
            credential_env_read_executed=False,
            wordpress_get_executed=False,
            errors=["--verify-wordpress-draft is required"],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.restore_runtime_freeze:
        result = build_run_result(
            status=STATUS_NOT_READY_MISSING_RESTORE_FLAG,
            production_status="POST_EXECUTION_NOT_READY",
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            post_link=post_link,
            runtime_freeze_restored=False,
            rerun_prevention_finalized=False,
            credential_env_read_executed=False,
            wordpress_get_executed=False,
            errors=["--restore-runtime-freeze is required"],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    required_paths = [
        Path(args.ls6oc1_execution_result),
        Path(args.ls6oc1_consumption_lock),
        Path(args.ls6oc1_run_result),
        Path(args.ls6oc1_validation_result),
        Path(args.runtime_freeze_state),
        Path(args.runtime_freeze_lock),
    ]
    missing_inputs = [str(path) for path in required_paths if not path.exists()]
    if missing_inputs:
        result = build_run_result(
            status=STATUS_NOT_READY,
            production_status="POST_EXECUTION_NOT_READY",
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            post_link=post_link,
            runtime_freeze_restored=False,
            rerun_prevention_finalized=False,
            credential_env_read_executed=False,
            wordpress_get_executed=False,
            errors=[f"missing required input: {item}" for item in missing_inputs],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    errors: list[str] = []
    ls6oc1_execution = load_json(Path(args.ls6oc1_execution_result))
    ls6oc1_consumption = load_json(Path(args.ls6oc1_consumption_lock))
    ls6oc1_run = load_json(Path(args.ls6oc1_run_result))
    ls6oc1_validation = load_json(Path(args.ls6oc1_validation_result))
    runtime_freeze_state = load_json(Path(args.runtime_freeze_state))
    runtime_freeze_lock = load_json(Path(args.runtime_freeze_lock))

    require(ls6oc1_run.get("status") == safe_value(policy, "required_previous_phase", "ls6oc1", "required_run_status"), "LS-6O-C-1 run status mismatch", errors)
    require(ls6oc1_validation.get("status") == safe_value(policy, "required_previous_phase", "ls6oc1", "required_validation_status"), "LS-6O-C-1 validation status mismatch", errors)
    require(int(ls6oc1_execution.get("new_post_id", 0)) == post_id, "LS-6O-C-1 new_post_id mismatch", errors)
    require(ls6oc1_execution.get("returned_post_status") == expected_status, "LS-6O-C-1 returned_post_status mismatch", errors)
    require(int(ls6oc1_execution.get("created_count", 0)) == created_count, "LS-6O-C-1 created_count mismatch", errors)
    require(int(ls6oc1_execution.get("max_items", 0)) == max_items, "LS-6O-C-1 max_items mismatch", errors)
    require(ls6oc1_consumption.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)
    require(runtime_freeze_state.get("runtime_freeze_active") is True, "runtime_freeze_active must be true before restore", errors)
    require(runtime_freeze_state.get("runtime_freeze_restored") is False, "runtime_freeze_restored must be false before LS-6P", errors)
    require(runtime_freeze_lock.get("locked") is True, "runtime freeze lock must be true", errors)

    require(ls6oc1_execution.get("publish_executed") is False, "publish_executed must remain false", errors)
    require(ls6oc1_execution.get("future_schedule_executed") is False, "future_schedule_executed must remain false", errors)
    require(ls6oc1_execution.get("wordpress_existing_post_update_executed") is False, "wordpress_existing_post_update_executed must remain false", errors)
    require(ls6oc1_execution.get("post119_update_executed") is False, "post119_update_executed must remain false", errors)
    require(ls6oc1_execution.get("delete_executed") is False, "delete_executed must remain false", errors)

    if errors:
        result = build_run_result(
            status=STATUS_NOT_READY,
            production_status="POST_EXECUTION_NOT_READY",
            post_id=post_id,
            draft_verified=False,
            returned_post_status=str(ls6oc1_execution.get("returned_post_status", "")),
            post_link=post_link,
            runtime_freeze_restored=False,
            rerun_prevention_finalized=False,
            credential_env_read_executed=False,
            wordpress_get_executed=False,
            errors=errors,
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    env = parse_env_file(Path(args.credential_env))
    credential_errors: list[str] = []
    for key in safe_value(policy, "credential_policy", "required_credential_keys") or []:
        require(bool(env.get(key)), f"{key} missing", credential_errors)

    if credential_errors:
        result = build_run_result(
            status=STATUS_FAILED,
            production_status="POST_EXECUTION_FAILED",
            post_id=post_id,
            draft_verified=False,
            returned_post_status=str(ls6oc1_execution.get("returned_post_status", "")),
            post_link=post_link,
            runtime_freeze_restored=False,
            rerun_prevention_finalized=False,
            credential_env_read_executed=True,
            wordpress_get_executed=False,
            errors=credential_errors,
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    base_url = env["WORDPRESS_BASE_URL"]
    username = env["WORDPRESS_USERNAME"]
    app_password = env["WORDPRESS_APP_PASSWORD"]
    token = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode("ascii")
    endpoint = base_url.rstrip("/") + f"/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = request.Request(endpoint, method="GET")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Accept", "application/json")

    api_errors: list[str] = []
    response_payload: dict[str, Any] = {}
    try:
        with request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                api_errors.append(f"WordPress GET HTTP status: {resp.status}")
            response_payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        api_errors.append(f"WordPress GET HTTPError: {exc.code}")
    except URLError as exc:
        api_errors.append(f"WordPress GET URLError: {exc.reason}")

    returned_post_status = str(response_payload.get("status", ""))
    returned_post_id = int(response_payload.get("id", 0) or 0)
    returned_post_link = str(response_payload.get("link", post_link) or post_link)
    returned_title = str(safe_value(response_payload, "title", "rendered") or "")
    title_match_warning = ""

    require(returned_post_id == post_id, "WordPress GET post id mismatch", api_errors)
    require(returned_post_status == expected_status, "WordPress GET status mismatch", api_errors)
    if returned_title and returned_title != payload_title:
        title_match_warning = f"Expected title '{payload_title}' but got '{returned_title}'"

    verification_status = "WORDPRESS_DRAFT_VERIFIED" if not api_errors else "WORDPRESS_DRAFT_VERIFICATION_FAILED"
    verification_result = build_wordpress_draft_verification_result(
        status=verification_status,
        post_id=post_id,
        expected_status=expected_status,
        returned_post_status=returned_post_status,
        post_link=returned_post_link,
        payload_title=payload_title,
        payload_asin=payload_asin,
        credential_env_read_executed=True,
        title_match_warning=title_match_warning,
        errors=api_errors,
    )
    write_json(Path(args.wordpress_draft_verification_output), verification_result)

    if api_errors:
        result = build_run_result(
            status=STATUS_FAILED,
            production_status="POST_EXECUTION_FAILED",
            post_id=post_id,
            draft_verified=False,
            returned_post_status=returned_post_status,
            post_link=returned_post_link,
            runtime_freeze_restored=False,
            rerun_prevention_finalized=False,
            credential_env_read_executed=True,
            wordpress_get_executed=True,
            errors=api_errors,
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    freeze_restore_result = build_runtime_freeze_restore_result(policy, [])
    rerun_lock = build_rerun_prevention_final_lock(policy, post_id, expected_status, created_count)
    write_json(Path(args.runtime_freeze_restore_output), freeze_restore_result)
    write_json(Path(args.rerun_prevention_lock_output), rerun_lock)

    result = build_run_result(
        status=STATUS_PASSED,
        production_status="POST_EXECUTION_DRAFT_VERIFIED_AND_LOCKED",
        post_id=post_id,
        draft_verified=True,
        returned_post_status=returned_post_status,
        post_link=returned_post_link,
        runtime_freeze_restored=True,
        rerun_prevention_finalized=True,
        credential_env_read_executed=True,
        wordpress_get_executed=True,
        errors=[],
    )
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())