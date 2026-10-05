#!/usr/bin/env python3

from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path
import sys
import types
import typing


if __package__ in {
    None,
    "",
}:
    ROOT = (
        Path(__file__)
        .resolve()
        .parents[1]
    )

    sys.path.insert(
        0,
        str(ROOT),
    )


from sqlalchemy import select

from app.db.models.sale_campaign_approval import (
    SaleCampaignApprovalRequest,
)
from app.db.session import SessionLocal
from app.services.dmm_sale_approval_snapshot_service import (
    build_dmm_sale_approval_snapshot,
)
from app.services.dmm_sale_autonomy_service import (
    stage_dmm_campaign,
)
from app.services.dmm_sale_campaign_collector import (
    DmmSaleCampaignCollector,
)
from app.services.dmm_sale_campaign_discovery_service import (
    DmmSaleCampaignDiscoveryService,
)
import app.services.dmm_sale_candidate_service as candidate_module
from app.services.dmm_sale_candidate_service import (
    DmmSaleCandidateService,
)
from app.services.slack_approval_socket_service import (
    SlackApprovalSocketConfig,
)


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run bounded DMM sale automation "
            "through Slack approval request."
        )
    )

    source = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    source.add_argument(
        "--campaign-url",
        action="append",
        dest="campaign_urls",
    )

    source.add_argument(
        "--discover",
        action="store_true",
    )

    parser.add_argument(
        "--seed-products",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--max-campaigns",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--threshold-percent",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--max-products",
        type=int,
        default=5,
    )

    mode = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    mode.add_argument(
        "--dry-run",
        action="store_true",
    )

    mode.add_argument(
        "--execute",
        action="store_true",
    )

    parser.add_argument(
        "--ttl-minutes",
        type=int,
        default=1440,
    )

    return parser


def _unwrap_type(
    value,
):
    origin = typing.get_origin(
        value
    )

    if origin in (
        typing.Union,
        types.UnionType,
    ):
        args = [
            item
            for item
            in typing.get_args(
                value
            )
            if item
            is not type(None)
        ]

        if len(args) == 1:
            return args[0]

    return value


def _construct(
    cls,
    *,
    depth=0,
):
    if depth > 6:
        raise RuntimeError(
            "DMM_SERVICE_CONSTRUCTOR_DEPTH"
        )

    signature = inspect.signature(
        cls
    )

    hints = {}

    try:
        hints = typing.get_type_hints(
            cls.__init__
        )
    except Exception:
        hints = {}

    kwargs = {}

    for parameter in (
        signature.parameters.values()
    ):
        if parameter.name == "self":
            continue

        if (
            parameter.kind
            in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }
        ):
            continue

        if (
            parameter.default
            is not inspect.Parameter.empty
        ):
            continue

        if (
            parameter.name
            == "collector"
        ):
            kwargs[
                parameter.name
            ] = _construct(
                DmmSaleCampaignCollector,
                depth=depth + 1,
            )

            continue

        hinted = _unwrap_type(
            hints.get(
                parameter.name
            )
        )

        if inspect.isclass(
            hinted
        ):
            kwargs[
                parameter.name
            ] = _construct(
                hinted,
                depth=depth + 1,
            )

            continue

        tokens = {
            token
            for token in (
                parameter.name
                .casefold()
                .replace(
                    "_service",
                    "",
                )
                .split("_")
            )
            if token
        }

        choices = []

        for name, value in vars(
            candidate_module
        ).items():
            if (
                not inspect.isclass(
                    value
                )
                or value
                is DmmSaleCandidateService
            ):
                continue

            if not str(
                getattr(
                    value,
                    "__module__",
                    "",
                )
            ).startswith(
                "app.services."
            ):
                continue

            lowered = (
                name.casefold()
            )

            score = sum(
                1
                for token
                in tokens
                if token in lowered
            )

            if score:
                choices.append(
                    (
                        score,
                        name,
                        value,
                    )
                )

        if choices:
            choices.sort(
                reverse=True,
                key=lambda row: (
                    row[0],
                    row[1],
                ),
            )

            kwargs[
                parameter.name
            ] = _construct(
                choices[0][2],
                depth=depth + 1,
            )

            continue

        raise RuntimeError(
            "UNSUPPORTED_REQUIRED_CONSTRUCTOR_ARG:"
            + cls.__name__
            + "."
            + parameter.name
        )

    return cls(
        **kwargs
    )


