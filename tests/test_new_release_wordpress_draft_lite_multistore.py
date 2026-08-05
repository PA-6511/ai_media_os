from __future__ import annotations

from html.parser import HTMLParser
import re
from types import SimpleNamespace

import pytest

from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
    WordPressMediaResponse,
)
from app.services.new_release_wordpress_draft_lite import (
    NEW_RELEASE_POST_META_KEY,
    STORE_AFFILIATE_META_KEYS,
    STORE_BUTTON_STYLES,
    NewReleaseWordPressDraftLiteError,
    _build_draft_payload,
    build_wordpress_store_offers,
    create_new_release_wordpress_draft_lite,
)


class StoreButtonsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.group_attrs = {}
        self.buttons = []
        self._in_group = False
        self._current_button = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if tag == "div" and "store-buttons" in classes:
            self._in_group = True
            self.group_attrs = attributes
        elif self._in_group and tag == "a":
            self._current_button = {
                "attrs": attributes,
                "text": "",
            }

    def handle_data(self, data):
        if self._current_button is not None:
            self._current_button["text"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._current_button is not None:
            self._current_button["text"] = self._current_button[
                "text"
            ].strip()
            self.buttons.append(self._current_button)
            self._current_button = None
        elif tag == "div" and self._in_group:
            self._in_group = False


def parse_store_buttons(content):
    parser = StoreButtonsParser()
    parser.feed(content)
    return parser.group_attrs, parser.buttons


def style_properties(style):
    return {
        name: value
        for declaration in style.split(";")
        if declaration
        for name, value in [declaration.split(":", 1)]
    }


def item(**overrides):
    values = {
        "id": "ebook-1",
        "source_item_id": "source-1",
        "title": "作品名 3",
        "volume_label": "第3巻",
        "author_name": "著者",
        "publisher_name": "出版社",
        "release_date": "2026-08-01",
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "wordpress_post_id": None,
        "wordpress_status": "NOT_CREATED",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def offer(store_name, **overrides):
    defaults = {
        "amazon": {
            "id": "offer-amazon",
            "store_item_id": "B012345678",
            "affiliate_url": "https://www.amazon.co.jp/dp/B012345678?tag=test-22",
            "product_url": "https://www.amazon.co.jp/dp/B012345678",
        },
        "rakuten_kobo": {
            "id": "offer-rakuten",
            "store_item_id": "4972000000001",
            "affiliate_url": "https://hb.afl.rakuten.co.jp/hgc/example/",
            "product_url": "https://books.rakuten.co.jp/rk/example/",
        },
        "dmm": {
            "id": "offer-dmm",
            "store_item_id": "b000example",
            "affiliate_url": "https://al.dmm.com/?af_id=x-main",
            "product_url": "https://book.dmm.com/product/123/b000example/",
        },
    }[store_name]
    values = {
        "store_name": store_name,
        "price_yen": 715,
        "price_amount": 715,
        "currency": "JPY",
        "availability_status": "FOUND_CONFIRMED",
        **defaults,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def payload_for(offers):
    payload, price = _build_draft_payload(
        item=item(),
        offers=offers,
        preferred_offer=offers[0],
    )
    return payload, price


def test_three_store_article_is_stable_and_uses_one_unified_price():
    offers = [
        offer("dmm"),
        offer("rakuten_kobo"),
        offer("amazon", price_yen=None, price_amount=None, currency=None),
    ]
    payload, price = payload_for(offers)
    content = payload["content"]
    group_attrs, buttons = parse_store_buttons(content)

    assert [button["attrs"]["data-store"] for button in buttons] == [
        "amazon",
        "rakuten_kobo",
        "dmm",
    ]
    assert [button["text"] for button in buttons] == [
        "Amazon Kindleで見る",
        "楽天Koboで見る",
        "DMMブックスで見る",
    ]
    assert content.count('rel="sponsored nofollow noopener"') == 3
    assert content.count('target="_blank"') == 3
    assert content.count('<a class="ebook-store-button ') == 3
    assert content.count("715円（税込）") == 1
    assert price.status == "PRICE_READY"
    assert price.missing_stores == ("amazon",)
    assert payload["meta"] == {
        NEW_RELEASE_POST_META_KEY: True,
        STORE_AFFILIATE_META_KEYS["amazon"]: offer("amazon").affiliate_url,
        STORE_AFFILIATE_META_KEYS["rakuten_kobo"]: offer("rakuten_kobo").affiliate_url,
        STORE_AFFILIATE_META_KEYS["dmm"]: offer("dmm").affiliate_url,
    }
    assert group_attrs["role"] == "group"
    assert group_attrs["aria-label"] == "電子書籍ストア"
    assert style_properties(group_attrs["style"]) == {
        "display": "grid",
        "gap": "12px",
        "margin-top": "24px",
        "grid-template-columns": "repeat(auto-fit,minmax(220px,1fr))",
    }
    expected_buttons = {
        "amazon": (
            "ebook-store-button--amazon",
            "Amazon Kindleでこの作品を見る",
            "#ffb84d",
            "#1f2937",
        ),
        "rakuten_kobo": (
            "ebook-store-button--rakuten-kobo",
            "楽天Koboでこの作品を見る",
            "#bf0000",
            "#ffffff",
        ),
        "dmm": (
            "ebook-store-button--dmm",
            "DMMブックスでこの作品を見る",
            "#0066cc",
            "#ffffff",
        ),
    }
    common_styles = {
        "display": "flex",
        "align-items": "center",
        "justify-content": "center",
        "min-height": "52px",
        "padding": "12px 18px",
        "border-radius": "8px",
        "font-weight": "700",
        "text-decoration": "none",
        "box-sizing": "border-box",
        "width": "100%",
    }
    for button in buttons:
        attrs = button["attrs"]
        store_name = attrs["data-store"]
        store_class, aria_label, background, color = expected_buttons[
            store_name
        ]
        assert set(attrs["class"].split()) == {
            "ebook-store-button",
            store_class,
        }
        assert attrs["target"] == "_blank"
        assert set(attrs["rel"].split()) == {
            "sponsored",
            "nofollow",
            "noopener",
        }
        assert attrs["aria-label"] == aria_label
        styles = style_properties(attrs["style"])
        assert {name: styles[name] for name in common_styles} == common_styles
        assert styles["background"] == background
        assert styles["color"] == color

    amazon_specific_styles = style_properties(
        STORE_BUTTON_STYLES["amazon"]
    )
    assert not {
        "width",
        "max-width",
        "min-width",
        "flex-basis",
        "display",
        "margin",
        "margin-left",
        "margin-right",
        "padding",
        "padding-left",
        "padding-right",
    } & amazon_specific_styles.keys()

    content_without_buttons = re.sub(r"<a\b[^>]*>.*?</a>", "", content)
    for label in (
        "Amazon Kindleで見る",
        "楽天Koboで見る",
        "DMMブックスで見る",
    ):
        assert label not in content_without_buttons
    assert "ebook-store-card" not in content
    assert "<h3>" not in content
    for class_name in (
        "ebook-new-release-article",
        "ebook-pr-disclosure",
        "ebook-product-layout",
        "ebook-cover-image",
        "ebook-release-metadata",
        "price-cards",
        "store-buttons",
    ):
        assert class_name in content


def test_compact_product_layout_has_desktop_and_mobile_rules():
    payload, _ = payload_for(
        [offer("amazon"), offer("rakuten_kobo"), offer("dmm")]
    )
    content = payload["content"]

    assert '<div class="ebook-product-layout">' in content
    assert ".ebook-new-release-article{max-width:880px;" in content
    assert (
        ".ebook-product-layout{display:grid;"
        "grid-template-columns:minmax(200px,240px) minmax(0,1fr);"
        "gap:24px;align-items:start;}"
    ) in content
    assert (
        ".ebook-release-metadata{display:grid;"
        "grid-template-columns:70px minmax(0,1fr);"
        "column-gap:12px;row-gap:8px;margin:0;}"
    ) in content
    assert "@media (max-width:768px)" in content
    assert (
        ".ebook-product-layout{grid-template-columns:"
        "minmax(92px,32vw) minmax(0,1fr);gap:12px;}"
    ) in content
    assert (
        ".ebook-cover-figure,.ebook-cover-image{"
        "max-width:140px!important;margin:0!important;}"
    ) in content
    assert (
        ".store-buttons{grid-template-columns:minmax(0,1fr)!important;}"
    ) in content


def test_compact_metadata_uses_dt_dd_rows_and_price_card():
    payload, _ = payload_for([offer("rakuten_kobo")])
    content = payload["content"]

    assert '<dl class="ebook-release-metadata">' in content
    for label, value in (
        ("著者", "著者"),
        ("出版社", "出版社"),
        ("発売日", "2026-08-01"),
    ):
        assert f"<dt>{label}</dt>" in content
        assert value in content
    assert '<section class="price-cards" aria-label="価格">' in content
    assert '<p class="ebook-unified-price">715円（税込）</p>' in content


@pytest.mark.parametrize(
    ("store_name", "button_label", "store_class"),
    [
        (
            "amazon",
            "Amazon Kindleで見る",
            "ebook-store-button--amazon",
        ),
        (
            "rakuten_kobo",
            "楽天Koboで見る",
            "ebook-store-button--rakuten-kobo",
        ),
    ],
)
def test_single_store_article(store_name, button_label, store_class):
    payload, price = payload_for([offer(store_name)])
    _group_attrs, buttons = parse_store_buttons(payload["content"])
    assert len(buttons) == 1
    assert buttons[0]["attrs"]["data-store"] == store_name
    assert buttons[0]["text"] == button_label
    assert store_class in buttons[0]["attrs"]["class"].split()
    assert price.price_yen == 715


def test_dmm_uses_resolved_blog_main_and_never_raw_x_link():
    raw = offer(
        "dmm",
        affiliate_url="https://al.dmm.com/?af_id=x-main",
    )
    blog_url = "https://al.dmm.com/?af_id=blog-main"
    prepared = build_wordpress_store_offers(
        [raw],
        dmm_wordpress_link_resolver=lambda candidate: blog_url,
    )
    payload, _ = payload_for(list(prepared))
    _group_attrs, buttons = parse_store_buttons(payload["content"])

    assert blog_url.replace("&", "&amp;") in payload["content"]
    assert "x-main" not in payload["content"]
    assert len(buttons) == 1
    assert buttons[0]["text"] == "DMMブックスで見る"
    assert "ebook-store-button--dmm" in buttons[0]["attrs"][
        "class"
    ].split()


def test_dmm_without_blog_main_is_not_filled_from_x_main():
    prepared = build_wordpress_store_offers(
        [offer("amazon"), offer("dmm")],
        dmm_wordpress_link_resolver=lambda candidate: None,
    )
    payload, _ = payload_for(list(prepared))
    _group_attrs, buttons = parse_store_buttons(payload["content"])
    assert [button["attrs"]["data-store"] for button in buttons] == [
        "amazon"
    ]
    assert "Amazon Kindleで見る" in payload["content"]
    assert "DMMブックスで見る" not in payload["content"]
    assert "ebook-store-button--dmm" not in payload["content"]
    assert "x-main" not in payload["content"]


@pytest.mark.parametrize(
    "bad_url",
    ["http://www.amazon.co.jp/dp/B012345678", "javascript:alert(1)", "/relative"],
)
def test_invalid_affiliate_url_is_rejected(bad_url):
    with pytest.raises(NewReleaseWordPressDraftLiteError, match="HTTPS"):
        payload_for([offer("amazon", affiliate_url=bad_url)])


def test_price_mismatch_requires_review_without_store_prices():
    payload, price = payload_for(
        [
            offer("amazon", price_yen=715, price_amount=715),
            offer("rakuten_kobo", price_yen=720, price_amount=720),
        ]
    )
    assert price.status == "PRICE_REVIEW_REQUIRED"
    assert price.price_yen is None
    assert "store_price_mismatch" in price.review_reasons
    assert "価格は確認中です" in payload["content"]
    assert "715円" not in payload["content"]
    assert "720円" not in payload["content"]


def test_price_fields_mismatch_requires_review():
    _payload, price = payload_for(
        [offer("amazon", price_yen=715, price_amount=700)]
    )
    assert price.status == "PRICE_REVIEW_REQUIRED"
    assert price.review_reasons == ("amazon:price_fields_mismatch",)


def test_post_title_is_preserved_without_duplicate_content_heading():
    source_item = item(
        title="YOUsweet-ユースイート- vol.4（2026年8月号）",
        volume_label="第4巻",
    )
    payload, _ = _build_draft_payload(
        item=source_item,
        offers=[offer("amazon")],
        preferred_offer=offer("amazon"),
    )
    expected_title = "YOUsweet-ユースイート- vol.4（2026年8月号）"
    assert payload["title"] == expected_title
    assert payload["excerpt"] == f"【PR】{expected_title}の発売情報です。"
    assert "<h2" not in payload["content"]
    assert "ebook-release-title" not in payload["content"]
    assert '<p class="ebook-pr-disclosure">' in payload["content"]
    assert '<div class="ebook-product-layout">' in payload["content"]
    assert '<div class="ebook-cover-image ebook-cover-placeholder"' in payload["content"]
    for label in ("著者", "出版社", "発売日"):
        assert f"<dt>{label}</dt>" in payload["content"]
    assert '<section class="price-cards" aria-label="価格">' in payload["content"]
    assert "第4巻" not in payload["title"]
    assert "第4巻" not in payload["content"]
    assert source_item.volume_label == "第4巻"


def test_title_does_not_duplicate_equivalent_volume_number():
    payload, _ = _build_draft_payload(
        item=item(title="作品名 ３", volume_label="第3巻"),
        offers=[offer("amazon")],
        preferred_offer=offer("amazon"),
    )

    assert payload["title"] == "作品名 ３"
    assert "３ 第3巻" not in payload["content"]


def test_cover_url_renders_image_without_placeholder():
    cover_url = "https://thumbnail.image.rakuten.co.jp/example/cover.jpg"
    payload, _ = _build_draft_payload(
        item=item(),
        offers=[offer("rakuten_kobo")],
        preferred_offer=offer("rakuten_kobo"),
        cover_image_url=cover_url,
    )

    assert '<img class="ebook-cover-image"' in payload["content"]
    assert f'src="{cover_url}"' in payload["content"]
    assert 'max-width:320px;margin:1.5rem auto' in payload["content"]
    assert "書影は確認中です" not in payload["content"]


def test_missing_cover_url_renders_placeholder():
    payload, _ = _build_draft_payload(
        item=item(),
        offers=[offer("rakuten_kobo")],
        preferred_offer=offer("rakuten_kobo"),
    )

    assert '<img class="ebook-cover-image"' not in payload["content"]
    assert "書影は確認中です" in payload["content"]


class FakeStateRepository:
    def __init__(self):
        self.wordpress_calls = []
        self.image_calls = []

    def mark_wordpress_draft_created(self, item, post_id, **kwargs):
        self.wordpress_calls.append(post_id)

    def set_image_status(self, item, status, **kwargs):
        self.image_calls.append(status)


class FakeWordPressClient:
    def __init__(self, post_id=321):
        self.post_id = post_id
        self.create_calls = []
        self.update_calls = []

    def create_draft(self, payload):
        self.create_calls.append(payload)
        return SimpleNamespace(
            post_id=self.post_id,
            status="draft",
            link="https://wordpress.test/?p=321",
        )

    def get_draft(self, *, post_id):
        return WordPressDraftResponse(post_id=post_id, status="draft")

    def upload_media(self, **kwargs):
        return WordPressMediaResponse(
            media_id=44,
            source_url="https://wordpress.test/uploads/cover.jpg",
            mime_type="image/jpeg",
        )

    def update_draft(self, *, post_id, payload):
        self.update_calls.append(payload)
        return WordPressDraftResponse(post_id=post_id, status="draft")


def run_create(client, *, cover_fetcher):
    repository = FakeStateRepository()
    result = create_new_release_wordpress_draft_lite(
        ebook_item_id="ebook-1",
        item=item(),
        offers=[offer("amazon"), offer("rakuten_kobo")],
        preferred_offer=offer("amazon"),
        wordpress_client=client,
        state_repository=repository,
        commit=lambda: None,
        rollback=lambda: None,
        cover_fetcher=cover_fetcher,
    )
    return result, repository


def test_cover_success_sets_body_image_and_featured_media():
    client = FakeWordPressClient()
    cover_calls = []

    def cover_fetcher(**kwargs):
        cover_calls.append(kwargs)
        return SimpleNamespace(
            image_url="https://thumbnail.image.rakuten.co.jp/example/cover.jpg",
            content_type="image/jpeg",
            content=b"jpeg",
        )

    result, repository = run_create(client, cover_fetcher=cover_fetcher)

    assert len(client.create_calls) == 1
    assert client.create_calls[0]["meta"] == {
        NEW_RELEASE_POST_META_KEY: True,
        "kindle_url": offer("amazon").affiliate_url,
        "rakuten_kobo_url": offer("rakuten_kobo").affiliate_url,
    }
    assert cover_calls[0]["page_url"] == "https://books.rakuten.co.jp/rk/example/"
    assert "https://thumbnail.image.rakuten.co.jp/example/cover.jpg" in client.create_calls[0]["content"]
    assert "書影は確認中です" not in client.create_calls[0]["content"]
    assert client.update_calls[0]["featured_media"] == 44
    assert '<img class="ebook-cover-image"' in client.update_calls[0]["content"]
    assert "https://wordpress.test/uploads/cover.jpg" in client.update_calls[0]["content"]
    assert result.image_status == "ATTACHED"
    assert result.featured_media_set is True
    assert repository.image_calls == ["READY"]


def test_cover_failure_keeps_draft_and_records_reason():
    client = FakeWordPressClient()

    def cover_fetcher(**kwargs):
        raise RuntimeError("cover failed")

    result, repository = run_create(client, cover_fetcher=cover_fetcher)

    assert len(client.create_calls) == 1
    assert "書影は確認中です" in client.create_calls[0]["content"]
    assert '<img class="ebook-cover-image"' not in client.create_calls[0]["content"]
    assert result.wordpress_status == "DRAFT"
    assert result.image_status == "REVIEW_REQUIRED"
    assert "cover failed" in result.image_error_summary
    assert result.featured_media_set is False
    assert repository.image_calls == ["REVIEW"]


@pytest.mark.parametrize("post_id", [None, 0, -1, "321", True])
def test_draft_without_positive_integer_post_id_is_not_success(post_id):
    client = FakeWordPressClient(post_id=post_id)
    with pytest.raises(
        NewReleaseWordPressDraftLiteError,
        match="positive integer",
    ):
        run_create(client, cover_fetcher=lambda **kwargs: None)
    assert len(client.create_calls) == 1
