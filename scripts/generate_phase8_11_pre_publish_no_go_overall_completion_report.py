#!/usr/bin/env python3
"""Phase 8-11 公開前レビュー・公開NO-GO判断フェーズ 総合完了レポート"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUTS = {
    "8-1": LOG_DIR / "phase8_1_pre_publish_review_design_validation_result.json",
    "8-2": LOG_DIR / "phase8_2_manual_pre_publish_review_result.json",
    "8-3": LOG_DIR / "phase8_3_publish_gate_design_validation_result.json",
    "8-4": LOG_DIR / "phase8_4_publish_execution_protocol_validation_result.json",
    "8-5": LOG_DIR / "phase8_5_manual_publish_rehearsal_validation_result.json",
    "8-6": LOG_DIR / "phase8_6_pre_publish_final_readiness_validation_result.json",
    "8-7": LOG_DIR / "phase8_7_publish_go_no_go_decision_result.json",
    "8-8": LOG_DIR / "phase8_8_keep_no_go_completion_report.json",
    "8-9": LOG_DIR / "phase8_9_manual_publish_go_redecision_result.json",
    "8-10": LOG_DIR / "phase8_10_keep_no_go_redecision_completion_report.json",
}

OUT_JSON = LOG_DIR / "phase8_11_pre_publish_no_go_overall_completion_report.json"
OUT_MD = LOG_DIR / "phase8_11_pre_publish_no_go_overall_completion_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(data: dict) -> None:
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(reason: str, checks: list | None = None) -> int:
    report = {
        "package_type": "phase8_11_pre_publish_no_go_overall_completion_report",
        "phase": "Phase 8-11",
        "status": "ABORT",
        "reason": reason,
        "checks": checks or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1


def main() -> int:
    for _, p in INPUTS.items():
        if not p.exists():
            return _abort(f"required log not found: {p}")

    d = {k: _load(v) for k, v in INPUTS.items()}

    draft_ids = [
        d["8-2"].get("wordpress_draft_id"),
        d["8-6"].get("target_draft_id"),
        d["8-7"].get("wordpress_draft_id"),
        d["8-8"].get("target_draft_id"),
        d["8-9"].get("wordpress_draft_id"),
        d["8-10"].get("target_draft_id"),
    ]

    checks = []
    for phase_key in ["8-1", "8-2", "8-3", "8-4", "8-5", "8-6", "8-7", "8-8", "8-9", "8-10"]:
        checks.append(
            {
                "check": f"{phase_key}_status=PASS",
                "passed": d[phase_key].get("status") == "PASS",
                "actual": d[phase_key].get("status"),
            }
        )

    checks.extend(
        [
            {
                "check": "phase8_2_decision=APPROVE",
                "passed": d["8-2"].get("decision") == "APPROVE",
                "actual": d["8-2"].get("decision"),
            },
            {
                "check": "phase8_7_decision=KEEP_NO_GO",
                "passed": d["8-7"].get("decision") == "KEEP_NO_GO",
                "actual": d["8-7"].get("decision"),
            },
            {
                "check": "phase8_9_decision=KEEP_NO_GO",
                "passed": d["8-9"].get("decision") == "KEEP_NO_GO",
                "actual": d["8-9"].get("decision"),
            },
            {
                "check": "phase8_7_publish_candidate_unlocked=false",
                "passed": d["8-7"].get("publish_candidate_unlocked_for_operator") is False,
                "actual": d["8-7"].get("publish_candidate_unlocked_for_operator"),
            },
            {
                "check": "phase8_9_publish_candidate_unlocked=false",
                "passed": d["8-9"].get("publish_candidate_unlocked_for_operator") is False,
                "actual": d["8-9"].get("publish_candidate_unlocked_for_operator"),
            },
            {
                "check": "all_publish_execution_no_go",
                "passed": all(
                    x.get("wordpress_publish_execution") == "NO_GO"
                    for x in [d["8-2"], d["8-6"], d["8-7"], d["8-8"], d["8-9"], d["8-10"]]
                ),
                "actual": {
                    "8-2": d["8-2"].get("wordpress_publish_execution"),
                    "8-6": d["8-6"].get("wordpress_publish_execution"),
                    "8-7": d["8-7"].get("wordpress_publish_execution"),
                    "8-8": d["8-8"].get("wordpress_publish_execution"),
                    "8-9": d["8-9"].get("wordpress_publish_execution"),
                    "8-10": d["8-10"].get("wordpress_publish_execution"),
                },
            },
            {
                "check": "all_wordpress_write_executed_false",
                "passed": all(
                    x.get("wordpress_write_executed") is False
                    for x in [d["8-1"], d["8-2"], d["8-3"], d["8-4"], d["8-5"], d["8-6"], d["8-7"], d["8-8"], d["8-9"], d["8-10"]]
                ),
                "actual": {
                    k: d[k].get("wordpress_write_executed")
                    for k in ["8-1", "8-2", "8-3", "8-4", "8-5", "8-6", "8-7", "8-8", "8-9", "8-10"]
                },
            },
            {
                "check": "draft_id_consistent=110",
                "passed": all(v == 110 for v in draft_ids),
                "actual": draft_ids,
            },
        ]
    )

    failed = [c for c in checks if not c["passed"]]
    all_passed = len(failed) == 0

    report = {
        "package_type": "phase8_11_pre_publish_no_go_overall_completion_report",
        "phase": "Phase 8-11",
        "status": "PASS" if all_passed else "ABORT",
        "phase8_overall_status": "PASS" if all_passed else "ABORT",
        "reason": (
            "phase8-1 through phase8-10 completed; KEEP_NO_GO maintained and publish remains locked"
            if all_passed
            else f"phase8 overall verification failed: {[f['check'] for f in failed]}"
        ),
        "decision": "KEEP_NO_GO",
        "target_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "phase_statuses": {k: d[k].get("status") for k in d.keys()},
        "checks": checks,
        "all_checks_passed": all_passed,
        "next_step": "maintain_no_go_or_manual_publish_redecision",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    _write_json(report)

    md_lines = [
        "# Phase 8-11 公開前レビュー・公開NO-GO判断フェーズ 総合完了レポート",
        "",
        f"生成日時: {report['generated_at']}",
        "",
        "## 判定",
        "",
        f"**{report['status']}** - {report['reason']}",
        "",
        "## 最終状態",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| phase8_overall_status | {report['phase8_overall_status']} |",
        f"| decision | {report['decision']} |",
        f"| target_draft_id | {report['target_draft_id']} |",
        f"| target_draft_status | {report['target_draft_status']} |",
        f"| publish_candidate_unlocked_for_operator | {report['publish_candidate_unlocked_for_operator']} |",
        f"| wordpress_publish_execution | {report['wordpress_publish_execution']} |",
        f"| wordpress_write_executed | {report['wordpress_write_executed']} |",
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
