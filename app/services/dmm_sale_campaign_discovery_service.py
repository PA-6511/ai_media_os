"""Discover official DMM Books campaign URLs from existing DMM products."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from typing import Any, Callable
from urllib.request import (
    Request,
    urlopen,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ebook import StoreOffer
from app.services.dmm_sale_campaign_collector import (
    validate_dmm_campaign_url,
)


MAX_RESPONSE_BYTES = (
    3 * 1024 * 1024
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; AI-Media-OS/1.0)"
)

_CAMPAIGN_URL_RE = re.compile(
    r"https://book\.dmm\.com/"
    r"list/campaign/"
    r"[A-Za-z0-9_-]+/",
    re.IGNORECASE,
)


class DmmSaleCampaignDiscoveryError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class DmmSaleCampaignDiscoveryResult:
    seed_product_count: int
    fetched_product_count: int
    failed_product_count: int
    discovered_campaign_count: int
    campaign_urls: tuple[str, ...]


def parse_dmm_campaign_urls_html(
    html: str,
) -> tuple[str, ...]:
    source = unescape(
        str(
            html or ""
        )
    )

    # Some embedded JSON may contain escaped
    # forward slashes.
    source = source.replace(
        r"\/",
        "/",
    )

    found = []

    for match in (
        _CAMPAIGN_URL_RE.finditer(
            source
        )
    ):
        raw = match.group(
            0
        )

        try:
            normalized = (
                validate_dmm_campaign_url(
                    raw
                )
            )
        except Exception:
            continue

        if normalized not in found:
            found.append(
                normalized
            )

    return tuple(
        found
    )


def _response_content_type(
    response: Any,
) -> str:
    headers = getattr(
        response,
        "headers",
        None,
    )

    if headers is None:
        return ""

    try:
        value = headers.get(
            "Content-Type",
            "",
        )
    except Exception:
        return ""

    return (
        str(
            value or ""
        )
        .split(
            ";",
            1,
        )[0]
        .strip()
        .casefold()
    )


class DmmSaleCampaignDiscoveryService:
    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        opener: Callable[..., Any] = urlopen,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.timeout_seconds = float(
            timeout_seconds
        )

        self.opener = opener

        self.user_agent = str(
            user_agent
        )

    def _fetch_product_html(
        self,
        product_url: str,
    ) -> str:
        request = Request(
            product_url,
            headers={
                "User-Agent":
                    self.user_agent,

                "Accept": (
                    "text/html,"
                    "application/xhtml+xml"
                ),
            },
            method="GET",
        )

        with self.opener(
            request,
            timeout=self.timeout_seconds,
        ) as response:
            content_type = (
                _response_content_type(
                    response
                )
            )

            if (
                content_type
                and content_type
                not in {
                    "text/html",
                    "application/xhtml+xml",
                }
            ):
                raise (
                    DmmSaleCampaignDiscoveryError(
                        "DMM_PRODUCT_CONTENT_TYPE_INVALID"
                    )
                )

            payload = response.read(
                MAX_RESPONSE_BYTES + 1
            )

            if (
                len(payload)
                > MAX_RESPONSE_BYTES
            ):
                raise (
                    DmmSaleCampaignDiscoveryError(
                        "DMM_PRODUCT_RESPONSE_TOO_LARGE"
                    )
                )

        try:
            return payload.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise (
                DmmSaleCampaignDiscoveryError(
                    "DMM_PRODUCT_ENCODING_INVALID"
                )
            ) from exc

    @staticmethod
    def _seed_product_urls(
        session: Session,
        *,
        max_seed_products: int,
    ) -> tuple[str, ...]:
        if (
            max_seed_products < 1
            or max_seed_products > 50
        ):
            raise (
                DmmSaleCampaignDiscoveryError(
                    "MAX_SEED_PRODUCTS_INVALID"
                )
            )

        rows = session.execute(
            select(
                StoreOffer.product_url
            )
            .where(
                StoreOffer.store_name
                == "dmm",

                StoreOffer.product_url
                .is_not(
                    None
                ),
            )
            .order_by(
                StoreOffer.store_item_id
                .desc()
            )
            .limit(
                max_seed_products
            )
        ).all()

        result = []

        for row in rows:
            value = str(
                row[0]
                or ""
            ).strip()

            if (
                value
                and value
                not in result
            ):
                result.append(
                    value
                )

        return tuple(
            result
        )

    def discover(
        self,
        session: Session,
        *,
        max_seed_products: int = 5,
        max_campaigns: int = 10,
    ) -> DmmSaleCampaignDiscoveryResult:
        if (
            max_campaigns < 1
            or max_campaigns > 50
        ):
            raise (
                DmmSaleCampaignDiscoveryError(
                    "MAX_CAMPAIGNS_INVALID"
                )
            )

        seed_urls = (
            self._seed_product_urls(
                session,
                max_seed_products=(
                    max_seed_products
                ),
            )
        )

        campaigns = []

        fetched = 0
        failed = 0

        for product_url in seed_urls:
            try:
                html = (
                    self._fetch_product_html(
                        product_url
                    )
                )

                fetched += 1

            except Exception:
                failed += 1
                continue

            for campaign_url in (
                parse_dmm_campaign_urls_html(
                    html
                )
            ):
                if (
                    campaign_url
                    in campaigns
                ):
                    continue

                campaigns.append(
                    campaign_url
                )

                if (
                    len(campaigns)
                    >= max_campaigns
                ):
                    break

            if (
                len(campaigns)
                >= max_campaigns
            ):
                break

        return (
            DmmSaleCampaignDiscoveryResult(
                seed_product_count=len(
                    seed_urls
                ),
                fetched_product_count=(
                    fetched
                ),
                failed_product_count=(
                    failed
                ),
                discovered_campaign_count=(
                    len(
                        campaigns
                    )
                ),
                campaign_urls=tuple(
                    campaigns
                ),
            )
        )
