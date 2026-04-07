from __future__ import annotations

import sys

from reporting.ops_header_builder import build_ops_header
from reporting.ops_header_writer import write_ops_header_json


def main() -> int:
    try:
        payload = build_ops_header()
        output_path = write_ops_header_json(payload)
        print(f"ops header generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops header build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())