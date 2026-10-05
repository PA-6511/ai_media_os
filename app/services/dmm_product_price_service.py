from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import json
import re
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


_PRODUCT_PATH = re.compile(
    r"^/product/[0-9]+/[A-Za-z0-9_-]+/?$"
)

_PRICE_NUMBER = re.compile(
    r"^[0-9]{1,8}(?:\.[0-9]+)?$"
)

_STRUCTURED_PRICE = re.compile(
    r'"price"\s*:\s*"?(?P<price>[0-9]{1,8}(?:\.[0-9]+)?)"?',
    re.IGNORECASE,
)

_JPY_NEARBY = re.compile(
    r'"(?:priceCurrency|currency)"\s*:\s*"JPY"',
    re.IGNORECASE,
)

_JAPANESE_PRICE_PATTERNS = (
    re.compile(
        r"(?:販売価格|税込価格|価格\s*[:：])"
        r"[^0-9]{0,40}"
        r"(?P<price>[0-9][0-9,]{0,10})"
        r"\s*円",
        re.IGNORECASE,
    ),
)


class DmmProductPriceError(RuntimeError):
    pass


@dataclass(frozen=True)
class DmmProductPriceResult:
    product_url: str
    price_yen: int
    currency: str
    source_method: str


class _StructuredPriceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.json_ld_parts: list[str] = []
        self.meta_prices: list[str] = []

        self._capture_json_ld = False
        self._buffer: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        values = {
            str(key).casefold():
                str(value or "")
            for key, value in attrs
        }

        lowered = tag.casefold()

        if lowered == "script":
            script_type = (
                values.get("type", "")
                .strip()
                .casefold()
            )

            if (
                script_type
                == "application/ld+json"
            ):
                self._capture_json_ld = True
                self._buffer = []

        if lowered == "meta":
            itemprop = (
                values.get("itemprop", "")
                .strip()
                .casefold()
            )

            property_name = (
                values.get("property", "")
                .strip()
                .casefold()
            )

            name = (
                values.get("name", "")
                .strip()
                .casefold()
            )

            if (
                itemprop == "price"
                or property_name
                in {
                    "product:price:amount",
                    "og:price:amount",
                }
                or name
                in {
                    "price",
                    "product:price:amount",
                }
            ):
                content = (
                    values.get(
                        "content",
                        "",
                    )
                    .strip()
                )

                if content:
                    self.meta_prices.append(
                        content
                    )

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._capture_json_ld:
            self._buffer.append(data)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag.casefold() == "script"
            and self._capture_json_ld
        ):
            value = "".join(
                self._buffer
            ).strip()

            if value:
                self.json_ld_parts.append(
                    value
                )

            self._capture_json_ld = False
            self._buffer = []


MAX_RESPONSE_BYTES = 2 * 1024 * 1024

_ALLOWED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
}


def validate_dmm_product_url(
    value: str,
) -> str:
    normalized = str(
        value or ""
    ).strip()

    parsed = urlsplit(
        normalized
    )

    if parsed.scheme != "https":
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_INVALID_SCHEME"
        )

    if (
        parsed.hostname or ""
    ).casefold() != "book.dmm.com":
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_INVALID_HOST"
        )

    if not _PRODUCT_PATH.fullmatch(
        parsed.path or ""
    ):
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_INVALID_PATH"
        )

    if parsed.username or parsed.password:
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_USERINFO_FORBIDDEN"
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_INVALID_PORT"
        ) from exc

    if port is not None:
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_PORT_FORBIDDEN"
        )

    if parsed.query:
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_QUERY_FORBIDDEN"
        )

    if parsed.fragment:
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_FRAGMENT_FORBIDDEN"
        )

    return normalized


