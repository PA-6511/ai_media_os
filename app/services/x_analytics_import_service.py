from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.x_analytics_repository import XAnalyticsRepository
from app.services.x_analytics_csv_parser import (
    ParsedXAnalyticsCsv,
    XAnalyticsCsvError,
    parse_x_analytics_csv,
)


VALID_SCOPES = {"lifetime", "interval", "unknown"}
VALID_REACH_METRICS = {None, "impressions", "views"}


class XAnalyticsImportError(RuntimeError):
    def __init__(self, message: str, *, import_run_id: str) -> None:
        super().__init__(message)
        self.import_run_id = import_run_id


@dataclass(frozen=True)
class XAnalyticsImportMetadata:
    source: str
    account_identifier: str
    metric_scope: str = "unknown"
    observed_at: datetime | None = None
    interval_start_at: datetime | None = None
    interval_end_at: datetime | None = None
    csv_timezone: str | None = None
    reach_metric_name: str | None = None


@dataclass(frozen=True)
class XAnalyticsImportSummary:
    import_run_id: str
    processed: int
    created: int
    updated: int
    skipped: int
    errors: int
    linked: int
    unlinked: int
    reused: bool


def parse_cli_datetime(value: str | None, field_name: str) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _validate_metadata(metadata: XAnalyticsImportMetadata) -> None:
    if not metadata.source.strip():
        raise ValueError("source is required")
    if not metadata.account_identifier.strip():
        raise ValueError("account_identifier is required")
    if metadata.metric_scope not in VALID_SCOPES:
        raise ValueError("metric_scope must be lifetime, interval, or unknown")
    if metadata.reach_metric_name not in VALID_REACH_METRICS:
        raise ValueError("reach_metric_name must be impressions or views")
    for field_name, value in (
        ("observed_at", metadata.observed_at),
        ("interval_start_at", metadata.interval_start_at),
        ("interval_end_at", metadata.interval_end_at),
    ):
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError(f"{field_name} must include a timezone")
    if metadata.metric_scope == "interval":
        if metadata.interval_start_at is None or metadata.interval_end_at is None:
            raise ValueError("interval scope requires interval start and end")
        if metadata.interval_end_at <= metadata.interval_start_at:
            raise ValueError("interval end must be after interval start")
    elif metadata.interval_start_at is not None or metadata.interval_end_at is not None:
        raise ValueError("interval bounds are only valid for interval scope")


def _metadata_value(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _build_import_key(
    csv_sha256: str, metadata: XAnalyticsImportMetadata
) -> str:
    payload = {
        "csv_sha256": csv_sha256,
        "source": metadata.source.strip(),
        "account_identifier": metadata.account_identifier.strip(),
        "metric_scope": metadata.metric_scope,
        "observed_at": _metadata_value(metadata.observed_at),
        "interval_start_at": _metadata_value(metadata.interval_start_at),
        "interval_end_at": _metadata_value(metadata.interval_end_at),
        "reach_metric_name": metadata.reach_metric_name,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _find_post_evidence(
    repository_root: Path | None, post_id: str
) -> tuple[Path | None, datetime | None]:
    if repository_root is None:
        return None, None
    roots = (
        repository_root / "exchange/evidence/ebook_autonomy/x_posts",
        repository_root / "exchange/approved/x_posts",
    )
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.glob("*.json"):
            try:
                payload: Any = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            evidence_post_id = str(
                payload.get("x_post_id") or payload.get("post_id") or ""
            ).strip()
            if evidence_post_id != post_id:
                continue
            posted_at = parse_cli_datetime(
                str(payload.get("posted_at") or "") or None,
                "evidence posted_at",
            )
            return path, posted_at
    return None, None


class XAnalyticsImportService:
    def __init__(self, session: Session, *, repository_root: Path | None = None) -> None:
        self.session = session
        self.repository = XAnalyticsRepository(session)
        self.repository_root = repository_root

    def import_file(
        self,
        input_path: Path,
        metadata: XAnalyticsImportMetadata,
        *,
        commit: bool = True,
    ) -> XAnalyticsImportSummary:
        run_id = str(uuid.uuid4())
        try:
            _validate_metadata(metadata)
            content = input_path.read_bytes()
            csv_sha256 = hashlib.sha256(content).hexdigest()
            import_key = _build_import_key(csv_sha256, metadata)
            parsed: ParsedXAnalyticsCsv = parse_x_analytics_csv(
                input_path, csv_timezone=metadata.csv_timezone
            )
            existing = self.repository.find_succeeded_import(import_key)
            if existing is not None:
                return XAnalyticsImportSummary(
                    import_run_id=existing.id,
                    processed=existing.row_count,
                    created=0,
                    updated=0,
                    skipped=existing.row_count,
                    errors=0,
                    linked=0,
                    unlinked=0,
                    reused=True,
                )

            run = self.repository.create_import_run(
                id=run_id,
                import_key=import_key,
                csv_sha256=csv_sha256,
                source=metadata.source.strip(),
                account_identifier=metadata.account_identifier.strip(),
                source_filename=input_path.name,
                metric_scope=metadata.metric_scope,
                observed_at=metadata.observed_at,
                interval_start_at=metadata.interval_start_at,
                interval_end_at=metadata.interval_end_at,
                csv_timezone=metadata.csv_timezone,
                reach_metric_name=metadata.reach_metric_name,
                headers_json=json.dumps(
                    parsed.headers, ensure_ascii=False
                ),
                row_count=len(parsed.rows),
                status="PROCESSING",
            )
            created = updated = skipped = linked = unlinked = 0
            seen_post_ids: set[str] = set()
            for row in parsed.rows:
                if row.post_id in seen_post_ids:
                    raise XAnalyticsCsvError(
                        f"row {row.row_number}: duplicate post_id in one CSV: "
                        f"{row.post_id}"
                    )
                seen_post_ids.add(row.post_id)
                evidence_path, evidence_posted_at = _find_post_evidence(
                    self.repository_root, row.post_id
                )
                result = self.repository.upsert_snapshot(
                    import_run=run,
                    row=row,
                    observed_at=metadata.observed_at,
                    interval_start_at=metadata.interval_start_at,
                    interval_end_at=metadata.interval_end_at,
                    reach_metric_name=metadata.reach_metric_name,
                    evidence_path=evidence_path,
                    evidence_posted_at=evidence_posted_at,
                )
                self.repository.add_import_row(
                    import_run_id=run.id,
                    snapshot_id=result.snapshot.id,
                    row=row,
                )
                created += int(result.created)
                updated += int(result.updated)
                skipped += int(not result.created and not result.updated)
                linked += int(result.snapshot.link_status == "MATCHED")
                unlinked += int(result.snapshot.link_status != "MATCHED")
            run.status = "SUCCEEDED"
            self.session.flush()
            if commit:
                self.session.commit()
            return XAnalyticsImportSummary(
                import_run_id=run.id,
                processed=len(parsed.rows),
                created=created,
                updated=updated,
                skipped=skipped,
                errors=0,
                linked=linked,
                unlinked=unlinked,
                reused=False,
            )
        except Exception as exc:
            self.session.rollback()
            raise XAnalyticsImportError(
                str(exc), import_run_id=run_id
            ) from exc

    def relink_unmatched(self, *, commit: bool = True) -> int:
        try:
            updated = self.repository.relink_unmatched()
            if commit:
                self.session.commit()
            return updated
        except Exception:
            self.session.rollback()
            raise