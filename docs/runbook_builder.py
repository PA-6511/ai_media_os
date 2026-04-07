from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _catalog() -> list[dict[str, Any]]:
    """Runbook の章とコマンド定義を返す。"""
    return [
        {
            "section": "日常点検",
            "purpose": "毎日の状態確認を短時間で実施する",
            "commands": [
                {
                    "label": "復旧一次確認サマリー",
                    "command": "python3 -m ops.run_recovery_check",
                    "note": "最新成果物・retry queue・anomaly・health score をまとめて確認",
                },
                {
                    "label": "成果物インデックス確認 (JSON)",
                    "command": "python3 -m reporting.run_artifact_index --format json",
                    "note": "latest daily/monthly/dashboard/archive と件数を確認",
                },
                {
                    "label": "成果物インデックス確認 (HTML)",
                    "command": "python3 -m reporting.run_artifact_index_html",
                    "note": "ブラウザ確認用 artifact_index_latest.html を再生成",
                },
            ],
        },
        {
            "section": "運用サイクル実行",
            "purpose": "定常運用フローを一括実行する",
            "commands": [
                {
                    "label": "ops cycle 実行",
                    "command": "python3 -m ops.run_ops_cycle",
                    "note": "scheduler/smoke/anomaly/report/dashboard/archive/log_rotate を順次実行",
                },
                {
                    "label": "失敗時即停止で実行",
                    "command": "python3 -m ops.run_ops_cycle --stop-on-error",
                    "note": "障害調査時に失敗ステップで停止したい場合に使用",
                },
            ],
        },
        {
            "section": "異常検知確認",
            "purpose": "anomaly の状態を詳細確認する",
            "commands": [
                {
                    "label": "anomaly check 実行",
                    "command": "python3 -m monitoring.run_anomaly_check",
                    "note": "OK/WARNING/CRITICAL と alert 内容を確認",
                }
            ],
        },
        {
            "section": "retry queue 確認",
            "purpose": "未解決リトライの滞留を把握する",
            "commands": [
                {
                    "label": "retry queue 一覧",
                    "command": "python3 -m pipelines.show_retry_queue",
                    "note": "queued/retrying/resolved/give_up の件数を確認",
                }
            ],
        },
        {
            "section": "日次レポート確認",
            "purpose": "日次の処理統計と成果物を確認する",
            "commands": [
                {
                    "label": "日次レポート表示",
                    "command": "python3 -m reporting.show_daily_report",
                    "note": "直近日次のサマリーを表示",
                },
                {
                    "label": "日次レポート生成",
                    "command": "python3 -m reporting.run_daily_report",
                    "note": "前日分をデフォルト生成",
                },
            ],
        },
        {
            "section": "月次レポート確認",
            "purpose": "月次の統計レポートを確認・再生成する",
            "commands": [
                {
                    "label": "月次レポート生成 (対象月指定)",
                    "command": "python3 -m reporting.run_monthly_report --month YYYYMM",
                    "note": "対象月の monthly_report_YYYYMM.* を生成",
                }
            ],
        },
        {
            "section": "アーカイブ確認",
            "purpose": "バックアップ生成状態と世代を確認する",
            "commands": [
                {
                    "label": "アーカイブ作成",
                    "command": "python3 -m ops.run_archive_backup",
                    "note": "data 配下の成果物バックアップを作成",
                },
                {
                    "label": "アーカイブ検査",
                    "command": "python3 -m ops.run_archive_inspect",
                    "note": "最新 zip の中身と生成時刻を確認",
                },
            ],
        },
        {
            "section": "復旧一次確認",
            "purpose": "障害時の初動確認を最短で行う",
            "commands": [
                {
                    "label": "復旧サマリー表示",
                    "command": "python3 -m ops.run_recovery_check",
                    "note": "latest artifacts / retry / anomaly / health score を総覧",
                },
                {
                    "label": "復旧サマリー JSON 出力",
                    "command": "python3 -m ops.run_recovery_check --format json",
                    "note": "Slack 連携や機械処理向け",
                },
            ],
        },
    ]


def build_runbook_markdown() -> str:
    """運用者向け Runbook Markdown を生成する。"""
    lines: list[str] = []
    lines.append("# AI Media OS Runbook")
    lines.append("")
    lines.append(f"- generated_at: {_now_iso()}")
    lines.append("- target: AI Media OS ops/recovery/reporting command set")
    lines.append("")
    lines.append("この Runbook は、障害時と定常点検で『まず何を打つか』を素早く判断するための最小手順書です。")
    lines.append("")

    for section in _catalog():
        lines.append(f"## {section['section']}")
        lines.append("")
        lines.append(f"目的: {section['purpose']}")
        lines.append("")
        for i, item in enumerate(section.get("commands", []), 1):
            lines.append(f"{i}. {item['label']}")
            lines.append("")
            lines.append("```bash")
            lines.append("cd ~/ai_media_os")
            lines.append(item["command"])
            lines.append("```")
            lines.append("")
            lines.append(f"補足: {item['note']}")
            lines.append("")

    lines.append("## 運用メモ")
    lines.append("")
    lines.append("- 失敗調査は run_recovery_check -> run_anomaly_check -> show_retry_queue の順で確認すると切り分けが速い。")
    lines.append("- バックアップ未作成時は run_archive_backup 実行後に run_archive_inspect で検証する。")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
