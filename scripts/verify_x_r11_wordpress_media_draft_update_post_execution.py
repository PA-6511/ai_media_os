from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
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
    EXPECTED_MEDIA_FILENAME,
    EXPECTED_MEDIA_SHA,
    EXPECTED_MEDIA_SLUG,
    EXPECTED_MEDIA_TITLE,
    EXPECTED_POST_SLUG,
    EXPECTED_POST_TITLE,
    MEDIA_URL_PLACEHOLDER,
    REMOTE_COVER_URL,
    extract_wp_text,
    find_media_duplicates,
    get_live_post,
    get_media_by_id,
    validate_media_object,
    verify_media_source_binary,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-MEDIA-DRAFT-UPDATE-"
    "POST-EXECUTION-VERIFICATION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_RECEIPT_DIGEST = (
    "b69b6d084d4703016fed55a8a37b2f9e"
    "75e813c935f5713218134a0baeca6228"
)

EXPECTED_APPROVAL_GATE_DIGEST = (
    "f608821d973164a21236c5b478425357"
    "3138a1b7f1033e81e264ec6eac5ac775"
)

EXPECTED_REVIEW_DIGEST = (
    "5b2faab0d29b9fe830daae7578d97a5b"
    "5d7fff20612a5a8afb963962f0a3d11b"
)

EXPECTED_APPROVAL_REQUEST_ID = (
    "xr11-wp-media-draft-update-"
    "5b2faab0d29b9fe830daae75"
)

EXPECTED_MEDIA_ID = 196
EXPECTED_POST_ID = 195
EXPECTED_CATEGORY_ID = 43

EXPECTED_MEDIA_SOURCE_URL = (
    "https://hoshido.jp/wp-content/uploads/"
    "2026/07/"
    "noa-senpai-wa-tomodachi-11-cover.jpg"
)


class PostExecutionVerificationError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise PostExecutionVerificationError(
            message
        )


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def validate_execution_claim(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_WORDPRESS_MEDIA_DRAFT_"
            "UPDATE_EXECUTION_CLAIM"
        ),
        "execution claim type mismatch",
    )

    require(
        value.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "execution claim request ID mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "execution claim gate digest mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "execution claim review digest mismatch",
    )

    require(
        value.get("media_sha256")
        == EXPECTED_MEDIA_SHA,
        "execution claim media SHA mismatch",
    )

    require(
        value.get("target_post_id")
        == EXPECTED_POST_ID,
        "execution claim post ID mismatch",
    )

    require(
        value.get(
            "maximum_media_create_count"
        )
        == 1,
        "execution claim media maximum mismatch",
    )

    require(
        value.get(
            "maximum_draft_update_count"
        )
        == 1,
        "execution claim update maximum mismatch",
    )

    require(
        value.get("execution_claimed")
        is True,
        "execution was not claimed",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "execution claim permits reexecution",
    )


def validate_consumption_lock(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_WORDPRESS_MEDIA_DRAFT_"
            "UPDATE_APPROVAL_CONSUMPTION"
        ),
        "consumption lock type mismatch",
    )

    require(
        value.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "consumption lock request ID mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "consumption lock gate digest mismatch",
    )

    require(
        value.get("approval_consumed")
        is True,
        "approval was not consumed",
    )

    require(
        value.get(
            "consumed_for_execution_attempt"
        )
        is True,
        "approval consumption attempt is missing",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "consumption lock permits reexecution",
    )


def validate_single_media_duplicate(
    value: dict[str, Any],
) -> None:
    require(
        value.get("duplicate_found")
        is True,
        "created media was not found",
    )

    require(
        value.get("exact_match_count")
        == 1,
        "exact media match count must equal one",
    )

    require(
        value.get("matched_media_ids")
        == [EXPECTED_MEDIA_ID],
        (
            "media duplicate search must resolve "
            f"only to media {EXPECTED_MEDIA_ID}"
        ),
    )


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


