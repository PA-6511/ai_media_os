from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.sale_campaign_approval import (
    SaleCampaignApprovalRequest,
)
from app.db.models.sale_roundup import SaleCampaign


DEFAULT_TTL_MINUTES = 1440
MAX_TTL_MINUTES = 10080
TERMINAL_STATUSES = frozenset(
    {"APPROVED", "REJECTED", "EXPIRED", "CANCELLED"}
)


class SaleCampaignApprovalError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SaleCampaignApprovalTicket:
    request_id: str
    campaign_id: str
    nonce: str
    expires_at: datetime


@dataclass(frozen=True)
class SaleCampaignApprovalDecisionResult:
    request_id: str
    campaign_id: str
    status: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_nonce(nonce: str) -> str:
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


class SaleCampaignApprovalService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _required(
        value: str,
        field_name: str,
        *,
        max_length: int,
    ) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise SaleCampaignApprovalError(
                f"invalid_{field_name}",
                f"{field_name} is required.",
            )
        if len(normalized) > max_length:
            raise SaleCampaignApprovalError(
                f"invalid_{field_name}",
                f"{field_name} exceeds maximum length.",
            )
        return normalized

    def _load_request(
        self,
        *,
        request_id: str,
        campaign_id: str,
        for_update: bool,
    ) -> SaleCampaignApprovalRequest:
        normalized_request_id = self._required(
            request_id,
            "request_id",
            max_length=36,
        )
        normalized_campaign_id = self._required(
            campaign_id,
            "campaign_id",
            max_length=128,
        )
        statement = select(SaleCampaignApprovalRequest).where(
            SaleCampaignApprovalRequest.id == normalized_request_id
        )
        if for_update:
            statement = statement.with_for_update()
        request = self.session.scalar(statement)
        if request is None:
            raise SaleCampaignApprovalError(
                "request_not_found",
                "Sale campaign approval request was not found.",
            )
        if request.campaign_id != normalized_campaign_id:
            raise SaleCampaignApprovalError(
                "campaign_mismatch",
                "Approval request does not belong to the campaign.",
            )
        return request

    @staticmethod
    def _verify_nonce(
        request: SaleCampaignApprovalRequest,
        nonce: str,
    ) -> None:
        supplied_hash = _hash_nonce(nonce or "")
        if not hmac.compare_digest(
            supplied_hash,
            request.request_nonce_hash,
        ):
            raise SaleCampaignApprovalError(
                "invalid_nonce",
                "Approval nonce is invalid.",
            )

    def create_request(
        self,
        *,
        campaign_id: str,
        requested_by: str,
        ttl_minutes: int = DEFAULT_TTL_MINUTES,
    ) -> SaleCampaignApprovalTicket:
        normalized_campaign_id = self._required(
            campaign_id,
            "campaign_id",
            max_length=128,
        )
        actor = self._required(
            requested_by,
            "requested_by",
            max_length=128,
        )
        if ttl_minutes < 1 or ttl_minutes > MAX_TTL_MINUTES:
            raise SaleCampaignApprovalError(
                "invalid_expiration",
                "ttl_minutes must be between 1 and 10080.",
            )
        if self.session.get(SaleCampaign, normalized_campaign_id) is None:
            raise SaleCampaignApprovalError(
                "campaign_not_found",
                "Sale campaign was not found.",
            )

        now = _utc_now()
        pending = self.session.scalar(
            select(SaleCampaignApprovalRequest)
            .where(
                SaleCampaignApprovalRequest.campaign_id
                == normalized_campaign_id,
                SaleCampaignApprovalRequest.status == "PENDING",
            )
            .order_by(SaleCampaignApprovalRequest.requested_at.desc())
            .limit(1)
            .with_for_update()
        )
        if pending is not None:
            if _as_utc(pending.expires_at) <= now:
                pending.status = "EXPIRED"
                pending.decided_by = "system:expiration"
                pending.decided_at = now
                pending.decision_note = "Expired before replacement request."
                self.session.flush()
            else:
                raise SaleCampaignApprovalError(
                    "duplicate_pending",
                    "A pending approval request already exists.",
                )

        nonce = secrets.token_urlsafe(32)
        expires_at = now + timedelta(minutes=ttl_minutes)
        request = SaleCampaignApprovalRequest(
            campaign_id=normalized_campaign_id,
            request_nonce_hash=_hash_nonce(nonce),
            requested_by=actor,
            requested_at=now,
            expires_at=expires_at,
        )
        self.session.add(request)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            duplicate = self.session.scalar(
                select(SaleCampaignApprovalRequest.id).where(
                    SaleCampaignApprovalRequest.campaign_id
                    == normalized_campaign_id,
                    SaleCampaignApprovalRequest.status == "PENDING",
                )
            )
            if duplicate is not None:
                raise SaleCampaignApprovalError(
                    "duplicate_pending",
                    "A pending approval request already exists.",
                ) from exc
            raise
        except Exception:
            self.session.rollback()
            raise

        return SaleCampaignApprovalTicket(
            request_id=request.id,
            campaign_id=request.campaign_id,
            nonce=nonce,
            expires_at=expires_at,
        )

    def get_request(
        self,
        *,
        request_id: str,
        campaign_id: str,
    ) -> SaleCampaignApprovalRequest:
        return self._load_request(
            request_id=request_id,
            campaign_id=campaign_id,
            for_update=False,
        )

    def _decide(
        self,
        *,
        request_id: str,
        campaign_id: str,
        nonce: str,
        decided_by: str,
        target_status: str,
        allowed_sources: frozenset[str],
        note: str,
    ) -> SaleCampaignApprovalDecisionResult:
        actor = self._required(
            decided_by,
            "decided_by",
            max_length=128,
        )
        request = self._load_request(
            request_id=request_id,
            campaign_id=campaign_id,
            for_update=True,
        )
        self._verify_nonce(request, nonce)

        if request.status in TERMINAL_STATUSES:
            raise SaleCampaignApprovalError(
                "already_decided",
                "Approval request has already reached a terminal status.",
            )

        now = _utc_now()
        is_due = _as_utc(request.expires_at) <= now

        if target_status == "EXPIRED":
            if request.status != "PENDING":
                raise SaleCampaignApprovalError(
                    "invalid_transition",
                    "Only pending requests can expire.",
                )
            if not is_due:
                raise SaleCampaignApprovalError(
                    "not_expired",
                    "Approval request has not reached its expiration time.",
                )
        elif request.status == "PENDING" and is_due:
            request.status = "EXPIRED"
            request.decided_by = actor
            request.decided_at = now
            request.decision_note = note or "Approval request expired."
            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise
            raise SaleCampaignApprovalError(
                "expired",
                "Approval request has expired.",
            )
        elif request.status not in allowed_sources:
            raise SaleCampaignApprovalError(
                "invalid_transition",
                f"Cannot transition {request.status} to {target_status}.",
            )

        request.status = target_status
        request.decided_by = actor
        request.decided_at = now
        request.decision_note = note or None
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return SaleCampaignApprovalDecisionResult(
            request_id=request.id,
            campaign_id=request.campaign_id,
            status=request.status,
        )

    def approve(
        self,
        *,
        request_id: str,
        campaign_id: str,
        nonce: str,
        decided_by: str,
        note: str = "",
    ) -> SaleCampaignApprovalDecisionResult:
        return self._decide(
            request_id=request_id,
            campaign_id=campaign_id,
            nonce=nonce,
            decided_by=decided_by,
            target_status="APPROVED",
            allowed_sources=frozenset({"PENDING"}),
            note=note,
        )

    def reject(
        self,
        *,
        request_id: str,
        campaign_id: str,
        nonce: str,
        decided_by: str,
        note: str = "",
    ) -> SaleCampaignApprovalDecisionResult:
        return self._decide(
            request_id=request_id,
            campaign_id=campaign_id,
            nonce=nonce,
            decided_by=decided_by,
            target_status="REJECTED",
            allowed_sources=frozenset({"PENDING"}),
            note=note,
        )

    def hold(
        self,
        *,
        request_id: str,
        campaign_id: str,
        nonce: str,
        decided_by: str,
        note: str = "",
    ) -> SaleCampaignApprovalDecisionResult:
        return self._decide(
            request_id=request_id,
            campaign_id=campaign_id,
            nonce=nonce,
            decided_by=decided_by,
            target_status="ON_HOLD",
            allowed_sources=frozenset({"PENDING"}),
            note=note,
        )

    def expire(
        self,
        *,
        request_id: str,
        campaign_id: str,
        nonce: str,
        decided_by: str,
        note: str = "",
    ) -> SaleCampaignApprovalDecisionResult:
        return self._decide(
            request_id=request_id,
            campaign_id=campaign_id,
            nonce=nonce,
            decided_by=decided_by,
            target_status="EXPIRED",
            allowed_sources=frozenset({"PENDING"}),
            note=note,
        )

    def cancel(
        self,
        *,
        request_id: str,
        campaign_id: str,
        nonce: str,
        decided_by: str,
        note: str = "",
    ) -> SaleCampaignApprovalDecisionResult:
        return self._decide(
            request_id=request_id,
            campaign_id=campaign_id,
            nonce=nonce,
            decided_by=decided_by,
            target_status="CANCELLED",
            allowed_sources=frozenset({"PENDING", "ON_HOLD"}),
            note=note,
        )

    def bind_slack_message(
        self,
        *,
        request_id: str,
        campaign_id: str,
        team_id: str,
        channel_id: str,
        message_ts: str,
    ) -> SaleCampaignApprovalRequest:
        team = self._required(team_id, "team_id", max_length=64)
        channel = self._required(channel_id, "channel_id", max_length=64)
        timestamp = self._required(
            message_ts,
            "message_ts",
            max_length=64,
        )
        request = self._load_request(
            request_id=request_id,
            campaign_id=campaign_id,
            for_update=True,
        )
        if request.status != "PENDING":
            raise SaleCampaignApprovalError(
                "invalid_status",
                "Only pending requests can be bound to a Slack message.",
            )

        existing = (
            request.slack_team_id,
            request.slack_channel_id,
            request.slack_message_ts,
        )
        target = (team, channel, timestamp)
        if any(value is not None for value in existing):
            if existing == target:
                return request
            raise SaleCampaignApprovalError(
                "already_bound",
                "Approval request is already bound to another message.",
            )

        request.slack_team_id = team
        request.slack_channel_id = channel
        request.slack_message_ts = timestamp
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return request
