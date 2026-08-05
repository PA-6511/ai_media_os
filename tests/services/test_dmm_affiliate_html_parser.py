from __future__ import annotations

import pytest

from app.services.dmm_affiliate_html_parser import (
    DmmAffiliateHtmlParseError,
    parse_dmm_affiliate_html,
    parse_dmm_input,
)


PRODUCT_NAME = "悪役をやめたら義弟に溺愛されました3【電子限定特典付き】"
AFFILIATE_URL = (
    "https://al.dmm.com/?lurl=https%3A%2F%2Fbook.dmm.com%2Fproduct%2F"
    "4493998%2Fb000fhftx08481%2F&af_id=xuanyilugang-008&ch=toolbar&ch_id=text"
)
HTML = f'<a href="{AFFILIATE_URL}" rel="sponsored">{PRODUCT_NAME}</a>'


def test_parse_valid_dmm_books_affiliate_html() -> None:
    result = parse_dmm_affiliate_html(HTML)

    assert result.product_name == PRODUCT_NAME
    assert result.affiliate_id == "xuanyilugang-008"
    assert result.product_group_id == "4493998"
    assert result.product_id == "b000fhftx08481"
    assert result.product_url == (
        "https://book.dmm.com/product/4493998/b000fhftx08481/"
    )
    assert result.affiliate_url == AFFILIATE_URL
    assert result.service == "book"
    assert result.channel == "toolbar"
    assert result.channel_id == "text"
    assert result.warnings == ()


def test_parse_html_entity_ampersands() -> None:
    result = parse_dmm_affiliate_html(HTML.replace("&", "&amp;"))

    assert result.affiliate_id == "xuanyilugang-008"
    assert result.channel == "toolbar"
    assert result.affiliate_url == AFFILIATE_URL


def test_parse_normal_dmm_books_product_url() -> None:
    result = parse_dmm_input(
        "https://book.dmm.com/product/group_1/item-2/"
    )

    assert result.product_group_id == "group_1"
    assert result.product_id == "item-2"
    assert result.source_type == "product_url"


def test_missing_sponsored_is_warning_not_parse_failure() -> None:
    result = parse_dmm_affiliate_html(HTML.replace(' rel="sponsored"', ""))

    assert result.warnings == ("rel_sponsored_missing",)


@pytest.mark.parametrize(
    "lurl",
    [
        "https://www.dmm.com/mono/hobby/-/detail/=/cid=test/",
        "https://video.dmm.com/example/",
        "https://games.dmm.com/example/",
        "https://evil.example/product/4493998/b000fhftx08481/",
        "http://book.dmm.com/product/4493998/b000fhftx08481/",
        "javascript:alert(1)",
        "data:text/html,test",
        "/product/4493998/b000fhftx08481/",
    ],
)
def test_reject_unsafe_lurl(lurl: str) -> None:
    from urllib.parse import quote

    unsafe = (
        '<a href="https://al.dmm.com/?lurl='
        f'{quote(lurl, safe="")}&af_id=xuanyilugang-008">作品</a>'
    )
    with pytest.raises(DmmAffiliateHtmlParseError):
        parse_dmm_affiliate_html(unsafe)


def test_reject_non_dmm_outer_host() -> None:
    with pytest.raises(DmmAffiliateHtmlParseError, match="affiliate_host"):
        parse_dmm_affiliate_html(
            HTML.replace("https://al.dmm.com/", "https://example.com/")
        )


def test_reject_javascript_input() -> None:
    with pytest.raises(DmmAffiliateHtmlParseError):
        parse_dmm_input("javascript:alert(1)")


def test_reject_javascript_affiliate_href() -> None:
    with pytest.raises(DmmAffiliateHtmlParseError, match="affiliate_host"):
        parse_dmm_affiliate_html('<a href="javascript:alert(1)">作品</a>')


def test_require_lurl() -> None:
    with pytest.raises(DmmAffiliateHtmlParseError, match="lurl_required"):
        parse_dmm_affiliate_html(
            '<a href="https://al.dmm.com/?af_id=xuanyilugang-008">作品</a>'
        )


def test_reject_multiple_anchors() -> None:
    with pytest.raises(DmmAffiliateHtmlParseError, match="single_anchor"):
        parse_dmm_affiliate_html(HTML + HTML)


@pytest.mark.parametrize(
    "path",
    [
        "/product/group%2Fescape/item/",
        "/product/group/item.dot/",
        "/product/group/item/extra/",
        "/product/group/item",
    ],
)
def test_reject_unsafe_or_noncanonical_product_path(path: str) -> None:
    with pytest.raises(DmmAffiliateHtmlParseError):
        parse_dmm_input(f"https://book.dmm.com{path}")
