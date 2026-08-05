from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import parse_qsl, urlsplit


SAFE_PRODUCT_COMPONENT = re.compile(r"^[A-Za-z0-9_-]+$")
PRODUCT_PATH = re.compile(
    r"^/product/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)/$"
)


class DmmAffiliateHtmlParseError(ValueError):
    """Raised when an input is not a safe DMM Books URL or affiliate anchor."""


@dataclass(frozen=True)
class DmmAffiliateParseResult:
    source_type: str
    product_name: str
    affiliate_id: str
    product_group_id: str
    product_id: str
    product_url: str
    affiliate_url: str
    service: str
    channel: str
    channel_id: str
    warnings: tuple[str, ...] = ()


class _SingleAnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchor_count = 0
        self.anchor_depth = 0
        self.href = ""
        self.rel_tokens: set[str] = set()
        self.text_parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() != "a":
            return
        self.anchor_count += 1
        self.anchor_depth += 1
        if self.anchor_count != 1:
            return
        attributes = {name.lower(): value or "" for name, value in attrs}
        self.href = attributes.get("href", "").strip()
        self.rel_tokens = {
            token.lower() for token in attributes.get("rel", "").split()
        }

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.anchor_depth:
            self.anchor_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.anchor_depth == 1 and self.anchor_count == 1:
            self.text_parts.append(data)


def _query_values(url: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for name, value in parse_qsl(
        urlsplit(url).query, keep_blank_values=True
    ):
        values.setdefault(name, []).append(value)
    return values


def _one_query_value(
    values: dict[str, list[str]], name: str, *, required: bool = False
) -> str:
    matches = values.get(name, [])
    if len(matches) > 1:
        raise DmmAffiliateHtmlParseError(f"duplicate_{name}")
    value = matches[0].strip() if matches else ""
    if required and not value:
        raise DmmAffiliateHtmlParseError(f"{name}_required")
    return value


def _parse_product_url(url: str) -> tuple[str, str, str]:
    normalized = url.strip()
    parsed = urlsplit(normalized)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "book.dmm.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise DmmAffiliateHtmlParseError("invalid_dmm_books_url")
    match = PRODUCT_PATH.fullmatch(parsed.path)
    if match is None:
        raise DmmAffiliateHtmlParseError("invalid_dmm_books_product_path")
    product_group_id, product_id = match.groups()
    if not (
        SAFE_PRODUCT_COMPONENT.fullmatch(product_group_id)
        and SAFE_PRODUCT_COMPONENT.fullmatch(product_id)
    ):
        raise DmmAffiliateHtmlParseError("unsafe_product_identifier")
    canonical = (
        f"https://book.dmm.com/product/{product_group_id}/{product_id}/"
    )
    return product_group_id, product_id, canonical


def parse_dmm_product_url(value: str) -> DmmAffiliateParseResult:
    product_group_id, product_id, product_url = _parse_product_url(value)
    return DmmAffiliateParseResult(
        source_type="product_url",
        product_name="",
        affiliate_id="",
        product_group_id=product_group_id,
        product_id=product_id,
        product_url=product_url,
        affiliate_url="",
        service="book",
        channel="",
        channel_id="",
    )


def parse_dmm_affiliate_url(value: str) -> DmmAffiliateParseResult:
    normalized = value.strip()
    outer = urlsplit(normalized)
    if (
        outer.scheme != "https"
        or outer.hostname != "al.dmm.com"
        or outer.username is not None
        or outer.password is not None
        or outer.port is not None
    ):
        raise DmmAffiliateHtmlParseError("invalid_affiliate_host")

    query = _query_values(normalized)
    product_group_id, product_id, product_url = _parse_product_url(
        _one_query_value(query, "lurl", required=True)
    )
    return DmmAffiliateParseResult(
        source_type="affiliate_url",
        product_name="",
        affiliate_id=_one_query_value(query, "af_id", required=True),
        product_group_id=product_group_id,
        product_id=product_id,
        product_url=product_url,
        affiliate_url=normalized,
        service="book",
        channel=_one_query_value(query, "ch"),
        channel_id=_one_query_value(query, "ch_id"),
    )


def parse_dmm_affiliate_html(value: str) -> DmmAffiliateParseResult:
    parser = _SingleAnchorParser()
    try:
        parser.feed(value.strip())
        parser.close()
    except (ValueError, TypeError) as exc:
        raise DmmAffiliateHtmlParseError("invalid_html") from exc
    if parser.anchor_count != 1:
        raise DmmAffiliateHtmlParseError("single_anchor_required")
    if not parser.href:
        raise DmmAffiliateHtmlParseError("affiliate_href_required")

    outer = urlsplit(parser.href)
    if (
        outer.scheme != "https"
        or outer.hostname != "al.dmm.com"
        or outer.username is not None
        or outer.password is not None
        or outer.port is not None
    ):
        raise DmmAffiliateHtmlParseError("invalid_affiliate_host")

    query = _query_values(parser.href)
    product_group_id, product_id, product_url = _parse_product_url(
        _one_query_value(query, "lurl", required=True)
    )
    product_name = re.sub(r"\s+", " ", "".join(parser.text_parts)).strip()
    warnings: list[str] = []
    if "sponsored" not in parser.rel_tokens:
        warnings.append("rel_sponsored_missing")

    return DmmAffiliateParseResult(
        source_type="affiliate_html",
        product_name=product_name,
        affiliate_id=_one_query_value(query, "af_id", required=True),
        product_group_id=product_group_id,
        product_id=product_id,
        product_url=product_url,
        affiliate_url=parser.href,
        service="book",
        channel=_one_query_value(query, "ch"),
        channel_id=_one_query_value(query, "ch_id"),
        warnings=tuple(warnings),
    )


def parse_dmm_input(value: str) -> DmmAffiliateParseResult:
    normalized = value.strip()
    if not normalized:
        raise DmmAffiliateHtmlParseError("input_required")
    if "<" in normalized or ">" in normalized:
        return parse_dmm_affiliate_html(normalized)
    return parse_dmm_product_url(normalized)
