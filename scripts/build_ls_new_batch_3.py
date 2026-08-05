#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/new_release_article_batch_dry_run_policy.json"
)
DEFAULT_VERIFICATION_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_verification_result.example.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_article_batch_dry_run_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_article_batch_dry_run_result.example.json"
)
DEFAULT_PREVIEW_ROOT = (
    ROOT / "exchange/output/new_release_article_previews"
)

RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_3_result.json"
REPORT_PATH = (
    ROOT / "reports/ls_new_batch_3_article_batch_dry_run_report.md"
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"required file missing: {path}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")

    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return str(resolved)


def normalize_text(
    value: Any,
    *,
    field_name: str,
    required: bool,
) -> str | None:
    if value is None:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} must be a string or null"
        )

    normalized = unicodedata.normalize("NFKC", value).strip()

    if normalized == "":
        if required:
            raise ValidationError(f"{field_name} must not be blank")
        return None

    return normalized


def validate_https_url(
    value: Any,
    *,
    field_name: str,
) -> str:
    normalized = normalize_text(
        value,
        field_name=field_name,
        required=True,
    )
    assert normalized is not None

    parsed = urlparse(normalized)

    require(
        parsed.scheme == "https" and bool(parsed.hostname),
        f"{field_name} must be a valid HTTPS URL",
    )

    return normalized


def parse_release_date(value: Any) -> str:
    normalized = normalize_text(
        value,
        field_name="release_date",
        required=True,
    )
    assert normalized is not None

    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            "release_date must use YYYY-MM-DD"
        ) from exc

    return parsed.isoformat()


def format_release_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.month}月{parsed.day}日"


def safe_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", normalized)
    slug = slug.strip("-._")

    if slug:
        return slug

    digest = hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:16]

    return f"item-{digest}"


def format_price(value: int | None) -> str:
    if value is None:
        return "価格は販売ページで確認"

    require(
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0,
        "price must be a non-negative integer or null",
    )

    return f"{value:,}円"


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-3",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_ARTICLE_BATCH_DRY_RUN_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    article = policy.get("article_generation", {})

    require(
        article.get("wordpress_status") == "draft",
        "WordPress status must remain draft",
    )
    require(
        article.get("description_mode") == "minimal",
        "description mode must remain minimal",
    )
    require(
        article.get("long_commentary_allowed") is False,
        "long commentary must remain blocked",
    )
    require(
        article.get("uncategorized_allowed") is False,
        "uncategorized must remain blocked",
    )
    require(
        article.get("store_button_order")
        == ["amazon", "rakuten_kobo", "dmm"],
        "store button order mismatch",
    )
    checks.append("post185_article_contract")

    x_policy = policy.get("x_candidate_generation", {})

    require(
        x_policy.get("automatic_post_allowed") is False,
        "automatic X posting must remain blocked",
    )
    require(
        x_policy.get("hashtags_allowed") is False,
        "hashtags must remain blocked in V1",
    )
    require(
        x_policy.get("emoji_allowed") is False,
        "emoji must remain blocked in V1",
    )
    require(
        x_policy.get("manual_review_required") is True,
        "X candidate must require manual review",
    )
    checks.append("x_candidate_boundary")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "external_api_call_allowed",
        "web_scraping_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "x_api_call_allowed",
        "x_post_allowed",
        "automatic_rule_update_allowed",
    ]:
        require(
            boundary.get(field) is False,
            f"{field} must remain false",
        )

    require(
        boundary.get("production_status") == "NO_GO",
        "production status must remain NO_GO",
    )
    require(
        boundary.get("safety_state") == "DRY_RUN_ONLY",
        "safety state must remain DRY_RUN_ONLY",
    )
    checks.append("execution_boundary")

    return checks


def validate_request(
    request: dict[str, Any],
    verification: dict[str, Any],
) -> None:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-3",
        "request phase_id mismatch",
    )
    require(
        request.get("batch_id") == verification.get("batch_id"),
        "request batch_id mismatch",
    )
    require(
        request.get("generation_mode") == "PREVIEW_ONLY",
        "generation_mode must be PREVIEW_ONLY",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be a positive integer",
    )

    options = request.get("generation_options")

    require(
        isinstance(options, dict),
        "generation_options must be an object",
    )

    required_options = [
        "include_article_html",
        "include_price_cards",
        "include_store_buttons",
        "include_x_candidate",
        "include_x_feedback_initialize_request",
    ]

    for option in required_options:
        require(
            options.get(option) is True,
            f"{option} must be true in LS-NEW-BATCH-3",
        )


