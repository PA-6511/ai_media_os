from __future__ import annotations

import hashlib

import pytest

from scripts.run_x_r11_wordpress_publication_once import (
    EXPECTED_MEDIA_SOURCE_URL,
    EXPECTED_POST_ID,
    EXPECTED_POST_SLUG,
    EXPECTED_POST_TITLE,
    PublicationExecutionError,
    validate_content,
    validate_post,
    validate_public_url,
)


def valid_content() -> str:
    return (
        '<article class="ebook-new-release-article">'
        '<div class="ebook-pr-disclosure">PR</div>'
        '<figure class="ebook-cover-image">'
        f'<img src="{EXPECTED_MEDIA_SOURCE_URL}" '
        'alt="のあ先輩はともだち。 第11巻 書影">'
        "</figure>"
        '<div class="price-cards"></div>'
        '<div class="store-buttons">'
        '<a href="https://hb.afl.rakuten.co.jp/'
        'example/?pc=bce9f1878b0032dc4745ecf22fd179a6">'
        "楽天Kobo"
        "</a>"
        "</div>"
        "</article>"
    )


def valid_post(
    *,
    status: str,
    content: str,
) -> dict:
    return {
        "id": EXPECTED_POST_ID,
        "status": status,
        "slug": EXPECTED_POST_SLUG,
        "title": {
            "raw": EXPECTED_POST_TITLE
        },
        "categories": [43],
        "content": {
            "raw": content
        },
        "link": (
            "https://example.com/"
            "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
        ),
    }


def test_valid_public_url_passes() -> None:
    validate_public_url(
        (
            "https://example.com/"
            "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
        ),
        expected_hostname="example.com",
    )


def test_http_public_url_fails() -> None:
    with pytest.raises(
        PublicationExecutionError,
        match="must use HTTPS",
    ):
        validate_public_url(
            "http://example.com/test/",
            expected_hostname="example.com",
        )


def test_valid_draft_post_passes(
    monkeypatch,
) -> None:
    content = valid_content()

    import scripts.run_x_r11_wordpress_publication_once as module

    monkeypatch.setattr(
        module,
        "EXPECTED_CONTENT_SHA",
        hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest(),
    )

    result = validate_post(
        valid_post(
            status="draft",
            content=content,
        ),
        expected_status="draft",
    )

    assert result["status"] == "draft"


def test_valid_published_post_passes(
    monkeypatch,
) -> None:
    content = valid_content()

    import scripts.run_x_r11_wordpress_publication_once as module

    monkeypatch.setattr(
        module,
        "EXPECTED_CONTENT_SHA",
        hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest(),
    )

    result = validate_post(
        valid_post(
            status="publish",
            content=content,
        ),
        expected_status="publish",
    )

    assert result["status"] == "publish"


def test_changed_content_fails(
    monkeypatch,
) -> None:
    content = valid_content()

    import scripts.run_x_r11_wordpress_publication_once as module

    monkeypatch.setattr(
        module,
        "EXPECTED_CONTENT_SHA",
        hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest(),
    )

    changed = content.replace(
        "楽天Kobo",
        "変更済み",
        1,
    )

    with pytest.raises(
        PublicationExecutionError,
        match="content SHA mismatch",
    ):
        validate_content(
            changed
        )


def test_wrong_post_status_fails(
    monkeypatch,
) -> None:
    content = valid_content()

    import scripts.run_x_r11_wordpress_publication_once as module

    monkeypatch.setattr(
        module,
        "EXPECTED_CONTENT_SHA",
        hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest(),
    )

    with pytest.raises(
        PublicationExecutionError,
        match="post status mismatch",
    ):
        validate_post(
            valid_post(
                status="draft",
                content=content,
            ),
            expected_status="publish",
        )
