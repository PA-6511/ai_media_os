#!/usr/bin/env python3
"""
Phase 7-6: WordPress実下書き作成フェーズ 全体完了レポート
対象: Phase 7-1 から Phase 7-5J の到達点を集約し、
- 1件限定 draft 作成は成功
- 公開/更新/削除/Export/自動化は NO-GO 継続
を固定する。
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUTS = {
    "7-1": LOG_DIR / "phase7_1_pre_release_checklist_validation_result.json",
    "7-2": LOG_DIR / "phase7_2_single_draft_create_execution_dry_run_result.json",
    "7-3": LOG_DIR / "phase7_3_single_draft_create_final_approval_result.json",
    "7-4": LOG_DIR / "phase7_4_single_draft_create_execution_gate_result.json",
    "7-5A": LOG_DIR / "phase7_5_freeze_or_live_decision_report.json",
    "7-5B": LOG_DIR / "phase7_5b_live_final_approval_result.json",
    "7-5C": LOG_DIR / "phase7_5c_single_draft_create_live_result.json",
    "7-5D": LOG_DIR / "phase7_5d_single_draft_live_manual_runbook_generation_result.json",
    "7-5E-decision": LOG_DIR / "phase7_5e_manual_go_freeze_decision_result.json",
    "7-5E-freeze": LOG_DIR / "phase7_5e_freeze_completion_report.json",
    "7-5F-redecision": LOG_DIR / "phase7_5f_manual_go_redecision_result.json",
    "7-5F-keep": LOG_DIR / "phase7_5f_keep_freeze_completion_report.json",
    "7-5G": LOG_DIR / "phase7_5g_post_draft_creation_verification_report.json",
    "7-5H": LOG_DIR / "phase7_5h_manual_wp_admin_verification_result.json",
    "7-5I": LOG_DIR / "phase7_5i_single_draft_creation_completion_report.json",
    "7-5J": LOG_DIR / "phase7_5j_single_draft_creation_final_summary_report.json",
}

OUT_JSON = LOG_DIR / "phase7_6_wordpress_draft_creation_overall_completion_report.json"
OUT_MD = LOG_DIR / "phase7_6_wordpress_draft_creation_overall_completion_report.md"


NO_GO_KEYS = [
    "publish_allowed",
    "update_allowed",
    "delete_allowed",
    "export_allowed",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
    "github_actions_triggered",
    "slack_notification_executed",
    "vps_self_builder_executed",
    "env_or_secrets_modified",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(data: dict) -> None:
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(reason: str, checks: list | None = None) -> int:
    report = {
        "package_type": "phase7_6_wordpress_draft_creation_overall_completion_report",
        "phase": "Phase 7-6",
        "status": "ABORT",
        "reason": reason,
        "checks": checks or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1


def main() -> int:
    for _, path in INPUTS.items():
        if not path.exists():
            return _abort(f"required log not found: {path}")

    d = {k: _load(v) for k, v in INPUTS.items()}

    draft_id_5c = d["7-5C"].get("wordpress_draft_id") or d["7-5C"].get("created_post_id")
    draft_id_5g = d["7-5G"].get("wordpress_draft_id")
    draft_id_5h = d["7-5H"].get("wordpress_draft_id")
    draft_id_5i = d["7-5I"].get("wordpress_draft_id")
    draft_id_5j = d["7-5J"].get("wordpress_draft_id")

    checks = []

    for phase_key in [
        "7-1",
        "7-2",
        "7-3",
        "7-4",
        "7-5B",
        "7-5C",
        "7-5D",
        "7-5E-decision",
        "7-5E-freeze",
        "7-5F-redecision",
        "7-5F-keep",
        "7-5G",
        "7-5H",
        "7-5I",
        "7-5J",
    ]:
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
                "check": "7-5A_phase7_5_decision in {FREEZE_RECOMMENDED, LIVE_CANDIDATE_BUT_LOCKED}",
                "passed": d["7-5A"].get("phase7_5_decision") in {
                    "FREEZE_RECOMMENDED",
                    "LIVE_CANDIDATE_BUT_LOCKED",
                },
                "actual": d["7-5A"].get("phase7_5_decision"),
            },
            {
                "check": "7-5A_all_prerequisite_phases_pass=true",
                "passed": d["7-5A"].get("all_prerequisite_phases_pass") is True,
                "actual": d["7-5A"].get("all_prerequisite_phases_pass"),
            },
            {
                "check": "7-5C_created_post_status=draft",
                "passed": d["7-5C"].get("created_post_status") == "draft",
                "actual": d["7-5C"].get("created_post_status"),
            },
            {
                "check": "7-5C_wordpress_write_executed=true",
                "passed": d["7-5C"].get("wordpress_write_executed") is True,
                "actual": d["7-5C"].get("wordpress_write_executed"),
            },
            {
                "check": "7-5C_relocked_after_execution=true",
                "passed": d["7-5C"].get("relocked_after_execution") is True,
                "actual": d["7-5C"].get("relocked_after_execution"),
            },
            {
                "check": "7-5H_decision=KEEP",
                "passed": d["7-5H"].get("decision") == "KEEP",
                "actual": d["7-5H"].get("decision"),
            },
            {
                "check": "7-5I_decision=KEEP",
                "passed": d["7-5I"].get("decision") == "KEEP",
                "actual": d["7-5I"].get("decision"),
            },
            {
                "check": "7-5J_decision=KEEP",
                "passed": d["7-5J"].get("decision") == "KEEP",
                "actual": d["7-5J"].get("decision"),
            },
            {
                "check": "draft_id_consistent_7-5C_to_7-5J",
                "passed": draft_id_5c is not None and draft_id_5c == draft_id_5g == draft_id_5h == draft_id_5i == draft_id_5j,
                "actual": {
                    "7-5C": draft_id_5c,
                    "7-5G": draft_id_5g,
                    "7-5H": draft_id_5h,
                    "7-5I": draft_id_5i,
                    "7-5J": draft_id_5j,
                },
            },
            {
                "check": "7-5J_all_checks_passed=true",
                "passed": d["7-5J"].get("all_checks_passed") is True,
                "actual": d["7-5J"].get("all_checks_passed"),
            },
            {
                "check": "7-5J_no_go_flags_all_false",
                "passed": all(d["7-5J"].get(k) is False for k in NO_GO_KEYS),
                "actual": {k: d["7-5J"].get(k) for k in NO_GO_KEYS},
            },
        ]
    )

    failed = [c for c in checks if not c["passed"]]
    all_passed = len(failed) == 0

    report = {
        "package_type": "phase7_6_wordpress_draft_creation_overall_completion_report",
        "phase": "Phase 7-6",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "phase7_overall_status": "PASS" if all_passed else "ABORT",
        "status": "PASS" if all_passed else "ABORT",
        "reason": (
            "phase7-1 through phase7-5j completed; single draft created and no-go constraints maintained"
            if all_passed
            else f"phase7 overall verification failed: {[f['check'] for f in failed]}"
        ),
        "wordpress_draft_id": draft_id_5c,
        "created_post_status": d["7-5C"].get("created_post_status"),
        "decision": d["7-5J"].get("decision"),
        "wordpress_write_executed": d["7-5C"].get("wordpress_write_executed"),
        "relocked_after_execution": d["7-5C"].get("relocked_after_execution"),
        "phase_statuses": {
            "7-1": d["7-1"].get("status"),
            "7-2": d["7-2"].get("status"),
            "7-3": d["7-3"].get("status"),
            "7-4": d["7-4"].get("status"),
            "7-5A": "PASS"
            if d["7-5A"].get("phase7_5_decision") in {"FREEZE_RECOMMENDED", "LIVE_CANDIDATE_BUT_LOCKED"}
            and d["7-5A"].get("all_prerequisite_phases_pass") is True
            else "ABORT",
            "7-5B": d["7-5B"].get("status"),
            "7-5C": d["7-5C"].get("status"),
            "7-5D": d["7-5D"].get("status"),
            "7-5E-decision": d["7-5E-decision"].get("status"),
            "7-5E-freeze": d["7-5E-freeze"].get("status"),
            "7-5F-redecision": d["7-5F-redecision"].get("status"),
            "7-5F-keep": d["7-5F-keep"].get("status"),
            "7-5G": d["7-5G"].get("status"),
            "7-5H": d["7-5H"].get("status"),
            "7-5I": d["7-5I"].get("status"),
            "7-5J": d["7-5J"].get("status"),
        },
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
        "next_step": "phase8_pre_publish_review_design_only" if all_passed else "manual_recheck_required",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    _write_json(report)

    md_lines = [
        "# Phase 7-6: WordPress実下書き作成フェーズ 全体完了レポート",
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
        f"| phase7_overall_status | {report['phase7_overall_status']} |",
        f"| wordpress_draft_id | {report['wordpress_draft_id']} |",
        f"| created_post_status | {report['created_post_status']} |",
        f"| decision | {report['decision']} |",
        f"| wordpress_write_executed | {report['wordpress_write_executed']} |",
        f"| relocked_after_execution | {report['relocked_after_execution']} |",
        "",
        "## フェーズ別ステータス",
        "",
        "| フェーズ | status |",
        "|---|---|",
    ]
    for k, v in report["phase_statuses"].items():
        md_lines.append(f"| {k} | {v} |")

    md_lines += [
        "",
        "## NO-GO 継続事項",
        "",
        "- 公開投稿: NO-GO",
        "- 既存記事更新: NO-GO",
        "- 記事削除: NO-GO",
        "- 外部Export: NO-GO",
        "- GitHub Actions起動: NO-GO",
        "- Slack本通知: NO-GO",
        "- VPS_SELF_BUILDER実行: NO-GO",
        "- .env / secrets / credentials 自動編集: NO-GO",
        "- 複数件投稿: NO-GO",
        "- cron自動化: NO-GO",
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
