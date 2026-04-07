from __future__ import annotations

# run_dashboard_build.py
# 最新の日次レポート JSON から簡易運用ダッシュボード HTML を生成する。

import argparse
import sys
from pathlib import Path
from typing import Any

from config.ops_settings_loader import get_ops_setting
from reporting.dashboard_builder import build_dashboard_html, build_dashboard_model
from reporting.dashboard_writer import write_dashboard
from reporting.report_history_loader import list_daily_report_jsons, load_recent_reports


BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE_DIR / "data" / "reports"


def load_latest_daily_report(report_dir: Path = REPORT_DIR) -> tuple[dict[str, Any], Path]:
    """最新日次レポートを読み込む。"""
    paths = list_daily_report_jsons(report_dir)
    if not paths:
        raise FileNotFoundError(
            "daily_report JSON が見つかりません。先に reporting.run_daily_report を実行してください。"
        )

    latest_path = paths[-1]
    reports = load_recent_reports(report_dir=report_dir, days=1)
    if not reports:
        raise ValueError(f"daily_report の読み込みに失敗しました: {latest_path}")

    return reports[-1], latest_path


def build_and_save_dashboard(report_dir: Path = REPORT_DIR, history_days: int = 7) -> str:
    """最新レポートと直近履歴からダッシュボードを生成して保存する。"""
    report, report_path = load_latest_daily_report(report_dir)
    recent_reports = load_recent_reports(report_dir=report_dir, days=history_days)

    model = build_dashboard_model(report, recent_reports=recent_reports)
    html = build_dashboard_html(model)
    output_path = write_dashboard(html, report_dir=report_dir)

    print(f"input report: {report_path}")
    print(f"history loaded: {len(recent_reports)} days")
    print(f"dashboard generated: {output_path}")
    return output_path


def main(argv: list[str] | None = None) -> int:
    """CLI エントリーポイント。"""
    default_history_days = int(get_ops_setting("dashboard.history_days", 7))

    parser = argparse.ArgumentParser(description="簡易運用ダッシュボードを生成する")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORT_DIR,
        help="daily_report の保存ディレクトリ (デフォルト: data/reports)",
    )
    parser.add_argument(
        "--history-days",
        type=int,
        default=default_history_days,
        help="履歴テーブルに載せる日数 (デフォルト: 7)",
    )
    args = parser.parse_args(argv)

    try:
        build_and_save_dashboard(report_dir=args.report_dir, history_days=args.history_days)
        return 0
    except Exception as exc:
        print(f"エラーが発生しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
