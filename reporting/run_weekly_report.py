from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporting.weekly_report_builder import (
    build_weekly_report,
    detect_latest_week,
    list_daily_reports_for_week,
)
from reporting.weekly_report_writer import (
    DEFAULT_REPORT_DIR,
    write_weekly_report_json,
    write_weekly_report_txt,
)


def _print_summary(weekly_report: dict, json_path: str, txt_path: str) -> None:
    print()
    print("=" * 70)
    print("週次レポート生成完了")
    print("=" * 70)
    print(f"対象週: {weekly_report.get('report_week', '')}")
    print(f"日次レポート数: {weekly_report.get('daily_report_count', 0)}")
    print()
    print("◆ 処理統計")
    print(f"成功合計: {weekly_report.get('total_success_count', 0)}")
    print(f"スキップ合計: {weekly_report.get('total_skipped_count', 0)}")
    print(f"失敗合計: {weekly_report.get('total_failed_count', 0)}")
    print(f"Draft 合計: {weekly_report.get('total_draft_count', 0)}")
    print(f"Retry Queue 合計: {weekly_report.get('total_retry_queued_count', 0)}")
    print()
    print("◆ 信号統計")
    print(f"combined 合計: {weekly_report.get('total_combined_count', 0)}")
    print(f"price_only 合計: {weekly_report.get('total_price_only_count', 0)}")
    print(f"release_only 合計: {weekly_report.get('total_release_only_count', 0)}")
    print()
    print(f"JSON: {json_path}")
    print(f"TXT:  {txt_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="週次運用レポートを生成する")
    parser.add_argument(
        "--week",
        type=str,
        default=None,
        help="対象週 (YYYYWww または YYYY-Www)。未指定時は最新週を自動検出",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="daily_report の保存ディレクトリ (デフォルト: data/reports)",
    )
    args = parser.parse_args(argv)

    try:
        week = args.week or detect_latest_week(args.report_dir)
        reports = list_daily_reports_for_week(args.report_dir, week)
        if not reports:
            print(f"対象週 {week} の daily_report が見つかりません")
            return 1

        weekly_report = build_weekly_report(reports)
        json_path = write_weekly_report_json(weekly_report, output_dir=args.report_dir)
        txt_path = write_weekly_report_txt(weekly_report, output_dir=args.report_dir)

        _print_summary(weekly_report, json_path, txt_path)
        return 0
    except Exception as exc:
        print(f"エラーが発生しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