def validate_updated_post(
    post: dict[str, Any],
    *,
    expected_content_sha256: str,
    media_source_url: str,
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

    content = extract_raw_content(
        post
    )

    content_sha256 = sha256_text(
        content
    )

    require(
        content_sha256
        == expected_content_sha256,
        "live updated content SHA mismatch",
    )

    require(
        content.count(
            media_source_url
        )
        == 1,
        (
            "WordPress media source URL "
            "count must equal one"
        ),
    )

    require(
        MEDIA_URL_PLACEHOLDER
        not in content,
        "media URL placeholder remains",
    )

    require(
        REMOTE_COVER_URL
        not in content,
        "remote cover URL remains",
    )

    require(
        "ebook-cover-image"
        in content,
        "cover-image marker is missing",
    )

    require(
        EXPECTED_MEDIA_TITLE
        in content,
        "cover alt text is missing",
    )

    return {
        "post_id": EXPECTED_POST_ID,
        "title": EXPECTED_POST_TITLE,
        "slug": EXPECTED_POST_SLUG,
        "status": "draft",
        "category_ids": [
            EXPECTED_CATEGORY_ID
        ],
        "content_sha256": content_sha256,
        "media_source_url_count": 1,
        "media_placeholder_absent": True,
        "remote_cover_url_absent": True,
        "cover_marker_verified": True,
        "cover_alt_text_verified": True,
        "link": post.get("link"),
        "date": post.get("date"),
        "modified": post.get("modified"),
    }


def validate_execution_receipt(
    value: dict[str, Any],
) -> tuple[
    str,
    str,
]:
    verify_digest(
        value,
        digest_field=(
            "wordpress_media_draft_update_"
            "one_shot_receipt_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_RECEIPT_DIGEST
        ),
        label="one-shot execution receipt",
    )

    require(
        value.get("status")
        == (
            "PASS_WORDPRESS_MEDIA_AND_DRAFT_"
            "UPDATE_ONE_SHOT"
        ),
        "one-shot receipt status mismatch",
    )

    require(
        value.get("execution_state")
        == (
            "MEDIA_CREATED_DRAFT_UPDATED_"
            "PUBLICATION_STILL_BLOCKED"
        ),
        "one-shot execution state mismatch",
    )

    require(
        value.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "one-shot receipt request ID mismatch",
    )

    require(
        value.get(
            "source_approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "one-shot receipt gate digest mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "one-shot receipt review digest mismatch",
    )

    require(
        value.get("approval_consumed")
        is True,
        "one-shot receipt approval not consumed",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "one-shot receipt permits reexecution",
    )

    require(
        value.get(
            "actual_media_create_count"
        )
        == 1,
        "actual media create count mismatch",
    )

    require(
        value.get(
            "actual_draft_update_count"
        )
        == 1,
        "actual draft update count mismatch",
    )

    require(
        value.get("wordpress_media_write")
        is True,
        "media write was not recorded",
    )

    require(
        value.get("wordpress_post_update")
        is True,
        "post update was not recorded",
    )

    require(
        value.get("wordpress_post_status")
        == "draft",
        "receipt post status mismatch",
    )

    require(
        value.get(
            "wordpress_publication_allowed"
        )
        is False,
        "receipt permits publication",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "receipt permits X execution",
    )

    media = value.get(
        "wordpress_media"
    )

    require(
        isinstance(media, dict),
        "receipt media evidence is missing",
    )

    require(
        media.get("media_id")
        == EXPECTED_MEDIA_ID,
        "receipt media ID mismatch",
    )

    require(
        media.get("source_url")
        == EXPECTED_MEDIA_SOURCE_URL,
        "receipt media source URL mismatch",
    )

    post = value.get(
        "wordpress_post"
    )

    require(
        isinstance(post, dict),
        "receipt post evidence is missing",
    )

    require(
        post.get("post_id")
        == EXPECTED_POST_ID,
        "receipt post ID mismatch",
    )

    require(
        post.get("status")
        == "draft",
        "receipt post must remain draft",
    )

    content_sha256 = post.get(
        "content_sha256"
    )

    require(
        isinstance(content_sha256, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            content_sha256,
        )
        is not None,
        "receipt content SHA is invalid",
    )

    return (
        media["source_url"],
        content_sha256,
    )


def verify_post_execution(
    *,
    production_database_path: Path,
    execution_receipt_path: Path,
    media_result_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    credential_env_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    execution_receipt_path = (
        execution_receipt_path.resolve()
    )

    media_result_path = (
        media_result_path.resolve()
    )

    execution_claim_path = (
        execution_claim_path.resolve()
    )

    consumption_lock_path = (
        consumption_lock_path.resolve()
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

    receipt = load_json(
        execution_receipt_path
    )

    (
        expected_media_source_url,
        expected_content_sha256,
    ) = validate_execution_receipt(
        receipt
    )

    media_result_receipt = load_json(
        media_result_path
    )

    media_result_digest = (
        media_result_receipt.get(
            "wordpress_media_result_"
            "digest_sha256"
        )
    )

    require(
        isinstance(media_result_digest, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            media_result_digest,
        )
        is not None,
        "media result digest is invalid",
    )

    media_result_payload = {
        key: item
        for key, item
        in media_result_receipt.items()
        if key
        != "wordpress_media_result_digest_sha256"
    }

    require(
        canonical_digest(
            media_result_payload
        )
        == media_result_digest,
        "media result canonical digest failed",
    )

    require(
        media_result_receipt.get("status")
        == (
            "PASS_WORDPRESS_MEDIA_CREATED_"
            "OR_RECONCILED"
        ),
        "media result status mismatch",
    )

    require(
        media_result_receipt.get(
            "actual_media_create_count"
        )
        == 1,
        "media result create count mismatch",
    )

    media_result_evidence = (
        media_result_receipt.get("media")
    )

    require(
        isinstance(
            media_result_evidence,
            dict,
        ),
        "media result evidence is missing",
    )

    require(
        media_result_evidence.get(
            "media_id"
        )
        == EXPECTED_MEDIA_ID,
        "media result ID mismatch",
    )

    require(
        media_result_evidence.get(
            "source_url"
        )
        == EXPECTED_MEDIA_SOURCE_URL,
        "media result source URL mismatch",
    )

    media_binary_evidence = (
        media_result_receipt.get(
            "media_binary_verification"
        )
    )

    require(
        isinstance(
            media_binary_evidence,
            dict,
        ),
        "media binary evidence is missing",
    )

    require(
        media_binary_evidence.get(
            "sha256"
        )
        == EXPECTED_MEDIA_SHA,
        "media result binary SHA mismatch",
    )

    execution_claim = load_json(
        execution_claim_path
    )

    validate_execution_claim(
        execution_claim
    )

    consumption_lock = load_json(
        consumption_lock_path
    )

    validate_consumption_lock(
        consumption_lock
    )

    env_values = parse_env_file(
        credential_env_path
    )

    rest_base = build_rest_base(
        env_values
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
        __import__(
            "urllib.parse",
            fromlist=["urlparse"],
        )
        .urlparse(
            rest_base
        )
        .hostname
        or ""
    )

    require(
        bool(wp_hostname),
        "WordPress hostname is missing",
    )

    live_media = get_media_by_id(
        rest_base=rest_base,
        authorization=authorization,
        media_id=EXPECTED_MEDIA_ID,
    )

    live_media_result = (
        validate_media_object(
            live_media,
            wp_hostname=wp_hostname,
        )
    )

    require(
        live_media_result["media_id"]
        == EXPECTED_MEDIA_ID,
        "live media ID mismatch",
    )

    require(
        live_media_result["slug"]
        == EXPECTED_MEDIA_SLUG,
        "live media slug mismatch",
    )

    require(
        live_media_result["source_url"]
        == expected_media_source_url,
        "live media source URL mismatch",
    )

    require(
        live_media_result["title"]
        == EXPECTED_MEDIA_TITLE,
        "live media title mismatch",
    )

    require(
        live_media_result["alt_text"]
        == EXPECTED_MEDIA_TITLE,
        "live media alt text mismatch",
    )

    require(
        live_media_result[
            "attached_post_id"
        ]
        == EXPECTED_POST_ID,
        "live media attachment mismatch",
    )

    require(
        Path(
            __import__(
                "urllib.parse",
                fromlist=["urlparse"],
            )
            .urlparse(
                live_media_result[
                    "source_url"
                ]
            )
            .path
        ).name
        == EXPECTED_MEDIA_FILENAME,
        "live media filename mismatch",
    )

    live_binary_result = (
        verify_media_source_binary(
            source_url=live_media_result[
                "source_url"
            ],
            authorization=authorization,
            wp_hostname=wp_hostname,
        )
    )

    require(
        live_binary_result["sha256"]
        == EXPECTED_MEDIA_SHA,
        "live media SHA mismatch",
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

    live_post_result = validate_updated_post(
        live_post,
        expected_content_sha256=(
            expected_content_sha256
        ),
        media_source_url=(
            expected_media_source_url
        ),
    )

    verified_at = datetime.now(
        timezone.utc
    ).isoformat()

    verification_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_MEDIA_DRAFT_UPDATE_"
            "POST_EXECUTION_VERIFICATION"
        ),
        "verification_state": (
            "MEDIA_196_AND_DRAFT_195_VERIFIED_"
            "PUBLICATION_REMAINS_BLOCKED"
        ),
        "verified_at": verified_at,
        "source_execution_receipt_path": str(
            execution_receipt_path
        ),
        "source_execution_receipt_digest_sha256": (
            EXPECTED_RECEIPT_DIGEST
        ),
        "source_media_result_path": str(
            media_result_path
        ),
        "source_media_result_digest_sha256": (
            media_result_digest
        ),
        "execution_claim_path": str(
            execution_claim_path
        ),
        "consumption_lock_path": str(
            consumption_lock_path
        ),
        "wordpress_media": (
            live_media_result
        ),
        "wordpress_media_binary_verification": (
            live_binary_result
        ),
        "wordpress_media_duplicate_verification": (
            duplicate_state
        ),
        "wordpress_post": (
            live_post_result
        ),
        "approval_consumed": True,
        "reexecution_allowed": False,
        "actual_media_create_count": 1,
        "actual_draft_update_count": 1,
        "media_duplicate_count_verified": 1,
        "wordpress_api_call": True,
        "wordpress_api_method": "GET_ONLY",
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_update": False,
        "wordpress_post_status": "draft",
        "wordpress_publication_allowed": False,
        "public_url_available": False,
        "x_public_url_replacement_allowed": False,
        "x_post_execution_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "MEDIA_AND_UPDATED_DRAFT_VERIFIED_"
            "NO_FURTHER_WORDPRESS_WRITE_ALLOWED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-PUBLICATION-READINESS-PREP"
        ),
    }

    verification = {
        **verification_payload,
        "wordpress_media_draft_update_"
        "post_execution_verification_"
        "digest_sha256": (
            canonical_digest(
                verification_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        verification,
    )

    return verification


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--execution-receipt",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--media-result",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--execution-claim",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--consumption-lock",
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
        result = verify_post_execution(
            production_database_path=(
                args.production_db
            ),
            execution_receipt_path=(
                args.execution_receipt
            ),
            media_result_path=(
                args.media_result
            ),
            execution_claim_path=(
                args.execution_claim
            ),
            consumption_lock_path=(
                args.consumption_lock
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
                        "FAIL_WORDPRESS_MEDIA_DRAFT_UPDATE_"
                        "POST_EXECUTION_VERIFICATION"
                    ),
                    "error": str(exc),
                    "wordpress_api_method": "GET_ONLY",
                    "wordpress_write": False,
                    "reexecution_allowed": False,
                    "wordpress_publication_allowed": False,
                    "x_post_execution_allowed": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    media = result[
        "wordpress_media"
    ]

    post = result[
        "wordpress_post"
    ]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "verification_state": (
                    result[
                        "verification_state"
                    ]
                ),
                "wordpress_media_id": (
                    media["media_id"]
                ),
                "wordpress_media_source_url": (
                    media["source_url"]
                ),
                "wordpress_media_sha256": (
                    result[
                        "wordpress_media_binary_verification"
                    ]["sha256"]
                ),
                "media_duplicate_count_verified": 1,
                "wordpress_post_id": (
                    post["post_id"]
                ),
                "wordpress_post_status": (
                    post["status"]
                ),
                "wordpress_post_content_sha256": (
                    post["content_sha256"]
                ),
                "approval_consumed": True,
                "reexecution_allowed": False,
                "wordpress_api_method": "GET_ONLY",
                "wordpress_write": False,
                "wordpress_publication_allowed": False,
                "public_url_available": False,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "verification_pack_path": str(
                    args.output.resolve()
                ),
                "verification_digest_sha256": (
                    result[
                        "wordpress_media_draft_update_"
                        "post_execution_verification_"
                        "digest_sha256"
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
