"""Fetch outside write transactions; apply only to unchanged, permitted items."""

import collections
import fcntl
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import select, text

from app.db.models import (
    EbookItem,
    ImageRightsEvidence,
    StoreCoverPolicyAgreement,
)
from app.db.session import SessionLocal
from app.integrations.amazon_creators_api_client import (
    AmazonCreatorsApiClient,
)
from app.services.amazon_creators_cover_persistence_service import (
    AmazonCreatorsCoverPersistenceService,
)
from app.services.display_cover_resolver import (
    DisplayCoverResolver,
)
from app.services.official_cover_automation_service import (
    RAKUTEN_KOBO_COVER_POLICY_VERSION,
)
from app.services.verified_cover_lookup import (
    configured_cover_request,
    verified_kobo_item,
)


def https(value):
    try:
        parsed = urlsplit(
            str(value or "")
        )
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


def snapshot(item):
    return (
        [
            getattr(
                item,
                column.name,
            )
            for column in item.__table__.columns
        ],
        sorted(
            (
                offer.id,
                tuple(
                    getattr(
                        offer,
                        column.name,
                    )
                    for column
                    in offer.__table__.columns
                ),
            )
            for offer in item.offers
        ),
    )


def _finish_job(
    session,
    *,
    item_id,
    revision,
    attempts,
    done,
    reason,
):
    delay = min(
        86400,
        60 * 2 ** min(
            attempts,
            10,
        ),
    )

    session.execute(
        text(
            """
            UPDATE cover_registration_jobs
            SET
                attempts=attempts+1,
                status=:status,
                reason=:reason,
                next_attempt_at=:next,
                updated_at=:now
            WHERE ebook_item_id=:id
              AND revision=:revision
            """
        ),
        {
            "status": (
                "RESOLVED"
                if done
                else "PENDING"
            ),
            "reason": reason,
            "next": (
                int(time.time())
                + delay
            ),
            "now": int(
                time.time()
            ),
            "id": item_id,
            "revision": revision,
        },
    )


def _amazon_failure_reason(
    result,
):
    token = str(
        getattr(
            result,
            "reason_code",
            "",
        )
        or getattr(
            result,
            "status",
            "",
        )
        or "UNAVAILABLE"
    ).strip()

    if token.startswith(
        "AMAZON_"
    ):
        return token[:160]

    return (
        "AMAZON_"
        + token
    )[:160]


def _run_amazon_fallback(
    item_id,
):
    client = (
        AmazonCreatorsApiClient
        .from_environment(
            minimum_request_interval_seconds=1.1,
        )
    )

    try:
        with SessionLocal() as session:
            return (
                AmazonCreatorsCoverPersistenceService(
                    session,
                    client,
                ).persist_item(
                    item_id,
                    execute=True,
                )
            )
    finally:
        client.close()


