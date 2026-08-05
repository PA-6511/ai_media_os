from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-DRAFT-RENDER-DRY-RUN"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_DESIGN_DIGEST = (
    "62f72e88d48e4b9b09ee19bbf6298b39"
    "38ef83595b6951dba40f905e201caf90"
)

EXPECTED_INPUT_DIGEST = (
    "f08301106c3475168d31f53c13ffa3e8"
    "83e0bdb7889de06196e9a21b48256337"
)

EXPECTED_DISCOVERY_DIGEST = (
    "006c8d083fe434e4c603342a99a160fe"
    "0b157a67a1f09c66f64fd4afd05e0b74"
)

EXPECTED_CONTRACT_ID = (
    "X_R11_LOCAL_WORDPRESS_DRAFT_TEMPLATE_V1"
)

EXPECTED_TITLE = "のあ先輩はともだち。"
EXPECTED_VOLUME_LABEL = "第11巻"
EXPECTED_AUTHOR = "あきやまえんま"
EXPECTED_PUBLISHER = "集英社"
EXPECTED_RELEASE_DATE = "2026-07-17"

EXPECTED_POST_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_POST_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_COVER_SHA256 = (
    "fcd5ed6e8a2136f45a380e055d3a34e7"
    "fe1e0d90cfaed9c8bcc8839c95a890c7"
)

EXPECTED_COVER_WIDTH = 300
EXPECTED_COVER_HEIGHT = 373

EXPECTED_AFFILIATE_PRODUCT_HASH = (
    "bce9f1878b0032dc4745ecf22fd179a6"
)

BLOCKED_OLD_AFFILIATE_PRODUCT_HASH = (
    "f402536ea6473a172c957407fae06192"
)

ALLOWED_AFFILIATE_HOSTS = {
    "hb.afl.rakuten.co.jp",
    "a.r10.to",
}

ALLOWED_COVER_HOSTS = {
    "shop.r10s.jp",
    "tshop.r10s.jp",
}

REQUIRED_MARKERS = (
    "ebook-new-release-article",
    "ebook-pr-disclosure",
    "ebook-cover-image",
    "price-cards",
    "store-buttons",
)

REQUIRED_PLACEHOLDERS = (
    "title",
    "volume_label",
    "release_date_display",
    "publisher_name",
    "author_name",
    "cover_image_url",
    "cover_image_alt",
    "rakuten_affiliate_url",
)

AFFILIATE_KEY_NAMES = {
    "rakuten_affiliate_url",
    "rakuten_tracking_url",
    "affiliate_url",
    "tracking_url",
}


class RenderDryRunError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RenderDryRunError(message)


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise RenderDryRunError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def verify_canonical_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str,
    label: str,
) -> None:
    recorded = value.get(
        digest_field
    )

    require(
        recorded == expected_digest,
        f"{label} digest mismatch",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == expected_digest,
        f"{label} digest verification failed",
    )


