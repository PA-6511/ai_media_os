from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docs.gui_go_live_checklist_builder import build_gui_go_live_checklist_markdown
from docs.gui_go_live_checklist_writer import (
    DEFAULT_GUI_GO_LIVE_CHECKLIST_PATH,
    write_gui_go_live_checklist_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GUI go-live checklist Markdown を生成する")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_GUI_GO_LIVE_CHECKLIST_PATH,
        help=f"出力先 markdown (デフォルト: {DEFAULT_GUI_GO_LIVE_CHECKLIST_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        markdown = build_gui_go_live_checklist_markdown()
        output_path = write_gui_go_live_checklist_markdown(markdown, output_path=args.output)
        print(f"gui go-live checklist written: {output_path}")
        return 0
    except Exception as exc:
        print(f"gui go-live checklist build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())