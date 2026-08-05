from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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

from app.services.slack_live_copy_guard import (  # noqa: E402
    SlackLiveCopyGuardError,
    validate_slack_live_copy_environment,
)


REPO_ROOT = Path(
    "/home/deploy/ai_media_os"
)

PRODUCTION_DATABASE_PATH = (
    REPO_ROOT
    / "data/database/ebook_affiliate.db"
)

COPY_DATABASE_PATH = Path(
    "/tmp/ebook_affiliate_slack_5f.db"
)

EXPECTED_DATABASE_URL = (
    "sqlite:////tmp/ebook_affiliate_slack_5f.db"
)

SEND_CONFIRM_NAME = (
    "SLACK_5F_SEND_CONFIRM"
)

SEND_CONFIRM_VALUE = (
    "SEND_ONE_SLACK_LIVE_COPY_MESSAGE"
)

SOURCE_NAME = (
    "slack_5f_live_copy_integration"
)

RECEIPT_PATH = Path(
    "/tmp/slack_approval_5f_receipt.json"
)


class Slack5FIntegrationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_environment(
    *,
    require_send_confirmation: bool,
):
    return validate_slack_live_copy_environment(
        os.environ,
        expected_database_url=(
            EXPECTED_DATABASE_URL
        ),
        expected_database_path=(
            COPY_DATABASE_PATH
        ),
        production_database_path=(
            PRODUCTION_DATABASE_PATH
        ),
        require_send_confirmation=(
            require_send_confirmation
        ),
        send_confirmation_name=(
            SEND_CONFIRM_NAME
        ),
        send_confirmation_value=(
            SEND_CONFIRM_VALUE
        ),
    )


def write_receipt(
    *,
    item_id: str,
    request_id: str,
    team_id: str,
    channel_id: str,
    message_ts: str,
    production_sha256_before: str,
) -> None:
    receipt: dict[str, Any] = {
        "phase": "SQL-B2-4B-5F",
        "mode": "LIVE_COPY_ONLY",
        "database_url": EXPECTED_DATABASE_URL,
        "item_id": item_id,
        "request_id": request_id,
        "team_id": team_id,
        "channel_id": channel_id,
        "message_ts": message_ts,
        "production_sha256_before": (
            production_sha256_before
        ),
        "raw_approval_token_stored": False,
        "sent_at": datetime.now(
            timezone.utc
        ).isoformat(),
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


def check_config() -> int:
    validate_environment(
        require_send_confirmation=False
    )

    print("SLACK_5F_CONFIG: PASS")
    print("DATABASE_TARGET: COPY_ONLY")
    print("MODE: LIVE")
    print("PRODUCTION_DATABASE_ALLOWED: FALSE")
    print("NETWORK_MESSAGE_SENT: FALSE")

    return 0


def send_one() -> int:
    config = validate_environment(
        require_send_confirmation=True
    )

    # ガード通過後にDB関連モジュールを読み込む。
    from sqlalchemy import func, select

    from app.db.models import EbookItem
    from app.db.session import SessionLocal
    from app.services.slack_approval_message_service import (
        SlackApprovalMessageService,
    )
    from app.services.workflow_approval_service import (
        WorkflowApprovalService,
    )

    production_sha256_before = sha256_file(
        PRODUCTION_DATABASE_PATH
    )

    client = WebClient(
        token=config.bot_token
    )

    try:
        auth = client.auth_test()
    except SlackApiError as exc:
        error = exc.response.get(
            "error",
            "unknown_error",
        )

        raise Slack5FIntegrationError(
            f"BOT_AUTH_FAILED: {error}"
        ) from exc

    actual_team_id = str(
        auth.get("team_id") or ""
    )

    if actual_team_id != config.team_id:
        raise Slack5FIntegrationError(
            "BOT_WORKSPACE_MISMATCH"
        )

    posted_message_ts = ""
    item_id = ""
    request_id = ""

    with SessionLocal() as session:
        existing_count = session.scalar(
            select(func.count())
            .select_from(EbookItem)
            .where(
                EbookItem.source_name
                == SOURCE_NAME
            )
        )

        if int(existing_count or 0) != 0:
            raise Slack5FIntegrationError(
                "5F integration item already exists; "
                "recreate the copy database"
            )

        item = EbookItem(
            source_name=SOURCE_NAME,
            source_item_id=(
                "SLACK-5F-"
                + uuid4().hex[:16].upper()
            ),
            title=(
                "【LIVEコピーDB試験】"
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

        item_id = item.id

        ticket = WorkflowApprovalService(
            session
        ).create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by=(
                "integration:sql-b2-4b-5f"
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
                channel=config.channel_id,
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
                raise Slack5FIntegrationError(
                    "Slack response did not "
                    "contain message timestamp"
                )

            message_service.register_sent_message(
                request_id=ticket.request_id,
                team_id=config.team_id,
                channel_id=config.channel_id,
                message_ts=posted_message_ts,
            )

            session.commit()

        except Exception:
            session.rollback()

            if posted_message_ts:
                try:
                    client.chat_delete(
                        channel=config.channel_id,
                        ts=posted_message_ts,
                    )
                except Exception:
                    pass

            raise

    write_receipt(
        item_id=item_id,
        request_id=request_id,
        team_id=config.team_id,
        channel_id=config.channel_id,
        message_ts=posted_message_ts,
        production_sha256_before=(
            production_sha256_before
        ),
    )

    print("SLACK_5F_MESSAGE_SENT: PASS")
    print("DATABASE_TARGET: COPY_ONLY")
    print("MODE: LIVE")
    print("PRODUCTION_DATABASE_ALLOWED: FALSE")
    print("RAW_TOKEN_OUTPUT: FALSE")
    print(f"REQUEST_ID: {request_id}")
    print(f"MESSAGE_TS: {posted_message_ts}")
    print(f"RECEIPT: {RECEIPT_PATH}")

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

        return send_one()

    except (
        SlackLiveCopyGuardError,
        Slack5FIntegrationError,
    ) as exc:
        print(
            f"SLACK_5F: FAIL ({exc})",
            file=sys.stderr,
        )
        return 2

    except SlackApiError as exc:
        error = exc.response.get(
            "error",
            "unknown_error",
        )

        print(
            f"SLACK_5F_API: FAIL ({error})",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
