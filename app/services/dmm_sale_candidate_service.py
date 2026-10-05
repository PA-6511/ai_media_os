# DMM_SALE_CANDIDATE_SERVICE_V1

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.request import Request, urlopen

from app.services.dmm_product_price_service import (
    DmmProductPriceError,
    parse_dmm_product_cover_image_url_html,
    parse_dmm_product_sale_html,
    parse_dmm_product_series_name_html,
    parse_dmm_product_title_html,
    validate_dmm_product_url,
)
from app.services.dmm_sale_campaign_collector import (
    DmmSaleCampaignCollector,
    DmmSaleCampaignProduct,
)


MAX_RESPONSE_BYTES = 3 * 1024 * 1024


class DmmSaleCandidateServiceError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class DmmSaleCandidate:
    campaign_url: str
    campaign_title: str | None

    # DMM_SALE_CANDIDATE_TITLE_V2
    title: str

    # DMM_SALE_CANDIDATE_METADATA_V3
    series_name: str
    cover_image_url: str

    source_filter_threshold: int

    series_id: str
    product_id: str
    product_url: str

    normal_price_yen: int
    sale_price_yen: int
    discount_percent: float

    sale_start_at: str | None
    sale_end_at: str | None

    source_method: str


@dataclass(frozen=True)
class DmmSaleCandidateCollection:
    campaign_url: str
    campaign_title: str | None

    filter_url: str
    source_filter_threshold: int

    filtered_product_count: int
    attempted_product_count: int

    resolved_count: int
    skipped_count: int

    candidates: tuple[
        DmmSaleCandidate,
        ...,
    ]


class DmmSaleCandidateService:
    def __init__(
        self,
        *,
        collector: (
            DmmSaleCampaignCollector
            | None
        ) = None,
        timeout_seconds: float = 15.0,
        opener: Callable[..., Any] = (
            urlopen
        ),
        user_agent: str = (
            "Mozilla/5.0 "
            "(compatible; AI-Media-OS/1.0)"
        ),
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive"
            )

        self.collector = (
            collector
            or DmmSaleCampaignCollector(
                timeout_seconds=(
                    timeout_seconds
                ),
                opener=opener,
                user_agent=user_agent,
            )
        )

        self.timeout_seconds = float(
            timeout_seconds
        )

        self.opener = opener
        self.user_agent = user_agent

    def _fetch_product_html(
        self,
        product: DmmSaleCampaignProduct,
    ) -> str:
        try:
            product_url = (
                validate_dmm_product_url(
                    product.product_url
                )
            )
        except DmmProductPriceError as exc:
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_URL_INVALID"
                )
            ) from exc

        request = Request(
            product_url,
            headers={
                "User-Agent":
                    self.user_agent,
                "Accept":
                    (
                        "text/html,"
                        "application/xhtml+xml"
                    ),
            },
            method="GET",
        )

        try:
            response = self.opener(
                request,
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_HTTP_FAILED"
                )
            ) from exc

        geturl = getattr(
            response,
            "geturl",
            None,
        )

        if not callable(
            geturl
        ):
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_FINAL_URL_UNAVAILABLE"
                )
            )

        try:
            final_url = (
                validate_dmm_product_url(
                    str(
                        geturl()
                        or ""
                    )
                )
            )
        except Exception as exc:
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_FINAL_URL_INVALID"
                )
            ) from exc

        if final_url != product_url:
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_REDIRECT_MISMATCH"
                )
            )

        try:
            payload = response.read(
                MAX_RESPONSE_BYTES + 1
            )
        except Exception as exc:
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_HTTP_FAILED"
                )
            ) from exc

        if not isinstance(
            payload,
            (bytes, bytearray),
        ):
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_RESPONSE_NOT_BYTES"
                )
            )

        if (
            len(payload)
            > MAX_RESPONSE_BYTES
        ):
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_PRODUCT_RESPONSE_TOO_LARGE"
                )
            )

        return bytes(
            payload
        ).decode(
            "utf-8",
            errors="replace",
        )

    def collect(
        self,
        campaign_url: str,
        *,
        threshold_percent: int,
        max_products: int = 10,
    ) -> DmmSaleCandidateCollection:
        if not (
            1
            <= threshold_percent
            <= 100
        ):
            raise ValueError(
                "threshold_percent "
                "must be between 1 and 100"
            )

        if max_products <= 0:
            raise ValueError(
                "max_products must be positive"
            )

        campaign = self.collector.fetch(
            campaign_url
        )

        matching_filters = [
            item
            for item in (
                campaign.discount_filters
            )
            if (
                item.relation
                == "AT_LEAST"
                and (
                    item.threshold_percent
                    == threshold_percent
                )
            )
        ]

        if not matching_filters:
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_FILTER_NOT_FOUND"
                )
            )

        if len(
            matching_filters
        ) != 1:
            raise (
                DmmSaleCandidateServiceError(
                    "DMM_SALE_FILTER_AMBIGUOUS"
                )
            )

        selected_filter = (
            matching_filters[0]
        )

        filtered = self.collector.fetch(
            selected_filter.url
        )

        attempted = 0
        skipped = 0

        candidates: list[
            DmmSaleCandidate
        ] = []

        for product in (
            filtered.products[
                :max_products
            ]
        ):
            attempted += 1

            html = (
                self._fetch_product_html(
                    product
                )
            )

            sale = (
                parse_dmm_product_sale_html(
                    html,
                    product_id=(
                        product.product_id
                    ),
                )
            )

            if sale is None:
                skipped += 1
                continue

            title = (
                parse_dmm_product_title_html(
                    html,
                    product_id=(
                        product.product_id
                    ),
                )
            )

            if not title:
                skipped += 1
                continue

            series_name = (
                parse_dmm_product_series_name_html(
                    html,
                    product_id=(
                        product.product_id
                    ),
                    series_id=(
                        product.series_id
                    ),
                )
            )

            cover_image_url = (
                parse_dmm_product_cover_image_url_html(
                    html,
                    product_id=(
                        product.product_id
                    ),
                )
            )

            if (
                not series_name
                or not cover_image_url
            ):
                skipped += 1
                continue

            candidates.append(
                DmmSaleCandidate(
                    campaign_url=(
                        campaign.source_url
                    ),
                    campaign_title=(
                        campaign.title
                    ),
                    title=title,
                    series_name=series_name,
                    cover_image_url=(
                        cover_image_url
                    ),
                    source_filter_threshold=(
                        threshold_percent
                    ),
                    series_id=(
                        product.series_id
                    ),
                    product_id=(
                        product.product_id
                    ),
                    product_url=(
                        product.product_url
                    ),
                    normal_price_yen=(
                        sale.normal_price_yen
                    ),
                    sale_price_yen=(
                        sale.sale_price_yen
                    ),
                    discount_percent=(
                        sale.discount_percent
                    ),
                    sale_start_at=(
                        sale.sale_start_at
                    ),
                    sale_end_at=(
                        sale.sale_end_at
                    ),
                    source_method=(
                        sale.source_method
                    ),
                )
            )

        return DmmSaleCandidateCollection(
            campaign_url=(
                campaign.source_url
            ),
            campaign_title=(
                campaign.title
            ),
            filter_url=(
                selected_filter.url
            ),
            source_filter_threshold=(
                threshold_percent
            ),
            filtered_product_count=len(
                filtered.products
            ),
            attempted_product_count=(
                attempted
            ),
            resolved_count=len(
                candidates
            ),
            skipped_count=skipped,
            candidates=tuple(
                candidates
            ),
        )
