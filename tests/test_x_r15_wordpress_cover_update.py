from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
    WordPressMediaResponse,
)
from app.services.x_r15_public_cover_source import (
    X15PublicCover,
)
from app.services.x_r15_wordpress_cover_update import (
    X15WordPressCoverUpdateError,
    execute_x_r15_wordpress_cover_update_once,
)


def build_item(**overrides):
    values = {
        "id": (
            "e2029b2f-f44a-462f-abc8-86c4bc74b818"
        ),
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
        "wordpress_post_id": "201",
        "x_status": "NOT_CREATED",
    }

    values.update(overrides)

    return SimpleNamespace(**values)


def build_offer():
    return SimpleNamespace(
        store_name="RAKUTEN_KOBO",
        store_item_id="4310000887411",
        affiliate_url=(
            "https://example.test/affiliate"
        ),
    )


def build_cover() -> X15PublicCover:
    return X15PublicCover(
        page_url=(
            "https://books.rakuten.co.jp/rk/example/"
        ),
        image_url=(
            "https://tshop.r10s.jp/example/cover.jpg"
        ),
        content_type="image/jpeg",
        content=(
            b"\xff\xd8"
            + (b"\x00" * 1200)
            + b"\xff\xd9"
        ),
        sha256="a" * 64,
        width=600,
        height=800,
        image_format="JPEG",
    )


class FakeClient:
    def __init__(self) -> None:
        self.preflight_calls = []
        self.upload_calls = []
        self.update_calls = []

    def get_draft(
        self,
        *,
        post_id,
    ):
        self.preflight_calls.append(post_id)

        return WordPressDraftResponse(
            post_id=201,
            status="draft",
            link="https://hoshido.jp/?p=201",
        )

    def upload_media(
        self,
        *,
        filename,
        content_type,
        content,
    ):
        self.upload_calls.append(
            {
                "filename": filename,
                "content_type": content_type,
                "content": content,
            }
        )

        return WordPressMediaResponse(
            media_id=321,
            source_url=(
                "https://hoshido.jp/"
                "wp-content/uploads/cover.jpg"
            ),
            mime_type="image/jpeg",
        )

    def update_draft(
        self,
        *,
        post_id,
        payload,
    ):
        self.update_calls.append(
            {
                "post_id": post_id,
                "payload": payload,
            }
        )

        return WordPressDraftResponse(
            post_id=201,
            status="draft",
            link="https://hoshido.jp/?p=201",
        )


def test_uploads_cover_and_updates_draft() -> None:
    client = FakeClient()
    fetch_calls = []

    def cover_fetcher(**kwargs):
        assert client.preflight_calls == [201]
        assert client.upload_calls == []
        assert client.update_calls == []

        fetch_calls.append(kwargs)
        return build_cover()

    result = execute_x_r15_wordpress_cover_update_once(
        item=build_item(),
        offer=build_offer(),
        client=client,
        cover_fetcher=cover_fetcher,
    )

    assert result.post_id == 201
    assert result.post_status == "draft"
    assert result.media_id == 321
    assert result.featured_media_set is True
    assert result.content_updated is True
    assert result.publish_executed is False

    assert client.preflight_calls == [201]
    assert len(fetch_calls) == 1
    assert len(client.upload_calls) == 1
    assert len(client.update_calls) == 1

    update = client.update_calls[0]

    assert update["post_id"] == 201
    assert update["payload"]["featured_media"] == 321
    assert (
        "ebook-cover-image"
        in update["payload"]["content"]
    )
    assert (
        "https://hoshido.jp/"
        "wp-content/uploads/cover.jpg"
        in update["payload"]["content"]
    )
    assert update["payload"].get("status") is None