def _product_identity(
    validated_url: str,
) -> tuple[str, str]:
    parsed = urlsplit(
        validated_url
    )

    parts = [
        part
        for part in (
            parsed.path or ""
        ).split("/")
        if part
    ]

    if (
        len(parts) != 3
        or parts[0] != "product"
    ):
        raise DmmProductPriceError(
            "DMM_PRODUCT_URL_IDENTITY_INVALID"
        )

    return (
        parts[1],
        parts[2],
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

    get_content_type = getattr(
        headers,
        "get_content_type",
        None,
    )

    if callable(get_content_type):
        value = str(
            get_content_type()
            or ""
        )

    else:
        getter = getattr(
            headers,
            "get",
            None,
        )

        value = (
            str(
                getter(
                    "Content-Type",
                    "",
                )
                or ""
            )
            if callable(getter)
            else ""
        )

    return (
        value
        .split(";", 1)[0]
        .strip()
        .casefold()
    )



def _normalize_price(
    value: object,
) -> int | None:
    text = str(
        value or ""
    ).strip().replace(
        ",",
        "",
    )

    if not _PRICE_NUMBER.fullmatch(
        text
    ):
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if (
        number <= 0
        or number > 10_000_000
        or not number.is_integer()
    ):
        return None

    return int(number)


def _collect_json_prices(
    value: Any,
    *,
    inherited_currency: str = "",
) -> list[int]:
    prices: list[int] = []

    if isinstance(
        value,
        dict,
    ):
        currency = str(
            value.get(
                "priceCurrency",
                value.get(
                    "currency",
                    inherited_currency,
                ),
            )
            or ""
        ).strip().upper()

        if "price" in value:
            price = _normalize_price(
                value.get("price")
            )

            if (
                price is not None
                and currency
                in {
                    "",
                    "JPY",
                }
            ):
                prices.append(price)

        for child in value.values():
            prices.extend(
                _collect_json_prices(
                    child,
                    inherited_currency=currency,
                )
            )

    elif isinstance(
        value,
        list,
    ):
        for child in value:
            prices.extend(
                _collect_json_prices(
                    child,
                    inherited_currency=(
                        inherited_currency
                    ),
                )
            )

    return prices


def _unique_prices(
    values: list[int],
) -> list[int]:
    result: list[int] = []

    for value in values:
        if value not in result:
            result.append(value)

    return result


def parse_dmm_product_price_html(
    html: str,
) -> tuple[int, str]:
    source = str(
        html or ""
    )

    if not source.strip():
        raise DmmProductPriceError(
            "DMM_PRODUCT_HTML_EMPTY"
        )

    parser = _StructuredPriceParser()

    try:
        parser.feed(source)
    except Exception as exc:
        raise DmmProductPriceError(
            "DMM_PRODUCT_HTML_PARSE_FAILED"
        ) from exc

    json_prices: list[int] = []

    for part in parser.json_ld_parts:
        try:
            payload = json.loads(
                unescape(part)
            )
        except Exception:
            continue

        json_prices.extend(
            _collect_json_prices(
                payload
            )
        )

    json_prices = _unique_prices(
        json_prices
    )

    if len(json_prices) == 1:
        return (
            json_prices[0],
            "JSON_LD",
        )

    if len(json_prices) > 1:
        raise DmmProductPriceError(
            "DMM_PRODUCT_PRICE_AMBIGUOUS_JSON_LD"
        )

    meta_prices = _unique_prices(
        [
            price
            for raw in parser.meta_prices
            if (
                price := _normalize_price(
                    raw
                )
            )
            is not None
        ]
    )

    if len(meta_prices) == 1:
        return (
            meta_prices[0],
            "META_PRICE",
        )

    if len(meta_prices) > 1:
        raise DmmProductPriceError(
            "DMM_PRODUCT_PRICE_AMBIGUOUS_META"
        )

    structured_prices: list[int] = []

    for match in _STRUCTURED_PRICE.finditer(
        source
    ):
        start = max(
            0,
            match.start() - 300,
        )

        end = min(
            len(source),
            match.end() + 300,
        )

        nearby = source[
            start:end
        ]

        if not _JPY_NEARBY.search(
            nearby
        ):
            continue

        price = _normalize_price(
            match.group("price")
        )

        if price is not None:
            structured_prices.append(
                price
            )

    structured_prices = (
        _unique_prices(
            structured_prices
        )
    )

    if len(structured_prices) == 1:
        return (
            structured_prices[0],
            "STRUCTURED_JPY",
        )

    if len(structured_prices) > 1:
        raise DmmProductPriceError(
            "DMM_PRODUCT_PRICE_AMBIGUOUS_STRUCTURED"
        )

    japanese_prices: list[int] = []

    normalized_source = unescape(
        re.sub(
            r"<[^>]+>",
            " ",
            source,
        )
    )

    for pattern in (
        _JAPANESE_PRICE_PATTERNS
    ):
        for match in pattern.finditer(
            normalized_source
        ):
            price = _normalize_price(
                match.group("price")
            )

            if price is not None:
                japanese_prices.append(
                    price
                )

    japanese_prices = _unique_prices(
        japanese_prices
    )

    if len(japanese_prices) == 1:
        return (
            japanese_prices[0],
            "JAPANESE_PRICE_TEXT",
        )

    if len(japanese_prices) > 1:
        raise DmmProductPriceError(
            "DMM_PRODUCT_PRICE_AMBIGUOUS_TEXT"
        )

    raise DmmProductPriceError(
        "DMM_PRODUCT_PRICE_NOT_FOUND"
    )


class DmmProductPriceService:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        opener: Callable[..., Any] = urlopen,
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
        product_url: str,
    ) -> DmmProductPriceResult:
        normalized_url = (
            validate_dmm_product_url(
                product_url
            )
        )

        requested_identity = (
            _product_identity(
                normalized_url
            )
        )

        request = Request(
            normalized_url,
            headers={
                "User-Agent":
                    self.user_agent,

                "Accept":
                    "text/html,"
                    "application/xhtml+xml",
            },
            method="GET",
        )

        try:
            response = self.opener(
                request,
                timeout=self.timeout_seconds,
            )

        except Exception as exc:
            raise DmmProductPriceError(
                "DMM_PRODUCT_HTTP_FAILED"
            ) from exc

        geturl = getattr(
            response,
            "geturl",
            None,
        )

        if not callable(geturl):
            raise DmmProductPriceError(
                "DMM_PRODUCT_FINAL_URL_UNAVAILABLE"
            )

        try:
            final_url_raw = str(
                geturl()
                or ""
            ).strip()

        except Exception as exc:
            raise DmmProductPriceError(
                "DMM_PRODUCT_FINAL_URL_UNAVAILABLE"
            ) from exc

        try:
            final_url = (
                validate_dmm_product_url(
                    final_url_raw
                )
            )

        except DmmProductPriceError as exc:
            raise DmmProductPriceError(
                "DMM_PRODUCT_FINAL_URL_INVALID"
            ) from exc

        final_identity = (
            _product_identity(
                final_url
            )
        )

        if (
            final_identity
            != requested_identity
        ):
            raise DmmProductPriceError(
                "DMM_PRODUCT_REDIRECT_IDENTITY_MISMATCH"
            )

        content_type = (
            _response_content_type(
                response
            )
        )

        if (
            content_type
            not in _ALLOWED_CONTENT_TYPES
        ):
            raise DmmProductPriceError(
                "DMM_PRODUCT_CONTENT_TYPE_UNSUPPORTED"
            )

        try:
            payload = response.read(
                MAX_RESPONSE_BYTES + 1
            )

        except Exception as exc:
            raise DmmProductPriceError(
                "DMM_PRODUCT_HTTP_FAILED"
            ) from exc

        if not isinstance(
            payload,
            (bytes, bytearray),
        ):
            raise DmmProductPriceError(
                "DMM_PRODUCT_RESPONSE_NOT_BYTES"
            )

        if (
            len(payload)
            > MAX_RESPONSE_BYTES
        ):
            raise DmmProductPriceError(
                "DMM_PRODUCT_RESPONSE_TOO_LARGE"
            )

        try:
            html = payload.decode(
                "utf-8"
            )
        except UnicodeDecodeError:
            html = payload.decode(
                "utf-8",
                errors="replace",
            )

        price_yen, source_method = (
            parse_dmm_product_price_html(
                html
            )
        )

        return DmmProductPriceResult(
            product_url=normalized_url,
            price_yen=price_yen,
            currency="JPY",
            source_method=source_method,
        )
