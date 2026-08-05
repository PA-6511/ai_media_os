from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping

from app.services.new_release_wordpress_draft_lite import (
    STORE_BUTTON_CLASSES,
    STORE_BUTTON_LABELS,
    SUPPORTED_STORE_ORDER,
    WordPressStoreOffer,
    build_wordpress_store_buttons_html,
    build_wordpress_store_offers,
    determine_unified_price,
)


TARGET_EBOOK_ITEM_ID = "32ca1eba-159d-481b-b4ca-7229ece11279"
TARGET_WORDPRESS_POST_ID = 207
TARGET_FEATURED_MEDIA_ID = 208
TARGET_UNIFIED_PRICE_YEN = 244
DEFAULT_DIAGNOSTIC_PATH = Path(
    "exchange/diagnostics/wordpress_existing_draft_store_buttons_update/"
    "post-207-store-buttons.html"
)
DEFAULT_EVIDENCE_DIRECTORY = Path(
    "exchange/logs/wordpress_existing_draft_updates"
)


class ExistingDraftStoreButtonsUpdateError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ExistingDraftStoreButtonsUpdateResult:
    status: str
    ebook_item_id: str
    wordpress_post_id: int
    before_content_sha256: str
    after_content_sha256: str
    replacement_count: int
    store_names: tuple[str, ...]
    store_labels: tuple[str, ...]
    external_update_attempted: bool
    external_update_succeeded: bool
    verified_after_update: bool
    diagnostic_path: str | None
    evidence_path: str | None


@dataclass(frozen=True)
class _BlockSpan:
    start: int
    end: int


_VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def normalize_wordpress_post_id(value: Any) -> int:
    if isinstance(value, bool):
        raise ExistingDraftStoreButtonsUpdateError(
            "invalid_wordpress_post_id",
            "wordpress_post_id must be a positive integer",
        )
    try:
        normalized = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ExistingDraftStoreButtonsUpdateError(
            "invalid_wordpress_post_id",
            "wordpress_post_id must be a positive integer",
        ) from exc
    if normalized <= 0:
        raise ExistingDraftStoreButtonsUpdateError(
            "invalid_wordpress_post_id",
            "wordpress_post_id must be a positive integer",
        )
    return normalized


