from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.integrations.wordpress_rest_client import WordPressDraftResponse
from app.services.wordpress_existing_draft_store_buttons_update import (
    ExistingDraftStoreButtonsUpdateError,
    TARGET_EBOOK_ITEM_ID,
    update_existing_draft_store_buttons,
)


BLOG_URL = "https://al.dmm.com/?af_id=wordpress-blog-main"
X_URL = "https://al.dmm.com/?af_id=x-main"


def make_item(**overrides):
    values = {
        "id": TARGET_EBOOK_ITEM_ID,
        "wordpress_status": "DRAFT",
        "wordpress_post_id": "207",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_offer(store_name: str, **overrides):
    values = {
        "id": f"offer-{store_name}",
        "store_name": store_name,
        "store_item_id": f"item-{store_name}",
        "affiliate_url": {
            "amazon": "https://www.amazon.co.jp/dp/example?tag=secret",
            "rakuten_kobo": "https://hb.afl.rakuten.co.jp/hgc/secret/",
            "dmm": "https://al.dmm.com/?af_id=legacy",
        }[store_name],
        "product_url": {
            "amazon": "https://www.amazon.co.jp/dp/example",
            "rakuten_kobo": "https://books.rakuten.co.jp/rk/example/",
            "dmm": "https://book.dmm.com/product/example/",
        }[store_name],
        "price_yen": 244,
        "price_amount": 244,
        "currency": "JPY",
        "availability_status": "FOUND_CONFIRMED",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_offers():
    return [
        make_offer("dmm"),
        make_offer("amazon"),
        make_offer("rakuten_kobo"),
    ]


def make_content(blocks: int = 1, *, dmm_href: str = BLOG_URL) -> str:
    old_block = (
        '<div class="legacy store-buttons">'
        "<h3>購入先</h3>"
        '<p><a href="https://www.amazon.co.jp/old">Amazon</a></p>'
        '<p><a href="https://books.rakuten.co.jp/old">楽天Kobo</a></p>'
        f'<p><a href="{dmm_href}">DMMブックス</a></p>'
        "</div>"
    )
    return (
        '<article><p class="ebook-pr-disclosure">【PR】広告を含みます。</p>'
        '<img class="ebook-cover-image" src="https://example.test/cover.jpg" '
        'alt="書影">'
        '<p class="ebook-unified-price">244円（税込）</p>'
        + old_block * blocks
        + '<p class="unchanged-tail">著者・出版社・発売日</p></article>'
    )


class FakeWordPressClient:
    def __init__(
        self,
        *,
        content: str | None = None,
        before_post_id: int = 207,
        before_status: str = "draft",
        before_featured_media: int = 208,
        after_status: str = "draft",
        after_featured_media: int = 208,
    ) -> None:
        self.current = WordPressDraftResponse(
            post_id=before_post_id,
            status=before_status,
            title="既存タイトル",
            content=content if content is not None else make_content(),
            excerpt="既存抜粋",
            featured_media=before_featured_media,
        )
        self.after_status = after_status
        self.after_featured_media = after_featured_media
        self.get_calls = []
        self.update_calls = []
        self.create_calls = []
        self.upload_calls = []

    def get_draft(self, *, post_id):
        self.get_calls.append(post_id)
        return deepcopy(self.current)

    def update_draft(self, *, post_id, payload):
        self.update_calls.append((post_id, deepcopy(payload)))
        self.current = WordPressDraftResponse(
            post_id=post_id,
            status=self.after_status,
            title=self.current.title,
            content=payload["content"],
            excerpt=self.current.excerpt,
            featured_media=self.after_featured_media,
        )
        return WordPressDraftResponse(
            post_id=post_id,
            status="draft",
        )

    def create_draft(self, payload):
        self.create_calls.append(payload)
        raise AssertionError("create_draft must not be called")

    def upload_media(self, **kwargs):
        self.upload_calls.append(kwargs)
        raise AssertionError("upload_media must not be called")


def run_update(
    tmp_path: Path,
    *,
    client: FakeWordPressClient | None = None,
    item=None,
    offers=None,
    execute: bool = False,
    confirm=207,
):
    client = client or FakeWordPressClient()
    result = update_existing_draft_store_buttons(
        ebook_item_id=TARGET_EBOOK_ITEM_ID,
        wordpress_post_id=207,
        confirm_wordpress_post_id=confirm,
        execute=execute,
        item=item or make_item(),
        offers=offers or make_offers(),
        wordpress_client=client,
        dmm_wordpress_link_resolver=lambda offer: BLOG_URL,
        dmm_x_link_resolver=lambda offer: X_URL,
        diagnostic_path=tmp_path / "diagnostic.html",
        evidence_directory=tmp_path / "evidence",
    )
    return result, client


def test_dry_run_does_not_update_and_writes_local_diagnostic(tmp_path):
    result, client = run_update(tmp_path)

    assert result.status == "DRY_RUN_READY"
    assert result.replacement_count == 1
    assert result.before_content_sha256 != result.after_content_sha256
    assert result.store_names == ("amazon", "rakuten_kobo", "dmm")
    assert result.store_labels == (
        "Amazon Kindleで見る",
        "楽天Koboで見る",
        "DMMブックスで見る",
    )
    assert client.update_calls == []
    assert client.create_calls == []
    assert client.upload_calls == []
    diagnostic = (tmp_path / "diagnostic.html").read_text(encoding="utf-8")
    assert diagnostic.count("ebook-store-button") == 6
    assert not (tmp_path / "evidence").exists()


def test_live_replaces_only_block_and_uses_minimal_payload(tmp_path):
    before = make_content()
    client = FakeWordPressClient(content=before)
    result, client = run_update(tmp_path, client=client, execute=True)

    assert result.status == "UPDATED_AND_VERIFIED"
    assert result.verified_after_update is True
    assert len(client.update_calls) == 1
    post_id, payload = client.update_calls[0]
    assert post_id == 207
    assert set(payload) == {"content", "status"}
    assert payload["status"] == "draft"
    content = payload["content"]
    assert content.index('data-store="amazon"') < content.index(
        'data-store="rakuten_kobo"'
    ) < content.index('data-store="dmm"')
    assert content.count('<a class="ebook-store-button ') == 3
    assert content.count('target="_blank"') == 3
    assert content.count('rel="sponsored nofollow noopener"') == 3
    assert BLOG_URL.replace("&", "&amp;") in content
    assert "x-main" not in content
    assert "<h3>購入先</h3>" not in content
    for retained in (
        "【PR】広告を含みます。",
        "ebook-cover-image",
        "244円（税込）",
        "著者・出版社・発売日",
    ):
        assert retained in content
    assert client.current.title == "既存タイトル"
    assert client.current.featured_media == 208
    assert client.create_calls == []
    assert client.upload_calls == []
    assert result.evidence_path is not None


def test_db_text_post_id_is_normalized(tmp_path):
    result, _ = run_update(
        tmp_path,
        item=make_item(wordpress_post_id=" 207 "),
    )
    assert result.wordpress_post_id == 207


@pytest.mark.parametrize(
    ("item", "code"),
    [
        (make_item(wordpress_status="PUBLISHED"), "db_wordpress_status_mismatch"),
        (make_item(wordpress_post_id="205"), "db_wordpress_post_id_mismatch"),
        (make_item(wordpress_post_id="not-an-int"), "invalid_wordpress_post_id"),
    ],
)
def test_invalid_database_preconditions_abort_without_update(
    tmp_path, item, code
):
    client = FakeWordPressClient()
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        run_update(tmp_path, client=client, item=item)
    assert exc_info.value.code == code
    assert client.update_calls == []


@pytest.mark.parametrize("blocks", [0, 2])
def test_store_buttons_count_must_be_exactly_one(tmp_path, blocks):
    client = FakeWordPressClient(content=make_content(blocks))
    with pytest.raises(
        ExistingDraftStoreButtonsUpdateError,
        match="exactly one store-buttons",
    ):
        run_update(tmp_path, client=client)
    assert client.update_calls == []


@pytest.mark.parametrize(
    ("client", "code"),
    [
        (FakeWordPressClient(before_post_id=205), "wordpress_post_id_mismatch"),
        (FakeWordPressClient(before_status="publish"), "wordpress_status_mismatch"),
        (FakeWordPressClient(before_featured_media=999), "featured_media_mismatch"),
    ],
)
def test_wordpress_preconditions_abort_without_update(tmp_path, client, code):
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        run_update(tmp_path, client=client)
    assert exc_info.value.code == code
    assert client.update_calls == []


def test_missing_store_aborts_without_update(tmp_path):
    client = FakeWordPressClient()
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        run_update(tmp_path, client=client, offers=make_offers()[:2])
    assert exc_info.value.code == "required_store_missing"
    assert client.update_calls == []


def test_dmm_x_main_in_existing_body_aborts(tmp_path):
    client = FakeWordPressClient(content=make_content(dmm_href=X_URL))
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        run_update(tmp_path, client=client)
    assert exc_info.value.code == "dmm_x_main_used"
    assert client.update_calls == []


@pytest.mark.parametrize(
    ("after_status", "after_media", "code"),
    [
        ("publish", 208, "post_update_status_mismatch"),
        ("draft", 999, "post_update_featured_media_mismatch"),
    ],
)
def test_post_update_verification_failure_is_not_success(
    tmp_path, after_status, after_media, code
):
    client = FakeWordPressClient(
        after_status=after_status,
        after_featured_media=after_media,
    )
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        run_update(tmp_path, client=client, execute=True)
    assert exc_info.value.code == code
    assert len(client.update_calls) == 1
    assert not (tmp_path / "evidence").exists()


def test_live_confirmation_is_required_before_get_or_update(tmp_path):
    client = FakeWordPressClient()
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        run_update(tmp_path, client=client, execute=True, confirm=None)
    assert exc_info.value.code == "live_confirmation_missing"
    assert client.get_calls == []
    assert client.update_calls == []


def test_live_confirmation_must_match_before_get_or_update(tmp_path):
    client = FakeWordPressClient()
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        run_update(tmp_path, client=client, execute=True, confirm=205)
    assert exc_info.value.code == "live_confirmation_mismatch"
    assert client.get_calls == []
    assert client.update_calls == []