# DMM_SALE_HTML_PARSER_V1

_DMM_SALE_RSC_PATTERN = re.compile(
    r'self\.__next_f\.push\(\[1,(".*?")\]\)',
    re.DOTALL,
)

_DMM_SALE_PRODUCT_ID_PATTERN = re.compile(
    r'"productId":"(?P<product_id>[A-Za-z0-9_-]+)"'
)

_DMM_SALE_FIXED_PRICE_PATTERN = re.compile(
    r'"fixedPrice":(?P<value>[0-9]+)'
)

_DMM_SALE_CAMPAIGN_PRICE_PATTERN = re.compile(
    r'"campaignPrice":'
    r'(?P<value>'
    r'[0-9]+'
    r'|null'
    r'|"\$undefined"'
    r')'
)

_DMM_SALE_SALES_PATTERN = re.compile(
    r'"sales":\{'
    r'(?P<body>[^{}]{0,1200})'
    r'\}'
)

_DMM_SALE_RATE_PATTERN = re.compile(
    r'"rate":(?P<value>[0-9]+(?:\.[0-9]+)?)'
)

_DMM_SALE_BEGIN_PATTERN = re.compile(
    r'"begin":"(?P<value>[^"]*)"'
)

_DMM_SALE_END_PATTERN = re.compile(
    r'"end":"(?P<value>[^"]*)"'
)


