from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)
from scripts.run_x_r11_wordpress_draft_creation_once import (
    build_authorization_header,
    build_rest_base,
    first_env,
    load_json,
    parse_env_file,
    sha256_file,
    verify_digest,
)
from scripts.run_x_r11_wordpress_media_draft_update_once import (
    extract_wp_text,
    find_media_duplicates,
    get_live_post,
    get_media_by_id,
    validate_media_object,
    verify_media_source_binary,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-PUBLICATION-READINESS-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST = (
    "48ca178ad9af187afa505ac4866f7e404"
    "ed04daba15ea1a2ede00c25caed8257"
)

EXPECTED_UPDATED_CONTENT_SHA = (
    "c3205ab12772cd5e8a644a9e84ff39b9"
    "44b8e17d5cd2484316972b8425ae7699"
)

EXPECTED_MEDIA_SHA = (
    "fcd5ed6e8a2136f45a380e055d3a34e7"
    "fe1e0d90cfaed9c8bcc8839c95a890c7"
)

EXPECTED_MEDIA_SOURCE_URL = (
    "https://hoshido.jp/wp-content/uploads/"
    "2026/07/"
    "noa-senpai-wa-tomodachi-11-cover.jpg"
)

EXPECTED_MEDIA_ID = 196
EXPECTED_POST_ID = 195
EXPECTED_CATEGORY_ID = 43

EXPECTED_POST_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_POST_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_MEDIA_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻 書影"
)

MEDIA_URL_PLACEHOLDER = (
    "{{WORDPRESS_MEDIA_SOURCE_URL}}"
)

PUBLIC_URL_PLACEHOLDER = (
    "{{WORDPRESS_PUBLIC_URL}}"
)

REMOTE_COVER_URL = (
    "https://shop.r10s.jp/"
    "rakutenkobo-ebooks/cabinet/6437/"
    "2000020786437.jpg"
)

PUBLICATION_REQUEST_ID = (
    "xr11-wp-publish-"
    + EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST[:24]
)


class PublicationReadinessError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise PublicationReadinessError(
            message
        )


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def extract_raw_content(
    post: dict[str, Any],
) -> str:
    content = post.get("content")

    if isinstance(content, dict):
        raw = content.get("raw")
    else:
        raw = content

    require(
        isinstance(raw, str)
        and raw,
        "live post raw content is missing",
    )

    return raw


def site_base_from_rest_base(
    rest_base: str,
) -> str:
    parsed = urllib.parse.urlparse(
        rest_base
    )

    require(
        parsed.scheme == "https",
        "WordPress REST base must use HTTPS",
    )

    require(
        bool(parsed.netloc),
        "WordPress REST hostname is missing",
    )

    path = parsed.path.rstrip("/")

    suffix = "/wp-json/wp/v2"

    require(
        path.endswith(suffix),
        (
            "WordPress REST base path must end "
            f"with {suffix}"
        ),
    )

    site_path = path[
        : -len(suffix)
    ]

    return urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            site_path,
            "",
            "",
            "",
        )
    ).rstrip("/")


def validate_live_draft(
    post: dict[str, Any],
    *,
    expected_content_sha256: str = (
        EXPECTED_UPDATED_CONTENT_SHA
    ),
    expected_media_source_url: str = (
        EXPECTED_MEDIA_SOURCE_URL
    ),
) -> dict[str, Any]:
    require(
        post.get("id")
        == EXPECTED_POST_ID,
        "live post ID mismatch",
    )

    require(
        post.get("status")
        == "draft",
        "live post must remain draft",
    )

    require(
        post.get("slug")
        == EXPECTED_POST_SLUG,
        "live post slug mismatch",
    )

    require(
        extract_wp_text(
            post.get("title")
        )
        == EXPECTED_POST_TITLE,
        "live post title mismatch",
    )

    require(
        post.get("categories")
        == [EXPECTED_CATEGORY_ID],
        "live post category mismatch",
    )

    raw_content = extract_raw_content(
        post
    )

    content_sha256 = sha256_text(
        raw_content
    )

    require(
        content_sha256
        == expected_content_sha256,
        "live post content SHA mismatch",
    )

    require(
        raw_content.count(
            expected_media_source_url
        )
        == 1,
        (
            "WordPress media source URL "
            "count must equal one"
        ),
    )

    require(
        MEDIA_URL_PLACEHOLDER
        not in raw_content,
        "media URL placeholder remains",
    )

    require(
        PUBLIC_URL_PLACEHOLDER
        not in raw_content,
        "public URL placeholder appears in article",
    )

    require(
        REMOTE_COVER_URL
        not in raw_content,
        "remote cover URL remains",
    )

    require(
        "ebook-new-release-article"
        in raw_content,
        "article marker is missing",
    )

    require(
        "ebook-pr-disclosure"
        in raw_content,
        "PR disclosure marker is missing",
    )

    require(
        "ebook-cover-image"
        in raw_content,
        "cover-image marker is missing",
    )

    require(
        "price-cards"
        in raw_content,
        "price-cards marker is missing",
    )

    require(
        "store-buttons"
        in raw_content,
        "store-buttons marker is missing",
    )

    require(
        EXPECTED_MEDIA_TITLE
        in raw_content,
        "cover alt text is missing",
    )

    current_link = post.get(
        "link"
    )

    require(
        isinstance(current_link, str)
        and current_link.startswith(
            "https://"
        ),
        "current WordPress link is invalid",
    )

    return {
        "post_id": EXPECTED_POST_ID,
        "title": EXPECTED_POST_TITLE,
        "slug": EXPECTED_POST_SLUG,
        "status": "draft",
        "category_ids": [
            EXPECTED_CATEGORY_ID
        ],
        "content_sha256": (
            content_sha256
        ),
        "media_source_url": (
            expected_media_source_url
        ),
        "media_source_url_count": 1,
        "remote_cover_url_absent": True,
        "media_placeholder_absent": True,
        "article_markers_verified": True,
        "pr_disclosure_verified": True,
        "cover_alt_text_verified": True,
        "current_draft_link": (
            current_link
        ),
        "modified": post.get(
            "modified"
        ),
    }


