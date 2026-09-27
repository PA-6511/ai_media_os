#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.read_only_session import ReadOnlySessionLocal
from app.services.x_analytics_import_service import parse_cli_datetime
from app.services.x_analytics_kpi_service import DEFAULT_TIMEZONE
from reporting.x_analytics_periodic_report import (
    DEFAULT_REPORT_DIR,
    build_periodic_report,
    default_period_key,
    write_periodic_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="X Analytics週次/月次レポートを手動生成する"
    )
    parser.add_argument("report_type", choices=("weekly", "monthly"))
    parser.add_argument("--period")
    parser.add_argument(
        "--period-mode", choices=("rolling", "calendar"), default="calendar"
    )
    parser.add_argument(
        "--reference-at",
        help="ISO 8601基準日時。rollingの終了境界、calendar選択の基準",
    )
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument(
        "--mode", choices=("posted_latest", "activity"), default="posted_latest"
    )
    parser.add_argument(
        "--ranking-metric",
        choices=("reach", "ctr", "follow_conversion", "rpmi", "epc"),
        default="reach",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args(argv)
    session = None
    try:
        reference_at = parse_cli_datetime(
            args.reference_at, "reference_at"
        ) or datetime.now(timezone.utc)
        period_key = (
            args.period
            or (
                default_period_key(
                    args.report_type,
                    timezone_name=args.timezone,
                    now=reference_at,
                )
                if args.period_mode == "calendar"
                else None
            )
        )
        session = ReadOnlySessionLocal()
        report = build_periodic_report(
            session,
            report_type=args.report_type,
            period_key=period_key,
            period_mode=args.period_mode,
            reference_at=reference_at,
            timezone_name=args.timezone,
            mode=args.mode,
            ranking_metric=args.ranking_metric,
            repository_root=ROOT,
        )
        json_path, markdown_path = write_periodic_report(
            report, output_dir=args.output_dir
        )
        print(
            json.dumps(
                {
                    "status": "GENERATED",
                    "report_id": report["report_id"],
                    "json_path": str(json_path),
                    "markdown_path": str(markdown_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            f"X Analytics report generation failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())