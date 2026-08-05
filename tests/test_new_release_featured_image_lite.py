from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
    WordPressMediaResponse,
)
from app.services.new_release_featured_image_lite import (
    NewReleaseFeaturedImageError,
    NewReleaseFeaturedImageInput,
    attach_featured_image_to_new_release_draft,
)
from app.services.x_r15_public_cover_source import (
    X15PublicCover,
)
from scripts.run_x_r13_wordpress_draft_creation_once import (
    execute_x_r13_wordpress_draft_once,
)


def build_item(**overrides):
    values = {
        "id": "e2029b2f-f44a-462f-abc8-86c4bc74b818",
        "source_item_id": "4310000887411",
        "title": "メダリスト",
        "volume_label": "第15巻",
        "author_name": "つるまいかだ",
        "publisher_name": "講談社",
        "release_date": date(2026, 7, 22),
        "item_type": "tankobon",
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "wordpress_status": "DRAFT",
        "wordpress_post_id": "777",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def build_offer(**overrides):
    values = {
        "store_name": "RAKUTEN_KOBO",
        "store_item_id": "4310000887411",
        "affiliate_url": "https://example.test/affiliate",
        "product_url": "https://books.rakuten.co.jp/rk/example/",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def build_cover() -> X15PublicCover:
    return X15PublicCover(
        page_url="https://books.rakuten.co.jp/rk/example/",
        image_url="https://tshop.r10s.jp/example/cover.jpg",
        content_type="image/jpeg",
        content=b"\xff\xd8" + (b"\x00" * 1200) + b"\xff\xd9",
        sha256="a" * 64,
        width=300,
        height=426,
        image_format="JPEG",
    )


class FakeImageClient:
    def __init__(self, *, live_status: str = "draft") -> None:
        self.live_status = live_status
        self.get_calls = []
        self.upload_calls = []
        self.update_calls = []
        self.publish_calls = 0

    def get_draft(self, *, post_id):
        self.get_calls.append(post_id)
        return WordPressDraftResponse(
            post_id=post_id,
            status=self.live_status,
            link=f"https://example.test/?p={post_id}",
        )

    def upload_media(self, *, filename, content_type, content):
        self.upload_calls.append(
            {
                "filename": filename,
                "content_type": content_type,
                "content": content,
            }
        )
        return WordPressMediaResponse(
            media_id=321,
            source_url="https://example.test/uploads/cover.jpg",
            mime_type="image/jpeg",
        )

    def update_draft(self, *, post_id, payload):
        self.update_calls.append(
            {
                "post_id": post_id,
                "payload": payload,
            }
        )
        return WordPressDraftResponse(
            post_id=post_id,
            status="draft",
            link=f"https://example.test/?p={post_id}",
        )

    def publish(self):
        self.publish_calls += 1


def build_input(**overrides) -> NewReleaseFeaturedImageInput:
    values = {
        "ebook_item_id": "e2029b2f-f44a-462f-abc8-86c4bc74b818",
        "source_item_id": "4310000887411",
        "wordpress_post_id": 777,
        "product_page_url": "https://books.rakuten.co.jp/rk/example/",
        "filename": "4310000887411.jpg",
        "item": build_item(),
        "offer": build_offer(),
    }
    values.update(overrides)
    return NewReleaseFeaturedImageInput(**values)


def test_attach_featured_image_happy_path() -> None:
    client = FakeImageClient()
    fetch_calls = []

    def cover_fetcher(**kwargs):
        fetch_calls.append(kwargs)
        return build_cover()

    result = attach_featured_image_to_new_release_draft(
        input_data=build_input(),
        client=client,
        cover_fetcher=cover_fetcher,
    )

    assert result.status == "ATTACHED"
    assert result.media_id == 321
    assert result.media_url == "https://example.test/uploads/cover.jpg"
    assert result.featured_media_set is True
    assert result.content_updated is True
    assert result.publish_executed is False
    assert client.get_calls == [777]
    assert len(fetch_calls) == 1
    assert len(client.upload_calls) == 1
    assert len(client.update_calls) == 1
    assert client.update_calls[0]["payload"]["featured_media"] == 321
    assert "status" not in client.update_calls[0]["payload"]
    assert client.publish_calls == 0


def test_non_draft_live_post_stops_before_cover_fetch() -> None:
    client = FakeImageClient(live_status="publish")
    fetch_calls = []

    with pytest.raises(
        NewReleaseFeaturedImageError,
        match="WordPress live post must remain draft",
    ):
        attach_featured_image_to_new_release_draft(
            input_data=build_input(),
            client=client,
            cover_fetcher=lambda **kwargs: fetch_calls.append(kwargs),
        )

    assert client.get_calls == [777]
    assert fetch_calls == []
    assert client.upload_calls == []
    assert client.update_calls == []


def test_empty_product_page_skips_without_external_calls() -> None:
    client = FakeImageClient()

    result = attach_featured_image_to_new_release_draft(
        input_data=build_input(product_page_url=""),
        client=client,
        cover_fetcher=lambda **kwargs: build_cover(),
    )

    assert result.status == "SKIPPED_NO_COVER_SOURCE"
    assert result.media_id is None
    assert result.featured_media_set is False
    assert result.content_updated is False
    assert client.get_calls == []
    assert client.upload_calls == []
    assert client.update_calls == []


def test_invalid_post_id_is_rejected() -> None:
    with pytest.raises(
        NewReleaseFeaturedImageError,
        match="wordpress_post_id must be a positive integer",
    ):
        attach_featured_image_to_new_release_draft(
            input_data=build_input(wordpress_post_id=0),
            client=FakeImageClient(),
            cover_fetcher=lambda **kwargs: build_cover(),
        )


def test_upload_failure_does_not_update_draft() -> None:
    client = FakeImageClient()

    def failing_upload(**kwargs):
        raise RuntimeError("upload failed")

    client.upload_media = failing_upload  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="upload failed"):
        attach_featured_image_to_new_release_draft(
            input_data=build_input(),
            client=client,
            cover_fetcher=lambda **kwargs: build_cover(),
        )

    assert client.get_calls == [777]
    assert client.update_calls == []


def test_update_failure_does_not_reupload_or_publish() -> None:
    client = FakeImageClient()

    def failing_update(*, post_id, payload):
        client.update_calls.append(
            {"post_id": post_id, "payload": payload}
        )
        raise RuntimeError("update failed")

    client.update_draft = failing_update  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="update failed"):
        attach_featured_image_to_new_release_draft(
            input_data=build_input(),
            client=client,
            cover_fetcher=lambda **kwargs: build_cover(),
        )

    assert len(client.upload_calls) == 1
    assert len(client.update_calls) == 1
    assert client.publish_calls == 0


