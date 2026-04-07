from __future__ import annotations

import sys

from reporting.ops_layout_builder import build_ops_layout
from reporting.ops_layout_writer import write_ops_layout_json


def main() -> int:
    try:
        payload = build_ops_layout()
        output_path = write_ops_layout_json(payload)
        print(f"ops layout generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops layout build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())