from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docs.daily_checklist_builder import build_daily_checklist_markdown
from docs.daily_checklist_writer import DEFAULT_DAILY_CHECKLIST_PATH, write_daily_checklist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="daily checklist を自動生成する")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DAILY_CHECKLIST_PATH,
        help=f"出力先 markdown (デフォルト: {DEFAULT_DAILY_CHECKLIST_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        markdown = build_daily_checklist_markdown()
        path = write_daily_checklist(markdown, output_path=args.output)
        print(f"daily checklist written: {path}")
        return 0
    except Exception as exc:
        print(f"daily checklist build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())