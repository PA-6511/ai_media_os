from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.models.x_analytics import (
    XAnalyticsApiCollectionSlot,
    XAnalyticsImportRun,
)
from app.db.repositories.x_analytics_repository import XAnalyticsRepository
from app.integrations.x_api_metrics_client import (
    MAX_POSTS_PER_REQUEST,
    POST_READ_UNIT_COST_USD,
    XApiFetchResult,
    XApiMetricsClient,
    XApiPostMetrics,
)
from app.services.x_analytics_csv_parser import ParsedXAnalyticsRow


SOURCE = "x_api_v2"
SLOT_OFFSETS = (("d1", 1), ("d7", 7), ("d28", 28))
PRIVATE_METRIC_CUTOFF_DAYS = 29


@dataclass(frozen=True)
class EvidencePost:
    post_id: str
    posted_at: datetime
    evidence_path: Path


@dataclass(frozen=True)
class CollectionTarget:
    post_id: str
    posted_at: datetime
    evidence_path: Path
    slot_id: str
    scheduled_for: datetime
    private_metrics_eligible: bool
    recovery_only: bool = False


@dataclass(frozen=True)
class CollectionPlan:
    as_of: datetime
    targets: tuple[CollectionTarget, ...]
    future_slot_count: int
    endpoint: str = "GET /2/tweets"
    unit_cost_usd: Decimal = POST_READ_UNIT_COST_USD

    @property
    def post_count(self) -> int:
        return len(self.targets)

    @property
    def base_estimated_cost_usd(self) -> Decimal:
        return self.unit_cost_usd * sum(
            not target.recovery_only for target in self.targets
        )

    @property
    def maximum_estimated_cost_usd(self) -> Decimal:
        private_count = sum(
            target.private_metrics_eligible and not target.recovery_only
            for target in self.targets
        )
        network_count = sum(not target.recovery_only for target in self.targets)
        return self.unit_cost_usd * (network_count + private_count)


@dataclass(frozen=True)
class CollectionLimits:
    daily_max_posts: int
    monthly_max_posts: int
    daily_max_cost_usd: Decimal
    monthly_max_cost_usd: Decimal


@dataclass(frozen=True)
class CollectionSummary:
    planned: int
    fetched: int
    saved: int
    skipped: int
    failed: int
    request_count: int
    resource_read_count: int
    estimated_cost_usd: Decimal
    author_match: bool | None


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def discover_evidence_posts(repository_root: Path) -> tuple[EvidencePost, ...]:
    selected: dict[str, EvidencePost] = {}
    roots = (
        repository_root / "exchange/evidence/ebook_autonomy/x_posts",
        repository_root / "exchange/approved/x_posts",
    )
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                post_id = str(
                    payload.get("x_post_id") or payload.get("post_id") or ""
                ).strip()
                posted_at = datetime.fromisoformat(
                    str(payload.get("posted_at") or "").replace("Z", "+00:00")
                )
                posted_at = _aware_utc(posted_at)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            if not post_id.isascii() or not post_id.isdecimal():
                continue
            candidate = EvidencePost(post_id, posted_at, path)
            previous = selected.get(post_id)
            if previous is None or candidate.evidence_path.as_posix() < previous.evidence_path.as_posix():
                selected[post_id] = candidate
    return tuple(selected[key] for key in sorted(selected))


