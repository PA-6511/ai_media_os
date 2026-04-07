from __future__ import annotations

import sys

from reporting.ops_status_light_builder import build_ops_status_light
from reporting.ops_status_light_writer import write_ops_status_light_json


def main() -> int:
    try:
        payload = build_ops_status_light()
        output_path = write_ops_status_light_json(payload)
        print(f"ops status light generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops status light build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())