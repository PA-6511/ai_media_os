from __future__ import annotations

import sys

from reporting.ops_page_dependencies_builder import build_ops_page_dependencies
from reporting.ops_page_dependencies_writer import write_ops_page_dependencies_json


def main() -> int:
    try:
        payload = build_ops_page_dependencies()
        output_path = write_ops_page_dependencies_json(payload)
        print(f"ops page dependencies generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops page dependencies build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
