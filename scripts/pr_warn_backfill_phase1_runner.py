#!/usr/bin/env python3
"""PR WARN Backfill Phase 1 runner (dry-run first).

This runner is intentionally safe-by-default:
- Default mode is DRY_RUN_ONLY.
- Live update is blocked unless explicit approval file is provided.
- Even in LIVE mode, exactly one post_id is allowed.
- This script does not perform WordPress write in this phase; it emits payload only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/pr_warn_backfill_phase0_dry_run_20260614.json"
DEFAULT_APPROVAL = ROOT / "exchange/human_review/pr_warn_backfill_phase1_approval.json"
DEFAULT_OUT_DIR = ROOT / "exchange/logs"

REQUIRED_APPROVAL_TOKEN = "APPROVED_PR_WARN_BACKFILL_PHASE1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_target(data: dict[str, Any], post_id: int) -> dict[str, Any] | None:
    for t in data.get("targets", []):
        if int(t.get("post_id", -1)) == post_id:
            return t
    return None


def _validate_target(target: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if target.get("classification") != "existing_draft_backfill":
        errs.append("classification must be existing_draft_backfill")
    if target.get("dry_run_would_change") is not True:
        errs.append("dry_run_would_change must be true")
    if not target.get("source_file"):
        errs.append("source_file is required")
    return errs


def _validate_approval(approval: dict[str, Any], post_id: int) -> list[str]:
    errs: list[str] = []
    if approval.get("approved") is not True:
        errs.append("approved must be true")
    if approval.get("approval_token") != REQUIRED_APPROVAL_TOKEN:
        errs.append("approval_token mismatch")
    if int(approval.get("approved_post_id", -1)) != post_id:
        errs.append("approved_post_id mismatch")
    if int(approval.get("max_live_updates", 0)) != 1:
        errs.append("max_live_updates must be 1")
    if approval.get("wordpress_write_allowed") is not True:
        errs.append("wordpress_write_allowed must be true")
    return errs


def run(
    input_path: Path,
    post_id: int,
    mode: str,
    output_path: Path,
    approval_path: Path | None,
) -> dict[str, Any]:
    if not input_path.exists():
        return {
            "status": "ABORT",
            "reason": f"input not found: {input_path}",
            "wordpress_write_executed": False,
            "created_at": _now_iso(),
        }

    data = _load_json(input_path)
    target = _find_target(data, post_id)
    if target is None:
        return {
            "status": "ABORT",
            "reason": f"post_id not found in phase0 targets: {post_id}",
            "wordpress_write_executed": False,
            "created_at": _now_iso(),
        }

    target_errs = _validate_target(target)
    if target_errs:
        return {
            "status": "ABORT",
            "reason": "target validation failed",
            "errors": target_errs,
            "wordpress_write_executed": False,
            "created_at": _now_iso(),
        }

    result: dict[str, Any] = {
        "phase": "PR WARN Backfill Phase 1",
        "mode": mode,
        "post_id": post_id,
        "title": target.get("title"),
        "source_file": target.get("source_file"),
        "dry_run_strategy": target.get("dry_run_strategy"),
        "proposed_notice_html": target.get("proposed_notice_html"),
        "classification": target.get("classification"),
        "source_age": target.get("source_age"),
        "wordpress_write_executed": False,
        "human_approval_required": True,
        "created_at": _now_iso(),
    }

    if mode == "DRY_RUN":
        result.update(
            {
                "status": "PASS_DRY_RUN_ONLY",
                "reason": "candidate payload generated; no wordpress update executed",
                "next_step": "human_approval_then_single_live_update",
            }
        )
    else:
        if approval_path is None or not approval_path.exists():
            result.update(
                {
                    "status": "ABORT",
                    "reason": "approval file required for LIVE mode",
                    "next_step": "provide approval and rerun",
                }
            )
        else:
            approval = _load_json(approval_path)
            approval_errs = _validate_approval(approval, post_id)
            if approval_errs:
                result.update(
                    {
                        "status": "ABORT",
                        "reason": "approval validation failed",
                        "errors": approval_errs,
                        "next_step": "fix approval file",
                    }
                )
            else:
                # Phase 1 preparation only: keep LIVE path blocked intentionally.
                result.update(
                    {
                        "status": "BLOCKED",
                        "reason": "live wordpress write is intentionally disabled in this preparation runner",
                        "next_step": "implement explicit wordpress update adapter after final review",
                    }
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_path"] = str(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="PR WARN Backfill Phase 1 runner (dry-run first)")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Phase0 dry-run JSON path")
    parser.add_argument("--post-id", type=int, required=True, help="Target post_id")
    parser.add_argument(
        "--mode",
        choices=["DRY_RUN", "LIVE"],
        default="DRY_RUN",
        help="Execution mode (default: DRY_RUN)",
    )
    parser.add_argument(
        "--approval",
        default=str(DEFAULT_APPROVAL),
        help="Human approval JSON path (required for LIVE)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. default: exchange/logs/pr_warn_backfill_phase1_<post_id>_<mode>.json",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    approval_path = Path(args.approval) if args.mode == "LIVE" else None

    if args.output:
        output_path = Path(args.output)
    else:
        output_name = f"pr_warn_backfill_phase1_{args.post_id}_{args.mode.lower()}.json"
        output_path = DEFAULT_OUT_DIR / output_name

    result = run(
        input_path=input_path,
        post_id=args.post_id,
        mode=args.mode,
        output_path=output_path,
        approval_path=approval_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("status") == "ABORT":
        return 2
    if result.get("status") in {"BLOCKED", "FAIL"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
