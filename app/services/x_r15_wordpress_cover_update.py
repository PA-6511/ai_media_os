from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.services.x_r13_wordpress_draft_payload_adapter import (
    X13WordPressDraftInput,
    build_x_r13_wordpress_draft_payload,
)
from app.services.x_r15_public_cover_source import (
    X15PublicCover,
    fetch_x15_public_cover,
)


X_R15_EBOOK_ITEM_ID = (
    "e2029b2f-f44a-462f-abc8-86c4bc74b818"
)

X_R15_SOURCE_ITEM_ID = "4310000887411"
X_R15_WORDPRESS_POST_ID = 201

X_R15_PRODUCT_PAGE_URL = (
    "https://books.rakuten.co.jp/rk/"
    "a4c432a967ca32a4ae2331dd5c4cd8a8/"
)


class X15WordPressCoverUpdateError(RuntimeError):
    pass


class X15WordPressCoverPartialFailure(
    X15WordPressCoverUpdateError
):
    def __init__(
        self,
        message: str,
        *,
        media_id: int,
        media_url: str,
        image_sha256: str,
        failure_stage: str,
        original_error_type: str,
    ) -> None:
        super().__init__(message)
        self.media_id = media_id
        self.media_url = media_url
        self.image_sha256 = image_sha256
        self.failure_stage = failure_stage
        self.original_error_type = original_error_type


@dataclass(frozen=True)
class X15WordPressCoverUpdateResult:
    ebook_item_id: str
    source_item_id: str
    post_id: int
    post_status: str
    media_id: int
    media_url: str
    image_sha256: str
    image_width: int
    image_height: int
    featured_media_set: bool
    content_updated: bool
    publish_executed: bool


def _value(source: Any, name: str) -> Any:
    if isinstance(source, dict):
        return source.get(name)

    return getattr(source, name)


def _required(
    value: Any,
    field_name: str,
) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise X15WordPressCoverUpdateError(
            f"{field_name} is required"
        )

    return normalized


def execute_x_r15_wordpress_cover_update_once(
    *,
    item: Any,
    offer: Any,
    client: Any,
    cover_fetcher: Callable[..., X15PublicCover] = (
        fetch_x15_public_cover
    ),
) -> X15WordPressCoverUpdateResult:
    ebook_item_id = _required(
        _value(item, "id"),
        "ebook_item_id",
    )

    source_item_id = _required(
        _value(item, "source_item_id"),
        "source_item_id",
    )

    if ebook_item_id != X_R15_EBOOK_ITEM_ID:
        raise X15WordPressCoverUpdateError(
            "ebook item does not match X-R15"
        )

    if source_item_id != X_R15_SOURCE_ITEM_ID:
        raise X15WordPressCoverUpdateError(
            "source item does not match X-R15"
        )

    if _value(item, "workflow_status") != "READY":
        raise X15WordPressCoverUpdateError(
            "workflow_status must be READY"
        )

    if _value(item, "review_status") != "APPROVED":
        raise X15WordPressCoverUpdateError(
            "review_status must be APPROVED"
        )

    if bool(_value(item, "publish_ready")):
        raise X15WordPressCoverUpdateError(
            "publish_ready must remain false"
        )

    if _value(item, "wordpress_status") != "DRAFT":
        raise X15WordPressCoverUpdateError(
            "wordpress_status must be DRAFT"
        )

    wordpress_post_id = _required(
        _value(item, "wordpress_post_id"),
        "wordpress_post_id",
    )

    if wordpress_post_id != str(
        X_R15_WORDPRESS_POST_ID
    ):
        raise X15WordPressCoverUpdateError(
            "wordpress_post_id must be 201"
        )

    if _value(item, "x_status") != "NOT_CREATED":
        raise X15WordPressCoverUpdateError(
            "x_status must remain NOT_CREATED"
        )

    store_name = _required(
        _value(offer, "store_name"),
        "store_name",
    ).upper()

    if store_name != "RAKUTEN_KOBO":
        raise X15WordPressCoverUpdateError(
            "store_name must be RAKUTEN_KOBO"
        )

    store_item_id = _required(
        _value(offer, "store_item_id"),
        "store_item_id",
    )

    if store_item_id != X_R15_SOURCE_ITEM_ID:
        raise X15WordPressCoverUpdateError(
            "store_item_id does not match X-R15"
        )

    affiliate_url = _required(
        _value(offer, "affiliate_url"),
        "affiliate_url",
    )

    if not affiliate_url.startswith("https://"):
        raise X15WordPressCoverUpdateError(
            "affiliate_url must use HTTPS"
        )

    live_post = client.get_draft(
        post_id=X_R15_WORDPRESS_POST_ID,
    )

    if live_post.post_id != X_R15_WORDPRESS_POST_ID:
        raise X15WordPressCoverUpdateError(
            "WordPress live post ID mismatch"
        )

    if live_post.status != "draft":
        raise X15WordPressCoverUpdateError(
            "WordPress live post must remain draft"
        )

    cover = cover_fetcher(
        page_url=X_R15_PRODUCT_PAGE_URL,
        expected_marker=X_R15_SOURCE_ITEM_ID,
    )

    media = client.upload_media(
        filename="medalist-15-rakuten-kobo.jpg",
        content_type=cover.content_type,
        content=cover.content,
    )

    try:
        payload = build_x_r13_wordpress_draft_payload(
            X13WordPressDraftInput(
                ebook_item_id=ebook_item_id,
                title=_required(
                    _value(item, "title"),
                    "title",
                ),
                volume_label=_required(
                    _value(item, "volume_label"),
                    "volume_label",
                ),
                author_name=_required(
                    _value(item, "author_name"),
                    "author_name",
                ),
                publisher_name=_required(
                    _value(item, "publisher_name"),
                    "publisher_name",
                ),
                release_date=_value(
                    item,
                    "release_date",
                ),
                item_type=_required(
                    _value(item, "item_type"),
                    "item_type",
                ),
                store_name=store_name,
                store_item_id=store_item_id,
                affiliate_url=affiliate_url,
                cover_image_url=media.source_url,
            )
        )

        response = client.update_draft(
            post_id=X_R15_WORDPRESS_POST_ID,
            payload={
                "content": payload["content"],
                "excerpt": payload["excerpt"],
                "featured_media": media.media_id,
            },
        )

        if response.post_id != X_R15_WORDPRESS_POST_ID:
            raise X15WordPressCoverUpdateError(
                "WordPress returned the wrong post ID"
            )

        if response.status != "draft":
            raise X15WordPressCoverUpdateError(
                "WordPress post did not remain draft"
            )

    except Exception as exc:
        if isinstance(
            exc,
            X15WordPressCoverPartialFailure,
        ):
            raise

        raise X15WordPressCoverPartialFailure(
            (
                "WordPress draft update was not "
                "confirmed after media upload"
            ),
            media_id=media.media_id,
            media_url=media.source_url,
            image_sha256=cover.sha256,
            failure_stage=(
                "AFTER_MEDIA_UPLOAD_BEFORE_"
                "DRAFT_UPDATE_CONFIRMED"
            ),
            original_error_type=(
                type(exc).__name__
            ),
        ) from exc

    return X15WordPressCoverUpdateResult(
        ebook_item_id=ebook_item_id,
        source_item_id=source_item_id,
        post_id=response.post_id,
        post_status=response.status,
        media_id=media.media_id,
        media_url=media.source_url,
        image_sha256=cover.sha256,
        image_width=cover.width,
        image_height=cover.height,
        featured_media_set=True,
        content_updated=True,
        publish_executed=False,
    )
