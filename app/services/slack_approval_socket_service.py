from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)
from app.db.repositories.workflow_approval_repository import (
    WorkflowApprovalRepository,
)
from app.services.slack_approval_message_service import (
    SlackApprovalMessageError,
    decode_slack_approval_action,
)
from app.services.workflow_approval_service import (
    WorkflowApprovalError,
    WorkflowApprovalService,
)


_ACTION_DECISIONS = {
    "ebook_approval_approve": "APPROVE",
    "ebook_approval_reject": "REJECT",
    "ebook_approval_hold": "HOLD",
}

_ALLOWED_MODES = {
    "DRY_RUN",
    "LIVE",
}

_LIVE_CONFIRM_VALUE = "I_UNDERSTAND_DB_WRITES"


class SlackApprovalSocketError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SlackApprovalSocketConfig:
    bot_token: str = field(repr=False)
    app_token: str = field(repr=False)

    team_id: str
    channel_id: str
    approver_user_ids: frozenset[str]

    mode: str
    live_confirmed: bool = False

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, str],
    ) -> "SlackApprovalSocketConfig":
        bot_token = str(
            values.get("SLACK_BOT_TOKEN", "")
        ).strip()

        app_token = str(
            values.get("SLACK_APP_TOKEN", "")
        ).strip()

        team_id = str(
            values.get(
                "SLACK_APPROVAL_TEAM_ID",
                "",
            )
        ).strip()

        channel_id = str(
            values.get(
                "SLACK_APPROVAL_CHANNEL_ID",
                "",
            )
        ).strip()

        raw_approvers = str(
            values.get(
                "SLACK_APPROVER_USER_IDS",
                "",
            )
        )

        approvers = frozenset(
            value.strip()
            for value in raw_approvers.split(",")
            if value.strip()
        )

        mode = str(
            values.get(
                "SLACK_APPROVAL_MODE",
                "DRY_RUN",
            )
        ).strip().upper()

        live_confirm = str(
            values.get(
                "SLACK_APPROVAL_LIVE_CONFIRM",
                "",
            )
        ).strip()

        if not bot_token.startswith("xoxb-"):
            raise SlackApprovalSocketError(
                "invalid_bot_token",
                "SLACK_BOT_TOKEN must start with xoxb-.",
            )

        if not app_token.startswith("xapp-"):
            raise SlackApprovalSocketError(
                "invalid_app_token",
                "SLACK_APP_TOKEN must start with xapp-.",
            )

        if not team_id.startswith("T"):
            raise SlackApprovalSocketError(
                "invalid_team_id",
                "SLACK_APPROVAL_TEAM_ID is invalid.",
            )

        if not channel_id.startswith("C"):
            raise SlackApprovalSocketError(
                "invalid_channel_id",
                "SLACK_APPROVAL_CHANNEL_ID is invalid.",
            )

        if not approvers:
            raise SlackApprovalSocketError(
                "missing_approvers",
                "At least one Slack approver is required.",
            )

        if not all(
            user_id.startswith("U")
            for user_id in approvers
        ):
            raise SlackApprovalSocketError(
                "invalid_approver_id",
                "Slack approver IDs must start with U.",
            )

        if mode not in _ALLOWED_MODES:
            raise SlackApprovalSocketError(
                "invalid_mode",
                "SLACK_APPROVAL_MODE must be "
                "DRY_RUN or LIVE.",
            )

        live_confirmed = (
            live_confirm == _LIVE_CONFIRM_VALUE
        )

        if mode == "LIVE" and not live_confirmed:
            raise SlackApprovalSocketError(
                "live_not_confirmed",
                "LIVE mode requires explicit "
                "SLACK_APPROVAL_LIVE_CONFIRM.",
            )

        return cls(
            bot_token=bot_token,
            app_token=app_token,
            team_id=team_id,
            channel_id=channel_id,
            approver_user_ids=approvers,
            mode=mode,
            live_confirmed=live_confirmed,
        )


@dataclass(frozen=True)
class SlackApprovalInteraction:
    team_id: str
    channel_id: str
    user_id: str
    message_ts: str
    action_id: str
    action_value: str


