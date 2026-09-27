#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.x_core_advisory.contract import XCoreAdvisoryContractError
from analytics.x_core_advisory.exporter import export_advisory_reports
from analytics.x_core_advisory.store import DEFAULT_EXPORT_ROOT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="検証済みレポートをCore AI参照用advisory snapshotへexportする"
    )
    parser.add_argument("--x-summary", type=Path)
    parser.add_argument("--weekly", type=Path)
    parser.add_argument("--monthly", type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--max-age-hours", type=int, default=48)
    parser.add_argument("--legacy-timezone", default="Asia/Tokyo")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = {
        report_type: path
        for report_type, path in (
            ("x_kpi_summary", args.x_summary),
            ("weekly", args.weekly),
            ("monthly", args.monthly),
        )
        if path is not None
    }
    try:
        if args.max_age_hours < 1:
            raise XCoreAdvisoryContractError(
                "max_age_hours must be at least 1"
            )
        results = export_advisory_reports(
            inputs,
            output_root=args.output_root,
            max_age_hours=args.max_age_hours,
            legacy_timezone=args.legacy_timezone,
        )
        print(
            json.dumps(
                {
                    "status": "EXPORTED",
                    "advisory_only": True,
                    "count": len(results),
                    "snapshots": results,
                },
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        )
        return 0
    except (OSError, XCoreAdvisoryContractError) as exc:
        print(f"X Core advisory export failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"X Core advisory export failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())