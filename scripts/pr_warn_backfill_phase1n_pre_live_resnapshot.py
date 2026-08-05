#!/usr/bin/env python3
"""PR WARN Backfill Phase 1N pre-live resnapshot runner (read-only GET only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import requests

ROOT = Path(__file__).resolve().parents[1]
TARGET_POST_ID = 101
PHASE = "PR_WARN_BACKFILL_PHASE1N"
VALID_MINUTES = 30

DEFAULT_POLICY_LOG = ROOT / "exchange/logs/pr_warn_backfill_phase1m_101_policy_dry_run.json"
DEFAULT_TEMPLATE = ROOT / "exchange/examples/pr_warn_backfill_phase1m_final_live_approval.template.json"
DEFAULT_ROLLBACK_SNAPSHOT = ROOT / "exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json"
DEFAULT_ROLLBACK_SNAPSHOT_RESULT = ROOT / "exchange/logs/pr_warn_backfill_phase1g_101_readonly_snapshot_result.json"
DEFAULT_PHASE1L_PAYLOAD_LOG = ROOT / "exchange/logs/pr_warn_backfill_phase1l_101_live_write_preparation_dry_run.json"
DEFAULT_SNAPSHOT_OUTPUT = ROOT / "exchange/logs/pr_warn_backfill_phase1n_101_pre_live_resnapshot.json"
DEFAULT_RESULT_OUTPUT = ROOT / "exchange/logs/pr_warn_backfill_phase1n_101_pre_live_resnapshot_result.json"

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


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _abort_result(
    *,
    status: str,
    reason: str,
    target_post_id: int,
    result_output: Path,
    mode: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": mode,
        "status": status,
        "reason": reason,
        "target_post_id": target_post_id,
        "wordpress_read_executed": False,
        "wordpress_write_executed": False,
        "live_execution_executed": False,
        "update_count": 0,
        "result_output": str(result_output),
        "next_required_phase": "Phase 1N-FIX or Phase 1N-RETRY",
        "created_at": _to_iso(_now_utc()),
    }
    if extra:
        result.update(extra)
    _write_json(result_output, result)
    return result


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


def _validate_policy_log(policy: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if policy.get("status") != "PASS_FINAL_APPROVAL_AND_RESNAPSHOT_POLICY_REPORTS_ONLY":
        errs.append("policy status must be PASS_FINAL_APPROVAL_AND_RESNAPSHOT_POLICY_REPORTS_ONLY")
    if policy.get("mode") != "REPORTS_ONLY":
        errs.append("policy mode must be REPORTS_ONLY")
    if int(policy.get("target_post_id", -1)) != TARGET_POST_ID:
        errs.append("policy target_post_id must be 101")
    return errs


def _validate_template(template: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if template.get("template_only") is not True:
        errs.append("template_only must be true")
    if template.get("approved") is not False:
        errs.append("approved must be false")
    if template.get("wordpress_live_write_allowed") is not False:
        errs.append("wordpress_live_write_allowed must be false")
    if int(template.get("target_post_id", -1)) != TARGET_POST_ID:
        errs.append("template target_post_id must be 101")
    if int(template.get("max_live_updates", -1)) != 1:
        errs.append("template max_live_updates must be 1")
    if template.get("allowed_changed_fields") != ["content"]:
        errs.append("template allowed_changed_fields must be ['content']")
    return errs


def _validate_rollback_snapshot(snapshot: dict[str, Any], snapshot_result: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if snapshot_result.get("status") != "PASS_READONLY_SNAPSHOT":
        errs.append("rollback snapshot result status must be PASS_READONLY_SNAPSHOT")
    if int(snapshot.get("fetched_post_id", -1)) != TARGET_POST_ID:
        errs.append("rollback snapshot fetched_post_id must be 101")
    if snapshot.get("status_from_wp") != "draft":
        errs.append("rollback snapshot status_from_wp must be draft")
    if not snapshot.get("content_hash"):
        errs.append("rollback snapshot content_hash is required")
    return errs


def _validate_phase1l_payload_log(payload_log: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if payload_log.get("payload_changed_fields") != ["content"]:
        errs.append("phase1l payload_changed_fields must be ['content']")
    return errs


def _build_snapshot(
    *,
    post_id: int,
    data: dict[str, Any],
    rollback_snapshot: dict[str, Any],
    rollback_snapshot_path: Path,
    fetched_at: datetime,
    valid_until: datetime,
    status: str,
) -> dict[str, Any]:
    content = _extract_content(data)

    title_rendered = ""
    title_data = data.get("title")
    if isinstance(title_data, dict):
        title_rendered = str(title_data.get("rendered", ""))
    elif isinstance(title_data, str):
        title_rendered = title_data

    modified = data.get("modified_gmt") or data.get("modified")
    content_hash = _sha256_text(content)

    return {
        "phase": PHASE,
        "mode": "READ_ONLY_GET",
        "status": status,
        "target_post_id": post_id,
        "fetched_post_id": int(data.get("id", -1)),
        "title": title_rendered,
        "status_from_wp": data.get("status"),
        "link": data.get("link"),
        "slug": data.get("slug"),
        "modified": modified,
        "categories": data.get("categories") if isinstance(data.get("categories"), list) else [],
        "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
        "featured_media": data.get("featured_media"),
        "content": content,
        "content_hash": content_hash,
        "title_hash": _sha256_text(title_rendered),
        "content_length": len(content),
        "fetched_at": _to_iso(fetched_at),
        "valid_until": _to_iso(valid_until),
        "valid_minutes": VALID_MINUTES,
        "source": "WordPress GET only",
        "compared_to_rollback_snapshot_path": str(rollback_snapshot_path),
        "rollback_snapshot_content_hash": rollback_snapshot.get("content_hash"),
        "rollback_snapshot_modified": rollback_snapshot.get("modified"),
        "modified_matches_rollback_snapshot": modified == rollback_snapshot.get("modified"),
        "content_hash_matches_rollback_snapshot": content_hash == rollback_snapshot.get("content_hash"),
        "wordpress_read_executed": True,
        "wordpress_write_executed": False,
        "live_execution_executed": False,
        "update_count": 0,
    }


def run(
    *,
    post_id: int,
    mode: str,
    policy_log_path: Path,
    template_path: Path,
    rollback_snapshot_path: Path,
    rollback_snapshot_result_path: Path,
    phase1l_payload_log_path: Path,
    snapshot_output: Path,
    result_output: Path,
    env: Mapping[str, str] | None = None,
    get_func: Callable[..., _ResponseLike] | None = None,
) -> dict[str, Any]:
    if post_id != TARGET_POST_ID:
        return _abort_result(
            status="ABORT_INVALID_TARGET_POST_ID",
            reason="post_id must be 101",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
        )

    if mode != "READ_ONLY_GET":
        return _abort_result(
            status="ABORT_UNSUPPORTED_MODE",
            reason="mode must be READ_ONLY_GET",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
        )

    for path, status, reason in [
        (policy_log_path, "ABORT_MISSING_POLICY_LOG", "policy log not found"),
        (template_path, "ABORT_MISSING_TEMPLATE", "template not found"),
        (rollback_snapshot_path, "ABORT_MISSING_ROLLBACK_SNAPSHOT", "rollback snapshot not found"),
        (rollback_snapshot_result_path, "ABORT_MISSING_ROLLBACK_SNAPSHOT_RESULT", "rollback snapshot result not found"),
        (phase1l_payload_log_path, "ABORT_MISSING_PHASE1L_PAYLOAD_LOG", "phase1l payload log not found"),
    ]:
        if not path.exists():
            return _abort_result(
                status=status,
                reason=f"{reason}: {path}",
                target_post_id=post_id,
                result_output=result_output,
                mode=mode,
            )

    policy = _load_json(policy_log_path)
    policy_errs = _validate_policy_log(policy)
    if policy_errs:
        return _abort_result(
            status="ABORT_POLICY_LOG_VALIDATION_FAILED",
            reason="policy log validation failed",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
            extra={"errors": policy_errs},
        )

    template = _load_json(template_path)
    template_errs = _validate_template(template)
    if template_errs:
        return _abort_result(
            status="ABORT_TEMPLATE_VALIDATION_FAILED",
            reason="template validation failed",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
            extra={"errors": template_errs},
        )

    rollback_snapshot = _load_json(rollback_snapshot_path)
    rollback_snapshot_result = _load_json(rollback_snapshot_result_path)
    rollback_errs = _validate_rollback_snapshot(rollback_snapshot, rollback_snapshot_result)
    if rollback_errs:
        return _abort_result(
            status="ABORT_ROLLBACK_SNAPSHOT_VALIDATION_FAILED",
            reason="rollback snapshot validation failed",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
            extra={"errors": rollback_errs},
        )

    phase1l_payload_log = _load_json(phase1l_payload_log_path)
    payload_errs = _validate_phase1l_payload_log(phase1l_payload_log)
    if payload_errs:
        return _abort_result(
            status="ABORT_PHASE1L_PAYLOAD_SCOPE_INVALID",
            reason="phase1l payload scope validation failed",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
            extra={"errors": payload_errs},
        )

    env_map = dict(os.environ if env is None else env)
    missing_env = [k for k in REQUIRED_ENV_KEYS if not str(env_map.get(k, "")).strip()]
    if missing_env:
        return _abort_result(
            status="ABORT_MISSING_WORDPRESS_ENV",
            reason="required wordpress env is missing",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
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
        return _abort_result(
            status="ABORT_WORDPRESS_GET_FAILED",
            reason=f"WordPress GET failed: {exc}",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
        )

    if int(getattr(response, "status_code", 0)) != 200:
        return _abort_result(
            status="ABORT_WORDPRESS_GET_FAILED",
            reason="WordPress GET returned non-200",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
            extra={"response_status_code": getattr(response, "status_code", None)},
        )

    data = response.json() if hasattr(response, "json") else {}
    if not isinstance(data, dict):
        return _abort_result(
            status="ABORT_INVALID_GET_RESPONSE",
            reason="GET response is not a JSON object",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
        )

    fetched_post_id = int(data.get("id", -1))
    fetched_status = data.get("status")
    fetched_at = _now_utc()
    valid_until = fetched_at + timedelta(minutes=VALID_MINUTES)

    provisional_status = "PASS_PRE_LIVE_RESNAPSHOT"
    if fetched_post_id != TARGET_POST_ID:
        provisional_status = "ABORT_FETCHED_POST_ID_MISMATCH"
    elif fetched_status != "draft":
        provisional_status = "ABORT_FETCHED_STATUS_NOT_DRAFT"

    snapshot = _build_snapshot(
        post_id=post_id,
        data=data,
        rollback_snapshot=rollback_snapshot,
        rollback_snapshot_path=rollback_snapshot_path,
        fetched_at=fetched_at,
        valid_until=valid_until,
        status=provisional_status,
    )

    if provisional_status == "PASS_PRE_LIVE_RESNAPSHOT":
        if snapshot["modified_matches_rollback_snapshot"] is not True:
            snapshot["status"] = "ABORT_PRE_LIVE_RESNAPSHOT_MODIFIED_DIFF"
        elif snapshot["content_hash_matches_rollback_snapshot"] is not True:
            snapshot["status"] = "ABORT_PRE_LIVE_RESNAPSHOT_CONTENT_HASH_DIFF"

    try:
        _write_json(snapshot_output, snapshot)
    except Exception as exc:  # pragma: no cover
        return _abort_result(
            status="ABORT_PRE_LIVE_RESNAPSHOT_SAVE_FAILED",
            reason=f"snapshot save failed: {exc}",
            target_post_id=post_id,
            result_output=result_output,
            mode=mode,
        )

    final_status = snapshot["status"]
    reason = "pre-live resnapshot pass"
    if final_status != "PASS_PRE_LIVE_RESNAPSHOT":
        reason_map = {
            "ABORT_FETCHED_POST_ID_MISMATCH": "fetched post_id mismatch",
            "ABORT_FETCHED_STATUS_NOT_DRAFT": "fetched status is not draft",
            "ABORT_PRE_LIVE_RESNAPSHOT_MODIFIED_DIFF": "modified differs from rollback snapshot",
            "ABORT_PRE_LIVE_RESNAPSHOT_CONTENT_HASH_DIFF": "content_hash differs from rollback snapshot",
        }
        reason = reason_map.get(final_status, "pre-live resnapshot failed")

    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": "READ_ONLY_GET",
        "status": final_status,
        "reason": reason,
        "target_post_id": post_id,
        "fetched_post_id": snapshot.get("fetched_post_id"),
        "wordpress_read_executed": True,
        "wordpress_write_executed": False,
        "live_execution_executed": False,
        "update_count": 0,
        "snapshot_output": str(snapshot_output),
        "result_output": str(result_output),
        "content_length": snapshot.get("content_length"),
        "content_hash": snapshot.get("content_hash"),
        "rollback_content_hash": snapshot.get("rollback_snapshot_content_hash"),
        "modified": snapshot.get("modified"),
        "rollback_modified": snapshot.get("rollback_snapshot_modified"),
        "modified_matches": snapshot.get("modified_matches_rollback_snapshot"),
        "content_hash_matches": snapshot.get("content_hash_matches_rollback_snapshot"),
        "status_draft": snapshot.get("status_from_wp") == "draft",
        "valid_minutes": VALID_MINUTES,
        "valid_until": snapshot.get("valid_until"),
        "next_required_phase": "Phase 1N-FIX",
        "created_at": _to_iso(_now_utc()),
    }

    _write_json(result_output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1N pre-live resnapshot runner (read-only GET)")
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--mode", choices=["READ_ONLY_GET"], required=True)
    parser.add_argument("--policy-log", default=str(DEFAULT_POLICY_LOG))
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--rollback-snapshot", default=str(DEFAULT_ROLLBACK_SNAPSHOT))
    parser.add_argument("--rollback-snapshot-result", default=str(DEFAULT_ROLLBACK_SNAPSHOT_RESULT))
    parser.add_argument("--phase1l-payload-log", default=str(DEFAULT_PHASE1L_PAYLOAD_LOG))
    parser.add_argument("--snapshot-output", default=str(DEFAULT_SNAPSHOT_OUTPUT))
    parser.add_argument("--result-output", default=str(DEFAULT_RESULT_OUTPUT))
    args = parser.parse_args()

    result = run(
        post_id=args.post_id,
        mode=args.mode,
        policy_log_path=Path(args.policy_log),
        template_path=Path(args.template),
        rollback_snapshot_path=Path(args.rollback_snapshot),
        rollback_snapshot_result_path=Path(args.rollback_snapshot_result),
        phase1l_payload_log_path=Path(args.phase1l_payload_log),
        snapshot_output=Path(args.snapshot_output),
        result_output=Path(args.result_output),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "PASS_PRE_LIVE_RESNAPSHOT":
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