@dataclass(frozen=True)
class SlackApprovalSocketResult:
    code: str
    dry_run: bool

    request_id: str
    decision: str
    request_status: str

    before_workflow_status: str
    after_workflow_status: str

    update_payload: dict[str, Any] | None


def _required(
    value: Any,
    field_name: str,
) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise SlackApprovalSocketError(
            "invalid_interaction",
            f"{field_name} is missing.",
        )

    return normalized


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def _slack_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def parse_slack_approval_interaction(
    body: Mapping[str, Any],
) -> SlackApprovalInteraction:
    team = body.get("team")
    channel = body.get("channel")
    user = body.get("user")
    container = body.get("container")
    message = body.get("message")
    actions = body.get("actions")

    team_mapping = (
        team if isinstance(team, Mapping) else {}
    )
    channel_mapping = (
        channel
        if isinstance(channel, Mapping)
        else {}
    )
    user_mapping = (
        user if isinstance(user, Mapping) else {}
    )
    container_mapping = (
        container
        if isinstance(container, Mapping)
        else {}
    )
    message_mapping = (
        message
        if isinstance(message, Mapping)
        else {}
    )

    if not isinstance(actions, list) or not actions:
        raise SlackApprovalSocketError(
            "invalid_interaction",
            "Slack action is missing.",
        )

    action = actions[0]

    if not isinstance(action, Mapping):
        raise SlackApprovalSocketError(
            "invalid_interaction",
            "Slack action is invalid.",
        )

    team_id = _required(
        team_mapping.get("id"),
        "team_id",
    )

    channel_id = _required(
        channel_mapping.get("id")
        or container_mapping.get("channel_id"),
        "channel_id",
    )

    user_id = _required(
        user_mapping.get("id"),
        "user_id",
    )

    message_ts = _required(
        container_mapping.get("message_ts")
        or message_mapping.get("ts"),
        "message_ts",
    )

    action_id = _required(
        action.get("action_id"),
        "action_id",
    )

    action_value = _required(
        action.get("value"),
        "action_value",
    )

    return SlackApprovalInteraction(
        team_id=team_id,
        channel_id=channel_id,
        user_id=user_id,
        message_ts=message_ts,
        action_id=action_id,
        action_value=action_value,
    )


def _build_final_update_payload(
    *,
    item: EbookItem,
    request: WorkflowApprovalRequest,
    decision: str,
    actor_user_id: str,
) -> dict[str, Any]:
    title = _slack_escape(item.title)
    final_status = request.status

    if decision == "APPROVE":
        symbol = "✅"
        heading = "承認済み"
    elif decision == "REJECT":
        symbol = "↩️"
        heading = "差戻し済み"
    else:
        symbol = "⏸️"
        heading = "保留中"

    fallback = (
        f"{symbol} 電子書籍記事 {heading}: "
        f"{item.title} / "
        f"{item.workflow_status}"
    )

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": (
                    f"{symbol} 電子書籍記事 "
                    f"{heading}"
                ),
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*作品名*\n{title}\n\n"
                    f"*Workflow*\n"
                    f"`{item.workflow_status}`\n\n"
                    f"*承認要求状態*\n"
                    f"`{final_status}`"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "処理者: "
                        f"`{actor_user_id}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "承認要求ID: "
                        f"`{request.id}`"
                    ),
                },
            ],
        },
    ]

    return {
        "text": fallback,
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }


