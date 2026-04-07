from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporting.artifact_index_builder import (
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_REPORT_DIR,
    build_artifact_index,
)
from reporting.artifact_index_html_builder import build_artifact_index_html


DEFAULT_OUTPUT = DEFAULT_REPORT_DIR / "artifact_index_latest.html"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="成果物インデックスを HTML として出力する")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="レポートディレクトリ (デフォルト: data/reports)",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=DEFAULT_ARCHIVE_DIR,
        help="アーカイブディレクトリ (デフォルト: data/archives)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"出力先 HTML パス (デフォルト: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)

    try:
        index = build_artifact_index(report_dir=args.report_dir, archive_dir=args.archive_dir)
        html_content = build_artifact_index_html(index)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html_content, encoding="utf-8")
        print(f"artifact index html written: {args.output}")
        print(f"daily_report_count:   {index.get('daily_report_count', 0)}")
        print(f"weekly_report_count:  {index.get('weekly_report_count', 0)}")
        print(f"monthly_report_count: {index.get('monthly_report_count', 0)}")
        print(f"archive_count:        {index.get('archive_count', 0)}")
        print(f"release_readiness_json: {index.get('latest_release_readiness_json') or 'N/A'}")
        print(f"release_readiness_md:   {index.get('latest_release_readiness_md') or 'N/A'}")
        return 0
    except Exception as exc:
        print(f"artifact index html failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
