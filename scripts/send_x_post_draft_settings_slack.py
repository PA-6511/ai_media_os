from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


if __package__ in {None, ""}:
    repo_root = Path(
        __file__
    ).resolve().parents[1]
    sys.path.insert(
        0,
        str(repo_root),
    )


from app.db.models.x_post_draft import (  # noqa: E402
    XPostDraft,
)
from app.db.session import SessionLocal  # noqa: E402
from app.services.slack_approval_socket_service import (  # noqa: E402
    SlackApprovalSocketConfig,
)
from app.services.x_post_draft_slack_preset_service import (  # noqa: E402
    build_x_post_draft_settings_message,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Send an X post draft settings card "
            "to the existing Slack approval channel."
        )
    )

    parser.add_argument(
        "--draft-id",
        required=True,
    )

    mode = parser.add_mutually_exclusive_group(
        required=True
    )

    mode.add_argument(
        "--dry-run",
        action="store_true",
    )

    mode.add_argument(
        "--send",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config = (
        SlackApprovalSocketConfig.from_mapping(
            os.environ
        )
    )

    with SessionLocal() as session:
        draft = session.get(
            XPostDraft,
            args.draft_id,
        )

        if draft is None:
            print(
                "X_POST_DRAFT_NOT_FOUND",
                file=sys.stderr,
            )
            return 2

        payload = (
            build_x_post_draft_settings_message(
                draft
            )
        )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "channel": config.channel_id,
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print(
            "SLACK_WRITE=NO"
        )
        return 0

    try:
        from slack_sdk import WebClient
    except ImportError:
        print(
            "SLACK_SDK_NOT_AVAILABLE",
            file=sys.stderr,
        )
        return 3

    client = WebClient(
        token=config.bot_token,
    )

    response = client.chat_postMessage(
        channel=config.channel_id,
        text=payload["text"],
        blocks=payload["blocks"],
        unfurl_links=False,
        unfurl_media=False,
    )

    print(
        "SLACK_X_DRAFT_SETTINGS_SENT=YES"
    )
    print(
        "CHANNEL_ID=",
        config.channel_id,
    )
    print(
        "MESSAGE_TS=",
        response.get("ts"),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
