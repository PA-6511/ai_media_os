#!/usr/bin/env python3

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


ROOT = Path(
    "/home/deploy/ai_media_os"
)


if str(ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(ROOT),
    )


from app.ebook_autonomy.x_live_canary import (  # noqa: E402
    XLiveCanaryError,
    inspect_delivery_state,
    run_live_canary,
)

from app.ebook_autonomy.x_publisher import (  # noqa: E402
    POSTED_EVIDENCE_ROOT,
    XPublisherError,
    prepare_current_xnr_post,
)


JST = ZoneInfo(
    "Asia/Tokyo"
)


def emit(
    *,
    status: str,
    code: str = "",
    x_post_id: str = "",
    x_post_url: str = "",
    evidence_path: str = "",
    delivery_state: str = "",
    x_post_executed: object = False,
) -> None:


    if x_post_executed is True:

        executed = "YES"

    elif x_post_executed is False:

        executed = "NO"

    else:

        executed = str(
            x_post_executed
        ).upper()


    print(
        "X_DAILY_STATUS="
        + status
    )

    print(
        "X_DAILY_CODE="
        + (
            code
            or status
        )
    )

    print(
        "X_DAILY_POST_ID="
        + x_post_id
    )

    print(
        "X_DAILY_POST_URL="
        + x_post_url
    )

    print(
        "X_DAILY_EVIDENCE_PATH="
        + evidence_path
    )

    print(
        "X_DAILY_DELIVERY_STATE="
        + delivery_state
    )

    print(
        "X_DAILY_POST_EXECUTED="
        + executed
    )


def _load_verified_cover_media_intent(
    wordpress_post_id: int | None,
) -> dict[str, object] | None:
    if wordpress_post_id is None:
        return None

    from sqlalchemy import select

    from app.db.models import EbookItem
    from app.db.session import SessionLocal
    from app.services.display_cover_resolver import (
        DisplayCoverResolver,
    )

    with SessionLocal() as session:
        session.connection().exec_driver_sql(
            "PRAGMA query_only=ON"
        )

        items = list(
            session.scalars(
                select(
                    EbookItem
                )
                .where(
                    EbookItem.wordpress_post_id
                    == wordpress_post_id
                )
                .limit(2)
            )
        )

        # Fail closed for attachment identity:
        # no exact item or duplicate mapping => text-only post.
        if len(items) != 1:
            return None

        item = items[0]

        cover = DisplayCoverResolver(
            session
        ).resolve(
            str(item.id)
        )

        cover_status = str(
            cover.display_cover_status
            or ""
        )

        cover_url = str(
            cover.display_cover_url
            or ""
        ).strip()

        if (
            cover_status != "AVAILABLE"
            or not cover_url.startswith(
                "https://"
            )
        ):
            return None

        return {
            "schema":
                "ebook_autonomy_verified_cover_media_v1",
            "wordpress_post_id":
                wordpress_post_id,
            "ebook_item_id":
                str(item.id),
            "cover_status":
                "AVAILABLE",
            "cover_source":
                str(
                    cover.display_cover_source
                    or ""
                ),
            "cover_url":
                cover_url,
        }


