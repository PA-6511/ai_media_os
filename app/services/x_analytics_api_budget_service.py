from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_UP
from typing import Any, Callable

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.models.x_analytics import (
    XAnalyticsApiBudgetRequest,
    XAnalyticsApiCollectionSlot,
)
from app.services.x_analytics_api_collection_service import (
    CollectionPlan,
    CollectionTarget,
)


MONEY_QUANTUM = Decimal("0.000001")
BASE_MONTHLY_LIMIT_USD = Decimal("0.500000")
UTC = timezone.utc


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_UP)


@dataclass(frozen=True)
class BudgetNotificationResult:
    sent: bool
    error: str | None = None


@dataclass(frozen=True)
class BudgetDecision:
    status: str
    budget_month_utc: str
    effective_limit_usd: Decimal
    estimated_used_usd: Decimal
    already_reserved_usd: Decimal
    reserved_usd: Decimal
    remaining_usd: Decimal
    allowed_targets: tuple[CollectionTarget, ...]
    held_targets: tuple[CollectionTarget, ...]
    reservation_id: str | None
    awaiting_request_id: str | None


def notify_budget_via_slack(payload: dict[str, Any]) -> BudgetNotificationResult:
    webhook = str(
        os.getenv("X_ANALYTICS_BUDGET_SLACK_WEBHOOK_URL")
        or os.getenv("SLACK_X_DRAFT_REVIEW_WEBHOOK_URL")
        or ""
    ).strip()
    if not webhook:
        return BudgetNotificationResult(False, "destination_not_configured")
    message = {
        "text": (
            "X実績収集：予算確認が必要\n"
            f"対象月(UTC): {payload['budget_month_utc']}\n"
            f"推定使用額: ${payload['estimated_used_usd']} / "
            f"予約額: ${payload['reserved_usd']} / "
            f"残予算: ${payload['remaining_base_budget_usd']}\n"
            f"次回対象: {payload['target_count']}件 / "
            f"最大追加費用: ${payload['additional_cost_usd']}\n"
            f"目的: {payload['purpose']}\n"
            f"見送る場合: {payload['impact_if_skipped']}\n"
            f"非公開指標期限: {payload['private_metrics_deadline_at'] or 'N/A'}\n"
            f"確認依頼ID: {payload['request_id']}\n"
            "確認先: 既存管理GUIの /x-analytics\n"
            "状態確認: .venv/bin/python scripts/manage_x_analytics_api_budget.py status\n"
            "却下: .venv/bin/python scripts/manage_x_analytics_api_budget.py reject REQUEST_ID --actor OPERATOR_NAME\n"
            "当月限定承認: .venv/bin/python scripts/manage_x_analytics_api_budget.py approve REQUEST_ID --actor OPERATOR_NAME --monthly-limit-usd NEW_TOTAL\n"
            "Slack返信だけでは承認されません。返答がない限り上限超過取得は実行しません。"
        )
    }
    try:
        import requests

        response = requests.post(webhook, json=message, timeout=15)
    except requests.RequestException:
        return BudgetNotificationResult(False, "transport_failed")
    return BudgetNotificationResult(
        response.status_code == 200,
        None if response.status_code == 200 else f"http_{response.status_code}",
    )


def send_budget_notification_connection_test() -> BudgetNotificationResult:
    webhook = str(
        os.getenv("X_ANALYTICS_BUDGET_SLACK_WEBHOOK_URL")
        or os.getenv("SLACK_X_DRAFT_REVIEW_WEBHOOK_URL")
        or ""
    ).strip()
    if not webhook:
        return BudgetNotificationResult(False, "destination_not_configured")
    try:
        import requests

        response = requests.post(
            webhook,
            json={
                "text": (
                    "接続テスト：X実績収集の予算確認通知を有効にしました。\n"
                    "基本上限は月$0.50です。これはテストで、増額承認は不要です。"
                )
            },
            timeout=15,
        )
    except requests.RequestException:
        return BudgetNotificationResult(False, "transport_failed")
    return BudgetNotificationResult(
        response.status_code == 200,
        None if response.status_code == 200 else f"http_{response.status_code}",
    )


def _month_bounds(value: datetime) -> tuple[datetime, datetime, str]:
    current = value.astimezone(UTC)
    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )
    return start, end, start.strftime("%Y-%m")


def _target_cost(target: CollectionTarget) -> Decimal:
    if target.recovery_only:
        return Decimal("0")
    return Decimal("0.010") if target.private_metrics_eligible else Decimal("0.005")


