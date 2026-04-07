from __future__ import annotations

import sys

from reporting.ops_gui_acceptance_builder import build_ops_gui_acceptance
from reporting.ops_gui_acceptance_writer import write_ops_gui_acceptance_json


def main() -> int:
    try:
        payload = build_ops_gui_acceptance()
        output_path = write_ops_gui_acceptance_json(payload)

        overall = str(payload.get("overall") or "FAIL")
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        pass_count = int(summary.get("pass_count", 0))
        total_checks = int(summary.get("total_checks", 0))
        missing_items = payload.get("missing_items") if isinstance(payload.get("missing_items"), list) else []

        print(f"ops gui acceptance generated: {output_path}")
        print(f"overall: {overall}")
        print(f"checks: {pass_count}/{total_checks} passed")
        if missing_items:
            print("missing_items:")
            for item in missing_items:
                print(f"- {item}")
        else:
            print("missing_items: []")

        return 0 if overall in {"PASS", "WARNING"} else 1
    except Exception as exc:  # noqa: BLE001
        print(f"ops gui acceptance build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
