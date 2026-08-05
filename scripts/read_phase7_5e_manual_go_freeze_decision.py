#!/usr/bin/env python3
"""Phase 7-5E 手動GO/FREEZE最終判断 読取スクリプト

目的:
- Phase 7-5D ランブック確認後の最終判断を記録する
- WordPress REST API POST は実行しない
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REVIEW_FILE = ROOT / "exchange/human_review/phase7_5e_manual_go_freeze_decision.json"
PHASE7_5D_RESULT = ROOT / "exchange/logs/phase7_5d_single_draft_live_manual_runbook_generation_result.json"
OUTPUT_FILE = ROOT / "exchange/logs/phase7_5e_manual_go_freeze_decision_result.json"

ALLOWED_DECISIONS = {
    "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME",
    "FREEZE",
    "REQUEST_FIX",
    "ABORT",
}

CONFIRM_KEYS = [
    "runbook_reviewed",
    "scope_one_time_only_confirmed",
    "status_draft_only_confirmed",
    "no_publish_update_delete_export_confirmed",
    "rollback_procedure_confirmed",
    "token_and_expiry_confirmed",
]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base() -> dict[str, Any]:
    return {
        "package_type": "phase7_5e_manual_go_freeze_decision_result",
        "phase": "Phase 7-5E",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
    }


def _abort(reason: str, output_path: Path) -> dict[str, Any]:
    result = _base()
    result.update(
        {
            "status": "ABORT",
            "reason": reason,
            "decision": None,
            "manual_decision_recorded": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save(output_path, result)
    return result


def run_read(
    review_path: Path = REVIEW_FILE,
    phase7_5d_result_path: Path = PHASE7_5D_RESULT,
    output_path: Path = OUTPUT_FILE,
) -> dict[str, Any]:
    if not phase7_5d_result_path.exists():
        return _abort(f"phase7_5d result not found: {phase7_5d_result_path}", output_path)

    try:
        p75d = _load_json(phase7_5d_result_path)
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in phase7_5d result: {e}", output_path)

    if p75d.get("status") != "PASS":
        return _abort("phase7_5d status must be PASS", output_path)

    if not review_path.exists():
        return _abort(f"review file not found: {review_path}", output_path)

    try:
        review = _load_json(review_path)
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in review file: {e}", output_path)

    if review.get("reviewer_is_human") is not True:
        return _abort("reviewer_is_human must be true", output_path)

    if review.get("wordpress_post_enabled") is not False:
        return _abort("wordpress_post_enabled must be false", output_path)
    if review.get("real_write_enabled") is not False:
        return _abort("real_write_enabled must be false", output_path)
    if review.get("wordpress_write_executed") is not False:
        return _abort("wordpress_write_executed must be false", output_path)

    decision = review.get("decision")
    if decision not in ALLOWED_DECISIONS:
        return _abort(f"invalid decision: {decision!r}", output_path)

    confirmation = review.get("manual_confirmation", {})
    missing = [k for k in CONFIRM_KEYS if k not in confirmation]
    if missing:
        return _abort(f"manual_confirmation missing keys: {missing}", output_path)

    all_confirmed = all(confirmation.get(k) is True for k in CONFIRM_KEYS)

    if decision == "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME" and not all_confirmed:
        return _abort(
            "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME requires all manual_confirmation keys true",
            output_path,
        )

    result = _base()
    result.update(
        {
            "status": "PASS",
            "reason": f"manual decision recorded: {decision}",
            "decision": decision,
            "manual_decision_recorded": True,
            "reviewer": review.get("reviewer", ""),
            "reviewer_is_human": True,
            "all_manual_confirmation_passed": all_confirmed,
            "fix_requests": review.get("fix_requests", []),
            "reviewed_at": review.get("reviewed_at", ""),
            "next_step": (
                "manual_execute_phase7_5c_with_execute_live"
                if decision == "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"
                else "freeze_or_rework"
            ),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    _save(output_path, result)
    return result


def main() -> int:
    result = run_read()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
