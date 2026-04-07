from __future__ import annotations

import sys

from reporting.ops_gui_handoff_builder import build_ops_gui_handoff
from reporting.ops_gui_handoff_writer import write_ops_gui_handoff_json


def main() -> int:
    try:
        payload = build_ops_gui_handoff()
        output_path = write_ops_gui_handoff_json(payload)
        print(f"ops gui handoff generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops gui handoff build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())