#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "exchange/logs"
OUTPUT_JSON = LOGS / "phase6_completion_report.json"
OUTPUT_MD = LOGS / "phase6_completion_report.md"

PHASE6_SUBPHASES = [
    ("6-1", "phase6_1_design_validation_result.json", "実下書き作成ポリシー設計"),
    ("6-2", "phase6_2_preflight_gate_validation_result.json", "preflight gate 設計"),
    ("6-3", "phase6_3_release_decision_rules_validation_result.json", "限定解放可否の最終意思決定ルール設計"),
    ("6-4", "phase6_4_controlled_unlock_plan_validation_result.json", "制御付き限定解放プラン設計"),
    ("6-5", "phase6_5_execution_spec_validation_result.json", "実行仕様書設計"),
    ("6-6", "phase6_6_pre_execution_rehearsal_validation_result.json", "実行直前リハーサル設計"),
    ("6-7", "phase6_7_unlock_readiness_decision_result.json", "readiness 判定設計"),
    ("6-8", "phase6_8_final_unlock_go_no_go_result.json", "最終GO/NO-GO設計"),
    ("6-9", "phase6_9_manual_unlock_protocol_validation_result.json", "手動限定解放プロトコル設計"),
]


def load_subphase(filename: str) -> dict | None:
    path = LOGS / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(logs_dir: Path | None = None) -> dict:
    effective_logs = Path(logs_dir) if logs_dir else LOGS
    subphase_results = []
    all_pass = True

    for tag, filename, label in PHASE6_SUBPHASES:
        data = None
        p = effective_logs / filename
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        status = data.get("status", "MISSING") if data else "MISSING"
        if status != "PASS":
            all_pass = False
        subphase_results.append({
            "phase": f"Phase {tag}",
            "label": label,
            "file": filename,
            "status": status,
        })

    overall = "COMPLETE_DESIGN_ONLY" if all_pass else "INCOMPLETE"
    return {
        "package_type": "phase6_completion_report",
        "phase": "Phase 6",
        "phase_range": "Phase 6-1 to 6-9",
        "overall_status": overall,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "real_write_enabled": False,
        "manual_unlock_status": "DESIGN_ONLY",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "subphase_results": subphase_results,
        "no_go_items": [
            "wordpress_rest_post",
            "wordpress_rest_put_patch",
            "publish_post",
            "update_existing_post",
            "delete_post",
            "external_export",
            "github_actions_trigger",
            "slack_production_notification",
            "cron_automation",
            "env_secret_auto_edit",
            "vps_self_builder_execution",
        ],
        "next_step": "Phase 7 or manual decision outside automation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_md(report: dict) -> str:
    lines = [
        "# Phase 6 WordPress実下書き作成 限定解放設計 完了レポート",
        "",
        f"生成日時: {report['generated_at']}",
        "",
        "## 全体状態",
        "",
        f"| 項目 | 判定 |",
        f"|------|------|",
        f"| overall_status | {report['overall_status']} |",
        f"| production_status | {report['production_status']} |",
        f"| wordpress_draft_creation | {report['wordpress_draft_creation']} |",
        f"| real_write_enabled | {report['real_write_enabled']} |",
        f"| manual_unlock_status | {report['manual_unlock_status']} |",
        f"| wordpress_write_executed | {report['wordpress_write_executed']} |",
        "",
        "## サブフェーズ結果一覧",
        "",
        "| フェーズ | 内容 | 判定 |",
        "|---------|------|------|",
    ]
    for r in report["subphase_results"]:
        lines.append(f"| {r['phase']} | {r['label']} | {r['status']} |")

    lines += [
        "",
        "## 本番系フラグ",
        "",
        "| フラグ | 状態 |",
        "|--------|------|",
        f"| auto_post | {report['auto_post']} |",
        f"| auto_update | {report['auto_update']} |",
        f"| auto_delete | {report['auto_delete']} |",
        f"| auto_export | {report['auto_export']} |",
        "",
        "## 全期間 NO-GO 維持項目",
        "",
    ]
    for item in report["no_go_items"]:
        lines.append(f"- {item}: NO-GO")

    lines += [
        "",
        "## 次ステップ",
        "",
        f"{report['next_step']}",
    ]
    return "\n".join(lines) + "\n"


def run_report(logs_dir: Path | None = None,
               output_json: Path | None = None,
               output_md: Path | None = None) -> dict:
    report = build_report(logs_dir)

    out_json = Path(output_json) if output_json else OUTPUT_JSON
    out_md = Path(output_md) if output_md else OUTPUT_MD
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(build_md(report), encoding="utf-8")

    return report


def main() -> int:
    report = run_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("overall_status") == "COMPLETE_DESIGN_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
