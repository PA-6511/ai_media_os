from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from app.services.x_r13_wordpress_draft_payload_adapter import (
    X13WordPressDraftInput,
    build_x_r13_wordpress_draft_payload,
)


class NewReleaseFeaturedImageError(RuntimeError):
    pass


@dataclass(frozen=True)
class NewReleaseFeaturedImageInput:
    ebook_item_id: str
    source_item_id: str
    wordpress_post_id: int
    product_page_url: str
    filename: str
    item: Any
    offer: Any


@dataclass(frozen=True)
class NewReleaseFeaturedImageResult:
    status: str
    wordpress_post_id: int
    media_id: int | None
    media_url: str | None
    image_sha256: str | None
    content_updated: bool
    featured_media_set: bool
    publish_executed: bool
    error_summary: str | None


def _value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)

    return getattr(source, name)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise NewReleaseFeaturedImageError(message)


def _required_text(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise NewReleaseFeaturedImageError(
            f"{field_name} is required"
        )

    return normalized


def _validate_positive_int(value: Any, field_name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise NewReleaseFeaturedImageError(
            f"{field_name} must be a positive integer"
        )

    return value


def _normalize_post_id(value: Any) -> str:
    normalized = str(value or "").strip()

    if not normalized.isdigit() or int(normalized) <= 0:
        raise NewReleaseFeaturedImageError(
            "item.wordpress_post_id must be a positive integer"
        )

    return normalized


def _validate_filename(filename: str) -> str:
    normalized = str(filename or "").strip()

    if not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9._-]{0,120})\.jpg",
        normalized,
    ):
        raise NewReleaseFeaturedImageError(
            "filename must be a safe .jpg filename"
        )

    return normalized


def attach_featured_image_to_new_release_draft(
    *,
    input_data: NewReleaseFeaturedImageInput,
    client: Any,
    cover_fetcher: Any,
) -> NewReleaseFeaturedImageResult:
    post_id = _validate_positive_int(
        input_data.wordpress_post_id,
        "wordpress_post_id",
    )
    product_page_url = str(
        input_data.product_page_url or ""
    ).strip()
    _validate_filename(input_data.filename)

    if product_page_url and not product_page_url.startswith(
        "https://"
    ):
        raise NewReleaseFeaturedImageError(
            "product_page_url must use HTTPS"
        )

    _require(
        _value(input_data.item, "workflow_status") == "READY",
        "workflow_status must be READY",
    )
    _require(
        _value(input_data.item, "review_status") == "APPROVED",
        "review_status must be APPROVED",
    )
    _require(
        not bool(_value(input_data.item, "publish_ready")),
        "publish_ready must remain false",
    )
    _require(
        _value(input_data.item, "wordpress_status") == "DRAFT",
        "wordpress_status must be DRAFT",
    )
    _require(
        _normalize_post_id(
            _value(input_data.item, "wordpress_post_id")
        )
        == str(post_id),
        "item.wordpress_post_id must match wordpress_post_id",
    )

    if not product_page_url:
        return NewReleaseFeaturedImageResult(
            status="SKIPPED_NO_COVER_SOURCE",
            wordpress_post_id=post_id,
            media_id=None,
            media_url=None,
            image_sha256=None,
            content_updated=False,
            featured_media_set=False,
            publish_executed=False,
            error_summary=None,
        )

    live_post = client.get_draft(post_id=post_id)

    _require(
        live_post.post_id == post_id,
        "WordPress live post ID mismatch",
    )
    _require(
        live_post.status == "draft",
        "WordPress live post must remain draft",
    )

    cover = cover_fetcher(
        page_url=product_page_url,
        expected_marker=_required_text(
            input_data.source_item_id,
            "source_item_id",
        ),
    )

    media = client.upload_media(
        filename=input_data.filename,
        content_type=cover.content_type,
        content=cover.content,
    )

    payload = build_x_r13_wordpress_draft_payload(
        X13WordPressDraftInput(
            ebook_item_id=_required_text(
                input_data.ebook_item_id,
                "ebook_item_id",
            ),
            title=_required_text(
                _value(input_data.item, "title"),
                "title",
            ),
            volume_label=_required_text(
                _value(input_data.item, "volume_label"),
                "volume_label",
            ),
            author_name=_required_text(
                _value(input_data.item, "author_name"),
                "author_name",
            ),
            publisher_name=_required_text(
                _value(input_data.item, "publisher_name"),
                "publisher_name",
            ),
            release_date=_value(input_data.item, "release_date"),
            item_type=_required_text(
                _value(input_data.item, "item_type"),
                "item_type",
            ),
            store_name=_required_text(
                _value(input_data.offer, "store_name"),
                "store_name",
            ),
            store_item_id=_required_text(
                _value(input_data.offer, "store_item_id"),
                "store_item_id",
            ),
            affiliate_url=_required_text(
                _value(input_data.offer, "affiliate_url"),
                "affiliate_url",
            ),
            cover_image_url=media.source_url,
        )
    )

    response = client.update_draft(
        post_id=post_id,
        payload={
            "content": payload["content"],
            "excerpt": payload["excerpt"],
            "featured_media": media.media_id,
        },
    )

    _require(
        response.post_id == post_id,
        "WordPress returned the wrong post ID",
    )
    _require(
        response.status == "draft",
        "WordPress post did not remain draft",
    )

    return NewReleaseFeaturedImageResult(
        status="ATTACHED",
        wordpress_post_id=post_id,
        media_id=media.media_id,
        media_url=media.source_url,
        image_sha256=cover.sha256,
        content_updated=True,
        featured_media_set=True,
        publish_executed=False,
        error_summary=None,
    )