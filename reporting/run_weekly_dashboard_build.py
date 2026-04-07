from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporting.weekly_dashboard_builder import (
    DEFAULT_REPORT_DIR,
    build_weekly_dashboard_html,
    build_weekly_dashboard_model,
    load_latest_weekly_report,
)
from reporting.weekly_dashboard_writer import write_weekly_dashboard


def build_and_save_weekly_dashboard(report_dir: Path = DEFAULT_REPORT_DIR) -> str:
    """最新週次レポートから週次ダッシュボードを生成して保存する。"""
    report, report_path = load_latest_weekly_report(report_dir)
    model = build_weekly_dashboard_model(report)
    html = build_weekly_dashboard_html(model)
    output_path = write_weekly_dashboard(html, report_dir=report_dir)

    print(f"input report: {report_path}")
    print(f"dashboard generated: {output_path}")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="週次ダッシュボードを生成する")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="weekly_report の保存ディレクトリ (デフォルト: data/reports)",
    )
    args = parser.parse_args(argv)

    try:
        build_and_save_weekly_dashboard(report_dir=args.report_dir)
        return 0
    except Exception as exc:
        print(f"エラーが発生しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