def atomic_write_text(
    path: Path,
    value: str,
) -> None:
    path = path.resolve()
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    temporary.write_text(
        value,
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


def find_values_for_keys(
    value: Any,
    keys: set[str],
) -> list[str]:
    results: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if (
                key in keys
                and isinstance(item, str)
                and item.strip()
            ):
                results.append(
                    item.strip()
                )

            results.extend(
                find_values_for_keys(
                    item,
                    keys,
                )
            )

    elif isinstance(value, list):
        for item in value:
            results.extend(
                find_values_for_keys(
                    item,
                    keys,
                )
            )

    return results


def resolve_required_string(
    value: dict[str, Any],
    *,
    keys: tuple[str, ...],
    label: str,
) -> str:
    values = find_values_for_keys(
        value,
        set(keys),
    )

    unique = list(
        dict.fromkeys(values)
    )

    require(
        len(unique) == 1,
        (
            f"{label} must resolve to exactly "
            f"one value; found={unique!r}"
        ),
    )

    return unique[0]


def release_date_display(
    value: str,
) -> str:
    try:
        parsed = date.fromisoformat(
            value
        )
    except ValueError as exc:
        raise RenderDryRunError(
            (
                "release date must use "
                f"YYYY-MM-DD: {value!r}"
            )
        ) from exc

    return (
        f"{parsed.year}年"
        f"{parsed.month}月"
        f"{parsed.day}日"
    )


def validate_https_url(
    url: str,
    *,
    allowed_hosts: set[str],
    label: str,
) -> str:
    parsed = urlparse(url)

    require(
        parsed.scheme == "https",
        f"{label} must use HTTPS",
    )

    hostname = (
        parsed.hostname or ""
    ).casefold()

    require(
        hostname in allowed_hosts,
        (
            f"{label} host is not allowed: "
            f"{hostname!r}"
        ),
    )

    require(
        not parsed.username
        and not parsed.password,
        (
            f"{label} must not include "
            "URL credentials"
        ),
    )

    return hostname


def resolve_affiliate_url(
    input_pack: dict[str, Any],
) -> str:
    values = find_values_for_keys(
        input_pack,
        AFFILIATE_KEY_NAMES,
    )

    allowed_values: list[str] = []

    for value in values:
        try:
            validate_https_url(
                value,
                allowed_hosts=(
                    ALLOWED_AFFILIATE_HOSTS
                ),
                label="Rakuten affiliate URL",
            )
        except RenderDryRunError:
            continue

        allowed_values.append(value)

    unique = list(
        dict.fromkeys(
            allowed_values
        )
    )

    require(
        unique,
        (
            "no permitted Rakuten affiliate "
            "URL was found"
        ),
    )

    require(
        all(
            BLOCKED_OLD_AFFILIATE_PRODUCT_HASH
            not in value
            for value in unique
        ),
        (
            "superseded affiliate product "
            "hash was found"
        ),
    )

    preferred = [
        value
        for value in unique
        if (
            EXPECTED_AFFILIATE_PRODUCT_HASH
            in value
        )
    ]

    if preferred:
        require(
            len(preferred) == 1,
            (
                "multiple current affiliate "
                "URLs were found"
            ),
        )
        return preferred[0]

    require(
        len(unique) == 1,
        (
            "affiliate URL is ambiguous and "
            "the expected product hash was "
            "not present"
        ),
    )

    return unique[0]


def validate_slug(
    value: str,
) -> None:
    require(
        re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*",
            value,
        )
        is not None,
        "WordPress slug is invalid",
    )

    require(
        len(value) <= 80,
        "WordPress slug is too long",
    )


def render_template(
    template_html: str,
    replacements: dict[str, str],
) -> tuple[
    str,
    dict[str, int],
]:
    actual_placeholders = set(
        re.findall(
            r"\{\{([a-z][a-z0-9_]*)\}\}",
            template_html,
        )
    )

    expected_placeholders = set(
        REQUIRED_PLACEHOLDERS
    )

    require(
        actual_placeholders
        == expected_placeholders,
        (
            "template placeholder set mismatch; "
            f"actual={sorted(actual_placeholders)!r}"
        ),
    )

    require(
        set(replacements)
        == expected_placeholders,
        "replacement value set mismatch",
    )

    rendered = template_html
    replacement_counts: dict[str, int] = {}

    for placeholder in REQUIRED_PLACEHOLDERS:
        token = "{{" + placeholder + "}}"

        count = rendered.count(token)

        require(
            count >= 1,
            (
                "template placeholder "
                f"is missing: {placeholder}"
            ),
        )

        replacement_counts[
            placeholder
        ] = count

        rendered = rendered.replace(
            token,
            html.escape(
                replacements[placeholder],
                quote=True,
            ),
        )

    unresolved = re.findall(
        r"\{\{[^{}]+\}\}",
        rendered,
    )

    require(
        not unresolved,
        (
            "unresolved template tokens remain: "
            f"{unresolved!r}"
        ),
    )

    return (
        rendered,
        replacement_counts,
    )