def _build_candidate_service():
    return _construct(
        DmmSaleCandidateService
    )


def _approval_state(
    session,
    campaign_id: str,
):
    rows = list(
        session.scalars(
            select(
                SaleCampaignApprovalRequest
            )
            .where(
                SaleCampaignApprovalRequest
                .campaign_id
                == campaign_id
            )
            .order_by(
                SaleCampaignApprovalRequest
                .requested_at
                .desc()
            )
        )
    )

    if not rows:
        return (
            "NONE",
            None,
        )

    # DMM1P_UNBOUND_PENDING_GATE_V1
    latest = rows[0]

    if latest.status == "PENDING":
        bound = all(
            str(
                value
                or ""
            ).strip()
            for value in (
                latest.slack_team_id,
                latest.slack_channel_id,
                latest.slack_message_ts,
            )
        )

        if not bound:
            return (
                "PENDING_UNBOUND",
                latest,
            )

    return (
        latest.status,
        latest,
    )


def _send_approval(
    *,
    session,
    snapshot,
    ttl_minutes,
):
    from slack_sdk import WebClient

    from scripts.send_amazon_sale_package_a_approval import (
        send_sale_campaign_approval,
    )

    config = (
        SlackApprovalSocketConfig
        .from_mapping(
            os.environ
        )
    )

    return send_sale_campaign_approval(
        session=session,
        client=WebClient(
            token=config.bot_token
        ),
        config=config,
        snapshot=snapshot,
        requested_by=(
            "slack:dmm-sale-autonomy"
        ),
        ttl_minutes=ttl_minutes,
    )


def _resolve_campaign_urls(
    args,
) -> tuple[str, ...]:
    if not args.discover:
        return tuple(
            args.campaign_urls
            or ()
        )

    with SessionLocal() as session:
        result = (
            DmmSaleCampaignDiscoveryService()
            .discover(
                session,
                max_seed_products=(
                    args.seed_products
                ),
                max_campaigns=(
                    args.max_campaigns
                ),
            )
        )

        session.rollback()

    print(
        "DISCOVERY_SEED_PRODUCT_COUNT="
        + str(
            result.seed_product_count
        )
    )

    print(
        "DISCOVERY_FETCHED_PRODUCT_COUNT="
        + str(
            result.fetched_product_count
        )
    )

    print(
        "DISCOVERY_FAILED_PRODUCT_COUNT="
        + str(
            result.failed_product_count
        )
    )

    print(
        "DISCOVERED_CAMPAIGN_COUNT="
        + str(
            result.discovered_campaign_count
        )
    )

    for url in (
        result.campaign_urls
    ):
        print(
            "DISCOVERED_CAMPAIGN_URL="
            + url
        )

    return (
        result.campaign_urls
    )


