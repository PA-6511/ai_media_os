from __future__ import annotations

import sys

from reporting.ops_nav_search_builder import build_ops_nav_search
from reporting.ops_nav_search_writer import write_ops_nav_search_json


def main() -> int:
    try:
        payload = build_ops_nav_search()
        output_path = write_ops_nav_search_json(payload)
        print(f"ops nav search generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops nav search build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
