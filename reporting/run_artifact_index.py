from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import (
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_REPORT_DIR,
    build_artifact_index,
)


def _as_text(index_data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("AI Media OS Artifact Index")
    lines.append("=" * 72)
    lines.append(f"generated_at: {index_data.get('generated_at', '')}")
    lines.append(f"report_dir:   {index_data.get('report_dir', '')}")
    lines.append(f"archive_dir:  {index_data.get('archive_dir', '')}")
    lines.append("")
    lines.append("Latest Artifacts")
    lines.append(f"- daily json:         {index_data.get('latest_daily_report_json')}")
    lines.append(f"- daily txt:          {index_data.get('latest_daily_report_txt')}")
    lines.append(f"- weekly json:        {index_data.get('latest_weekly_report_json')}")
    lines.append(f"- weekly txt:         {index_data.get('latest_weekly_report_txt')}")
    lines.append(f"- monthly json:       {index_data.get('latest_monthly_report_json')}")
    lines.append(f"- monthly txt:        {index_data.get('latest_monthly_report_txt')}")
    lines.append(f"- dashboard:          {index_data.get('latest_dashboard')}")
    lines.append(f"- weekly dashboard:   {index_data.get('latest_weekly_dashboard')}")
    lines.append(f"- monthly dashboard:  {index_data.get('latest_monthly_dashboard')}")
    lines.append(f"- release readiness json: {index_data.get('latest_release_readiness_json')}")
    lines.append(f"- release readiness md:   {index_data.get('latest_release_readiness_md')}")
    lines.append(f"- archive:            {index_data.get('latest_archive')}")
    lines.append("")
    lines.append("Counts")
    lines.append(f"- daily_report_count:   {index_data.get('daily_report_count', 0)}")
    lines.append(f"- weekly_report_count:  {index_data.get('weekly_report_count', 0)}")
    lines.append(f"- monthly_report_count: {index_data.get('monthly_report_count', 0)}")
    lines.append(f"- archive_count:        {index_data.get('archive_count', 0)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="成果物メタ一覧を生成して表示する")
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
        "--format",
        choices=["pretty", "json", "txt"],
        default="pretty",
        help="表示形式 (pretty/json/txt)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="出力先ファイル。未指定なら標準出力のみ",
    )
    args = parser.parse_args(argv)

    try:
        index_data = build_artifact_index(report_dir=args.report_dir, archive_dir=args.archive_dir)

        if args.format == "json":
            rendered = json.dumps(index_data, ensure_ascii=False, indent=2)
        else:
            rendered = _as_text(index_data)

        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
            print(f"artifact index written: {args.output}")

        print(rendered)
        return 0
    except Exception as exc:
        print(f"artifact index failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())