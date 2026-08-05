from __future__ import annotations

import argparse
import hashlib
import html
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
from scripts.build_x_r11_wordpress_publication_readiness_prep import (
    EXPECTED_MEDIA_ID,
    EXPECTED_MEDIA_SHA,
    EXPECTED_MEDIA_SOURCE_URL,
    EXPECTED_POST_ID,
    EXPECTED_POST_TITLE,
    EXPECTED_POST_SLUG,
    EXPECTED_UPDATED_CONTENT_SHA,
    validate_live_draft,
    validate_publication_request_preview,
    validate_single_media_duplicate,
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
    "WORDPRESS-PUBLICATION-HUMAN-REVIEW-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_READINESS_DIGEST = (
    "a12a60b5f1cba0d44600184f8ea6484b"
    "6c75148f7eaaeb626ab451f944c514f4"
)

EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST = (
    "48ca178ad9af187afa505ac4866f7e404"
    "ed04daba15ea1a2ede00c25caed8257"
)

EXPECTED_CATEGORY_ID = 43

EXPECTED_PUBLICATION_REQUEST_ID = (
    "xr11-wp-publish-"
    "48ca178ad9af187afa505ac4"
)

EXPECTED_MEDIA_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻 書影"
)

CURRENT_PRODUCT_HASH = (
    "bce9f1878b0032dc4745ecf22fd179a6"
)

BLOCKED_OLD_PRODUCT_HASH = (
    "f402536ea6473a172c957407fae06192"
)

REMOTE_COVER_URL = (
    "https://shop.r10s.jp/"
    "rakutenkobo-ebooks/cabinet/6437/"
    "2000020786437.jpg"
)

MEDIA_URL_PLACEHOLDER = (
    "{{WORDPRESS_MEDIA_SOURCE_URL}}"
)

PUBLIC_URL_PLACEHOLDER = (
    "{{WORDPRESS_PUBLIC_URL}}"
)

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "PUBLICATION_ONLY"
)

APPROVAL_SCOPE = (
    "ONE_WORDPRESS_POST_195_"
    "PUBLICATION_STATUS_UPDATE_ONLY"
)

EXPECTED_CHECK_COUNT = 12

ALLOWED_AFFILIATE_HOSTS = {
    "hb.afl.rakuten.co.jp",
    "a.r10.to",
}


class PublicationHumanReviewError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise PublicationHumanReviewError(
            message
        )


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


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

    temporary.replace(path)


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


def extract_affiliate_urls(
    content: str,
) -> list[str]:
    href_values = re.findall(
        r'''href=["']([^"']+)["']''',
        content,
        flags=re.IGNORECASE,
    )

    candidates: list[str] = []

    for raw_value in href_values:
        value = html.unescape(
            raw_value.strip()
        )

        parsed = urllib.parse.urlparse(
            value
        )

        hostname = (
            parsed.hostname or ""
        ).casefold()

        if (
            parsed.scheme == "https"
            and hostname
            in ALLOWED_AFFILIATE_HOSTS
        ):
            candidates.append(value)

    return list(
        dict.fromkeys(candidates)
    )


