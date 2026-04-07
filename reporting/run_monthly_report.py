from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from reporting.monthly_report_builder import build_monthly_report, list_daily_reports_for_month
from reporting.monthly_report_writer import (
    DEFAULT_REPORT_DIR,
    write_monthly_report_json,
    write_monthly_report_txt,
)


DAILY_REPORT_PATTERN = re.compile(r"^daily_report_(\d{8})\.json$")


def _normalize_month(month_str: str) -> str:
    text = month_str.strip()
    if len(text) == 7 and text[4] == "-":
        text = text.replace("-", "")
    if len(text) != 6 or not text.isdigit():
        raise ValueError(f"month は YYYYMM または YYYY-MM 形式で指定してください: {month_str}")
    return text


def detect_latest_month(report_dir: Path = DEFAULT_REPORT_DIR) -> str:
    """daily_report から最新月(YYYYMM)を検出する。"""
    if not report_dir.exists() or not report_dir.is_dir():
        raise FileNotFoundError(f"レポートディレクトリが見つかりません: {report_dir}")

    months: list[str] = []
    for path in report_dir.glob("daily_report_*.json"):
        matched = DAILY_REPORT_PATTERN.match(path.name)
        if not matched:
            continue
        months.append(matched.group(1)[:6])

    if not months:
        raise FileNotFoundError("daily_report_*.json が見つかりません")

    return sorted(months)[-1]


def _print_summary(monthly_report: dict, json_path: str, txt_path: str) -> None:
    print()
    print("=" * 70)
    print("月次レポート生成完了")
    print("=" * 70)
    print(f"対象月: {monthly_report.get('report_month', '')}")
    print(f"日次レポート数: {monthly_report.get('daily_report_count', 0)}")
    print()
    print("◆ 処理統計")
    print(f"成功合計: {monthly_report.get('total_success_count', 0)}")
    print(f"スキップ合計: {monthly_report.get('total_skipped_count', 0)}")
    print(f"失敗合計: {monthly_report.get('total_failed_count', 0)}")
    print(f"Draft 合計: {monthly_report.get('total_draft_count', 0)}")
    print(f"Retry Queue 合計: {monthly_report.get('total_retry_queued_count', 0)}")
    print()
    print("◆ 信号統計")
    print(f"combined 合計: {monthly_report.get('total_combined_count', 0)}")
    print(f"price_only 合計: {monthly_report.get('total_price_only_count', 0)}")
    print(f"release_only 合計: {monthly_report.get('total_release_only_count', 0)}")
    print()
    print(f"JSON: {json_path}")
    print(f"TXT:  {txt_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="月次運用レポートを生成する")
    parser.add_argument(
        "--month",
        type=str,
        default=None,
        help="対象月 (YYYYMM または YYYY-MM)。未指定時は最新月を自動検出",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="daily_report の保存ディレクトリ (デフォルト: data/reports)",
    )
    args = parser.parse_args(argv)

    try:
        month = _normalize_month(args.month) if args.month else detect_latest_month(args.report_dir)
        reports = list_daily_reports_for_month(args.report_dir, month)
        if not reports:
            print(f"対象月 {month} の daily_report が見つかりません")
            return 1

        monthly_report = build_monthly_report(reports)
        json_path = write_monthly_report_json(monthly_report, output_dir=args.report_dir)
        txt_path = write_monthly_report_txt(monthly_report, output_dir=args.report_dir)

        _print_summary(monthly_report, json_path, txt_path)
        return 0
    except Exception as exc:
        print(f"エラーが発生しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