class XAnalyticsApiCollectionService:
    def __init__(
        self,
        session: Session,
        *,
        repository_root: Path,
        account_identifier: str = "configured-account",
        source: str = SOURCE,
        expected_author_id: str | None = None,
    ) -> None:
        self.session = session
        self.repository = XAnalyticsRepository(session)
        self.repository_root = repository_root
        self.account_identifier = account_identifier
        self.source = source
        self.expected_author_id = expected_author_id
        self.author_match: bool | None = None
        self.http_request_count = 0
        self.spool_root = repository_root / "exchange/x_analytics/api_responses"

    def _existing_slots(self, post_id: str) -> dict[str, XAnalyticsApiCollectionSlot]:
        try:
            return {
                row.slot_id: row
                for row in self.session.scalars(
                    select(XAnalyticsApiCollectionSlot).where(
                        XAnalyticsApiCollectionSlot.source == self.source,
                        XAnalyticsApiCollectionSlot.account_identifier
                        == self.account_identifier,
                        XAnalyticsApiCollectionSlot.post_id == post_id,
                    )
                )
            }
        except OperationalError as exc:
            self.session.rollback()
            if "x_analytics_api_collection_slots" not in str(exc):
                raise
            return {}

    @staticmethod
    def _spool_name(post_id: str, slot_id: str) -> str:
        return hashlib.sha256(f"{post_id}\0{slot_id}".encode()).hexdigest() + ".json"

    def _spool_path(self, post_id: str, slot_id: str) -> Path:
        return self.spool_root / self._spool_name(post_id, slot_id)

    def plan(self, *, as_of: datetime | None = None) -> CollectionPlan:
        now = _aware_utc(as_of or datetime.now(timezone.utc))
        targets: list[CollectionTarget] = []
        future_count = 0
        for post in discover_evidence_posts(self.repository_root):
            slots = self._existing_slots(post.post_id)
            if any(
                slot.status == "FAILED"
                and slot.last_error_code == "post_not_returned"
                for slot in slots.values()
            ):
                continue
            for slot in slots.values():
                if slot.status == "FETCHED" or (
                    slot.status == "CLAIMED"
                    and self._spool_path(post.post_id, slot.slot_id).is_file()
                ):
                    targets.append(
                        CollectionTarget(
                            post.post_id,
                            post.posted_at,
                            post.evidence_path,
                            slot.slot_id,
                            _aware_utc(slot.scheduled_for),
                            now < post.posted_at + timedelta(days=PRIVATE_METRIC_CUTOFF_DAYS),
                            recovery_only=True,
                        )
                    )
            if any(slot.status == "SUCCEEDED" for slot in slots.values()):
                bootstrap = slots.get("bootstrap")
                bootstrap_observed_at = (
                    _aware_utc(bootstrap.observed_at)
                    if bootstrap is not None and bootstrap.observed_at is not None
                    else None
                )
                due = [
                    (name, post.posted_at + timedelta(days=days))
                    for name, days in SLOT_OFFSETS
                    if post.posted_at + timedelta(days=days) <= now
                    and name not in slots
                    and (
                        bootstrap_observed_at is None
                        or post.posted_at + timedelta(days=days)
                        > bootstrap_observed_at
                    )
                ]
            else:
                due = [
                    (name, post.posted_at + timedelta(days=days))
                    for name, days in SLOT_OFFSETS
                    if post.posted_at + timedelta(days=days) <= now
                ]
                if len(due) > 1 and "bootstrap" not in slots:
                    due = [("bootstrap", now)]
            future_count += sum(
                post.posted_at + timedelta(days=days) > now
                for _, days in SLOT_OFFSETS
            )
            available = [item for item in due if item[0] not in slots]
            if available:
                slot_id, scheduled_for = available[-1]
                targets.append(
                    CollectionTarget(
                        post.post_id,
                        post.posted_at,
                        post.evidence_path,
                        slot_id,
                        scheduled_for,
                        now < post.posted_at + timedelta(days=PRIVATE_METRIC_CUTOFF_DAYS),
                    )
                )
        unique = {(target.post_id, target.slot_id): target for target in targets}
        return CollectionPlan(now, tuple(unique[key] for key in sorted(unique)), future_count)

    def _claim(self, target: CollectionTarget) -> XAnalyticsApiCollectionSlot | None:
        existing = self.session.scalar(
            select(XAnalyticsApiCollectionSlot).where(
                XAnalyticsApiCollectionSlot.source == self.source,
                XAnalyticsApiCollectionSlot.account_identifier == self.account_identifier,
                XAnalyticsApiCollectionSlot.post_id == target.post_id,
                XAnalyticsApiCollectionSlot.slot_id == target.slot_id,
            )
        )
        if existing is not None:
            return existing if existing.status == "FETCHED" else None
        slot = XAnalyticsApiCollectionSlot(
            source=self.source,
            account_identifier=self.account_identifier,
            post_id=target.post_id,
            slot_id=target.slot_id,
            scheduled_for=target.scheduled_for,
            evidence_path=str(target.evidence_path),
            posted_at=target.posted_at,
            status="CLAIMED",
            claimed_at=datetime.now(timezone.utc),
        )
        self.session.add(slot)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            return None
        return slot

    @staticmethod
    def _atomic_write(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            os.write(descriptor, payload.encode("utf-8"))
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            os.replace(name, path)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                Path(name).unlink()
            except FileNotFoundError:
                pass

    def _record_fetch(
        self,
        slot: XAnalyticsApiCollectionSlot,
        post: XApiPostMetrics,
        result: XApiFetchResult,
        observed_at: datetime,
    ) -> None:
        payload = json.dumps(
            {"post": asdict(post), "public_only": result.public_only},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()
        self._atomic_write(self._spool_path(slot.post_id, slot.slot_id), payload)
        slot.status = "FETCHED"
        slot.observed_at = observed_at
        slot.response_sha256 = digest
        slot.response_json = payload
        slot.public_only = result.public_only
        slot.request_count = result.request_count
        slot.estimated_cost_usd = POST_READ_UNIT_COST_USD * result.request_count
        slot.last_error_code = None
        self.session.commit()

    def fetch(
        self,
        plan: CollectionPlan,
        client: XApiMetricsClient,
        *,
        observed_at: datetime | None = None,
    ) -> int:
        fixed_observed = _aware_utc(observed_at) if observed_at is not None else None
        claimed: list[tuple[CollectionTarget, XAnalyticsApiCollectionSlot]] = []
        for target in plan.targets:
            slot = self._claim(target)
            if slot is None or slot.status == "FETCHED":
                continue
            claimed.append((target, slot))
        fetched = 0
        for private in (True, False):
            group = [pair for pair in claimed if pair[0].private_metrics_eligible is private]
            for offset in range(0, len(group), MAX_POSTS_PER_REQUEST):
                batch = group[offset : offset + MAX_POSTS_PER_REQUEST]
                if not batch:
                    continue
                try:
                    result = client.fetch_posts(
                        [target.post_id for target, _ in batch],
                        include_private=private,
                    )
                except Exception as exc:
                    code = getattr(exc, "category", type(exc).__name__)
                    request_count = int(getattr(exc, "request_count", 0))
                    self.http_request_count += request_count
                    for _, slot in batch:
                        slot.status = "FAILED"
                        slot.last_error_code = str(code)[:64]
                        slot.request_count = request_count
                        slot.estimated_cost_usd = (
                            POST_READ_UNIT_COST_USD * request_count
                        )
                    self.session.commit()
                    raise
                self.http_request_count += result.request_count
                returned = {post.post_id: post for post in result.posts}
                if self.expected_author_id is not None:
                    author_ids = {
                        post.author_id for post in result.posts if post.author_id
                    }
                    self.author_match = bool(author_ids) and author_ids == {
                        self.expected_author_id
                    }
                    if not self.author_match:
                        for _, slot in batch:
                            slot.status = "FAILED"
                            slot.last_error_code = "author_mismatch"
                        self.session.commit()
                        raise ValueError("X_API_AUTHOR_MISMATCH")
                response_observed_at = fixed_observed or datetime.now(timezone.utc)
                for target, slot in batch:
                    post = returned.get(target.post_id)
                    if post is None:
                        slot.status = "FAILED"
                        slot.last_error_code = "post_not_returned"
                        continue
                    self._record_fetch(slot, post, result, response_observed_at)
                    fetched += 1
                self.session.commit()
        return fetched

    def _restore_spooled_claims(self) -> None:
        claimed = list(
            self.session.scalars(
                select(XAnalyticsApiCollectionSlot).where(
                    XAnalyticsApiCollectionSlot.source == self.source,
                    XAnalyticsApiCollectionSlot.account_identifier == self.account_identifier,
                    XAnalyticsApiCollectionSlot.status == "CLAIMED",
                )
            )
        )
        for slot in claimed:
            path = self._spool_path(slot.post_id, slot.slot_id)
            if not path.is_file():
                continue
            payload = path.read_text(encoding="utf-8")
            slot.status = "FETCHED"
            slot.response_json = payload
            slot.response_sha256 = hashlib.sha256(payload.encode()).hexdigest()
        self.session.commit()

    def persist_fetched(self) -> int:
        self._restore_spooled_claims()
        slots = list(
            self.session.scalars(
                select(XAnalyticsApiCollectionSlot).where(
                    XAnalyticsApiCollectionSlot.source == self.source,
                    XAnalyticsApiCollectionSlot.account_identifier == self.account_identifier,
                    XAnalyticsApiCollectionSlot.status == "FETCHED",
                )
            )
        )
        saved = 0
        for slot in slots:
            payload = json.loads(str(slot.response_json))
            post = payload["post"]
            metrics = dict(post["metrics"])
            imported_at = _aware_utc(slot.observed_at or datetime.now(timezone.utc))
            import_key = hashlib.sha256(
                f"{self.source}\0{self.account_identifier}\0{slot.post_id}\0{slot.slot_id}\0{slot.response_sha256}".encode()
            ).hexdigest()
            run = self.repository.find_succeeded_import(import_key)
            if run is None:
                run = self.repository.create_import_run(
                    id=str(uuid.uuid4()),
                    import_key=import_key,
                    csv_sha256=str(slot.response_sha256),
                    source=self.source,
                    account_identifier=self.account_identifier,
                    source_filename="x-api-response.json",
                    metric_scope="lifetime",
                    observed_at=imported_at,
                    csv_timezone="UTC",
                    reach_metric_name="impressions",
                    headers_json=json.dumps(
                        {
                            "transport": "x_api_v2",
                            "slot_id": slot.slot_id,
                            "scheduled_for": _aware_utc(slot.scheduled_for).isoformat(),
                            "public_only": bool(slot.public_only),
                        },
                        sort_keys=True,
                    ),
                    row_count=1,
                    status="PROCESSING",
                )
                row = ParsedXAnalyticsRow(
                    row_number=1,
                    post_id=slot.post_id,
                    posted_at=_aware_utc(slot.posted_at),
                    text=post.get("text"),
                    post_type=None,
                    metrics=metrics,
                    present_fields=frozenset(
                        name for name, value in metrics.items() if value is not None
                    ),
                    source_headers={name: f"x_api_v2.{name}" for name in metrics},
                    raw_payload=post.get("raw_payload", {}),
                    unknown_payload={
                        "missing_reasons": post.get("missing_reasons", {}),
                        "slot_id": slot.slot_id,
                        "scheduled_for": _aware_utc(slot.scheduled_for).isoformat(),
                    },
                    engagement_rate_format=None,
                )
                result = self.repository.upsert_snapshot(
                    import_run=run,
                    row=row,
                    observed_at=imported_at,
                    interval_start_at=None,
                    interval_end_at=None,
                    reach_metric_name="impressions",
                    evidence_path=Path(slot.evidence_path),
                    evidence_posted_at=_aware_utc(slot.posted_at),
                )
                self.repository.add_import_row(
                    import_run_id=run.id,
                    snapshot_id=result.snapshot.id,
                    row=row,
                )
                run.status = "SUCCEEDED"
            slot.import_run_id = run.id
            slot.status = "SUCCEEDED"
            self.session.commit()
            saved += 1
        return saved

    def _enforce_limits(self, plan: CollectionPlan, limits: CollectionLimits) -> None:
        network_posts = sum(not target.recovery_only for target in plan.targets)
        maximum_cost = plan.maximum_estimated_cost_usd
        day_start = plan.as_of.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = day_start.replace(day=1)
        daily_posts = int(
            self.session.scalar(
                select(func.coalesce(func.sum(XAnalyticsApiCollectionSlot.request_count), 0)).where(
                    XAnalyticsApiCollectionSlot.source == self.source,
                    XAnalyticsApiCollectionSlot.account_identifier == self.account_identifier,
                    XAnalyticsApiCollectionSlot.claimed_at >= day_start,
                )
            )
            or 0
        )
        monthly_posts = int(
            self.session.scalar(
                select(func.coalesce(func.sum(XAnalyticsApiCollectionSlot.request_count), 0)).where(
                    XAnalyticsApiCollectionSlot.source == self.source,
                    XAnalyticsApiCollectionSlot.account_identifier == self.account_identifier,
                    XAnalyticsApiCollectionSlot.claimed_at >= month_start,
                )
            )
            or 0
        )
        daily_cost = Decimal(
            self.session.scalar(
                select(func.coalesce(func.sum(XAnalyticsApiCollectionSlot.estimated_cost_usd), 0)).where(
                    XAnalyticsApiCollectionSlot.source == self.source,
                    XAnalyticsApiCollectionSlot.account_identifier == self.account_identifier,
                    XAnalyticsApiCollectionSlot.claimed_at >= day_start,
                )
            )
            or 0
        )
        monthly_cost = Decimal(
            self.session.scalar(
                select(func.coalesce(func.sum(XAnalyticsApiCollectionSlot.estimated_cost_usd), 0)).where(
                    XAnalyticsApiCollectionSlot.source == self.source,
                    XAnalyticsApiCollectionSlot.account_identifier == self.account_identifier,
                    XAnalyticsApiCollectionSlot.claimed_at >= month_start,
                )
            )
            or 0
        )
        private_posts = sum(
            target.private_metrics_eligible and not target.recovery_only
            for target in plan.targets
        )
        maximum_resources = network_posts + private_posts
        if daily_posts + maximum_resources > limits.daily_max_posts:
            raise ValueError("DAILY_POST_LIMIT")
        if monthly_posts + maximum_resources > limits.monthly_max_posts:
            raise ValueError("MONTHLY_POST_LIMIT")
        if daily_cost + maximum_cost > limits.daily_max_cost_usd:
            raise ValueError("DAILY_COST_LIMIT")
        if monthly_cost + maximum_cost > limits.monthly_max_cost_usd:
            raise ValueError("MONTHLY_COST_LIMIT")

    def execute(
        self,
        plan: CollectionPlan,
        client: XApiMetricsClient,
        *,
        limits: CollectionLimits,
    ) -> CollectionSummary:
        self._enforce_limits(plan, limits)
        recovered = self.persist_fetched()
        fetched = self.fetch(plan, client)
        saved = recovered + self.persist_fetched()
        plan_keys = {(target.post_id, target.slot_id) for target in plan.targets}
        slots = [
            slot
            for slot in self.session.scalars(
                select(XAnalyticsApiCollectionSlot).where(
                    XAnalyticsApiCollectionSlot.source == self.source,
                    XAnalyticsApiCollectionSlot.account_identifier
                    == self.account_identifier,
                )
            )
            if (slot.post_id, slot.slot_id) in plan_keys
        ]
        return CollectionSummary(
            planned=plan.post_count,
            fetched=fetched,
            saved=saved,
            skipped=max(0, plan.post_count - fetched - recovered),
            failed=sum(slot.status == "FAILED" for slot in slots),
            request_count=self.http_request_count,
            resource_read_count=sum(slot.request_count for slot in slots),
            estimated_cost_usd=sum(
                (Decimal(slot.estimated_cost_usd) for slot in slots), Decimal("0")
            ),
            author_match=self.author_match,
        )