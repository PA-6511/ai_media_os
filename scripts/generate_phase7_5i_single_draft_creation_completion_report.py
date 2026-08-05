#!/usr/bin/env python3
"""
Phase 7-5I: 1件限定 WordPress実下書き作成 完了レポート
- Phase 7-5C / 7-5G / 7-5H の証跡を集約
- 下書きID、status=draft、decision=KEEP を確定記録
- 公開投稿/更新/削除/Export/自動化は NO-GO 継続を明記
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

RESULT_7_5C = LOG_DIR / "phase7_5c_single_draft_create_live_result.json"
RESULT_7_5G = LOG_DIR / "phase7_5g_post_draft_creation_verification_report.json"
RESULT_7_5H = LOG_DIR / "phase7_5h_manual_wp_admin_verification_result.json"

OUT_JSON = LOG_DIR / "phase7_5i_single_draft_creation_completion_report.json"
OUT_MD = LOG_DIR / "phase7_5i_single_draft_creation_completion_report.md"


def _abort(reason: str, checks: list | None = None) -> dict:
    report = {
        "package_type": "phase7_5i_single_draft_creation_completion_report",
        "phase": "Phase 7-5I",
        "status": "ABORT",
        "reason": reason,
        "checks": checks or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    for path in [RESULT_7_5C, RESULT_7_5G, RESULT_7_5H]:
        if not path.exists():
            _abort(f"required log not found: {path}")
            return 1

    c = _load(RESULT_7_5C)
    g = _load(RESULT_7_5G)
    h = _load(RESULT_7_5H)

    draft_id_c = c.get("wordpress_draft_id") or c.get("created_post_id")
    draft_id_g = g.get("wordpress_draft_id")
    draft_id_h = h.get("wordpress_draft_id")

    checks = [
        {
            "check": "phase7_5c_status=PASS",
            "passed": c.get("status") == "PASS",
            "actual": c.get("status"),
        },
        {
            "check": "phase7_5c_wordpress_write_executed=true",
            "passed": c.get("wordpress_write_executed") is True,
            "actual": c.get("wordpress_write_executed"),
        },
        {
            "check": "phase7_5c_created_post_status=draft",
            "passed": c.get("created_post_status") == "draft",
            "actual": c.get("created_post_status"),
        },
        {
            "check": "phase7_5c_relocked_after_execution=true",
            "passed": c.get("relocked_after_execution") is True,
            "actual": c.get("relocked_after_execution"),
        },
        {
            "check": "phase7_5g_status=PASS",
            "passed": g.get("status") == "PASS",
            "actual": g.get("status"),
        },
        {
            "check": "phase7_5g_all_checks_passed=true",
            "passed": g.get("all_checks_passed") is True,
            "actual": g.get("all_checks_passed"),
        },
        {
            "check": "phase7_5h_status=PASS",
            "passed": h.get("status") == "PASS",
            "actual": h.get("status"),
        },
        {
            "check": "phase7_5h_decision=KEEP",
            "passed": h.get("decision") == "KEEP",
            "actual": h.get("decision"),
        },
        {
            "check": "draft_id_consistent_across_7_5c_7_5g_7_5h",
            "passed": draft_id_c is not None and draft_id_c == draft_id_g == draft_id_h,
            "actual": {
                "phase7_5c": draft_id_c,
                "phase7_5g": draft_id_g,
                "phase7_5h": draft_id_h,
            },
        },
    ]

    safety_false_keys = [
        "publish_allowed",
        "update_allowed",
        "delete_allowed",
        "export_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
    ]

    safety_false_passed = all(g.get(k) is False for k in safety_false_keys)
    checks.append(
        {
            "check": "phase7_5g_no_go_flags_all_false",
            "passed": safety_false_passed,
            "actual": {k: g.get(k) for k in safety_false_keys},
        }
    )

    failed = [ch for ch in checks if not ch["passed"]]
    all_passed = len(failed) == 0

    report = {
        "package_type": "phase7_5i_single_draft_creation_completion_report",
        "phase": "Phase 7-5I",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": "PASS" if all_passed else "ABORT",
        "reason": (
            "single draft creation lifecycle completed with NO-GO constraints maintained"
            if all_passed
            else f"completion verification failed: {[ch['check'] for ch in failed]}"
        ),
        "wordpress_draft_id": draft_id_c,
        "created_post_status": c.get("created_post_status"),
        "decision": h.get("decision"),
        "wordpress_write_executed": c.get("wordpress_write_executed"),
        "relocked_after_execution": c.get("relocked_after_execution"),
        "phase7_5c_status": c.get("status"),
        "phase7_5g_status": g.get("status"),
        "phase7_5h_status": h.get("status"),
        "phase7_5h_next_step": h.get("next_step"),
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
        "checks": checks,
        "all_checks_passed": all_passed,
        "next_step": (
            "maintain_no_go_and_manual_operations_only"
            if all_passed
            else "manual_recheck_required"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Phase 7-5I: 1件限定 WordPress実下書き作成 完了レポート",
        "",
        f"生成日時: {report['generated_at']}",
        "",
        "## 判定",
        "",
        f"**{report['status']}** - {report['reason']}",
        "",
        "## 集約結果",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| wordpress_draft_id | {report['wordpress_draft_id']} |",
        f"| created_post_status | {report['created_post_status']} |",
        f"| decision | {report['decision']} |",
        f"| wordpress_write_executed | {report['wordpress_write_executed']} |",
        f"| relocked_after_execution | {report['relocked_after_execution']} |",
        f"| phase7_5c_status | {report['phase7_5c_status']} |",
        f"| phase7_5g_status | {report['phase7_5g_status']} |",
        f"| phase7_5h_status | {report['phase7_5h_status']} |",
        "",
        "## NO-GO 継続事項",
        "",
        "- 公開投稿: NO-GO",
        "- 既存記事更新: NO-GO",
        "- 記事削除: NO-GO（必要時は人間の手動操作のみ）",
        "- 外部Export: NO-GO",
        "- GitHub Actions起動: NO-GO",
        "- Slack本通知: NO-GO",
        "- VPS_SELF_BUILDER実行: NO-GO",
        "- .env / secrets / credentials 自動編集: NO-GO",
        "",
        "## チェック結果",
        "",
        "| チェック | 結果 |",
        "|---|---|",
    ]
    for ch in checks:
        mark = "OK" if ch["passed"] else "NG"
        md_lines.append(f"| {ch['check']} | {mark} |")

    md_lines += ["", "## 次のステップ", "", report["next_step"]]
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
