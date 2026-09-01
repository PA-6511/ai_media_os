from __future__ import annotations

from src.rakuten_kobo_csv import (
    normalize_author_name,
    normalize_publisher_name,
)

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import html
import json
import re
import unicodedata
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.integrations.rakuten_kobo_api_client import (
    GetOnlyTransport,
    RakutenKoboApiClient,
    RakutenKoboApiError,
    RequestsGetTransport,
)
from app.integrations.rakuten_kobo_live_configuration import (
    load_repository_live_configuration,
)
from app.services.store_url_policy import (
    StoreUrlPolicyError,
    normalize_store_url,
)


# KOBO_OFFICIAL_MANUAL_RESOLUTION_V3


class RakutenKoboManualOfferResolutionError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


@dataclass(frozen=True)
class RakutenKoboManualOfferResolution:
    item_number: str
    item_price_yen: int
    product_url: str
    official_product_url: str
    provider_title: str
    author_name: str | None = None
    publisher_name: str | None = None


def _normalized_product_identity(
    value: str,
) -> tuple[str, str, str]:
    try:
        normalized = normalize_store_url(
            str(value or "").strip(),
            store_name="rakuten_kobo",
            purpose="product",
            required=True,
        )
    except StoreUrlPolicyError as exc:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_PRODUCT_URL_INVALID"
        ) from exc

    if not normalized:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_PRODUCT_URL_REQUIRED"
        )

    parsed = urlsplit(normalized)

    host = str(parsed.hostname or "").lower()
    path = parsed.path or "/"

    if path != "/":
        path = path.rstrip("/") + "/"

    return normalized, host, path


def _payload_items(
    payload: Any,
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_RESPONSE_INVALID"
        )

    raw_items: Any = payload.get("Items")

    if raw_items is None:
        raw_items = payload.get("items")

    if raw_items is None and isinstance(
        payload.get("Item"),
        dict,
    ):
        raw_items = [
            payload["Item"]
        ]

    if not isinstance(raw_items, list):
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_RESPONSE_INVALID"
        )

    result: list[dict[str, Any]] = []

    for entry in raw_items:
        if not isinstance(entry, dict):
            continue

        wrapped = entry.get("Item")

        if isinstance(wrapped, dict):
            result.append(wrapped)
        else:
            result.append(entry)

    return result


def _official_price_yen(
    value: Any,
) -> int:
    try:
        price = Decimal(
            str(value).strip()
        )
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PRICE_INVALID"
        ) from exc

    if (
        not price.is_finite()
        or price <= 0
        or price
        != price.to_integral_value()
    ):
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PRICE_INVALID"
        )

    return int(price)


def _entered_price_yen(
    value: str,
) -> int | None:
    text = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip()

    if not text:
        return None

    text = "".join(
        character
        for character in text
        if not character.isspace()
    )

    for token in (
        ",",
        "円",
        "¥",
        "JPY",
        "jpy",
    ):
        text = text.replace(
            token,
            "",
        )

    try:
        price = Decimal(text)
    except (
        InvalidOperation,
        ValueError,
    ) as exc:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_ENTERED_PRICE_INVALID"
        ) from exc

    if (
        not price.is_finite()
        or price <= 0
        or price
        != price.to_integral_value()
    ):
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_ENTERED_PRICE_INVALID"
        )

    return int(price)



# KOBO_MANUAL_TITLE_RETRY_V1
def _reduced_title_for_retry(
    value: str,
) -> str:
    """
    Remove only a trailing volume-like token for one
    bounded official API retry.

    Examples:
      奴隷先生 8      -> 奴隷先生
      奴隷先生 第8巻 -> 奴隷先生

    Never manufacture provider IDs or prices.
    """
    title = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip()

    if not title:
        return ""

    patterns = (
        r"\s+第?\d+\s*巻\s*$",
        r"\s+\d+\s*$",
        r"\s*[（(]\s*\d+\s*[)）]\s*$",
    )

    reduced = title

    for pattern in patterns:
        candidate = re.sub(
            pattern,
            "",
            reduced,
        ).strip()

        if (
            candidate
            and candidate != reduced
        ):
            reduced = candidate
            break

    if reduced == title:
        return ""

    return reduced


