from __future__ import annotations

import sys

from reporting.ops_gui_schema_builder import build_ops_gui_schema
from reporting.ops_gui_schema_writer import write_ops_gui_schema_json


def main() -> int:
    try:
        payload = build_ops_gui_schema()
        output_path = write_ops_gui_schema_json(payload)
        print(f"ops gui schema generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops gui schema build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())