def test_wrong_post_blocks_all_transport() -> None:
    client = FakeClient()
    fetch_calls = []

    def cover_fetcher(**kwargs):
        fetch_calls.append(kwargs)
        return build_cover()

    with pytest.raises(
        X15WordPressCoverUpdateError,
        match="wordpress_post_id must be 201",
    ):
        execute_x_r15_wordpress_cover_update_once(
            item=build_item(
                wordpress_post_id="999"
            ),
            offer=build_offer(),
            client=client,
            cover_fetcher=cover_fetcher,
        )

    assert fetch_calls == []
    assert client.upload_calls == []
    assert client.update_calls == []



def test_update_failure_after_media_upload_exposes_reconciliation_evidence(
) -> None:
    from datetime import date
    from types import SimpleNamespace

    import pytest

    from app.services.x_r15_wordpress_cover_update import (
        X15WordPressCoverPartialFailure,
        execute_x_r15_wordpress_cover_update_once,
    )

    class FailingClient:
        def get_draft(
            self,
            *,
            post_id,
        ):
            return WordPressDraftResponse(
                post_id=201,
                status="draft",
                link="https://hoshido.jp/?p=201",
            )

        def upload_media(
            self,
            *,
            filename,
            content_type,
            content,
        ):
            return SimpleNamespace(
                media_id=321,
                source_url=(
                    "https://hoshido.jp/"
                    "wp-content/uploads/"
                    "medalist-15.jpg"
                ),
                mime_type="image/jpeg",
            )

        def update_draft(
            self,
            *,
            post_id,
            payload,
        ):
            raise RuntimeError(
                "simulated draft update failure"
            )

    item = SimpleNamespace(
        id=(
            "e2029b2f-f44a-462f-"
            "abc8-86c4bc74b818"
        ),
        source_item_id="4310000887411",
        workflow_status="READY",
        review_status="APPROVED",
        publish_ready=False,
        wordpress_status="DRAFT",
        wordpress_post_id="201",
        x_status="NOT_CREATED",
        title="メダリスト",
        volume_label="第15巻",
        author_name="つるまいかだ",
        publisher_name="講談社",
        release_date=date(2026, 7, 22),
        item_type="tankobon",
    )

    offer = SimpleNamespace(
        store_name="RAKUTEN_KOBO",
        store_item_id="4310000887411",
        affiliate_url=(
            "https://example.test/affiliate"
        ),
    )

    cover = SimpleNamespace(
        content_type="image/jpeg",
        content=b"jpeg-test-content",
        sha256="a" * 64,
        width=300,
        height=426,
    )

    with pytest.raises(
        X15WordPressCoverPartialFailure
    ) as caught:
        execute_x_r15_wordpress_cover_update_once(
            item=item,
            offer=offer,
            client=FailingClient(),
            cover_fetcher=lambda **kwargs: cover,
        )

    failure = caught.value

    assert failure.media_id == 321
    assert failure.media_url.endswith(
        "/medalist-15.jpg"
    )
    assert failure.image_sha256 == "a" * 64
    assert failure.failure_stage == (
        "AFTER_MEDIA_UPLOAD_BEFORE_"
        "DRAFT_UPDATE_CONFIRMED"
    )
    assert failure.original_error_type == (
        "RuntimeError"
    )



def test_non_draft_live_preflight_blocks_cover_fetch_and_all_writes(
) -> None:
    client = FakeClient()
    fetch_calls = []

    def non_draft_preflight(
        *,
        post_id,
    ):
        client.preflight_calls.append(post_id)

        return WordPressDraftResponse(
            post_id=201,
            status="publish",
            link="https://hoshido.jp/?p=201",
        )

    client.get_draft = non_draft_preflight

    def cover_fetcher(**kwargs):
        fetch_calls.append(kwargs)
        return build_cover()

    with pytest.raises(
        X15WordPressCoverUpdateError,
        match="live post must remain draft",
    ):
        execute_x_r15_wordpress_cover_update_once(
            item=build_item(),
            offer=build_offer(),
            client=client,
            cover_fetcher=cover_fetcher,
        )

    assert client.preflight_calls == [201]
    assert fetch_calls == []
    assert client.upload_calls == []
    assert client.update_calls == []