# KOBO_OFFICIAL_TITLE_FETCH_SHARED_V1
def fetch_official_kobo_items_by_title(
    title: str,
    *,
    transport: GetOnlyTransport | None = None,
    hits: int = 1,
) -> tuple[dict[str, Any], ...]:
    """Fetch bounded official Kobo candidates using a title only.

    The original title is queried first.  When it returns no items,
    the existing bounded trailing-volume retry is attempted once.
    No database write or product selection is performed here.
    The default remains hits=1 for manual resolver compatibility.

    # KOBO_OFFICIAL_TITLE_FETCH_HITS_V1
    """
    normalized_title = str(
        title or ""
    ).strip()

    if not normalized_title:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_TITLE_REQUIRED_FOR_OFFICIAL_LOOKUP"
        )

    def fetch_once(
        query_title: str,
    ) -> list[dict[str, Any]]:
        try:
            configuration = (
                load_repository_live_configuration(
                    title=query_title,
                    item_number=None,
                    hits=hits,
                )
            )
        except RakutenKoboApiError as exc:
            raise RakutenKoboManualOfferResolutionError(
                "KOBO_OFFICIAL_API_CONFIGURATION_INVALID"
            ) from exc

        if configuration is None:
            raise RakutenKoboManualOfferResolutionError(
                "KOBO_OFFICIAL_API_NOT_CONFIGURED"
            )

        try:
            response = RakutenKoboApiClient(
                transport
                or RequestsGetTransport()
            ).fetch(
                configuration
            )
        except RakutenKoboApiError as exc:
            raise RakutenKoboManualOfferResolutionError(
                "KOBO_OFFICIAL_API_FAILED"
            ) from exc

        try:
            payload = json.loads(
                response.body.decode(
                    "utf-8"
                )
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RakutenKoboManualOfferResolutionError(
                "KOBO_OFFICIAL_RESPONSE_INVALID"
            ) from exc

        return _payload_items(
            payload
        )

    items = fetch_once(
        normalized_title
    )

    if not items:
        retry_title = (
            _reduced_title_for_retry(
                normalized_title
            )
        )

        if retry_title:
            items = fetch_once(
                retry_title
            )

    return tuple(
        items
    )



# KOBO_OFFICIAL_PRODUCT_PAGE_FALLBACK_V1
def _normalized_visible_text(
    value: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(
            str(value or "")
        ),
    ).strip()


def _resolve_official_product_page_html(
    *,
    requested_title: str,
    product_url: str,
    entered_price: str,
    page_html: str,
) -> RakutenKoboManualOfferResolution:
    """
    Resolve only when the exact human-confirmed Rakuten Books Kobo page
    independently binds title, itemNumber and price.

    No provider ID or price is guessed.
    """

    normalized_input_url, _, _ = (
        _normalized_product_identity(
            product_url
        )
    )

    requested = unicodedata.normalize(
        "NFKC",
        str(requested_title or ""),
    ).strip()

    if not requested:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_TITLE_REQUIRED_FOR_OFFICIAL_LOOKUP"
        )

    source = str(
        page_html or ""
    )

    # --------------------------------------------------
    # 1. Exact page <title>.
    #
    # Example:
    # 楽天Kobo電子書籍ストア: 奴隷先生 8 - 村生ミオ - 7275000883042
    # --------------------------------------------------

    title_match = re.search(
        r"<title[^>]*>(.*?)</title>",
        source,
        flags=re.I | re.S,
    )

    if title_match is None:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PAGE_TITLE_MISSING"
        )

    page_title = _normalized_visible_text(
        re.sub(
            r"<[^>]+>",
            " ",
            title_match.group(1),
        )
    )

    normalized_page_title = unicodedata.normalize(
        "NFKC",
        page_title,
    )

    if requested not in normalized_page_title:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PAGE_TITLE_MISMATCH"
        )

    title_numbers = re.findall(
        r"(?<!\d)(\d{13})(?!\d)",
        normalized_page_title,
    )

    if len(
        set(
            title_numbers
        )
    ) != 1:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PAGE_ITEM_NUMBER_AMBIGUOUS"
        )

    item_number = next(
        iter(
            set(
                title_numbers
            )
        )
    )

    if not re.fullmatch(
        r"[0-9]{13}",
        item_number,
    ):
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_ITEM_NUMBER_INVALID"
        )

    # --------------------------------------------------
    # 2. Require the same item number in page metadata.
    # This prevents accepting an unrelated 13-digit
    # recommendation/product number elsewhere in HTML.
    # --------------------------------------------------

    metadata_number_bound = bool(
        re.search(
            r'<meta[^>]+(?:name|property)=["\']'
            r'(?:keywords|description|og:title)'
            r'["\'][^>]+content=["\'][^"\']*'
            + re.escape(
                item_number
            ),
            source,
            flags=re.I | re.S,
        )
        or re.search(
            re.escape(
                item_number
            )
            + r'[^<]{0,200}</title>',
            source,
            flags=re.I | re.S,
        )
    )

    if not metadata_number_bound:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PAGE_ITEM_NUMBER_NOT_BOUND"
        )

    # --------------------------------------------------
    # 3. Price must come from a tag that also carries
    # the requested title.
    #
    # Actual page:
    # data-title="奴隷先生 8" data-price="858"
    # --------------------------------------------------

    tag_candidates = re.findall(
        r"<[^>]+>",
        source,
        flags=re.S,
    )

    matched_prices: set[int] = set()

    for tag in tag_candidates:
        title_attr = re.search(
            r'data-title=["\']([^"\']+)["\']',
            tag,
            flags=re.I,
        )

        price_attr = re.search(
            r'data-price=["\']([^"\']+)["\']',
            tag,
            flags=re.I,
        )

        if (
            title_attr is None
            or price_attr is None
        ):
            continue

        tag_title = unicodedata.normalize(
            "NFKC",
            html.unescape(
                title_attr.group(1)
            ),
        ).strip()

        if tag_title != requested:
            continue

        price = _official_price_yen(
            price_attr.group(1)
        )

        matched_prices.add(
            price
        )

    if len(
        matched_prices
    ) != 1:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PAGE_PRICE_AMBIGUOUS"
        )

    official_price = next(
        iter(
            matched_prices
        )
    )

    manual_price = _entered_price_yen(
        entered_price
    )

    if (
        manual_price is not None
        and manual_price != official_price
    ):
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PRICE_MISMATCH"
        )

    return RakutenKoboManualOfferResolution(
        item_number=item_number,
        item_price_yen=official_price,
        product_url=normalized_input_url,
        official_product_url=normalized_input_url,
        provider_title=requested,
    )


