#!/usr/bin/env python3
"""PR WARN Backfill Phase 1D single-item live runner scaffold (DRY_RUN_ONLY).

Safety policy for Phase 1D:
- Only post_id=101 is allowed.
- LIVE mode is not supported in this phase.
- No WordPress API write is executed.
- Approval file must be explicitly true-gated.
- Phase0 diff must indicate PR notice insertion only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET_POST_ID = 101

DEFAULT_PHASE0 = ROOT / "reports/pr_warn_backfill_phase0_dry_run_20260614.json"
DEFAULT_DRY_RUN_SOURCE = ROOT / "exchange/logs/pr_warn_backfill_phase1_101_dry_run.json"
DEFAULT_APPROVAL = ROOT / "exchange/human_review/pr_warn_backfill_phase1_101_human_approval.approved.json"
DEFAULT_OUT_DIR = ROOT / "exchange/logs"

NOTICE_HTML = '<p class="pr-notice">※本記事にはアフィリエイト広告（PR）が含まれます。</p>'
FORBIDDEN_FIELDS = [
    "title",
    "url",
    "cta",
    "featured_image",
    "status",
    "category",
    "tag",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _abort(status: str, reason: str, mode: str, post_id: int, output_path: Path, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "phase": "PR_WARN_BACKFILL_PHASE1D",
        "mode": mode,
        "status": status,
        "reason": reason,
        "target_post_id": post_id,
        "wordpress_write_executed": False,
        "live_mode_supported": False,
        "created_at": _now_iso(),
    }
    if extra:
        result.update(extra)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
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


def _validate_diff_preview_pr_notice_only(target: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    diff = target.get("diff_preview")
    if not isinstance(diff, list) or not diff:
        return ["diff_preview is required"]

    if target.get("dry_run_strategy") != "insert_after_h1":
        errs.append("dry_run_strategy must be insert_after_h1")

    removed = [line for line in diff if isinstance(line, str) and line.startswith("-") and not line.startswith("---")]
    added = [line for line in diff if isinstance(line, str) and line.startswith("+") and not line.startswith("+++ ") and not line.startswith("+++")]

    if len(removed) != 1:
        errs.append("diff_preview must contain exactly one removed content line")
    if len(added) != 1:
        errs.append("diff_preview must contain exactly one added content line")

    if removed and "<h1>" not in removed[0]:
        errs.append("removed line must include h1")
    if added:
        if "<h1>" not in added[0]:
            errs.append("added line must include h1")
        if NOTICE_HTML not in added[0]:
            errs.append("added line must include PR notice html")

    return errs


def _validate_phase1_dry_run_source(dry_run: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if int(dry_run.get("post_id", -1)) != TARGET_POST_ID:
        errs.append("dry_run_source.post_id must be 101")
    if dry_run.get("mode") != "DRY_RUN":
        errs.append("dry_run_source.mode must be DRY_RUN")
    if dry_run.get("wordpress_write_executed") is not False:
        errs.append("dry_run_source.wordpress_write_executed must be false")
    if dry_run.get("dry_run_strategy") != "insert_after_h1":
        errs.append("dry_run_source.dry_run_strategy must be insert_after_h1")
    return errs


def run(
    *,
    post_id: int,
    mode: str,
    approval_path: Path,
    phase0_path: Path,
    dry_run_source_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if post_id != TARGET_POST_ID:
        return _abort(
            "ABORT_INVALID_TARGET_POST_ID",
            "post_id must be 101 in Phase 1D",
            mode,
            post_id,
            output_path,
        )

    if mode == "LIVE":
        return _abort(
            "ABORT_LIVE_NOT_SUPPORTED_IN_PHASE1D",
            "LIVE mode is not supported in Phase 1D",
            mode,
            post_id,
            output_path,
        )

    if not approval_path.exists():
        return _abort("ABORT_MISSING_APPROVAL_FILE", f"approval file not found: {approval_path}", mode, post_id, output_path)
    if not phase0_path.exists():
        return _abort("ABORT_MISSING_PHASE0_FILE", f"phase0 file not found: {phase0_path}", mode, post_id, output_path)
    if not dry_run_source_path.exists():
        return _abort("ABORT_MISSING_DRY_RUN_SOURCE", f"dry run source not found: {dry_run_source_path}", mode, post_id, output_path)

    approval = _load_json(approval_path)
    approval_errs = _validate_approval(approval)
    if approval_errs:
        return _abort(
            "ABORT_APPROVAL_VALIDATION_FAILED",
            "approval validation failed",
            mode,
            post_id,
            output_path,
            extra={"errors": approval_errs},
        )

    phase0 = _load_json(phase0_path)
    target = _find_phase0_target(phase0, post_id)
    if target is None:
        return _abort(
            "ABORT_PHASE0_TARGET_NOT_FOUND",
            "post_id=101 not found in phase0 targets",
            mode,
            post_id,
            output_path,
        )

    diff_errs = _validate_diff_preview_pr_notice_only(target)
    if diff_errs:
        return _abort(
            "ABORT_DIFF_SCOPE_VIOLATION",
            "phase0 diff contains disallowed changes",
            mode,
            post_id,
            output_path,
            extra={"errors": diff_errs},
        )

    dry_run_source = _load_json(dry_run_source_path)
    dry_run_errs = _validate_phase1_dry_run_source(dry_run_source)
    if dry_run_errs:
        return _abort(
            "ABORT_DRY_RUN_SOURCE_VALIDATION_FAILED",
            "phase1 dry-run source validation failed",
            mode,
            post_id,
            output_path,
            extra={"errors": dry_run_errs},
        )

    title = str(target.get("title", "")).strip()
    proposed_notice = str(target.get("proposed_notice_html", NOTICE_HTML)).strip() or NOTICE_HTML

    result: dict[str, Any] = {
        "phase": "PR_WARN_BACKFILL_PHASE1D",
        "mode": "DRY_RUN",
        "status": "PASS_DRY_RUN_ONLY",
        "target_post_id": post_id,
        "title": title,
        "approval_file": str(approval_path),
        "approved": True,
        "wordpress_write_allowed": True,
        "max_live_updates": 1,
        "phase0_source": str(phase0_path),
        "dry_run_source": str(dry_run_source_path),
        "proposed_insert_position": "after_h1",
        "proposed_notice_text": proposed_notice,
        "proposed_changed_fields": ["content"],
        "forbidden_changed_fields": FORBIDDEN_FIELDS,
        "wordpress_write_executed": False,
        "live_mode_supported": False,
        "payload_preview": {
            "post_id": post_id,
            "operation": "content_patch_preview_only",
            "status": "draft",
            "patch": {
                "insert_position": "after_h1",
                "notice_html": proposed_notice,
            },
        },
        "rollback_required_before_live": True,
        "post_live_verification_required": True,
        "safety_flags": {
            "single_post_only": True,
            "bulk_backfill_forbidden": True,
            "publish_forbidden": True,
            "update_forbidden_in_phase1d": True,
            "title_change_forbidden": True,
            "url_change_forbidden": True,
            "cta_change_forbidden": True,
            "featured_image_change_forbidden": True,
            "status_change_forbidden": True,
            "category_tag_change_forbidden": True,
        },
        "created_at": _now_iso(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_path"] = str(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="PR WARN Backfill Phase 1D single-item live runner scaffold (dry-run only)")
    parser.add_argument("--post-id", type=int, required=True, help="Target post id (must be 101)")
    parser.add_argument("--mode", choices=["DRY_RUN", "LIVE"], default="DRY_RUN")
    parser.add_argument("--approval", default=str(DEFAULT_APPROVAL), help="Approved human review json path")
    parser.add_argument("--phase0", default=str(DEFAULT_PHASE0), help="Phase0 dry-run json path")
    parser.add_argument("--dry-run-source", default=str(DEFAULT_DRY_RUN_SOURCE), help="Phase1 dry-run result json path")
    parser.add_argument("--output", default=None, help="Output json path")
    args = parser.parse_args()

    output = Path(args.output) if args.output else (DEFAULT_OUT_DIR / f"pr_warn_backfill_phase1d_{args.post_id}_{args.mode.lower()}.json")

    result = run(
        post_id=args.post_id,
        mode=args.mode,
        approval_path=Path(args.approval),
        phase0_path=Path(args.phase0),
        dry_run_source_path=Path(args.dry_run_source),
        output_path=output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if str(result.get("status", "")).startswith("PASS"):
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