def run(limit=20):
    counts = collections.Counter()

    with SessionLocal() as session:
        jobs = list(
            session.execute(
                text(
                    """
                    SELECT
                        ebook_item_id,
                        revision,
                        attempts
                    FROM cover_registration_jobs
                    WHERE status='PENDING'
                      AND next_attempt_at<=:now
                    ORDER BY
                        next_attempt_at,
                        updated_at
                    LIMIT :limit
                    """
                ),
                {
                    "now": int(
                        time.time()
                    ),
                    "limit": limit,
                },
            )
        )

    for (
        item_id,
        revision,
        attempts,
    ) in jobs:
        api = None
        reason = ""
        done = False
        network_attempted = False
        amazon_offer_count = 0
        kobo_offer = None

        with SessionLocal() as session:
            item = session.get(
                EbookItem,
                item_id,
            )

            if item is None:
                continue

            before = snapshot(
                item
            )

            if (
                DisplayCoverResolver(
                    session
                )
                .resolve(
                    item_id
                )
                .display_cover_status
                == "AVAILABLE"
            ):
                reason = (
                    "EXISTING_OFFICIAL_REUSED"
                )
                done = True

            elif (
                item.cover_source
                == "MANUAL"
                and item.cover_status
                == "AUTO_ALLOWED"
            ):
                reason = (
                    "MANUAL_COVER_PRESERVED"
                )

            else:
                kobo_offers = [
                    offer
                    for offer in item.offers
                    if offer.store_name
                    == "rakuten_kobo"
                ]

                amazon_offers = [
                    offer
                    for offer in item.offers
                    if offer.store_name
                    == "amazon"
                ]

                amazon_offer_count = len(
                    amazon_offers
                )

                policy = session.get(
                    StoreCoverPolicyAgreement,
                    "rakuten_kobo",
                )

                if len(
                    kobo_offers
                ) != 1:
                    reason = (
                        "KOBO_OFFER_UNAVAILABLE;"
                        "DMM_API_NOT_CONFIGURED;"
                        "AMAZON_IMAGE_PERMISSION_"
                        "NOT_VERIFIED"
                    )

                elif (
                    not policy
                    or not policy.agreed
                    or policy.policy_version
                    != RAKUTEN_KOBO_COVER_POLICY_VERSION
                ):
                    reason = (
                        "POLICY_NOT_AGREED"
                    )

                else:
                    kobo_offer = (
                        kobo_offers[0]
                    )

                    session.expunge_all()
                    session.rollback()

                    network_attempted = True

                    try:
                        api = (
                            verified_kobo_item(
                                item,
                                kobo_offer,
                                configuration_loader=(
                                    configured_cover_request
                                ),
                            )
                        )
                    except Exception as exc:
                        reason = str(
                            getattr(
                                exc,
                                "code",
                                type(
                                    exc
                                ).__name__,
                            )
                        )[:160]

        need_amazon = False

        with SessionLocal() as session:
            session.execute(
                text(
                    "BEGIN IMMEDIATE"
                )
            )

            current_revision = (
                session.execute(
                    text(
                        """
                        SELECT revision
                        FROM cover_registration_jobs
                        WHERE ebook_item_id=:id
                        """
                    ),
                    {
                        "id": item_id,
                    },
                ).scalar()
            )

            item = session.get(
                EbookItem,
                item_id,
            )

            if (
                current_revision
                != revision
                or item is None
                or snapshot(
                    item
                )
                != before
            ):
                session.rollback()
                counts[
                    "CONCURRENT_CHANGE"
                ] += 1

                if network_attempted:
                    time.sleep(
                        1.1
                    )

                continue

            if api:
                policy = session.get(
                    StoreCoverPolicyAgreement,
                    "rakuten_kobo",
                )

                rights = session.scalar(
                    select(
                        ImageRightsEvidence
                    )
                    .where(
                        ImageRightsEvidence
                        .candidate_id
                        == item_id
                    )
                    .order_by(
                        ImageRightsEvidence
                        .verified_at.desc(),
                        ImageRightsEvidence
                        .created_at.desc(),
                        ImageRightsEvidence
                        .id.desc(),
                    )
                    .limit(1)
                )

                if (
                    not policy
                    or not policy.agreed
                    or policy.policy_version
                    != RAKUTEN_KOBO_COVER_POLICY_VERSION
                ):
                    reason = (
                        "POLICY_NOT_AGREED"
                    )

                elif (
                    rights
                    and rights.rights_status
                    in (
                        "VERIFIED_NOT_ALLOWED",
                        "UNRESOLVED",
                    )
                ):
                    reason = (
                        "RIGHTS_NOT_ALLOWED"
                    )

                elif (
                    not https(
                        api.get(
                            "affiliateUrl"
                        )
                    )
                    or (
                        kobo_offer.affiliate_url
                        and not https(
                            kobo_offer.affiliate_url
                        )
                    )
                ):
                    reason = (
                        "AFFILIATE_URL_"
                        "MISSING_OR_INVALID"
                    )

                else:
                    item.cover_source = (
                        "RAKUTEN_KOBO_API"
                    )
                    item.cover_source_item_id = (
                        kobo_offer.store_item_id
                    )
                    item.cover_image_url = (
                        api[
                            "largeImageUrl"
                        ]
                    )
                    item.cover_destination_url = (
                        kobo_offer.affiliate_url
                        or api[
                            "affiliateUrl"
                        ]
                    )
                    item.cover_retrieved_at = (
                        datetime.now(
                            timezone.utc
                        )
                    )
                    item.cover_policy_version = (
                        policy.policy_version
                    )
                    item.cover_status = (
                        "AUTO_ALLOWED"
                    )
                    item.image_status = (
                        "READY"
                    )

                    reason = (
                        "OFFICIAL_COVER_SAVED"
                    )
                    done = True

            need_amazon = (
                not done
                and amazon_offer_count
                == 1
            )

            if need_amazon:
                session.rollback()
            else:
                _finish_job(
                    session,
                    item_id=item_id,
                    revision=revision,
                    attempts=attempts,
                    done=done,
                    reason=reason,
                )
                session.commit()

        if not need_amazon:
            counts[
                reason
            ] += 1

            if network_attempted:
                time.sleep(
                    1.1
                )

            continue

        network_attempted = True
        amazon_result = None

        try:
            amazon_result = (
                _run_amazon_fallback(
                    item_id
                )
            )
        except Exception as exc:
            reason = (
                "AMAZON_"
                + str(
                    getattr(
                        exc,
                        "code",
                        type(
                            exc
                        ).__name__,
                    )
                )
            )[:160]

        if amazon_result is not None:
            amazon_status = str(
                amazon_result.status
                or ""
            ).upper()

            if (
                amazon_status
                == "AUTO_ALLOWED"
            ):
                done = True
                reason = (
                    "AMAZON_COVER_SAVED"
                )

            elif (
                amazon_status
                == "NOOP_ALREADY_ALLOWED"
            ):
                reason = (
                    "AMAZON_NOOP_ALREADY_ALLOWED"
                )

            else:
                reason = (
                    _amazon_failure_reason(
                        amazon_result
                    )
                )

        with SessionLocal() as session:
            session.execute(
                text(
                    "BEGIN IMMEDIATE"
                )
            )

            current_revision = (
                session.execute(
                    text(
                        """
                        SELECT revision
                        FROM cover_registration_jobs
                        WHERE ebook_item_id=:id
                        """
                    ),
                    {
                        "id": item_id,
                    },
                ).scalar()
            )

            current_item = session.get(
                EbookItem,
                item_id,
            )

            if (
                current_revision
                != revision
                or current_item
                is None
            ):
                session.rollback()
                counts[
                    "CONCURRENT_CHANGE"
                ] += 1

                if network_attempted:
                    time.sleep(
                        1.1
                    )

                continue

            if (
                amazon_result
                is not None
                and str(
                    amazon_result.status
                    or ""
                ).upper()
                == "NOOP_ALREADY_ALLOWED"
            ):
                if (
                    DisplayCoverResolver(
                        session
                    )
                    .resolve(
                        item_id
                    )
                    .display_cover_status
                    == "AVAILABLE"
                ):
                    done = True
                    reason = (
                        "EXISTING_OFFICIAL_REUSED"
                    )
                else:
                    done = False
                    reason = (
                        "AMAZON_NOOP_NOT_DISPLAYABLE"
                    )

            _finish_job(
                session,
                item_id=item_id,
                revision=revision,
                attempts=attempts,
                done=done,
                reason=reason,
            )

            session.commit()

        counts[
            reason
        ] += 1

        if network_attempted:
            time.sleep(
                1.1
            )

    print(
        json.dumps(
            dict(
                counts
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    with open(
        (
            "/home/deploy/ai_media_os/"
            "data/database/"
            "cover_registration.lock"
        ),
        "a",
    ) as lock:
        try:
            fcntl.flock(
                lock,
                fcntl.LOCK_EX
                | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            raise SystemExit(
                0
            )

        run()