def validate_single_media_duplicate(
    value: dict[str, Any],
) -> None:
    require(
        value.get("duplicate_found")
        is True,
        "WordPress media was not found",
    )

    require(
        value.get("exact_match_count")
        == 1,
        (
            "exact WordPress media match "
            "count must equal one"
        ),
    )

    require(
        value.get("matched_media_ids")
        == [EXPECTED_MEDIA_ID],
        (
            "media search must resolve only "
            f"to media {EXPECTED_MEDIA_ID}"
        ),
    )


def build_publication_request_preview() -> dict[str, Any]:
    return {
        "request_id": (
            PUBLICATION_REQUEST_ID
        ),
        "api_method": "POST_ONCE",
        "resource": (
            "/wp-json/wp/v2/posts/195"
        ),
        "payload": {
            "status": "publish",
        },
        "target_post_id": (
            EXPECTED_POST_ID
        ),
        "maximum_update_count": 1,
        "required_pre_execution_status": (
            "draft"
        ),
        "required_post_execution_status": (
            "publish"
        ),
        "content_change_allowed": False,
        "title_change_allowed": False,
        "slug_change_allowed": False,
        "category_change_allowed": False,
        "media_change_allowed": False,
        "publication_only": True,
        "execution_allowed": False,
    }


def validate_publication_request_preview(
    value: dict[str, Any],
) -> None:
    require(
        value.get("request_id")
        == PUBLICATION_REQUEST_ID,
        "publication request ID mismatch",
    )

    require(
        value.get("api_method")
        == "POST_ONCE",
        "publication method mismatch",
    )

    require(
        value.get("resource")
        == "/wp-json/wp/v2/posts/195",
        "publication resource mismatch",
    )

    require(
        value.get("payload")
        == {
            "status": "publish",
        },
        "publication payload mismatch",
    )

    require(
        value.get("target_post_id")
        == EXPECTED_POST_ID,
        "publication target post mismatch",
    )

    require(
        value.get("maximum_update_count")
        == 1,
        (
            "publication maximum update "
            "count must equal one"
        ),
    )

    require(
        value.get(
            "required_pre_execution_status"
        )
        == "draft",
        "publication pre-status mismatch",
    )

    require(
        value.get(
            "required_post_execution_status"
        )
        == "publish",
        "publication post-status mismatch",
    )

    for field in (
        "content_change_allowed",
        "title_change_allowed",
        "slug_change_allowed",
        "category_change_allowed",
        "media_change_allowed",
    ):
        require(
            value.get(field)
            is False,
            (
                "publication preview permits "
                f"an unexpected change: {field}"
            ),
        )

    require(
        value.get("publication_only")
        is True,
        "publication request is not publication-only",
    )

    require(
        value.get("execution_allowed")
        is False,
        (
            "publication execution must "
            "remain blocked"
        ),
    )