def _resolve_official_product_page(
    *,
    requested_title: str,
    product_url: str,
    entered_price: str,
) -> RakutenKoboManualOfferResolution:
    request = Request(
        product_url,
        headers={
            "User-Agent":
                "Mozilla/5.0 "
                "AI-Media-OS-Kobo-Official-Resolver/1.0",
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=30,
        ) as response:
            status = int(
                getattr(
                    response,
                    "status",
                    200,
                )
            )

            if status != 200:
                raise RakutenKoboManualOfferResolutionError(
                    "KOBO_OFFICIAL_PRODUCT_PAGE_HTTP_ERROR"
                )

            body = response.read()

    except RakutenKoboManualOfferResolutionError:
        raise

    except Exception as exc:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PRODUCT_PAGE_FAILED"
        ) from exc

    try:
        page_html = body.decode(
            "utf-8"
        )
    except UnicodeDecodeError as exc:
        raise RakutenKoboManualOfferResolutionError(
            "KOBO_OFFICIAL_PRODUCT_PAGE_INVALID"
        ) from exc

    return _resolve_official_product_page_html(
        requested_title=requested_title,
        product_url=product_url,
        entered_price=entered_price,
        page_html=page_html,
    )



def _optional_author_name(
    value: Any,
) -> str | None:
    """Normalize official Kobo author metadata fail-soft."""

    try:
        normalized = normalize_author_name(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    return (
        str(normalized or "").strip()
        or None
    )


def _optional_publisher_name(
    value: Any,
) -> str | None:
    """Normalize official Kobo publisher metadata fail-soft."""

    try:
        normalized = normalize_publisher_name(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    return (
        str(normalized or "").strip()
        or None
    )


class RakutenKoboManualOfferResolver:
    """Resolve a manually supplied Kobo product URL against the official API.

    Official sources are queried with bounded retries only.
    No database write is performed here.
    """

    def __init__(
        self,
        transport: GetOnlyTransport | None = None,
    ) -> None:
        self.transport = transport

    def resolve(
        self,
        *,
        title: str,
        product_url: str,
        entered_price: str = "",
    ) -> RakutenKoboManualOfferResolution:
        normalized_title = str(
            title or ""
        ).strip()

        if not normalized_title:
            raise RakutenKoboManualOfferResolutionError(
                "KOBO_TITLE_REQUIRED_FOR_OFFICIAL_LOOKUP"
            )

        (
            normalized_input_url,
            input_host,
            input_path,
        ) = _normalized_product_identity(
            product_url
        )

        items = fetch_official_kobo_items_by_title(
            normalized_title,
            transport=self.transport,
        )

        if not items:
            # KOBO_OFFICIAL_PRODUCT_PAGE_FALLBACK_V1
            try:
                return _resolve_official_product_page(
                    requested_title=normalized_title,
                    product_url=normalized_input_url,
                    entered_price=entered_price,
                )
            except RakutenKoboManualOfferResolutionError:
                raise RakutenKoboManualOfferResolutionError(
                    "KOBO_OFFICIAL_ITEM_NOT_FOUND"
                )

        matched: dict[str, Any] | None = None
        official_url = ""

        for item in items:
            raw_item_url = str(
                item.get("itemUrl")
                or ""
            ).strip()

            if not raw_item_url:
                continue

            try:
                (
                    normalized_api_url,
                    api_host,
                    api_path,
                ) = _normalized_product_identity(
                    raw_item_url
                )
            except RakutenKoboManualOfferResolutionError:
                continue

            # Query strings such as ?l-id=... are intentionally ignored.
            # The official API item URL must bind to the same Kobo /rk/ path.
            if (
                api_host == input_host
                and api_path == input_path
            ):
                matched = item
                official_url = (
                    normalized_api_url
                )
                break

        if matched is None:
            # KOBO_OFFICIAL_PRODUCT_PAGE_FALLBACK_V1
            #
            # Title search may lag behind a newly published/available
            # Rakuten Books Kobo product page.  The human-confirmed exact
            # product URL is therefore used as a second official source,
            # but only when title + 13-digit item number + price bind
            # unambiguously on that page.
            try:
                return _resolve_official_product_page(
                    requested_title=normalized_title,
                    product_url=normalized_input_url,
                    entered_price=entered_price,
                )
            except RakutenKoboManualOfferResolutionError:
                raise RakutenKoboManualOfferResolutionError(
                    "KOBO_OFFICIAL_PRODUCT_URL_MISMATCH"
                )

        item_number = str(
            matched.get("itemNumber")
            or ""
        ).strip()

        if not re.fullmatch(
            r"[0-9]{13}",
            item_number,
        ):
            raise RakutenKoboManualOfferResolutionError(
                "KOBO_OFFICIAL_ITEM_NUMBER_INVALID"
            )

        official_price = _official_price_yen(
            matched.get("itemPrice")
        )

        manual_price = _entered_price_yen(
            entered_price
        )

        if (
            manual_price is not None
            and manual_price
            != official_price
        ):
            raise RakutenKoboManualOfferResolutionError(
                "KOBO_OFFICIAL_PRICE_MISMATCH"
            )

        return RakutenKoboManualOfferResolution(
            item_number=item_number,
            item_price_yen=official_price,
            # Keep the human-confirmed normalized input URL.
            # Affiliate URL generation may already be bound to this URL.
            product_url=normalized_input_url,
            official_product_url=official_url,
            provider_title=str(
                matched.get("title")
                or ""
            ).strip(),
            author_name=(
                _optional_author_name(
                    matched.get("author")
                )
            ),
            publisher_name=(
                _optional_publisher_name(
                    matched.get("publisherName")
                )
            ),
        )
