from __future__ import annotations

import pytest

from scripts.run_x_r11_wordpress_draft_creation_once import (
    DraftCreationError,
    build_rest_base,
    extract_title,
    validate_created_post,
)


def test_site_url_becomes_rest_base() -> None:
    result = build_rest_base(
        {
            "WORDPRESS_SITE_URL": (
                "https://example.com"
            )
        }
    )

    assert result == (
        "https://example.com/wp-json/wp/v2"
    )


def test_existing_rest_base_is_preserved() -> None:
    result = build_rest_base(
        {
            "WORDPRESS_REST_BASE_URL": (
                "https://example.com/"
                "wp-json/wp/v2/"
            )
        }
    )

    assert result == (
        "https://example.com/wp-json/wp/v2"
    )


def test_extract_raw_title() -> None:
    assert extract_title(
        {
            "title": {
                "raw": "作品名"
            }
        }
    ) == "作品名"


def test_created_publish_post_is_rejected() -> None:
    with pytest.raises(
        DraftCreationError,
        match="must equal draft",
    ):
        validate_created_post(
            {
                "id": 123,
                "title": {
                    "raw": (
                        "のあ先輩はともだち。 "
                        "第11巻｜配信開始"
                    )
                },
                "slug": (
                    "noa-senpai-wa-tomodachi-"
                    "11-6ffa7a8d"
                ),
                "status": "publish",
                "categories": [43],
                "content": {
                    "raw": "<p>content</p>"
                },
            },
            expected_content="<p>content</p>",
        )


def test_valid_created_draft_passes() -> None:
    result = validate_created_post(
        {
            "id": 123,
            "title": {
                "raw": (
                    "のあ先輩はともだち。 "
                    "第11巻｜配信開始"
                )
            },
            "slug": (
                "noa-senpai-wa-tomodachi-"
                "11-6ffa7a8d"
            ),
            "status": "draft",
            "categories": [43],
            "content": {
                "raw": "<p>content</p>"
            },
            "link": "https://example.com/?p=123",
        },
        expected_content="<p>content</p>",
    )

    assert result["post_id"] == 123
    assert result["status"] == "draft"


def test_duplicate_search_uses_php_status_array(
    monkeypatch,
) -> None:
    import scripts.run_x_r11_wordpress_draft_creation_once as runner

    requested_urls: list[str] = []

    def fake_request_json(
        *,
        method: str,
        url: str,
        authorization: str,
        payload=None,
    ):
        assert method == "GET"
        assert authorization == "Basic test"

        requested_urls.append(url)

        return []

    monkeypatch.setattr(
        runner,
        "request_json",
        fake_request_json,
    )

    result = runner.find_duplicate_posts(
        rest_base=(
            "https://example.com/"
            "wp-json/wp/v2"
        ),
        authorization="Basic test",
    )

    assert result[
        "duplicate_found"
    ] is False

    assert len(requested_urls) == 2

    for url in requested_urls:
        assert (
            "status%5B%5D=publish"
            in url
        )
        assert (
            "status%5B%5D=future"
            in url
        )
        assert (
            "status%5B%5D=draft"
            in url
        )
        assert (
            "status%5B%5D=pending"
            in url
        )
        assert (
            "status%5B%5D=private"
            in url
        )
