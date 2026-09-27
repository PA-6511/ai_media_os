#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.slack_periodic_report_service import (  # noqa: E402
    build_periodic_report_slack_payload,
)
from core.core_ai.module import Module  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Core advisoryから週次/月次Slackレポートpayloadを生成する"
        )
    )
    parser.add_argument(
        "report_type",
        choices=("weekly", "monthly"),
    )
    mode = parser.add_mutually_exclusive_group(
        required=True
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Slackへ送信せずpayloadだけ出力する",
    )
    mode.add_argument(
        "--send",
        action="store_true",
        help="Slackへ1回送信する",
    )

    args = parser.parse_args(argv)

    result = Module().evaluate_x_analytics_advisory(
        report_type=args.report_type
    )

    payload = build_periodic_report_slack_payload(
        report_type=args.report_type,
        core_result=result,
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "report_type": args.report_type,
                    "dry_run": True,
                    "text": payload.text,
                    "blocks": payload.blocks,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    token = str(
        os.environ.get(
            "SLACK_BOT_TOKEN",
            "",
        )
    ).strip()

    channel_id = str(
        os.environ.get(
            "SLACK_APPROVAL_CHANNEL_ID",
            "",
        )
    ).strip()

    if not token.startswith("xoxb-"):
        print(
            "SLACK_CONFIG_ERROR=INVALID_BOT_TOKEN",
            file=sys.stderr,
        )
        return 2

    if not channel_id.startswith("C"):
        print(
            "SLACK_CONFIG_ERROR=INVALID_CHANNEL_ID",
            file=sys.stderr,
        )
        return 3

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except Exception:
        print(
            "SLACK_CONFIG_ERROR=SLACK_SDK_UNAVAILABLE",
            file=sys.stderr,
        )
        return 4

    client = WebClient(
        token=token
    )

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=payload.text,
            blocks=payload.blocks,
        )
    except SlackApiError as exc:
        error = "unknown"

        if getattr(
            exc,
            "response",
            None,
        ) is not None:
            try:
                error = str(
                    exc.response.get(
                        "error",
                        "unknown",
                    )
                )
            except Exception:
                pass

        print(
            "SLACK_SEND_ERROR="
            + error,
            file=sys.stderr,
        )
        return 5

    response_channel = str(
        response.get(
            "channel",
            "",
        )
    )
    message_ts = str(
        response.get(
            "ts",
            "",
        )
    )

    if (
        response_channel != channel_id
        or not message_ts
    ):
        print(
            "SLACK_SEND_ERROR=RESPONSE_BINDING_MISMATCH",
            file=sys.stderr,
        )
        return 6

    print(
        json.dumps(
            {
                "report_type": args.report_type,
                "sent": True,
                "channel_id": response_channel,
                "message_ts": message_ts,
                "text": payload.text,
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
