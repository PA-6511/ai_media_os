from __future__ import annotations

import sys

from reporting.ops_error_display_model_builder import build_ops_error_display_model
from reporting.ops_error_display_model_writer import write_ops_error_display_model_json


def main() -> int:
    try:
        payload = build_ops_error_display_model()
        output_path = write_ops_error_display_model_json(payload)
        print(f"ops error display model generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops error display model build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
