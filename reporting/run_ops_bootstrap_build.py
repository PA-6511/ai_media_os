from __future__ import annotations

import sys

from reporting.ops_bootstrap_builder import build_ops_bootstrap
from reporting.ops_bootstrap_writer import write_ops_bootstrap_json


def main() -> int:
    try:
        payload = build_ops_bootstrap()
        output_path = write_ops_bootstrap_json(payload)
        print(f"ops bootstrap generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops bootstrap build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())