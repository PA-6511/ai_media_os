#!/usr/bin/env python3
"""PR WARN Backfill Phase 1J dedicated live write runner scaffold (DRY_RUN_ONLY).

Phase 1J purpose:
- Create a dedicated runner for future single-post live write.
- Keep write path blocked in this phase.
- Validate approval/snapshot preconditions and emit dry-run evidence only.
- Never execute WordPress API read/write in this phase.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET_POST_ID = 101

PHASE = "PR_WARN_BACKFILL_PHASE1J"
FORBIDDEN_CHANGED_FIELDS = [
    "title",
    "status",
    "slug",
    "link",
    "categories",
    "tags",
    "featured_media",
    "publish",
    "excerpt",
    "author",
    "date",
]

DEFAULT_APPROVAL = ROOT / "exchange/human_review/pr_warn_backfill_phase1_101_human_approval.approved.json"
DEFAULT_FINAL_LIVE_APPROVAL = ROOT / "exchange/examples/pr_warn_backfill_phase1i_final_live_approval.example.json"
DEFAULT_SNAPSHOT = ROOT / "exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json"
DEFAULT_SNAPSHOT_RESULT = ROOT / "exchange/logs/pr_warn_backfill_phase1g_101_readonly_snapshot_result.json"
DEFAULT_PHASE1F_DRY_RUN = ROOT / "exchange/logs/pr_warn_backfill_phase1f_live_route_101_dry_run.json"
DEFAULT_RESULT_OUTPUT = ROOT / "exchange/logs/pr_warn_backfill_phase1j_101_live_write_dry_run.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(
    *,
    status: str,
    reason: str,
    post_id: int,
    mode: str,
    output_path: Path,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": mode,
        "status": status,
        "reason": reason,
        "target_post_id": post_id,
        "dedicated_live_write_runner_created": True,
        "existing_runners_modified": False,
        "pre_live_resnapshot_required": True,
        "pre_live_resnapshot_executed": False,
        "live_write_supported_in_this_phase": False,
        "live_write_blocked_reason": "PHASE1J_DRY_RUN_ONLY",
        "proposed_changed_fields": ["content"],
        "forbidden_changed_fields": FORBIDDEN_CHANGED_FIELDS,
        "snapshot_available": False,
        "rollback_snapshot_available": False,
        "wordpress_read_executed": False,
        "wordpress_write_executed": False,
        "live_execution_executed": False,
        "update_count": 0,
        "created_at": _now_iso(),
    }
    if extra:
        result.update(extra)
    _write_json(output_path, result)
    result["output_path"] = str(output_path)
    return result


def _validate_primary_approval(approval: dict[str, Any]) -> list[str]:
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


def _validate_final_live_approval_example(example: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if example.get("approved") is not False:
        errs.append("final live approval example approved must be false")
    if example.get("wordpress_live_write_allowed") is not False:
        errs.append("final live approval example wordpress_live_write_allowed must be false")
    if int(example.get("target_post_id", -1)) != TARGET_POST_ID:
        errs.append("final live approval example target_post_id must be 101")
    if int(example.get("max_live_updates", -1)) != 1:
        errs.append("final live approval example max_live_updates must be 1")
    if example.get("allowed_changed_fields") != ["content"]:
        errs.append("final live approval example allowed_changed_fields must be ['content']")
    return errs


def _validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if int(snapshot.get("fetched_post_id", -1)) != TARGET_POST_ID:
        errs.append("snapshot fetched_post_id must be 101")
    if snapshot.get("status_from_wp") != "draft":
        errs.append("snapshot status_from_wp must be draft")
    if not snapshot.get("content_hash"):
        errs.append("snapshot content_hash is required")
    content_length = snapshot.get("content_length")
    if not isinstance(content_length, int) or content_length <= 0:
        errs.append("snapshot content_length must be positive int")
    if int(snapshot.get("target_post_id", -1)) != TARGET_POST_ID:
        errs.append("snapshot target_post_id must be 101")
    return errs


def _validate_snapshot_result(snapshot_result: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if snapshot_result.get("status") != "PASS_READONLY_SNAPSHOT":
        errs.append("snapshot result status must be PASS_READONLY_SNAPSHOT")
    return errs


def _validate_phase1f_dry_run(dry: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if dry.get("status") != "PASS_DRY_RUN_FIRST_ONLY":
        errs.append("phase1f dry run status must be PASS_DRY_RUN_FIRST_ONLY")
    if int(dry.get("target_post_id", -1)) != TARGET_POST_ID:
        errs.append("phase1f dry run target_post_id must be 101")
    if dry.get("proposed_changed_fields") != ["content"]:
        errs.append("phase1f dry run proposed_changed_fields must be ['content']")
    if dry.get("wordpress_write_executed") is not False:
        errs.append("phase1f dry run wordpress_write_executed must be false")
    if int(dry.get("update_count", -1)) != 0:
        errs.append("phase1f dry run update_count must be 0")
    return errs


def run(
    *,
    post_id: int,
    mode: str,
    approval_path: Path,
    final_live_approval_path: Path,
    snapshot_path: Path,
    snapshot_result_path: Path,
    phase1f_dry_run_path: Path,
    result_output_path: Path,
) -> dict[str, Any]:
    if post_id != TARGET_POST_ID:
        return _abort(
            status="ABORT_INVALID_TARGET_POST_ID",
            reason="post_id must be 101",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )

    if mode != "DRY_RUN":
        return _abort(
            status="ABORT_MODE_NOT_ALLOWED",
            reason="Phase 1J supports DRY_RUN only",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )

    if not approval_path.exists():
        return _abort(
            status="ABORT_MISSING_APPROVAL_FILE",
            reason=f"approval file not found: {approval_path}",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )
    if not final_live_approval_path.exists():
        return _abort(
            status="ABORT_MISSING_FINAL_LIVE_APPROVAL_EXAMPLE",
            reason=f"final live approval example not found: {final_live_approval_path}",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )
    if not snapshot_path.exists():
        return _abort(
            status="ABORT_MISSING_SNAPSHOT_FILE",
            reason=f"snapshot file not found: {snapshot_path}",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )
    if not snapshot_result_path.exists():
        return _abort(
            status="ABORT_MISSING_SNAPSHOT_RESULT_FILE",
            reason=f"snapshot result file not found: {snapshot_result_path}",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )
    if not phase1f_dry_run_path.exists():
        return _abort(
            status="ABORT_MISSING_PHASE1F_DRY_RUN_LOG",
            reason=f"phase1f dry-run log not found: {phase1f_dry_run_path}",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )

    approval = _load_json(approval_path)
    approval_errs = _validate_primary_approval(approval)
    if approval_errs:
        return _abort(
            status="ABORT_APPROVAL_VALIDATION_FAILED",
            reason="approval validation failed",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
            extra={"errors": approval_errs},
        )

    final_live_approval = _load_json(final_live_approval_path)
    final_live_approval_errs = _validate_final_live_approval_example(final_live_approval)
    if final_live_approval_errs:
        return _abort(
            status="ABORT_FINAL_LIVE_APPROVAL_EXAMPLE_INVALID",
            reason="final live approval example validation failed",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
            extra={"errors": final_live_approval_errs},
        )

    snapshot = _load_json(snapshot_path)
    snapshot_errs = _validate_snapshot(snapshot)
    if snapshot_errs:
        return _abort(
            status="ABORT_SNAPSHOT_VALIDATION_FAILED",
            reason="snapshot validation failed",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
            extra={"errors": snapshot_errs},
        )

    snapshot_result = _load_json(snapshot_result_path)
    snapshot_result_errs = _validate_snapshot_result(snapshot_result)
    if snapshot_result_errs:
        return _abort(
            status="ABORT_SNAPSHOT_RESULT_VALIDATION_FAILED",
            reason="snapshot result validation failed",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
            extra={"errors": snapshot_result_errs},
        )

    phase1f_dry = _load_json(phase1f_dry_run_path)
    phase1f_errs = _validate_phase1f_dry_run(phase1f_dry)
    if phase1f_errs:
        return _abort(
            status="ABORT_PHASE1F_DRY_RUN_VALIDATION_FAILED",
            reason="phase1f dry-run validation failed",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
            extra={"errors": phase1f_errs},
        )

    if phase1f_dry.get("proposed_changed_fields") != ["content"]:
        return _abort(
            status="ABORT_FORBIDDEN_FIELD_CHANGE_DETECTED",
            reason="only content field is allowed",
            post_id=post_id,
            mode=mode,
            output_path=result_output_path,
        )

    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": "DRY_RUN",
        "status": "PASS_LIVE_WRITE_RUNNER_DRY_RUN_ONLY",
        "target_post_id": post_id,
        "title": snapshot.get("title"),
        "dedicated_live_write_runner_created": True,
        "existing_runners_modified": False,
        "approval_file": str(approval_path),
        "approved_file_currently_allows_write": True,
        "final_live_approval_path": str(final_live_approval_path),
        "final_live_approval_example_only": True,
        "final_live_approval_approved": False,
        "final_live_write_allowed": False,
        "pre_live_resnapshot_required": True,
        "pre_live_resnapshot_executed": False,
        "abort_if_modified_drift_on_resnapshot": True,
        "abort_if_content_hash_drift_on_resnapshot": True,
        "live_write_supported_in_this_phase": False,
        "live_write_blocked_reason": "PHASE1J_DRY_RUN_ONLY",
        "proposed_changed_fields": ["content"],
        "forbidden_changed_fields": FORBIDDEN_CHANGED_FIELDS,
        "snapshot_available": True,
        "snapshot_content_hash": snapshot.get("content_hash"),
        "snapshot_content_length": snapshot.get("content_length"),
        "snapshot_modified": snapshot.get("modified"),
        "rollback_snapshot_available": True,
        "wordpress_read_executed": False,
        "wordpress_write_executed": False,
        "live_execution_executed": False,
        "update_count": 0,
        "next_required_phase": "Phase 1J-FIX or Phase 1K",
        "missing_for_live_enable": [
            "final live approval active file with approved=true",
            "pre-live resnapshot execution",
            "dedicated live write path implementation and guarded release",
        ],
        "created_at": _now_iso(),
    }

    _write_json(result_output_path, result)
    result["output_path"] = str(result_output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="PR WARN Backfill Phase 1J dedicated live write runner scaffold (dry-run only)")
    parser.add_argument("--post-id", type=int, required=True, help="Target post id (must be 101)")
    parser.add_argument("--mode", default="DRY_RUN", help="Execution mode (must be DRY_RUN in Phase 1J)")
    parser.add_argument("--approval", default=str(DEFAULT_APPROVAL), help="Primary approved file")
    parser.add_argument(
        "--final-live-approval",
        default=str(DEFAULT_FINAL_LIVE_APPROVAL),
        help="Final live approval example file (must remain disabled in this phase)",
    )
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="Read-only snapshot file")
    parser.add_argument("--snapshot-result", default=str(DEFAULT_SNAPSHOT_RESULT), help="Read-only snapshot result file")
    parser.add_argument("--phase1f-dry-run", default=str(DEFAULT_PHASE1F_DRY_RUN), help="Phase1F dry-run log")
    parser.add_argument("--result-output", default=str(DEFAULT_RESULT_OUTPUT), help="Result output path")
    args = parser.parse_args()

    result = run(
        post_id=args.post_id,
        mode=args.mode,
        approval_path=Path(args.approval),
        final_live_approval_path=Path(args.final_live_approval),
        snapshot_path=Path(args.snapshot),
        snapshot_result_path=Path(args.snapshot_result),
        phase1f_dry_run_path=Path(args.phase1f_dry_run),
        result_output_path=Path(args.result_output),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if str(result.get("status", "")).startswith("PASS"):
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
