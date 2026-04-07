from __future__ import annotations

import argparse
import sys

from reporting.ops_recent_events_builder import build_ops_recent_events
from reporting.ops_recent_events_writer import write_ops_recent_events_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ops recent events JSON を生成する")
    parser.add_argument("--limit", type=int, default=5, help="出力するイベント件数 (default: 5)")
    args = parser.parse_args(argv)

    try:
        payload = build_ops_recent_events(limit=args.limit)
        output_path = write_ops_recent_events_json(payload)
        print(f"ops recent events generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops recent events build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())