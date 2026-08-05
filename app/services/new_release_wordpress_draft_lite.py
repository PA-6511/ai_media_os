from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import html
import re
import unicodedata
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlsplit

from app.services.store_url_policy import STORE_WORDPRESS_LINK_HOSTS

from app.services.x_r15_public_cover_source import (
    fetch_x15_public_cover,
)


SUPPORTED_STORE_ORDER = ("amazon", "rakuten_kobo", "dmm")
NEW_RELEASE_POST_META_KEY = "_ai_media_os_new_release"
STORE_AFFILIATE_META_KEYS = {
    "amazon": "kindle_url",
    "rakuten_kobo": "rakuten_kobo_url",
    "dmm": "dmm_url",
}
STORE_BUTTON_LABELS = {
    "amazon": "Amazon Kindleで見る",
    "rakuten_kobo": "楽天Koboで見る",
    "dmm": "DMMブックスで見る",
}
STORE_BUTTON_ARIA_LABELS = {
    "amazon": "Amazon Kindleでこの作品を見る",
    "rakuten_kobo": "楽天Koboでこの作品を見る",
    "dmm": "DMMブックスでこの作品を見る",
}
STORE_BUTTON_CLASSES = {
    "amazon": "ebook-store-button--amazon",
    "rakuten_kobo": "ebook-store-button--rakuten-kobo",
    "dmm": "ebook-store-button--dmm",
}
STORE_BUTTON_BASE_STYLE = (
    "display:flex;"
    "align-items:center;"
    "justify-content:center;"
    "min-height:52px;"
    "padding:12px 18px;"
    "border-radius:8px;"
    "font-weight:700;"
    "text-decoration:none;"
    "box-sizing:border-box;"
    "width:100%;"
)
STORE_BUTTON_STYLES = {
    "amazon": "background:#ffb84d;color:#1f2937;",
    "rakuten_kobo": "background:#bf0000;color:#ffffff;",
    "dmm": "background:#0066cc;color:#ffffff;",
}
STORE_AFFILIATE_HOSTS = STORE_WORDPRESS_LINK_HOSTS


class NewReleaseWordPressDraftLiteError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WordPressStoreOffer:
    store_name: str
    store_item_id: str
    affiliate_url: str
    product_url: str | None = None
    price_yen: Any = None
    price_amount: Any = None
    currency: str | None = None
    availability_status: str | None = None
    source_offer_id: str | None = None


@dataclass(frozen=True)
class UnifiedPriceResult:
    status: str
    price_yen: int | None
    missing_stores: tuple[str, ...]
    review_reasons: tuple[str, ...]


@dataclass(frozen=True)
class NewReleaseWordPressDraftLiteResult:
    status: str
    wordpress_post_id: int
    wordpress_status: str
    wordpress_link: str | None
    image_status: str
    image_media_id: int | None
    image_media_url: str | None
    image_error_summary: str | None
    featured_media_set: bool
    price_status: str
    unified_price_yen: int | None
    missing_price_stores: tuple[str, ...]
    price_review_reasons: tuple[str, ...]
    publish_executed: bool


def _value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name)


def _optional_value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _require(
    condition: bool,
    message: str,
    code: str = "invalid_state",
) -> None:
    if not condition:
        raise NewReleaseWordPressDraftLiteError(code, message)


def _required_text(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise NewReleaseWordPressDraftLiteError(
            "invalid_request",
            f"{field_name} is required",
        )
    return normalized


def _valid_positive_int(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int)
        and value > 0
    )


def _display_title(item: Any) -> str:
    title = _required_text(_value(item, "title"), "title")
    volume_label = str(
        _optional_value(item, "volume_label") or ""
    ).strip()
    if not volume_label:
        return title

    normalized_title = unicodedata.normalize("NFKC", title).strip()
    normalized_volume = unicodedata.normalize(
        "NFKC", volume_label
    ).strip()
    if normalized_volume in normalized_title:
        return title

    volume_match = re.fullmatch(
        r"(?:第\s*)?(\d+)(?:\s*巻)?",
        normalized_volume,
    )
    if volume_match is not None:
        volume_number = re.escape(volume_match.group(1))
        equivalent_volume_patterns = (
            rf"(?:第\s*)?{volume_number}\s*巻",
            rf"\bvol\.?\s*{volume_number}\b",
            rf"(?:第\s*)?{volume_number}(?:\s*巻)?\s*$",
        )
        if any(
            re.search(pattern, normalized_title, re.IGNORECASE)
            for pattern in equivalent_volume_patterns
        ):
            return title

    return f"{title} {volume_label}"