@dataclass(frozen=True)
class DmmProductSaleResult:
    product_id: str
    normal_price_yen: int
    sale_price_yen: int
    discount_percent: float
    sale_start_at: str | None
    sale_end_at: str | None
    source_method: str


def _dmm_sale_optional_text(
    value: str | None,
) -> str | None:
    normalized = str(
        value or ""
    ).strip()

    if (
        not normalized
        or normalized == "$undefined"
    ):
        return None

    return normalized


def _dmm_sale_exact_product_blocks(
    html: str,
    product_id: str,
) -> list[str]:
    target = str(
        product_id or ""
    ).strip()

    if not target:
        raise DmmProductPriceError(
            "DMM_SALE_PRODUCT_ID_REQUIRED"
        )

    blocks: list[str] = []

    needle = (
        '"productId":"'
        + target
        + '"'
    )

    for match in _DMM_SALE_RSC_PATTERN.finditer(
        str(
            html or ""
        )
    ):
        try:
            segment = json.loads(
                match.group(1)
            )
        except Exception:
            continue

        if not isinstance(
            segment,
            str,
        ):
            continue

        start = 0

        while True:
            position = segment.find(
                needle,
                start,
            )

            if position < 0:
                break

            next_product = segment.find(
                '"productId":"',
                position + len(
                    needle
                ),
            )

            if (
                next_product < 0
                or (
                    next_product
                    - position
                )
                > 12000
            ):
                end = min(
                    len(segment),
                    position + 12000,
                )
            else:
                end = next_product

            blocks.append(
                segment[
                    position:end
                ]
            )

            start = (
                position
                + len(
                    needle
                )
            )

    return blocks

# DMM_SALE_HTML_PARSER_V2_SPLIT_RSC

def parse_dmm_product_sale_html(
    html: str,
    *,
    product_id: str,
) -> DmmProductSaleResult | None:
    source = str(
        html or ""
    )

    if not source.strip():
        raise DmmProductPriceError(
            "DMM_PRODUCT_HTML_EMPTY"
        )

    target = str(
        product_id or ""
    ).strip()

    blocks = (
        _dmm_sale_exact_product_blocks(
            source,
            target,
        )
    )

    if not blocks:
        return None

    price_candidates: list[
        tuple[int, int]
    ] = []

    sale_metadata: list[
        tuple[
            float | None,
            str | None,
            str | None,
        ]
    ] = []

    # Pass 1:
    # collect the exact target product's
    # fixedPrice / campaignPrice.
    for block in blocks:
        fixed_match = (
            _DMM_SALE_FIXED_PRICE_PATTERN
            .search(
                block
            )
        )

        campaign_match = (
            _DMM_SALE_CAMPAIGN_PRICE_PATTERN
            .search(
                block
            )
        )

        if (
            fixed_match is not None
            and campaign_match is not None
        ):
            campaign_raw = (
                campaign_match.group(
                    "value"
                )
            )

            if campaign_raw not in {
                "null",
                '"$undefined"',
            }:
                normal_price = int(
                    fixed_match.group(
                        "value"
                    )
                )

                sale_price = int(
                    campaign_raw
                )

                if (
                    normal_price > 0
                    and 0
                    <= sale_price
                    < normal_price
                ):
                    candidate = (
                        normal_price,
                        sale_price,
                    )

                    if (
                        candidate
                        not in price_candidates
                    ):
                        price_candidates.append(
                            candidate
                        )

        # Pass 2 is intentionally done
        # across every exact target block.
        # DMM can emit campaignPrice in one
        # RSC query result and campaignDetail
        # in another RSC query result.
        sales_match = (
            _DMM_SALE_SALES_PATTERN
            .search(
                block
            )
        )

        if sales_match is None:
            continue

        sales_body = (
            sales_match.group(
                "body"
            )
        )

        rate_match = (
            _DMM_SALE_RATE_PATTERN
            .search(
                sales_body
            )
        )

        begin_match = (
            _DMM_SALE_BEGIN_PATTERN
            .search(
                sales_body
            )
        )

        end_match = (
            _DMM_SALE_END_PATTERN
            .search(
                sales_body
            )
        )

        rate = (
            float(
                rate_match.group(
                    "value"
                )
            )
            if rate_match
            else None
        )

        begin = (
            _dmm_sale_optional_text(
                begin_match.group(
                    "value"
                )
                if begin_match
                else None
            )
        )

        end = (
            _dmm_sale_optional_text(
                end_match.group(
                    "value"
                )
                if end_match
                else None
            )
        )

        metadata = (
            rate,
            begin,
            end,
        )

        if metadata not in sale_metadata:
            sale_metadata.append(
                metadata
            )

    if not price_candidates:
        return None

    if len(
        price_candidates
    ) > 1:
        raise DmmProductPriceError(
            "DMM_SALE_PRICE_AMBIGUOUS"
        )

    (
        normal_price,
        sale_price,
    ) = price_candidates[0]

    calculated_discount = round(
        (
            normal_price
            - sale_price
        )
        * 100.0
        / normal_price,
        2,
    )

    discount_percent = (
        calculated_discount
    )

    sale_start_at = None
    sale_end_at = None

    # Prefer exact DMM campaign metadata
    # when present. Price math remains a
    # bounded fallback.
    if sale_metadata:
        (
            dmm_rate,
            dmm_begin,
            dmm_end,
        ) = sale_metadata[0]

        if dmm_rate is not None:
            discount_percent = (
                dmm_rate
            )

        sale_start_at = dmm_begin
        sale_end_at = dmm_end

    return DmmProductSaleResult(
        product_id=target,
        normal_price_yen=(
            normal_price
        ),
        sale_price_yen=(
            sale_price
        ),
        discount_percent=(
            discount_percent
        ),
        sale_start_at=(
            sale_start_at
        ),
        sale_end_at=(
            sale_end_at
        ),
        source_method=(
            "DMM_RSC_CAMPAIGN_PRICE_V1"
        ),
    )

