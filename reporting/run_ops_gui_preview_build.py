from __future__ import annotations

import sys

from reporting.ops_gui_preview_builder import build_ops_gui_preview_html
from reporting.ops_gui_preview_writer import write_ops_gui_preview_html


def main() -> int:
    try:
        html = build_ops_gui_preview_html()
        output_path = write_ops_gui_preview_html(html)
        print(f"ops gui preview generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops gui preview build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())