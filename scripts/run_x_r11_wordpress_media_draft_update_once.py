from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
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
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)
from scripts.run_x_r11_wordpress_draft_creation_once import (
    build_authorization_header,
    build_rest_base,
    collection_url,
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
    "WORDPRESS-MEDIA-DRAFT-UPDATE-"
    "ONE-SHOT-EXECUTION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_APPROVAL_GATE_DIGEST = (
    "f608821d973164a21236c5b478425357"
    "3138a1b7f1033e81e264ec6eac5ac775"
)

EXPECTED_REVIEW_DIGEST = (
    "5b2faab0d29b9fe830daae7578d97a5b"
    "5d7fff20612a5a8afb963962f0a3d11b"
)

EXPECTED_READINESS_DIGEST = (
    "5aa7223ed42f04ab393ed21fa93f23081"
    "eb143a8b4360b5082492c9fe62c788a"
)

EXPECTED_MEDIA_SHA = (
    "fcd5ed6e8a2136f45a380e055d3a34e7"
    "fe1e0d90cfaed9c8bcc8839c95a890c7"
)

EXPECTED_ORIGINAL_CONTENT_SHA = (
    "ae18a9116741fea0ea51bc105ed89a6c5"
    "14bf512bc02d1d0c69f6998695aef5b"
)

EXPECTED_APPROVAL_REQUEST_ID = (
    "xr11-wp-media-draft-update-"
    "5b2faab0d29b9fe830daae75"
)

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "MEDIA_AND_DRAFT_UPDATE_ONLY"
)

EXPECTED_APPROVAL_SCOPE = (
    "ONE_WORDPRESS_MEDIA_UPLOAD_AND_"
    "ONE_DRAFT_CONTENT_UPDATE_ONLY"
)

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

EXPECTED_MEDIA_FILENAME = (
    "noa-senpai-wa-tomodachi-"
    "11-cover.jpg"
)

EXPECTED_MEDIA_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-cover"
)

EXPECTED_MEDIA_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻 書影"
)

EXPECTED_MEDIA_DESCRIPTION = (
    "『のあ先輩はともだち。』"
    "第11巻の書影"
)

MEDIA_URL_PLACEHOLDER = (
    "{{WORDPRESS_MEDIA_SOURCE_URL}}"
)

REMOTE_COVER_URL = (
    "https://shop.r10s.jp/"
    "rakutenkobo-ebooks/cabinet/6437/"
    "2000020786437.jpg"
)

MAX_MEDIA_BYTES = 5 * 1024 * 1024
HTTP_TIMEOUT_SECONDS = 30
RECONCILIATION_ATTEMPTS = 3


