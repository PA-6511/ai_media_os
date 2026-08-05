from __future__ import annotations

import pytest

from scripts.build_x_r11_wordpress_draft_render_dry_run import (
    RenderDryRunError,
    render_template,
    validate_https_url,
    validate_rendered_html,
    validate_slug,
)


def valid_template() -> str:
    return """
    <article class="ebook-new-release-article">
      <aside class="ebook-pr-disclosure">
        {{title}}
      </aside>
      <figure class="ebook-cover-image">
        <img
          src="{{cover_image_url}}"
          alt="{{cover_image_alt}}"
        >
      </figure>
      <div class="price-cards">
        {{volume_label}}
        {{release_date_display}}
        {{publisher_name}}
        {{author_name}}
      </div>
      <nav class="store-buttons">
        <a
          class="store-button store-button-rakuten-kobo"
          href="{{rakuten_affiliate_url}}"
          target="_blank"
          rel="sponsored nofollow noopener noreferrer"
        >
          楽天Kobo
        </a>
      </nav>
    </article>
    """


def valid_replacements() -> dict[str, str]:
    return {
        "title": "作品名",
        "volume_label": "第11巻",
        "release_date_display": (
            "2026年7月17日"
        ),
        "publisher_name": "出版社",
        "author_name": "著者",
        "cover_image_url": (
            "https://shop.r10s.jp/"
            "cover.jpg"
        ),
        "cover_image_alt": "作品名 書影",
        "rakuten_affiliate_url": (
            "https://a.r10.to/example"
        ),
    }


def test_template_render_escapes_values() -> None:
    replacements = valid_replacements()

    replacements["title"] = (
        "作品名 <特別版>"
    )

    rendered, counts = render_template(
        valid_template(),
        replacements,
    )

    assert (
        "作品名 &lt;特別版&gt;"
        in rendered
    )

    assert counts["title"] == 1


def test_unknown_placeholder_is_rejected() -> None:
    template = (
        valid_template()
        + "{{unknown_value}}"
    )

    with pytest.raises(
        RenderDryRunError,
        match="placeholder set mismatch",
    ):
        render_template(
            template,
            valid_replacements(),
        )


def test_http_url_is_rejected() -> None:
    with pytest.raises(
        RenderDryRunError,
        match="HTTPS",
    ):
        validate_https_url(
            "http://a.r10.to/example",
            allowed_hosts={
                "a.r10.to"
            },
            label="affiliate URL",
        )


def test_disallowed_host_is_rejected() -> None:
    with pytest.raises(
        RenderDryRunError,
        match="not allowed",
    ):
        validate_https_url(
            "https://example.com/cover.jpg",
            allowed_hosts={
                "shop.r10s.jp"
            },
            label="cover URL",
        )


def test_invalid_slug_is_rejected() -> None:
    with pytest.raises(
        RenderDryRunError,
        match="slug is invalid",
    ):
        validate_slug(
            "日本語 スラッグ"
        )


def test_rendered_html_validation_passes() -> None:
    replacements = valid_replacements()

    rendered, _ = render_template(
        valid_template(),
        replacements,
    )

    result = validate_rendered_html(
        rendered,
        affiliate_url=(
            replacements[
                "rakuten_affiliate_url"
            ]
        ),
        cover_image_url=(
            replacements[
                "cover_image_url"
            ]
        ),
    )

    assert result[
        "rendered_html_validation_passed"
    ] is True
