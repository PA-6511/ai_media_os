from __future__ import annotations

import sys

from reporting.ops_timestamps_builder import build_ops_timestamps
from reporting.ops_timestamps_writer import write_ops_timestamps_json


def main() -> int:
    try:
        payload = build_ops_timestamps()
        output_path = write_ops_timestamps_json(payload)
        print(f"ops timestamps generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops timestamps build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())