# DMM_PRODUCT_TITLE_HTML_PARSER_V1

_DMM_PRODUCT_TITLE_PATTERN = re.compile(
    r'"title":"(?P<value>(?:\\.|[^"])*)"'
)


def _dmm_exact_product_metadata_blocks(
    html: str,
    product_id: str,
) -> list[str]:
    target = str(
        product_id or ""
    ).strip()

    if not target:
        raise DmmProductPriceError(
            "DMM_PRODUCT_ID_REQUIRED"
        )

    blocks: list[str] = []

    needles = (
        (
            '"productId":"'
            + target
            + '"'
        ),
        (
            '"contentId":"'
            + target
            + '"'
        ),
    )

    for match in _DMM_SALE_RSC_PATTERN.finditer(
        str(
            html or ""
        )
    ):
        try:
            segment = json.loads(
                match.group(1)
            )
        except Exception:
            continue

        if not isinstance(
            segment,
            str,
        ):
            continue

        for needle in needles:
            start = 0

            while True:
                position = segment.find(
                    needle,
                    start,
                )

                if position < 0:
                    break

                next_positions: list[int] = []

                for next_needle in (
                    '"productId":"',
                    '"contentId":"',
                ):
                    next_position = (
                        segment.find(
                            next_needle,
                            position
                            + len(
                                needle
                            ),
                        )
                    )

                    if next_position >= 0:
                        next_positions.append(
                            next_position
                        )

                if next_positions:
                    end = min(
                        next_positions
                    )

                    if (
                        end - position
                        > 12000
                    ):
                        end = min(
                            len(segment),
                            position + 12000,
                        )

                else:
                    end = min(
                        len(segment),
                        position + 12000,
                    )

                block = segment[
                    position:end
                ]

                if block not in blocks:
                    blocks.append(
                        block
                    )

                start = (
                    position
                    + len(
                        needle
                    )
                )

    return blocks


def parse_dmm_product_title_html(
    html: str,
    *,
    product_id: str,
) -> str | None:
    source = str(
        html or ""
    )

    if not source.strip():
        raise DmmProductPriceError(
            "DMM_PRODUCT_HTML_EMPTY"
        )

    titles: list[str] = []

    for block in (
        _dmm_exact_product_metadata_blocks(
            source,
            product_id,
        )
    ):
        for match in (
            _DMM_PRODUCT_TITLE_PATTERN.finditer(
                block
            )
        ):
            try:
                title = json.loads(
                    '"'
                    + match.group(
                        "value"
                    )
                    + '"'
                )
            except Exception:
                continue

            normalized = str(
                title or ""
            ).strip()

            if (
                normalized
                and normalized
                not in titles
            ):
                titles.append(
                    normalized
                )

    if not titles:
        return None

    # DMM may expose both a series/base title
    # and a volume-specific title for the same
    # exact content ID. Prefer the more specific
    # (normally longer) title.
    return max(
        titles,
        key=lambda value: (
            len(value),
            value,
        ),
    )

