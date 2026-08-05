from __future__ import annotations

import argparse
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
from scripts.run_x_r11_wordpress_publication_once import (
    EXPECTED_CONTENT_SHA,
    EXPECTED_MEDIA_ID,
    EXPECTED_MEDIA_SHA,
    EXPECTED_MEDIA_SOURCE_URL,
    EXPECTED_POST_ID,
    EXPECTED_POST_SLUG,
    EXPECTED_POST_TITLE,
    get_live_post,
    validate_media_preflight,
    validate_post,
    validate_public_url,
    verify_public_page,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-PUBLICATION-"
    "POST-EXECUTION-VERIFICATION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_RECEIPT_DIGEST = (
    "0b3127e0fa3a6d98b6d42338dfe2d785"
    "036e62ff56fbda8bbc0e38020fb9e868"
)

EXPECTED_APPROVAL_GATE_DIGEST = (
    "e758fa7f28141c47e2bc518b1987ed58"
    "0baa6a07586626db7e685b67d4ae841a"
)

EXPECTED_REVIEW_DIGEST = (
    "557286fce0da4e6114fa29fdb95a5d9e"
    "26cceaad86bf2258835c33a929b0dbfd"
)

EXPECTED_APPROVAL_REQUEST_ID = (
    "xr11-wp-publish-"
    "48ca178ad9af187afa505ac4"
)

EXPECTED_PUBLIC_URL = (
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
)

EXPECTED_CATEGORY_IDS = [43]


class PublicationVerificationError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise PublicationVerificationError(
            message
        )


def validate_execution_claim(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_WORDPRESS_PUBLICATION_"
            "EXECUTION_CLAIM"
        ),
        "publication execution claim type mismatch",
    )

    require(
        value.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "publication execution request ID mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "publication execution gate digest mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "publication execution review digest mismatch",
    )

    require(
        value.get("target_post_id")
        == EXPECTED_POST_ID,
        "publication execution post ID mismatch",
    )

    require(
        value.get(
            "required_pre_execution_status"
        )
        == "draft",
        "publication execution pre-status mismatch",
    )

    require(
        value.get(
            "required_post_execution_status"
        )
        == "publish",
        "publication execution post-status mismatch",
    )

    require(
        value.get(
            "required_content_sha256"
        )
        == EXPECTED_CONTENT_SHA,
        "publication execution content SHA mismatch",
    )

    require(
        value.get("required_media_id")
        == EXPECTED_MEDIA_ID,
        "publication execution media ID mismatch",
    )

    require(
        value.get(
            "maximum_publication_update_count"
        )
        == 1,
        "publication execution maximum mismatch",
    )

    require(
        value.get("execution_claimed")
        is True,
        "publication execution was not claimed",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "publication execution claim permits rerun",
    )


def validate_consumption_lock(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_WORDPRESS_PUBLICATION_"
            "APPROVAL_CONSUMPTION"
        ),
        "publication consumption lock type mismatch",
    )

    require(
        value.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "publication consumption request ID mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "publication consumption gate digest mismatch",
    )

    require(
        value.get("approval_consumed")
        is True,
        "publication approval was not consumed",
    )

    require(
        value.get(
            "consumed_for_execution_attempt"
        )
        is True,
        "publication execution attempt is missing",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "publication consumption lock permits rerun",
    )