def build_readiness_prep(
    *,
    production_database_path: Path,
    post_execution_verification_path: Path,
    credential_env_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    post_execution_verification_path = (
        post_execution_verification_path.resolve()
    )

    credential_env_path = (
        credential_env_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    verification = load_json(
        post_execution_verification_path
    )

    verify_digest(
        verification,
        digest_field=(
            "wordpress_media_draft_update_"
            "post_execution_verification_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST
        ),
        label=(
            "media and draft update "
            "post-execution verification"
        ),
    )

    require(
        verification.get("status")
        == (
            "PASS_WORDPRESS_MEDIA_DRAFT_UPDATE_"
            "POST_EXECUTION_VERIFICATION"
        ),
        "post-execution verification did not pass",
    )

    require(
        verification.get("verification_state")
        == (
            "MEDIA_196_AND_DRAFT_195_VERIFIED_"
            "PUBLICATION_REMAINS_BLOCKED"
        ),
        "post-execution verification state mismatch",
    )

    require(
        verification.get("approval_consumed")
        is True,
        "media/update approval was not consumed",
    )

    require(
        verification.get("reexecution_allowed")
        is False,
        "media/update reexecution is allowed",
    )

    require(
        verification.get(
            "media_duplicate_count_verified"
        )
        == 1,
        "verified media duplicate count mismatch",
    )

    require(
        verification.get(
            "wordpress_publication_allowed"
        )
        is False,
        (
            "source verification unexpectedly "
            "permits publication"
        ),
    )

    require(
        verification.get("public_url_available")
        is False,
        (
            "public URL must remain unavailable "
            "before publication"
        ),
    )

    require(
        verification.get(
            "x_post_execution_allowed"
        )
        is False,
        (
            "X post execution must remain "
            "blocked"
        ),
    )

    env_values = parse_env_file(
        credential_env_path
    )

    rest_base = build_rest_base(
        env_values
    )

    site_base = site_base_from_rest_base(
        rest_base
    )

    username = first_env(
        env_values,
        (
            "WORDPRESS_USERNAME",
            "WP_USERNAME",
            "WORDPRESS_USER",
            "WP_USER",
        ),
        "WordPress username",
    )

    application_password = first_env(
        env_values,
        (
            "WORDPRESS_APPLICATION_PASSWORD",
            "WP_APPLICATION_PASSWORD",
            "WORDPRESS_APP_PASSWORD",
            "WP_APP_PASSWORD",
        ),
        "WordPress application password",
    )

    authorization = (
        build_authorization_header(
            username,
            application_password,
        )
    )

    wp_hostname = (
        urllib.parse.urlparse(
            site_base
        ).hostname
        or ""
    )

    require(
        bool(wp_hostname),
        "WordPress site hostname is missing",
    )

    live_media = get_media_by_id(
        rest_base=rest_base,
        authorization=authorization,
        media_id=EXPECTED_MEDIA_ID,
    )

    media_result = (
        validate_media_object(
            live_media,
            wp_hostname=wp_hostname,
        )
    )

    require(
        media_result["media_id"]
        == EXPECTED_MEDIA_ID,
        "live media ID mismatch",
    )

    require(
        media_result["source_url"]
        == EXPECTED_MEDIA_SOURCE_URL,
        "live media source URL mismatch",
    )

    media_binary = (
        verify_media_source_binary(
            source_url=media_result[
                "source_url"
            ],
            authorization=authorization,
            wp_hostname=wp_hostname,
        )
    )

    require(
        media_binary["sha256"]
        == EXPECTED_MEDIA_SHA,
        "live WordPress media SHA mismatch",
    )

    duplicate_state = (
        find_media_duplicates(
            rest_base=rest_base,
            authorization=authorization,
        )
    )

    validate_single_media_duplicate(
        duplicate_state
    )

    live_post = get_live_post(
        rest_base=rest_base,
        authorization=authorization,
    )

    post_result = validate_live_draft(
        live_post
    )

    source_post = verification.get(
        "wordpress_post"
    )

    require(
        isinstance(source_post, dict),
        "source verified post is missing",
    )

    require(
        source_post.get("content_sha256")
        == EXPECTED_UPDATED_CONTENT_SHA,
        "source verified content SHA mismatch",
    )

    require(
        post_result["content_sha256"]
        == source_post["content_sha256"],
        (
            "live post content differs from "
            "post-execution verification"
        ),
    )

    publication_preview = (
        build_publication_request_preview()
    )

    validate_publication_request_preview(
        publication_preview
    )

    prepared_at = datetime.now(
        timezone.utc
    ).isoformat()

    prep_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_PUBLICATION_"
            "READINESS_PREP"
        ),
        "readiness_state": (
            "PUBLICATION_REQUEST_PREVIEW_FIXED_"
            "AWAITING_HUMAN_REVIEW"
        ),
        "prepared_at": prepared_at,
        "source_post_execution_verification_path": str(
            post_execution_verification_path
        ),
        "source_post_execution_verification_digest_sha256": (
            EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST
        ),
        "wordpress_site": {
            "site_base": site_base,
            "rest_base": rest_base,
            "hostname": wp_hostname,
        },
        "wordpress_media": {
            **media_result,
            "sha256": (
                media_binary["sha256"]
            ),
            "byte_size": (
                media_binary["byte_size"]
            ),
            "duplicate_count_verified": 1,
        },
        "wordpress_post": (
            post_result
        ),
        "publication_request_preview": (
            publication_preview
        ),
        "publication_preconditions": {
            "post_id": EXPECTED_POST_ID,
            "post_status": "draft",
            "post_title": EXPECTED_POST_TITLE,
            "post_slug": EXPECTED_POST_SLUG,
            "category_ids": [
                EXPECTED_CATEGORY_ID
            ],
            "content_sha256": (
                EXPECTED_UPDATED_CONTENT_SHA
            ),
            "media_id": EXPECTED_MEDIA_ID,
            "media_source_url": (
                EXPECTED_MEDIA_SOURCE_URL
            ),
            "media_sha256": (
                EXPECTED_MEDIA_SHA
            ),
            "media_duplicate_count": 1,
            "all_preconditions_verified": True,
        },
        "post_publication_verification_contract": {
            "wordpress_post_id": (
                EXPECTED_POST_ID
            ),
            "required_status": "publish",
            "required_title": (
                EXPECTED_POST_TITLE
            ),
            "required_slug": (
                EXPECTED_POST_SLUG
            ),
            "required_category_ids": [
                EXPECTED_CATEGORY_ID
            ],
            "required_content_sha256": (
                EXPECTED_UPDATED_CONTENT_SHA
            ),
            "required_media_id": (
                EXPECTED_MEDIA_ID
            ),
            "required_media_source_url": (
                EXPECTED_MEDIA_SOURCE_URL
            ),
            "required_media_sha256": (
                EXPECTED_MEDIA_SHA
            ),
            "public_link_source": (
                "WORDPRESS_PUBLISH_RESPONSE_AND_"
                "POST_PUBLISH_GET"
            ),
            "public_link_must_use_https": True,
            "public_link_hostname_must_equal": (
                wp_hostname
            ),
            "public_link_must_resolve": True,
            "content_change_allowed": False,
            "title_change_allowed": False,
            "slug_change_allowed": False,
            "category_change_allowed": False,
            "media_change_allowed": False,
        },
        "human_review_required": True,
        "human_review_completed": False,
        "publication_approval_issued": False,
        "publication_approval_consumed": False,
        "publication_execution_allowed": False,
        "wordpress_publication_allowed": False,
        "wordpress_api_call": True,
        "wordpress_api_method": "GET_ONLY",
        "wordpress_write": False,
        "wordpress_post_update": False,
        "public_url_available": False,
        "public_url": None,
        "x_public_url_replacement_allowed": False,
        "x_final_review_allowed": False,
        "x_post_execution_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PUBLICATION_PREVIEW_READY_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-PUBLICATION-"
            "HUMAN-REVIEW-PREP"
        ),
    }

    prep = {
        **prep_payload,
        "wordpress_publication_readiness_"
        "prep_digest_sha256": (
            canonical_digest(
                prep_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        prep,
    )

    return prep


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--post-execution-verification",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--credential-env",
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
        result = build_readiness_prep(
            production_database_path=(
                args.production_db
            ),
            post_execution_verification_path=(
                args.post_execution_verification
            ),
            credential_env_path=(
                args.credential_env
            ),
            output_path=args.output,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_PUBLICATION_"
                        "READINESS_PREP"
                    ),
                    "error": str(exc),
                    "publication_execution_allowed": False,
                    "wordpress_publication_allowed": False,
                    "wordpress_api_method": "GET_ONLY",
                    "wordpress_write": False,
                    "public_url_available": False,
                    "x_post_execution_allowed": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    post = result[
        "wordpress_post"
    ]

    media = result[
        "wordpress_media"
    ]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "readiness_state": (
                    result["readiness_state"]
                ),
                "publication_request_id": (
                    result[
                        "publication_request_preview"
                    ]["request_id"]
                ),
                "wordpress_media_id": (
                    media["media_id"]
                ),
                "wordpress_media_sha256": (
                    media["sha256"]
                ),
                "wordpress_post_id": (
                    post["post_id"]
                ),
                "wordpress_post_status": (
                    post["status"]
                ),
                "wordpress_post_content_sha256": (
                    post["content_sha256"]
                ),
                "human_review_required": True,
                "human_review_completed": False,
                "publication_approval_issued": False,
                "publication_execution_allowed": False,
                "wordpress_publication_allowed": False,
                "wordpress_api_method": "GET_ONLY",
                "wordpress_write": False,
                "public_url_available": False,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "prep_pack_path": str(
                    args.output.resolve()
                ),
                "prep_digest_sha256": (
                    result[
                        "wordpress_publication_"
                        "readiness_prep_digest_sha256"
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
