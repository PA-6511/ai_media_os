from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Any, Protocol


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


from dev_agent.proposal_bridge import (  # noqa: E402
    load_write_proposal,
)
from dev_agent.slack_proposal_approval_adapter import (  # noqa: E402
    build_slack_proposal_approval_message,
)


class SlackSendConfigLike(Protocol):
    bot_token: str
    team_id: str
    channel_id: str
    mode: str
    live_confirmed: bool


class DevAgentProposalSlackSendError(
    RuntimeError
):
    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DevAgentProposalSlackSendResult:
    proposal_id: str
    proposal_state: str
    team_id: str
    channel_id: str
    message_ts: str


def preflight_dev_agent_proposal_for_send(
    proposal_id: str,
) -> tuple[str, str]:
    normalized_id = str(
        proposal_id or ""
    ).strip()

    if not normalized_id:
        raise DevAgentProposalSlackSendError(
            "invalid_proposal_id",
            "proposal_id is required.",
        )

    proposal = load_write_proposal(
        normalized_id
    )

    if proposal["status"] != "VALID":
        raise DevAgentProposalSlackSendError(
            str(
                proposal.get(
                    "reason",
                    "PROPOSAL_VALIDATION_FAILED",
                )
            ),
            "Dev Agent proposal validation failed.",
        )

    proposal_state = str(
        proposal.get(
            "proposal_state",
            "",
        )
    )

    if proposal_state != "PENDING":
        raise DevAgentProposalSlackSendError(
            "PROPOSAL_NOT_PENDING",
            "Only PENDING proposals may be sent.",
        )

    return normalized_id, proposal_state


def send_dev_agent_proposal(
    *,
    client: Any,
    config: SlackSendConfigLike,
    proposal_id: str,
) -> DevAgentProposalSlackSendResult:
    (
        normalized_id,
        proposal_state,
    ) = preflight_dev_agent_proposal_for_send(
        proposal_id
    )

    if (
        config.mode != "LIVE"
        or not config.live_confirmed
    ):
        raise DevAgentProposalSlackSendError(
            "live_send_not_enabled",
            "Slack LIVE send is not explicitly enabled.",
        )

    payload = (
        build_slack_proposal_approval_message(
            normalized_id
        )
    )

    response = client.chat_postMessage(
        channel=config.channel_id,
        **payload,
    )

    if (
        not response
        or response.get("ok") is False
    ):
        raise DevAgentProposalSlackSendError(
            "slack_send_failed",
            "Slack chat_postMessage failed.",
        )

    response_channel = str(
        response.get("channel") or ""
    ).strip()

    message_ts = str(
        response.get("ts") or ""
    ).strip()

    if (
        response_channel != config.channel_id
        or not message_ts
    ):
        raise DevAgentProposalSlackSendError(
            "invalid_slack_response",
            "Slack response binding is invalid.",
        )

    return DevAgentProposalSlackSendResult(
        proposal_id=normalized_id,
        proposal_state=proposal_state,
        team_id=config.team_id,
        channel_id=response_channel,
        message_ts=message_ts,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Send one PENDING Dev Agent "
            "proposal approval request to Slack."
        )
    )

    parser.add_argument(
        "--proposal-id",
        required=True,
    )

    parser.add_argument(
        "--send",
        action="store_true",
        required=True,
        help=(
            "Explicitly authorize one Slack "
            "network message send."
        ),
    )

    return parser.parse_args()


def main() -> int:
    from slack_sdk import WebClient

    from app.services.slack_approval_socket_service import (
        SlackApprovalSocketConfig,
    )

    args = parse_args()

    # Fail closed before requiring Slack credentials.
    # send_dev_agent_proposal() repeats this check
    # immediately before the network send.
    try:
        preflight_dev_agent_proposal_for_send(
            args.proposal_id
        )
    except DevAgentProposalSlackSendError as exc:
        print(
            f"DEV_AGENT_PROPOSAL_SLACK_SEND=DENIED"
        )
        print(
            f"ERROR_CODE={exc.code}"
        )
        print(
            "NETWORK_MESSAGE_SENT=NO"
        )
        print(
            "SOURCE_WRITE_PERFORMED=NO"
        )
        print(
            "AI_EXECUTION_STARTED=NO"
        )
        return 2

    config = (
        SlackApprovalSocketConfig.from_mapping(
            os.environ
        )
    )

    result = send_dev_agent_proposal(
        client=WebClient(
            token=config.bot_token
        ),
        config=config,
        proposal_id=args.proposal_id,
    )

    print(
        f"PROPOSAL_ID={result.proposal_id}"
    )
    print(
        f"PROPOSAL_STATE="
        f"{result.proposal_state}"
    )
    print(
        f"SLACK_TEAM_ID={result.team_id}"
    )
    print(
        f"SLACK_CHANNEL_ID="
        f"{result.channel_id}"
    )
    print(
        f"SLACK_MESSAGE_TS="
        f"{result.message_ts}"
    )
    print(
        "SOURCE_WRITE_PERFORMED=NO"
    )
    print(
        "AI_EXECUTION_STARTED=NO"
    )
    print(
        "PROTOTYPE_4F_B_SEND=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
