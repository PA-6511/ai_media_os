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


STATUS_PASSED = "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"
STATUS_NOT_READY_MISSING_VERIFY_FLAG = "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"
STATUS_NOT_READY_MISSING_RECORD_FLAG = "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_RECORD_FLAG"


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


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6s_manual_publish_final_preflight_policy.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6q-ready-result", default="exchange/logs/start_ls6q_human_wordpress_draft_review_ready_result.json")
    parser.add_argument("--ls6q-review-result", default="exchange/human_review/start_ls6q_human_wordpress_draft_review_result.json")
    parser.add_argument("--ls6p-draft-verification-result", default="exchange/runtime/start_ls6p_wordpress_draft_verification_result.json")
    parser.add_argument("--ls6p-runtime-freeze-restore-result", default="exchange/runtime/start_ls6p_runtime_freeze_restore_result.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6p-validation-result", default="exchange/logs/start_ls6p_post_execution_evidence_freeze_restore_validation_result.json")
    parser.add_argument("--ls6oc1-execution-result", default="exchange/runtime/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--wordpress-current-draft-status-output", default="exchange/runtime/start_ls6s_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--manual-publish-final-preflight-output", default="exchange/runtime/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--manual-publish-final-preflight-lock-output", default="exchange/locks/start_ls6s_manual_publish_final_preflight.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--report", default="reports/start_ls6s_manual_publish_final_preflight_report.md")
    parser.add_argument("--verify-current-draft", action="store_true")
    parser.add_argument("--record-final-preflight", action="store_true")
    return parser.parse_args()


