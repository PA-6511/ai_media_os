#!/usr/bin/env python3
"""PR WARN Backfill Phase 1F-LIVE-ROUTE runner scaffold (DRY_RUN_FIRST).

This phase prepares a LIVE-capable route but does not enable LIVE execution.
- Single target only: post_id=101.
- Approval and phase0 constraints are strictly validated.
- DRY_RUN emits payload/snapshot/rollback/post-live verification plans.
- LIVE mode always aborts in this phase.
- No WordPress API request is sent.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET_POST_ID = 101

DEFAULT_APPROVAL = ROOT / "exchange/human_review/pr_warn_backfill_phase1_101_human_approval.approved.json"
DEFAULT_PHASE0 = ROOT / "reports/pr_warn_backfill_phase0_dry_run_20260614.json"
DEFAULT_PHASE1D_DRY = ROOT / "exchange/logs/pr_warn_backfill_phase1d_101_dry_run.json"
DEFAULT_PHASE1F_ABORT = ROOT / "exchange/logs/pr_warn_backfill_phase1f_101_live_result.json"
DEFAULT_OUT_DIR = ROOT / "exchange/logs"

PHASE = "PR_WARN_BACKFILL_PHASE1F_LIVE_ROUTE"
NOTICE_TEXT = "PR：本記事には広告が含まれます。"
FORBIDDEN_CHANGED_FIELDS = [
    "title",
    "url",
    "cta",
    "featured_image",
    "status",
    "category",
    "tag",
    "publish",
]


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
    mode: str,
    post_id: int,
    output_path: Path,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": mode,
        "status": status,
        "reason": reason,
        "target_post_id": post_id,
        "live_route_available": False,
        "live_mode_enabled": False,
        "wordpress_write_executed": False,
        "update_count": 0,
        "changed_fields": [],
        "forbidden_changed_fields": FORBIDDEN_CHANGED_FIELDS,
        "created_at": _now_iso(),
    }
    if extra:
        result.update(extra)
    _write_json(output_path, result)
    result["output_path"] = str(output_path)
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


def _find_phase0_target(phase0: dict[str, Any], post_id: int) -> dict[str, Any] | None:
    for target in phase0.get("targets", []):
        if int(target.get("post_id", -1)) == post_id:
            return target
    return None


def _validate_phase0_notice_only(target: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if target.get("dry_run_strategy") != "insert_after_h1":
        errs.append("dry_run_strategy must be insert_after_h1")

    diff = target.get("diff_preview")
    if not isinstance(diff, list) or not diff:
        errs.append("diff_preview is required")
        return errs

    removed = [line for line in diff if isinstance(line, str) and line.startswith("-") and not line.startswith("---")]
    added = [line for line in diff if isinstance(line, str) and line.startswith("+") and not line.startswith("+++")]

    if len(removed) != 1:
        errs.append("diff must have exactly one removed content line")
    if len(added) != 1:
        errs.append("diff must have exactly one added content line")

    if removed and "<h1>" not in removed[0]:
        errs.append("removed line must include h1")

    if added:
        add = added[0]
        if "<h1>" not in add:
            errs.append("added line must include h1")
        if "pr-notice" not in add:
            errs.append("added line must include pr-notice")

    return errs


def _validate_phase1d_dry_run(dry: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if dry.get("status") != "PASS_DRY_RUN_ONLY":
        errs.append("phase1d dry-run status must be PASS_DRY_RUN_ONLY")
    if int(dry.get("target_post_id", -1)) != TARGET_POST_ID:
        errs.append("phase1d target_post_id must be 101")
    if dry.get("wordpress_write_executed") is not False:
        errs.append("phase1d wordpress_write_executed must be false")
    if dry.get("proposed_changed_fields") != ["content"]:
        errs.append("phase1d proposed_changed_fields must be ['content']")
    return errs


def run(
    *,
    post_id: int,
    mode: str,
    approval_path: Path,
    phase0_path: Path,
    phase1d_dry_run_path: Path,
    phase1f_abort_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if post_id != TARGET_POST_ID:
        return _abort(
            status="ABORT_INVALID_TARGET_POST_ID",
            reason="post_id must be 101",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
        )

    if mode == "LIVE":
        return _abort(
            status="ABORT_LIVE_NOT_ENABLED_IN_LIVE_ROUTE_PHASE",
            reason="LIVE is intentionally disabled in Phase 1F-LIVE-ROUTE",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
            extra={"next_required_phase": "Phase 1G or Phase 1F-LIVE-ENABLE"},
        )

    if not approval_path.exists():
        return _abort(
            status="ABORT_MISSING_APPROVAL_FILE",
            reason=f"approval file not found: {approval_path}",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
        )
    if not phase0_path.exists():
        return _abort(
            status="ABORT_MISSING_PHASE0_FILE",
            reason=f"phase0 file not found: {phase0_path}",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
        )
    if not phase1d_dry_run_path.exists():
        return _abort(
            status="ABORT_MISSING_PHASE1D_DRY_RUN_LOG",
            reason=f"phase1d dry-run log not found: {phase1d_dry_run_path}",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
        )

    approval = _load_json(approval_path)
    approval_errs = _validate_approval(approval)
    if approval_errs:
        return _abort(
            status="ABORT_APPROVAL_VALIDATION_FAILED",
            reason="approval validation failed",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
            extra={"errors": approval_errs},
        )

    phase0 = _load_json(phase0_path)
    target = _find_phase0_target(phase0, post_id)
    if target is None:
        return _abort(
            status="ABORT_PHASE0_TARGET_NOT_FOUND",
            reason="post_id=101 not found in phase0 targets",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
        )

    diff_errs = _validate_phase0_notice_only(target)
    if diff_errs:
        return _abort(
            status="ABORT_PHASE0_DIFF_SCOPE_VIOLATION",
            reason="phase0 diff contains disallowed changes",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
            extra={"errors": diff_errs},
        )

    phase1d_dry = _load_json(phase1d_dry_run_path)
    dry_errs = _validate_phase1d_dry_run(phase1d_dry)
    if dry_errs:
        return _abort(
            status="ABORT_PHASE1D_DRY_RUN_VALIDATION_FAILED",
            reason="phase1d dry-run validation failed",
            mode=mode,
            post_id=post_id,
            output_path=output_path,
            extra={"errors": dry_errs},
        )

    prior_abort_status = None
    if phase1f_abort_path.exists():
        try:
            prior_abort_status = _load_json(phase1f_abort_path).get("status")
        except Exception:
            prior_abort_status = None

    snapshot_plan = {
        "required_before_live": True,
        "fields": ["post_id", "title", "content", "status", "link", "modified"],
        "snapshot_output_path": "exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json",
        "if_snapshot_failed": "live_forbidden",
    }

    rollback_plan = {
        "enabled_for_live_phase": True,
        "single_item_only": True,
        "target_post_id": 101,
        "restore_from_snapshot_field": "content",
        "verify_after_rollback": True,
        "rollback_log_path": "exchange/logs/pr_warn_backfill_phase1g_101_rollback_result.json",
    }

    post_live_verification_plan = {
        "fetch_target_post_again": True,
        "verify_pr_notice_inserted": True,
        "verify_immutable_fields": ["title", "url", "cta", "featured_image", "status", "category", "tag"],
        "verify_update_count_equals": 1,
        "run_draft_check": True,
        "verify_pr_warn_decrease_for_target": True,
        "if_any_mismatch": "stop_additional_execution",
    }

    result: dict[str, Any] = {
        "phase": PHASE,
        "mode": "DRY_RUN",
        "status": "PASS_DRY_RUN_FIRST_ONLY",
        "target_post_id": post_id,
        "title": target.get("title"),
        "approval_file": str(approval_path),
        "approved": True,
        "wordpress_write_allowed": True,
        "max_live_updates": 1,
        "phase0_source": str(phase0_path),
        "prior_phase1f_abort_log": str(phase1f_abort_path),
        "prior_phase1f_abort_status": prior_abort_status,
        "live_route_available": False,
        "live_mode_enabled": False,
        "wordpress_write_executed": False,
        "update_count": 0,
        "proposed_notice_text": NOTICE_TEXT,
        "proposed_insert_position": "after_h1",
        "proposed_changed_fields": ["content"],
        "forbidden_changed_fields": FORBIDDEN_CHANGED_FIELDS,
        "payload_preview": {
            "target_post_id": 101,
            "operation": "content_patch_preview_only",
            "patch": {
                "insert_position": "after_h1",
                "notice_text": NOTICE_TEXT,
            },
            "write_enabled": False,
        },
        "snapshot_plan": snapshot_plan,
        "rollback_plan": rollback_plan,
        "post_live_verification_plan": post_live_verification_plan,
        "safety_flags": {
            "single_post_only": True,
            "max_live_updates_equals_one": True,
            "content_only_change": True,
            "forbidden_field_updates_blocked": True,
            "bulk_backfill_forbidden": True,
            "publish_forbidden": True,
            "wordpress_api_send_disabled_in_phase": True,
        },
        "created_at": _now_iso(),
    }

    _write_json(output_path, result)
    result["output_path"] = str(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="PR WARN Backfill Phase 1F-LIVE-ROUTE runner scaffold (dry-run first)")
    parser.add_argument("--post-id", type=int, required=True, help="Target post id (must be 101)")
    parser.add_argument("--mode", choices=["DRY_RUN", "LIVE"], default="DRY_RUN")
    parser.add_argument("--approval", default=str(DEFAULT_APPROVAL), help="Approved human review file")
    parser.add_argument("--phase0", default=str(DEFAULT_PHASE0), help="Phase0 dry-run source file")
    parser.add_argument("--phase1d-dry-run", default=str(DEFAULT_PHASE1D_DRY), help="Phase1D dry-run log")
    parser.add_argument("--prior-phase1f-abort", default=str(DEFAULT_PHASE1F_ABORT), help="Prior Phase1F abort log")
    parser.add_argument("--output", default=None, help="Output path")
    args = parser.parse_args()

    if args.output:
        output_path = Path(args.output)
    else:
        suffix = "dry_run" if args.mode == "DRY_RUN" else "live_abort"
        output_path = DEFAULT_OUT_DIR / f"pr_warn_backfill_phase1f_live_route_{args.post_id}_{suffix}.json"

    result = run(
        post_id=args.post_id,
        mode=args.mode,
        approval_path=Path(args.approval),
        phase0_path=Path(args.phase0),
        phase1d_dry_run_path=Path(args.phase1d_dry_run),
        phase1f_abort_path=Path(args.prior_phase1f_abort),
        output_path=output_path,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if str(result.get("status", "")).startswith("PASS"):
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
