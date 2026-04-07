from __future__ import annotations

import sys

from reporting.ops_gui_health_builder import build_ops_gui_health
from reporting.ops_gui_health_writer import write_ops_gui_health_json


def main() -> int:
    try:
        payload = build_ops_gui_health()
        output_path = write_ops_gui_health_json(payload)
        print(f"ops gui health generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops gui health build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())