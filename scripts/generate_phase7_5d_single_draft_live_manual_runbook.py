#!/usr/bin/env python3
"""Phase 7-5D 1件限定 WordPress実下書き作成 手動実行ランブック生成

目的:
- 実POST前に、人間向け手順を固定する
- 実行可否の最終判断は人間のみ
- このスクリプト自体は WordPress POST を実行しない
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "exchange/logs"

PHASE7_5A = LOGS / "phase7_5_freeze_or_live_decision_report.json"
PHASE7_5B = LOGS / "phase7_5b_live_final_approval_result.json"
PHASE7_5C = LOGS / "phase7_5c_single_draft_create_live_result.json"

RUNBOOK_JSON = LOGS / "phase7_5d_single_draft_live_manual_runbook.json"
RUNBOOK_MD = LOGS / "phase7_5d_single_draft_live_manual_runbook.md"
RESULT_JSON = LOGS / "phase7_5d_single_draft_live_manual_runbook_generation_result.json"

VALID_TOKEN = "APPROVE_SINGLE_DRAFT_CREATE_LIVE_ONE_TIME"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _abort(reason: str, output_result_path: Path) -> dict[str, Any]:
    result = {
        "package_type": "phase7_5d_single_draft_live_manual_runbook_generation_result",
        "phase": "Phase 7-5D",
        "status": "ABORT",
        "reason": reason,
        "runbook_generated": False,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(output_result_path, result)
    return result


def _build_runbook() -> dict[str, Any]:
    return {
        "package_type": "phase7_5d_single_draft_live_manual_runbook",
        "phase": "Phase 7-5D",
        "purpose": "1件限定 WordPress draft 作成を手動実行するためのランブック",
        "runbook_status": "READY_FOR_MANUAL_DECISION",
        "live_execution_allowed": False,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "fixed_manual_procedure": {
            "1_operator": {
                "description": "誰が実行するか",
                "required": True,
                "value": "未入力（実行担当者を人間で記入）",
            },
            "2_execution_time": {
                "description": "実行時刻",
                "required": True,
                "value": "未入力（ISO8601で記録）",
            },
            "3_precheck_files": {
                "description": "実行前に確認するファイル",
                "required": True,
                "files": [
                    "exchange/logs/phase7_5_freeze_or_live_decision_report.json",
                    "exchange/logs/phase7_5b_live_final_approval_result.json",
                    "exchange/outgoing/wordpress_draft_create_payload.dry_run.json",
                    "scripts/run_phase7_5c_single_draft_create_live_manual.py",
                ],
            },
            "4_execution_command": {
                "description": "実行コマンド",
                "required": True,
                "command": "python3 scripts/run_phase7_5c_single_draft_create_live_manual.py --execute-live --wordpress-base-url <WP_BASE_URL> --wp-username <WP_USERNAME> --wp-app-password <WP_APP_PASSWORD>",
                "note": "実行は手動のみ。自動実行・cron・GitHub Actionsは禁止。",
            },
            "5_wp_admin_checks": {
                "description": "実行直後に確認する WordPress 管理画面項目",
                "required": True,
                "items": [
                    "新規下書きが1件のみ作成されている",
                    "投稿ステータスが draft のまま",
                    "公開されていない",
                    "タイトルと本文が payload と一致",
                ],
            },
            "6_save_draft_id": {
                "description": "作成された下書きIDの保存方法",
                "required": True,
                "method": "exchange/logs/phase7_5c_single_draft_create_live_result.json の created_post_id を確認し、運用記録へ転記",
            },
            "7_stop_conditions_on_failure": {
                "description": "失敗時の停止条件",
                "required": True,
                "conditions": [
                    "HTTP status が 201 以外",
                    "レスポンスに post id がない",
                    "status が draft 以外",
                    "想定外の複数投稿が確認された",
                ],
            },
            "8_relock_confirmation": {
                "description": "成功後の再ロック確認",
                "required": True,
                "check": "phase7_5c result の relocked_after_execution が true であること",
            },
            "9_manual_delete_procedure": {
                "description": "手動削除が必要な場合の手順",
                "required": True,
                "steps": [
                    "WordPress管理画面で対象下書きを開く",
                    "対象IDを再確認",
                    "手動でゴミ箱へ移動",
                    "必要なら完全削除",
                    "実施結果を証跡ログに記録",
                ],
            },
            "10_post_execution_report": {
                "description": "実行後レポートの保存",
                "required": True,
                "files": [
                    "exchange/logs/phase7_5c_single_draft_create_live_result.json",
                    "exchange/logs/phase7_5d_single_draft_live_manual_runbook_generation_result.json",
                ],
            },
        },
        "still_forbidden": [
            "cron_registration",
            "github_actions_trigger",
            "slack_production_notification",
            "multiple_post_create",
            "publish_post",
            "update_existing_post",
            "delete_post_by_automation",
            "external_export",
            "vps_execution",
            "env_secret_auto_edit",
        ],
        "next_step": "manual_go_or_freeze_decision",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_md(runbook: dict[str, Any]) -> str:
    proc = runbook["fixed_manual_procedure"]
    lines = [
        "# Phase 7-5D 1件限定 WordPress実下書き作成 手動実行ランブック",
        "",
        f"生成日時: {runbook['generated_at']}",
        "",
        "## 状態",
        "",
        f"- runbook_status: {runbook['runbook_status']}",
        f"- live_execution_allowed: {runbook['live_execution_allowed']}",
        f"- production_status: {runbook['production_status']}",
        f"- wordpress_draft_creation: {runbook['wordpress_draft_creation']}",
        f"- wordpress_write_executed: {runbook['wordpress_write_executed']}",
        "",
        "## 手動実行手順（固定10項目）",
        "",
        f"1. {proc['1_operator']['description']}: {proc['1_operator']['value']}",
        f"2. {proc['2_execution_time']['description']}: {proc['2_execution_time']['value']}",
        "3. 実行前に確認するファイル:",
    ]
    for f in proc["3_precheck_files"]["files"]:
        lines.append(f"- {f}")

    lines += [
        f"4. 実行コマンド: {proc['4_execution_command']['command']}",
        f"- 注意: {proc['4_execution_command']['note']}",
        "5. 実行直後に確認する WordPress 管理画面項目:",
    ]
    for item in proc["5_wp_admin_checks"]["items"]:
        lines.append(f"- {item}")

    lines += [
        f"6. 下書きIDの保存方法: {proc['6_save_draft_id']['method']}",
        "7. 失敗時の停止条件:",
    ]
    for cond in proc["7_stop_conditions_on_failure"]["conditions"]:
        lines.append(f"- {cond}")

    lines += [
        f"8. 再ロック確認: {proc['8_relock_confirmation']['check']}",
        "9. 手動削除手順:",
    ]
    for step in proc["9_manual_delete_procedure"]["steps"]:
        lines.append(f"- {step}")

    lines += [
        "10. 実行後レポート保存先:",
    ]
    for f in proc["10_post_execution_report"]["files"]:
        lines.append(f"- {f}")

    lines += [
        "",
        "## まだ禁止される操作",
        "",
    ]
    for item in runbook["still_forbidden"]:
        lines.append(f"- {item}")

    lines += [
        "",
        f"next_step: {runbook['next_step']}",
    ]
    return "\n".join(lines) + "\n"


def run_generate(
    phase7_5a_path: Path = PHASE7_5A,
    phase7_5b_path: Path = PHASE7_5B,
    phase7_5c_path: Path = PHASE7_5C,
    output_runbook_json: Path = RUNBOOK_JSON,
    output_runbook_md: Path = RUNBOOK_MD,
    output_result_json: Path = RESULT_JSON,
) -> dict[str, Any]:
    if not phase7_5a_path.exists():
        return _abort(f"missing prerequisite: {phase7_5a_path}", output_result_json)
    if not phase7_5b_path.exists():
        return _abort(f"missing prerequisite: {phase7_5b_path}", output_result_json)
    if not phase7_5c_path.exists():
        return _abort(f"missing prerequisite: {phase7_5c_path}", output_result_json)

    p75a = _load_json(phase7_5a_path)
    p75b = _load_json(phase7_5b_path)
    p75c = _load_json(phase7_5c_path)

    if p75a.get("phase7_5_decision") != "FREEZE_RECOMMENDED":
        return _abort("phase7_5_decision must be FREEZE_RECOMMENDED", output_result_json)
    if p75b.get("status") != "PASS":
        return _abort("phase7_5b status must be PASS", output_result_json)
    if p75b.get("approval_token") != VALID_TOKEN:
        return _abort("phase7_5b approval_token invalid", output_result_json)
    if p75c.get("wordpress_write_executed") is not False:
        return _abort("phase7_5c wordpress_write_executed must be false at runbook stage", output_result_json)

    runbook = _build_runbook()
    _write_json(output_runbook_json, runbook)
    _write_md(output_runbook_md, _build_md(runbook))

    result = {
        "package_type": "phase7_5d_single_draft_live_manual_runbook_generation_result",
        "phase": "Phase 7-5D",
        "status": "PASS",
        "reason": "manual runbook generated successfully",
        "runbook_generated": True,
        "runbook_json": str(output_runbook_json),
        "runbook_md": str(output_runbook_md),
        "fixed_procedure_item_count": 10,
        "still_forbidden_count": len(runbook["still_forbidden"]),
        "live_execution_allowed": False,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": runbook["next_step"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(output_result_json, result)
    return result


def main() -> int:
    result = run_generate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