def _normalize_store_name(offer: Any) -> str:
    return str(_optional_value(offer, "store_name") or "").strip().lower()


def _validate_https_url(
    value: Any,
    *,
    field_name: str,
    allowed_hosts: set[str] | None = None,
) -> str:
    normalized = _required_text(value, field_name)
    parsed = urlsplit(normalized)
    host = (parsed.hostname or "").lower()
    _require(
        parsed.scheme == "https"
        and bool(host)
        and parsed.username is None
        and parsed.password is None,
        f"{field_name} must use HTTPS and be an absolute URL",
        "invalid_request",
    )
    if allowed_hosts is not None:
        _require(
            host in allowed_hosts,
            f"{field_name} host is not allowed",
            "invalid_request",
        )
    return normalized


def normalize_wordpress_store_offers(
    offers: Iterable[Any],
) -> tuple[WordPressStoreOffer, ...]:
    by_store: dict[str, WordPressStoreOffer] = {}
    for offer in offers:
        store_name = _normalize_store_name(offer)
        if store_name not in SUPPORTED_STORE_ORDER:
            continue
        availability = str(
            _optional_value(offer, "availability_status") or ""
        ).strip().upper()
        if availability in {
            "NOT_FOUND",
            "UNAVAILABLE",
            "REMOVED",
            "ERROR",
        }:
            continue
        _require(
            store_name not in by_store,
            f"multiple {store_name} offers are not allowed",
            "invalid_request",
        )
        affiliate_url = _validate_https_url(
            _optional_value(offer, "affiliate_url"),
            field_name=f"{store_name}.affiliate_url",
            allowed_hosts=STORE_AFFILIATE_HOSTS[store_name],
        )
        by_store[store_name] = WordPressStoreOffer(
            store_name=store_name,
            store_item_id=_required_text(
                _optional_value(offer, "store_item_id"),
                f"{store_name}.store_item_id",
            ),
            affiliate_url=affiliate_url,
            product_url=str(
                _optional_value(offer, "product_url") or ""
            ).strip()
            or None,
            price_yen=_optional_value(offer, "price_yen"),
            price_amount=_optional_value(offer, "price_amount"),
            currency=str(
                _optional_value(offer, "currency") or ""
            ).strip()
            or None,
            availability_status=availability or None,
            source_offer_id=str(
                _optional_value(offer, "source_offer_id")
                or _optional_value(offer, "id")
                or ""
            ).strip()
            or None,
        )

    _require(
        bool(by_store),
        "at least one eligible store offer is required",
        "invalid_request",
    )
    return tuple(
        by_store[store_name]
        for store_name in SUPPORTED_STORE_ORDER
        if store_name in by_store
    )


def build_wordpress_store_buttons_html(
    offers: Iterable[Any],
) -> str:
    """Render the shared responsive WordPress store-button group."""

    normalized_offers = normalize_wordpress_store_offers(offers)
    buttons: list[str] = []
    for offer in normalized_offers:
        store_name = offer.store_name
        store_class = html.escape(
            STORE_BUTTON_CLASSES[store_name],
            quote=True,
        )
        store_aria_label = html.escape(
            STORE_BUTTON_ARIA_LABELS[store_name],
            quote=True,
        )
        store_style = (
            STORE_BUTTON_BASE_STYLE + STORE_BUTTON_STYLES[store_name]
        )
        buttons.append(
            '<a class="ebook-store-button '
            f'{store_class}" '
            f'data-store="{html.escape(store_name, quote=True)}" '
            f'href="{html.escape(offer.affiliate_url, quote=True)}" '
            'target="_blank" rel="sponsored nofollow noopener" '
            f'aria-label="{store_aria_label}" '
            f'style="{store_style}">'
            f'{html.escape(STORE_BUTTON_LABELS[store_name])}'
            "</a>"
        )

    return (
        '<div class="store-buttons" role="group" '
        'aria-label="電子書籍ストア" '
        'style="display:grid;gap:12px;margin-top:24px;'
        'grid-template-columns:repeat(auto-fit,minmax(220px,1fr));">'
        f'{"".join(buttons)}'
        "</div>"
    )


