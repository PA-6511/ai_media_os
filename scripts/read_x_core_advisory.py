#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.x_core_advisory.store import DEFAULT_EXPORT_ROOT
from core.x_analytics_advisory_reader import XAnalyticsAdvisoryReader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Core AI用X Analytics advisory snapshotをread-onlyで取得する"
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--latest",
        choices=("x_kpi_summary", "weekly", "monthly"),
    )
    target.add_argument("--snapshot-id")
    parser.add_argument("--root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument(
        "--now",
        help="Freshness evaluation time for deterministic read-only checks (ISO-8601)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    now = None
    if args.now:
        try:
            now = datetime.fromisoformat(
                str(args.now).replace("Z", "+00:00")
            )
        except ValueError:
            parser.error("--now must be a valid ISO-8601 datetime")
        if now.tzinfo is None:
            parser.error("--now must include a timezone")
        now = now.astimezone(timezone.utc)

    reader = XAnalyticsAdvisoryReader(args.root)
    result = (
        reader.get_latest(args.latest, now=now)
        if args.latest
        else reader.get_snapshot(args.snapshot_id)
    )
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0 if result.get("status") in {"OK", "STALE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())