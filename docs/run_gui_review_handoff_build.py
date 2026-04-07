from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docs.gui_review_handoff_builder import build_gui_review_handoff_markdown
from docs.gui_review_handoff_writer import (
    DEFAULT_GUI_REVIEW_HANDOFF_PATH,
    write_gui_review_handoff_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GUI実装レビュー用ハンドオフ Markdown を生成する")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_GUI_REVIEW_HANDOFF_PATH,
        help=f"出力先 markdown (デフォルト: {DEFAULT_GUI_REVIEW_HANDOFF_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        md = build_gui_review_handoff_markdown()
        output_path = write_gui_review_handoff_markdown(md, output_path=args.output)
        print(f"gui review handoff written: {output_path}")
        return 0
    except Exception as exc:
        print(f"gui review handoff build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