def validate_rendered_html(
    rendered_html: str,
    *,
    affiliate_url: str,
    cover_image_url: str,
) -> dict[str, Any]:
    missing_markers = [
        marker
        for marker in REQUIRED_MARKERS
        if marker not in rendered_html
    ]

    require(
        not missing_markers,
        (
            "rendered markers are missing: "
            + ", ".join(missing_markers)
        ),
    )

    for forbidden_tag in (
        "script",
        "iframe",
        "form",
        "input",
        "button",
        "object",
        "embed",
    ):
        require(
            re.search(
                rf"<\s*{forbidden_tag}\b",
                rendered_html,
                flags=re.IGNORECASE,
            )
            is None,
            (
                "rendered HTML contains "
                f"forbidden tag: {forbidden_tag}"
            ),
        )

    require(
        re.search(
            r"\son[a-z]+\s*=",
            rendered_html,
            flags=re.IGNORECASE,
        )
        is None,
        (
            "rendered HTML contains an "
            "inline event handler"
        ),
    )

    require(
        re.search(
            r"\sstyle\s*=",
            rendered_html,
            flags=re.IGNORECASE,
        )
        is None,
        "rendered HTML contains inline style",
    )

    escaped_affiliate_url = html.escape(
        affiliate_url,
        quote=True,
    )

    escaped_cover_url = html.escape(
        cover_image_url,
        quote=True,
    )

    require(
        (
            'href="'
            + escaped_affiliate_url
            + '"'
        )
        in rendered_html,
        (
            "rendered affiliate URL "
            "is missing"
        ),
    )

    require(
        (
            'src="'
            + escaped_cover_url
            + '"'
        )
        in rendered_html,
        "rendered cover URL is missing",
    )

    require(
        rendered_html.count(
            'class="store-button '
            'store-button-rakuten-kobo"'
        )
        == 1,
        (
            "rendered HTML must contain "
            "exactly one Rakuten store button"
        ),
    )

    require(
        (
            'rel="sponsored nofollow '
            'noopener noreferrer"'
        )
        in rendered_html,
        "affiliate rel policy is missing",
    )

    require(
        'target="_blank"'
        in rendered_html,
        (
            "affiliate target policy "
            "is missing"
        ),
    )

    require(
        BLOCKED_OLD_AFFILIATE_PRODUCT_HASH
        not in rendered_html,
        (
            "superseded affiliate product "
            "hash appears in rendered HTML"
        ),
    )

    return {
        "required_markers": {
            marker: True
            for marker in REQUIRED_MARKERS
        },
        "unresolved_placeholders": [],
        "forbidden_tags_found": [],
        "inline_event_handlers_found": False,
        "inline_styles_found": False,
        "rakuten_store_button_count": 1,
        "affiliate_rel_verified": True,
        "affiliate_target_blank_verified": True,
        "affiliate_url_verified": True,
        "cover_image_url_verified": True,
        "old_affiliate_hash_absent": True,
        "rendered_html_validation_passed": True,
    }


