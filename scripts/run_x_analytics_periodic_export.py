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

from analytics.x_core_advisory.exporter import export_advisory_reports
from analytics.x_core_advisory.store import DEFAULT_EXPORT_ROOT
from app.db.read_only_session import ReadOnlySessionLocal
from app.services.x_analytics_import_service import parse_cli_datetime
from app.services.x_analytics_kpi_service import DEFAULT_TIMEZONE
from reporting.x_analytics_periodic_report import (
    DEFAULT_REPORT_DIR,
    build_periodic_report,
    previous_complete_period_key,
    write_periodic_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="前回完了期間のX Analytics report生成とCore advisory export"
    )
    parser.add_argument("report_type", choices=("weekly", "monthly"))
    parser.add_argument("--period")
    parser.add_argument(
        "--period-mode", choices=("rolling", "calendar"), default="rolling"
    )
    parser.add_argument("--reference-at")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument(
        "--mode", choices=("posted_latest", "activity"), default="posted_latest"
    )
    parser.add_argument("--source")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    args = parser.parse_args(argv)
    session = None
    try:
        generated_at = datetime.now(timezone.utc)
        reference_at = parse_cli_datetime(
            args.reference_at, "reference_at"
        ) or generated_at
        effective_period_mode = (
            "calendar" if args.period else args.period_mode
        )
        period_key = (
            args.period
            or (
                previous_complete_period_key(
                    args.report_type,
                    timezone_name=args.timezone,
                    now=reference_at,
                )
                if effective_period_mode == "calendar"
                else None
            )
        )
        session = ReadOnlySessionLocal()
        report = build_periodic_report(
            session,
            report_type=args.report_type,
            period_key=period_key,
            period_mode=effective_period_mode,
            reference_at=reference_at,
            timezone_name=args.timezone,
            mode=args.mode,
            source=args.source,
            generated_at=generated_at,
            repository_root=ROOT,
        )
        json_path, markdown_path = write_periodic_report(
            report, output_dir=args.report_dir
        )
        export_inputs = {args.report_type: json_path}
        if args.report_type == "weekly":
            export_inputs["x_kpi_summary"] = json_path
        exported = export_advisory_reports(
            export_inputs,
            output_root=args.export_root,
            generated_at=generated_at,
        )
        print(
            json.dumps(
                {
                    "status": "GENERATED_AND_EXPORTED",
                    "report_id": report["report_id"],
                    "json_path": str(json_path),
                    "markdown_path": str(markdown_path),
                    "exports": exported,
                    "advisory_only": True,
                },
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        )
        return 0
    except Exception as exc:
        print(
            f"X Analytics periodic export failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())