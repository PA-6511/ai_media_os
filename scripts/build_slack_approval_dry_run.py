from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


from app.services.slack_approval_message_service import (  # noqa: E402
    SlackApprovalMessageContext,
    SlackApprovalMessageService,
    build_slack_approval_message,
    redact_slack_approval_message,
)


_SAMPLE_TOKEN = (
    "sample-approval-token-"
    "never-use-in-production"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a redacted Slack approval "
            "Block Kit DRY_RUN document."
        )
    )

    parser.add_argument(
        "--sample",
        action="store_true",
        help="Build a synthetic sample without DB access.",
    )

    parser.add_argument(
        "--request-id",
        help="Existing pending approval request ID.",
    )

    parser.add_argument(
        "--token-env",
        default="AI_MEDIA_SLACK_APPROVAL_TOKEN",
        help=(
            "Environment variable containing the "
            "one-time approval token."
        ),
    )

    parser.add_argument(
        "--gui-url",
        help="Optional HTTPS GUI URL.",
    )

    parser.add_argument(
        "--output",
        default=(
            "/tmp/"
            "slack_approval_message_dry_run.json"
        ),
        help="DRY_RUN JSON output under /tmp.",
    )

    return parser.parse_args()


def require_tmp_output(value: str) -> Path:
    output = Path(value).expanduser().resolve()
    tmp_root = Path("/tmp").resolve()

    if output != tmp_root and tmp_root not in output.parents:
        raise ValueError(
            "DRY_RUN output must be under /tmp"
        )

    return output


def build_sample_payload(
    gui_url: str | None,
) -> tuple[str, dict]:
    context = SlackApprovalMessageContext(
        request_id=(
            "00000000-0000-0000-0000-"
            "000000000001"
        ),
        approval_type="REVIEW_READY",
        expected_current_status="REVIEW",
        requested_status="READY",
        expires_at=datetime(
            2026,
            7,
            14,
            3,
            0,
            tzinfo=timezone.utc,
        ),
        item_id=(
            "00000000-0000-0000-0000-"
            "000000000002"
        ),
        title="サンプルコミック 第1巻",
        release_date=date(2026, 7, 15),
        wordpress_status="DRAFT",
        x_status="DRAFT",
        review_status="IN_REVIEW",
        affiliate_status="READY",
        image_status="READY",
        publish_ready=True,
    )

    payload = build_slack_approval_message(
        context,
        token=_SAMPLE_TOKEN,
        gui_url=gui_url,
    )

    return context.request_id, payload


def build_database_payload(
    request_id: str,
    token_env: str,
    gui_url: str | None,
) -> tuple[str, dict]:
    token = os.environ.get(token_env, "").strip()

    if not token:
        raise ValueError(
            f"{token_env} is not set"
        )

    from app.db.session import SessionLocal

    with SessionLocal() as session:
        payload = SlackApprovalMessageService(
            session
        ).build_message(
            request_id=request_id,
            token=token,
            gui_url=gui_url,
        )

    return request_id, payload


def main() -> int:
    args = parse_args()
    output = require_tmp_output(args.output)

    if args.sample:
        request_id, payload = build_sample_payload(
            args.gui_url
        )
    else:
        request_id = (args.request_id or "").strip()

        if not request_id:
            raise ValueError(
                "--request-id is required "
                "unless --sample is used"
            )

        request_id, payload = build_database_payload(
            request_id=request_id,
            token_env=args.token_env,
            gui_url=args.gui_url,
        )

    redacted_payload = (
        redact_slack_approval_message(payload)
    )

    document = {
        "schema": (
            "SLACK_APPROVAL_MESSAGE_DRY_RUN_V1"
        ),
        "dry_run": True,
        "network_called": False,
        "request_id": request_id,
        "action_tokens_redacted": True,
        "payload": redacted_payload,
    }

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": "PASS_DRY_RUN_ONLY",
                "network_called": False,
                "request_id": request_id,
                "output": str(output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