def validate_receipt_summary(
    value: dict[str, Any],
) -> None:
    require(
        value.get("status")
        == "PASS_WORDPRESS_PUBLICATION_ONE_SHOT",
        "publication receipt status mismatch",
    )

    require(
        value.get("execution_state")
        == (
            "WORDPRESS_POST_195_PUBLISHED_"
            "PUBLIC_URL_VERIFIED_X_STILL_BLOCKED"
        ),
        "publication execution state mismatch",
    )

    require(
        value.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "publication receipt request ID mismatch",
    )

    require(
        value.get(
            "source_approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "publication receipt gate digest mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "publication receipt review digest mismatch",
    )

    require(
        value.get(
            "actual_publication_update_count"
        )
        == 1,
        "publication update count mismatch",
    )

    require(
        value.get("approval_consumed")
        is True,
        "publication receipt approval is not consumed",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "publication receipt permits rerun",
    )

    require(
        value.get(
            "wordpress_publication_executed"
        )
        is True,
        "publication was not recorded as executed",
    )

    require(
        value.get("wordpress_post_status")
        == "publish",
        "publication receipt post status mismatch",
    )

    require(
        value.get("public_url_available")
        is True,
        "publication receipt has no public URL",
    )

    require(
        value.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "publication receipt public URL mismatch",
    )

    require(
        value.get(
            "x_public_url_replacement_allowed"
        )
        is True,
        "X public URL replacement is not allowed",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "publication receipt permits X posting",
    )

    require(
        value.get("x_api_call")
        is False,
        "publication receipt records an X API call",
    )

    require(
        value.get("x_post")
        is False,
        "publication receipt records an X post",
    )

    before = value.get(
        "wordpress_post_before"
    )

    after = value.get(
        "wordpress_post_after"
    )

    require(
        isinstance(before, dict),
        "pre-publication post evidence is missing",
    )

    require(
        isinstance(after, dict),
        "post-publication evidence is missing",
    )

    require(
        before.get("post_id")
        == EXPECTED_POST_ID,
        "pre-publication post ID mismatch",
    )

    require(
        before.get("status")
        == "draft",
        "pre-publication status mismatch",
    )

    require(
        after.get("post_id")
        == EXPECTED_POST_ID,
        "published post ID mismatch",
    )

    require(
        after.get("status")
        == "publish",
        "published post status mismatch",
    )

    require(
        after.get("title")
        == before.get("title")
        == EXPECTED_POST_TITLE,
        "post title changed during publication",
    )

    require(
        after.get("slug")
        == before.get("slug")
        == EXPECTED_POST_SLUG,
        "post slug changed during publication",
    )

    require(
        after.get("category_ids")
        == before.get("category_ids")
        == EXPECTED_CATEGORY_IDS,
        "post categories changed during publication",
    )

    require(
        after.get("content_sha256")
        == before.get("content_sha256")
        == EXPECTED_CONTENT_SHA,
        "post content changed during publication",
    )

    require(
        after.get("link")
        == EXPECTED_PUBLIC_URL,
        "published post link mismatch",
    )

    public_page = value.get(
        "public_page_verification"
    )

    require(
        isinstance(public_page, dict),
        "public page verification is missing",
    )

    require(
        public_page.get("http_status")
        == 200,
        "public page status was not 200",
    )

    require(
        public_page.get("resolved_url")
        == EXPECTED_PUBLIC_URL,
        "resolved public URL mismatch",
    )


def verify_publication(
    *,
    production_database_path: Path,
    publication_receipt_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    credential_env_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    publication_receipt_path = (
        publication_receipt_path.resolve()
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
        publication_receipt_path
    )

    verify_digest(
        receipt,
        digest_field=(
            "wordpress_publication_one_shot_"
            "receipt_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_RECEIPT_DIGEST
        ),
        label="publication one-shot receipt",
    )

    validate_receipt_summary(
        receipt
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
        urllib.parse.urlparse(
            rest_base
        ).hostname
        or ""
    )

    require(
        bool(wp_hostname),
        "WordPress hostname is missing",
    )

    live_media = validate_media_preflight(
        rest_base=rest_base,
        authorization=authorization,
        wp_hostname=wp_hostname,
    )

    require(
        live_media["media_id"]
        == EXPECTED_MEDIA_ID,
        "live WordPress media ID mismatch",
    )

    require(
        live_media["source_url"]
        == EXPECTED_MEDIA_SOURCE_URL,
        "live WordPress media URL mismatch",
    )

    require(
        live_media["sha256"]
        == EXPECTED_MEDIA_SHA,
        "live WordPress media SHA mismatch",
    )

    require(
        live_media["duplicate_count_verified"]
        == 1,
        "live WordPress media duplicate count mismatch",
    )

    live_post = get_live_post(
        rest_base=rest_base,
        authorization=authorization,
    )

    live_post_result = validate_post(
        live_post,
        expected_status="publish",
    )

    require(
        live_post_result["link"]
        == EXPECTED_PUBLIC_URL,
        "live WordPress public URL mismatch",
    )

    validate_public_url(
        live_post_result["link"],
        expected_hostname=wp_hostname,
    )

    public_page = verify_public_page(
        public_url=EXPECTED_PUBLIC_URL,
        expected_hostname=wp_hostname,
    )

    require(
        public_page["http_status"] == 200,
        "public page GET did not return 200",
    )

    require(
        public_page["resolved_url"]
        == EXPECTED_PUBLIC_URL,
        "public page resolved URL mismatch",
    )

    verified_at = datetime.now(
        timezone.utc
    ).isoformat()

    verification_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_PUBLICATION_"
            "POST_EXECUTION_VERIFICATION"
        ),
        "verification_state": (
            "WORDPRESS_POST_195_PUBLISH_AND_"
            "PUBLIC_URL_VERIFIED_"
            "X_URL_REPLACEMENT_READY"
        ),
        "verified_at": verified_at,
        "source_publication_receipt_path": str(
            publication_receipt_path
        ),
        "source_publication_receipt_digest_sha256": (
            EXPECTED_RECEIPT_DIGEST
        ),
        "execution_claim_path": str(
            execution_claim_path
        ),
        "consumption_lock_path": str(
            consumption_lock_path
        ),
        "wordpress_media": live_media,
        "wordpress_post": live_post_result,
        "public_page_verification": public_page,
        "approval_consumed": True,
        "reexecution_allowed": False,
        "actual_publication_update_count": 1,
        "wordpress_api_call": True,
        "wordpress_api_method": "GET_ONLY",
        "wordpress_write": False,
        "wordpress_post_update": False,
        "wordpress_publication_executed": True,
        "wordpress_post_status": "publish",
        "public_url_available": True,
        "public_url": EXPECTED_PUBLIC_URL,
        "x_public_url_replacement_allowed": True,
        "x_final_review_allowed": False,
        "x_post_execution_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "WORDPRESS_PUBLICATION_VERIFIED_"
            "X_LOCAL_URL_REPLACEMENT_ONLY_ALLOWED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-DRAFT-PUBLIC-URL-"
            "REPLACEMENT-LOCAL-PREP"
        ),
    }

    verification = {
        **verification_payload,
        "wordpress_publication_post_execution_"
        "verification_digest_sha256": (
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
        "--publication-receipt",
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
        result = verify_publication(
            production_database_path=(
                args.production_db
            ),
            publication_receipt_path=(
                args.publication_receipt
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
                        "FAIL_WORDPRESS_PUBLICATION_"
                        "POST_EXECUTION_VERIFICATION"
                    ),
                    "error": str(exc),
                    "wordpress_api_method": "GET_ONLY",
                    "wordpress_write": False,
                    "reexecution_allowed": False,
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

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "verification_state": (
                    result["verification_state"]
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
                "wordpress_media_id": (
                    result[
                        "wordpress_media"
                    ]["media_id"]
                ),
                "wordpress_media_sha256": (
                    result[
                        "wordpress_media"
                    ]["sha256"]
                ),
                "public_url_available": True,
                "public_url": (
                    result["public_url"]
                ),
                "public_http_status": (
                    result[
                        "public_page_verification"
                    ]["http_status"]
                ),
                "approval_consumed": True,
                "reexecution_allowed": False,
                "wordpress_api_method": "GET_ONLY",
                "wordpress_write": False,
                "x_public_url_replacement_allowed": True,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "verification_pack_path": str(
                    args.output.resolve()
                ),
                "verification_digest_sha256": (
                    result[
                        "wordpress_publication_"
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
