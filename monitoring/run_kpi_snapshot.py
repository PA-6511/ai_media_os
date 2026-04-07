from __future__ import annotations

import json
import sys

from monitoring.kpi_snapshot_builder import build_kpi_snapshot
from monitoring.kpi_snapshot_writer import append_kpi_snapshot, write_latest_kpi_snapshot


def main(argv: list[str] | None = None) -> int:
    _ = argv
    try:
        snapshot = build_kpi_snapshot()
        jsonl_path = append_kpi_snapshot(snapshot)
        latest_path = write_latest_kpi_snapshot(snapshot)

        print("KPI snapshot saved")
        print(f"jsonl: {jsonl_path}")
        print(f"latest: {latest_path}")
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"kpi snapshot failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
