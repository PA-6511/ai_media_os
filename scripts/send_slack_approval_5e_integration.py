from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


from slack_sdk import WebClient  # noqa: E402
from slack_sdk.errors import SlackApiError  # noqa: E402

from app.db.models import EbookItem  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.slack_approval_message_service import (  # noqa: E402
    SlackApprovalMessageService,
)
from app.services.workflow_approval_service import (  # noqa: E402
    WorkflowApprovalService,
)


EXPECTED_DATABASE_URL = (
    "sqlite:////tmp/ebook_affiliate_slack_5e.db"
)

SEND_CONFIRM_VALUE = (
    "SEND_ONE_SLACK_DRY_RUN_MESSAGE"
)

RECEIPT_PATH = Path(
    "/tmp/slack_approval_5e_receipt.json"
)


class IntegrationGuardError(RuntimeError):
    pass


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise IntegrationGuardError(
            f"{name}: MISSING"
        )

    return value


def validate_environment(
    *,
    require_send_confirmation: bool,
) -> dict[str, str]:
    database_backend = required_env(
        "DATABASE_BACKEND"
    )

    database_url = required_env(
        "DATABASE_URL"
    )

    bot_token = required_env(
        "SLACK_BOT_TOKEN"
    )

    team_id = required_env(
        "SLACK_APPROVAL_TEAM_ID"
    )

    channel_id = required_env(
        "SLACK_APPROVAL_CHANNEL_ID"
    )

    mode = required_env(
        "SLACK_APPROVAL_MODE"
    )

    if database_backend != "sqlite":
        raise IntegrationGuardError(
            "DATABASE_BACKEND must be sqlite"
        )

    if database_url != EXPECTED_DATABASE_URL:
        raise IntegrationGuardError(
            "DATABASE_URL must point exactly to "
            "/tmp/ebook_affiliate_slack_5e.db"
        )

    database_path = Path(
        "/tmp/ebook_affiliate_slack_5e.db"
    )

    if not database_path.is_file():
        raise IntegrationGuardError(
            "5E copy database does not exist"
        )

    if mode != "DRY_RUN":
        raise IntegrationGuardError(
            "SLACK_APPROVAL_MODE must remain DRY_RUN"
        )

    if not bot_token.startswith("xoxb-"):
        raise IntegrationGuardError(
            "SLACK_BOT_TOKEN has an invalid prefix"
        )

    if not team_id.startswith("T"):
        raise IntegrationGuardError(
            "SLACK_APPROVAL_TEAM_ID is invalid"
        )

    if not channel_id.startswith("C"):
        raise IntegrationGuardError(
            "SLACK_APPROVAL_CHANNEL_ID is invalid"
        )

    if require_send_confirmation:
        confirmation = os.environ.get(
            "SLACK_5E_SEND_CONFIRM",
            "",
        ).strip()

        if confirmation != SEND_CONFIRM_VALUE:
            raise IntegrationGuardError(
                "Explicit 5E send confirmation "
                "is missing"
            )

    return {
        "bot_token": bot_token,
        "team_id": team_id,
        "channel_id": channel_id,
        "database_url": database_url,
    }


def write_receipt(
    *,
    item_id: str,
    request_id: str,
    team_id: str,
    channel_id: str,
    message_ts: str,
) -> None:
    receipt: dict[str, Any] = {
        "phase": "SQL-B2-4B-5E",
        "mode": "DRY_RUN",
        "database_url": EXPECTED_DATABASE_URL,
        "item_id": item_id,
        "request_id": request_id,
        "team_id": team_id,
        "channel_id": channel_id,
        "message_ts": message_ts,
        "sent_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "raw_approval_token_stored": False,
    }

    RECEIPT_PATH.write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    RECEIPT_PATH.chmod(0o600)