def main() -> int:


    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--wordpress-status",
        required=True,
    )

    parser.add_argument(
        "--wordpress-permalink",
        required=True,
    )

    parser.add_argument(
        "--wordpress-post-id",
        default="",
    )

    parser.add_argument(
        "--article-url-state",
        required=True,
    )

    parser.add_argument(
        "--article-url",
        required=True,
    )

    parser.add_argument(
        "--draft-path",
        required=True,
    )


    args = parser.parse_args()


    # --------------------------------------------------------
    # Outer Daily Cycle process authorization.
    # --------------------------------------------------------

    if (
        os.environ.get(
            "EBOOK_AUTONOMY_DAILY_X_ENABLED",
            "0",
        )
        != "1"
    ):

        emit(
            status="AUTOMATION_DISABLED",
            code=(
                "EBOOK_AUTONOMY_DAILY_X_ENABLED"
                "_REQUIRED"
            ),
            x_post_executed=False,
        )

        return 40


    run_id = str(
        os.environ.get(
            "EBOOK_AUTONOMY_CURRENT_RUN_ID",
            "",
        )
        or ""
    ).strip()


    if not run_id:

        run_id = datetime.now(
            JST
        ).strftime(
            "%Y%m%d_%H%M%S_%f"
        )


    try:

        wp_post_id = (
            int(
                args.wordpress_post_id
            )
            if args.wordpress_post_id
            else None
        )

    except ValueError:

        wp_post_id = None


    # --------------------------------------------------------
    # Bind CURRENT new_release result.
    #
    # Never depend on the previous Daily Cycle evidence.
    # --------------------------------------------------------

    current_context = {

        "available": True,

        "code": "PASS",

        "detail": "",

        "source_path":
            "CURRENT_DAILY_CYCLE",

        "schema":
            "ebook_autonomy_daily_cycle_v1",

        "run_id":
            run_id,

        "started_at": "",

        "finished_at": "",

        "status":
            "IN_PROGRESS",

        "new_release": {

            "status":
                "PASS",

            "wordpress_post_id":
                wp_post_id,

            "wordpress_status":
                args.wordpress_status,

            "wordpress_permalink":
                args.wordpress_permalink,

            "x_article_url_state":
                args.article_url_state,

            "x_article_url":
                args.article_url,

            "x_draft_path":
                args.draft_path,
        },

        "x_publish": {},

        "sale": {},

        "campaign": {},
    }


    os.environ[
        "EBOOK_AUTONOMY_X_CONTEXT_JSON"
    ] = json.dumps(
        current_context,
        ensure_ascii=False,
        separators=(",", ":"),
    )


    # --------------------------------------------------------
    # Unlock ONLY this child process.
    #
    # credential.env remains X_AUTOPUBLISH_ENABLED=0.
    # --------------------------------------------------------

    os.environ[
        "X_AUTOPUBLISH_ENABLED"
    ] = "1"


    # --------------------------------------------------------
    # Prepare first.
    #
    # All errors here are known PRE-SEND failures.
    # --------------------------------------------------------

    try:

        plan = (
            prepare_current_xnr_post()
        )

    except XPublisherError as exc:

        emit(
            status="PRE_SEND_BLOCKED",
            code=str(exc)[:500],
            x_post_executed=False,
        )

        return 20


    # --------------------------------------------------------
    # Deployment canary:
    # only allow already-posted payload.
    # --------------------------------------------------------

    if (
        os.environ.get(
            "EBOOK_AUTONOMY_DAILY_X_"
            "EXPECT_EXISTING_ONLY",
            "0",
        )
        == "1"
    ):

        if not plan.already_posted:

            emit(
                status=(
                    "CANARY_NEW_POST_BLOCKED"
                ),
                code=(
                    "EXPECTED_EXISTING_POST"
                ),
                x_post_executed=False,
            )

            return 42


    # --------------------------------------------------------
    # Execute guarded live publisher.
    # --------------------------------------------------------

    try:

        verified_cover_media_intent = (
            _load_verified_cover_media_intent(
                wp_post_id
            )
        )

        result = run_live_canary(
            confirm="LIVE_X_POST",
            verified_cover_media_intent=(
                verified_cover_media_intent
            ),
        )


    except XLiveCanaryError as exc:

        message = str(exc)


        if (
            "X_PRE_SEND_BLOCKED:"
            in message
        ):

            emit(
                status="PRE_SEND_BLOCKED",
                code=message[:500],
                x_post_executed=False,
            )

            return 20


        if (
            "X_DELIVERY_UNKNOWN"
            in message
            or "UNKNOWN_DELIVERY"
            in message
            or "DELIVERY_RETRY_BLOCKED:"
            in message
        ):

            emit(
                status="UNKNOWN_DELIVERY",
                code=message[:500],
                x_post_executed="UNKNOWN",
            )

            return 30


        emit(
            status="FAILED",
            code=message[:500],
            x_post_executed=False,
        )

        return 31


    except XPublisherError as exc:

        emit(
            status="PRE_SEND_BLOCKED",
            code=str(exc)[:500],
            x_post_executed=False,
        )

        return 20


    # --------------------------------------------------------
    # Normalize evidence / URL also for SKIP path.
    # --------------------------------------------------------

    status = str(
        result.get("status")
        or "UNKNOWN"
    )


    x_post_id = str(
        result.get("x_post_id")
        or plan.existing_post_id
        or ""
    ).strip()


    x_post_url = str(
        result.get("x_post_url")
        or ""
    ).strip()


    if (
        not x_post_url
        and x_post_id
    ):

        x_post_url = (
            "https://x.com/i/web/status/"
            + x_post_id
        )


    evidence_path = str(
        result.get("evidence_path")
        or ""
    ).strip()


    if not evidence_path:

        candidate = (
            POSTED_EVIDENCE_ROOT
            / (
                plan.draft_sha256
                + ".json"
            )
        )

        if candidate.is_file():

            evidence_path = str(
                candidate
            )


    delivery_state = str(
        result.get("delivery_state")
        or ""
    ).strip()


    if not delivery_state:

        try:

            state = (
                inspect_delivery_state(
                    plan
                )
            )

            delivery_state = str(
                state.get("path")
                or ""
            )

        except Exception:

            delivery_state = ""


    emit(
        status=status,
        code=status,
        x_post_id=x_post_id,
        x_post_url=x_post_url,
        evidence_path=evidence_path,
        delivery_state=delivery_state,
        x_post_executed=(
            result.get(
                "x_post_executed",
                False,
            )
        ),
    )


    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
