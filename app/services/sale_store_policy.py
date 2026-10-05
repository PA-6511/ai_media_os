from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import parse_qs, urlsplit


class SaleStorePolicyError(ValueError):
    """A fail-closed Sale store-boundary validation error."""


_CANONICAL_STORES = frozenset({"rakuten_kobo", "dmm", "amazon"})

_STORE_ALIASES = {
    "rakuten_kobo": "rakuten_kobo",
    "rakuten": "rakuten_kobo",
    "kobo": "rakuten_kobo",
    "dmm": "dmm",
    "dmm_books": "dmm",
    "amazon": "amazon",
    "amazon_kindle": "amazon",
    "kindle": "amazon",
}

_DISPLAY_NAMES = {
    "rakuten_kobo": "楽天Kobo",
    "dmm": "DMMブックス",
    "amazon": "Amazon Kindle",
}

_PRODUCT_HOSTS = {
    "rakuten_kobo": frozenset({"books.rakuten.co.jp"}),
    "dmm": frozenset({"book.dmm.com"}),
    "amazon": frozenset({"amazon.co.jp", "www.amazon.co.jp"}),
}

_AFFILIATE_HOSTS = {
    "rakuten_kobo": frozenset({"hb.afl.rakuten.co.jp", "a.r10.to"}),
    "dmm": frozenset({"al.dmm.com"}),
    "amazon": frozenset({"amazon.co.jp", "www.amazon.co.jp"}),
}

_COVER_HOSTS = {
    "rakuten_kobo": frozenset({"thumbnail.image.rakuten.co.jp"}),
    "dmm": frozenset({"pics.dmm.com", "ebook-assets.dmm.com"}),
    "amazon": frozenset({"m.media-amazon.com"}),
}

_TRUSTED_VERIFICATION_SOURCES = frozenset(
    {
        "trusted_affiliate_generator",
        "store_url_policy_verified",
        "trusted_store_producer",
    }
)
_CONTROL_OR_WHITESPACE = re.compile(r"[\x00-\x20\x7f]")
_RAW_HTML_OR_QUOTE = re.compile(r"[<>\"']")
_MALFORMED_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_AMAZON_PRODUCT_PATH = re.compile(
    r"/(?:dp|gp/product)/[A-Za-z0-9]{10}(?:/|$)", re.IGNORECASE
)
_RAKUTEN_PRODUCT_PATH = re.compile(
    r"/(?:rk|e-book)/[A-Za-z0-9_-]{6,255}/?", re.IGNORECASE
)
_DMM_PRODUCT_PATH = re.compile(
    r"/product/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/", re.IGNORECASE
)
_MAX_URL_LENGTH = 2048


def normalize_sale_store(value: object) -> str | None:
    """Normalize a store identifier at a Sale input boundary."""
    if not isinstance(value, str):
        return None
    return _STORE_ALIASES.get(value.strip().casefold())


def require_canonical_sale_store(value: object) -> str:
    """Require an already-canonical store identifier at a consumer boundary."""
    if not isinstance(value, str) or value not in _CANONICAL_STORES:
        raise SaleStorePolicyError("NON_CANONICAL_SALE_STORE")
    return value


def sale_store_display_name(canonical_store: object) -> str:
    return _DISPLAY_NAMES[require_canonical_sale_store(canonical_store)]


def allowed_product_hosts(canonical_store: object) -> frozenset[str]:
    return _PRODUCT_HOSTS[require_canonical_sale_store(canonical_store)]


def allowed_affiliate_hosts(canonical_store: object) -> frozenset[str]:
    return _AFFILIATE_HOSTS[require_canonical_sale_store(canonical_store)]


def allowed_cover_hosts(canonical_store: object) -> frozenset[str]:
    return _COVER_HOSTS[require_canonical_sale_store(canonical_store)]


def _parse_https_url(url: object):
    if not isinstance(url, str) or not url or url != url.strip():
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    if (
        len(url) > _MAX_URL_LENGTH
        or _CONTROL_OR_WHITESPACE.search(url)
        or _RAW_HTML_OR_QUOTE.search(url)
        or _MALFORMED_PERCENT_ESCAPE.search(url)
    ):
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION") from exc
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
    ):
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    host = parsed.hostname.casefold()
    if host.endswith("."):
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    return parsed, host


def _require_host(host: str, allowed_hosts: frozenset[str]) -> None:
    if host not in allowed_hosts:
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")