def validate_review_content(
    content: str,
    *,
    expected_content_sha256: str = (
        EXPECTED_UPDATED_CONTENT_SHA
    ),
    expected_media_source_url: str = (
        EXPECTED_MEDIA_SOURCE_URL
    ),
) -> dict[str, Any]:
    require(
        sha256_text(content)
        == expected_content_sha256,
        "publication review content SHA mismatch",
    )

    require(
        content.count(
            expected_media_source_url
        )
        == 1,
        (
            "WordPress media source URL "
            "count must equal one"
        ),
    )

    require(
        REMOTE_COVER_URL not in content,
        "remote cover URL remains",
    )

    require(
        MEDIA_URL_PLACEHOLDER
        not in content,
        "media URL placeholder remains",
    )

    require(
        PUBLIC_URL_PLACEHOLDER
        not in content,
        "public URL placeholder appears in article",
    )

    required_markers = (
        "ebook-new-release-article",
        "ebook-pr-disclosure",
        "ebook-cover-image",
        "price-cards",
        "store-buttons",
    )

    missing_markers = [
        marker
        for marker in required_markers
        if marker not in content
    ]

    require(
        not missing_markers,
        (
            "required article markers are missing: "
            + ", ".join(missing_markers)
        ),
    )

    require(
        EXPECTED_MEDIA_TITLE
        in content,
        "cover alt text is missing",
    )

    require(
        BLOCKED_OLD_PRODUCT_HASH
        not in content,
        "superseded affiliate hash remains",
    )

    affiliate_urls = extract_affiliate_urls(
        content
    )

    require(
        len(affiliate_urls) == 1,
        (
            "exactly one permitted affiliate "
            f"URL is required; found={len(affiliate_urls)}"
        ),
    )

    require(
        CURRENT_PRODUCT_HASH
        in affiliate_urls[0],
        "current affiliate product hash is missing",
    )

    return {
        "content_sha256_verified": True,
        "media_source_url_count": 1,
        "remote_cover_url_absent": True,
        "media_placeholder_absent": True,
        "public_url_placeholder_absent": True,
        "required_article_markers_verified": True,
        "pr_disclosure_verified": True,
        "cover_alt_text_verified": True,
        "affiliate_url_count": 1,
        "affiliate_url": affiliate_urls[0],
        "current_affiliate_hash_verified": True,
        "old_affiliate_hash_absent": True,
    }