# DMM_PRODUCT_SALE_METADATA_V2


def _decoded_dmm_rsc_segments_for_product(
    html: str,
    product_id: str,
) -> list[str]:
    target = str(
        product_id or ""
    ).strip()

    if not target:
        raise DmmProductPriceError(
            "DMM_PRODUCT_ID_REQUIRED"
        )

    segments: list[str] = []

    for match in _DMM_SALE_RSC_PATTERN.finditer(
        str(
            html or ""
        )
    ):
        try:
            decoded = json.loads(
                match.group(1)
            )
        except Exception:
            continue

        if not isinstance(
            decoded,
            str,
        ):
            continue

        if target not in decoded:
            continue

        if decoded not in segments:
            segments.append(
                decoded
            )

    return segments


def _decode_dmm_json_string_value_v2(
    value: str,
) -> str:
    try:
        return str(
            json.loads(
                '"'
                + value
                + '"'
            )
            or ""
        ).strip()
    except Exception:
        return (
            str(
                value or ""
            )
            .replace(
                "\\/",
                "/",
            )
            .replace(
                "\\u0026",
                "&",
            )
            .strip()
        )


def parse_dmm_product_series_name_html(
    html: str,
    *,
    product_id: str,
    series_id: str,
) -> str | None:
    target_series = str(
        series_id or ""
    ).strip()

    if not target_series:
        return None

    escaped_series = re.escape(
        target_series
    )

    patterns = (
        re.compile(
            r'"series"\s*:\s*\{'
            r'[^{}]{0,1200}'
            r'"seriesId"\s*:\s*"'
            + escaped_series
            + r'"'
            r'[^{}]{0,1200}'
            r'"title"\s*:\s*"'
            r'(?P<value>(?:\\.|[^"])*)"',
            flags=re.S,
        ),
        re.compile(
            r'"seriesId"\s*:\s*"'
            + escaped_series
            + r'"'
            r'[^{}]{0,600}'
            r'"title"\s*:\s*"'
            r'(?P<value>(?:\\.|[^"])*)"',
            flags=re.S,
        ),
    )

    values: list[str] = []

    for segment in (
        _decoded_dmm_rsc_segments_for_product(
            html,
            product_id,
        )
    ):
        for pattern in patterns:
            for match in pattern.finditer(
                segment
            ):
                value = (
                    _decode_dmm_json_string_value_v2(
                        match.group(
                            "value"
                        )
                    )
                )

                if (
                    value
                    and value
                    not in values
                ):
                    values.append(
                        value
                    )

    if not values:
        return None

    return values[0]


def parse_dmm_product_cover_image_url_html(
    html: str,
    *,
    product_id: str,
) -> str | None:
    target = str(
        product_id or ""
    ).strip()

    if not target:
        raise DmmProductPriceError(
            "DMM_PRODUCT_ID_REQUIRED"
        )

    escaped = re.escape(
        target
    )

    pattern = re.compile(
        r'https://ebook-assets\.dmm\.com/'
        r'digital/e-book/'
        + escaped
        + r'/'
        + escaped
        + r'(?P<size>pl|ps|pt)'
        r'\.(?P<ext>webp|jpg|jpeg|png)',
        flags=re.I,
    )

    candidates: list[
        tuple[int, str]
    ] = []

    size_rank = {
        "pl": 0,
        "ps": 1,
        "pt": 2,
    }

    ext_rank = {
        "webp": 0,
        "jpg": 1,
        "jpeg": 2,
        "png": 3,
    }

    for segment in (
        _decoded_dmm_rsc_segments_for_product(
            html,
            product_id,
        )
    ):
        normalized = (
            segment
            .replace(
                "\\/",
                "/",
            )
            .replace(
                "\\u0026",
                "&",
            )
        )

        for match in pattern.finditer(
            normalized
        ):
            url = match.group(0)

            score = (
                size_rank.get(
                    match.group(
                        "size"
                    ).lower(),
                    9,
                )
                * 10
                + ext_rank.get(
                    match.group(
                        "ext"
                    ).lower(),
                    9,
                )
            )

            entry = (
                score,
                url,
            )

            if entry not in candidates:
                candidates.append(
                    entry
                )

    if not candidates:
        return None

    candidates.sort(
        key=lambda entry: (
            entry[0],
            entry[1],
        )
    )

    return candidates[0][1]
