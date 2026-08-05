#!/usr/bin/env python3
"""Phase 1G read-only snapshot runner for post_id=101.

Safety guarantees:
- Only READ_ONLY_GET mode is supported.
- Only post_id=101 is allowed.
- Only WordPress GET is used.
- No WordPress write is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import requests

ROOT = Path(__file__).resolve().parents[1]
TARGET_POST_ID = 101
PHASE = "PR_WARN_BACKFILL_PHASE1G_READONLY_SNAPSHOT"

DEFAULT_APPROVAL = ROOT / "exchange/human_review/pr_warn_backfill_phase1_101_human_approval.approved.json"
DEFAULT_SNAPSHOT_OUTPUT = ROOT / "exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json"
DEFAULT_RESULT_OUTPUT = ROOT / "exchange/logs/pr_warn_backfill_phase1g_101_readonly_snapshot_result.json"

REQUIRED_ENV_KEYS = [
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
]


class _ResponseLike:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(
    *,
    status: str,
    reason: str,
    target_post_id: int,
    result_output: Path,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": "READ_ONLY_GET",
        "status": status,
        "reason": reason,
        "target_post_id": target_post_id,
        "wordpress_read_executed": False,
        "wordpress_write_executed": False,
        "update_count": 0,
        "created_at": _now_iso(),
    }
    if extra:
        result.update(extra)
    _write_json(result_output, result)
    result["result_output"] = str(result_output)
    return result


def _validate_approval(approval: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if approval.get("approved") is not True:
        errs.append("approved must be true")
    if approval.get("wordpress_write_allowed") is not True:
        errs.append("wordpress_write_allowed must be true")
    if int(approval.get("target_post_id", -1)) != TARGET_POST_ID:
        errs.append("target_post_id must be 101")
    if int(approval.get("max_live_updates", -1)) != 1:
        errs.append("max_live_updates must be 1")
    return errs


def _extract_content(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, dict):
        raw = content.get("raw")
        if isinstance(raw, str) and raw:
            return raw
        rendered = content.get("rendered")
        if isinstance(rendered, str):
            return rendered
    if isinstance(content, str):
        return content
    return ""


def _default_get(
    *,
    base_url: str,
    post_id: int,
    username: str,
    app_password: str,
) -> _ResponseLike:
    url = f"{base_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    response = requests.get(
        url,
        params={"context": "edit"},
        auth=(username, app_password),
        timeout=20,
        headers={"Content-Type": "application/json"},
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return _ResponseLike(status_code=response.status_code, payload=payload)


def run(
    *,
    post_id: int,
    mode: str,
    approval_path: Path,
    snapshot_output: Path,
    result_output: Path,
    env: Mapping[str, str] | None = None,
    get_func: Callable[..., _ResponseLike] | None = None,
) -> dict[str, Any]:
    if post_id != TARGET_POST_ID:
        return _abort(
            status="ABORT_INVALID_TARGET_POST_ID",
            reason="post_id must be 101",
            target_post_id=post_id,
            result_output=result_output,
        )

    if mode != "READ_ONLY_GET":
        return _abort(
            status="ABORT_UNSUPPORTED_MODE",
            reason="mode must be READ_ONLY_GET",
            target_post_id=post_id,
            result_output=result_output,
        )

    if not approval_path.exists():
        return _abort(
            status="ABORT_MISSING_APPROVAL_FILE",
            reason=f"approval file not found: {approval_path}",
            target_post_id=post_id,
            result_output=result_output,
        )

    approval = _load_json(approval_path)
    approval_errs = _validate_approval(approval)
    if approval_errs:
        return _abort(
            status="ABORT_APPROVAL_VALIDATION_FAILED",
            reason="approval validation failed",
            target_post_id=post_id,
            result_output=result_output,
            extra={"errors": approval_errs},
        )

    env_map = dict(os.environ if env is None else env)
    missing_env = [k for k in REQUIRED_ENV_KEYS if not str(env_map.get(k, "")).strip()]
    if missing_env:
        return _abort(
            status="ABORT_MISSING_WORDPRESS_ENV",
            reason="required wordpress env is missing",
            target_post_id=post_id,
            result_output=result_output,
            extra={"missing_env_keys": missing_env},
        )

    getter = get_func or _default_get

    try:
        response = getter(
            base_url=env_map["WORDPRESS_BASE_URL"],
            post_id=post_id,
            username=env_map["WORDPRESS_USERNAME"],
            app_password=env_map["WORDPRESS_APP_PASSWORD"],
        )
    except Exception as exc:  # pragma: no cover
        return _abort(
            status="ABORT_WORDPRESS_GET_FAILED",
            reason=f"read-only GET failed: {exc}",
            target_post_id=post_id,
            result_output=result_output,
        )

    if int(getattr(response, "status_code", 0)) != 200:
        return _abort(
            status="ABORT_WORDPRESS_GET_FAILED",
            reason="read-only GET returned non-200 status",
            target_post_id=post_id,
            result_output=result_output,
            extra={"response_status_code": getattr(response, "status_code", None)},
        )

    data = response.json() if hasattr(response, "json") else {}
    if not isinstance(data, dict):
        return _abort(
            status="ABORT_INVALID_GET_RESPONSE",
            reason="GET response is not a JSON object",
            target_post_id=post_id,
            result_output=result_output,
        )

    fetched_post_id = int(data.get("id", -1))
    if fetched_post_id != TARGET_POST_ID:
        return _abort(
            status="ABORT_FETCHED_POST_ID_MISMATCH",
            reason="fetched post_id does not match target",
            target_post_id=post_id,
            result_output=result_output,
            extra={"fetched_post_id": data.get("id")},
        )

    title_rendered = ""
    title_data = data.get("title")
    if isinstance(title_data, dict):
        title_rendered = str(title_data.get("rendered", ""))
    elif isinstance(title_data, str):
        title_rendered = title_data

    content_text = _extract_content(data)
    snapshot: dict[str, Any] = {
        "phase": PHASE,
        "mode": "READ_ONLY_GET",
        "status": "PASS_READONLY_SNAPSHOT",
        "target_post_id": post_id,
        "fetched_post_id": fetched_post_id,
        "title": title_rendered,
        "content": content_text,
        "status_from_wp": data.get("status"),
        "link": data.get("link"),
        "slug": data.get("slug"),
        "modified": data.get("modified_gmt") or data.get("modified"),
        "categories": data.get("categories") if isinstance(data.get("categories"), list) else [],
        "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
        "featured_media": data.get("featured_media"),
        "content_hash": _sha256_text(content_text),
        "title_hash": _sha256_text(title_rendered),
        "content_length": len(content_text),
        "fetched_at": _now_iso(),
        "source": "WordPress GET only",
        "rollback_source": "content",
        "wordpress_read_executed": True,
        "wordpress_write_executed": False,
        "update_count": 0,
    }

    _write_json(snapshot_output, snapshot)

    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": "READ_ONLY_GET",
        "status": "PASS_READONLY_SNAPSHOT",
        "target_post_id": post_id,
        "fetched_post_id": fetched_post_id,
        "wordpress_read_executed": True,
        "wordpress_write_executed": False,
        "update_count": 0,
        "snapshot_output": str(snapshot_output),
        "result_output": str(result_output),
        "title": title_rendered,
        "status_from_wp": snapshot["status_from_wp"],
        "link_present": bool(snapshot.get("link")),
        "modified": snapshot["modified"],
        "content_length": snapshot["content_length"],
        "content_hash": snapshot["content_hash"],
        "title_hash": snapshot["title_hash"],
        "notes": [
            "No WordPress write executed.",
            "No POST/PUT/PATCH/DELETE executed.",
            "Snapshot content saved to file only (not printed).",
        ],
        "created_at": _now_iso(),
    }

    _write_json(result_output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1G read-only snapshot runner for post_id=101")
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--mode", choices=["READ_ONLY_GET"], required=True)
    parser.add_argument("--approval", default=str(DEFAULT_APPROVAL))
    parser.add_argument("--snapshot-output", default=str(DEFAULT_SNAPSHOT_OUTPUT))
    parser.add_argument("--result-output", default=str(DEFAULT_RESULT_OUTPUT))
    args = parser.parse_args()

    result = run(
        post_id=args.post_id,
        mode=args.mode,
        approval_path=Path(args.approval),
        snapshot_output=Path(args.snapshot_output),
        result_output=Path(args.result_output),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "PASS_READONLY_SNAPSHOT":
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
