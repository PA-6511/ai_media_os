from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Mapping


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


from sqlalchemy.orm import Session

from app.services.sale_campaign_approval_service import (
    SaleCampaignApprovalService,
)
from app.services.slack_approval_socket_service import (
    SlackApprovalSocketConfig,
)
from app.services.slack_sale_approval_message_service import (
    build_sale_approval_message,
)


class SaleApprovalSendError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SaleApprovalSendResult:
    request_id: str
    campaign_id: str
    expires_at: datetime
    team_id: str
    channel_id: str
    message_ts: str
    payload: dict[str, Any]


def send_sale_campaign_approval(
    *,
    session: Session,
    client: Any,
    config: SlackApprovalSocketConfig,
    snapshot: Mapping[str, Any],
    requested_by: str,
    ttl_minutes: int = 1440,
) -> SaleApprovalSendResult:
    if config.mode != "LIVE" or not config.live_confirmed:
        raise SaleApprovalSendError(
            "live_send_not_enabled",
            "Slack approval LIVE mode is not explicitly confirmed.",
        )
    campaign_id = str(snapshot.get("campaign_id") or "").strip()
    ticket = SaleCampaignApprovalService(session).create_request(
        campaign_id=campaign_id,
        requested_by=requested_by,
        ttl_minutes=ttl_minutes,
    )
    request = SaleCampaignApprovalService(session).get_request(
        request_id=ticket.request_id,
        campaign_id=campaign_id,
    )
    payload = build_sale_approval_message(
        snapshot=snapshot,
        request_id=ticket.request_id,
        campaign_id=campaign_id,
        nonce=ticket.nonce,
        status=request.status,
        expires_at=ticket.expires_at,
    )
    response = client.chat_postMessage(
        channel=config.channel_id,
        **payload,
    )
    if not response or response.get("ok") is False:
        raise SaleApprovalSendError(
            "slack_send_failed",
            "Slack chat_postMessage failed.",
        )
    response_channel = str(response.get("channel") or "").strip()
    message_ts = str(response.get("ts") or "").strip()
    if response_channel != config.channel_id or not message_ts:
        raise SaleApprovalSendError(
            "invalid_slack_response",
            "Slack response did not contain the expected binding.",
        )
    SaleCampaignApprovalService(session).bind_slack_message(
        request_id=ticket.request_id,
        campaign_id=campaign_id,
        team_id=config.team_id,
        channel_id=response_channel,
        message_ts=message_ts,
    )
    return SaleApprovalSendResult(
        request_id=ticket.request_id,
        campaign_id=campaign_id,
        expires_at=ticket.expires_at,
        team_id=config.team_id,
        channel_id=response_channel,
        message_ts=message_ts,
        payload=payload,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send one Package A sale campaign approval to Slack."
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--send", action="store_true", required=True)
    parser.add_argument("--ttl-minutes", type=int, default=1440)
    return parser.parse_args()


def main() -> int:
    import os

    from slack_sdk import WebClient

    from app.db.session import SessionLocal

    args = parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise SaleApprovalSendError(
            "invalid_snapshot", "Campaign Snapshot must be a JSON object."
        )
    config = SlackApprovalSocketConfig.from_mapping(os.environ)
    with SessionLocal() as session:
        result = send_sale_campaign_approval(
            session=session,
            client=WebClient(token=config.bot_token),
            config=config,
            snapshot=snapshot,
            requested_by="slack:package-a-step-4",
            ttl_minutes=args.ttl_minutes,
        )
    print(f"SALE_APPROVAL_REQUEST_ID={result.request_id}")
    print(f"SLACK_MESSAGE_TS={result.message_ts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
