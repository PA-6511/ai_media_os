from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.run_x_r11_wordpress_draft_creation_once import (
    build_authorization_header,
    build_rest_base,
    first_env,
    load_json,
    parse_env_file,
    request_json,
    sha256_file,
    validate_created_post,
    verify_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-MEDIA-PUBLICATION-READINESS-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_WORDING_GATE_DIGEST = (
    "b52ca408c72095ea3b958bf28c044804"
    "c1f554ceda5f7b8fa7084539eda6ea8c"
)

EXPECTED_VERIFICATION_DIGEST = (
    "3271baa516a5d5de36a087195430aade3"
    "788a364aa543670c2044d33f7699514"
)

EXPECTED_DISCOVERY_DIGEST = (
    "006c8d083fe434e4c603342a99a160fe"
    "0b157a67a1f09c66f64fd4afd05e0b74"
)

EXPECTED_FINAL_GATE_DIGEST = (
    "f348d6f37980fdd5ccd5e9c9f5bc84c3"
    "7afc80509b369cd293fb5614f7edfd86"
)

EXPECTED_ORIGINAL_HTML_SHA = (
    "ae18a9116741fea0ea51bc105ed89a6c5"
    "14bf512bc02d1d0c69f6998695aef5b"
)

EXPECTED_COVER_SHA = (
    "fcd5ed6e8a2136f45a380e055d3a34e7"
    "fe1e0d90cfaed9c8bcc8839c95a890c7"
)

EXPECTED_POST_ID = 195

EXPECTED_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

REMOTE_COVER_URL = (
    "https://shop.r10s.jp/"
    "rakutenkobo-ebooks/cabinet/6437/"
    "2000020786437.jpg"
)

EXPECTED_COVER_ALT = (
    "のあ先輩はともだち。 "
    "第11巻 書影"
)

MEDIA_FILENAME = (
    "noa-senpai-wa-tomodachi-"
    "11-cover.jpg"
)

MEDIA_URL_PLACEHOLDER = (
    "{{WORDPRESS_MEDIA_SOURCE_URL}}"
)

HTTP_TIMEOUT_SECONDS = 20
MAX_IMAGE_BYTES = 5 * 1024 * 1024

ALLOWED_IMAGE_HOSTS = {
    "shop.r10s.jp",
    "tshop.r10s.jp",
}


class MediaReadinessError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise MediaReadinessError(
            message
        )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def atomic_write_bytes(
    path: Path,
    value: bytes,
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    descriptor = os.open(
        temporary,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_TRUNC,
        0o600,
    )

    try:
        os.write(
            descriptor,
            value,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

    os.replace(
        temporary,
        path,
    )


def atomic_write_text(
    path: Path,
    value: str,
) -> None:
    atomic_write_bytes(
        path,
        value.encode("utf-8"),
    )


def validate_media_filename(
    value: str,
) -> None:
    require(
        value == MEDIA_FILENAME,
        "media filename mismatch",
    )

    require(
        value.endswith(".jpg"),
        "media filename must end in .jpg",
    )

    require(
        "/" not in value
        and "\\" not in value,
        "media filename must not contain a path",
    )


def validate_image_binary(
    value: bytes,
    *,
    expected_sha256: str = EXPECTED_COVER_SHA,
) -> dict[str, Any]:
    require(
        0 < len(value) <= MAX_IMAGE_BYTES,
        "cover image size is outside limits",
    )

    require(
        value.startswith(b"\xff\xd8\xff"),
        "cover image is not a JPEG",
    )

    digest = sha256_bytes(
        value
    )

    require(
        digest == expected_sha256,
        "cover image SHA mismatch",
    )

    return {
        "byte_size": len(value),
        "sha256": digest,
        "jpeg_magic_verified": True,
        "maximum_byte_size": (
            MAX_IMAGE_BYTES
        ),
    }


def fetch_cover_image(
    url: str,
) -> tuple[
    bytes,
    dict[str, Any],
]:
    parsed = urllib.parse.urlparse(
        url
    )

    hostname = (
        parsed.hostname or ""
    ).casefold()

    require(
        parsed.scheme == "https",
        "cover URL must use HTTPS",
    )

    require(
        hostname in ALLOWED_IMAGE_HOSTS,
        (
            "cover image hostname is "
            f"not allowed: {hostname!r}"
        ),
    )

    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Accept": (
                "image/jpeg,"
                "application/octet-stream;q=0.5"
            ),
            "User-Agent": (
                "ai-media-os-x-r11-media-prep/1.0"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
                .split(
                    ";",
                    1,
                )[0]
                .strip()
                .casefold()
            )

            value = response.read(
                MAX_IMAGE_BYTES + 1
            )

    except urllib.error.HTTPError as exc:
        raise MediaReadinessError(
            (
                "cover image HTTP failure: "
                f"{exc.code}"
            )
        ) from exc

    except urllib.error.URLError as exc:
        raise MediaReadinessError(
            (
                "cover image connection "
                f"failure: {exc}"
            )
        ) from exc

    require(
        content_type in {
            "image/jpeg",
            "image/jpg",
            "application/octet-stream",
        },
        (
            "unexpected cover content type: "
            f"{content_type!r}"
        ),
    )

    validation = validate_image_binary(
        value
    )

    return (
        value,
        {
            **validation,
            "content_type": content_type,
            "source_url": url,
            "source_hostname": hostname,
            "fetch_timeout_seconds": (
                HTTP_TIMEOUT_SECONDS
            ),
        },
    )


def replace_remote_cover_url(
    original_content: str,
) -> str:
    require(
        original_content.count(
            REMOTE_COVER_URL
        )
        == 1,
        (
            "remote cover URL count "
            "must equal one"
        ),
    )

    require(
        MEDIA_URL_PLACEHOLDER
        not in original_content,
        (
            "media URL placeholder already "
            "exists in original content"
        ),
    )

    updated = original_content.replace(
        REMOTE_COVER_URL,
        MEDIA_URL_PLACEHOLDER,
        1,
    )

    require(
        REMOTE_COVER_URL
        not in updated,
        "remote cover URL remains",
    )

    require(
        updated.count(
            MEDIA_URL_PLACEHOLDER
        )
        == 1,
        (
            "media URL placeholder count "
            "must equal one"
        ),
    )

    require(
        (
            'alt="'
            + EXPECTED_COVER_ALT
            + '"'
        )
        in updated,
        "cover alt text is missing",
    )

    require(
        "ebook-cover-image"
        in updated,
        "cover-image marker is missing",
    )

    return updated


def validate_wording_gate(
    value: dict[str, Any],
) -> None:
    require(
        value.get("status")
        == (
            "PASS_X_DRAFT_WORDING_REVIEW_"
            "APPROVED_PUBLIC_URL_PENDING"
        ),
        "wording review gate did not pass",
    )

    require(
        value.get("wording_gate_state")
        == (
            "WORDING_FIXED_AWAITING_"
            "WORDPRESS_PUBLICATION_AND_PUBLIC_URL"
        ),
        "wording gate state mismatch",
    )

    human_review = value.get(
        "human_review"
    )

    require(
        isinstance(human_review, dict),
        "wording human-review evidence is missing",
    )

    require(
        human_review.get("decision")
        == "APPROVED",
        "wording was not approved",
    )

    require(
        human_review.get(
            "approval_consumed"
        )
        is True,
        (
            "wording approval was "
            "not consumed"
        ),
    )

    x_draft = value.get(
        "x_draft"
    )

    require(
        isinstance(x_draft, dict),
        "fixed X draft is missing",
    )

    require(
        x_draft.get("wording_fixed")
        is True,
        "X wording is not fixed",
    )

    wordpress_post = value.get(
        "wordpress_post"
    )

    require(
        isinstance(wordpress_post, dict),
        "WordPress post evidence is missing",
    )

    require(
        wordpress_post.get("post_id")
        == EXPECTED_POST_ID,
        "WordPress post ID mismatch",
    )

    require(
        wordpress_post.get("status")
        == "draft",
        "WordPress post must remain draft",
    )

    require(
        value.get(
            "wordpress_publication_allowed"
        )
        is False,
        (
            "publication must remain "
            "blocked"
        ),
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        (
            "X execution must remain "
            "blocked"
        ),
    )


def build_readiness_prep(
    *,
    production_database_path: Path,
    wording_gate_pack_path: Path,
    verification_pack_path: Path,
    discovery_pack_path: Path,
    final_gate_pack_path: Path,
    credential_env_path: Path,
    local_media_path: Path,
    content_preview_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    wording_gate_pack_path = (
        wording_gate_pack_path.resolve()
    )

    verification_pack_path = (
        verification_pack_path.resolve()
    )

    discovery_pack_path = (
        discovery_pack_path.resolve()
    )

    final_gate_pack_path = (
        final_gate_pack_path.resolve()
    )

    credential_env_path = (
        credential_env_path.resolve()
    )

    local_media_path = (
        local_media_path.resolve()
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

    wording_gate = load_json(
        wording_gate_pack_path
    )

    verify_digest(
        wording_gate,
        digest_field=(
            "x_draft_wording_review_gate_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_WORDING_GATE_DIGEST
        ),
        label="X wording review gate",
    )

    validate_wording_gate(
        wording_gate
    )

    verification = load_json(
        verification_pack_path
    )

    verify_digest(
        verification,
        digest_field=(
            "wordpress_draft_post_creation_"
            "verification_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_VERIFICATION_DIGEST
        ),
        label="post-creation verification",
    )

    require(
        verification.get("status")
        == (
            "PASS_WORDPRESS_DRAFT_"
            "POST_CREATION_VERIFICATION"
        ),
        (
            "post-creation verification "
            "did not pass"
        ),
    )

    discovery = load_json(
        discovery_pack_path
    )

    verify_digest(
        discovery,
        digest_field=(
            "wordpress_draft_render_input_"
            "discovery_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_DISCOVERY_DIGEST
        ),
        label="cover discovery",
    )

    cover = discovery.get(
        "cover_image"
    )

    require(
        isinstance(cover, dict),
        "cover evidence is missing",
    )

    require(
        cover.get("cover_image_url")
        == REMOTE_COVER_URL,
        "cover source URL mismatch",
    )

    require(
        cover.get("cover_image_alt")
        == EXPECTED_COVER_ALT,
        "cover alt text mismatch",
    )

    require(
        cover.get("sha256")
        == EXPECTED_COVER_SHA,
        "cover evidence SHA mismatch",
    )

    require(
        cover.get("width") == 300,
        "cover width mismatch",
    )

    require(
        cover.get("height") == 373,
        "cover height mismatch",
    )

    image_policy = discovery.get(
        "image_usage_policy"
    )

    require(
        isinstance(image_policy, dict),
        "image usage policy is missing",
    )

    require(
        image_policy.get(
            "source_image_hotlink_approved"
        )
        is False,
        (
            "source-image hotlink must "
            "remain unapproved"
        ),
    )

    require(
        image_policy.get(
            "wordpress_media_upload_"
            "required_before_publish"
        )
        is True,
        (
            "WordPress media upload "
            "requirement is missing"
        ),
    )

    final_gate = load_json(
        final_gate_pack_path
    )

    verify_digest(
        final_gate,
        digest_field=(
            "wordpress_draft_final_gate_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_FINAL_GATE_DIGEST
        ),
        label="WordPress Final Gate",
    )

    payload_preview = load_json(
        Path(
            final_gate[
                "payload_preview_path"
            ]
        )
    )

    verify_digest(
        payload_preview,
        digest_field=(
            "wordpress_draft_payload_"
            "preview_digest_sha256"
        ),
        expected_digest=(
            final_gate[
                "payload_preview_digest_sha256"
            ]
        ),
        label="WordPress payload preview",
    )

    request_payload = payload_preview.get(
        "wordpress_request"
    )

    require(
        isinstance(request_payload, dict),
        "WordPress request preview is missing",
    )

    original_content = request_payload.get(
        "content"
    )

    require(
        isinstance(original_content, str)
        and original_content,
        "original article content is missing",
    )

    require(
        sha256_text(original_content)
        == EXPECTED_ORIGINAL_HTML_SHA,
        "original article HTML SHA mismatch",
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

    live_post_url = (
        rest_base.rstrip("/")
        + "/posts/"
        + str(EXPECTED_POST_ID)
        + "?context=edit"
        + "&_fields=id,title,slug,status,"
        + "categories,content,link"
    )

    live_post = request_json(
        method="GET",
        url=live_post_url,
        authorization=authorization,
    )

    require(
        isinstance(live_post, dict),
        "live WordPress post is invalid",
    )

    post_result = validate_created_post(
        live_post,
        expected_content=original_content,
    )

    require(
        post_result["post_id"]
        == EXPECTED_POST_ID,
        "live post ID mismatch",
    )

    validate_media_filename(
        MEDIA_FILENAME
    )

    image_bytes, image_validation = (
        fetch_cover_image(
            REMOTE_COVER_URL
        )
    )

    atomic_write_bytes(
        local_media_path,
        image_bytes,
    )

    require(
        sha256_file(
            local_media_path
        )
        == EXPECTED_COVER_SHA,
        "written local media SHA mismatch",
    )

    content_preview = (
        replace_remote_cover_url(
            original_content
        )
    )

    atomic_write_text(
        content_preview_path,
        content_preview,
    )

    content_preview_sha = sha256_text(
        content_preview
    )

    prepared_at = datetime.now(
        timezone.utc
    ).isoformat()

    media_upload_request_id = (
        "xr11-wp-media-upload-"
        + EXPECTED_COVER_SHA[:24]
    )

    draft_update_request_id = (
        "xr11-wp-draft-update-"
        + content_preview_sha[:24]
    )

    prep_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_MEDIA_"
            "PUBLICATION_READINESS_PREP"
        ),
        "readiness_state": (
            "MEDIA_BINARY_FIXED_AWAITING_"
            "EXPLICIT_MEDIA_UPLOAD_AND_"
            "DRAFT_UPDATE_APPROVAL"
        ),
        "prepared_at": prepared_at,
        "source_wording_gate_pack_path": str(
            wording_gate_pack_path
        ),
        "source_wording_gate_digest_sha256": (
            EXPECTED_WORDING_GATE_DIGEST
        ),
        "source_verification_pack_path": str(
            verification_pack_path
        ),
        "source_verification_digest_sha256": (
            EXPECTED_VERIFICATION_DIGEST
        ),
        "source_discovery_pack_path": str(
            discovery_pack_path
        ),
        "source_discovery_digest_sha256": (
            EXPECTED_DISCOVERY_DIGEST
        ),
        "source_final_gate_pack_path": str(
            final_gate_pack_path
        ),
        "source_final_gate_digest_sha256": (
            EXPECTED_FINAL_GATE_DIGEST
        ),
        "wordpress_post": {
            "post_id": EXPECTED_POST_ID,
            "title": EXPECTED_TITLE,
            "slug": EXPECTED_SLUG,
            "status": "draft",
            "category_ids": [43],
            "public_url_available": False,
        },
        "cover_media": {
            "source_url": REMOTE_COVER_URL,
            "source_hotlink_approved": False,
            "local_media_path": str(
                local_media_path
            ),
            "filename": MEDIA_FILENAME,
            "mime_type": "image/jpeg",
            "title": EXPECTED_COVER_ALT,
            "alt_text": EXPECTED_COVER_ALT,
            "caption": "",
            "description": (
                "『のあ先輩はともだち。』"
                "第11巻の書影"
            ),
            "expected_width": 300,
            "expected_height": 373,
            **image_validation,
        },
        "media_upload_request_preview": {
            "request_id": (
                media_upload_request_id
            ),
            "api_method": "POST_ONCE",
            "resource": "/wp-json/wp/v2/media",
            "binary_path": str(
                local_media_path
            ),
            "filename": MEDIA_FILENAME,
            "content_type": "image/jpeg",
            "metadata_after_upload": {
                "title": EXPECTED_COVER_ALT,
                "alt_text": EXPECTED_COVER_ALT,
                "caption": "",
                "description": (
                    "『のあ先輩はともだち。』"
                    "第11巻の書影"
                ),
            },
            "maximum_create_count": 1,
            "execution_allowed": False,
        },
        "draft_content_update_preview": {
            "request_id": (
                draft_update_request_id
            ),
            "api_method": "POST_ONCE",
            "resource": (
                "/wp-json/wp/v2/posts/195"
            ),
            "post_status_must_remain": "draft",
            "original_content_sha256": (
                EXPECTED_ORIGINAL_HTML_SHA
            ),
            "content_preview_path": str(
                content_preview_path
            ),
            "content_preview_sha256": (
                content_preview_sha
            ),
            "media_source_url_placeholder": (
                MEDIA_URL_PLACEHOLDER
            ),
            "placeholder_count": 1,
            "remote_source_url_removed": True,
            "execution_allowed": False,
        },
        "execution_constraints": {
            "media_upload_count_maximum": 1,
            "post_update_count_maximum": 1,
            "post_id_must_equal": (
                EXPECTED_POST_ID
            ),
            "post_status_must_remain": "draft",
            "failure_stops_all": True,
            "duplicate_media_preflight_required": True,
            "media_sha_verification_required": True,
            "media_source_url_verification_required": True,
            "reexecution_lock_required": True,
            "publication_in_same_execution_allowed": False,
        },
        "remaining_requirements": [
            "HUMAN_MEDIA_AND_DRAFT_UPDATE_REVIEW",
            "EXPLICIT_MEDIA_UPLOAD_AND_DRAFT_UPDATE_APPROVAL",
            "MEDIA_UPLOAD_ONE_SHOT",
            "DRAFT_CONTENT_UPDATE_ONE_SHOT",
            "POST_UPDATE_VERIFICATION",
            "SEPARATE_WORDPRESS_PUBLICATION_REVIEW",
            "SEPARATE_WORDPRESS_PUBLICATION_APPROVAL",
            "PUBLIC_URL_VERIFICATION",
            "X_PUBLIC_URL_REPLACEMENT",
            "FINAL_X_REVIEW",
            "EXPLICIT_X_POST_APPROVAL",
        ],
        "media_binary_fixed": True,
        "media_upload_allowed": False,
        "draft_content_update_allowed": False,
        "wordpress_publication_allowed": False,
        "public_url_available": False,
        "x_public_url_replacement_allowed": False,
        "x_post_execution_allowed": False,
        "external_image_fetch": True,
        "wordpress_api_call": True,
        "wordpress_api_method": "GET_ONLY",
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_update": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "MEDIA_AND_DRAFT_UPDATE_PREVIEW_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-MEDIA-DRAFT-UPDATE-"
            "HUMAN-REVIEW-PREP"
        ),
    }

    prep = {
        **prep_payload,
        "wordpress_media_publication_"
        "readiness_prep_digest_sha256": (
            __import__(
                "scripts.build_x_r9_preflight_approval_pack",
                fromlist=["canonical_digest"],
            ).canonical_digest(
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
        "--wording-gate-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--verification-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--discovery-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--final-gate-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--credential-env",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--local-media",
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
        result = build_readiness_prep(
            production_database_path=(
                args.production_db
            ),
            wording_gate_pack_path=(
                args.wording_gate_pack
            ),
            verification_pack_path=(
                args.verification_pack
            ),
            discovery_pack_path=(
                args.discovery_pack
            ),
            final_gate_pack_path=(
                args.final_gate_pack
            ),
            credential_env_path=(
                args.credential_env
            ),
            local_media_path=(
                args.local_media
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
                        "FAIL_WORDPRESS_MEDIA_"
                        "PUBLICATION_READINESS_PREP"
                    ),
                    "error": str(exc),
                    "media_upload_allowed": False,
                    "draft_content_update_allowed": False,
                    "wordpress_publication_allowed": False,
                    "wordpress_write": False,
                    "x_api_call": False,
                    "x_post": False,
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
                "readiness_state": (
                    result["readiness_state"]
                ),
                "wordpress_post_id": 195,
                "wordpress_post_status": "draft",
                "media_binary_fixed": True,
                "media_sha256": (
                    result[
                        "cover_media"
                    ]["sha256"]
                ),
                "media_byte_size": (
                    result[
                        "cover_media"
                    ]["byte_size"]
                ),
                "media_upload_allowed": False,
                "draft_content_update_allowed": False,
                "wordpress_publication_allowed": False,
                "wordpress_api_method": "GET_ONLY",
                "wordpress_write": False,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "local_media_path": (
                    result[
                        "cover_media"
                    ]["local_media_path"]
                ),
                "content_preview_path": (
                    result[
                        "draft_content_update_preview"
                    ]["content_preview_path"]
                ),
                "prep_pack_path": str(
                    args.output.resolve()
                ),
                "prep_digest_sha256": (
                    result[
                        "wordpress_media_publication_"
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
