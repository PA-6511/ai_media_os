from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ebook import EbookItem, StoreOffer
from app.db.models.x_analytics import (
    XAnalyticsImportRow,
    XAnalyticsImportRun,
    XAnalyticsMetricSnapshot,
)
from app.services.x_analytics_csv_parser import COUNT_FIELDS, ParsedXAnalyticsRow


@dataclass(frozen=True)
class XAnalyticsLink:
    status: str
    ebook_item_id: str | None = None
    post_type: str | None = None
    post_type_source: str | None = None
    store_name: str | None = None
    has_cover: bool | None = None
    source: str | None = None


@dataclass(frozen=True)
class SnapshotUpsertResult:
    snapshot: XAnalyticsMetricSnapshot
    created: bool
    updated: bool


def build_observation_key(
    *,
    source: str,
    account_identifier: str,
    post_id: str,
    metric_scope: str,
    observed_at: datetime | None,
    interval_start_at: datetime | None,
    interval_end_at: datetime | None,
) -> str:
    values = (
        source,
        account_identifier,
        post_id,
        metric_scope,
        observed_at.isoformat() if observed_at else "UNKNOWN",
        interval_start_at.isoformat() if interval_start_at else "",
        interval_end_at.isoformat() if interval_end_at else "",
    )
    return hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()



ROUNDUP_POST_TYPE = "daily_new_release_roundup"
ROUNDUP_STORE_NAME = "multi_store"
ROUNDUP_POST_TYPE_SOURCE = "post_evidence:ebook_autonomy_x_post_v1"


def resolve_roundup_post_dimensions(
    post_id: str,
    evidence_path: object,
) -> dict[str, object]:
    """
    Resolve post-level dimensions for the historical
    autonomous daily new-release roundup X posts.

    This deliberately does not manufacture an ebook_item_id
    because one roundup can contain many ebook items.
    """
    import json
    from pathlib import Path

    if not evidence_path:
        return {}

    path = Path(str(evidence_path))

    if not path.is_file():
        return {}

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {}

    if not isinstance(payload, dict):
        return {}

    if payload.get("schema") != "ebook_autonomy_x_post_v1":
        return {}

    if payload.get("status") != "POSTED":
        return {}

    evidence_post_id = str(
        payload.get("x_post_id")
        or ""
    ).strip()

    if evidence_post_id != str(post_id).strip():
        return {}

    draft_raw = str(
        payload.get("draft_path")
        or ""
    ).strip()

    article_url = str(
        payload.get("article_url")
        or ""
    ).strip()

    if not draft_raw:
        return {}

    draft_path = Path(draft_raw)

    if not draft_path.is_file():
        return {}

    name = draft_path.name

    if (
        "daily_new_release_roundup"
        not in draft_raw
        or not name.startswith(
            "new_release_roundup_"
        )
        or not name.endswith(
            "_x_draft.txt"
        )
    ):
        return {}

    if "/daily-new-releases-" not in article_url:
        return {}

    try:
        draft_text = draft_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return {}

    # The historical autonomous roundup X publisher posts
    # text only. The draft explicitly advertises the three
    # storefronts as one combined roundup.
    store_marker = (
        "Kindle・楽天Kobo・DMMブックス"
    )

    if store_marker not in draft_text:
        return {}

    return {
        "post_type":
            ROUNDUP_POST_TYPE,
        "post_type_source":
            ROUNDUP_POST_TYPE_SOURCE,
        "store_name":
            ROUNDUP_STORE_NAME,
        "has_cover":
            False,
    }


class XAnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_succeeded_import(
        self, import_key: str
    ) -> XAnalyticsImportRun | None:
        return self.session.scalar(
            select(XAnalyticsImportRun).where(
                XAnalyticsImportRun.import_key == import_key,
                XAnalyticsImportRun.status == "SUCCEEDED",
            )
        )

    def create_import_run(self, **values: object) -> XAnalyticsImportRun:
        run = XAnalyticsImportRun(**values)
        self.session.add(run)
        self.session.flush()
        return run

    def link_post(self, post_id: str) -> XAnalyticsLink:
        items = list(
            self.session.scalars(
                select(EbookItem).where(EbookItem.x_post_id == post_id).limit(2)
            )
        )
        if not items:
            return XAnalyticsLink(status="UNMATCHED")
        if len(items) != 1:
            return XAnalyticsLink(
                status="AMBIGUOUS", source="ebook_items.x_post_id"
            )
        item = items[0]
        stores = set(
            self.session.scalars(
                select(StoreOffer.store_name).where(
                    StoreOffer.ebook_item_id == item.id
                )
            )
        )
        return XAnalyticsLink(
            status="MATCHED",
            ebook_item_id=item.id,
            post_type=item.item_type,
            post_type_source="ebook_items.item_type",
            store_name=next(iter(stores)) if len(stores) == 1 else None,
            has_cover=bool(item.cover_image_url),
            source="ebook_items.x_post_id",
        )

    def upsert_snapshot(
        self,
        *,
        import_run: XAnalyticsImportRun,
        row: ParsedXAnalyticsRow,
        observed_at: datetime | None,
        interval_start_at: datetime | None,
        interval_end_at: datetime | None,
        reach_metric_name: str | None,
        evidence_path: Path | None,
        evidence_posted_at: datetime | None,
    ) -> SnapshotUpsertResult:
        observation_key = build_observation_key(
            source=import_run.source,
            account_identifier=import_run.account_identifier,
            post_id=row.post_id,
            metric_scope=import_run.metric_scope,
            observed_at=observed_at,
            interval_start_at=interval_start_at,
            interval_end_at=interval_end_at,
        )
        snapshot = self.session.scalar(
            select(XAnalyticsMetricSnapshot).where(
                XAnalyticsMetricSnapshot.observation_key == observation_key
            )
        )
        created = snapshot is None
        link = self.link_post(row.post_id)
        post_dimensions = resolve_roundup_post_dimensions(
            row.post_id,
            evidence_path,
        )
        if snapshot is None:
            snapshot = XAnalyticsMetricSnapshot(
                observation_key=observation_key,
                source=import_run.source,
                account_identifier=import_run.account_identifier,
                post_id=row.post_id,
                metric_scope=import_run.metric_scope,
                observed_at=observed_at,
                interval_start_at=interval_start_at,
                interval_end_at=interval_end_at,
                link_status=link.status,
                first_import_run_id=import_run.id,
                last_import_run_id=import_run.id,
            )
            self.session.add(snapshot)

        desired: dict[str, object | None] = {
            "posted_at": row.posted_at or evidence_posted_at,
            "text": row.text,
            "post_type": (
                row.post_type
                or post_dimensions.get("post_type")
                or link.post_type
            ),
            "post_type_source": (
                "csv"
                if row.post_type
                else (
                    post_dimensions.get("post_type_source")
                    or link.post_type_source
                )
            ),
            "engagement_rate_format": row.engagement_rate_format,
            "reach_metric_name": reach_metric_name,
            "reach_metric_source_header": (
                row.source_headers.get(reach_metric_name)
                if reach_metric_name
                else None
            ),
            "ebook_item_id": link.ebook_item_id,
            "store_name": (
                post_dimensions.get("store_name")
                or link.store_name
            ),
            "has_cover": (
                post_dimensions["has_cover"]
                if "has_cover" in post_dimensions
                else link.has_cover
            ),
            "link_status": (
                link.status
                if created
                or link.status == "MATCHED"
                or snapshot.link_status != "MATCHED"
                else None
            ),
            "link_source": link.source,
            "post_evidence_path": str(evidence_path) if evidence_path else None,
        }
        desired.update(row.metrics)

        updated = False
        for field_name, value in desired.items():
            if value is None:
                continue
            current = getattr(snapshot, field_name)
            if current == value:
                continue
            if observed_at is None and current is not None:
                continue
            setattr(snapshot, field_name, value)
            updated = not created
        if not created and snapshot.last_import_run_id != import_run.id:
            snapshot.last_import_run_id = import_run.id
            updated = True
        self.session.flush()
        return SnapshotUpsertResult(snapshot, created, updated)

    def add_import_row(
        self,
        *,
        import_run_id: str,
        snapshot_id: str,
        row: ParsedXAnalyticsRow,
    ) -> None:
        self.session.add(
            XAnalyticsImportRow(
                import_run_id=import_run_id,
                snapshot_id=snapshot_id,
                row_number=row.row_number,
                raw_payload_json=json.dumps(
                    row.raw_payload, ensure_ascii=False, sort_keys=True
                ),
                unknown_payload_json=json.dumps(
                    row.unknown_payload, ensure_ascii=False, sort_keys=True
                ),
                source_headers_json=json.dumps(
                    row.source_headers, ensure_ascii=False, sort_keys=True
                ),
            )
        )

    def enrich_roundup_dimensions(self) -> int:
        snapshots = list(
            self.session.scalars(
                select(XAnalyticsMetricSnapshot).where(
                    XAnalyticsMetricSnapshot.post_evidence_path.is_not(
                        None
                    )
                )
            )
        )

        updated = 0

        for snapshot in snapshots:
            dimensions = resolve_roundup_post_dimensions(
                snapshot.post_id,
                snapshot.post_evidence_path,
            )

            if not dimensions:
                continue

            changed = False

            if snapshot.post_type is None:
                snapshot.post_type = str(
                    dimensions["post_type"]
                )
                changed = True

            if snapshot.post_type_source is None:
                snapshot.post_type_source = str(
                    dimensions["post_type_source"]
                )
                changed = True

            if snapshot.store_name is None:
                snapshot.store_name = str(
                    dimensions["store_name"]
                )
                changed = True

            if snapshot.has_cover is None:
                snapshot.has_cover = bool(
                    dimensions["has_cover"]
                )
                changed = True

            if changed:
                updated += 1

        self.session.flush()

        return updated

    def relink_unmatched(self) -> int:
        snapshots = list(
            self.session.scalars(
                select(XAnalyticsMetricSnapshot).where(
                    XAnalyticsMetricSnapshot.link_status != "MATCHED"
                )
            )
        )
        updated = 0
        for snapshot in snapshots:
            link = self.link_post(snapshot.post_id)
            if link.status != "MATCHED":
                continue
            snapshot.ebook_item_id = link.ebook_item_id
            snapshot.post_type = snapshot.post_type or link.post_type
            snapshot.post_type_source = (
                snapshot.post_type_source or link.post_type_source
            )
            snapshot.store_name = link.store_name
            snapshot.has_cover = link.has_cover
            snapshot.link_status = link.status
            snapshot.link_source = link.source
            updated += 1
        self.session.flush()
        return updated