def _value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ExistingDraftStoreButtonsUpdateError(code, message)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class _StoreButtonsLocator(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_offsets = [0]
        for match in re.finditer(r"\n", source):
            self.line_offsets.append(match.end())
        self.stack: list[tuple[str, int | None]] = []
        self.spans: list[_BlockSpan] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    @staticmethod
    def _is_target(attrs: list[tuple[str, str | None]]) -> bool:
        class_value = next(
            (value for name, value in attrs if name == "class"),
            "",
        )
        return "store-buttons" in str(class_value or "").split()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        target_start = self._offset() if self._is_target(attrs) else None
        if tag not in _VOID_ELEMENTS:
            self.stack.append((tag, target_start))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if self._is_target(attrs):
            start = self._offset()
            end = self.source.find(">", start)
            if end >= 0:
                self.spans.append(_BlockSpan(start=start, end=end + 1))

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        match_index = next(
            (
                index
                for index in range(len(self.stack) - 1, -1, -1)
                if self.stack[index][0] == tag
            ),
            None,
        )
        if match_index is None:
            return
        closed = self.stack[match_index:]
        del self.stack[match_index:]
        end_start = self._offset()
        end = self.source.find(">", end_start)
        if end < 0:
            return
        for _, target_start in closed:
            if target_start is not None:
                self.spans.append(
                    _BlockSpan(start=target_start, end=end + 1)
                )


def locate_store_buttons_blocks(content: str) -> tuple[_BlockSpan, ...]:
    parser = _StoreButtonsLocator(content)
    parser.feed(content)
    parser.close()
    return tuple(sorted(parser.spans, key=lambda span: span.start))


def replace_store_buttons_block(
    content: str,
    replacement_html: str,
) -> tuple[str, int]:
    spans = locate_store_buttons_blocks(content)
    _require(
        len(spans) == 1,
        "store_buttons_count_mismatch",
        "content must contain exactly one store-buttons block",
    )
    span = spans[0]
    return content[: span.start] + replacement_html + content[span.end :], 1


class _ContentInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.hrefs: list[str] = []
        self.has_image = False
        self.button_stores: list[str] = []
        self.button_attributes: list[dict[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {
            name: str(value or "") for name, value in attrs
        }
        if tag == "img" and attributes.get("src", "").strip():
            self.has_image = True
        if tag != "a":
            return
        href = unescape(attributes.get("href", "").strip())
        if href:
            self.hrefs.append(href)
        classes = set(attributes.get("class", "").split())
        if "ebook-store-button" in classes:
            self.button_stores.append(attributes.get("data-store", ""))
            self.button_attributes.append(attributes)

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)


def _inspect(content: str) -> _ContentInspector:
    inspector = _ContentInspector()
    inspector.feed(content)
    inspector.close()
    return inspector


def _validate_price_once(content: str) -> None:
    visible_text = " ".join(_inspect(content).text_parts)
    count = len(
        re.findall(
            rf"(?<!\d){TARGET_UNIFIED_PRICE_YEN}\s*円",
            visible_text,
        )
    )
    _require(
        count == 1,
        "unified_price_mismatch",
        "unified price 244 yen must appear exactly once",
    )


def _validate_rendered_buttons(
    content: str,
    expected_offers: tuple[WordPressStoreOffer, ...],
    *,
    dmm_x_url: str | None,
) -> None:
    spans = locate_store_buttons_blocks(content)
    _require(
        len(spans) == 1,
        "store_buttons_count_mismatch",
        "content must contain exactly one store-buttons block",
    )
    block = content[spans[0].start : spans[0].end]
    inspector = _inspect(block)
    _require(
        tuple(inspector.button_stores) == SUPPORTED_STORE_ORDER,
        "store_button_order_mismatch",
        "store buttons must be Amazon, Rakuten Kobo, then DMM",
    )
    _require(
        len(inspector.button_attributes) == 3
        and len(inspector.hrefs) == 3,
        "store_button_count_mismatch",
        "store-buttons must contain exactly three link buttons",
    )
    expected_by_store = {offer.store_name: offer for offer in expected_offers}
    for store_name, attributes in zip(
        SUPPORTED_STORE_ORDER,
        inspector.button_attributes,
        strict=True,
    ):
        classes = set(attributes.get("class", "").split())
        rel = set(attributes.get("rel", "").split())
        _require(
            STORE_BUTTON_CLASSES[store_name] in classes,
            "store_button_class_mismatch",
            f"{store_name} BEM class is missing",
        )
        _require(
            attributes.get("target") == "_blank"
            and rel == {"sponsored", "nofollow", "noopener"},
            "store_button_link_policy_mismatch",
            f"{store_name} link policy is invalid",
        )
        _require(
            unescape(attributes.get("href", ""))
            == expected_by_store[store_name].affiliate_url,
            "store_button_destination_mismatch",
            f"{store_name} destination does not match the selected offer",
        )
    if str(dmm_x_url or "").strip():
        _require(
            str(dmm_x_url).strip() not in inspector.hrefs,
            "dmm_x_main_used",
            "DMM x_main must not be used in WordPress content",
        )


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_success_evidence(
    *,
    directory: Path,
    result: ExistingDraftStoreButtonsUpdateResult,
    status_before: str,
    status_after: str,
    featured_media_before: int,
    featured_media_after: int,
    now: datetime,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_name = f"{timestamp}-post-{result.wordpress_post_id}"
    evidence = {
        "ebook_item_id": result.ebook_item_id,
        "wordpress_post_id": result.wordpress_post_id,
        "operation": "STORE_BUTTONS_REFRESH",
        "before_content_sha256": result.before_content_sha256,
        "after_content_sha256": result.after_content_sha256,
        "wordpress_status_before": status_before,
        "wordpress_status_after": status_after,
        "featured_media_before": featured_media_before,
        "featured_media_after": featured_media_after,
        "store_button_count": 3,
        "external_update_attempted": True,
        "external_update_succeeded": True,
        "verified_after_update": True,
        "error_summary": None,
    }
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    for sequence in range(1000):
        suffix = "" if sequence == 0 else f"-{sequence:03d}"
        path = directory / f"{base_name}{suffix}.json"
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(serialized)
            return path
        except FileExistsError:
            continue
    raise ExistingDraftStoreButtonsUpdateError(
        "evidence_path_exhausted",
        "could not allocate a new evidence path",
    )


def update_existing_draft_store_buttons(
    *,
    ebook_item_id: str,
    wordpress_post_id: Any,
    confirm_wordpress_post_id: Any | None,
    execute: bool,
    item: Any,
    offers: Iterable[Any],
    wordpress_client: Any,
    dmm_wordpress_link_resolver: Callable[[Any], str | None],
    dmm_x_link_resolver: Callable[[Any], str | None] | None = None,
    diagnostic_path: str | Path = DEFAULT_DIAGNOSTIC_PATH,
    evidence_directory: str | Path = DEFAULT_EVIDENCE_DIRECTORY,
    now_provider: Callable[[], datetime] | None = None,
) -> ExistingDraftStoreButtonsUpdateResult:
    normalized_ebook_item_id = str(ebook_item_id or "").strip()
    _require(
        normalized_ebook_item_id == TARGET_EBOOK_ITEM_ID,
        "ebook_item_id_mismatch",
        "ebook_item_id is not the authorized target",
    )
    requested_post_id = normalize_wordpress_post_id(wordpress_post_id)
    _require(
        requested_post_id == TARGET_WORDPRESS_POST_ID,
        "wordpress_post_id_mismatch",
        "wordpress_post_id is not the authorized target",
    )
    if execute:
        _require(
            confirm_wordpress_post_id is not None,
            "live_confirmation_missing",
            "confirm_wordpress_post_id is required for live execution",
        )
        confirmed_post_id = normalize_wordpress_post_id(
            confirm_wordpress_post_id
        )
        _require(
            confirmed_post_id == requested_post_id,
            "live_confirmation_mismatch",
            "confirmed WordPress post id does not match",
        )

    _require(
        str(_value(item, "id") or "").strip() == TARGET_EBOOK_ITEM_ID,
        "db_ebook_item_id_mismatch",
        "database item id does not match the authorized target",
    )
    _require(
        str(_value(item, "wordpress_status") or "").strip().upper()
        == "DRAFT",
        "db_wordpress_status_mismatch",
        "database wordpress_status must be DRAFT",
    )
    db_post_id = normalize_wordpress_post_id(
        _value(item, "wordpress_post_id")
    )
    _require(
        db_post_id == TARGET_WORDPRESS_POST_ID,
        "db_wordpress_post_id_mismatch",
        "database wordpress_post_id does not match 207",
    )

    source_offers = tuple(offers)
    prepared_offers = build_wordpress_store_offers(
        source_offers,
        dmm_wordpress_link_resolver=dmm_wordpress_link_resolver,
    )
    _require(
        tuple(offer.store_name for offer in prepared_offers)
        == SUPPORTED_STORE_ORDER,
        "required_store_missing",
        "Amazon, Rakuten Kobo, and DMM offers are all required",
    )
    price = determine_unified_price(prepared_offers)
    _require(
        price.status == "PRICE_READY"
        and price.price_yen == TARGET_UNIFIED_PRICE_YEN,
        "db_unified_price_mismatch",
        "database offers must resolve to the unified 244 yen price",
    )
    dmm_offer = next(
        offer for offer in prepared_offers if offer.store_name == "dmm"
    )
    _require(
        bool(dmm_offer.affiliate_url),
        "dmm_blog_main_missing",
        "an active DMM wordpress/blog_main link is required",
    )
    dmm_source_offer = next(
        offer
        for offer in source_offers
        if str(_value(offer, "store_name") or "").strip().lower() == "dmm"
    )
    dmm_x_url = (
        dmm_x_link_resolver(dmm_source_offer)
        if dmm_x_link_resolver is not None
        else None
    )

    before = wordpress_client.get_draft(post_id=requested_post_id)
    _require(
        _value(before, "post_id") == TARGET_WORDPRESS_POST_ID,
        "wordpress_post_id_mismatch",
        "WordPress GET returned the wrong post id",
    )
    _require(
        _value(before, "status") == "draft",
        "wordpress_status_mismatch",
        "WordPress GET status must be draft",
    )
    _require(
        _value(before, "featured_media") == TARGET_FEATURED_MEDIA_ID,
        "featured_media_mismatch",
        "featured_media must be 208",
    )
    before_content = _value(before, "content")
    before_title = _value(before, "title")
    before_excerpt = _value(before, "excerpt")
    _require(
        isinstance(before_content, str) and bool(before_content.strip()),
        "wordpress_content_missing",
        "WordPress editable content is required",
    )
    _require(
        isinstance(before_title, str),
        "wordpress_title_missing",
        "WordPress editable title is required",
    )
    before_inspector = _inspect(before_content)
    if str(dmm_x_url or "").strip():
        _require(
            str(dmm_x_url).strip() not in before_inspector.hrefs,
            "dmm_x_main_used",
            "current WordPress content uses DMM x_main",
        )
    _validate_price_once(before_content)
    _require(
        before_inspector.has_image,
        "cover_image_missing",
        "WordPress content must contain a cover image",
    )

    replacement_html = build_wordpress_store_buttons_html(prepared_offers)
    after_content, replacement_count = replace_store_buttons_block(
        before_content,
        replacement_html,
    )
    _require(
        after_content != before_content,
        "content_unchanged",
        "store-buttons replacement would not change the content",
    )
    _validate_price_once(after_content)
    _validate_rendered_buttons(
        after_content,
        prepared_offers,
        dmm_x_url=dmm_x_url,
    )
    _require(
        _inspect(after_content).has_image,
        "cover_image_missing",
        "replacement content must retain the cover image",
    )

    before_sha = _sha256(before_content)
    after_sha = _sha256(after_content)
    store_names = tuple(offer.store_name for offer in prepared_offers)
    store_labels = tuple(STORE_BUTTON_LABELS[name] for name in store_names)

    if not execute:
        output_path = Path(diagnostic_path)
        _write_text(output_path, replacement_html + "\n")
        return ExistingDraftStoreButtonsUpdateResult(
            status="DRY_RUN_READY",
            ebook_item_id=normalized_ebook_item_id,
            wordpress_post_id=requested_post_id,
            before_content_sha256=before_sha,
            after_content_sha256=after_sha,
            replacement_count=replacement_count,
            store_names=store_names,
            store_labels=store_labels,
            external_update_attempted=False,
            external_update_succeeded=False,
            verified_after_update=False,
            diagnostic_path=str(output_path),
            evidence_path=None,
        )

    response = wordpress_client.update_draft(
        post_id=requested_post_id,
        payload={"content": after_content, "status": "draft"},
    )
    _require(
        _value(response, "post_id") == TARGET_WORDPRESS_POST_ID
        and _value(response, "status") == "draft",
        "wordpress_update_response_invalid",
        "WordPress update response did not confirm draft 207",
    )
    verified = wordpress_client.get_draft(post_id=requested_post_id)
    verified_content = _value(verified, "content")
    _require(
        _value(verified, "post_id") == TARGET_WORDPRESS_POST_ID,
        "post_update_id_mismatch",
        "post-update WordPress id changed",
    )
    _require(
        _value(verified, "status") == "draft",
        "post_update_status_mismatch",
        "post-update WordPress status is not draft",
    )
    _require(
        _value(verified, "featured_media") == TARGET_FEATURED_MEDIA_ID,
        "post_update_featured_media_mismatch",
        "post-update featured_media changed",
    )
    _require(
        _value(verified, "title") == before_title,
        "post_update_title_mismatch",
        "post-update title changed",
    )
    _require(
        _value(verified, "excerpt") == before_excerpt,
        "post_update_excerpt_mismatch",
        "post-update excerpt changed",
    )
    _require(
        verified_content == after_content,
        "post_update_content_mismatch",
        "post-update content does not exactly match the planned content",
    )
    _validate_price_once(verified_content)
    _validate_rendered_buttons(
        verified_content,
        prepared_offers,
        dmm_x_url=dmm_x_url,
    )
    _require(
        _inspect(verified_content).has_image,
        "post_update_cover_image_missing",
        "post-update content lost the cover image",
    )

    result = ExistingDraftStoreButtonsUpdateResult(
        status="UPDATED_AND_VERIFIED",
        ebook_item_id=normalized_ebook_item_id,
        wordpress_post_id=requested_post_id,
        before_content_sha256=before_sha,
        after_content_sha256=after_sha,
        replacement_count=replacement_count,
        store_names=store_names,
        store_labels=store_labels,
        external_update_attempted=True,
        external_update_succeeded=True,
        verified_after_update=True,
        diagnostic_path=None,
        evidence_path=None,
    )
    evidence_path = _write_success_evidence(
        directory=Path(evidence_directory),
        result=result,
        status_before=str(_value(before, "status")),
        status_after=str(_value(verified, "status")),
        featured_media_before=int(_value(before, "featured_media")),
        featured_media_after=int(_value(verified, "featured_media")),
        now=(now_provider or (lambda: datetime.now(timezone.utc)))(),
    )
    return replace(result, evidence_path=str(evidence_path))
