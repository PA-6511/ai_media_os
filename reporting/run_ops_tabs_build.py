from __future__ import annotations

import sys

from reporting.ops_tabs_builder import build_ops_tabs
from reporting.ops_tabs_writer import write_ops_tabs_json


def main() -> int:
    try:
        payload = build_ops_tabs()
        output_path = write_ops_tabs_json(payload)
        print(f"ops tabs generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops tabs build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())