class MediaDraftUpdateExecutionError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise MediaDraftUpdateExecutionError(
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


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    try:
        descriptor = os.open(
            path,
            (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
            ),
            0o600,
        )
    except FileExistsError as exc:
        raise MediaDraftUpdateExecutionError(
            f"one-shot artifact already exists: {path}"
        ) from exc

    try:
        os.write(
            descriptor,
            data,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def extract_wp_text(
    value: Any,
) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in (
            "raw",
            "rendered",
        ):
            candidate = value.get(key)

            if isinstance(candidate, str):
                cleaned = re.sub(
                    r"<[^>]+>",
                    "",
                    html.unescape(
                        candidate
                    ),
                ).strip()

                if cleaned:
                    return cleaned

    return ""


def validate_jpeg_file(
    path: Path,
) -> bytes:
    require(
        path.is_file(),
        "local media binary is missing",
    )

    value = path.read_bytes()

    require(
        0 < len(value) <= MAX_MEDIA_BYTES,
        "media binary size is outside limits",
    )

    require(
        value.startswith(
            b"\xff\xd8\xff"
        ),
        "media binary is not a JPEG",
    )

    require(
        sha256_bytes(value)
        == EXPECTED_MEDIA_SHA,
        "media binary SHA mismatch",
    )

    return value


def validate_approval_gate(
    gate: dict[str, Any],
) -> str:
    require(
        gate.get("status")
        == (
            "PASS_WORDPRESS_MEDIA_DRAFT_UPDATE_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "approval gate status mismatch",
    )

    require(
        gate.get("approval_gate_state")
        == (
            "READY_AWAITING_ONE_SHOT_MEDIA_"
            "UPLOAD_AND_DRAFT_UPDATE_EXECUTION"
        ),
        "approval gate state mismatch",
    )

    require(
        gate.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "approval request ID mismatch",
    )

    require(
        gate.get("source_review_digest_sha256")
        == EXPECTED_REVIEW_DIGEST,
        "source review digest mismatch",
    )

    require(
        gate.get("approval_issued")
        is True,
        "approval was not issued",
    )

    require(
        gate.get("approval_consumed")
        is False,
        "approval was already consumed",
    )

    require(
        gate.get("runner_execution_allowed")
        is True,
        "runner execution is not allowed",
    )

    require(
        gate.get("media_upload_allowed")
        is True,
        "media upload is not allowed",
    )

    require(
        gate.get("draft_content_update_allowed")
        is True,
        "draft update is not allowed",
    )

    require(
        gate.get("wordpress_publication_allowed")
        is False,
        "WordPress publication is unexpectedly allowed",
    )

    require(
        gate.get("x_post_execution_allowed")
        is False,
        "X post execution is unexpectedly allowed",
    )

    limits = gate.get(
        "execution_limits"
    )

    require(
        isinstance(limits, dict),
        "execution limits are missing",
    )

    require(
        limits.get(
            "maximum_media_create_count"
        )
        == 1,
        "maximum media create count mismatch",
    )

    require(
        limits.get(
            "maximum_draft_update_count"
        )
        == 1,
        "maximum draft update count mismatch",
    )

    require(
        limits.get("target_post_id")
        == EXPECTED_POST_ID,
        "target post ID mismatch",
    )

    require(
        limits.get(
            "required_final_post_status"
        )
        == "draft",
        "required final status mismatch",
    )

    require(
        limits.get(
            "publication_in_same_execution_allowed"
        )
        is False,
        "same-execution publication is allowed",
    )

    require(
        limits.get(
            "x_post_in_same_execution_allowed"
        )
        is False,
        "same-execution X post is allowed",
    )

    certificate_digest = gate.get(
        "approval_certificate_digest_sha256"
    )

    require(
        isinstance(
            certificate_digest,
            str,
        )
        and re.fullmatch(
            r"[0-9a-f]{64}",
            certificate_digest,
        )
        is not None,
        "approval certificate digest is invalid",
    )

    return certificate_digest


def validate_certificate(
    certificate: dict[str, Any],
    *,
    expected_digest: str,
) -> None:
    verify_digest(
        certificate,
        digest_field=(
            "wordpress_media_draft_update_"
            "approval_certificate_digest_sha256"
        ),
        expected_digest=expected_digest,
        label="approval certificate",
    )

    require(
        certificate.get("status")
        == (
            "WORDPRESS_MEDIA_DRAFT_UPDATE_"
            "APPROVAL_ISSUED_NOT_CONSUMED"
        ),
        "approval certificate status mismatch",
    )

    require(
        certificate.get(
            "approval_request_id"
        )
        == EXPECTED_APPROVAL_REQUEST_ID,
        "certificate request ID mismatch",
    )

    require(
        certificate.get("approval_label")
        == EXPECTED_APPROVAL_LABEL,
        "certificate approval label mismatch",
    )

    require(
        certificate.get("approval_scope")
        == EXPECTED_APPROVAL_SCOPE,
        "certificate approval scope mismatch",
    )

    require(
        certificate.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "certificate review digest mismatch",
    )

    require(
        certificate.get(
            "source_readiness_digest_sha256"
        )
        == EXPECTED_READINESS_DIGEST,
        "certificate readiness digest mismatch",
    )

    require(
        certificate.get("wordpress_post_id")
        == EXPECTED_POST_ID,
        "certificate post ID mismatch",
    )

    require(
        certificate.get(
            "wordpress_post_status_required"
        )
        == "draft",
        "certificate post status mismatch",
    )

    require(
        certificate.get("media_sha256")
        == EXPECTED_MEDIA_SHA,
        "certificate media SHA mismatch",
    )

    require(
        certificate.get(
            "maximum_media_create_count"
        )
        == 1,
        "certificate media maximum mismatch",
    )

    require(
        certificate.get(
            "maximum_draft_update_count"
        )
        == 1,
        "certificate update maximum mismatch",
    )

    require(
        certificate.get(
            "runner_execution_allowed"
        )
        is True,
        "certificate does not allow runner",
    )

    require(
        certificate.get(
            "approval_consumed"
        )
        is False,
        "certificate approval was already consumed",
    )

    require(
        certificate.get(
            "wordpress_publication_allowed"
        )
        is False,
        "certificate permits publication",
    )


def validate_issuance_lock(
    lock: dict[str, Any],
    *,
    certificate_digest: str,
    approval_gate_digest: str,
) -> None:
    require(
        lock.get("lock_type")
        == (
            "X_R11_WORDPRESS_MEDIA_DRAFT_"
            "UPDATE_APPROVAL_ISSUANCE"
        ),
        "issuance lock type mismatch",
    )

    require(
        lock.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "issuance lock request ID mismatch",
    )

    require(
        lock.get("source_review_digest_sha256")
        == EXPECTED_REVIEW_DIGEST,
        "issuance lock review digest mismatch",
    )

    require(
        lock.get(
            "approval_certificate_digest_sha256"
        )
        == certificate_digest,
        "issuance lock certificate digest mismatch",
    )

    require(
        lock.get(
            "approval_gate_digest_sha256"
        )
        == approval_gate_digest,
        "issuance lock gate digest mismatch",
    )

    require(
        lock.get("approval_issued")
        is True,
        "issuance lock does not record approval",
    )

    require(
        lock.get("approval_consumed")
        is False,
        "issuance lock says approval was consumed",
    )

    require(
        lock.get("reissuance_allowed")
        is False,
        "issuance lock permits reissuance",
    )


def validate_review_pack(
    review: dict[str, Any],
) -> tuple[
    Path,
    Path,
    str,
]:
    verify_digest(
        review,
        digest_field=(
            "wordpress_media_draft_update_"
            "human_review_prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_REVIEW_DIGEST
        ),
        label="human review prep",
    )

    require(
        review.get("status")
        == (
            "PASS_WORDPRESS_MEDIA_DRAFT_"
            "UPDATE_HUMAN_REVIEW_PREP_READY"
        ),
        "human review prep status mismatch",
    )

    require(
        review.get(
            "source_readiness_prep_digest_sha256"
        )
        == EXPECTED_READINESS_DIGEST,
        "review readiness digest mismatch",
    )

    media_request = review.get(
        "media_upload_request_preview"
    )

    require(
        isinstance(media_request, dict),
        "media request preview is missing",
    )

    require(
        media_request.get("api_method")
        == "POST_ONCE",
        "media request method mismatch",
    )

    require(
        media_request.get("resource")
        == "/wp-json/wp/v2/media",
        "media request resource mismatch",
    )

    require(
        media_request.get("filename")
        == EXPECTED_MEDIA_FILENAME,
        "media request filename mismatch",
    )

    require(
        media_request.get(
            "maximum_create_count"
        )
        == 1,
        "media create maximum mismatch",
    )

    media_path = Path(
        media_request["binary_path"]
    ).resolve()

    validate_jpeg_file(
        media_path
    )

    update_request = review.get(
        "draft_content_update_preview"
    )

    require(
        isinstance(update_request, dict),
        "draft update preview is missing",
    )

    require(
        update_request.get("api_method")
        == "POST_ONCE",
        "draft update method mismatch",
    )

    require(
        update_request.get("resource")
        == "/wp-json/wp/v2/posts/195",
        "draft update resource mismatch",
    )

    require(
        update_request.get(
            "post_status_must_remain"
        )
        == "draft",
        "draft status requirement mismatch",
    )

    require(
        update_request.get(
            "original_content_sha256"
        )
        == EXPECTED_ORIGINAL_CONTENT_SHA,
        "original content SHA mismatch",
    )

    require(
        update_request.get(
            "media_source_url_placeholder"
        )
        == MEDIA_URL_PLACEHOLDER,
        "media URL placeholder mismatch",
    )

    require(
        update_request.get(
            "placeholder_count"
        )
        == 1,
        "placeholder count mismatch",
    )

    content_path = Path(
        update_request[
            "content_preview_path"
        ]
    ).resolve()

    require(
        content_path.is_file(),
        "content preview file is missing",
    )

    content_preview_sha = (
        update_request.get(
            "content_preview_sha256"
        )
    )

    require(
        sha256_file(content_path)
        == content_preview_sha,
        "content preview SHA mismatch",
    )

    content_preview = content_path.read_text(
        encoding="utf-8"
    )

    require(
        content_preview.count(
            MEDIA_URL_PLACEHOLDER
        )
        == 1,
        "content preview placeholder count mismatch",
    )

    require(
        REMOTE_COVER_URL
        not in content_preview,
        "remote cover URL remains in preview",
    )

    return (
        media_path,
        content_path,
        content_preview_sha,
    )


def validate_original_live_post(
    post: dict[str, Any],
    *,
    original_content: str,
) -> None:
    validate_created_post(
        post,
        expected_content=original_content,
    )

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


def find_media_duplicates(
    *,
    rest_base: str,
    authorization: str,
) -> dict[str, Any]:
    fields = (
        "id,slug,status,source_url,title,"
        "alt_text,caption,description,"
        "mime_type,media_details,post"
    )

    slug_url = collection_url(
        rest_base,
        "media",
        {
            "context": "edit",
            "status": "inherit",
            "slug": EXPECTED_MEDIA_SLUG,
            "per_page": 100,
            "_fields": fields,
        },
    )

    title_url = collection_url(
        rest_base,
        "media",
        {
            "context": "edit",
            "status": "inherit",
            "search": EXPECTED_MEDIA_TITLE,
            "per_page": 100,
            "_fields": fields,
        },
    )

    slug_result = request_json(
        method="GET",
        url=slug_url,
        authorization=authorization,
    )

    title_result = request_json(
        method="GET",
        url=title_url,
        authorization=authorization,
    )

    require(
        isinstance(slug_result, list),
        "media slug response must be a list",
    )

    require(
        isinstance(title_result, list),
        "media title response must be a list",
    )

    exact: dict[int, dict[str, Any]] = {}

    for item in (
        slug_result
        + title_result
    ):
        if not isinstance(item, dict):
            continue

        item_id = item.get("id")

        if not isinstance(item_id, int):
            continue

        if (
            item.get("slug")
            == EXPECTED_MEDIA_SLUG
            or extract_wp_text(
                item.get("title")
            )
            == EXPECTED_MEDIA_TITLE
        ):
            exact[item_id] = item

    return {
        "slug_query_count": len(
            slug_result
        ),
        "title_query_count": len(
            title_result
        ),
        "exact_match_count": len(exact),
        "matched_media_ids": sorted(
            exact
        ),
        "items": [
            exact[item_id]
            for item_id in sorted(exact)
        ],
        "duplicate_found": bool(exact),
    }


def build_multipart_body(
    *,
    fields: dict[str, str],
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> tuple[
    bytes,
    str,
]:
    boundary = (
        "----ai-media-os-x-r11-"
        + EXPECTED_MEDIA_SHA[:24]
    )

    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                (
                    "--"
                    + boundary
                    + "\r\n"
                ).encode("ascii"),
                (
                    "Content-Disposition: "
                    f'form-data; name="{name}"'
                    "\r\n\r\n"
                ).encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    chunks.extend(
        [
            (
                "--"
                + boundary
                + "\r\n"
            ).encode("ascii"),
            (
                "Content-Disposition: "
                'form-data; name="file"; '
                f'filename="{filename}"'
                "\r\n"
            ).encode("utf-8"),
            (
                "Content-Type: "
                + content_type
                + "\r\n\r\n"
            ).encode("ascii"),
            file_bytes,
            b"\r\n",
            (
                "--"
                + boundary
                + "--\r\n"
            ).encode("ascii"),
        ]
    )

    return (
        b"".join(chunks),
        boundary,
    )


def upload_media_once(
    *,
    rest_base: str,
    authorization: str,
    file_bytes: bytes,
) -> dict[str, Any]:
    fields = {
        "slug": EXPECTED_MEDIA_SLUG,
        "title": EXPECTED_MEDIA_TITLE,
        "alt_text": EXPECTED_MEDIA_TITLE,
        "caption": "",
        "description": (
            EXPECTED_MEDIA_DESCRIPTION
        ),
        "post": str(
            EXPECTED_POST_ID
        ),
    }

    body, boundary = (
        build_multipart_body(
            fields=fields,
            filename=(
                EXPECTED_MEDIA_FILENAME
            ),
            content_type="image/jpeg",
            file_bytes=file_bytes,
        )
    )

    url = (
        rest_base.rstrip("/")
        + "/media"
    )

    request = urllib.request.Request(
        url=url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": authorization,
            "Content-Type": (
                "multipart/form-data; "
                f"boundary={boundary}"
            ),
            "User-Agent": (
                "ai-media-os-x-r11-"
                "media-update-one-shot/1.0"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            response_body = (
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.HTTPError as exc:
        try:
            error_body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            error_body = "<unreadable>"

        raise MediaDraftUpdateExecutionError(
            (
                "media POST HTTP failure "
                f"{exc.code}: "
                f"{error_body[:500]}"
            )
        ) from exc

    except urllib.error.URLError as exc:
        raise MediaDraftUpdateExecutionError(
            f"media POST connection failure: {exc}"
        ) from exc

    try:
        value = json.loads(
            response_body
        )
    except json.JSONDecodeError as exc:
        raise MediaDraftUpdateExecutionError(
            (
                "media POST returned invalid JSON: "
                f"{response_body[:500]}"
            )
        ) from exc

    require(
        isinstance(value, dict),
        "media POST response must be an object",
    )

    return value


def get_media_by_id(
    *,
    rest_base: str,
    authorization: str,
    media_id: int,
) -> dict[str, Any]:
    url = (
        rest_base.rstrip("/")
        + "/media/"
        + str(media_id)
        + "?context=edit"
        + "&_fields=id,slug,status,source_url,"
        + "title,alt_text,caption,description,"
        + "mime_type,media_details,post"
    )

    value = request_json(
        method="GET",
        url=url,
        authorization=authorization,
    )

    require(
        isinstance(value, dict),
        "media GET response must be an object",
    )

    return value


def validate_media_object(
    media: dict[str, Any],
    *,
    wp_hostname: str,
) -> dict[str, Any]:
    media_id = media.get("id")

    require(
        isinstance(media_id, int)
        and media_id > 0,
        "WordPress media ID is invalid",
    )

    require(
        media.get("slug")
        == EXPECTED_MEDIA_SLUG,
        "WordPress media slug mismatch",
    )

    require(
        media.get("mime_type")
        == "image/jpeg",
        "WordPress media MIME type mismatch",
    )

    require(
        extract_wp_text(
            media.get("title")
        )
        == EXPECTED_MEDIA_TITLE,
        "WordPress media title mismatch",
    )

    require(
        media.get("alt_text")
        == EXPECTED_MEDIA_TITLE,
        "WordPress media alt text mismatch",
    )

    require(
        media.get("post")
        == EXPECTED_POST_ID,
        "WordPress media attachment post mismatch",
    )

    source_url = media.get(
        "source_url"
    )

    require(
        isinstance(source_url, str)
        and source_url,
        "WordPress media source URL is missing",
    )

    parsed = urllib.parse.urlparse(
        source_url
    )

    require(
        parsed.scheme == "https",
        "WordPress media URL must use HTTPS",
    )

    require(
        (
            parsed.hostname
            or ""
        ).casefold()
        == wp_hostname.casefold(),
        "WordPress media hostname mismatch",
    )

    basename = urllib.parse.unquote(
        Path(parsed.path).name
    )

    require(
        basename == EXPECTED_MEDIA_FILENAME,
        (
            "WordPress renamed the media file: "
            f"{basename!r}"
        ),
    )

    details = media.get(
        "media_details"
    )

    require(
        isinstance(details, dict),
        "WordPress media details are missing",
    )

    require(
        details.get("width") == 300,
        "WordPress media width mismatch",
    )

    require(
        details.get("height") == 373,
        "WordPress media height mismatch",
    )

    return {
        "media_id": media_id,
        "slug": media["slug"],
        "mime_type": media["mime_type"],
        "title": EXPECTED_MEDIA_TITLE,
        "alt_text": media["alt_text"],
        "attached_post_id": media["post"],
        "source_url": source_url,
        "width": details["width"],
        "height": details["height"],
    }


def verify_media_source_binary(
    *,
    source_url: str,
    authorization: str,
    wp_hostname: str,
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(
        source_url
    )

    require(
        (
            parsed.hostname
            or ""
        ).casefold()
        == wp_hostname.casefold(),
        "media source hostname mismatch",
    )

    request = urllib.request.Request(
        url=source_url,
        method="GET",
        headers={
            "Accept": "image/jpeg",
            "Authorization": authorization,
            "User-Agent": (
                "ai-media-os-x-r11-"
                "media-verification/1.0"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            value = response.read(
                MAX_MEDIA_BYTES + 1
            )

    except Exception as exc:
        raise MediaDraftUpdateExecutionError(
            (
                "uploaded media binary "
                f"verification failed: {exc}"
            )
        ) from exc

    require(
        0 < len(value) <= MAX_MEDIA_BYTES,
        "uploaded media size is invalid",
    )

    require(
        value.startswith(
            b"\xff\xd8\xff"
        ),
        "uploaded media is not a JPEG",
    )

    digest = sha256_bytes(
        value
    )

    require(
        digest == EXPECTED_MEDIA_SHA,
        "uploaded media SHA mismatch",
    )

    return {
        "byte_size": len(value),
        "sha256": digest,
        "jpeg_magic_verified": True,
    }


def reconcile_media_after_attempt(
    *,
    rest_base: str,
    authorization: str,
    wp_hostname: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    last_state: dict[str, Any] = {}

    for attempt in range(
        1,
        RECONCILIATION_ATTEMPTS + 1,
    ):
        state = find_media_duplicates(
            rest_base=rest_base,
            authorization=authorization,
        )

        last_state = state

        if state["exact_match_count"] == 1:
            media_id = state[
                "matched_media_ids"
            ][0]

            live_media = get_media_by_id(
                rest_base=rest_base,
                authorization=authorization,
                media_id=media_id,
            )

            media_result = (
                validate_media_object(
                    live_media,
                    wp_hostname=wp_hostname,
                )
            )

            binary_result = (
                verify_media_source_binary(
                    source_url=media_result[
                        "source_url"
                    ],
                    authorization=authorization,
                    wp_hostname=wp_hostname,
                )
            )

            return (
                media_result,
                binary_result,
            )

        if attempt < RECONCILIATION_ATTEMPTS:
            time.sleep(1)

    raise MediaDraftUpdateExecutionError(
        (
            "media POST outcome could not be "
            f"reconciled: {last_state}"
        )
    )


def get_live_post(
    *,
    rest_base: str,
    authorization: str,
) -> dict[str, Any]:
    url = (
        rest_base.rstrip("/")
        + "/posts/"
        + str(EXPECTED_POST_ID)
        + "?context=edit"
        + "&_fields=id,title,slug,status,"
        + "categories,content,link,date,modified"
    )

    value = request_json(
        method="GET",
        url=url,
        authorization=authorization,
    )

    require(
        isinstance(value, dict),
        "post GET response must be an object",
    )

    return value


def build_updated_content(
    *,
    content_preview: str,
    media_source_url: str,
) -> str:
    require(
        content_preview.count(
            MEDIA_URL_PLACEHOLDER
        )
        == 1,
        "content placeholder count must equal one",
    )

    require(
        media_source_url.startswith(
            "https://"
        ),
        "media source URL must use HTTPS",
    )

    updated = content_preview.replace(
        MEDIA_URL_PLACEHOLDER,
        media_source_url,
        1,
    )

    require(
        MEDIA_URL_PLACEHOLDER
        not in updated,
        "media URL placeholder remains",
    )

    require(
        REMOTE_COVER_URL
        not in updated,
        "remote cover URL remains",
    )

    require(
        updated.count(
            media_source_url
        )
        == 1,
        "uploaded media URL count must equal one",
    )

    return updated


def update_post_once(
    *,
    rest_base: str,
    authorization: str,
    updated_content: str,
) -> dict[str, Any]:
    url = (
        rest_base.rstrip("/")
        + "/posts/"
        + str(EXPECTED_POST_ID)
    )

    value = request_json(
        method="POST",
        url=url,
        authorization=authorization,
        payload={
            "content": updated_content,
            "status": "draft",
        },
    )

    require(
        isinstance(value, dict),
        "post update response must be an object",
    )

    return value


def reconcile_post_after_attempt(
    *,
    rest_base: str,
    authorization: str,
    updated_content: str,
) -> dict[str, Any]:
    last_error = ""

    for attempt in range(
        1,
        RECONCILIATION_ATTEMPTS + 1,
    ):
        live_post = get_live_post(
            rest_base=rest_base,
            authorization=authorization,
        )

        try:
            validate_created_post(
                live_post,
                expected_content=updated_content,
            )

            require(
                live_post.get("id")
                == EXPECTED_POST_ID,
                "reconciled post ID mismatch",
            )

            require(
                live_post.get("status")
                == "draft",
                "reconciled post is not draft",
            )

            return live_post

        except Exception as exc:
            last_error = str(exc)

        if attempt < RECONCILIATION_ATTEMPTS:
            time.sleep(1)

    raise MediaDraftUpdateExecutionError(
        (
            "post update outcome could not be "
            f"reconciled: {last_error}"
        )
    )


def run_one_shot(
    *,
    production_database_path: Path,
    approval_gate_pack_path: Path,
    approval_certificate_path: Path,
    issuance_lock_path: Path,
    review_pack_path: Path,
    credential_env_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    media_result_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "execution_claim_created": False,
        "approval_consumed": False,
        "media_post_attempted": False,
        "media_created_or_reconciled": False,
        "draft_update_attempted": False,
        "draft_updated_or_reconciled": False,
    }

    try:
        production_database_path = (
            production_database_path.resolve()
        )

        require(
            sha256_file(
                production_database_path
            )
            == EXPECTED_DATABASE_SHA,
            "production database changed",
        )

        for path, label in (
            (
                execution_claim_path,
                "execution claim",
            ),
            (
                consumption_lock_path,
                "consumption lock",
            ),
            (
                media_result_path,
                "media result",
            ),
            (
                receipt_path,
                "execution receipt",
            ),
        ):
            require(
                not path.exists(),
                f"{label} already exists",
            )

        gate = load_json(
            approval_gate_pack_path
        )

        verify_digest(
            gate,
            digest_field=(
                "wordpress_media_draft_update_"
                "explicit_approval_gate_digest_sha256"
            ),
            expected_digest=(
                EXPECTED_APPROVAL_GATE_DIGEST
            ),
            label="approval gate",
        )

        certificate_digest = (
            validate_approval_gate(
                gate
            )
        )

        certificate = load_json(
            approval_certificate_path
        )

        validate_certificate(
            certificate,
            expected_digest=(
                certificate_digest
            ),
        )

        issuance_lock = load_json(
            issuance_lock_path
        )

        validate_issuance_lock(
            issuance_lock,
            certificate_digest=(
                certificate_digest
            ),
            approval_gate_digest=(
                EXPECTED_APPROVAL_GATE_DIGEST
            ),
        )

        review = load_json(
            review_pack_path
        )

        (
            media_path,
            content_preview_path,
            content_preview_sha,
        ) = validate_review_pack(
            review
        )

        file_bytes = validate_jpeg_file(
            media_path
        )

        content_preview = (
            content_preview_path.read_text(
                encoding="utf-8"
            )
        )

        require(
            sha256_text(content_preview)
            == content_preview_sha,
            "content preview text SHA mismatch",
        )

        env_values = parse_env_file(
            credential_env_path
        )

        rest_base = build_rest_base(
            env_values
        )

        parsed_rest_base = (
            urllib.parse.urlparse(
                rest_base
            )
        )

        wp_hostname = (
            parsed_rest_base.hostname
            or ""
        )

        require(
            bool(wp_hostname),
            "WordPress hostname is missing",
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

        original_post = get_live_post(
            rest_base=rest_base,
            authorization=authorization,
        )

        original_content_value = (
            original_post.get("content")
        )

        if isinstance(
            original_content_value,
            dict,
        ):
            original_content = (
                original_content_value.get(
                    "raw"
                )
            )
        else:
            original_content = (
                original_content_value
            )

        require(
            isinstance(original_content, str),
            "live original content is missing",
        )

        require(
            sha256_text(original_content)
            == EXPECTED_ORIGINAL_CONTENT_SHA,
            "live original content SHA changed",
        )

        validate_original_live_post(
            original_post,
            original_content=original_content,
        )

        duplicate_state = (
            find_media_duplicates(
                rest_base=rest_base,
                authorization=authorization,
            )
        )

        require(
            duplicate_state[
                "duplicate_found"
            ]
            is False,
            (
                "duplicate media found before "
                f"execution: {duplicate_state}"
            ),
        )

        claimed_at = datetime.now(
            timezone.utc
        ).isoformat()

        claim_payload = {
            "lock_type": (
                "X_R11_WORDPRESS_MEDIA_DRAFT_"
                "UPDATE_EXECUTION_CLAIM"
            ),
            "created_at": claimed_at,
            "approval_request_id": (
                EXPECTED_APPROVAL_REQUEST_ID
            ),
            "approval_gate_digest_sha256": (
                EXPECTED_APPROVAL_GATE_DIGEST
            ),
            "approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "source_review_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "media_sha256": (
                EXPECTED_MEDIA_SHA
            ),
            "target_post_id": (
                EXPECTED_POST_ID
            ),
            "maximum_media_create_count": 1,
            "maximum_draft_update_count": 1,
            "execution_claimed": True,
            "reexecution_allowed": False,
        }

        atomic_create_json(
            execution_claim_path,
            claim_payload,
        )

        state[
            "execution_claim_created"
        ] = True

        consumption_payload = {
            "lock_type": (
                "X_R11_WORDPRESS_MEDIA_DRAFT_"
                "UPDATE_APPROVAL_CONSUMPTION"
            ),
            "created_at": claimed_at,
            "approval_request_id": (
                EXPECTED_APPROVAL_REQUEST_ID
            ),
            "approval_label": (
                EXPECTED_APPROVAL_LABEL
            ),
            "approval_scope": (
                EXPECTED_APPROVAL_SCOPE
            ),
            "approval_gate_digest_sha256": (
                EXPECTED_APPROVAL_GATE_DIGEST
            ),
            "approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "execution_claim_path": str(
                execution_claim_path.resolve()
            ),
            "approval_consumed": True,
            "consumed_for_execution_attempt": True,
            "reexecution_allowed": False,
        }

        atomic_create_json(
            consumption_lock_path,
            consumption_payload,
        )

        state["approval_consumed"] = True
        state["media_post_attempted"] = True

        media_recovered = False

        try:
            uploaded_response = (
                upload_media_once(
                    rest_base=rest_base,
                    authorization=authorization,
                    file_bytes=file_bytes,
                )
            )

            uploaded_media_id = (
                uploaded_response.get("id")
            )

            require(
                isinstance(
                    uploaded_media_id,
                    int,
                )
                and uploaded_media_id > 0,
                "media POST returned no media ID",
            )

            live_media = get_media_by_id(
                rest_base=rest_base,
                authorization=authorization,
                media_id=uploaded_media_id,
            )

            media_result = (
                validate_media_object(
                    live_media,
                    wp_hostname=wp_hostname,
                )
            )

            media_binary_result = (
                verify_media_source_binary(
                    source_url=media_result[
                        "source_url"
                    ],
                    authorization=authorization,
                    wp_hostname=wp_hostname,
                )
            )

        except Exception:
            (
                media_result,
                media_binary_result,
            ) = reconcile_media_after_attempt(
                rest_base=rest_base,
                authorization=authorization,
                wp_hostname=wp_hostname,
            )

            media_recovered = True

        state[
            "media_created_or_reconciled"
        ] = True

        media_receipt_payload = {
            "phase": PHASE,
            "status": (
                "PASS_WORDPRESS_MEDIA_CREATED_"
                "OR_RECONCILED"
            ),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "approval_request_id": (
                EXPECTED_APPROVAL_REQUEST_ID
            ),
            "media": media_result,
            "media_binary_verification": (
                media_binary_result
            ),
            "media_recovered_after_uncertain_post": (
                media_recovered
            ),
            "actual_media_create_count": 1,
            "reexecution_allowed": False,
        }

        media_receipt = {
            **media_receipt_payload,
            "wordpress_media_result_"
            "digest_sha256": (
                canonical_digest(
                    media_receipt_payload
                )
            ),
        }

        atomic_create_json(
            media_result_path,
            media_receipt,
        )

        updated_content = build_updated_content(
            content_preview=content_preview,
            media_source_url=media_result[
                "source_url"
            ],
        )

        updated_content_sha = (
            sha256_text(
                updated_content
            )
        )

        pre_update_post = get_live_post(
            rest_base=rest_base,
            authorization=authorization,
        )

        validate_original_live_post(
            pre_update_post,
            original_content=original_content,
        )

        state[
            "draft_update_attempted"
        ] = True

        update_recovered = False

        try:
            update_post_once(
                rest_base=rest_base,
                authorization=authorization,
                updated_content=updated_content,
            )

            final_post = get_live_post(
                rest_base=rest_base,
                authorization=authorization,
            )

            validate_created_post(
                final_post,
                expected_content=updated_content,
            )

        except Exception:
            final_post = (
                reconcile_post_after_attempt(
                    rest_base=rest_base,
                    authorization=authorization,
                    updated_content=updated_content,
                )
            )

            update_recovered = True

        require(
            final_post.get("id")
            == EXPECTED_POST_ID,
            "final post ID mismatch",
        )

        require(
            final_post.get("status")
            == "draft",
            "final post was not kept as draft",
        )

        require(
            final_post.get("slug")
            == EXPECTED_POST_SLUG,
            "final post slug mismatch",
        )

        require(
            final_post.get("categories")
            == [EXPECTED_CATEGORY_ID],
            "final post category mismatch",
        )

        require(
            extract_wp_text(
                final_post.get("title")
            )
            == EXPECTED_POST_TITLE,
            "final post title mismatch",
        )

        final_content_object = (
            final_post.get("content")
        )

        if isinstance(
            final_content_object,
            dict,
        ):
            final_content = (
                final_content_object.get(
                    "raw"
                )
            )
        else:
            final_content = (
                final_content_object
            )

        require(
            final_content == updated_content,
            "final post content mismatch",
        )

        require(
            sha256_text(final_content)
            == updated_content_sha,
            "final post content SHA mismatch",
        )

        require(
            MEDIA_URL_PLACEHOLDER
            not in final_content,
            "media URL placeholder remains",
        )

        require(
            REMOTE_COVER_URL
            not in final_content,
            "remote cover URL remains",
        )

        require(
            final_content.count(
                media_result["source_url"]
            )
            == 1,
            "WordPress media URL count mismatch",
        )

        state[
            "draft_updated_or_reconciled"
        ] = True

        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        receipt_payload = {
            "phase": PHASE,
            "status": (
                "PASS_WORDPRESS_MEDIA_AND_DRAFT_"
                "UPDATE_ONE_SHOT"
            ),
            "execution_state": (
                "MEDIA_CREATED_DRAFT_UPDATED_"
                "PUBLICATION_STILL_BLOCKED"
            ),
            "completed_at": completed_at,
            "approval_request_id": (
                EXPECTED_APPROVAL_REQUEST_ID
            ),
            "source_approval_gate_path": str(
                approval_gate_pack_path.resolve()
            ),
            "source_approval_gate_digest_sha256": (
                EXPECTED_APPROVAL_GATE_DIGEST
            ),
            "approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "source_review_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "execution_claim_path": str(
                execution_claim_path.resolve()
            ),
            "consumption_lock_path": str(
                consumption_lock_path.resolve()
            ),
            "media_result_path": str(
                media_result_path.resolve()
            ),
            "wordpress_media": media_result,
            "wordpress_media_binary_verification": (
                media_binary_result
            ),
            "wordpress_post": {
                "post_id": EXPECTED_POST_ID,
                "title": EXPECTED_POST_TITLE,
                "slug": EXPECTED_POST_SLUG,
                "status": "draft",
                "category_ids": [
                    EXPECTED_CATEGORY_ID
                ],
                "link": final_post.get("link"),
                "content_sha256": (
                    updated_content_sha
                ),
                "media_source_url": (
                    media_result[
                        "source_url"
                    ]
                ),
                "remote_cover_url_absent": True,
                "media_placeholder_absent": True,
            },
            "media_recovered_after_uncertain_post": (
                media_recovered
            ),
            "draft_update_recovered_after_uncertain_post": (
                update_recovered
            ),
            "approval_consumed": True,
            "reexecution_allowed": False,
            "actual_media_create_count": 1,
            "actual_draft_update_count": 1,
            "wordpress_api_call": True,
            "wordpress_write": True,
            "wordpress_media_write": True,
            "wordpress_post_update": True,
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
                "MEDIA_AND_DRAFT_UPDATE_COMPLETE_"
                "PUBLICATION_AND_X_BLOCKED"
            ),
            "authorized_next_phase": (
                "X-R11-PRODUCTION-CANDIDATE-1-"
                "WORDPRESS-MEDIA-DRAFT-UPDATE-"
                "POST-EXECUTION-VERIFICATION"
            ),
        }

        receipt = {
            **receipt_payload,
            "wordpress_media_draft_update_"
            "one_shot_receipt_digest_sha256": (
                canonical_digest(
                    receipt_payload
                )
            ),
        }

        atomic_write_json(
            receipt_path,
            receipt,
        )

        return receipt

    except Exception as exc:
        failure_payload = {
            "phase": PHASE,
            "status": (
                "FAIL_WORDPRESS_MEDIA_DRAFT_"
                "UPDATE_ONE_SHOT"
            ),
            "failed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "error": str(exc),
            **state,
            "automatic_reexecution_allowed": False,
            "manual_reconciliation_required": bool(
                state[
                    "execution_claim_created"
                ]
            ),
            "wordpress_publication_allowed": False,
            "x_post_execution_allowed": False,
            "database_write": False,
            "workflow_write": False,
            "x_api_call": False,
            "x_post": False,
            "production_status": "NO_GO",
        }

        failure = {
            **failure_payload,
            "wordpress_media_draft_update_"
            "failure_receipt_digest_sha256": (
                canonical_digest(
                    failure_payload
                )
            ),
        }

        if not receipt_path.exists():
            atomic_write_json(
                receipt_path,
                failure,
            )

        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-gate-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-certificate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--issuance-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--review-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--credential-env",
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
        "--media-result",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--receipt",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_one_shot(
            production_database_path=(
                args.production_db
            ),
            approval_gate_pack_path=(
                args.approval_gate_pack
            ),
            approval_certificate_path=(
                args.approval_certificate
            ),
            issuance_lock_path=(
                args.issuance_lock
            ),
            review_pack_path=(
                args.review_pack
            ),
            credential_env_path=(
                args.credential_env
            ),
            execution_claim_path=(
                args.execution_claim
            ),
            consumption_lock_path=(
                args.consumption_lock
            ),
            media_result_path=(
                args.media_result
            ),
            receipt_path=args.receipt,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_MEDIA_DRAFT_"
                        "UPDATE_ONE_SHOT"
                    ),
                    "error": str(exc),
                    "automatic_reexecution_allowed": False,
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
                "execution_state": (
                    result["execution_state"]
                ),
                "approval_request_id": (
                    result["approval_request_id"]
                ),
                "wordpress_media_id": (
                    result[
                        "wordpress_media"
                    ]["media_id"]
                ),
                "wordpress_media_source_url": (
                    result[
                        "wordpress_media"
                    ]["source_url"]
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
                "actual_media_create_count": 1,
                "actual_draft_update_count": 1,
                "approval_consumed": True,
                "reexecution_allowed": False,
                "wordpress_write": True,
                "wordpress_publication_allowed": False,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "receipt_path": str(
                    args.receipt.resolve()
                ),
                "receipt_digest_sha256": (
                    result[
                        "wordpress_media_draft_update_"
                        "one_shot_receipt_digest_sha256"
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
