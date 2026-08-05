#!/usr/bin/env python3
"""Phase 7-5B  LIVE最終承認ファイル読み取りスクリプト
WordPress REST API POST は一切行わない。
human_review ファイルを読み取り、LIVE承認の形式が正しいかを検証して証跡を保存する。
実POSTは Phase 7-5C で別途実施。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUMAN_REVIEW_DIR = ROOT / "exchange/human_review"
REVIEW_FILE = HUMAN_REVIEW_DIR / "phase7_5b_live_final_approval.json"
PHASE7_5A_RESULT = ROOT / "exchange/logs/phase7_5_freeze_or_live_decision_report.json"
OUTPUT = ROOT / "exchange/logs/phase7_5b_live_final_approval_result.json"

VALID_TOKEN = "APPROVE_SINGLE_DRAFT_CREATE_LIVE_ONE_TIME"
FORBIDDEN_TOKENS = {
    "APPROVE_SINGLE_DRAFT_CREATE_LIVE",
    "APPROVE_MANUAL_UNLOCK_DRAFT_CREATE_ONLY",
    "APPROVE_DRAFT_CREATE_ONLY",
}

REQUIRED_REMAINING_KEYS = [
    "live_01_payload_title_content",
    "live_02_content_url",
    "live_03_affiliate_tag",
    "live_04_pr_notation",
    "live_05_wp_user_role_editor",
    "live_06_status_draft_only",
    "live_07_rollback_plan",
    "live_08_token_valid_within_30min",
]

REQUIRED_TOKEN_CONSTRAINTS = {
    "one_time_only": True,
    "post_status": "draft",
    "post_count_limit": 1,
    "publish_allowed": False,
    "update_allowed": False,
    "delete_allowed": False,
    "export_allowed": False,
}


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_5b_live_final_approval_result",
        "phase": "Phase 7-5B",
        "status": "ABORT",
        "reason": reason,
        "approval_token_valid": False,
        "all_remaining_items_confirmed": False,
        "token_constraints_valid": False,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_read(
    review_path: Path = REVIEW_FILE,
    phase7_5a_result_path: Path = PHASE7_5A_RESULT,
    output_path: Path = OUTPUT,
) -> dict:

    # Phase 7-5A レポート確認
    if not phase7_5a_result_path.exists():
        return _abort(f"Phase 7-5A report not found: {phase7_5a_result_path}")
    try:
        p75a = json.loads(phase7_5a_result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in Phase 7-5A report: {e}")

    if p75a.get("phase7_5_decision") != "FREEZE_RECOMMENDED":
        return _abort("Phase 7-5A decision must be FREEZE_RECOMMENDED")
    if p75a.get("live_execution_allowed") is not False:
        return _abort("Phase 7-5A: live_execution_allowed must be false")

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

    # 禁止トークンの検出
    token = review.get("approval_token", "")
    if token in FORBIDDEN_TOKENS:
        return _abort(f"forbidden token used: {token!r}")

    # 正規トークンの確認
    if token != VALID_TOKEN:
        return _abort(f"approval_token must be {VALID_TOKEN!r}, got {token!r}")

    # decision の確認
    decision = review.get("decision", "")
    if decision != VALID_TOKEN:
        return _abort(f"decision must be {VALID_TOKEN!r}, got {decision!r}")

    # 安全フラグ確認
    if review.get("wordpress_post_enabled") is not False:
        return _abort("review file: wordpress_post_enabled must be false")
    if review.get("real_write_enabled") is not False:
        return _abort("review file: real_write_enabled must be false")
    if review.get("wordpress_write_executed") is not False:
        return _abort("review file: wordpress_write_executed must be false")

    # 残確認8項目の存在確認
    remaining = review.get("remaining_items_confirmed", {})
    missing_keys = [k for k in REQUIRED_REMAINING_KEYS if k not in remaining]
    if missing_keys:
        return _abort(f"remaining_items_confirmed missing keys: {missing_keys}")

    # 全項目 true 必須
    all_confirmed = all(remaining.get(k) is True for k in REQUIRED_REMAINING_KEYS)
    if not all_confirmed:
        unconfirmed = [k for k in REQUIRED_REMAINING_KEYS if not remaining.get(k)]
        return _abort(f"remaining items not confirmed: {unconfirmed}")

    # token_constraints 確認
    constraints = review.get("token_constraints", {})
    invalid_constraints = []
    for key, expected in REQUIRED_TOKEN_CONSTRAINTS.items():
        if constraints.get(key) != expected:
            invalid_constraints.append(
                f"{key}: expected={expected!r}, got={constraints.get(key)!r}"
            )
    if invalid_constraints:
        return _abort(f"token_constraints invalid: {invalid_constraints}")

    # expires_minutes の確認（1〜30 の範囲）
    expires = constraints.get("expires_minutes")
    if not isinstance(expires, int) or not (1 <= expires <= 30):
        return _abort(
            f"token_constraints.expires_minutes must be int 1-30, got {expires!r}"
        )

    result = {
        "package_type": "phase7_5b_live_final_approval_result",
        "phase": "Phase 7-5B",
        "status": "PASS",
        "reason": "LIVE final approval format is valid. WordPress POST is NOT executed here.",
        "approval_token": VALID_TOKEN,
        "approval_token_valid": True,
        "all_remaining_items_confirmed": True,
        "token_constraints_valid": True,
        "token_constraints": constraints,
        "reviewer": review.get("reviewer", ""),
        "reviewer_is_human": True,
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
        "next_step": "phase7_5c_single_draft_create_live_post",
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