def build_render_dry_run(
    *,
    production_database_path: Path,
    design_pack_path: Path,
    input_pack_path: Path,
    discovery_pack_path: Path,
    template_path: Path,
    rendered_html_path: Path,
    payload_preview_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    design_pack_path = (
        design_pack_path.resolve()
    )

    input_pack_path = (
        input_pack_path.resolve()
    )

    discovery_pack_path = (
        discovery_pack_path.resolve()
    )

    template_path = template_path.resolve()
    rendered_html_path = (
        rendered_html_path.resolve()
    )

    payload_preview_path = (
        payload_preview_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    design = load_json(
        design_pack_path
    )

    inputs = load_json(
        input_pack_path
    )

    discovery = load_json(
        discovery_pack_path
    )

    verify_canonical_digest(
        design,
        digest_field=(
            "local_wordpress_draft_template_"
            "contract_design_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_DESIGN_DIGEST
        ),
        label="local template design pack",
    )

    verify_canonical_digest(
        inputs,
        digest_field=(
            "wordpress_draft_input_fixing_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_INPUT_DIGEST
        ),
        label="WordPress input pack",
    )

    verify_canonical_digest(
        discovery,
        digest_field=(
            "wordpress_draft_render_input_"
            "discovery_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_DISCOVERY_DIGEST
        ),
        label="render input discovery pack",
    )

    require(
        design.get("status")
        == (
            "PASS_LOCAL_WORDPRESS_DRAFT_"
            "TEMPLATE_CONTRACT_FIXED"
        ),
        "local template design did not pass",
    )

    require(
        discovery.get("status")
        == (
            "PASS_WORDPRESS_DRAFT_"
            "RENDER_INPUT_DISCOVERY"
        ),
        "render input discovery did not pass",
    )

    require(
        discovery.get(
            "discovery_state"
        )
        == (
            "COVER_IMAGE_VERIFIED_"
            "RENDER_DRY_RUN_READY"
        ),
        "render input discovery is not ready",
    )

    require(
        discovery.get(
            "remaining_render_input_count"
        )
        == 0,
        "render inputs remain unresolved",
    )

    require(
        discovery.get(
            "render_dry_run_allowed"
        )
        is True,
        "render dry run is not allowed",
    )

    require(
        discovery.get(
            "draft_creation_allowed"
        )
        is False,
        (
            "draft creation must remain "
            "blocked"
        ),
    )

    require(
        design[
            "local_template_contract"
        ]["contract_id"]
        == EXPECTED_CONTRACT_ID,
        "template contract ID mismatch",
    )

    require(
        design[
            "local_template_contract"
        ]["wordpress_category_id"]
        == 43,
        "WordPress category mismatch",
    )

    require(
        template_path.is_file(),
        "HTML template is missing",
    )

    template_html = template_path.read_text(
        encoding="utf-8"
    )

    expected_template_sha = design[
        "local_template_contract"
    ]["template_sha256"]

    require(
        sha256_text(template_html)
        == expected_template_sha,
        (
            "HTML template changed after "
            "contract fixation"
        ),
    )

    title = resolve_required_string(
        inputs,
        keys=("title",),
        label="title",
    )

    volume_label = resolve_required_string(
        inputs,
        keys=("volume_label",),
        label="volume label",
    )

    author_name = resolve_required_string(
        inputs,
        keys=("author_name",),
        label="author name",
    )

    publisher_name = (
        resolve_required_string(
            inputs,
            keys=(
                "publisher_name",
                "publisher",
            ),
            label="publisher name",
        )
    )

    release_date_value = (
        resolve_required_string(
            inputs,
            keys=("release_date",),
            label="release date",
        )
    )

    require(
        title == EXPECTED_TITLE,
        "title mismatch",
    )

    require(
        volume_label
        == EXPECTED_VOLUME_LABEL,
        "volume label mismatch",
    )

    require(
        author_name == EXPECTED_AUTHOR,
        "author mismatch",
    )

    require(
        publisher_name
        == EXPECTED_PUBLISHER,
        "publisher mismatch",
    )

    require(
        release_date_value
        == EXPECTED_RELEASE_DATE,
        "release date mismatch",
    )

    affiliate_url = resolve_affiliate_url(
        inputs
    )

    affiliate_hostname = (
        validate_https_url(
            affiliate_url,
            allowed_hosts=(
                ALLOWED_AFFILIATE_HOSTS
            ),
            label="Rakuten affiliate URL",
        )
    )

    cover = discovery.get(
        "cover_image"
    )

    require(
        isinstance(cover, dict),
        "cover image evidence is missing",
    )

    cover_image_url = str(
        cover.get(
            "cover_image_url",
            "",
        )
    )

    cover_image_alt = str(
        cover.get(
            "cover_image_alt",
            "",
        )
    )

    cover_hostname = validate_https_url(
        cover_image_url,
        allowed_hosts=(
            ALLOWED_COVER_HOSTS
        ),
        label="cover image URL",
    )

    require(
        cover.get("sha256")
        == EXPECTED_COVER_SHA256,
        "cover image SHA mismatch",
    )

    require(
        cover.get("width")
        == EXPECTED_COVER_WIDTH,
        "cover image width mismatch",
    )

    require(
        cover.get("height")
        == EXPECTED_COVER_HEIGHT,
        "cover image height mismatch",
    )

    require(
        cover.get(
            "cover_image_url_verified"
        )
        is True,
        "cover image URL is not verified",
    )

    require(
        discovery[
            "image_usage_policy"
        ][
            "source_image_hotlink_approved"
        ]
        is False,
        (
            "source-image hotlink policy "
            "unexpectedly changed"
        ),
    )

    validate_slug(
        EXPECTED_POST_SLUG
    )

    replacements = {
        "title": title,
        "volume_label": volume_label,
        "release_date_display": (
            release_date_display(
                release_date_value
            )
        ),
        "publisher_name": (
            publisher_name
        ),
        "author_name": author_name,
        "cover_image_url": (
            cover_image_url
        ),
        "cover_image_alt": (
            cover_image_alt
        ),
        "rakuten_affiliate_url": (
            affiliate_url
        ),
    }

    rendered_html, replacement_counts = (
        render_template(
            template_html,
            replacements,
        )
    )

    rendered_validation = (
        validate_rendered_html(
            rendered_html,
            affiliate_url=affiliate_url,
            cover_image_url=(
                cover_image_url
            ),
        )
    )

    rendered_html_sha256 = sha256_text(
        rendered_html
    )

    wordpress_request = {
        "title": EXPECTED_POST_TITLE,
        "slug": EXPECTED_POST_SLUG,
        "status": "draft",
        "categories": [43],
        "content": rendered_html,
    }

    payload_preview_payload = {
        "preview_only": True,
        "execution_allowed": False,
        "wordpress_api_method": (
            "NOT_CALLED"
        ),
        "maximum_post_create_count": 1,
        "wordpress_request": (
            wordpress_request
        ),
    }

    payload_preview = {
        **payload_preview_payload,
        "wordpress_draft_payload_preview_"
        "digest_sha256": (
            canonical_digest(
                payload_preview_payload
            )
        ),
    }

    atomic_write_text(
        rendered_html_path,
        rendered_html,
    )

    atomic_write_json(
        payload_preview_path,
        payload_preview,
    )

    dry_run_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_DRAFT_"
            "RENDER_DRY_RUN"
        ),
        "render_state": (
            "LOCAL_RENDER_COMPLETE_"
            "HUMAN_REVIEW_REQUIRED"
        ),
        "rendered_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_design_pack_path": str(
            design_pack_path
        ),
        "source_design_pack_digest_sha256": (
            EXPECTED_DESIGN_DIGEST
        ),
        "source_input_pack_path": str(
            input_pack_path
        ),
        "source_input_pack_digest_sha256": (
            EXPECTED_INPUT_DIGEST
        ),
        "source_discovery_pack_path": str(
            discovery_pack_path
        ),
        "source_discovery_pack_digest_sha256": (
            EXPECTED_DISCOVERY_DIGEST
        ),
        "production_database_path": str(
            production_database_path
        ),
        "required_production_database_sha256": (
            EXPECTED_DATABASE_SHA
        ),
        "template_contract_id": (
            EXPECTED_CONTRACT_ID
        ),
        "template_path": str(
            template_path
        ),
        "template_sha256": (
            expected_template_sha
        ),
        "post_preview": {
            "title": EXPECTED_POST_TITLE,
            "slug": EXPECTED_POST_SLUG,
            "status": "draft",
            "category_ids": [43],
            "category_name": "コミック新刊",
            "maximum_post_create_count": 1,
        },
        "render_inputs": {
            "title": title,
            "volume_label": volume_label,
            "release_date": (
                release_date_value
            ),
            "release_date_display": (
                replacements[
                    "release_date_display"
                ]
            ),
            "publisher_name": (
                publisher_name
            ),
            "author_name": author_name,
            "cover_image_url": (
                cover_image_url
            ),
            "cover_image_alt": (
                cover_image_alt
            ),
            "affiliate_hostname": (
                affiliate_hostname
            ),
            "cover_hostname": (
                cover_hostname
            ),
        },
        "replacement_counts": (
            replacement_counts
        ),
        "rendered_validation": (
            rendered_validation
        ),
        "rendered_html_path": str(
            rendered_html_path
        ),
        "rendered_html_sha256": (
            rendered_html_sha256
        ),
        "rendered_html_byte_size": len(
            rendered_html.encode("utf-8")
        ),
        "payload_preview_path": str(
            payload_preview_path
        ),
        "payload_preview_digest_sha256": (
            payload_preview[
                "wordpress_draft_payload_"
                "preview_digest_sha256"
            ]
        ),
        "cover_image_policy": {
            "source_image_hotlink_approved": (
                False
            ),
            "remote_image_used_for_local_preview": (
                True
            ),
            "publication_with_remote_image_allowed": (
                False
            ),
            "wordpress_media_upload_required_before_publish": (
                True
            ),
            "wordpress_media_write": False,
        },
        "human_review_required": True,
        "human_review_completed": False,
        "render_dry_run_completed": True,
        "draft_creation_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_creation": False,
        "normal_x_fb_write": False,
        "x_api_call": False,
        "x_post": False,
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-DRAFT-RENDER-"
            "HUMAN-REVIEW"
        ),
        "next_phase_execution_allowed": True,
        "production_status": "NO_GO",
        "safety_state": (
            "LOCAL_RENDER_COMPLETE_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
    }

    dry_run = {
        **dry_run_payload,
        "wordpress_draft_render_dry_run_"
        "digest_sha256": (
            canonical_digest(
                dry_run_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        dry_run,
    )

    return dry_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--design-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--input-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--discovery-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--template",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--rendered-html",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--payload-preview",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = build_render_dry_run(
            production_database_path=(
                args.production_db
            ),
            design_pack_path=(
                args.design_pack
            ),
            input_pack_path=(
                args.input_pack
            ),
            discovery_pack_path=(
                args.discovery_pack
            ),
            template_path=args.template,
            rendered_html_path=(
                args.rendered_html
            ),
            payload_preview_path=(
                args.payload_preview
            ),
            output_path=args.output,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_DRAFT_"
                        "RENDER_DRY_RUN"
                    ),
                    "error": str(exc),
                    "draft_creation_allowed": False,
                    "database_write": False,
                    "wordpress_api_call": False,
                    "wordpress_write": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "render_state": (
                    result["render_state"]
                ),
                "post_title": (
                    result[
                        "post_preview"
                    ]["title"]
                ),
                "post_slug": (
                    result[
                        "post_preview"
                    ]["slug"]
                ),
                "post_status": "draft",
                "category_ids": [43],
                "rendered_html_sha256": (
                    result[
                        "rendered_html_sha256"
                    ]
                ),
                "rendered_html_byte_size": (
                    result[
                        "rendered_html_byte_size"
                    ]
                ),
                "rendered_html_validation_passed": (
                    True
                ),
                "human_review_required": True,
                "human_review_completed": False,
                "source_image_hotlink_approved": (
                    False
                ),
                "wordpress_media_upload_required_before_publish": (
                    True
                ),
                "draft_creation_allowed": False,
                "database_write": False,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "rendered_html_path": (
                    result[
                        "rendered_html_path"
                    ]
                ),
                "payload_preview_path": (
                    result[
                        "payload_preview_path"
                    ]
                ),
                "dry_run_pack_path": str(
                    args.output.resolve()
                ),
                "dry_run_digest_sha256": (
                    result[
                        "wordpress_draft_render_"
                        "dry_run_digest_sha256"
                    ]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
