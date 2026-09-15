from __future__ import annotations

import unicodedata

import hashlib
import html
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


SCHEMA_MAX_ITEMS = 200
DEFAULT_X_PREVIEW_ITEMS = 3
STORE_DEFINITIONS = (
    ("kindle", "Kindle", "kindle"),
    ("rakuten", "楽天Kobo", "rakuten"),
    ("dmm", "DMMブックス", "dmm"),
)


class XnrRoundupContentError(RuntimeError):
    pass


@dataclass(frozen=True)
class XnrRoundupContent:
    target_date: str
    title: str
    wordpress_html: str
    wordpress_item_count: int
    x_draft_text: str
    x_preview_count: int
    total_item_count: int
    source_digest: str

    def to_plan(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "target_date": self.target_date,
            "title": self.title,
            "wordpress_html": self.wordpress_html,
            "wordpress_item_count": self.wordpress_item_count,
            "x_draft_text": self.x_draft_text,
            "x_preview_count": self.x_preview_count,
            "total_item_count": self.total_item_count,
            "source_digest": self.source_digest,
            "wordpress_content_digest": hashlib.sha256(
                self.wordpress_html.encode("utf-8")
            ).hexdigest(),
        }


def _source_digest(
    *,
    target_date: str,
    title: str,
    wordpress_html: str,
    wordpress_item_count: int,
) -> str:
    """Hash only the canonical WordPress publication projection.

    XNR_STABLE_PUBLICATION_DIGEST_V1:
    volatile export-envelope fields such as generated_at and data for
    unrelated release dates must never invalidate an already-published
    roundup. X-body integrity is protected separately by x_draft_sha256.
    """
    projection = {
        "contract": "XNR_WORDPRESS_PUBLICATION_V1",
        "target_date": str(target_date),
        "title": str(title),
        "wordpress_slug": (
            "daily-new-releases-"
            + str(target_date)
        ),
        "wordpress_html": str(wordpress_html),
        "wordpress_item_count": int(
            wordpress_item_count
        ),
    }
    encoded = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _https_url(value: Any) -> str:
    normalized = str(value or "").strip()
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    return normalized


def _price(stores: Mapping[str, Any]) -> str:
    for key in ("rakuten", "kindle", "dmm"):
        store = stores.get(key)
        if not isinstance(store, Mapping):
            continue
        value = store.get("price")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f"¥{int(value):,}"
        label = str(store.get("price_label") or "").strip()
        if label:
            return label
    return ""


def _target_items(
    payload: Mapping[str, Any],
    target_date: str,
) -> list[Mapping[str, Any]]:
    releases = payload.get("new_releases")
    if not isinstance(releases, list):
        raise XnrRoundupContentError("MALFORMED_PUBLIC_SOURCE")
    items = [
        item
        for item in releases
        if isinstance(item, Mapping)
        and str(item.get("release_date") or "") == target_date
    ]
    if not items:
        raise XnrRoundupContentError("NO_TARGET_ITEMS")
    if len(items) > SCHEMA_MAX_ITEMS:
        raise XnrRoundupContentError("SOURCE_ITEM_LIMIT_EXCEEDED")
    return items


