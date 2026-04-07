from __future__ import annotations

import sys

from reporting.ops_filters_builder import build_ops_filters
from reporting.ops_filters_writer import write_ops_filters_json


def main() -> int:
    try:
        payload = build_ops_filters()
        output_path = write_ops_filters_json(payload)
        print(f"ops filters generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops filters build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())