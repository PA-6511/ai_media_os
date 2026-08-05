#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import EbookItem  # noqa: E402
from app.db.read_only_session import ReadOnlySessionLocal  # noqa: E402
from app.db.repositories.store_offer_affiliate_link_repository import (  # noqa: E402
    StoreOfferAffiliateLinkRepository,
)
from app.integrations.wordpress_rest_client import WordPressRestClient  # noqa: E402
from app.services.wordpress_existing_draft_store_buttons_update import (  # noqa: E402
    DEFAULT_DIAGNOSTIC_PATH,
    DEFAULT_EVIDENCE_DIRECTORY,
    ExistingDraftStoreButtonsUpdateError,
    TARGET_EBOOK_ITEM_ID,
    TARGET_WORDPRESS_POST_ID,
    update_existing_draft_store_buttons,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely refresh only the store-buttons block of existing "
            "WordPress draft 207. The default mode is GET-only dry-run."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--ebook-item-id")
    parser.add_argument("--wordpress-post-id")
    parser.add_argument("--confirm-wordpress-post-id")
    parser.add_argument(
        "--diagnostic-output",
        default=str(DEFAULT_DIAGNOSTIC_PATH),
    )
    parser.add_argument(
        "--evidence-directory",
        default=str(DEFAULT_EVIDENCE_DIRECTORY),
    )
    return parser.parse_args(argv)


def _resolved_targets(
    args: argparse.Namespace,
) -> tuple[str, str, str | None]:
    if args.execute:
        missing = [
            flag
            for flag, value in (
                ("--ebook-item-id", args.ebook_item_id),
                ("--wordpress-post-id", args.wordpress_post_id),
                (
                    "--confirm-wordpress-post-id",
                    args.confirm_wordpress_post_id,
                ),
            )
            if value is None
        ]
        if missing:
            raise ExistingDraftStoreButtonsUpdateError(
                "live_arguments_missing",
                "live execution requires explicit " + ", ".join(missing),
            )
    return (
        args.ebook_item_id or TARGET_EBOOK_ITEM_ID,
        args.wordpress_post_id or str(TARGET_WORDPRESS_POST_ID),
        args.confirm_wordpress_post_id,
    )


def _required_environment() -> tuple[str, str, str]:
    base_url = str(os.environ.get("WORDPRESS_BASE_URL") or "").strip()
    username = str(os.environ.get("WORDPRESS_USERNAME") or "").strip()
    application_password = str(
        os.environ.get("WORDPRESS_APPLICATION_PASSWORD")
        or os.environ.get("WORDPRESS_APP_PASSWORD")
        or ""
    ).strip()
    missing = [
        name
        for name, value in (
            ("WORDPRESS_BASE_URL", base_url),
            ("WORDPRESS_USERNAME", username),
            (
                "WORDPRESS_APPLICATION_PASSWORD/WORDPRESS_APP_PASSWORD",
                application_password,
            ),
        )
        if not value
    ]
    if missing:
        raise ExistingDraftStoreButtonsUpdateError(
            "wordpress_credentials_missing",
            "required WordPress environment is missing: "
            + ", ".join(missing),
        )
    return base_url, username, application_password


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        ebook_item_id, wordpress_post_id, confirmed_post_id = (
            _resolved_targets(args)
        )
        base_url, username, application_password = _required_environment()
        wordpress_client = WordPressRestClient(
            base_url=base_url,
            username=username,
            application_password=application_password,
        )

        with ReadOnlySessionLocal() as session:
            item = session.scalar(
                select(EbookItem)
                .where(EbookItem.id == ebook_item_id)
                .options(selectinload(EbookItem.offers))
            )
            if item is None:
                raise ExistingDraftStoreButtonsUpdateError(
                    "db_item_not_found",
                    "target ebook item was not found",
                )
            affiliate_links = StoreOfferAffiliateLinkRepository(session)

            def wordpress_link(offer):
                link = affiliate_links.get_dmm_wordpress_link(
                    store_offer_id=offer.id
                )
                return str(getattr(link, "affiliate_url", "") or "") or None

            def x_link(offer):
                link = affiliate_links.get_dmm_x_link(
                    store_offer_id=offer.id
                )
                return str(getattr(link, "affiliate_url", "") or "") or None

            result = update_existing_draft_store_buttons(
                ebook_item_id=ebook_item_id,
                wordpress_post_id=wordpress_post_id,
                confirm_wordpress_post_id=confirmed_post_id,
                execute=args.execute,
                item=item,
                offers=tuple(item.offers),
                wordpress_client=wordpress_client,
                dmm_wordpress_link_resolver=wordpress_link,
                dmm_x_link_resolver=x_link,
                diagnostic_path=args.diagnostic_output,
                evidence_directory=args.evidence_directory,
            )

        print(
            json.dumps(
                {
                    "status": result.status,
                    "ebook_item_id": result.ebook_item_id,
                    "wordpress_post_id": result.wordpress_post_id,
                    "before_content_sha256": result.before_content_sha256,
                    "after_content_sha256": result.after_content_sha256,
                    "replacement_count": result.replacement_count,
                    "stores": [
                        {"name": name, "label": label}
                        for name, label in zip(
                            result.store_names,
                            result.store_labels,
                            strict=True,
                        )
                    ],
                    "external_update_attempted": (
                        result.external_update_attempted
                    ),
                    "external_update_succeeded": (
                        result.external_update_succeeded
                    ),
                    "verified_after_update": result.verified_after_update,
                    "diagnostic_path": result.diagnostic_path,
                    "evidence_path": result.evidence_path,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except ExistingDraftStoreButtonsUpdateError as exc:
        print(
            json.dumps(
                {"status": "ABORTED", "code": exc.code, "error": str(exc)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:240],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