def validate_verification_input(
    verification: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    require(
        verification.get("phase_id") == "LS-NEW-BATCH-2",
        "verification phase_id mismatch",
    )
    require(
        verification.get("policy_id")
        == policy.get("verification_policy_id"),
        "verification policy reference mismatch",
    )
    require(
        verification.get("template_contract_id")
        == policy.get("template_contract_id"),
        "template contract reference mismatch",
    )

    items = verification.get("items")

    require(
        isinstance(items, list),
        "verification items must be a list",
    )
    require(
        verification.get("record_count") == len(items),
        "verification record_count mismatch",
    )


def validate_ready_item(
    item: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    item_id = normalize_text(
        item.get("item_id"),
        field_name="item_id",
        required=True,
    )
    assert item_id is not None

    title = normalize_text(
        item.get("title"),
        field_name=f"{item_id}.title",
        required=True,
    )
    volume_label = normalize_text(
        item.get("volume_label"),
        field_name=f"{item_id}.volume_label",
        required=True,
    )
    publisher = normalize_text(
        item.get("publisher"),
        field_name=f"{item_id}.publisher",
        required=True,
    )

    assert title is not None
    assert volume_label is not None
    assert publisher is not None

    authors = item.get("authors")

    require(
        isinstance(authors, list) and len(authors) >= 1,
        f"{item_id}.authors must contain at least one author",
    )

    normalized_authors = [
        normalize_text(
            author,
            field_name=f"{item_id}.authors",
            required=True,
        )
        for author in authors
    ]

    category = normalize_text(
        item.get("category"),
        field_name=f"{item_id}.category",
        required=True,
    )
    assert category is not None

    category_mapping = policy[
        "article_generation"
    ]["category_mapping"]

    require(
        category in category_mapping,
        f"{item_id}: unsupported category: {category}",
    )

    release_date = parse_release_date(
        item.get("release_date")
    )

    resolved_image = item.get("resolved_image")

    require(
        isinstance(resolved_image, dict),
        f"{item_id}.resolved_image must be an object",
    )

    image_url = validate_https_url(
        resolved_image.get("url"),
        field_name=f"{item_id}.resolved_image.url",
    )

    image_source = normalize_text(
        resolved_image.get("source"),
        field_name=f"{item_id}.resolved_image.source",
        required=True,
    )
    assert image_source is not None

    links = item.get("resolved_store_links")
    prices = item.get("resolved_prices_jpy")
    stores = item.get("stores")

    require(
        isinstance(links, dict),
        f"{item_id}.resolved_store_links must be an object",
    )
    require(
        isinstance(prices, dict),
        f"{item_id}.resolved_prices_jpy must be an object",
    )
    require(
        isinstance(stores, dict),
        f"{item_id}.stores must be an object",
    )

    store_order = policy[
        "article_generation"
    ]["store_button_order"]

    normalized_stores: list[dict[str, Any]] = []

    for store_name in store_order:
        store_observation = stores.get(store_name)

        require(
            isinstance(store_observation, dict),
            f"{item_id}.stores.{store_name} must be an object",
        )

        status = store_observation.get("status")
        link = links.get(store_name)
        price = prices.get(store_name)

        if status != "FOUND":
            require(
                link is None,
                f"{item_id}: non-found {store_name} "
                "must not have a resolved URL",
            )
            continue

        validated_link = validate_https_url(
            link,
            field_name=(
                f"{item_id}.resolved_store_links.{store_name}"
            ),
        )

        if price is not None:
            require(
                isinstance(price, int)
                and not isinstance(price, bool)
                and price >= 0,
                f"{item_id}: invalid {store_name} price",
            )

        normalized_stores.append(
            {
                "store_name": store_name,
                "url": validated_link,
                "price_jpy": price,
            }
        )

    require(
        len(normalized_stores) >= 2,
        f"{item_id}: READY_FOR_DRAFT requires "
        "at least two found stores",
    )
    require(
        any(
            store["price_jpy"] is not None
            for store in normalized_stores
        ),
        f"{item_id}: READY_FOR_DRAFT requires "
        "at least one confirmed price",
    )

    mismatches = item.get("mismatches", [])

    require(
        isinstance(mismatches, list) and len(mismatches) == 0,
        f"{item_id}: READY_FOR_DRAFT must not contain mismatches",
    )

    return {
        "item_id": item_id,
        "batch_id": normalize_text(
            item.get("batch_id"),
            field_name=f"{item_id}.batch_id",
            required=True,
        ),
        "title": title,
        "volume_label": volume_label,
        "release_date": release_date,
        "publisher": publisher,
        "authors": normalized_authors,
        "category": category,
        "category_definition": category_mapping[category],
        "image": {
            "source": image_source,
            "url": image_url,
        },
        "stores": normalized_stores,
    }


def render_store_cards(
    normalized: dict[str, Any],
    policy: dict[str, Any],
) -> str:
    display_names = policy[
        "article_generation"
    ]["store_display_names"]

    cards: list[str] = []

    for store in normalized["stores"]:
        store_name = store["store_name"]
        display_name = display_names[store_name]
        price_text = format_price(store["price_jpy"])

        cards.append(
            "\n".join(
                [
                    (
                        '<div class="ebook-price-card" '
                        f'data-store="{html.escape(store_name)}">'
                    ),
                    (
                        '  <p class="ebook-store-name">'
                        f"{html.escape(display_name)}</p>"
                    ),
                    (
                        '  <p class="ebook-store-price">'
                        f"{html.escape(price_text)}</p>"
                    ),
                    (
                        '  <a class="ebook-store-button" '
                        f'href="{html.escape(store["url"], quote=True)}" '
                        'target="_blank" '
                        'rel="nofollow sponsored noopener">'
                        f"{html.escape(display_name)}で確認"
                        "</a>"
                    ),
                    "</div>",
                ]
            )
        )

    return "\n".join(cards)


def render_article_html(
    normalized: dict[str, Any],
    policy: dict[str, Any],
) -> str:
    title_with_volume = (
        f"{normalized['title']} {normalized['volume_label']}"
    )
    release_date_text = format_release_date(
        normalized["release_date"]
    )
    author_text = "／".join(normalized["authors"])
    category_name = normalized[
        "category_definition"
    ]["category_name"]

    store_cards = render_store_cards(
        normalized=normalized,
        policy=policy,
    )

    return "\n".join(
        [
            (
                '<div class="ebook-new-release-article" '
                'data-template-id="POST185_STANDARD_TEMPLATE_V1">'
            ),
            (
                '  <p class="ebook-pr-disclosure">'
                "※本記事にはアフィリエイト広告を含みます。"
                "</p>"
            ),
            '  <div class="ebook-release-layout">',
            '    <figure class="ebook-cover-image">',
            (
                '      <img '
                f'src="{html.escape(normalized["image"]["url"], quote=True)}" '
                f'alt="{html.escape(title_with_volume, quote=True)}の書影" '
                'loading="lazy">'
            ),
            "    </figure>",
            '    <section class="ebook-release-summary">',
            (
                "      <h2>"
                f"{html.escape(title_with_volume)}"
                "</h2>"
            ),
            "      <ul>",
            (
                "        <li>発売日："
                f"{html.escape(release_date_text)}</li>"
            ),
            (
                "        <li>著者："
                f"{html.escape(author_text)}</li>"
            ),
            (
                "        <li>出版社："
                f"{html.escape(normalized['publisher'])}</li>"
            ),
            (
                "        <li>分類："
                f"{html.escape(category_name)}</li>"
            ),
            "      </ul>",
            "    </section>",
            "  </div>",
            '  <section class="ebook-store-section">',
            "    <h2>電子書籍ストアの価格・販売ページ</h2>",
            (
                '    <div class="ebook-price-card-grid">'
            ),
            store_cards,
            "    </div>",
            "  </section>",
            "</div>",
            "",
        ]
    )


def build_x_candidate(
    normalized: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    release_date_text = format_release_date(
        normalized["release_date"]
    )

    store_names = policy[
        "article_generation"
    ]["store_display_names"]

    found_store_names = [
        store_names[store["store_name"]]
        for store in normalized["stores"]
    ]

    text = (
        f"『{normalized['title']} "
        f"{normalized['volume_label']}』は"
        f"{release_date_text}発売。\n"
        f"{'・'.join(found_store_names)}の価格と"
        "販売ページを記事でまとめています。"
    )

    max_characters = policy[
        "x_candidate_generation"
    ]["max_text_characters_without_url"]

    require(
        len(text) <= max_characters,
        f"{normalized['item_id']}: X candidate exceeds "
        f"{max_characters} characters",
    )
    require(
        "#" not in text,
        f"{normalized['item_id']}: hashtags are forbidden",
    )

    return {
        "template_id": policy[
            "x_candidate_generation"
        ]["template_id"],
        "candidate_text_without_url": text,
        "character_count_without_url": len(text),
        "reserved_url_characters": policy[
            "x_candidate_generation"
        ]["reserved_url_characters"],
        "requires_manual_review": True,
        "requires_article_url_append": True,
        "automatic_post_allowed": False,
        "wording_labels": [
            "TITLE_FIRST",
            "INFORMATIONAL_TONE",
            "ARTICLE_CTA",
            "NO_EMOJI",
            "NO_HASHTAG",
        ],
    }


def build_feedback_initialize_request(
    normalized: dict[str, Any],
    x_candidate: dict[str, Any],
) -> dict[str, Any]:
    feedback_id = safe_slug(
        "x-fb-"
        + normalized["batch_id"]
        + "-"
        + normalized["item_id"]
    )

    return {
        "action": "INITIALIZE",
        "feedback_id": feedback_id,
        "article_item_id": normalized["item_id"],
        "wordpress_post_id": None,
        "template_id": x_candidate["template_id"],
        "article_context": {
            "title": normalized["title"],
            "volume_label": normalized["volume_label"],
            "release_date": normalized["release_date"],
            "category": normalized["category"],
        },
        "generated_text": x_candidate[
            "candidate_text_without_url"
        ],
        "wording_labels": x_candidate[
            "wording_labels"
        ],
    }


def build_generated_item(
    item: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    normalized = validate_ready_item(
        item=item,
        policy=policy,
    )

    title_with_volume = (
        f"{normalized['title']} {normalized['volume_label']}"
    )

    article_html = render_article_html(
        normalized=normalized,
        policy=policy,
    )

    x_candidate = build_x_candidate(
        normalized=normalized,
        policy=policy,
    )

    feedback_request = build_feedback_initialize_request(
        normalized=normalized,
        x_candidate=x_candidate,
    )

    post_slug = safe_slug(normalized["item_id"])

    article_payload = {
        "post_title": (
            f"『{title_with_volume}』"
            "電子書籍版の発売日・価格情報"
        ),
        "post_name": post_slug,
        "post_status": "draft",
        "category_slug": normalized[
            "category_definition"
        ]["category_slug"],
        "category_name": normalized[
            "category_definition"
        ]["category_name"],
        "uncategorized_assigned": False,
        "template_id": "POST185_STANDARD_TEMPLATE_V1",
        "description_mode": "minimal",
        "post_excerpt": (
            f"『{title_with_volume}』の発売日と"
            "電子書籍ストア情報をまとめています。"
        ),
        "content_html": article_html,
        "metadata": {
            "item_id": normalized["item_id"],
            "batch_id": normalized["batch_id"],
            "release_date": normalized["release_date"],
            "image_source": normalized["image"]["source"],
            "store_button_order": [
                store["store_name"]
                for store in normalized["stores"]
            ],
        },
    }

    digest_source = {
        "article_payload": article_payload,
        "x_candidate": x_candidate,
        "x_feedback_initialize_request": feedback_request,
    }

    digest = hashlib.sha256(
        json.dumps(
            digest_source,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "item_id": normalized["item_id"],
        "source_classification": "READY_FOR_DRAFT",
        "article_payload": article_payload,
        "x_candidate": x_candidate,
        "x_feedback_initialize_request": feedback_request,
        "preview_digest_sha256": digest,
        "wordpress_write_allowed": False,
        "x_post_allowed": False,
    }


def build_output(
    verification: dict[str, Any],
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    validate_request(
        request=request,
        verification=verification,
    )
    validate_verification_input(
        verification=verification,
        policy=policy,
    )

    eligible = set(policy["eligible_classifications"])

    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in verification["items"]:
        classification = item.get(
            "verification_classification"
        )

        if classification not in eligible:
            skipped.append(
                {
                    "item_id": item.get("item_id"),
                    "classification": classification,
                    "reason": "NOT_READY_FOR_DRAFT",
                }
            )
            continue

        generated.append(
            build_generated_item(
                item=item,
                policy=policy,
            )
        )

    return {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-3",
        "policy_id": policy["policy_id"],
        "template_contract_id": policy[
            "template_contract_id"
        ],
        "batch_id": verification["batch_id"],
        "generation_mode": "PREVIEW_ONLY",
        "source_record_count": len(
            verification["items"]
        ),
        "generated_item_count": len(generated),
        "skipped_item_count": len(skipped),
        "generated_items": generated,
        "skipped_items": skipped,
        "execution_boundary": {
            "external_api_call_allowed": False,
            "web_scraping_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
            "automatic_rule_update_allowed": False,
            "production_status": "NO_GO",
            "safety_state": "DRY_RUN_ONLY",
        },
    }


def build_phase_result(
    *,
    policy_checks: list[str],
    output: dict[str, Any],
    verification_path: Path,
    request_path: Path,
    output_path: Path,
    preview_paths: list[Path],
) -> dict[str, Any]:
    return {
        "phase_id": "LS-NEW-BATCH-3",
        "status": "PASS_ARTICLE_BATCH_DRY_RUN_NO_LIVE_WRITE",
        "decision": "POST185_ARTICLE_AND_X_PREVIEW_GENERATOR_READY",
        "policy_id": output["policy_id"],
        "template_contract_id": output[
            "template_contract_id"
        ],
        "batch_id": output["batch_id"],
        "verification_input_path": display_path(
            verification_path
        ),
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "preview_paths": [
            display_path(path)
            for path in preview_paths
        ],
        "source_record_count": output[
            "source_record_count"
        ],
        "generated_item_count": output[
            "generated_item_count"
        ],
        "skipped_item_count": output[
            "skipped_item_count"
        ],
        "verified_checks": policy_checks
        + [
            "eligible_classification_filter",
            "ready_item_defense_validation",
            "post185_html_rendering",
            "price_card_rendering",
            "fixed_store_button_order",
            "uncategorized_exclusion",
            "x_candidate_generation",
            "x_feedback_initialize_request_generation",
            "deterministic_preview_digest",
        ],
        "external_api_call_allowed": False,
        "web_scraping_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "x_api_call_allowed": False,
        "x_post_allowed": False,
        "automatic_rule_update_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
        "ready_for_real_ready_item_dry_run": True,
        "ready_for_ls_new_batch_4": True,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    previews = (
        "\n".join(
            f"- `{path}`"
            for path in result["preview_paths"]
        )
        if result["preview_paths"]
        else "- 生成対象なし"
    )

    return f"""# LS-NEW-BATCH-3 Article Batch Dry-Run Report

## Result

- Phase: `LS-NEW-BATCH-3`
- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Policy: `{result["policy_id"]}`
- Template contract: `{result["template_contract_id"]}`
- Batch: `{result["batch_id"]}`
- Source records: `{result["source_record_count"]}`
- Generated items: `{result["generated_item_count"]}`
- Skipped items: `{result["skipped_item_count"]}`

## HTML Previews

{previews}

## Verified Checks

{checks}

## Safety Boundary

- External API call allowed: `false`
- Web scraping allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X API call allowed: `false`
- X posting allowed: `false`
- Automatic wording-rule update allowed: `false`
- Production status: `NO_GO`
- Safety state: `DRY_RUN_ONLY`

## Next State

`READY_FOR_DRAFT` の作品だけをpost_id=185標準テンプレート準拠の
記事ペイロード、HTMLプレビュー、X候補文、X-FB初期化要求へ
変換できます。

WordPress下書き作成およびX投稿は実行していません。
"""


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--verification",
        type=Path,
        default=DEFAULT_VERIFICATION_PATH,
    )
    parser.add_argument(
        "--request",
        type=Path,
        default=DEFAULT_REQUEST_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    parser.add_argument(
        "--preview-root",
        type=Path,
        default=DEFAULT_PREVIEW_ROOT,
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    verification_path = resolve_path(args.verification)
    request_path = resolve_path(args.request)
    output_path = resolve_path(args.output)
    preview_root = resolve_path(args.preview_root)

    try:
        policy = load_json(POLICY_PATH)
        verification = load_json(verification_path)
        request = load_json(request_path)

        policy_checks = validate_policy(policy)

        output = build_output(
            verification=verification,
            request=request,
            policy=policy,
        )

        preview_paths = [
            (
                preview_root
                / safe_slug(output["batch_id"])
                / (
                    item["article_payload"]["post_name"]
                    + ".html"
                )
            )
            for item in output["generated_items"]
        ]

        result = build_phase_result(
            policy_checks=policy_checks,
            output=output,
            verification_path=verification_path,
            request_path=request_path,
            output_path=output_path,
            preview_paths=preview_paths,
        )

        if not args.check_only:
            write_json(output_path, output)

            for item, preview_path in zip(
                output["generated_items"],
                preview_paths,
                strict=True,
            ):
                write_text(
                    preview_path,
                    item["article_payload"][
                        "content_html"
                    ],
                )

            write_json(RESULT_PATH, result)

            REPORT_PATH.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            REPORT_PATH.write_text(
                build_report(result),
                encoding="utf-8",
            )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": "LS-NEW-BATCH-3",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "wordpress_write_allowed": False,
                    "x_post_allowed": False,
                    "external_api_call_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
