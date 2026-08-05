#!/usr/bin/env python3
"""Phase 7-5C 1件限定 WordPress実下書き作成（手動実行専用）

安全ポリシー:
- 自動実行禁止（execute_live=True かつ人間実行のみ）
- post_status=draft のみ
- publish/update/delete/export は禁止
- 1件のみ
- 成功/失敗どちらでも証跡を保存
- 実行後は自動再ロック
"""

import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
PHASE7_5B_RESULT = ROOT / "exchange/logs/phase7_5b_live_final_approval_result.json"
PAYLOAD_FILE = ROOT / "exchange/outgoing/wordpress_draft_create_payload.dry_run.json"
OUTPUT_FILE = ROOT / "exchange/logs/phase7_5c_single_draft_create_live_result.json"

VALID_TOKEN = "APPROVE_SINGLE_DRAFT_CREATE_LIVE_ONE_TIME"


class _DummyAuth:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_result(output_path: Path, result: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_result() -> dict[str, Any]:
    return {
        "package_type": "phase7_5c_single_draft_create_live_result",
        "phase": "Phase 7-5C",
        "mode": "MANUAL_ONE_TIME_EXECUTION",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
    }


def _abort(reason: str, output_path: Path, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result = _base_result()
    result.update(
        {
            "status": "ABORT",
            "reason": reason,
            "live_execution_attempted": False,
            "wordpress_post_enabled": False,
            "real_write_enabled": False,
            "wordpress_write_executed": False,
            "relocked_after_execution": True,
            "next_step": "manual_recheck_required",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if extra:
        result.update(extra)
    _save_result(output_path, result)
    return result


def run_live_manual(
    phase7_5b_result_path: Path = PHASE7_5B_RESULT,
    payload_path: Path = PAYLOAD_FILE,
    output_path: Path = OUTPUT_FILE,
    *,
    execute_live: bool = False,
    wordpress_base_url: str | None = None,
    wp_username: str | None = None,
    wp_app_password: str | None = None,
    post_func: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    if not phase7_5b_result_path.exists():
        return _abort(f"phase7_5b result not found: {phase7_5b_result_path}", output_path)

    try:
        p75b = _load_json(phase7_5b_result_path)
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in phase7_5b result: {e}", output_path)

    if p75b.get("status") != "PASS":
        return _abort("phase7_5b status must be PASS", output_path)
    if p75b.get("approval_token") != VALID_TOKEN:
        return _abort("invalid approval_token for live execution", output_path)
    if p75b.get("approval_token_valid") is not True:
        return _abort("approval_token_valid must be true", output_path)
    if p75b.get("all_remaining_items_confirmed") is not True:
        return _abort("all_remaining_items_confirmed must be true", output_path)
    if p75b.get("token_constraints_valid") is not True:
        return _abort("token_constraints_valid must be true", output_path)

    constraints = p75b.get("token_constraints", {})
    if constraints.get("one_time_only") is not True:
        return _abort("token_constraints.one_time_only must be true", output_path)
    if constraints.get("post_status") != "draft":
        return _abort("token_constraints.post_status must be draft", output_path)
    if constraints.get("post_count_limit") != 1:
        return _abort("token_constraints.post_count_limit must be 1", output_path)
    if constraints.get("publish_allowed") is not False:
        return _abort("token_constraints.publish_allowed must be false", output_path)
    if constraints.get("update_allowed") is not False:
        return _abort("token_constraints.update_allowed must be false", output_path)
    if constraints.get("delete_allowed") is not False:
        return _abort("token_constraints.delete_allowed must be false", output_path)
    if constraints.get("export_allowed") is not False:
        return _abort("token_constraints.export_allowed must be false", output_path)

    expires = constraints.get("expires_minutes")
    if not isinstance(expires, int) or not (1 <= expires <= 30):
        return _abort("token_constraints.expires_minutes must be int 1-30", output_path)

    if not payload_path.exists():
        return _abort(f"payload not found: {payload_path}", output_path)

    try:
        payload = _load_json(payload_path)
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in payload: {e}", output_path)

    if payload.get("status") != "draft":
        return _abort("payload.status must be draft", output_path)

    post_payload = {
        "title": payload.get("title", ""),
        "content": payload.get("content", ""),
        "status": "draft",
    }

    if not execute_live:
        return _abort(
            "manual execution flag is false. live execution is intentionally blocked.",
            output_path,
            extra={
                "live_execution_attempted": False,
                "wordpress_post_enabled": False,
                "real_write_enabled": False,
                "next_step": "set_execute_live_true_for_manual_run",
                "payload_preview": post_payload,
            },
        )

    if not wordpress_base_url or not wp_username or not wp_app_password:
        return _abort(
            "wordpress_base_url/wp_username/wp_app_password are required for execute_live",
            output_path,
        )

    endpoint = wordpress_base_url.rstrip("/") + "/wp-json/wp/v2/posts"

    if post_func is None:
        import requests
        from requests.auth import HTTPBasicAuth

        response = requests.post(
            endpoint,
            json=post_payload,
            auth=HTTPBasicAuth(wp_username, wp_app_password),
            timeout=20,
        )
    else:
        response = post_func(
            endpoint,
            json=post_payload,
            auth=_DummyAuth(wp_username, wp_app_password),
            timeout=20,
        )

    status_code = getattr(response, "status_code", None)
    response_json = {}
    try:
        response_json = response.json()
    except Exception:
        response_json = {"raw_text": getattr(response, "text", "")}

    common = _base_result()
    common.update(
        {
            "live_execution_attempted": True,
            "wordpress_post_enabled": True,
            "real_write_enabled": True,
            "endpoint": endpoint,
            "post_payload": post_payload,
            "response_status_code": status_code,
            "response_excerpt": response_json,
            "relocked_after_execution": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    if status_code == 201 and isinstance(response_json, dict) and response_json.get("id"):
        common.update(
            {
                "status": "PASS",
                "reason": "single draft create live execution succeeded",
                "wordpress_write_executed": True,
                "created_post_id": response_json.get("id"),
                "created_post_status": response_json.get("status"),
                "next_step": "manual_verify_and_relock_confirmed",
            }
        )
    else:
        common.update(
            {
                "status": "FAIL",
                "reason": "live execution attempted but response was not success",
                "wordpress_write_executed": False,
                "next_step": "manual_investigation_required",
            }
        )

    _save_result(output_path, common)
    return common


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 7-5C single draft create live manual runner"
    )
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="実際にWordPress POSTを実行する（指定しない場合は安全停止）",
    )
    parser.add_argument("--wordpress-base-url", default=None)
    parser.add_argument("--wp-username", default=None)
    parser.add_argument("--wp-app-password", default=None)
    args = parser.parse_args()

    result = run_live_manual(
        execute_live=args.execute_live,
        wordpress_base_url=args.wordpress_base_url,
        wp_username=args.wp_username,
        wp_app_password=args.wp_app_password,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
