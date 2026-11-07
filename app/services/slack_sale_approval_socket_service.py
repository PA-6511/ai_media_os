from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.sale_roundup import SaleCampaign
from app.services.sale_campaign_approval_service import (
    SaleCampaignApprovalError,
    SaleCampaignApprovalService,
)
from app.services.slack_approval_socket_service import (
    SlackApprovalInteraction,
    SlackApprovalSocketConfig,
)
from app.services.slack_sale_approval_message_service import (
    APPROVE_ACTION_ID,
    HOLD_ACTION_ID,
    REJECT_ACTION_ID,
    SlackSaleApprovalMessageError,
    build_sale_approval_update,
    decode_sale_approval_action,
)


_ACTION_DECISIONS = {
    APPROVE_ACTION_ID: "APPROVE",
    HOLD_ACTION_ID: "HOLD",
    REJECT_ACTION_ID: "REJECT",
}


class SlackSaleApprovalSocketError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SlackSaleApprovalSocketResult:
    code: str
    dry_run: bool
    request_id: str
    campaign_id: str
    decision: str
    status: str
    update_payload: dict[str, Any] | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SlackSaleApprovalSocketService:
    def __init__(
        self,
        session: Session,
        config: SlackApprovalSocketConfig,
    ) -> None:
        self.session = session
        self.config = config
        self.approvals = SaleCampaignApprovalService(session)

    def _authorize(self, interaction: SlackApprovalInteraction) -> None:
        if interaction.team_id != self.config.team_id:
            raise SlackSaleApprovalSocketError(
                "unauthorized_team", "Slack workspace is not authorized."
            )
        if interaction.channel_id != self.config.channel_id:
            raise SlackSaleApprovalSocketError(
                "unauthorized_channel", "Slack channel is not authorized."
            )
        if interaction.user_id not in self.config.approver_user_ids:
            raise SlackSaleApprovalSocketError(
                "unauthorized_user", "Slack user is not an approver."
            )

    def process_interaction(
        self,
        interaction: SlackApprovalInteraction,
    ) -> SlackSaleApprovalSocketResult:
        self._authorize(interaction)
        expected_decision = _ACTION_DECISIONS.get(interaction.action_id)
        if expected_decision is None:
            raise SlackSaleApprovalSocketError(
                "unsupported_action", "Slack action is not supported."
            )
        try:
            action = decode_sale_approval_action(interaction.action_value)
        except SlackSaleApprovalMessageError as exc:
            raise SlackSaleApprovalSocketError(exc.code, str(exc)) from exc
        if action.decision != expected_decision:
            raise SlackSaleApprovalSocketError(
                "decision_mismatch",
                "Slack action ID and decision do not match.",
            )
        try:
            request = self.approvals.get_request(
                request_id=action.request_id,
                campaign_id=action.campaign_id,
            )
        except SaleCampaignApprovalError as exc:
            raise SlackSaleApprovalSocketError(exc.code, str(exc)) from exc

        expected_binding = (
            request.slack_team_id,
            request.slack_channel_id,
            request.slack_message_ts,
        )
        actual_binding = (
            interaction.team_id,
            interaction.channel_id,
            interaction.message_ts,
        )
        if expected_binding != actual_binding:
            raise SlackSaleApprovalSocketError(
                "message_binding_mismatch",
                "Slack message does not match the approval request.",
            )
        if request.status != "PENDING":
            raise SlackSaleApprovalSocketError(
                "already_decided",
                "Sale approval request has already been processed.",
            )
        supplied_hash = hashlib.sha256(
            action.nonce.encode("utf-8")
        ).hexdigest()
        if not hmac.compare_digest(supplied_hash, request.request_nonce_hash):
            raise SlackSaleApprovalSocketError(
                "invalid_nonce", "Sale approval nonce is invalid."
            )

        campaign = self.session.get(SaleCampaign, action.campaign_id)
        if campaign is None:
            raise SlackSaleApprovalSocketError(
                "campaign_not_found", "Sale campaign was not found."
            )
        now = _utc_now()
        expired = _as_utc(request.expires_at) <= now
        if self.config.mode == "DRY_RUN":
            if expired:
                raise SlackSaleApprovalSocketError(
                    "request_expired", "Sale approval request has expired."
                )
            return SlackSaleApprovalSocketResult(
                code="dry_run_no_mutation",
                dry_run=True,
                request_id=request.id,
                campaign_id=request.campaign_id,
                decision=action.decision,
                status=request.status,
                update_payload=None,
            )

        actor = f"slack:{interaction.user_id}"
        try:
            if expired:
                decision_result = self.approvals.expire(
                    request_id=request.id,
                    campaign_id=request.campaign_id,
                    nonce=action.nonce,
                    decided_by=actor,
                    note="Expired during Slack action validation.",
                )
                code = "request_expired"
            else:
                method = {
                    "APPROVE": self.approvals.approve,
                    "HOLD": self.approvals.hold,
                    "REJECT": self.approvals.reject,
                }[action.decision]
                decision_result = method(
                    request_id=request.id,
                    campaign_id=request.campaign_id,
                    nonce=action.nonce,
                    decided_by=actor,
                    note="Decision received through Slack Socket Mode.",
                )
                code = "decision_applied"
        except SaleCampaignApprovalError as exc:
            raise SlackSaleApprovalSocketError(exc.code, str(exc)) from exc

        self.session.expire_all()
        refreshed = self.approvals.get_request(
            request_id=request.id,
            campaign_id=request.campaign_id,
        )
        update_payload = build_sale_approval_update(
            campaign_id=campaign.id,
            campaign_title=campaign.title,
            status=refreshed.status,
            actor_user_id=interaction.user_id,
            decided_at=refreshed.decided_at or now,
        )
        return SlackSaleApprovalSocketResult(
            code=code,
            dry_run=False,
            request_id=decision_result.request_id,
            campaign_id=decision_result.campaign_id,
            decision=action.decision,
            status=decision_result.status,
            update_payload=update_payload,
        )