def _render_card(item: Mapping[str, Any], index: int) -> str:
    title = str(item.get("title") or "").strip()
    if not title:
        raise XnrRoundupContentError("MALFORMED_PUBLIC_ITEM")
    authors = " / ".join(
        str(author).strip()
        for author in (item.get("authors") or [])
        if str(author).strip()
    )
    publisher = str(item.get("publisher") or "").strip()
    image_url = _https_url(item.get("image_url"))
    stores = item.get("stores")
    if not isinstance(stores, Mapping):
        stores = {}
    price = _price(stores)
    parts = [
        '<section class="ai-nr-roundup__item">',
        (
            f'<h2 id="book-{index}" class="ai-nr-roundup__title">'
            f"{html.escape(title)}</h2>"
        ),
        '<div class="ai-nr-roundup__main">',
        '<div class="ai-nr-roundup__cover-wrap">',
    ]
    if image_url:
        parts.append(
            '<img class="ai-nr-roundup__cover"'
            f' src="{html.escape(image_url, quote=True)}"'
            f' alt="{html.escape(title, quote=True)} 書影"'
            ' loading="lazy" decoding="async">'
        )
    parts.extend(
        [
            "</div>",
            '<div class="ai-nr-roundup__info">',
        ]
    )
    if authors:
        parts.append(
            f'<p class="ai-nr-roundup__author">{html.escape(authors)}</p>'
        )
    if publisher:
        parts.append(
            f'<p class="ai-nr-roundup__publisher">{html.escape(publisher)}</p>'
        )
    if price:
        parts.append(
            f'<div class="ai-nr-roundup__price">{html.escape(price)}</div>'
        )
    parts.append('<div class="ai-nr-roundup__stores">')
    for key, label, css_class in STORE_DEFINITIONS:
        store = stores.get(key)
        if not isinstance(store, Mapping):
            continue
        if str(store.get("status") or "").strip().upper() != "FOUND":
            continue
        url = _https_url(store.get("url"))
        if not url:
            continue
        parts.append(
            f'<a class="ai-nr-roundup__btn ai-nr-roundup__btn--{css_class}"'
            f' href="{html.escape(url, quote=True)}" target="_blank"'
            f' rel="nofollow sponsored noopener">{label}</a>'
        )
    parts.extend(["</div>", "</div>", "</div>", "</section>"])
    return "".join(parts)


# XNR_WEIGHTED_LENGTH_V1
#
# Conservative X weighted-length preflight for the XNR
# generated text.
#
# - NFC normalization
# - X/twitter-text v3 single-character ranges
# - all URLs count as 23
# - {ARTICLE_URL} also counts as 23 before finalization
#
# This deliberately does NOT replace the legacy X Draft
# Module's character-count contract.  It is local to the
# autonomous daily roundup.
_XNR_X_MAX_WEIGHTED_LENGTH = 280
_XNR_X_TRANSFORMED_URL_LENGTH = 23
_XNR_ARTICLE_URL_TOKEN = "{ARTICLE_URL}"

_XNR_X_SINGLE_WEIGHT_RANGES = (
    (0, 4351),
    (8192, 8205),
    (8208, 8223),
    (8242, 8247),
)


def _x_codepoint_weight(
    character: str,
) -> int:
    value = ord(character)

    for start, end in (
        _XNR_X_SINGLE_WEIGHT_RANGES
    ):
        if start <= value <= end:
            return 1

    return 2


def _x_weighted_length(
    text: str,
) -> int:
    normalized = unicodedata.normalize(
        "NFC",
        text,
    )

    total = 0
    index = 0

    while index < len(normalized):

        if normalized.startswith(
            _XNR_ARTICLE_URL_TOKEN,
            index,
        ):
            total += (
                _XNR_X_TRANSFORMED_URL_LENGTH
            )
            index += len(
                _XNR_ARTICLE_URL_TOKEN
            )
            continue

        if (
            normalized.startswith(
                "https://",
                index,
            )
            or normalized.startswith(
                "http://",
                index,
            )
        ):
            end = index

            while (
                end < len(normalized)
                and not normalized[
                    end
                ].isspace()
            ):
                end += 1

            total += (
                _XNR_X_TRANSFORMED_URL_LENGTH
            )

            index = end
            continue

        total += _x_codepoint_weight(
            normalized[index]
        )

        index += 1

    return total


