from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporting.ops_portal_builder import build_ops_portal_html
from reporting.ops_portal_writer import DEFAULT_REPORT_DIR, write_ops_portal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="運用総合HTMLポータルを生成する")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="出力先ディレクトリ (デフォルト: data/reports)",
    )
    args = parser.parse_args(argv)

    try:
        html = build_ops_portal_html()
        output_path = write_ops_portal(html, report_dir=args.report_dir)
        print(f"ops portal generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops portal build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
