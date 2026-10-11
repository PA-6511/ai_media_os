from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from dev_agent.proposal_bridge import (
    load_write_proposal,
    mark_proposal_approved,
)


DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID = (
    "dev_agent_proposal_approve"
)


class SlackInteractionLike(Protocol):
    team_id: str
    channel_id: str
    user_id: str
    message_ts: str
    action_id: str
    action_value: str


class SlackConfigLike(Protocol):
    team_id: str
    channel_id: str
    approver_user_ids: frozenset[str]
    mode: str


class SlackProposalApprovalError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SlackProposalApprovalResult:
    proposal_id: str
    proposal_state: str
    dry_run: bool


def _slack_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _clip(
    value: Any,
    limit: int,
) -> str:
    text = str(value or "")

    if len(text) <= limit:
        return text

    return text[: limit - 1] + "…"


def _authorize(
    interaction: SlackInteractionLike,
    config: SlackConfigLike,
) -> None:
    if interaction.team_id != config.team_id:
        raise SlackProposalApprovalError(
            "unauthorized_team",
            "Slack workspace is not authorized.",
        )

    if interaction.channel_id != config.channel_id:
        raise SlackProposalApprovalError(
            "unauthorized_channel",
            "Slack channel is not authorized.",
        )

    if (
        interaction.user_id
        not in config.approver_user_ids
    ):
        raise SlackProposalApprovalError(
            "unauthorized_user",
            "Slack user is not an approver.",
        )


def approve_slack_proposal(
    *,
    interaction: SlackInteractionLike,
    config: SlackConfigLike,
) -> SlackProposalApprovalResult:
    _authorize(
        interaction,
        config,
    )

    if (
        interaction.action_id
        != DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID
    ):
        raise SlackProposalApprovalError(
            "unsupported_action",
            "Slack action is not supported.",
        )

    proposal_id = (
        interaction.action_value or ""
    ).strip()

    if not proposal_id:
        raise SlackProposalApprovalError(
            "invalid_proposal_id",
            "proposal_id is required.",
        )

    proposal = load_write_proposal(
        proposal_id
    )

    if proposal["status"] != "VALID":
        raise SlackProposalApprovalError(
            str(
                proposal.get(
                    "reason",
                    "PROPOSAL_VALIDATION_FAILED",
                )
            ),
            "Dev Agent proposal validation failed.",
        )

    if config.mode == "DRY_RUN":
        return SlackProposalApprovalResult(
            proposal_id=proposal_id,
            proposal_state=str(
                proposal.get(
                    "proposal_state",
                    "PENDING",
                )
            ),
            dry_run=True,
        )

    approval = mark_proposal_approved(
        proposal_id
    )

    if approval["status"] != "VALID":
        raise SlackProposalApprovalError(
            str(
                approval.get(
                    "reason",
                    "PROPOSAL_APPROVAL_FAILED",
                )
            ),
            "Dev Agent proposal approval failed.",
        )

    return SlackProposalApprovalResult(
        proposal_id=proposal_id,
        proposal_state=str(
            approval["proposal_state"]
        ),
        dry_run=False,
    )


def build_slack_proposal_approval_message(
    proposal_id: str,
) -> dict[str, Any]:
    proposal = load_write_proposal(
        proposal_id
    )

    if proposal["status"] != "VALID":
        raise SlackProposalApprovalError(
            str(
                proposal.get(
                    "reason",
                    "PROPOSAL_VALIDATION_FAILED",
                )
            ),
            "Dev Agent proposal validation failed.",
        )

    relative_path = _slack_escape(
        proposal["relative_path"]
    )

    old_text = _slack_escape(
        _clip(
            proposal["old_text"],
            700,
        )
    )

    new_text = _slack_escape(
        _clip(
            proposal["new_text"],
            700,
        )
    )

    before_sha256 = _slack_escape(
        proposal["before_sha256"]
    )

    proposal_text = _slack_escape(
        proposal_id
    )

    return {
        "text": (
            "Dev Agent proposal 承認待ち: "
            f"{proposal_id}"
        ),
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": (
                        "Dev Agent 修正Proposal 承認待ち"
                    ),
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Proposal ID*\n"
                        f"`{proposal_text}`\n\n"
                        f"*対象ファイル*\n"
                        f"`{relative_path}`\n\n"
                        f"*Before SHA256*\n"
                        f"`{before_sha256}`"
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*OLD*\n"
                            f"```{old_text}```"
                        ),
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*NEW*\n"
                            f"```{new_text}```"
                        ),
                    },
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Proposalを承認",
                            "emoji": True,
                        },
                        "action_id": (
                            DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID
                        ),
                        "value": proposal_id,
                        "style": "primary",
                        "confirm": {
                            "title": {
                                "type": "plain_text",
                                "text": "承認確認",
                            },
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    "このProposal IDを"
                                    "承認します。\n"
                                    "この操作だけでは"
                                    "AI実行は開始しません。"
                                ),
                            },
                            "confirm": {
                                "type": "plain_text",
                                "text": "承認する",
                            },
                            "deny": {
                                "type": "plain_text",
                                "text": "キャンセル",
                            },
                        },
                    }
                ],
            },
        ],
        "unfurl_links": False,
        "unfurl_media": False,
    }
