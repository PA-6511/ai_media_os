from __future__ import annotations

import sys

from reporting.ops_widgets_builder import build_ops_widgets
from reporting.ops_widgets_writer import write_ops_widgets_json


def main() -> int:
    try:
        payload = build_ops_widgets()
        output_path = write_ops_widgets_json(payload)
        print(f"ops widgets generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops widgets build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())