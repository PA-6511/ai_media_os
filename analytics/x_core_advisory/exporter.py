from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from analytics.x_core_advisory.contract import (
    XCoreAdvisoryContractError,
    build_advisory_snapshot,
    strict_load_json,
)
from analytics.x_core_advisory.store import XCoreAdvisoryStore


def export_advisory_reports(
    inputs: Mapping[str, Path],
    *,
    output_root: Path,
    generated_at: datetime | None = None,
    max_age_hours: int = 48,
    legacy_timezone: str = "Asia/Tokyo",
) -> list[dict[str, object]]:
    if not inputs:
        raise XCoreAdvisoryContractError("at least one source report is required")
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(
        timezone.utc
    )
    store = XCoreAdvisoryStore(output_root)
    results: list[dict[str, object]] = []
    for report_type in ("x_kpi_summary", "weekly", "monthly"):
        source_path = inputs.get(report_type)
        if source_path is None:
            continue
        source_report = strict_load_json(source_path)
        snapshot = build_advisory_snapshot(
            source_report,
            report_type=report_type,
            source_path=source_path,
            generated_at=generated,
            max_age_hours=max_age_hours,
            legacy_timezone=legacy_timezone,
        )
        results.append(store.publish(snapshot))
    return results