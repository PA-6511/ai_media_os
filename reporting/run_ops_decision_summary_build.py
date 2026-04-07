from __future__ import annotations

import sys

from reporting.ops_decision_summary_builder import build_ops_decision_summary
from reporting.ops_decision_summary_writer import write_ops_decision_summary_json


def main() -> int:
    try:
        payload = build_ops_decision_summary()
        output_path = write_ops_decision_summary_json(payload)
        print(f"ops decision summary generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops decision summary build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())