from __future__ import annotations

import sys

from reporting.ops_home_payload_builder import build_ops_home_payload
from reporting.ops_home_payload_writer import write_ops_home_payload_json


def main() -> int:
    try:
        payload = build_ops_home_payload()
        output_path = write_ops_home_payload_json(payload)
        print(f"ops home payload generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops home payload build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())