class FakeDraftCreationClient:
    def __init__(self) -> None:
        self.create_payloads = []
        self.get_calls = []
        self.upload_calls = []
        self.update_calls = []

    def create_draft(self, payload):
        self.create_payloads.append(payload)
        return WordPressDraftResponse(
            post_id=777,
            status="draft",
            link="https://example.test/?p=777",
        )

    def get_draft(self, *, post_id):
        self.get_calls.append(post_id)
        return WordPressDraftResponse(
            post_id=post_id,
            status="draft",
            link=f"https://example.test/?p={post_id}",
        )

    def upload_media(self, *, filename, content_type, content):
        self.upload_calls.append(filename)
        return WordPressMediaResponse(
            media_id=222,
            source_url="https://example.test/uploads/runner.jpg",
            mime_type="image/jpeg",
        )

    def update_draft(self, *, post_id, payload):
        self.update_calls.append(payload)
        return WordPressDraftResponse(
            post_id=post_id,
            status="draft",
            link=f"https://example.test/?p={post_id}",
        )


class FakeStateRepository:
    def mark_wordpress_draft_created(
        self,
        item,
        post_id,
        *,
        changed_by,
        note="",
    ):
        item.wordpress_post_id = str(post_id)
        item.wordpress_status = "DRAFT"
        return True


def build_request(**overrides):
    values = {
        "status": "APPROVED",
        "approval_type": "REVIEW_READY",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_x_r13_runner_keeps_backward_compatible_success_without_cover_source() -> None:
    item = build_item(
        wordpress_status="NOT_CREATED",
        wordpress_post_id=None,
    )
    offer = build_offer(product_url="")
    client = FakeDraftCreationClient()
    events = []

    result = execute_x_r13_wordpress_draft_once(
        item=item,
        approval_request=build_request(),
        offer=offer,
        client=client,
        state_repository=FakeStateRepository(),
        commit=lambda: events.append("commit"),
        rollback=lambda: events.append("rollback"),
        cover_fetcher=lambda **kwargs: build_cover(),
    )

    assert result.post_id == 777
    assert result.status == "draft"
    assert result.committed is True
    assert result.image_status == "SKIPPED_NO_COVER_SOURCE"
    assert result.image_media_id is None
    assert result.featured_media_set is False
    assert events == ["commit"]
    assert client.get_calls == []
    assert client.upload_calls == []
    assert client.update_calls == []


def test_x_r13_runner_returns_review_required_on_image_failure() -> None:
    item = build_item(
        wordpress_status="NOT_CREATED",
        wordpress_post_id=None,
    )
    offer = build_offer()
    client = FakeDraftCreationClient()
    events = []

    def failing_upload(*, filename, content_type, content):
        client.upload_calls.append(filename)
        raise RuntimeError("media upload exploded")

    client.upload_media = failing_upload  # type: ignore[method-assign]

    result = execute_x_r13_wordpress_draft_once(
        item=item,
        approval_request=build_request(),
        offer=offer,
        client=client,
        state_repository=FakeStateRepository(),
        commit=lambda: events.append("commit"),
        rollback=lambda: events.append("rollback"),
        cover_fetcher=lambda **kwargs: build_cover(),
    )

    assert result.post_id == 777
    assert result.committed is True
    assert result.image_status == "REVIEW_REQUIRED"
    assert "RuntimeError" in str(result.image_error_summary)
    assert item.wordpress_post_id == "777"
    assert item.wordpress_status == "DRAFT"
    assert events == ["commit"]
    assert client.get_calls == [777]
    assert len(client.upload_calls) == 1
    assert client.update_calls == []