def send_message() -> int:
    config = validate_environment(
        require_send_confirmation=True
    )

    client = WebClient(
        token=config["bot_token"]
    )

    try:
        auth = client.auth_test()
    except SlackApiError as exc:
        error = exc.response.get(
            "error",
            "unknown_error",
        )
        raise IntegrationGuardError(
            f"BOT_AUTH_FAILED: {error}"
        ) from exc

    actual_team_id = str(
        auth.get("team_id") or ""
    )

    if actual_team_id != config["team_id"]:
        raise IntegrationGuardError(
            "BOT_WORKSPACE_MISMATCH"
        )

    posted_message_ts = ""
    test_item_id = ""
    request_id = ""

    with SessionLocal() as session:
        source_item_id = (
            "SLACK-5E-"
            + uuid4().hex[:16].upper()
        )

        item = EbookItem(
            source_name=(
                "slack_5e_dry_run_integration"
            ),
            source_item_id=source_item_id,
            title=(
                "【DRY_RUN統合試験】"
                "電子書籍承認Bot"
            ),
            item_type="tankobon",
            workflow_status="REVIEW",
            wordpress_status="DRAFT",
            x_status="DRAFT",
            affiliate_status="READY",
            image_status="READY",
            publish_ready=True,
        )

        session.add(item)
        session.commit()
        session.refresh(item)

        test_item_id = item.id

        ticket = WorkflowApprovalService(
            session
        ).create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by=(
                "integration:sql-b2-4b-5e"
            ),
            ttl_minutes=60,
        )

        request_id = ticket.request_id

        message_service = (
            SlackApprovalMessageService(session)
        )

        payload = message_service.build_message(
            request_id=ticket.request_id,
            token=ticket.token,
            gui_url=None,
        )

        try:
            response = client.chat_postMessage(
                channel=config["channel_id"],
                text=payload["text"],
                blocks=payload["blocks"],
                unfurl_links=bool(
                    payload.get(
                        "unfurl_links",
                        False,
                    )
                ),
                unfurl_media=bool(
                    payload.get(
                        "unfurl_media",
                        False,
                    )
                ),
            )

            posted_message_ts = str(
                response.get("ts") or ""
            )

            if not posted_message_ts:
                raise IntegrationGuardError(
                    "Slack response did not "
                    "contain message timestamp"
                )

            message_service.register_sent_message(
                request_id=ticket.request_id,
                team_id=config["team_id"],
                channel_id=config["channel_id"],
                message_ts=posted_message_ts,
            )

            session.commit()

        except Exception:
            session.rollback()

            if posted_message_ts:
                try:
                    client.chat_delete(
                        channel=config[
                            "channel_id"
                        ],
                        ts=posted_message_ts,
                    )
                except Exception:
                    pass

            raise

    write_receipt(
        item_id=test_item_id,
        request_id=request_id,
        team_id=config["team_id"],
        channel_id=config["channel_id"],
        message_ts=posted_message_ts,
    )

    print("SLACK_5E_MESSAGE_SENT: PASS")
    print("MODE: DRY_RUN")
    print("COPY_DATABASE_ONLY: PASS")
    print("RAW_TOKEN_OUTPUT: FALSE")
    print(
        f"REQUEST_ID: {request_id}"
    )
    print(
        f"MESSAGE_TS: {posted_message_ts}"
    )
    print(
        f"RECEIPT: {RECEIPT_PATH}"
    )

    return 0


def check_config() -> int:
    validate_environment(
        require_send_confirmation=False
    )

    print("SLACK_5E_CONFIG: PASS")
    print("MODE: DRY_RUN")
    print("DATABASE: COPY_ONLY")
    print("NETWORK_MESSAGE_SENT: FALSE")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--check-config",
        action="store_true",
    )

    group.add_argument(
        "--send-one",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.check_config:
            return check_config()

        return send_message()

    except IntegrationGuardError as exc:
        print(
            f"SLACK_5E: FAIL ({exc})",
            file=sys.stderr,
        )
        return 2

    except SlackApiError as exc:
        error = exc.response.get(
            "error",
            "unknown_error",
        )
        print(
            f"SLACK_5E_API: FAIL ({error})",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