def _target_payload(target: CollectionTarget) -> dict[str, Any]:
    return {
        "post_id": target.post_id,
        "slot_id": target.slot_id,
        "scheduled_for": target.scheduled_for.astimezone(UTC).isoformat(),
        "private_metrics_eligible": target.private_metrics_eligible,
        "maximum_cost_usd": str(money(_target_cost(target))),
    }


def _request_key(month: str, kind: str, targets: tuple[CollectionTarget, ...]) -> str:
    payload = json.dumps(
        {
            "month": month,
            "kind": kind,
            "targets": [_target_payload(target) for target in targets],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class XAnalyticsApiBudgetService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _used(self, start: datetime, end: datetime) -> Decimal:
        value = self.session.scalar(
            select(
                func.coalesce(
                    func.sum(XAnalyticsApiCollectionSlot.estimated_cost_usd), 0
                )
            ).where(
                XAnalyticsApiCollectionSlot.source == "x_api_v2",
                XAnalyticsApiCollectionSlot.claimed_at >= start,
                XAnalyticsApiCollectionSlot.claimed_at < end,
            )
        )
        return money(value or 0)

    def _reserved(self, month: str) -> Decimal:
        value = self.session.scalar(
            select(
                func.coalesce(
                    func.sum(XAnalyticsApiBudgetRequest.reserved_cost_usd), 0
                )
            ).where(
                XAnalyticsApiBudgetRequest.budget_month_utc == month,
                XAnalyticsApiBudgetRequest.status == "RESERVED",
            )
        )
        return money(value or 0)

    def _reserved_target_keys(self, month: str) -> set[tuple[str, str]]:
        result: set[tuple[str, str]] = set()
        rows = self.session.scalars(
            select(XAnalyticsApiBudgetRequest).where(
                XAnalyticsApiBudgetRequest.budget_month_utc == month,
                XAnalyticsApiBudgetRequest.status == "RESERVED",
            )
        )
        for row in rows:
            for target in json.loads(row.targets_json):
                result.add((str(target["post_id"]), str(target["slot_id"])))
        return result

    @staticmethod
    def _deadline(targets: tuple[CollectionTarget, ...]) -> datetime | None:
        values = [
            target.posted_at.astimezone(UTC) + timedelta(days=29)
            for target in targets
            if target.private_metrics_eligible
        ]
        return min(values) if values else None

    def _new_row(
        self,
        *,
        month: str,
        kind: str,
        status: str,
        targets: tuple[CollectionTarget, ...],
        base_limit: Decimal,
        used: Decimal,
        reserved: Decimal,
        additional: Decimal,
    ) -> XAnalyticsApiBudgetRequest:
        row = XAnalyticsApiBudgetRequest(
            id=str(uuid.uuid4()),
            request_key=_request_key(month, kind, targets),
            budget_month_utc=month,
            status=status,
            base_limit_usd=money(base_limit),
            estimated_used_usd=used,
            reserved_cost_usd=reserved,
            additional_cost_usd=additional,
            target_count=len(targets),
            targets_json=json.dumps(
                [_target_payload(target) for target in targets],
                sort_keys=True,
                separators=(",", ":"),
            ),
            purpose=(
                "Collect scheduled X post metrics before private metrics expire."
            ),
            impact_if_skipped=(
                "The slot remains unobserved; private metrics may become unavailable."
            ),
            private_metrics_deadline_at=self._deadline(targets),
            reservation_expires_at=(
                datetime.now(UTC) + timedelta(minutes=15)
                if status == "RESERVED"
                else None
            ),
            evidence_json=json.dumps(
                {
                    "endpoint": "GET /2/tweets",
                    "unit_cost_usd": "0.005",
                    "pricing_basis": "standard_post_read_owned_discount_not_assumed",
                    "month_boundary_timezone": "UTC",
                },
                sort_keys=True,
            ),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def reserve(
        self,
        plan: CollectionPlan,
        *,
        base_limit: Decimal = BASE_MONTHLY_LIMIT_USD,
        notifier: Callable[[dict[str, Any]], BudgetNotificationResult] | None = None,
    ) -> BudgetDecision:
        self.session.rollback()
        self.session.execute(text("BEGIN IMMEDIATE"))
        start, end, month = _month_bounds(plan.as_of)
        now = datetime.now(UTC)
        expired = self.session.scalars(
            select(XAnalyticsApiBudgetRequest).where(
                XAnalyticsApiBudgetRequest.budget_month_utc == month,
                XAnalyticsApiBudgetRequest.status == "RESERVED",
                XAnalyticsApiBudgetRequest.reservation_expires_at < now,
            )
        )
        for row in expired:
            row.status = "CANCELLED"
        self.session.flush()
        used = self._used(start, end)
        already_reserved = self._reserved(month)
        reserved_keys = self._reserved_target_keys(month)
        candidates = tuple(
            target
            for target in plan.targets
            if (target.post_id, target.slot_id) not in reserved_keys
        )
        held_key = _request_key(month, "approval", candidates)
        existing_request = self.session.scalar(
            select(XAnalyticsApiBudgetRequest).where(
                XAnalyticsApiBudgetRequest.request_key == held_key
            )
        )
        effective_limit = money(base_limit)
        if existing_request is not None and existing_request.status == "APPROVED":
            effective_limit = money(existing_request.approved_limit_usd or base_limit)
        available = max(Decimal("0"), effective_limit - used - already_reserved)
        allowed: list[CollectionTarget] = []
        held: list[CollectionTarget] = []
        reserved_cost = Decimal("0")
        for target in candidates:
            cost = _target_cost(target)
            if reserved_cost + cost <= available:
                allowed.append(target)
                reserved_cost += cost
            else:
                held.append(target)

        reservation: XAnalyticsApiBudgetRequest | None = None
        if allowed:
            allowed_tuple = tuple(allowed)
            reservation_key = _request_key(month, "reservation", allowed_tuple)
            reservation = self.session.scalar(
                select(XAnalyticsApiBudgetRequest).where(
                    XAnalyticsApiBudgetRequest.request_key == reservation_key
                )
            )
            if reservation is None:
                reservation = self._new_row(
                    month=month,
                    kind="reservation",
                    status="RESERVED",
                    targets=allowed_tuple,
                    base_limit=base_limit,
                    used=used,
                    reserved=money(reserved_cost),
                    additional=Decimal("0"),
                )

        awaiting: XAnalyticsApiBudgetRequest | None = None
        if held:
            held_tuple = tuple(held)
            held_key = _request_key(month, "approval", held_tuple)
            awaiting = self.session.scalar(
                select(XAnalyticsApiBudgetRequest).where(
                    XAnalyticsApiBudgetRequest.request_key == held_key
                )
            )
            if awaiting is None:
                additional = money(sum((_target_cost(item) for item in held), Decimal("0")))
                awaiting = self._new_row(
                    month=month,
                    kind="approval",
                    status="AWAITING_BUDGET_APPROVAL",
                    targets=held_tuple,
                    base_limit=base_limit,
                    used=used,
                    reserved=Decimal("0"),
                    additional=additional,
                )
            elif awaiting.status == "REJECTED":
                self.session.commit()
                return BudgetDecision(
                    "rejected", month, effective_limit, used, already_reserved,
                    money(reserved_cost), money(available - reserved_cost),
                    tuple(allowed), tuple(held),
                    reservation.id if reservation else None, awaiting.id,
                )
        self.session.commit()

        if (
            awaiting is not None
            and awaiting.notification_status == "NOT_REQUESTED"
        ):
            payload = self.request_payload(awaiting.id)
            outcome = (
                notifier(payload)
                if notifier is not None
                else BudgetNotificationResult(False, "destination_not_configured")
            )
            awaiting.notification_status = "SENT" if outcome.sent else "FAILED"
            awaiting.notification_error = outcome.error
            awaiting.notified_at = datetime.now(UTC)
            self.session.commit()

        status = (
            "partially_reserved"
            if allowed and held
            else "awaiting_budget_approval"
            if held
            else "reserved"
        )
        return BudgetDecision(
            status=status,
            budget_month_utc=month,
            effective_limit_usd=effective_limit,
            estimated_used_usd=used,
            already_reserved_usd=already_reserved,
            reserved_usd=money(reserved_cost),
            remaining_usd=money(available - reserved_cost),
            allowed_targets=tuple(allowed),
            held_targets=tuple(held),
            reservation_id=reservation.id if reservation else None,
            awaiting_request_id=awaiting.id if awaiting else None,
        )

    def request_payload(self, request_id: str) -> dict[str, Any]:
        row = self.session.get(XAnalyticsApiBudgetRequest, request_id)
        if row is None:
            raise ValueError("budget request not found")
        reserved = self._reserved(row.budget_month_utc)
        return {
            "request_id": row.id,
            "status": row.status.lower(),
            "budget_month_utc": row.budget_month_utc,
            "estimated_used_usd": str(row.estimated_used_usd),
            "reserved_usd": str(reserved),
            "base_limit_usd": str(row.base_limit_usd),
            "remaining_base_budget_usd": str(
                max(
                    Decimal("0"),
                    money(row.base_limit_usd)
                    - money(row.estimated_used_usd)
                    - reserved,
                )
            ),
            "additional_cost_usd": str(row.additional_cost_usd),
            "target_count": row.target_count,
            "purpose": row.purpose,
            "impact_if_skipped": row.impact_if_skipped,
            "private_metrics_deadline_at": (
                row.private_metrics_deadline_at.isoformat()
                if row.private_metrics_deadline_at else None
            ),
            "choices": ["reject", "approve_with_monthly_limit"],
            "evidence": json.loads(row.evidence_json),
            "notification_status": row.notification_status,
            "decision_notification_status": row.decision_notification_status,
        }

    def decide(
        self,
        request_id: str,
        *,
        decision: str,
        actor: str,
        new_limit: Decimal | None,
        note: str | None = None,
        now: datetime | None = None,
        notifier: Callable[[dict[str, Any]], BudgetNotificationResult] | None = None,
    ) -> None:
        row = self.session.get(XAnalyticsApiBudgetRequest, request_id)
        if row is None or row.status != "AWAITING_BUDGET_APPROVAL":
            raise ValueError("budget request is not awaiting approval")
        _, _, current_month = _month_bounds(now or datetime.now(UTC))
        if row.budget_month_utc != current_month:
            raise ValueError("budget request month is no longer current")
        normalized = decision.strip().lower()
        if normalized == "approve":
            if new_limit is None or money(new_limit) <= money(row.base_limit_usd):
                raise ValueError("approved monthly limit must exceed base limit")
            row.status = "APPROVED"
            row.decision = "APPROVE"
            row.approved_limit_usd = money(new_limit)
        elif normalized == "reject":
            row.status = "REJECTED"
            row.decision = "REJECT"
        else:
            raise ValueError("decision must be approve or reject")
        row.decided_by = actor.strip()
        row.decided_at = now or datetime.now(UTC)
        row.decision_note = note
        self.session.commit()
        if row.decision_notification_status == "NOT_REQUESTED":
            payload = self.request_payload(row.id)
            outcome = (
                notifier(payload)
                if notifier is not None
                else BudgetNotificationResult(False, "destination_not_configured")
            )
            row.decision_notification_status = "SENT" if outcome.sent else "FAILED"
            row.decision_notification_error = outcome.error
            row.decision_notified_at = datetime.now(UTC)
            self.session.commit()

    def consume(self, reservation_id: str | None, *, actual_cost: Decimal) -> None:
        if reservation_id is None:
            return
        row = self.session.get(XAnalyticsApiBudgetRequest, reservation_id)
        if row is None or row.status != "RESERVED":
            return
        row.status = "CONSUMED"
        row.reserved_cost_usd = money(actual_cost)
        self.session.commit()

    def actual_cost_for_targets(
        self, targets: tuple[CollectionTarget, ...]
    ) -> Decimal:
        keys = {(target.post_id, target.slot_id) for target in targets}
        if not keys:
            return Decimal("0.000000")
        rows = self.session.scalars(
            select(XAnalyticsApiCollectionSlot).where(
                XAnalyticsApiCollectionSlot.source == "x_api_v2"
            )
        )
        return money(
            sum(
                (
                    Decimal(row.estimated_cost_usd)
                    for row in rows
                    if (row.post_id, row.slot_id) in keys
                ),
                Decimal("0"),
            )
        )

    def current_status(
        self,
        *,
        now: datetime | None = None,
        base_limit: Decimal = BASE_MONTHLY_LIMIT_USD,
    ) -> dict[str, Any]:
        start, end, month = _month_bounds(now or datetime.now(UTC))
        used = self._used(start, end)
        reserved = self._reserved(month)
        pending = list(
            self.session.scalars(
                select(XAnalyticsApiBudgetRequest).where(
                    XAnalyticsApiBudgetRequest.budget_month_utc == month,
                    XAnalyticsApiBudgetRequest.status == "AWAITING_BUDGET_APPROVAL",
                ).order_by(XAnalyticsApiBudgetRequest.created_at, XAnalyticsApiBudgetRequest.id)
            )
        )
        return {
            "budget_month_utc": month,
            "month_boundary_timezone": "UTC",
            "base_limit_usd": str(money(base_limit)),
            "estimated_used_usd": str(used),
            "reserved_usd": str(reserved),
            "remaining_usd": str(max(Decimal("0"), money(base_limit) - used - reserved)),
            "x_actual_billing_usd": None,
            "x_actual_billing_status": "not_verified",
            "pending_requests": [self.request_payload(row.id) for row in pending],
        }