#!/usr/bin/env python3
"""Phase 8-8 KEEP_NO_GO確定レポート生成"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"
INPUT_8_7 = LOG_DIR / "phase8_7_publish_go_no_go_decision_result.json"
INPUT_8_6 = LOG_DIR / "phase8_6_pre_publish_final_readiness_validation_result.json"
OUT_JSON = LOG_DIR / "phase8_8_keep_no_go_completion_report.json"
OUT_MD = LOG_DIR / "phase8_8_keep_no_go_completion_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _abort(reason: str, checks: list | None = None) -> int:
    report = {
        "package_type": "phase8_8_keep_no_go_completion_report",
        "phase": "Phase 8-8",
        "status": "ABORT",
        "reason": reason,
        "checks": checks or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1


def main() -> int:
    if not INPUT_8_7.exists() or not INPUT_8_6.exists():
        missing = []
        if not INPUT_8_7.exists():
            missing.append(str(INPUT_8_7))
        if not INPUT_8_6.exists():
            missing.append(str(INPUT_8_6))
        return _abort(f"required log not found: {missing}")

    d87 = _load(INPUT_8_7)
    d86 = _load(INPUT_8_6)

    checks = [
        {
            "check": "phase8_7_status=PASS",
            "passed": d87.get("status") == "PASS",
            "actual": d87.get("status"),
        },
        {
            "check": "phase8_7_decision=KEEP_NO_GO",
            "passed": d87.get("decision") == "KEEP_NO_GO",
            "actual": d87.get("decision"),
        },
        {
            "check": "publish_candidate_unlocked_for_operator=false",
            "passed": d87.get("publish_candidate_unlocked_for_operator") is False,
            "actual": d87.get("publish_candidate_unlocked_for_operator"),
        },
        {
            "check": "wordpress_publish_execution=NO_GO",
            "passed": d87.get("wordpress_publish_execution") == "NO_GO",
            "actual": d87.get("wordpress_publish_execution"),
        },
        {
            "check": "wordpress_write_executed=false",
            "passed": d87.get("wordpress_write_executed") is False,
            "actual": d87.get("wordpress_write_executed"),
        },
        {
            "check": "phase8_6_status=PASS",
            "passed": d86.get("status") == "PASS",
            "actual": d86.get("status"),
        },
        {
            "check": "target_draft_id=110",
            "passed": d87.get("wordpress_draft_id") == 110,
            "actual": d87.get("wordpress_draft_id"),
        },
    ]

    failed = [c for c in checks if not c["passed"]]
    all_passed = len(failed) == 0

    report = {
        "package_type": "phase8_8_keep_no_go_completion_report",
        "phase": "Phase 8-8",
        "status": "PASS" if all_passed else "ABORT",
        "reason": (
            "KEEP_NO_GO decision confirmed; publish remains locked"
            if all_passed
            else f"keep_no_go confirmation failed: {[f['check'] for f in failed]}"
        ),
        "phase8_7_decision": d87.get("decision"),
        "publish_candidate_unlocked_for_operator": d87.get("publish_candidate_unlocked_for_operator"),
        "wordpress_publish_execution": d87.get("wordpress_publish_execution"),
        "wordpress_write_executed": d87.get("wordpress_write_executed"),
        "target_draft_id": d87.get("wordpress_draft_id"),
        "target_draft_status": d87.get("target_draft_status"),
        "production_status": "NO_GO",
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "checks": checks,
        "all_checks_passed": all_passed,
        "next_step": (
            "maintain_no_go_or_manual_publish_redecision"
            if all_passed
            else "manual_recheck_required"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Phase 8-8 KEEP_NO_GO確定レポート",
        "",
        f"生成日時: {report['generated_at']}",
        "",
        "## 判定",
        "",
        f"**{report['status']}** - {report['reason']}",
        "",
        "## 確定状態",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| phase8_7_decision | {report['phase8_7_decision']} |",
        f"| publish_candidate_unlocked_for_operator | {report['publish_candidate_unlocked_for_operator']} |",
        f"| wordpress_publish_execution | {report['wordpress_publish_execution']} |",
        f"| wordpress_write_executed | {report['wordpress_write_executed']} |",
        f"| target_draft_id | {report['target_draft_id']} |",
        f"| target_draft_status | {report['target_draft_status']} |",
        "",
        "## NO-GO 継続事項",
        "",
        "- WordPress publish 実行: NO-GO",
        "- 既存記事更新: NO-GO",
        "- 記事削除: NO-GO",
        "- 外部Export: NO-GO",
        "- 複数件投稿: NO-GO",
        "- cron自動化: NO-GO",
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
    for c in checks:
        md_lines.append(f"| {c['check']} | {'OK' if c['passed'] else 'NG'} |")

    md_lines += ["", "## 次のステップ", "", report["next_step"]]
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