def main():
    args = _parser().parse_args()

    candidate_service = (
        _build_candidate_service()
    )

    print(
        "DMM_CANDIDATE_SERVICE="
        + type(
            candidate_service
        ).__name__
    )

    campaign_urls = (
        _resolve_campaign_urls(
            args
        )
    )

    if not campaign_urls:
        print(
            "DMM_AUTONOMY_RESULT="
            "NO_CAMPAIGNS_DISCOVERED"
        )

        print(
            "DMM_AUTONOMY_SENT_COUNT=0"
        )

        print(
            "DMM_AUTONOMY_SKIPPED_COUNT=0"
        )

        print(
            "DMM_AUTONOMY_FAILED_COUNT=0"
        )

        print(
            "DMM_AUTONOMY_GATE=PASS"
        )

        return 0

    failures = 0
    sent = 0
    skipped = 0

    for campaign_url in (
        campaign_urls
    ):
        print()
        print(
            "DMM_CAMPAIGN_URL="
            + campaign_url
        )

        with SessionLocal() as session:
            try:
                result = (
                    stage_dmm_campaign(
                        session,
                        candidate_service=(
                            candidate_service
                        ),
                        campaign_url=(
                            campaign_url
                        ),
                        threshold_percent=(
                            args.threshold_percent
                        ),
                        max_products=(
                            args.max_products
                        ),
                    )
                )

                print(
                    "CAMPAIGN_ID="
                    + str(
                        result.campaign_id
                    )
                )

                print(
                    "CANDIDATE_COUNT="
                    + str(
                        result.candidate_count
                    )
                )

                print(
                    "SALE_CREATED_COUNT="
                    + str(
                        result.sale_created_count
                    )
                )

                print(
                    "SALE_REUSED_COUNT="
                    + str(
                        result.sale_reused_count
                    )
                )

                print(
                    "AFFILIATE_UPDATED_COUNT="
                    + str(
                        result.affiliate_updated_count
                    )
                )

                print(
                    "AFFILIATE_REUSED_COUNT="
                    + str(
                        result.affiliate_reused_count
                    )
                )

                if not result.campaign_id:
                    session.rollback()

                    print(
                        "DMM_CAMPAIGN_RESULT="
                        "NO_CANDIDATES"
                    )

                    skipped += 1
                    continue

                if args.dry_run:
                    session.rollback()

                    print(
                        "DMM_CAMPAIGN_RESULT="
                        "DRY_RUN_ROLLBACK"
                    )

                    continue

                session.commit()

                state, request = (
                    _approval_state(
                        session,
                        result.campaign_id,
                    )
                )

                print(
                    "APPROVAL_STATE="
                    + state
                )

                if state == "PENDING_UNBOUND":
                    raise RuntimeError(
                        "UNBOUND_PENDING_APPROVAL"
                    )

                if state in {
                    "PENDING",
                    "APPROVED",
                    "ON_HOLD",
                    "REJECTED",
                }:
                    print(
                        "SLACK_APPROVAL="
                        "SKIPPED_EXISTING_"
                        + state
                    )

                    skipped += 1
                    continue

                snapshot = (
                    build_dmm_sale_approval_snapshot(
                        session,
                        campaign_id=(
                            result.campaign_id
                        ),
                    )
                )

                send_result = (
                    _send_approval(
                        session=session,
                        snapshot=snapshot,
                        ttl_minutes=(
                            args.ttl_minutes
                        ),
                    )
                )

                print(
                    "SALE_APPROVAL_REQUEST_ID="
                    + send_result.request_id
                )

                print(
                    "SLACK_MESSAGE_TS="
                    + send_result.message_ts
                )

                print(
                    "DMM_CAMPAIGN_RESULT="
                    "SLACK_APPROVAL_SENT"
                )

                sent += 1

            except Exception as exc:
                session.rollback()

                failures += 1

                print(
                    "DMM_CAMPAIGN_RESULT=ERROR"
                )

                print(
                    "ERROR_TYPE="
                    + type(
                        exc
                    ).__name__
                )

                print(
                    "ERROR="
                    + str(
                        exc
                    )
                )

    print()
    print(
        "DMM_AUTONOMY_SENT_COUNT="
        + str(
            sent
        )
    )

    print(
        "DMM_AUTONOMY_SKIPPED_COUNT="
        + str(
            skipped
        )
    )

    print(
        "DMM_AUTONOMY_FAILED_COUNT="
        + str(
            failures
        )
    )

    if failures:
        return 1

    print(
        "DMM_AUTONOMY_GATE=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