def build_wordpress_store_offers(
    offers: Iterable[Any],
    *,
    dmm_wordpress_link_resolver: Callable[[Any], str | None],
) -> tuple[WordPressStoreOffer, ...]:
    """Resolve DMM exclusively through wordpress/blog_main."""

    prepared: list[WordPressStoreOffer] = []
    for offer in offers:
        store_name = _normalize_store_name(offer)
        if store_name not in SUPPORTED_STORE_ORDER:
            continue
        affiliate_url = _optional_value(offer, "affiliate_url")
        if store_name == "dmm":
            affiliate_url = dmm_wordpress_link_resolver(offer)
            if not str(affiliate_url or "").strip():
                continue
        prepared.append(
            WordPressStoreOffer(
                store_name=store_name,
                store_item_id=str(
                    _optional_value(offer, "store_item_id") or ""
                ).strip(),
                affiliate_url=str(affiliate_url or "").strip(),
                product_url=str(
                    _optional_value(offer, "product_url") or ""
                ).strip()
                or None,
                price_yen=_optional_value(offer, "price_yen"),
                price_amount=_optional_value(offer, "price_amount"),
                currency=str(
                    _optional_value(offer, "currency") or ""
                ).strip()
                or None,
                availability_status=str(
                    _optional_value(offer, "availability_status") or ""
                ).strip()
                or None,
                source_offer_id=str(
                    _optional_value(offer, "id") or ""
                ).strip()
                or None,
            )
        )
    return normalize_wordpress_store_offers(prepared)


