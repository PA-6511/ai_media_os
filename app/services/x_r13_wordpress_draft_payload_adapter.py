from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date
from typing import Any


X_R13_EBOOK_ITEM_ID = (
    "e2029b2f-f44a-462f-abc8-86c4bc74b818"
)


class X13WordPressDraftPayloadError(ValueError):
    pass


@dataclass(frozen=True)
class X13WordPressDraftInput:
    ebook_item_id: str
    title: str
    volume_label: str
    author_name: str
    publisher_name: str
    release_date: date | str
    item_type: str
    store_name: str
    store_item_id: str
    affiliate_url: str
    cover_image_url: str | None = None
    slug: str = "medalist-15-rakuten-kobo"


def _required(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise X13WordPressDraftPayloadError(
            f"{field_name} is required"
        )

    return normalized


def _release_date_text(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()

    normalized = _required(value, "release_date")

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        raise X13WordPressDraftPayloadError(
            "release_date must use YYYY-MM-DD"
        )

    return normalized


def build_x_r13_wordpress_draft_payload(
    value: X13WordPressDraftInput,
) -> dict[str, Any]:
    if value.ebook_item_id != X_R13_EBOOK_ITEM_ID:
        raise X13WordPressDraftPayloadError(
            "ebook_item_id does not match X-R13"
        )

    title = _required(value.title, "title")
    volume_label = _required(value.volume_label, "volume_label")
    author_name = _required(value.author_name, "author_name")
    publisher_name = _required(value.publisher_name, "publisher_name")
    store_item_id = _required(value.store_item_id, "store_item_id")
    affiliate_url = _required(value.affiliate_url, "affiliate_url")
    release_date = _release_date_text(value.release_date)

    if value.item_type != "tankobon":
        raise X13WordPressDraftPayloadError(
            "item_type must be tankobon"
        )

    if value.store_name.strip().upper() != "RAKUTEN_KOBO":
        raise X13WordPressDraftPayloadError(
            "store_name must be RAKUTEN_KOBO"
        )

    if not affiliate_url.startswith("https://"):
        raise X13WordPressDraftPayloadError(
            "affiliate_url must use HTTPS"
        )

    slug = _required(value.slug, "slug")

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise X13WordPressDraftPayloadError(
            "slug must use lowercase ASCII kebab-case"
        )

    display_title = f"{title} {volume_label}"

    escaped_author = html.escape(author_name)
    escaped_publisher = html.escape(publisher_name)
    escaped_release_date = html.escape(release_date)
    escaped_affiliate_url = html.escape(affiliate_url, quote=True)
    escaped_store_item_id = html.escape(store_item_id, quote=True)
    escaped_display_title = html.escape(display_title)

    cover_image_url = str(
        value.cover_image_url or ""
    ).strip()

    if (
        cover_image_url
        and not cover_image_url.startswith("https://")
    ):
        raise X13WordPressDraftPayloadError(
            "cover_image_url must use HTTPS"
        )

    escaped_cover_image_url = html.escape(
        cover_image_url,
        quote=True,
    )

    cover_html = ""

    if escaped_cover_image_url:
        cover_html = (
            '<figure class="ebook-cover-figure" '
            'style="max-width:320px;margin:1.5rem auto;'
            'text-align:center;">'
            '<img class="ebook-cover-image" '
            f'src="{escaped_cover_image_url}" '
            f'alt="{escaped_display_title} 書影" '
            'loading="lazy" decoding="async" '
            'style="display:block;width:100%;height:auto;'
            'border-radius:10px;'
            'box-shadow:0 6px 20px rgba(15,23,42,.12);" />'
            "</figure>"
        )

    content = (
        '<article class="ebook-new-release-article" '
        'data-store="rakuten-kobo" '
        f'data-store-item-id="{escaped_store_item_id}">'

        '<p class="ebook-pr-disclosure" '
        'style="margin:0 0 1.25rem;color:#4b5563;">'
        "本記事はプロモーションを含みます。"
        "</p>"

        f"{cover_html}"

        '<section class="ebook-release-metadata-card" '
        'aria-label="書籍情報" '
        'style="margin:1.5rem 0;padding:1rem 1.25rem;'
        'border:1px solid #e5e7eb;border-radius:12px;'
        'background:#f8fafc;">'

        '<dl class="ebook-release-metadata" '
        'style="display:grid;grid-template-columns:6em 1fr;'
        'gap:.75rem 1rem;margin:0;">'

        '<dt style="font-weight:700;">著者</dt>'
        f'<dd style="margin:0;">{escaped_author}</dd>'

        '<dt style="font-weight:700;">出版社</dt>'
        f'<dd style="margin:0;">{escaped_publisher}</dd>'

        '<dt style="font-weight:700;">発売日</dt>'
        f'<dd style="margin:0;">{escaped_release_date}</dd>'

        "</dl>"
        "</section>"

        '<div class="store-buttons" '
        'style="margin-top:1.5rem;">'

        '<a class="ebook-store-button '
        'ebook-store-button-rakuten-kobo" '
        f'href="{escaped_affiliate_url}" '
        'rel="sponsored nofollow" '
        'style="display:block;max-width:420px;'
        'margin:0 auto;padding:14px 18px;'
        'border-radius:10px;background:#bf0000;'
        'color:#ffffff;font-weight:700;'
        'text-align:center;text-decoration:none;">'
        "楽天Koboで読む・購入する"
        "</a>"

        "</div>"
        "</article>"
    )

    return {
        "title": display_title,
        "slug": slug,
        "status": "draft",
        "content": content,
        "excerpt": f"{display_title}の楽天Kobo配信情報です。",
        "comment_status": "closed",
        "ping_status": "closed",
    }
