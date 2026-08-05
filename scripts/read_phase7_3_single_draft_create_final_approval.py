#!/usr/bin/env python3
"""Phase 7-3  1件限定 実下書き作成 人間最終承認 読み取りスクリプト
WordPress REST API POST は一切行わない。
human_review ファイルを読み取り、承認内容を検証して証跡を保存する。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUMAN_REVIEW_DIR = ROOT / "exchange/human_review"
REVIEW_FILE = HUMAN_REVIEW_DIR / "phase7_3_single_draft_create_final_approval.json"
PHASE7_2_RESULT = ROOT / "exchange/logs/phase7_2_single_draft_create_execution_dry_run_result.json"
OUTPUT = ROOT / "exchange/logs/phase7_3_single_draft_create_final_approval_result.json"

ALLOWED_DECISIONS = {
    "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY",
    "REQUEST_FIX",
    "REJECT",
    "ABORT",
}
FORBIDDEN_DECISION = "APPROVE_SINGLE_DRAFT_CREATE_LIVE"

REQUIRED_CHECKLIST_KEYS = [
    "title_confirmed",
    "content_html_confirmed",
    "status_is_draft",
    "no_publish_no_future_no_pending",
    "affiliate_tag_confirmed",
    "content_url_confirmed",
    "pr_notation_confirmed",
    "category_confirmed",
    "tag_confirmed",
    "dry_run_true_confirmed",
    "wordpress_post_must_not_be_called_confirmed",
]


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_3_single_draft_create_final_approval_result",
        "phase": "Phase 7-3",
        "status": "ABORT",
        "reason": reason,
        "decision": None,
        "human_approval_required": True,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_read(
    review_path: Path = REVIEW_FILE,
    phase7_2_result_path: Path = PHASE7_2_RESULT,
    output_path: Path = OUTPUT,
) -> dict:

    # Phase 7-2 dry-run 完了確認
    if not phase7_2_result_path.exists():
        return _abort(f"Phase 7-2 result not found: {phase7_2_result_path}")
    try:
        p72 = json.loads(phase7_2_result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in Phase 7-2 result: {e}")
    if p72.get("status") != "PASS":
        return _abort("Phase 7-2 dry-run status is not PASS")
    if p72.get("dry_run_completed") is not True:
        return _abort("Phase 7-2 dry_run_completed must be true")

    # human_review ファイルの読み込み
    if not review_path.exists():
        return _abort(f"human review file not found: {review_path}")
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in review file: {e}")

    # reviewer_is_human 確認
    if review.get("reviewer_is_human") is not True:
        return _abort("reviewer_is_human must be true")

    # 禁止判定の検出
    decision = review.get("decision", "")
    if decision == FORBIDDEN_DECISION:
        return _abort(f"forbidden decision: {FORBIDDEN_DECISION} is not allowed in Phase 7-3")

    # 許可判定の確認
    if decision not in ALLOWED_DECISIONS:
        return _abort(
            f"decision must be one of {sorted(ALLOWED_DECISIONS)}, got: {decision!r}"
        )

    # 安全フラグ確認
    if review.get("wordpress_post_enabled") is not False:
        return _abort("review file: wordpress_post_enabled must be false")
    if review.get("real_write_enabled") is not False:
        return _abort("review file: real_write_enabled must be false")
    if review.get("wordpress_write_executed") is not False:
        return _abort("review file: wordpress_write_executed must be false")

    # チェックリスト項目の存在確認
    checklist = review.get("review_checklist", {})
    missing_keys = [k for k in REQUIRED_CHECKLIST_KEYS if k not in checklist]
    if missing_keys:
        return _abort(f"review_checklist missing keys: {missing_keys}")

    # APPROVE の場合はチェックリスト全項目 true 必須
    checklist_all_true = all(checklist.get(k) is True for k in REQUIRED_CHECKLIST_KEYS)
    if decision == "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY" and not checklist_all_true:
        return _abort(
            "decision is APPROVE but not all review_checklist items are true"
        )

    result = {
        "package_type": "phase7_3_single_draft_create_final_approval_result",
        "phase": "Phase 7-3",
        "status": "PASS",
        "reason": f"human review recorded: decision={decision}",
        "decision": decision,
        "human_approval_required": True,
        "reviewer": review.get("reviewer", ""),
        "reviewer_is_human": True,
        "checklist_all_confirmed": checklist_all_true,
        "fix_requests": review.get("fix_requests", []),
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "reviewed_at": review.get("reviewed_at", ""),
        "next_step": (
            "phase7_4_single_draft_create_execution"
            if decision == "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY"
            else "re_review_or_abort"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_read()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
