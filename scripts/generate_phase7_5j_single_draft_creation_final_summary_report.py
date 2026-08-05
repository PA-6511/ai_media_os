#!/usr/bin/env python3
"""
Phase 7-5J: 1件限定 WordPress実下書き作成フェーズ 総合完了レポート
対象: 7-5A〜7-5I の証跡を集約し、最終状態を固定する。
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUTS = {
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
}

OUT_JSON = LOG_DIR / "phase7_5j_single_draft_creation_final_summary_report.json"
OUT_MD = LOG_DIR / "phase7_5j_single_draft_creation_final_summary_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(data: dict) -> None:
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(reason: str, checks: list | None = None) -> int:
    report = {
        "package_type": "phase7_5j_single_draft_creation_final_summary_report",
        "phase": "Phase 7-5J",
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

    data = {k: _load(v) for k, v in INPUTS.items()}

    d75c = data["7-5C"]
    d75g = data["7-5G"]
    d75h = data["7-5H"]
    d75i = data["7-5I"]
    d75e = data["7-5E-decision"]
    d75f = data["7-5F-redecision"]

    draft_id_c = d75c.get("wordpress_draft_id") or d75c.get("created_post_id")
    draft_id_g = d75g.get("wordpress_draft_id")
    draft_id_h = d75h.get("wordpress_draft_id")
    draft_id_i = d75i.get("wordpress_draft_id")

    checks = []

    checks.append(
        {
            "check": "7-5A_decision in {FREEZE_RECOMMENDED, LIVE_CANDIDATE_BUT_LOCKED}",
            "passed": data["7-5A"].get("phase7_5_decision") in {
                "FREEZE_RECOMMENDED",
                "LIVE_CANDIDATE_BUT_LOCKED",
            },
            "actual": data["7-5A"].get("phase7_5_decision"),
        }
    )
    checks.append(
        {
            "check": "7-5A_all_prerequisite_phases_pass=true",
            "passed": data["7-5A"].get("all_prerequisite_phases_pass") is True,
            "actual": data["7-5A"].get("all_prerequisite_phases_pass"),
        }
    )

    for phase_key in [
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
    ]:
        checks.append(
            {
                "check": f"{phase_key}_status=PASS",
                "passed": data[phase_key].get("status") == "PASS",
                "actual": data[phase_key].get("status"),
            }
        )

    checks.extend(
        [
            {
                "check": "7-5E_decision=FREEZE",
                "passed": d75e.get("decision") == "FREEZE",
                "actual": d75e.get("decision"),
            },
            {
                "check": "7-5F_redecision=MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME",
                "passed": d75f.get("decision") == "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME",
                "actual": d75f.get("decision"),
            },
            {
                "check": "7-5C_wordpress_write_executed=true",
                "passed": d75c.get("wordpress_write_executed") is True,
                "actual": d75c.get("wordpress_write_executed"),
            },
            {
                "check": "7-5C_created_post_status=draft",
                "passed": d75c.get("created_post_status") == "draft",
                "actual": d75c.get("created_post_status"),
            },
            {
                "check": "7-5C_relocked_after_execution=true",
                "passed": d75c.get("relocked_after_execution") is True,
                "actual": d75c.get("relocked_after_execution"),
            },
            {
                "check": "7-5H_decision=KEEP",
                "passed": d75h.get("decision") == "KEEP",
                "actual": d75h.get("decision"),
            },
            {
                "check": "draft_id_consistent_7-5C_7-5G_7-5H_7-5I",
                "passed": (
                    draft_id_c is not None
                    and draft_id_c == draft_id_g == draft_id_h == draft_id_i
                ),
                "actual": {
                    "7-5C": draft_id_c,
                    "7-5G": draft_id_g,
                    "7-5H": draft_id_h,
                    "7-5I": draft_id_i,
                },
            },
        ]
    )

    no_go_keys = [
        "publish_allowed",
        "update_allowed",
        "delete_allowed",
        "export_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
    ]

    checks.append(
        {
            "check": "no_go_flags_all_false_in_7-5G",
            "passed": all(d75g.get(k) is False for k in no_go_keys),
            "actual": {k: d75g.get(k) for k in no_go_keys},
        }
    )

    failed = [c for c in checks if not c["passed"]]
    all_passed = len(failed) == 0

    report = {
        "package_type": "phase7_5j_single_draft_creation_final_summary_report",
        "phase": "Phase 7-5J",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": "PASS" if all_passed else "ABORT",
        "reason": (
            "phase7-5 lifecycle completed; one draft created and NO-GO constraints maintained"
            if all_passed
            else f"phase7-5 summary verification failed: {[f['check'] for f in failed]}"
        ),
        "wordpress_draft_id": draft_id_c,
        "created_post_status": d75c.get("created_post_status"),
        "decision": d75h.get("decision"),
        "wordpress_write_executed": d75c.get("wordpress_write_executed"),
        "relocked_after_execution": d75c.get("relocked_after_execution"),
        "phase_statuses": {
            "7-5A": "PASS"
            if data["7-5A"].get("phase7_5_decision") in {"FREEZE_RECOMMENDED", "LIVE_CANDIDATE_BUT_LOCKED"}
            and data["7-5A"].get("all_prerequisite_phases_pass") is True
            else "ABORT",
            "7-5B": data["7-5B"].get("status"),
            "7-5C": data["7-5C"].get("status"),
            "7-5D": data["7-5D"].get("status"),
            "7-5E-decision": data["7-5E-decision"].get("status"),
            "7-5E-freeze": data["7-5E-freeze"].get("status"),
            "7-5F-redecision": data["7-5F-redecision"].get("status"),
            "7-5F-keep": data["7-5F-keep"].get("status"),
            "7-5G": data["7-5G"].get("status"),
            "7-5H": data["7-5H"].get("status"),
            "7-5I": data["7-5I"].get("status"),
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
        "next_step": "maintain_no_go_until_new_manual_phase" if all_passed else "manual_recheck_required",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    _write_json(report)

    md_lines = [
        "# Phase 7-5J: 1件限定 WordPress実下書き作成フェーズ 総合完了レポート",
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
    for c in checks:
        md_lines.append(f"| {c['check']} | {'OK' if c['passed'] else 'NG'} |")

    md_lines += ["", "## 次のステップ", "", report["next_step"]]
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
