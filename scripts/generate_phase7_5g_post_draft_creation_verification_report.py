#!/usr/bin/env python3
"""
Phase 7-5G: 実下書き作成後 手動確認・証跡保存レポート生成
- Phase 7-5C で作成した下書き（ID:110）の成功を記録
- 公開・更新・削除・Export は引き続き NO-GO と明記
- relocked_after_execution=true を記録
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOG_DIR = ROOT / "exchange" / "logs"
RESULT_7_5C = LOG_DIR / "phase7_5c_single_draft_create_live_result.json"
OUT_JSON = LOG_DIR / "phase7_5g_post_draft_creation_verification_report.json"
OUT_MD = LOG_DIR / "phase7_5g_post_draft_creation_verification_report.md"


def _abort(reason: str, extra: dict | None = None) -> dict:
    report = {
        "package_type": "phase7_5g_post_draft_creation_verification_report",
        "phase": "Phase 7-5G",
        "status": "ABORT",
        "reason": reason,
        **(extra or {}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1)


def main() -> None:
    # --- Phase 7-5C ログ読み込み ---
    if not RESULT_7_5C.exists():
        _abort("phase7_5c result log not found")

    c = json.loads(RESULT_7_5C.read_text(encoding="utf-8"))

    # --- 必須確認 ---
    checks = []

    # 1. 実行ステータス PASS
    checks.append({
        "check": "phase7_5c_status=PASS",
        "passed": c.get("status") == "PASS",
        "actual": c.get("status"),
    })

    # 2. 実書き込み実行済み
    checks.append({
        "check": "wordpress_write_executed=true",
        "passed": c.get("wordpress_write_executed") is True,
        "actual": c.get("wordpress_write_executed"),
    })

    # 3. 下書きID が存在する
    draft_id = c.get("wordpress_draft_id") or c.get("created_post_id")
    checks.append({
        "check": "draft_id_exists",
        "passed": draft_id is not None,
        "actual": draft_id,
    })

    # 4. ステータスが draft
    checks.append({
        "check": "created_post_status=draft",
        "passed": c.get("created_post_status") == "draft",
        "actual": c.get("created_post_status"),
    })

    # 5. 実行後再ロック確認
    checks.append({
        "check": "relocked_after_execution=true",
        "passed": c.get("relocked_after_execution") is True,
        "actual": c.get("relocked_after_execution"),
    })

    # 6. 自動投稿・公開系がすべて false
    safety_keys = ["auto_post", "auto_update", "auto_delete", "auto_export", "publish_allowed"]
    safety_all_false = all(c.get(k) is False for k in safety_keys)
    checks.append({
        "check": "all_safety_flags_false",
        "passed": safety_all_false,
        "actual": {k: c.get(k) for k in safety_keys},
    })

    failed = [ch for ch in checks if not ch["passed"]]
    all_passed = len(failed) == 0

    report = {
        "package_type": "phase7_5g_post_draft_creation_verification_report",
        "phase": "Phase 7-5G",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        # --- 下書き作成証跡 ---
        "wordpress_draft_id": draft_id,
        "created_post_status": c.get("created_post_status"),
        "wordpress_write_executed": c.get("wordpress_write_executed"),
        "live_execution_attempted": c.get("live_execution_attempted"),
        "relocked_after_execution": c.get("relocked_after_execution"),
        # --- NO-GO 継続宣言 ---
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "github_actions_triggered": False,
        "slack_notification_executed": False,
        "vps_self_builder_executed": False,
        "env_or_secrets_modified": False,
        # --- 判定 ---
        "checks": checks,
        "all_checks_passed": all_passed,
        "status": "PASS" if all_passed else "ABORT",
        "reason": (
            "post-draft creation verified; draft only, not published"
            if all_passed
            else f"verification failed: {[ch['check'] for ch in failed]}"
        ),
        "next_step": "manual_delete_or_keep_draft_as_is" if all_passed else "manual_recheck_required",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # --- JSON 出力 ---
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- MD 出力 ---
    md_lines = [
        "# Phase 7-5G: 実下書き作成後 手動確認・証跡保存レポート",
        "",
        f"生成日時: {report['generated_at']}",
        "",
        "## 判定",
        "",
        f"**{report['status']}** — {report['reason']}",
        "",
        "## 下書き作成証跡",
        "",
        f"| 項目 | 値 |",
        f"|---|---|",
        f"| wordpress_draft_id | `{draft_id}` |",
        f"| created_post_status | `{report['created_post_status']}` |",
        f"| wordpress_write_executed | `{report['wordpress_write_executed']}` |",
        f"| relocked_after_execution | `{report['relocked_after_execution']}` |",
        "",
        "## NO-GO 継続事項",
        "",
        "- 公開投稿: **NO-GO**",
        "- 既存記事更新: **NO-GO**",
        "- 記事削除: **NO-GO**（手動削除は人間判断で可）",
        "- 外部Export: **NO-GO**",
        "- GitHub Actions起動: **NO-GO**",
        "- Slack本通知: **NO-GO**",
        "- VPS_SELF_BUILDER実行: **NO-GO**",
        "- .env / secrets / credentials 自動編集: **NO-GO**",
        "",
        "## チェック結果",
        "",
        "| チェック | 結果 |",
        "|---|---|",
    ]
    for ch in checks:
        mark = "✅" if ch["passed"] else "❌"
        md_lines.append(f"| {ch['check']} | {mark} `{ch['actual']}` |")

    md_lines += ["", f"## 次のステップ", "", f"`{report['next_step']}`"]

    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
