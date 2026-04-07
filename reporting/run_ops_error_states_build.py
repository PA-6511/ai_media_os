from __future__ import annotations

import sys

from reporting.ops_error_states_builder import build_ops_error_states
from reporting.ops_error_states_writer import write_ops_error_states_json


def main() -> int:
    try:
        payload = build_ops_error_states()
        output_path = write_ops_error_states_json(payload)
        print(f"ops error states generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops error states build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