def build_review_checklist() -> list[dict[str, str]]:
    return [
        {
            "check_id": "POST_TITLE_AND_VOLUME",
            "description": (
                "作品名・巻数・配信開始の"
                "タイトル表記が正しい"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "RELEASE_INFORMATION",
            "description": (
                "発売日・著者・出版社の"
                "新刊情報が正しい"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "CATEGORY_ASSIGNMENT",
            "description": (
                "カテゴリがコミック新刊"
                "（ID 43）だけである"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "PR_DISCLOSURE",
            "description": (
                "広告・PR表示が見やすい位置にある"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "COVER_IMAGE",
            "description": (
                "書影が正しく表示され、"
                "代替テキストも適切である"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "AFFILIATE_DESTINATION",
            "description": (
                "楽天Koboボタンが対象商品の"
                "正しいアフィリエイトURLへ接続する"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "PRICE_AND_STORE_UI",
            "description": (
                "価格カードとストアボタンの"
                "表示崩れがない"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "MOBILE_DISPLAY",
            "description": (
                "スマートフォン表示で書影・"
                "本文・ボタンが崩れていない"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "CONTENT_FREEZE",
            "description": (
                "公開時にタイトル・本文・スラッグ・"
                "カテゴリ・書影を変更しない"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "PUBLICATION_SCOPE",
            "description": (
                "対象が投稿ID 195の"
                "draft→publish変更1回だけである"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "PUBLIC_URL_VERIFICATION",
            "description": (
                "公開後にHTTPS公開URLと"
                "表示内容を別工程で再確認する"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "X_EXECUTION_BOUNDARY",
            "description": (
                "今回の承認・実行にX投稿や"
                "X API呼出しを含めない"
            ),
            "human_decision": "PENDING",
        },
    ]


def validate_pending_checklist(
    checklist: Any,
) -> None:
    require(
        isinstance(checklist, list),
        "human review checklist must be a list",
    )

    require(
        len(checklist)
        == EXPECTED_CHECK_COUNT,
        (
            "human review checklist must contain "
            f"{EXPECTED_CHECK_COUNT} checks"
        ),
    )

    check_ids: list[str] = []

    for item in checklist:
        require(
            isinstance(item, dict),
            "human review checklist item is invalid",
        )

        check_id = item.get(
            "check_id"
        )

        require(
            isinstance(check_id, str)
            and check_id,
            "human review check ID is missing",
        )

        require(
            item.get("human_decision")
            == "PENDING",
            (
                "human review checklist must "
                "remain pending"
            ),
        )

        check_ids.append(check_id)

    require(
        len(set(check_ids))
        == EXPECTED_CHECK_COUNT,
        "human review check IDs are not unique",
    )


def build_human_review_prep(
    *,
    production_database_path: Path,
    readiness_prep_path: Path,
    credential_env_path: Path,
    content_preview_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    readiness_prep_path = (
        readiness_prep_path.resolve()
    )

    credential_env_path = (
        credential_env_path.resolve()
    )

    content_preview_path = (
        content_preview_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    readiness = load_json(
        readiness_prep_path
    )

    verify_digest(
        readiness,
        digest_field=(
            "wordpress_publication_readiness_"
            "prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_READINESS_DIGEST
        ),
        label="publication readiness prep",
    )

    require(
        readiness.get("status")
        == (
            "PASS_WORDPRESS_PUBLICATION_"
            "READINESS_PREP"
        ),
        "publication readiness prep did not pass",
    )

    require(
        readiness.get("readiness_state")
        == (
            "PUBLICATION_REQUEST_PREVIEW_FIXED_"
            "AWAITING_HUMAN_REVIEW"
        ),
        "publication readiness state mismatch",
    )

    require(
        readiness.get(
            "source_post_execution_verification_"
            "digest_sha256"
        )
        == EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST,
        "source verification digest mismatch",
    )

    require(
        readiness.get(
            "human_review_required"
        )
        is True,
        "human review is not required",
    )

    require(
        readiness.get(
            "human_review_completed"
        )
        is False,
        "human review is already complete",
    )

    require(
        readiness.get(
            "publication_approval_issued"
        )
        is False,
        "publication approval was already issued",
    )

    require(
        readiness.get(
            "publication_execution_allowed"
        )
        is False,
        "publication execution is already allowed",
    )

    require(
        readiness.get(
            "wordpress_publication_allowed"
        )
        is False,
        "WordPress publication is already allowed",
    )

    require(
        readiness.get(
            "public_url_available"
        )
        is False,
        "public URL is unexpectedly available",
    )

    require(
        readiness.get(
            "x_post_execution_allowed"
        )
        is False,
        "X post execution is unexpectedly allowed",
    )

    publication_preview = readiness.get(
        "publication_request_preview"
    )

    require(
        isinstance(publication_preview, dict),
        "publication request preview is missing",
    )

    validate_publication_request_preview(
        publication_preview
    )

    require(
        publication_preview.get("request_id")
        == EXPECTED_PUBLICATION_REQUEST_ID,
        "publication request ID mismatch",
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

    live_media = get_media_by_id(
        rest_base=rest_base,
        authorization=authorization,
        media_id=EXPECTED_MEDIA_ID,
    )

    media_result = validate_media_object(
        live_media,
        wp_hostname=wp_hostname,
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

    media_binary = verify_media_source_binary(
        source_url=media_result[
            "source_url"
        ],
        authorization=authorization,
        wp_hostname=wp_hostname,
    )

    require(
        media_binary["sha256"]
        == EXPECTED_MEDIA_SHA,
        "live media SHA mismatch",
    )

    duplicate_state = find_media_duplicates(
        rest_base=rest_base,
        authorization=authorization,
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

    raw_content = extract_raw_content(
        live_post
    )

    content_validation = validate_review_content(
        raw_content
    )

    atomic_write_text(
        content_preview_path,
        raw_content,
    )

    require(
        sha256_file(
            content_preview_path
        )
        == EXPECTED_UPDATED_CONTENT_SHA,
        "written review content SHA mismatch",
    )

    checklist = build_review_checklist()

    validate_pending_checklist(
        checklist
    )

    prepared_at = datetime.now(
        timezone.utc
    ).isoformat()

    review_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_PUBLICATION_"
            "HUMAN_REVIEW_PREP_READY"
        ),
        "human_review_state": (
            "AWAITING_EXPLICIT_HUMAN_"
            "PUBLICATION_DECISION"
        ),
        "prepared_at": prepared_at,
        "source_readiness_prep_path": str(
            readiness_prep_path
        ),
        "source_readiness_prep_digest_sha256": (
            EXPECTED_READINESS_DIGEST
        ),
        "source_post_execution_verification_digest_sha256": (
            EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST
        ),
        "wordpress_media": {
            **media_result,
            "sha256": media_binary[
                "sha256"
            ],
            "byte_size": media_binary[
                "byte_size"
            ],
            "duplicate_count_verified": 1,
        },
        "wordpress_post": {
            **post_result,
            "content_preview_path": str(
                content_preview_path
            ),
            "content_validation": (
                content_validation
            ),
        },
        "publication_request_preview": (
            publication_preview
        ),
        "machine_precheck": {
            "passed": True,
            "check_count": (
                EXPECTED_CHECK_COUNT
            ),
            "post_status_is_draft": True,
            "content_sha256_verified": True,
            "media_sha256_verified": True,
            "media_duplicate_count_verified": 1,
            "pr_disclosure_verified": True,
            "affiliate_url_verified": True,
            "publication_request_is_status_only": True,
            "x_execution_blocked": True,
        },
        "human_review_checklist": checklist,
        "approval_label_if_approved": (
            APPROVAL_LABEL
        ),
        "approval_scope_if_approved": (
            APPROVAL_SCOPE
        ),
        "human_decision": "PENDING",
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
            "PUBLICATION_HUMAN_REVIEW_PENDING_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-PUBLICATION-"
            "EXPLICIT-APPROVAL-GATE"
        ),
    }

    review = {
        **review_payload,
        "wordpress_publication_human_review_"
        "prep_digest_sha256": (
            canonical_digest(
                review_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        review,
    )

    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--readiness-prep",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--credential-env",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--content-preview",
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
        result = build_human_review_prep(
            production_database_path=(
                args.production_db
            ),
            readiness_prep_path=(
                args.readiness_prep
            ),
            credential_env_path=(
                args.credential_env
            ),
            content_preview_path=(
                args.content_preview
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
                        "HUMAN_REVIEW_PREP"
                    ),
                    "error": str(exc),
                    "human_review_completed": False,
                    "publication_approval_issued": False,
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

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "human_review_state": (
                    result["human_review_state"]
                ),
                "publication_request_id": (
                    result[
                        "publication_request_preview"
                    ]["request_id"]
                ),
                "wordpress_media_id": (
                    result[
                        "wordpress_media"
                    ]["media_id"]
                ),
                "wordpress_post_id": (
                    result[
                        "wordpress_post"
                    ]["post_id"]
                ),
                "wordpress_post_status": (
                    result[
                        "wordpress_post"
                    ]["status"]
                ),
                "wordpress_post_content_sha256": (
                    result[
                        "wordpress_post"
                    ]["content_sha256"]
                ),
                "machine_precheck_passed": True,
                "human_check_count": (
                    EXPECTED_CHECK_COUNT
                ),
                "human_decision": "PENDING",
                "publication_approval_issued": False,
                "publication_execution_allowed": False,
                "wordpress_publication_allowed": False,
                "wordpress_api_method": "GET_ONLY",
                "wordpress_write": False,
                "public_url_available": False,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "approval_label_if_approved": (
                    APPROVAL_LABEL
                ),
                "content_preview_path": str(
                    args.content_preview.resolve()
                ),
                "review_pack_path": str(
                    args.output.resolve()
                ),
                "review_digest_sha256": (
                    result[
                        "wordpress_publication_"
                        "human_review_prep_digest_sha256"
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
