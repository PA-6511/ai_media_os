#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib import error, request


HttpPostFn = Callable[[str, str, str, dict[str, Any]], tuple[int | None, dict[str, Any] | None, str | None]]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_wp_post(base_url: str, username: str, app_password: str, payload: dict[str, Any]) -> tuple[int | None, dict[str, Any] | None, str | None]:
    url = base_url.rstrip("/") + "/wp-json/wp/v2/posts"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    token = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    try:
        with request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            data = json.loads(text) if text else {}
            return resp.getcode(), data, None
    except error.HTTPError as exc:
        return exc.code, None, "HTTP_ERROR"
    except error.URLError:
        return None, None, "NETWORK_ERROR"
    except Exception:
        return None, None, "UNEXPECTED_ERROR"


def build_base_result(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "LS-6B",
        "status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP",
        "execution_mode": policy.get("execution_mode", "ONE_SHOT_WRITE_ALLOWED"),
        "production_status": policy.get("production_status", "LIMITED_GO_DRAFT_ONLY"),
        "approval_label": policy.get("required_approval_label"),
        "approval_is_actual": False,
        "post_id": None,
        "post_status": None,
        "max_items": None,
        "payload_count": None,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "existing_post_update_executed": False,
        "delete_executed": False,
        "amazon_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "approval_token_consumed": False,
        "freeze_after_run_executed": False,
        "safe_stop": True,
        "http_status_code": None,
        "error_category": None,
        "errors": [],
        "next_phase": {
            "phase": "LS-7",
            "execution_allowed": False,
            "requires_human_review": True,
            "manual_publish_only": True,
        },
        "generated_at": now_iso(),
    }


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_preconditions(
    policy: dict[str, Any],
    payload: dict[str, Any],
    ls3: dict[str, Any],
    ls4: dict[str, Any],
    ls5: dict[str, Any],
    ls6a: dict[str, Any],
    ls6b_prep: dict[str, Any],
    approval: dict[str, Any],
    env_map: dict[str, str],
    lock: dict[str, Any] | None,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}

    require(policy.get("phase") == "LS-6B", "policy phase must be LS-6B", errors)
    require(policy.get("execution_mode") == "ONE_SHOT_WRITE_ALLOWED", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "LIMITED_GO_DRAFT_ONLY", "policy production_status mismatch", errors)

    require(ls3.get("status") == "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY", "LS-3 status mismatch", errors)
    require(ls4.get("status") == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY", "LS-4 status mismatch", errors)
    require(ls5.get("status") == "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION", "LS-5 status mismatch", errors)
    require(ls6a.get("status") == "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION", "LS-6A status mismatch", errors)
    require(ls6b_prep.get("status") == "LS6B_PREP_RUNNER_DESIGN_BLOCKED_PASS_NO_EXECUTION", "LS-6B-PREP status mismatch", errors)

    label = policy.get("required_approval_label")
    require(approval.get("approval_status") == "HUMAN_APPROVED", "approval_status must be HUMAN_APPROVED", errors)
    require(approval.get("approval_label") == label, "approval_label mismatch", errors)

    for key in policy.get("required_credential_keys", []):
        require(bool(env_map.get(key)), f"credential key missing or empty: {key}", errors)

    payloads = payload.get("payloads", [])
    max_items = payload.get("max_items")
    require(isinstance(payloads, list), "payloads must be a list", errors)
    if isinstance(payloads, list):
        require(len(payloads) == 1, "payloads length must be exactly 1", errors)
    require(isinstance(max_items, int), "max_items must be int", errors)
    if isinstance(max_items, int):
        require(max_items <= 1, "max_items must be <= 1", errors)

    item = payloads[0] if isinstance(payloads, list) and payloads else {}
    require(item.get("post_status") == "draft", "payload item post_status must be draft", errors)

    scope = policy.get("one_shot_scope", {})
    require(scope.get("max_items") == 1, "policy one_shot_scope.max_items must be 1", errors)
    require(scope.get("post_status") == "draft", "policy one_shot_scope.post_status must be draft", errors)
    require(scope.get("publish_allowed") is False, "publish_allowed must be false", errors)
    require(scope.get("future_schedule_allowed") is False, "future_schedule_allowed must be false", errors)
    require(scope.get("existing_post_update_allowed") is False, "existing_post_update_allowed must be false", errors)
    require(scope.get("delete_allowed") is False, "delete_allowed must be false", errors)

    if lock and lock.get("locked") is True and lock.get("reason") == "ONE_SHOT_DRAFT_ALREADY_CREATED":
        meta["locked"] = True
    else:
        meta["locked"] = False

    meta["payload_count"] = len(payloads) if isinstance(payloads, list) else 0
    meta["max_items"] = max_items if isinstance(max_items, int) else None
    meta["item"] = item
    return errors, meta


def write_lock(lock_path: Path, post_id: int, approval_label: str) -> None:
    lock_data = {
        "phase": "LS-6B",
        "locked": True,
        "reason": "ONE_SHOT_DRAFT_ALREADY_CREATED",
        "post_id": post_id,
        "post_status": "draft",
        "approval_label": approval_label,
        "rerun_allowed": False,
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_phase(
    *,
    policy_path: Path,
    payload_path: Path,
    credential_env_path: Path,
    ls3_result_path: Path,
    ls4_result_path: Path,
    ls5_result_path: Path,
    ls6a_ready_result_path: Path,
    ls6b_prep_result_path: Path,
    approval_path: Path,
    lock_path: Path,
    execute: bool,
    wp_post: HttpPostFn | None = None,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    payload = load_json(payload_path)
    ls3 = load_json(ls3_result_path)
    ls4 = load_json(ls4_result_path)
    ls5 = load_json(ls5_result_path)
    ls6a = load_json(ls6a_ready_result_path)
    ls6b_prep = load_json(ls6b_prep_result_path)
    approval = load_json(approval_path)
    env_map = parse_env(credential_env_path)
    lock = load_json(lock_path) if lock_path.exists() else None

    result = build_base_result(policy)
    result["approval_is_actual"] = approval.get("approval_status") == "HUMAN_APPROVED"

    errors, meta = validate_preconditions(policy, payload, ls3, ls4, ls5, ls6a, ls6b_prep, approval, env_map, lock)
    result["errors"].extend(errors)
    result["payload_count"] = meta.get("payload_count")
    result["max_items"] = meta.get("max_items")

    if meta.get("locked"):
        result["status"] = "LS6B_ONE_SHOT_ALREADY_EXECUTED_LOCKED"
        result["safe_stop"] = True
        result["freeze_after_run_executed"] = True
        return result

    if not execute:
        if errors:
            result["status"] = "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP"
            result["freeze_after_run_executed"] = True
            return result
        result["status"] = "LS6B_ONE_SHOT_DRAFT_CREATION_PREFLIGHT_PASS_NO_EXECUTION"
        result["safe_stop"] = False
        result["freeze_after_run_executed"] = False
        return result

    if errors:
        result["status"] = "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP"
        result["freeze_after_run_executed"] = True
        return result

    item = meta["item"]
    api_payload = {
        "title": item.get("title", ""),
        "content": item.get("content", ""),
        "status": "draft",
    }
    wp_post_impl = wp_post or default_wp_post

    status_code, resp_json, error_category = wp_post_impl(
        env_map["WORDPRESS_BASE_URL"],
        env_map["WORDPRESS_USERNAME"],
        env_map["WORDPRESS_APP_PASSWORD"],
        api_payload,
    )
    result["wordpress_api_call_executed"] = True
    result["http_status_code"] = status_code
    result["error_category"] = error_category

    if status_code in (200, 201) and isinstance(resp_json, dict) and isinstance(resp_json.get("id"), int):
        result["status"] = "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN"
        result["post_id"] = resp_json["id"]
        result["post_status"] = "draft"
        result["wordpress_write_executed"] = True
        result["wordpress_draft_creation_executed"] = True
        result["approval_token_consumed"] = True
        result["freeze_after_run_executed"] = True
        result["safe_stop"] = False
        write_lock(lock_path, resp_json["id"], policy.get("required_approval_label", ""))
        return result

    result["status"] = "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP"
    result["freeze_after_run_executed"] = True
    result["safe_stop"] = True
    return result


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6B WordPress One-shot Draft Creation Report",
        "",
        f"- generated_at: {result.get('generated_at')}",
        f"- status: {result.get('status')}",
        f"- execution_mode: {result.get('execution_mode')}",
        f"- production_status: {result.get('production_status')}",
        f"- post_id: {result.get('post_id')}",
        f"- post_status: {result.get('post_status')}",
        f"- payload_count: {result.get('payload_count')}",
        f"- max_items: {result.get('max_items')}",
        f"- wordpress_api_call_executed: {result.get('wordpress_api_call_executed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- wordpress_draft_creation_executed: {result.get('wordpress_draft_creation_executed')}",
        f"- publish_executed: {result.get('publish_executed')}",
        f"- future_schedule_executed: {result.get('future_schedule_executed')}",
        f"- existing_post_update_executed: {result.get('existing_post_update_executed')}",
        f"- delete_executed: {result.get('delete_executed')}",
        f"- approval_token_consumed: {result.get('approval_token_consumed')}",
        f"- freeze_after_run_executed: {result.get('freeze_after_run_executed')}",
        f"- safe_stop: {result.get('safe_stop')}",
        "",
        "## Errors",
    ]
    errs = result.get("errors", [])
    if errs:
        lines.extend(f"- {e}" for e in errs)
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls6b_wordpress_one_shot_draft_creation_policy.json")
    p.add_argument("--payload", default="exchange/logs/start_ls4_wordpress_draft_payload_preview.json")
    p.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    p.add_argument("--ls3-result", default="exchange/logs/start_ls3_wordpress_credential_ready_result.json")
    p.add_argument("--ls4-result", default="exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json")
    p.add_argument("--ls5-result", default="exchange/logs/start_ls5_one_shot_draft_approval_result.json")
    p.add_argument("--ls6a-ready-result", default="exchange/logs/start_ls6a_one_shot_draft_actual_approval_ready_result.json")
    p.add_argument("--ls6b-prep-result", default="exchange/logs/start_ls6b_prep_one_shot_draft_creation_runner_result.json")
    p.add_argument("--approval", default="exchange/human_review/start_ls6a_one_shot_draft_actual_approval.json")
    p.add_argument("--lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    p.add_argument("--output", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_result.json")
    p.add_argument("--report", default="reports/start_ls6b_wordpress_one_shot_draft_creation_report.md")
    p.add_argument("--execute", action="store_true")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    result = run_phase(
        policy_path=Path(a.policy),
        payload_path=Path(a.payload),
        credential_env_path=Path(a.credential_env),
        ls3_result_path=Path(a.ls3_result),
        ls4_result_path=Path(a.ls4_result),
        ls5_result_path=Path(a.ls5_result),
        ls6a_ready_result_path=Path(a.ls6a_ready_result),
        ls6b_prep_result_path=Path(a.ls6b_prep_result),
        approval_path=Path(a.approval),
        lock_path=Path(a.lock),
        execute=a.execute,
    )

    output_path = Path(a.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, Path(a.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
