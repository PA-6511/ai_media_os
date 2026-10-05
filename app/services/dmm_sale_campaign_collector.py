# DMM_SALE_CAMPAIGN_COLLECTOR_V1

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


MAX_RESPONSE_BYTES = 3 * 1024 * 1024

_CAMPAIGN_PATH = re.compile(
    r"^/list/campaign/[^/]+/?$"
)

_PRODUCT_PATH = re.compile(
    r"^/product/"
    r"(?P<series_id>[0-9]+)/"
    r"(?P<product_id>[A-Za-z0-9_-]+)/?$"
)

_DISCOUNT_FILTER_TEXT = re.compile(
    r"(?P<rate>[0-9]{1,3})"
    r"\s*%\s*OFF"
    r"(?P<suffix>以上|未満)"
    r"(?:\((?P<count>[0-9]+)\))?",
    re.IGNORECASE,
)


class DmmSaleCampaignCollectorError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class DmmSaleDiscountFilter:
    threshold_percent: int
    relation: str
    result_count: int | None
    url: str
    text: str


@dataclass(frozen=True)
class DmmSaleCampaignProduct:
    series_id: str
    product_id: str
    product_url: str


@dataclass(frozen=True)
class DmmSaleCampaignSnapshot:
    source_url: str
    title: str | None
    discount_filters: tuple[
        DmmSaleDiscountFilter,
        ...,
    ]
    products: tuple[
        DmmSaleCampaignProduct,
        ...,
    ]


