from __future__ import annotations

import sys

from reporting.ops_sidebar_builder import build_ops_sidebar
from reporting.ops_sidebar_writer import write_ops_sidebar_json


def main() -> int:
    try:
        payload = build_ops_sidebar()
        output_path = write_ops_sidebar_json(payload)
        print(f"ops sidebar generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops sidebar build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())