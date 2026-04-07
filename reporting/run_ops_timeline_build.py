from __future__ import annotations

import sys

from reporting.ops_timeline_builder import build_ops_timeline
from reporting.ops_timeline_writer import write_ops_timeline_json


def main() -> int:
    try:
        payload = build_ops_timeline()
        output_path = write_ops_timeline_json(payload)
        print(f"ops timeline generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops timeline build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())