def build_wp_status_result(
    *,
    status: str,
    post_id: int,
    expected_status: str,
    returned_post_status: str,
    post_link: str,
    payload_title: str,
    payload_asin: str,
    wordpress_get_executed: bool,
    credential_env_read_executed: bool,
    title_match_warning: str,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6S",
        "document_type": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_RESULT",
        "status": status,
        "post_id": post_id,
        "expected_status": expected_status,
        "returned_post_status": returned_post_status,
        "post_link": post_link,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "wordpress_get_executed": wordpress_get_executed,
        "wordpress_get_post_id": post_id if wordpress_get_executed else 0,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
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


def build_preflight_result(
    *,
    status: str,
    post_id: int,
    current_post_status_verified: bool,
    returned_post_status: str,
    ls6r_approval_verified: bool,
    approval_label: str,
    wordpress_get_executed: bool,
    credential_env_read_executed: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6S",
        "document_type": "MANUAL_PUBLISH_FINAL_PREFLIGHT_RESULT",
        "status": status,
        "post_id": post_id,
        "current_post_status_verified": current_post_status_verified,
        "returned_post_status": returned_post_status,
        "ls6r_approval_verified": ls6r_approval_verified,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "wordpress_get_executed": wordpress_get_executed,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "credential_env_read_executed": credential_env_read_executed,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "separate_execute_now_confirmation_required": True,
        "publish_execution_still_blocked": True,
        "errors": errors,
    }


def build_preflight_lock(post_id: int, approval_label: str, returned_post_status: str) -> dict[str, Any]:
    return {
        "phase": "LS-6S",
        "document_type": "MANUAL_PUBLISH_FINAL_PREFLIGHT_LOCK",
        "status": "MANUAL_PUBLISH_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": post_id,
        "target_post_status": returned_post_status,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": "LS-6T",
        "requires_separate_execute_now_confirmation": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(
    *,
    status: str,
    post_id: int,
    draft_verified: bool,
    returned_post_status: str,
    approval_label: str,
    wordpress_get_executed: bool,
    credential_env_read_executed: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6S",
        "status": status,
        "execution_mode": "FINAL_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": post_id,
        "draft_verified": draft_verified,
        "returned_post_status": returned_post_status,
        "wordpress_get_executed": wordpress_get_executed,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "separate_execute_now_confirmation_required": True,
        "publish_execution_still_blocked": True,
        "credential_env_read_executed": credential_env_read_executed,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
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
        "# LS-6S Manual Publish Final Preflight Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- wordpress_get_executed: {result['wordpress_get_executed']}",
        f"- approval_label: {result['approval_label']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- manual_publish_allowed_by_this_phase: {result['manual_publish_allowed_by_this_phase']}",
        f"- manual_publish_execution_allowed_by_this_phase: {result['manual_publish_execution_allowed_by_this_phase']}",
        f"- manual_publish_executed: {result['manual_publish_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- credential_value_output: {result['credential_value_output']}",
        f"- authorization_header_output: {result['authorization_header_output']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_separate_execute_now_confirmation: {result['next_phase']['requires_separate_execute_now_confirmation']}",
        f"- manual_publish_execution_allowed_by_this_phase: {result['next_phase']['manual_publish_execution_allowed_by_this_phase']}",
        f"- publish_execution_still_blocked: {result['next_phase']['publish_execution_still_blocked']}",
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


def validate_prerequisites(
    policy: dict[str, Any],
    ls6r_ready: dict[str, Any],
    ls6r_approval: dict[str, Any],
    ls6q_ready: dict[str, Any],
    ls6q_review: dict[str, Any],
    ls6p_verify: dict[str, Any],
    ls6p_freeze: dict[str, Any],
    ls6p_lock: dict[str, Any],
    ls6p_validation: dict[str, Any],
    ls6oc1_exec: dict[str, Any],
    ls6oc1_lock: dict[str, Any],
    errors: list[str],
) -> None:
    target = policy.get("target_post", {})
    post_id = to_int(target.get("post_id"))
    expected_status = str(target.get("expected_current_status", "draft"))

    require(policy.get("phase") == "LS-6S", "policy.phase mismatch", errors)
    require(policy.get("execution_mode") == "FINAL_PREFLIGHT_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    require(ls6r_ready.get("status") == safe_get(policy, "required_previous_phase", "ls6r", "required_ready_status"), "LS-6R ready status mismatch", errors)
    require(ls6r_ready.get("approval_status") == safe_get(policy, "required_previous_phase", "ls6r", "required_approval_status"), "LS-6R approval_status mismatch", errors)
    require(ls6r_ready.get("approval_label") == safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label"), "LS-6R approval_label mismatch", errors)
    require(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    require(ls6r_ready.get("manual_publish_executed") is False, "LS-6R manual_publish_executed must be false", errors)
    require(safe_get(ls6r_ready, "next_phase", "phase") == "LS-6S", "LS-6R next_phase.phase mismatch", errors)

    approval = ls6r_approval.get("approval", {})
    require(ls6r_approval.get("approval_status") == safe_get(policy, "required_previous_phase", "ls6r", "required_approval_status"), "LS-6R approval result status mismatch", errors)
    require(approval.get("approval_label") == safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label"), "LS-6R approval result label mismatch", errors)
    require(approval.get("approval_label_consumed") is False, "LS-6R approval result label_consumed must be false", errors)
    require(approval.get("manual_publish_executed") is False, "LS-6R approval result manual_publish_executed must be false", errors)

    require(ls6q_ready.get("status") == safe_get(policy, "required_previous_phase", "ls6q", "required_ready_status"), "LS-6Q ready status mismatch", errors)
    require(ls6q_ready.get("human_decision") == safe_get(policy, "required_previous_phase", "ls6q", "required_human_decision"), "LS-6Q human_decision mismatch", errors)
    require(safe_get(ls6q_review, "human_decision", "decision") == safe_get(policy, "required_previous_phase", "ls6q", "required_human_decision"), "LS-6Q review decision mismatch", errors)

    require(ls6p_validation.get("status") == safe_get(policy, "required_previous_phase", "ls6p", "required_validation_status"), "LS-6P validation status mismatch", errors)
    require(to_int(ls6p_validation.get("post_id", ls6p_verify.get("post_id"))) == post_id, "LS-6P post_id mismatch", errors)
    require(ls6p_verify.get("returned_post_status") == expected_status, "LS-6P returned_post_status mismatch", errors)
    require(ls6p_validation.get("runtime_freeze_restored") is True, "LS-6P runtime_freeze_restored must be true", errors)
    require(ls6p_freeze.get("runtime_freeze_restored") is True, "LS-6P freeze restore result mismatch", errors)
    require(ls6p_lock.get("locked") is True, "LS-6P lock must be true", errors)
    require(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)

    require(to_int(ls6oc1_exec.get("new_post_id", ls6oc1_exec.get("post_id"))) == post_id, "LS-6O-C-1 post_id mismatch", errors)
    require(ls6oc1_exec.get("returned_post_status") == safe_get(policy, "required_previous_phase", "ls6oc1", "required_returned_post_status"), "LS-6O-C-1 returned_post_status mismatch", errors)
    require(to_int(ls6oc1_exec.get("created_count")) == to_int(safe_get(policy, "required_previous_phase", "ls6oc1", "required_created_count")), "LS-6O-C-1 created_count mismatch", errors)
    require(ls6oc1_lock.get("rerun_allowed") is safe_get(policy, "required_previous_phase", "ls6oc1", "required_rerun_allowed"), "LS-6O-C-1 rerun_allowed mismatch", errors)


def main() -> int:
    args = parse_args()
    policy_path = Path(args.policy)

    policy = load_json(policy_path)
    target = policy.get("target_post", {})
    post_id = to_int(target.get("post_id"))
    expected_status = str(target.get("expected_current_status", "draft"))
    post_link = str(target.get("post_link", ""))
    payload_title = str(target.get("title", ""))
    payload_asin = str(target.get("asin", ""))
    approval_label_required = str(safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label") or "")

    if not args.verify_current_draft:
        result = build_run_result(
            status=STATUS_NOT_READY_MISSING_VERIFY_FLAG,
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            approval_label=approval_label_required,
            wordpress_get_executed=False,
            credential_env_read_executed=False,
            errors=["--verify-current-draft is required"],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.record_final_preflight:
        result = build_run_result(
            status=STATUS_NOT_READY_MISSING_RECORD_FLAG,
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            approval_label=approval_label_required,
            wordpress_get_executed=False,
            credential_env_read_executed=False,
            errors=["--record-final-preflight is required"],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    required_paths = [
        policy_path,
        Path(args.ls6r_ready_result),
        Path(args.ls6r_approval_result),
        Path(args.ls6q_ready_result),
        Path(args.ls6q_review_result),
        Path(args.ls6p_draft_verification_result),
        Path(args.ls6p_runtime_freeze_restore_result),
        Path(args.ls6p_rerun_prevention_lock),
        Path(args.ls6p_validation_result),
        Path(args.ls6oc1_execution_result),
        Path(args.ls6oc1_consumption_lock),
    ]
    missing_inputs = [str(path) for path in required_paths if not path.exists()]
    if missing_inputs:
        result = build_run_result(
            status=STATUS_NOT_READY,
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            approval_label=approval_label_required,
            wordpress_get_executed=False,
            credential_env_read_executed=False,
            errors=[f"missing required input: {item}" for item in missing_inputs],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6r_approval = load_json(Path(args.ls6r_approval_result))
    ls6q_ready = load_json(Path(args.ls6q_ready_result))
    ls6q_review = load_json(Path(args.ls6q_review_result))
    ls6p_verify = load_json(Path(args.ls6p_draft_verification_result))
    ls6p_freeze = load_json(Path(args.ls6p_runtime_freeze_restore_result))
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock))
    ls6p_validation = load_json(Path(args.ls6p_validation_result))
    ls6oc1_exec = load_json(Path(args.ls6oc1_execution_result))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    precheck_errors: list[str] = []
    validate_prerequisites(
        policy=policy,
        ls6r_ready=ls6r_ready,
        ls6r_approval=ls6r_approval,
        ls6q_ready=ls6q_ready,
        ls6q_review=ls6q_review,
        ls6p_verify=ls6p_verify,
        ls6p_freeze=ls6p_freeze,
        ls6p_lock=ls6p_lock,
        ls6p_validation=ls6p_validation,
        ls6oc1_exec=ls6oc1_exec,
        ls6oc1_lock=ls6oc1_lock,
        errors=precheck_errors,
    )

    if precheck_errors:
        result = build_run_result(
            status=STATUS_NOT_READY,
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            approval_label=approval_label_required,
            wordpress_get_executed=False,
            credential_env_read_executed=False,
            errors=precheck_errors,
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    credential_errors: list[str] = []
    env_path = Path(args.credential_env)
    if not env_path.exists():
        credential_errors.append(f"missing required input: {args.credential_env}")
        env: dict[str, str] = {}
    else:
        env = parse_env_file(env_path)

    for key in safe_get(policy, "credential_policy", "required_credential_keys") or []:
        require(bool(env.get(key)), f"{key} missing", credential_errors)

    if credential_errors:
        wp_result = build_wp_status_result(
            status="WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_FAILED",
            post_id=post_id,
            expected_status=expected_status,
            returned_post_status="",
            post_link=post_link,
            payload_title=payload_title,
            payload_asin=payload_asin,
            wordpress_get_executed=False,
            credential_env_read_executed=True,
            title_match_warning="",
            errors=credential_errors,
        )
        preflight_result = build_preflight_result(
            status="MANUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH",
            post_id=post_id,
            current_post_status_verified=False,
            returned_post_status="",
            ls6r_approval_verified=False,
            approval_label=approval_label_required,
            wordpress_get_executed=False,
            credential_env_read_executed=True,
            errors=credential_errors,
        )
        run_result = build_run_result(
            status=STATUS_FAILED,
            post_id=post_id,
            draft_verified=False,
            returned_post_status="",
            approval_label=approval_label_required,
            wordpress_get_executed=False,
            credential_env_read_executed=True,
            errors=credential_errors,
        )
        write_json(Path(args.wordpress_current_draft_status_output), wp_result)
        write_json(Path(args.manual_publish_final_preflight_output), preflight_result)
        write_json(Path(args.output), run_result)
        write_report(run_result, Path(args.report))
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
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

    returned_post_id = to_int(response_payload.get("id"))
    returned_post_status = str(response_payload.get("status", ""))
    returned_post_link = str(response_payload.get("link", post_link) or post_link)
    returned_title = str(safe_get(response_payload, "title", "rendered") or "")
    title_match_warning = ""

    require(returned_post_id == post_id, "WordPress GET post id mismatch", api_errors)
    require(returned_post_status == expected_status, "WordPress GET post status mismatch", api_errors)
    if returned_title and returned_title != payload_title:
        title_match_warning = f"Title differs: expected '{payload_title}' got '{returned_title}'"

    wp_ok = not api_errors
    wp_result = build_wp_status_result(
        status="WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED" if wp_ok else "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_FAILED",
        post_id=post_id,
        expected_status=expected_status,
        returned_post_status=returned_post_status,
        post_link=returned_post_link,
        payload_title=payload_title,
        payload_asin=payload_asin,
        wordpress_get_executed=True,
        credential_env_read_executed=True,
        title_match_warning=title_match_warning,
        errors=api_errors,
    )

    preflight_ok = wp_ok
    preflight_errors = list(api_errors)
    preflight_result = build_preflight_result(
        status="MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH" if preflight_ok else "MANUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH",
        post_id=post_id,
        current_post_status_verified=preflight_ok,
        returned_post_status=returned_post_status,
        ls6r_approval_verified=True,
        approval_label=approval_label_required,
        wordpress_get_executed=True,
        credential_env_read_executed=True,
        errors=preflight_errors,
    )

    run_result = build_run_result(
        status=STATUS_PASSED if preflight_ok else STATUS_FAILED,
        post_id=post_id,
        draft_verified=preflight_ok,
        returned_post_status=returned_post_status,
        approval_label=approval_label_required,
        wordpress_get_executed=True,
        credential_env_read_executed=True,
        errors=preflight_errors,
    )

    write_json(Path(args.wordpress_current_draft_status_output), wp_result)
    write_json(Path(args.manual_publish_final_preflight_output), preflight_result)
    if preflight_ok:
        lock_payload = build_preflight_lock(post_id, approval_label_required, returned_post_status)
        write_json(Path(args.manual_publish_final_preflight_lock_output), lock_payload)
    write_json(Path(args.output), run_result)
    write_report(run_result, Path(args.report))
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