class SlackApprovalSocketService:
    def __init__(
        self,
        session: Session,
        config: SlackApprovalSocketConfig,
    ) -> None:
        self.session = session
        self.config = config

        self.repository = WorkflowApprovalRepository(
            session
        )

    def _authorize(
        self,
        interaction: SlackApprovalInteraction,
    ) -> None:
        if interaction.team_id != self.config.team_id:
            raise SlackApprovalSocketError(
                "unauthorized_team",
                "Slack workspace is not authorized.",
            )

        if (
            interaction.channel_id
            != self.config.channel_id
        ):
            raise SlackApprovalSocketError(
                "unauthorized_channel",
                "Slack channel is not authorized.",
            )

        if (
            interaction.user_id
            not in self.config.approver_user_ids
        ):
            raise SlackApprovalSocketError(
                "unauthorized_user",
                "Slack user is not an approver.",
            )

    def process_interaction(
        self,
        interaction: SlackApprovalInteraction,
    ) -> SlackApprovalSocketResult:
        self._authorize(interaction)

        expected_decision = _ACTION_DECISIONS.get(
            interaction.action_id
        )

        if expected_decision is None:
            raise SlackApprovalSocketError(
                "unsupported_action",
                "Slack action is not supported.",
            )

        try:
            decoded_action = (
                decode_slack_approval_action(
                    interaction.action_value
                )
            )
        except SlackApprovalMessageError as exc:
            raise SlackApprovalSocketError(
                exc.code,
                str(exc),
            ) from exc

        if (
            decoded_action.decision
            != expected_decision
        ):
            raise SlackApprovalSocketError(
                "decision_mismatch",
                "Slack action ID and decision "
                "do not match.",
            )

        request = self.repository.get(
            decoded_action.request_id
        )

        if request is None:
            raise SlackApprovalSocketError(
                "request_not_found",
                "Approval request was not found.",
            )

        binding = (
            request.slack_team_id,
            request.slack_channel_id,
            request.slack_message_ts,
        )

        interaction_binding = (
            interaction.team_id,
            interaction.channel_id,
            interaction.message_ts,
        )

        if binding != interaction_binding:
            raise SlackApprovalSocketError(
                "message_binding_mismatch",
                "Slack message does not match "
                "the approval request.",
            )

        if request.status != "PENDING":
            raise SlackApprovalSocketError(
                "request_not_pending",
                "Approval request is no longer pending.",
            )

        supplied_hash = _hash_token(
            decoded_action.token
        )

        if not hmac.compare_digest(
            supplied_hash,
            request.request_nonce_hash,
        ):
            raise SlackApprovalSocketError(
                "invalid_token",
                "Approval token is invalid.",
            )

        now = datetime.now(timezone.utc)

        if _as_utc(request.expires_at) <= now:
            raise SlackApprovalSocketError(
                "request_expired",
                "Approval request has expired.",
            )

        item = self.session.get(
            EbookItem,
            request.ebook_item_id,
        )

        if item is None:
            raise SlackApprovalSocketError(
                "item_not_found",
                "Referenced ebook item was not found.",
            )

        before_status = item.workflow_status

        if (
            before_status
            != request.expected_current_status
        ):
            raise SlackApprovalSocketError(
                "stale_workflow_state",
                "Workflow state no longer matches "
                "the approval request.",
            )

        if self.config.mode == "DRY_RUN":
            return SlackApprovalSocketResult(
                code="dry_run_no_mutation",
                dry_run=True,
                request_id=request.id,
                decision=decoded_action.decision,
                request_status=request.status,
                before_workflow_status=before_status,
                after_workflow_status=before_status,
                update_payload=None,
            )

        try:
            decision_result = (
                WorkflowApprovalService(
                    self.session
                ).decide_request(
                    request_id=request.id,
                    token=decoded_action.token,
                    decision=decoded_action.decision,
                    decided_by=(
                        f"slack:{interaction.user_id}"
                    ),
                    note=(
                        "Decision received through "
                        "Slack Socket Mode."
                    ),
                )
            )
        except WorkflowApprovalError as exc:
            raise SlackApprovalSocketError(
                exc.code,
                str(exc),
            ) from exc

        self.session.expire_all()

        refreshed_request = self.repository.get(
            request.id
        )

        refreshed_item = self.session.get(
            EbookItem,
            request.ebook_item_id,
        )

        if (
            refreshed_request is None
            or refreshed_item is None
        ):
            raise SlackApprovalSocketError(
                "post_decision_load_failed",
                "Updated approval data could "
                "not be reloaded.",
            )

        update_payload = _build_final_update_payload(
            item=refreshed_item,
            request=refreshed_request,
            decision=decoded_action.decision,
            actor_user_id=interaction.user_id,
        )

        return SlackApprovalSocketResult(
            code="decision_applied",
            dry_run=False,
            request_id=decision_result.request_id,
            decision=decision_result.decision,
            request_status=(
                decision_result.request_status
            ),
            before_workflow_status=(
                decision_result.before_workflow_status
            ),
            after_workflow_status=(
                decision_result.after_workflow_status
            ),
            update_payload=update_payload,
        )
