from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit


STORE_PRODUCT_HOSTS = {
    "rakuten_kobo": frozenset({"books.rakuten.co.jp"}),
    "amazon": frozenset({"amazon.co.jp", "www.amazon.co.jp"}),
    "dmm": frozenset({"book.dmm.com"}),
}

STORE_AFFILIATE_HOSTS = {
    "rakuten_kobo": frozenset({"hb.afl.rakuten.co.jp", "a.r10.to"}),
    "amazon": frozenset({"amazon.co.jp", "www.amazon.co.jp"}),
    "dmm": frozenset({"al.dmm.com"}),
}

STORE_WORDPRESS_LINK_HOSTS = {
    store_name: STORE_PRODUCT_HOSTS[store_name] | STORE_AFFILIATE_HOSTS[store_name]
    for store_name in STORE_PRODUCT_HOSTS
}

_PLACEHOLDER_HOSTS = frozenset({
    "example.com",
    "www.example.com",
    "example.net",
    "www.example.net",
    "example.org",
    "www.example.org",
})
_PLACEHOLDER_TOKENS = re.compile(
    r"(?:^|[^a-z0-9])(dummy|example|placeholder|sample|test|unknown)(?:[^a-z0-9]|$)",
    re.IGNORECASE,
)
_CONTROL_OR_WHITESPACE = re.compile(r"[\x00-\x20\x7f]")
_RAW_HTML_OR_QUOTE = re.compile(r"[<>\"']")
_MAX_URL_LENGTH = 2048
_SHORTENER_HOSTS = frozenset({
    "amzn.to",
    "a.co",
    "bit.ly",
    "tinyurl.com",
    "x.gd",
})


class StoreUrlPolicyError(ValueError):
    pass


def _product_path_allowed(store_name: str, path: str) -> bool:
    if store_name == "amazon":
        return bool(
            re.search(
                r"/(?:dp|gp/product)/[A-Za-z0-9]{10}(?:/|$)",
                path,
            )
        )
    if store_name == "rakuten_kobo":
        return bool(
            re.search(
                r"/(?:rk|e-book)/[A-Za-z0-9_-]{6,255}/?",
                path,
                re.IGNORECASE,
            )
        )
    if store_name == "dmm":
        return bool(
            re.fullmatch(
                r"/product/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/",
                path,
                re.IGNORECASE,
            )
        )
    raise StoreUrlPolicyError("STORE_NOT_SUPPORTED")


def _product_query_allowed(store_name: str, query: str) -> bool:
    if not query:
        return True
    values = parse_qs(query, keep_blank_values=True)
    if "tag" in values or "af_id" in values or "lurl" in values:
        return False
    if store_name == "rakuten_kobo":
        return True
    if store_name == "dmm":
        return False
    return store_name == "amazon"


def normalize_store_url(
    value: str,
    *,
    store_name: str,
    purpose: str,
    required: bool,
) -> str | None:
    raw_value = str(value or "")
    normalized = raw_value.strip()
    if not normalized:
        if required:
            raise StoreUrlPolicyError("AFFILIATE_URL_REQUIRED")
        return None
    if _RAW_HTML_OR_QUOTE.search(normalized):
        raise StoreUrlPolicyError("URL_HTML_FRAGMENT_FORBIDDEN")
    if len(normalized) > _MAX_URL_LENGTH or _CONTROL_OR_WHITESPACE.search(
        normalized
    ):
        raise StoreUrlPolicyError("URL_INVALID")
    try:
        parsed = urlsplit(normalized)
        port = parsed.port
    except ValueError as exc:
        raise StoreUrlPolicyError("URL_INVALID") from exc
    scheme = parsed.scheme.casefold()
    if purpose == "product":
        if scheme not in {"http", "https"}:
            raise StoreUrlPolicyError("URL_HTTP_REQUIRED")
    elif scheme != "https":
        raise StoreUrlPolicyError("URL_HTTPS_REQUIRED")
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise StoreUrlPolicyError("URL_INVALID")
    host = parsed.hostname.casefold().rstrip(".")
    if host in _SHORTENER_HOSTS:
        raise StoreUrlPolicyError("URL_SHORTENER_FORBIDDEN")
    path_and_query = (
        parsed.path
        if purpose == "product"
        else f"{parsed.path}?{parsed.query}"
    )
    if host in _PLACEHOLDER_HOSTS or _PLACEHOLDER_TOKENS.search(path_and_query):
        raise StoreUrlPolicyError("URL_PLACEHOLDER_FORBIDDEN")
    allowed_by_purpose = {
        "product": STORE_PRODUCT_HOSTS,
        "affiliate": STORE_AFFILIATE_HOSTS,
    }
    try:
        allowed_hosts = allowed_by_purpose[purpose][store_name]
    except KeyError as exc:
        raise StoreUrlPolicyError("STORE_NOT_SUPPORTED") from exc
    if (
        purpose == "product"
        and host in STORE_AFFILIATE_HOSTS.get(store_name, frozenset())
        and host not in STORE_PRODUCT_HOSTS.get(store_name, frozenset())
    ):
        raise StoreUrlPolicyError("URL_AFFILIATE_URL_NOT_PRODUCT")
    if host not in allowed_hosts:
        raise StoreUrlPolicyError("URL_HOST_NOT_ALLOWED")
    if not parsed.path.strip("/") and not parsed.query:
        raise StoreUrlPolicyError("URL_PATH_REQUIRED")
    if purpose == "product":
        if not _product_path_allowed(store_name, parsed.path):
            raise StoreUrlPolicyError("URL_PRODUCT_TYPE_NOT_ALLOWED")
        if not _product_query_allowed(store_name, parsed.query):
            raise StoreUrlPolicyError("URL_AFFILIATE_URL_NOT_PRODUCT")
    if store_name == "dmm" and purpose == "affiliate":
        destination = (parse_qs(parsed.query).get("lurl") or [""])[0]
        if destination:
            destination_url = urlsplit(unquote(destination))
            if (
                destination_url.scheme != "https"
                or destination_url.hostname != "book.dmm.com"
            ):
                raise StoreUrlPolicyError("URL_PRODUCT_TYPE_NOT_ALLOWED")
    query = parsed.query
    if store_name == "rakuten_kobo" and purpose == "product":
        query = ""
    if store_name == "dmm" and purpose == "product":
        query = ""
    return urlunsplit(("https", host, parsed.path, query, ""))


def store_item_id_from_url(value: str | None, *, store_name: str) -> str | None:
    """Extract a product identifier only when the URL has a known store shape."""
    if not value:
        return None
    parsed = urlsplit(value)
    decoded = unquote(value)
    if store_name == "amazon":
        match = re.search(
            r"/(?:dp|gp/product)/([A-Za-z0-9]{10})(?:[/?]|$)",
            parsed.path + ("?" + parsed.query if parsed.query else ""),
        )
        return match.group(1).upper() if match else None
    if store_name == "rakuten_kobo":
        match = re.search(
            r"/(?:rk|e-book)/([A-Za-z0-9_-]{6,255})(?:[/?]|$)",
            decoded,
            re.IGNORECASE,
        )
        return match.group(1) if match else None
    if store_name == "dmm":
        match = re.search(
            r"/(?:detail|digital/-/detail/=/cid=)/([A-Za-z0-9_-]{3,255})(?:[/?]|$)",
            decoded,
            re.IGNORECASE,
        )
        return match.group(1) if match else None
    raise StoreUrlPolicyError("STORE_NOT_SUPPORTED")
