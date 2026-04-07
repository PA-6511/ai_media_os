from __future__ import annotations

import sys

from reporting.ops_api_payload_builder import build_ops_api_payload
from reporting.ops_api_payload_writer import write_ops_api_payload_json


def main() -> int:
    try:
        payload = build_ops_api_payload()
        output_path = write_ops_api_payload_json(payload)
        print(f"ops api payload generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops api payload build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())