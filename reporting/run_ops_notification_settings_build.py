from __future__ import annotations

import sys

from reporting.ops_notification_settings_builder import build_ops_notification_settings
from reporting.ops_notification_settings_writer import write_ops_notification_settings_json


def main() -> int:
    try:
        payload = build_ops_notification_settings()
        output_path = write_ops_notification_settings_json(payload)
        print(f"ops notification settings generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops notification settings build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())