def validate_sale_product_url(canonical_store: object, url: object) -> str:
    store = require_canonical_sale_store(canonical_store)
    parsed, host = _parse_https_url(url)
    _require_host(host, allowed_product_hosts(store))

    path_allowed = {
        "rakuten_kobo": _RAKUTEN_PRODUCT_PATH.search,
        "dmm": _DMM_PRODUCT_PATH.fullmatch,
        "amazon": _AMAZON_PRODUCT_PATH.search,
    }[store]
    if not path_allowed(parsed.path):
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")

    query = parse_qs(parsed.query, keep_blank_values=True)
    if {"tag", "af_id", "lurl"} & query.keys():
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    if store == "dmm" and parsed.query:
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    return url


def _validate_structured_evidence(
    canonical_store: str, affiliate_url: str, evidence: object
) -> None:
    if not isinstance(evidence, Mapping):
        raise SaleStorePolicyError("SALE_STORE_REVIEW_REQUIRED")
    if (
        evidence.get("canonical_store") != canonical_store
        or evidence.get("affiliate_url") != affiliate_url
        or evidence.get("verification_source")
        not in _TRUSTED_VERIFICATION_SOURCES
        or not isinstance(evidence.get("producer"), str)
        or not evidence["producer"].strip()
    ):
        raise SaleStorePolicyError("SALE_STORE_REVIEW_REQUIRED")


def _single_embedded_destination(parsed, parameter: str) -> str | None:
    values = parse_qs(parsed.query, keep_blank_values=True).get(parameter)
    if values is None:
        return None
    if len(values) != 1 or not values[0]:
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    return values[0]


def validate_sale_affiliate_url(
    canonical_store: object, url: object, evidence: object = None
) -> str:
    store = require_canonical_sale_store(canonical_store)
    parsed, host = _parse_https_url(url)
    _require_host(host, allowed_affiliate_hosts(store))

    destination_parameter = {
        "rakuten_kobo": "pc",
        "dmm": "lurl",
        "amazon": None,
    }[store]
    if destination_parameter is not None:
        destination = _single_embedded_destination(parsed, destination_parameter)
        if destination is not None:
            try:
                validate_sale_product_url(store, destination)
            except SaleStorePolicyError as exc:
                raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION") from exc
            return url

        _validate_structured_evidence(store, url, evidence)
        return url

    if not _AMAZON_PRODUCT_PATH.search(parsed.path):
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    return url


def validate_sale_cover_url(canonical_store: object, url: object) -> str:
    store = require_canonical_sale_store(canonical_store)
    parsed, host = _parse_https_url(url)
    _require_host(host, allowed_cover_hosts(store))
    if not parsed.path.strip("/"):
        raise SaleStorePolicyError("SALE_URL_POLICY_VIOLATION")
    return url


def sale_store_gate_reasons(
    campaign_store: object, offer: object
) -> list[str]:
    normalized_campaign_store = normalize_sale_store(campaign_store)
    if normalized_campaign_store is None:
        return ["SALE_STORE_REVIEW_REQUIRED"]
    if not isinstance(offer, Mapping):
        return ["SALE_STORE_MISMATCH"]
    normalized_offer_store = normalize_sale_store(offer.get("store_name"))
    if normalized_offer_store != normalized_campaign_store:
        return ["SALE_STORE_MISMATCH"]
    return []


def validate_sale_snapshot_store(snapshot: object) -> str:
    """Validate the strict, single-store contract at a Sale consumer boundary."""
    if not isinstance(snapshot, Mapping):
        raise SaleStorePolicyError("SALE_STORE_SNAPSHOT_INVALID")
    campaign_store = require_canonical_sale_store(snapshot.get("campaign_store"))
    items = snapshot.get("items")
    if not isinstance(items, (list, tuple)):
        raise SaleStorePolicyError("SALE_STORE_SNAPSHOT_INVALID")

    for item in items:
        if not isinstance(item, Mapping):
            raise SaleStorePolicyError("SALE_STORE_SNAPSHOT_INVALID")
        item_store = require_canonical_sale_store(item.get("store_name"))
        if item_store != campaign_store:
            raise SaleStorePolicyError("SALE_STORE_MISMATCH")
        validate_sale_product_url(campaign_store, item.get("product_url"))
        validate_sale_affiliate_url(
            campaign_store,
            item.get("affiliate_url"),
            item.get("affiliate_evidence"),
        )
        validate_sale_cover_url(campaign_store, item.get("cover_image_url"))
    return campaign_store


__all__ = [
    "SaleStorePolicyError",
    "allowed_affiliate_hosts",
    "allowed_cover_hosts",
    "allowed_product_hosts",
    "normalize_sale_store",
    "require_canonical_sale_store",
    "sale_store_display_name",
    "sale_store_gate_reasons",
    "validate_sale_affiliate_url",
    "validate_sale_cover_url",
    "validate_sale_product_url",
    "validate_sale_snapshot_store",
]
