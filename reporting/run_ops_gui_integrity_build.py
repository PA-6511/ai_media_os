from __future__ import annotations

import sys

from reporting.ops_gui_integrity_builder import build_ops_gui_integrity
from reporting.ops_gui_integrity_writer import write_ops_gui_integrity_json


def main() -> int:
    try:
        payload = build_ops_gui_integrity()
        output_path = write_ops_gui_integrity_json(payload)
        print(f"ops gui integrity generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops gui integrity build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())