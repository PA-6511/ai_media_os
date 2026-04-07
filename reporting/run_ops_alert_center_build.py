from __future__ import annotations

import sys

from reporting.ops_alert_center_builder import build_ops_alert_center
from reporting.ops_alert_center_writer import write_ops_alert_center_json


def main() -> int:
    try:
        payload = build_ops_alert_center()
        output_path = write_ops_alert_center_json(payload)
        print(f"ops alert center generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops alert center build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())