class _CampaignHtmlParser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.title_parts: list[str] = []
        self.anchors: list[
            tuple[str, str]
        ] = []

        self._in_title = False
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:
        lowered = tag.casefold()

        if lowered == "title":
            self._in_title = True
            return

        if lowered != "a":
            return

        values = {
            str(key).casefold():
                str(value or "")
            for key, value in attrs
        }

        href = (
            values.get(
                "href",
                "",
            )
            .strip()
        )

        self._anchor_href = (
            href or None
        )

        self._anchor_text = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._in_title:
            self.title_parts.append(
                data
            )

        if (
            self._anchor_href
            is not None
        ):
            self._anchor_text.append(
                data
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        lowered = tag.casefold()

        if lowered == "title":
            self._in_title = False
            return

        if (
            lowered != "a"
            or self._anchor_href
            is None
        ):
            return

        text = re.sub(
            r"\s+",
            " ",
            "".join(
                self._anchor_text
            ),
        ).strip()

        self.anchors.append(
            (
                self._anchor_href,
                text,
            )
        )

        self._anchor_href = None
        self._anchor_text = []


def validate_dmm_campaign_url(
    url: str,
) -> str:
    normalized = unescape(
        str(
            url or ""
        )
    ).strip()

    parsed = urlsplit(
        normalized
    )

    if (
        parsed.scheme != "https"
        or (
            parsed.hostname
            or ""
        ).casefold()
        != "book.dmm.com"
        or not _CAMPAIGN_PATH.fullmatch(
            parsed.path or ""
        )
    ):
        raise DmmSaleCampaignCollectorError(
            "DMM_CAMPAIGN_URL_INVALID"
        )

    return normalized


def _normalize_product_url(
    raw_url: str,
    *,
    base_url: str,
) -> DmmSaleCampaignProduct | None:
    absolute = urljoin(
        base_url,
        unescape(
            str(
                raw_url or ""
            )
        ).strip(),
    )

    parsed = urlsplit(
        absolute
    )

    if (
        parsed.scheme != "https"
        or (
            parsed.hostname
            or ""
        ).casefold()
        != "book.dmm.com"
    ):
        return None

    match = _PRODUCT_PATH.fullmatch(
        parsed.path or ""
    )

    if match is None:
        return None

    clean_url = (
        "https://book.dmm.com"
        + parsed.path
    )

    return DmmSaleCampaignProduct(
        series_id=match.group(
            "series_id"
        ),
        product_id=match.group(
            "product_id"
        ),
        product_url=clean_url,
    )


def parse_dmm_sale_campaign_html(
    html: str,
    *,
    source_url: str,
) -> DmmSaleCampaignSnapshot:
    validated_url = (
        validate_dmm_campaign_url(
            source_url
        )
    )

    source = str(
        html or ""
    )

    if not source.strip():
        raise DmmSaleCampaignCollectorError(
            "DMM_CAMPAIGN_HTML_EMPTY"
        )

    parser = _CampaignHtmlParser()

    try:
        parser.feed(
            source
        )
    except Exception as exc:
        raise DmmSaleCampaignCollectorError(
            "DMM_CAMPAIGN_HTML_PARSE_FAILED"
        ) from exc

    title = re.sub(
        r"\s+",
        " ",
        "".join(
            parser.title_parts
        ),
    ).strip()

    if not title:
        title = None

    filters: list[
        DmmSaleDiscountFilter
    ] = []

    filter_keys: set[
        tuple[int, str, str]
    ] = set()

    products: list[
        DmmSaleCampaignProduct
    ] = []

    product_ids: set[str] = set()

    for href, text in parser.anchors:
        product = _normalize_product_url(
            href,
            base_url=validated_url,
        )

        if (
            product is not None
            and product.product_id
            not in product_ids
        ):
            product_ids.add(
                product.product_id
            )

            products.append(
                product
            )

        discount = (
            _DISCOUNT_FILTER_TEXT
            .search(
                text
            )
        )

        if discount is None:
            continue

        absolute = urljoin(
            validated_url,
            unescape(
                href
            ),
        )

        parsed = urlsplit(
            absolute
        )

        if (
            parsed.scheme != "https"
            or (
                parsed.hostname
                or ""
            ).casefold()
            != "book.dmm.com"
            or not _CAMPAIGN_PATH.fullmatch(
                parsed.path or ""
            )
        ):
            continue

        rate = int(
            discount.group(
                "rate"
            )
        )

        suffix = discount.group(
            "suffix"
        )

        relation = (
            "AT_LEAST"
            if suffix == "以上"
            else "UNDER"
        )

        count_raw = discount.group(
            "count"
        )

        count = (
            int(
                count_raw
            )
            if count_raw
            else None
        )

        key = (
            rate,
            relation,
            absolute,
        )

        if key in filter_keys:
            continue

        filter_keys.add(
            key
        )

        filters.append(
            DmmSaleDiscountFilter(
                threshold_percent=rate,
                relation=relation,
                result_count=count,
                url=absolute,
                text=text,
            )
        )

    filters.sort(
        key=lambda item: (
            0
            if item.relation
            == "AT_LEAST"
            else 1,
            -item.threshold_percent,
            item.url,
        )
    )

    return DmmSaleCampaignSnapshot(
        source_url=validated_url,
        title=title,
        discount_filters=tuple(
            filters
        ),
        products=tuple(
            products
        ),
    )


class DmmSaleCampaignCollector:
    def __init__(
        self,
        *,
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

        self.timeout_seconds = float(
            timeout_seconds
        )

        self.opener = opener
        self.user_agent = user_agent

    def fetch(
        self,
        campaign_url: str,
    ) -> DmmSaleCampaignSnapshot:
        validated_url = (
            validate_dmm_campaign_url(
                campaign_url
            )
        )

        request = Request(
            validated_url,
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
                DmmSaleCampaignCollectorError(
                    "DMM_CAMPAIGN_HTTP_FAILED"
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
            raise DmmSaleCampaignCollectorError(
                "DMM_CAMPAIGN_FINAL_URL_UNAVAILABLE"
            )

        try:
            final_url = (
                validate_dmm_campaign_url(
                    str(
                        geturl()
                        or ""
                    )
                )
            )
        except Exception as exc:
            raise (
                DmmSaleCampaignCollectorError(
                    "DMM_CAMPAIGN_FINAL_URL_INVALID"
                )
            ) from exc

        try:
            payload = response.read(
                MAX_RESPONSE_BYTES + 1
            )
        except Exception as exc:
            raise (
                DmmSaleCampaignCollectorError(
                    "DMM_CAMPAIGN_HTTP_FAILED"
                )
            ) from exc

        if not isinstance(
            payload,
            (bytes, bytearray),
        ):
            raise DmmSaleCampaignCollectorError(
                "DMM_CAMPAIGN_RESPONSE_NOT_BYTES"
            )

        if (
            len(payload)
            > MAX_RESPONSE_BYTES
        ):
            raise DmmSaleCampaignCollectorError(
                "DMM_CAMPAIGN_RESPONSE_TOO_LARGE"
            )

        html = bytes(
            payload
        ).decode(
            "utf-8",
            errors="replace",
        )

        return parse_dmm_sale_campaign_html(
            html,
            source_url=final_url,
        )