def _make_x_draft_weighted_safe(
    text: str,
    *,
    limit: int = (
        _XNR_X_MAX_WEIGHTED_LENGTH
    ),
) -> tuple[str, int]:
    lines = (
        unicodedata.normalize(
            "NFC",
            text,
        )
        .strip()
        .splitlines()
    )

    def render() -> str:
        return (
            "\n".join(lines).strip()
            + "\n"
        )

    while (
        _x_weighted_length(
            render()
        )
        > limit
    ):
        bullet_positions = [
            index
            for index, line
            in enumerate(lines)
            if line.startswith("・")
        ]

        if not bullet_positions:
            raise XnrRoundupContentError(
                "X_DRAFT_WEIGHTED_LENGTH_EXCEEDED"
            )

        # Degrade gracefully:
        # 3 -> 2 -> 1 -> 0 preview titles.
        del lines[
            bullet_positions[-1]
        ]

    safe_text = render()

    preview_count = sum(
        1
        for line in lines
        if line.startswith("・")
    )

    return (
        safe_text,
        preview_count,
    )


def build_xnr_roundup_content(
    payload: Mapping[str, Any],
    *,
    target_date: str,
    date_label: str,
    x_preview_items: int = DEFAULT_X_PREVIEW_ITEMS,
) -> XnrRoundupContent:
    if x_preview_items < 3 or x_preview_items > 5:
        raise XnrRoundupContentError("INVALID_X_PREVIEW_ITEMS")
    items = _target_items(payload, target_date)
    total_count = len(items)
    title = f"【{date_label}発売】本日の電子書籍新刊まとめ"
    cards = "".join(
        _render_card(item, index)
        for index, item in enumerate(items, 1)
    )
    wordpress_html = (
        '<div class="ai-nr-roundup">'
        '<p class="ai-nr-roundup__pr"><strong>PR</strong> '
        "本ページにはアフィリエイトリンクを含みます。</p>"
        '<p class="ai-nr-roundup__lead">'
        f"本日の電子書籍新刊{total_count}作品をまとめました。</p>"
        f"{cards}</div>"
    )
    preview = items[:x_preview_items]
    month = int(target_date[5:7])
    day = int(target_date[8:10])
    lines = [f"【{month}/{day}発売📚 本日の電子書籍新刊】", ""]
    lines.extend(
        "・" + str(item.get("title") or "").strip()
        for item in preview
    )
    lines.extend(
        [
            "",
            f"本日の新刊は全{total_count}作品。",
            "Kindle・楽天Kobo・DMMブックスをまとめてチェック👇",
            "{ARTICLE_URL}",
            "",
            "#PR #電子書籍 #新刊",
        ]
    )
    x_draft_text, safe_x_preview_count = _make_x_draft_weighted_safe(
        "\n".join(lines).strip() + "\n"
    )

    return XnrRoundupContent(
        target_date=target_date,
        title=title,
        wordpress_html=wordpress_html,
        wordpress_item_count=total_count,
        x_draft_text=x_draft_text,
        x_preview_count=safe_x_preview_count,
        total_item_count=total_count,
        source_digest=_source_digest(
            target_date=target_date,
            title=title,
            wordpress_html=wordpress_html,
            wordpress_item_count=total_count,
        ),
    )


def decide_existing_wordpress_action(
    *,
    post_id: int | None,
    post_status: str | None,
    existing_item_count: int | None,
    existing_source_digest: str | None,
    expected_item_count: int,
    expected_source_digest: str,
) -> str:
    # XNR_PUBLISHED_IDEMPOTENCE_V1
    if post_id is None:
        return "CREATE_DRAFT"

    normalized_status = str(
        post_status or ""
    ).strip().lower()

    source_matches = (
        existing_item_count == expected_item_count
        and existing_source_digest == expected_source_digest
    )

    if normalized_status == "publish":
        if source_matches:
            return "ALREADY_PUBLISHED"
        return "BLOCK_EXISTING_NON_DRAFT"

    if normalized_status != "draft":
        return "BLOCK_EXISTING_NON_DRAFT"

    if source_matches:
        return "KEEP_CURRENT_DRAFT"

    return "UPDATE_EXISTING_DRAFT"
