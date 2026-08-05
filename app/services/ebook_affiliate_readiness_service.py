from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlsplit

from app.services.amazon_manual_link_service import ASIN_PATTERN
from app.services.dmm_affiliate_html_parser import (
    DmmAffiliateHtmlParseError,
    parse_dmm_affiliate_html,
    parse_dmm_affiliate_url,
)
from app.services.store_url_policy import STORE_AFFILIATE_HOSTS


_PLACEHOLDER_TOKENS = {
    "dummy",
    "example",
    "na",
    "none",
    "notset",
    "null",
    "placeholder",
    "sample",
    "tbd",
    "test",
    "undefined",
    "unknown",
}


@dataclass(frozen=True)
class EbookAffiliateReadiness:
    amazon_affiliate_ready: bool
    rakuten_kobo_affiliate_ready: bool
    dmm_affiliate_ready: bool
    affiliate_ready_count: int


class _SingleAffiliateAnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchor_count = 0
        self.href = ""
        self.has_unsafe_element = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style", "iframe", "object"}:
            self.has_unsafe_element = True
        if normalized_tag != "a":
            return
        self.anchor_count += 1
        if self.anchor_count == 1:
            attributes = {name.lower(): value or "" for name, value in attrs}
            self.href = attributes.get("href", "").strip()


def _value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _is_placeholder(value: Any) -> bool:
    normalized = str(value or "").strip().casefold()
    if not normalized:
        return True
    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    return (
        compact in _PLACEHOLDER_TOKENS
        or any(token in compact for token in ("placeholder", "dummy", "unknown"))
    )


def _single_anchor_href(value: str) -> str:
    parser = _SingleAffiliateAnchorParser()
    try:
        parser.feed(value)
        parser.close()
    except (TypeError, ValueError):
        return ""
    if (
        parser.anchor_count != 1
        or not parser.href
        or parser.has_unsafe_element
    ):
        return ""
    return parser.href


def _url_or_anchor_href(value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized or _is_placeholder(normalized):
        return ""
    if "<" in normalized or ">" in normalized:
        return _single_anchor_href(normalized)
    return normalized


def _valid_https_url(value: str, *, allowed_hosts: set[str]) -> bool:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").casefold() in allowed_hosts
        and parsed.username is None
        and parsed.password is None
        and port is None
        and not _is_placeholder(value)
    )


def _valid_asin(value: Any) -> bool:
    normalized = str(value or "").strip().upper()
    if not ASIN_PATTERN.fullmatch(normalized):
        return False
    if _is_placeholder(normalized) or len(set(normalized)) == 1:
        return False
    return True


def _valid_amazon_affiliate_url(value: Any) -> bool:
    url = _url_or_anchor_href(value)
    if not _valid_https_url(
        url, allowed_hosts={"amazon.co.jp", "www.amazon.co.jp"}
    ):
        return False
    parsed = urlsplit(url)
    path_match = re.search(
        r"/(?:dp|gp/product)/([A-Za-z0-9]{10})(?:/|$)", parsed.path
    )
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return (
        path_match is not None
        and _valid_asin(path_match.group(1))
        and not _is_placeholder(query.get("tag"))
    )


def _amazon_offer_ready(offer: Any) -> bool:
    if _valid_asin(_value(offer, "store_item_id")):
        return True
    verified = (
        bool(str(_value(offer, "verification_method") or "").strip())
        and _value(offer, "verified_at") is not None
        and str(_value(offer, "availability_status") or "").strip().upper()
        == "FOUND_CONFIRMED"
    )
    return verified and _valid_amazon_affiliate_url(
        _value(offer, "affiliate_url")
    )


def _rakuten_offer_ready(offer: Any) -> bool:
    url = _url_or_anchor_href(_value(offer, "affiliate_url"))
    if not _valid_https_url(
        url,
        allowed_hosts=set(STORE_AFFILIATE_HOSTS["rakuten_kobo"]),
    ):
        return False
    parsed = urlsplit(url)
    return bool(parsed.path.strip("/") or parsed.query)


def is_dmm_affiliate_value_ready(value: Any) -> bool:
    normalized = str(value or "").strip()
    if not normalized or _is_placeholder(normalized):
        return False
    try:
        if "<" in normalized or ">" in normalized:
            parse_dmm_affiliate_html(normalized)
        else:
            parse_dmm_affiliate_url(normalized)
    except (DmmAffiliateHtmlParseError, TypeError, ValueError):
        return False
    return True


def affiliate_url_registration_status(
    value: Any,
    *,
    store_name: str,
) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "missing"
    try:
        parsed = urlsplit(normalized)
        port = parsed.port
    except (TypeError, ValueError):
        return "invalid"
    allowed_hosts = STORE_AFFILIATE_HOSTS.get(store_name, frozenset())
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold().rstrip(".")
        not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        return "invalid"
    return "registered"


def affiliate_store_registration_state(
    offers: Iterable[Any],
    *,
    store_name: str,
) -> str:
    statuses = [
        affiliate_url_registration_status(
            _value(offer, "affiliate_url"),
            store_name=store_name,
        )
        for offer in offers
        if str(_value(offer, "store_name") or "").strip().casefold()
        == store_name
    ]
    if "registered" in statuses:
        return "registered"
    if "invalid" in statuses:
        return "invalid"
    return "unregistered"


def build_ebook_affiliate_readiness(
    offers: Iterable[Any],
    *,
    affiliate_urls_by_offer_id: Mapping[str, Iterable[str]] | None = None,
) -> EbookAffiliateReadiness:
    ready = {
        "amazon": False,
        "rakuten_kobo": False,
        "dmm": False,
    }
    offer_list = list(offers)
    for store_name in ready:
        ready[store_name] = affiliate_store_registration_state(
            offer_list,
            store_name=store_name,
        ) == "registered"

    count = sum(ready.values())
    return EbookAffiliateReadiness(
        amazon_affiliate_ready=ready["amazon"],
        rakuten_kobo_affiliate_ready=ready["rakuten_kobo"],
        dmm_affiliate_ready=ready["dmm"],
        affiliate_ready_count=count,
    )