def _decimal_price(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("NaN")


def determine_unified_price(
    offers: Iterable[WordPressStoreOffer],
) -> UnifiedPriceResult:
    prices: dict[str, int] = {}
    missing: list[str] = []
    reasons: list[str] = []

    for offer in offers:
        price_amount = _decimal_price(offer.price_amount)
        price_yen = _decimal_price(offer.price_yen)
        if (
            price_amount is not None
            and price_yen is not None
            and price_amount != price_yen
        ):
            reasons.append(f"{offer.store_name}:price_fields_mismatch")
            continue
        value = price_amount if price_amount is not None else price_yen
        currency = str(offer.currency or "").strip().upper()
        if value is None:
            missing.append(offer.store_name)
            continue
        if currency != "JPY":
            reasons.append(f"{offer.store_name}:currency_not_jpy")
            continue
        if not value.is_finite() or value <= 0 or value != value.to_integral_value():
            reasons.append(f"{offer.store_name}:invalid_price")
            continue
        prices[offer.store_name] = int(value)

    distinct_prices = set(prices.values())
    if len(distinct_prices) > 1:
        reasons.append("store_price_mismatch")
    if not prices and not reasons:
        reasons.append("verified_price_missing")

    if reasons:
        return UnifiedPriceResult(
            status="PRICE_REVIEW_REQUIRED",
            price_yen=None,
            missing_stores=tuple(missing),
            review_reasons=tuple(reasons),
        )
    return UnifiedPriceResult(
        status="PRICE_READY",
        price_yen=next(iter(distinct_prices)),
        missing_stores=tuple(missing),
        review_reasons=(),
    )


def _slugify(item: Any, preferred_offer: Any) -> str:
    base = _display_title(item)
    ascii_only = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    if ascii_only:
        return ascii_only[:80]
    source_item_id = _required_text(
        _value(preferred_offer, "store_item_id"),
        "store_item_id",
    )
    return f"ebook-{source_item_id.lower()}"


def _cover_filename(item: Any, cover_offer: Any) -> str:
    source_item_id = str(
        _optional_value(item, "source_item_id")
        or _optional_value(cover_offer, "store_item_id")
        or "cover"
    ).strip()
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", source_item_id).strip("-")
    return (safe or "cover").lower() + ".jpg"


def _select_cover_offer(
    offers: Iterable[WordPressStoreOffer],
) -> WordPressStoreOffer | None:
    for offer in offers:
        if offer.store_name != "rakuten_kobo" or not offer.product_url:
            continue
        try:
            _validate_https_url(
                offer.product_url,
                field_name="rakuten_kobo.product_url",
                allowed_hosts={"books.rakuten.co.jp"},
            )
        except NewReleaseWordPressDraftLiteError:
            continue
        return offer
    return None


def _build_draft_payload(
    *,
    item: Any,
    offers: Iterable[Any],
    preferred_offer: Any,
    cover_image_url: str | None = None,
) -> tuple[dict[str, Any], UnifiedPriceResult]:
    normalized_offers = normalize_wordpress_store_offers(offers)
    display_title = _display_title(item)
    price = determine_unified_price(normalized_offers)
    escaped_title = html.escape(display_title)
    author_name = html.escape(
        str(_optional_value(item, "author_name") or "").strip()
    )
    publisher_name = html.escape(
        str(_optional_value(item, "publisher_name") or "").strip()
    )
    release_date = html.escape(
        str(_optional_value(item, "release_date") or "").strip()
    )

    normalized_cover_url = str(cover_image_url or "").strip()
    if normalized_cover_url:
        normalized_cover_url = _validate_https_url(
            normalized_cover_url,
            field_name="cover_image_url",
        )
        cover_html = (
            '<figure class="ebook-cover-figure" '
            'style="width:100%;max-width:320px;margin:1.5rem auto;text-align:center;">'
            '<img class="ebook-cover-image" '
            f'src="{html.escape(normalized_cover_url, quote=True)}" '
            f'alt="{escaped_title} 書影" loading="lazy" decoding="async" '
            'style="display:block;width:100%;height:auto;object-fit:contain;border-radius:10px;box-shadow:0 6px 20px rgba(15,23,42,.12);" />'
            "</figure>"
        )
    else:
        cover_html = (
            '<div class="ebook-cover-image ebook-cover-placeholder" '
            'role="img" aria-label="書影は確認中です">書影は確認中です</div>'
        )

    if price.status == "PRICE_READY":
        price_text = f"{price.price_yen:,}円（税込）"
    else:
        price_text = "価格は確認中です"
    price_html = (
        '<section class="price-cards" aria-label="価格">'
        f'<p class="ebook-unified-price">{html.escape(price_text)}</p>'
        "</section>"
    )
    store_buttons_html = build_wordpress_store_buttons_html(
        normalized_offers
    )
    affiliate_meta = {
        STORE_AFFILIATE_META_KEYS[offer.store_name]: offer.affiliate_url
        for offer in normalized_offers
    }

    content = (
        '<style>'
        '.ebook-new-release-article{max-width:880px;margin:0 auto;box-sizing:border-box;}'
        '.ebook-pr-disclosure{margin:0 0 16px;}'
        '.ebook-product-layout{display:grid;grid-template-columns:minmax(200px,240px) minmax(0,1fr);gap:24px;align-items:start;}'
        '.ebook-release-metadata-card{min-width:0;}'
        '.ebook-release-metadata{display:grid;grid-template-columns:70px minmax(0,1fr);column-gap:12px;row-gap:8px;margin:0;}'
        '.ebook-release-metadata dt,.ebook-release-metadata dd{margin:0;padding:0;}'
        '.ebook-release-metadata dt{font-weight:700;}'
        '.ebook-unified-price{font-weight:700;}'
        '.ebook-cover-placeholder{width:100%;max-width:230px;min-height:280px;margin:0 auto;display:flex;align-items:center;justify-content:center;box-sizing:border-box;}'
        '@media (max-width:768px){'
        '.ebook-new-release-article{max-width:100%;}'
        '.ebook-product-layout{grid-template-columns:minmax(92px,32vw) minmax(0,1fr);gap:12px;}'
        '.ebook-cover-figure,.ebook-cover-image{max-width:140px!important;margin:0!important;}'
        '.store-buttons{grid-template-columns:minmax(0,1fr)!important;}'
        '}'
        '</style>'
        '<article class="ebook-new-release-article" '
        f'data-store-count="{len(normalized_offers)}">'
        '<p class="ebook-pr-disclosure">本記事はプロモーションを含みます。</p>'
        '<div class="ebook-product-layout">'
        f"{cover_html}"
        '<section class="ebook-release-metadata-card" aria-label="書籍情報">'
        '<dl class="ebook-release-metadata">'
        '<dt>著者</dt>'
        f"<dd>{author_name}</dd>"
        '<dt>出版社</dt>'
        f"<dd>{publisher_name}</dd>"
        '<dt>発売日</dt>'
        f"<dd>{release_date}</dd>"
        "</dl></section></div>"
        f"{price_html}"
        f"{store_buttons_html}"
        "</article>"
    )
    return (
        {
            "title": display_title,
            "slug": _slugify(item, preferred_offer),
            "status": "draft",
            "content": content,
            "excerpt": f"【PR】{display_title}の発売情報です。",
            "comment_status": "closed",
            "ping_status": "closed",
            "meta": {
                NEW_RELEASE_POST_META_KEY: True,
                **affiliate_meta,
            },
        },
        price,
    )


def build_new_release_wordpress_draft_payload(
    *,
    item: Any,
    offers: Iterable[Any],
    preferred_offer: Any,
    cover_image_url: str | None = None,
) -> tuple[dict[str, Any], UnifiedPriceResult]:
    """Build the canonical single-item WordPress draft payload."""
    return _build_draft_payload(
        item=item,
        offers=offers,
        preferred_offer=preferred_offer,
        cover_image_url=cover_image_url,
    )


def _summarize_error(exc: Exception) -> str:
    detail = str(exc).strip()
    if detail:
        return f"{type(exc).__name__}: {detail}"[:240]
    return type(exc).__name__


def _record_image_state(
    *,
    state_repository: Any,
    item: Any,
    image_status: str,
    actor: str,
    note: str,
    commit: Callable[[], None],
    rollback: Callable[[], None],
) -> str | None:
    if not hasattr(state_repository, "set_image_status"):
        return None
    database_value = "READY" if image_status == "ATTACHED" else "REVIEW"
    try:
        state_repository.set_image_status(
            item,
            database_value,
            changed_by=actor,
            note=note,
        )
        commit()
    except Exception as exc:
        rollback()
        return _summarize_error(exc)
    return None


def create_new_release_wordpress_draft_lite(
    *,
    ebook_item_id: str,
    item: Any,
    offers: Iterable[Any],
    preferred_offer: Any,
    wordpress_client: Any,
    state_repository: Any,
    commit: Callable[[], None],
    rollback: Callable[[], None],
    cover_fetcher: Any = fetch_x15_public_cover,
    actor: str = "human:local_gui:wordpress_draft_lite",
    before_external_create: Callable[[], None] | None = None,
    after_external_create: Callable[[Any], None] | None = None,
) -> NewReleaseWordPressDraftLiteResult:
    normalized_item_id = _required_text(ebook_item_id, "ebook_item_id")
    normalized_offers = normalize_wordpress_store_offers(offers)
    _require(
        normalized_item_id == _required_text(_value(item, "id"), "item.id"),
        "ebook item mismatch",
        "invalid_request",
    )
    _require(
        _value(item, "workflow_status") == "READY",
        "workflow_status must be READY",
        "invalid_state",
    )
    _require(
        _value(item, "review_status") == "APPROVED",
        "review_status must be APPROVED",
        "invalid_state",
    )
    _require(
        not bool(_value(item, "publish_ready")),
        "publish_ready must remain false",
        "invalid_state",
    )
    _require(
        not str(_optional_value(item, "wordpress_post_id") or "").strip(),
        "WordPress draft already exists",
        "already_created",
    )
    _require(
        str(
            _optional_value(item, "wordpress_status") or "NOT_CREATED"
        ).upper()
        in {"", "NOT_CREATED"},
        "wordpress_status must be NOT_CREATED",
        "invalid_state",
    )

    cover_offer = _select_cover_offer(normalized_offers)
    cover = None
    source_cover_url = None
    image_error_summary = "verified Rakuten Kobo cover source was not available"
    if cover_offer is not None:
        try:
            cover = cover_fetcher(
                page_url=cover_offer.product_url,
                expected_marker=cover_offer.store_item_id,
            )
            raw_cover_url = str(
                _optional_value(cover, "image_url") or ""
            ).strip()
            if raw_cover_url:
                source_cover_url = _validate_https_url(
                    raw_cover_url,
                    field_name="cover.image_url",
                )
        except Exception as exc:
            cover = None
            image_error_summary = _summarize_error(exc)

    payload, price = _build_draft_payload(
        item=item,
        offers=normalized_offers,
        preferred_offer=preferred_offer,
        cover_image_url=source_cover_url,
    )
    try:
        if before_external_create is not None:
            before_external_create()
        response = wordpress_client.create_draft(payload)
        _require(
            _valid_positive_int(_optional_value(response, "post_id")),
            "WordPress response post_id must be a positive integer",
            "transport_error",
        )
        _require(
            _optional_value(response, "status") == "draft",
            "WordPress response is not draft",
            "transport_error",
        )
        if after_external_create is not None:
            after_external_create(response)
        state_repository.mark_wordpress_draft_created(
            item,
            response.post_id,
            changed_by=actor,
            note="WordPress multi-store draft created from local GUI.",
        )
        commit()
    except Exception:
        rollback()
        raise

    image_status = "REVIEW_REQUIRED"
    image_media_id = None
    image_media_url = None
    featured_media_set = False

    if cover_offer is not None and cover is not None:
        try:
            live_post = wordpress_client.get_draft(post_id=response.post_id)
            _require(
                _optional_value(live_post, "post_id") == response.post_id,
                "WordPress live post ID mismatch",
                "transport_error",
            )
            _require(
                _optional_value(live_post, "status") == "draft",
                "WordPress live post must remain draft",
                "transport_error",
            )
            media = wordpress_client.upload_media(
                filename=_cover_filename(item, cover_offer),
                content_type=cover.content_type,
                content=cover.content,
            )
            _require(
                _valid_positive_int(_optional_value(media, "media_id")),
                "WordPress media_id must be a positive integer",
                "transport_error",
            )
            media_url = _validate_https_url(
                _optional_value(media, "source_url"),
                field_name="media.source_url",
            )
            update_payload, _ = _build_draft_payload(
                item=item,
                offers=normalized_offers,
                preferred_offer=preferred_offer,
                cover_image_url=media_url,
            )
            update_response = wordpress_client.update_draft(
                post_id=response.post_id,
                payload={
                    "content": update_payload["content"],
                    "excerpt": update_payload["excerpt"],
                    "featured_media": media.media_id,
                },
            )
            _require(
                _optional_value(update_response, "post_id")
                == response.post_id,
                "WordPress updated post ID mismatch",
                "transport_error",
            )
            _require(
                _optional_value(update_response, "status") == "draft",
                "WordPress post did not remain draft",
                "transport_error",
            )
            image_status = "ATTACHED"
            image_media_id = media.media_id
            image_media_url = media_url
            image_error_summary = None
            featured_media_set = True
        except Exception as exc:
            image_error_summary = _summarize_error(exc)

    image_state_error = _record_image_state(
        state_repository=state_repository,
        item=item,
        image_status=image_status,
        actor=actor,
        note=(
            "Verified cover uploaded and featured media attached."
            if image_status == "ATTACHED"
            else f"Cover requires review: {image_error_summary}"
        ),
        commit=commit,
        rollback=rollback,
    )
    if image_state_error is not None:
        image_status = "REVIEW_REQUIRED"
        image_error_summary = (
            f"image state persistence failed: {image_state_error}"
        )[:240]

    result_status = "DRAFT_CREATED"
    if image_status == "REVIEW_REQUIRED":
        result_status = "DRAFT_CREATED_IMAGE_REVIEW_REQUIRED"

    return NewReleaseWordPressDraftLiteResult(
        status=result_status,
        wordpress_post_id=response.post_id,
        wordpress_status="DRAFT",
        wordpress_link=response.link,
        image_status=image_status,
        image_media_id=image_media_id,
        image_media_url=image_media_url,
        image_error_summary=image_error_summary,
        featured_media_set=featured_media_set,
        price_status=price.status,
        unified_price_yen=price.price_yen,
        missing_price_stores=price.missing_stores,
        price_review_reasons=price.review_reasons,
        publish_executed=False,
    )
