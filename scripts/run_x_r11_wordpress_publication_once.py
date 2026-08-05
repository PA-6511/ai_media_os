from __future__ import annotations

import argparse
import hashlib
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
    first_env,
    load_json,
    parse_env_file,
    request_json,
    sha256_file,
    verify_digest,
)
from scripts.run_x_r11_wordpress_media_draft_update_once import (
    extract_wp_text,
    find_media_duplicates,
    get_media_by_id,
    validate_media_object,
    verify_media_source_binary,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-PUBLICATION-ONE-SHOT-EXECUTION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_APPROVAL_GATE_DIGEST = (
    "e758fa7f28141c47e2bc518b1987ed58"
    "0baa6a07586626db7e685b67d4ae841a"
)

EXPECTED_REVIEW_DIGEST = (
    "557286fce0da4e6114fa29fdb95a5d9e"
    "26cceaad86bf2258835c33a929b0dbfd"
)

EXPECTED_READINESS_DIGEST = (
    "a12a60b5f1cba0d44600184f8ea6484b"
    "6c75148f7eaaeb626ab451f944c514f4"
)

EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST = (
    "48ca178ad9af187afa505ac4866f7e404"
    "ed04daba15ea1a2ede00c25caed8257"
)

EXPECTED_CONTENT_SHA = (
    "c3205ab12772cd5e8a644a9e84ff39b9"
    "44b8e17d5cd2484316972b8425ae7699"
)

EXPECTED_MEDIA_SHA = (
    "fcd5ed6e8a2136f45a380e055d3a34e7"
    "fe1e0d90cfaed9c8bcc8839c95a890c7"
)

EXPECTED_APPROVAL_REQUEST_ID = (
    "xr11-wp-publish-"
    "48ca178ad9af187afa505ac4"
)

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "PUBLICATION_ONLY"
)

EXPECTED_APPROVAL_SCOPE = (
    "ONE_WORDPRESS_POST_195_"
    "PUBLICATION_STATUS_UPDATE_ONLY"
)

EXPECTED_POST_ID = 195
EXPECTED_MEDIA_ID = 196
EXPECTED_CATEGORY_ID = 43

EXPECTED_POST_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_POST_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_MEDIA_SOURCE_URL = (
    "https://hoshido.jp/wp-content/uploads/"
    "2026/07/"
    "noa-senpai-wa-tomodachi-11-cover.jpg"
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

HTTP_TIMEOUT_SECONDS = 30
RECONCILIATION_ATTEMPTS = 5


class PublicationExecutionError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise PublicationExecutionError(
            message
        )


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
        raise PublicationExecutionError(
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
        "WordPress raw content is missing",
    )

    return raw


def validate_content(
    content: str,
) -> None:
    require(
        sha256_text(content)
        == EXPECTED_CONTENT_SHA,
        "WordPress content SHA mismatch",
    )

    require(
        content.count(
            EXPECTED_MEDIA_SOURCE_URL
        )
        == 1,
        (
            "WordPress media source URL "
            "count must equal one"
        ),
    )

    require(
        CURRENT_PRODUCT_HASH in content,
        "current affiliate product hash is missing",
    )

    require(
        BLOCKED_OLD_PRODUCT_HASH
        not in content,
        "superseded affiliate hash remains",
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

    require(
        REMOTE_COVER_URL
        not in content,
        "remote cover URL remains",
    )

    for marker in (
        "ebook-new-release-article",
        "ebook-pr-disclosure",
        "ebook-cover-image",
        "price-cards",
        "store-buttons",
    ):
        require(
            marker in content,
            f"required article marker is missing: {marker}",
        )

    require(
        EXPECTED_MEDIA_TITLE in content,
        "cover alt text is missing",
    )


def validate_post(
    post: dict[str, Any],
    *,
    expected_status: str,
) -> dict[str, Any]:
    require(
        post.get("id")
        == EXPECTED_POST_ID,
        "WordPress post ID mismatch",
    )

    require(
        post.get("status")
        == expected_status,
        (
            "WordPress post status mismatch: "
            f"expected={expected_status!r}, "
            f"actual={post.get('status')!r}"
        ),
    )

    require(
        post.get("slug")
        == EXPECTED_POST_SLUG,
        "WordPress post slug mismatch",
    )

    require(
        extract_wp_text(
            post.get("title")
        )
        == EXPECTED_POST_TITLE,
        "WordPress post title mismatch",
    )

    require(
        post.get("categories")
        == [EXPECTED_CATEGORY_ID],
        "WordPress post category mismatch",
    )

    content = extract_raw_content(
        post
    )

    validate_content(
        content
    )

    link = post.get("link")

    require(
        isinstance(link, str)
        and link.startswith("https://"),
        "WordPress post link is invalid",
    )

    return {
        "post_id": EXPECTED_POST_ID,
        "title": EXPECTED_POST_TITLE,
        "slug": EXPECTED_POST_SLUG,
        "status": expected_status,
        "category_ids": [
            EXPECTED_CATEGORY_ID
        ],
        "content_sha256": (
            EXPECTED_CONTENT_SHA
        ),
        "link": link,
        "date": post.get("date"),
        "modified": post.get("modified"),
    }


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
        "WordPress post GET returned an invalid object",
    )

    return value


def validate_approval_gate(
    gate: dict[str, Any],
) -> str:
    require(
        gate.get("status")
        == (
            "PASS_WORDPRESS_PUBLICATION_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "publication approval gate status mismatch",
    )

    require(
        gate.get("approval_gate_state")
        == (
            "READY_AWAITING_ONE_SHOT_"
            "WORDPRESS_PUBLICATION_EXECUTION"
        ),
        "publication approval gate state mismatch",
    )

    require(
        gate.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "publication approval request ID mismatch",
    )

    require(
        gate.get("source_review_digest_sha256")
        == EXPECTED_REVIEW_DIGEST,
        "publication gate review digest mismatch",
    )

    require(
        gate.get(
            "publication_approval_issued"
        )
        is True,
        "publication approval was not issued",
    )

    require(
        gate.get(
            "publication_approval_consumed"
        )
        is False,
        "publication approval was already consumed",
    )

    require(
        gate.get("runner_execution_allowed")
        is True,
        "publication runner is not allowed",
    )

    require(
        gate.get(
            "publication_execution_allowed"
        )
        is True,
        "publication execution is not allowed",
    )

    require(
        gate.get(
            "wordpress_publication_allowed"
        )
        is True,
        "WordPress publication is not allowed",
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
        "publication execution limits are missing",
    )

    require(
        limits.get(
            "maximum_publication_update_count"
        )
        == 1,
        "publication maximum update count mismatch",
    )

    require(
        limits.get("target_post_id")
        == EXPECTED_POST_ID,
        "publication target post mismatch",
    )

    require(
        limits.get(
            "required_pre_execution_status"
        )
        == "draft",
        "publication pre-status mismatch",
    )

    require(
        limits.get(
            "required_post_execution_status"
        )
        == "publish",
        "publication post-status mismatch",
    )

    require(
        limits.get("publication_payload")
        == {
            "status": "publish",
        },
        "publication payload mismatch",
    )

    for field in (
        "content_change_allowed",
        "title_change_allowed",
        "slug_change_allowed",
        "category_change_allowed",
        "media_change_allowed",
        "x_post_in_same_execution_allowed",
    ):
        require(
            limits.get(field)
            is False,
            (
                "publication gate permits "
                f"unexpected action: {field}"
            ),
        )

    certificate_digest = gate.get(
        "approval_certificate_digest_sha256"
    )

    require(
        isinstance(certificate_digest, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            certificate_digest,
        )
        is not None,
        "publication certificate digest is invalid",
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
            "wordpress_publication_approval_"
            "certificate_digest_sha256"
        ),
        expected_digest=expected_digest,
        label="publication approval certificate",
    )

    require(
        certificate.get("status")
        == (
            "WORDPRESS_PUBLICATION_APPROVAL_"
            "ISSUED_NOT_CONSUMED"
        ),
        "publication certificate status mismatch",
    )

    require(
        certificate.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "publication certificate request ID mismatch",
    )

    require(
        certificate.get("approval_label")
        == EXPECTED_APPROVAL_LABEL,
        "publication approval label mismatch",
    )

    require(
        certificate.get("approval_scope")
        == EXPECTED_APPROVAL_SCOPE,
        "publication approval scope mismatch",
    )

    require(
        certificate.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "publication certificate review digest mismatch",
    )

    require(
        certificate.get(
            "source_readiness_digest_sha256"
        )
        == EXPECTED_READINESS_DIGEST,
        (
            "publication certificate readiness "
            "digest mismatch"
        ),
    )

    require(
        certificate.get(
            "source_post_execution_"
            "verification_digest_sha256"
        )
        == EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST,
        (
            "publication certificate source "
            "verification digest mismatch"
        ),
    )

    require(
        certificate.get("wordpress_post_id")
        == EXPECTED_POST_ID,
        "publication certificate post ID mismatch",
    )

    require(
        certificate.get(
            "required_content_sha256"
        )
        == EXPECTED_CONTENT_SHA,
        "publication certificate content SHA mismatch",
    )

    require(
        certificate.get("required_media_id")
        == EXPECTED_MEDIA_ID,
        "publication certificate media ID mismatch",
    )

    require(
        certificate.get(
            "required_media_sha256"
        )
        == EXPECTED_MEDIA_SHA,
        "publication certificate media SHA mismatch",
    )

    require(
        certificate.get(
            "maximum_publication_update_count"
        )
        == 1,
        "publication certificate maximum mismatch",
    )

    require(
        certificate.get("publication_payload")
        == {
            "status": "publish",
        },
        "publication certificate payload mismatch",
    )

    require(
        certificate.get(
            "runner_execution_allowed"
        )
        is True,
        "publication certificate blocks runner",
    )

    require(
        certificate.get("approval_consumed")
        is False,
        "publication approval was already consumed",
    )


def validate_issuance_lock(
    lock: dict[str, Any],
    *,
    certificate_digest: str,
) -> None:
    require(
        lock.get("lock_type")
        == (
            "X_R11_WORDPRESS_PUBLICATION_"
            "APPROVAL_ISSUANCE"
        ),
        "publication issuance lock type mismatch",
    )

    require(
        lock.get("approval_request_id")
        == EXPECTED_APPROVAL_REQUEST_ID,
        "publication issuance request ID mismatch",
    )

    require(
        lock.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "publication issuance review digest mismatch",
    )

    require(
        lock.get(
            "approval_certificate_digest_sha256"
        )
        == certificate_digest,
        (
            "publication issuance certificate "
            "digest mismatch"
        ),
    )

    require(
        lock.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "publication issuance gate digest mismatch",
    )

    require(
        lock.get("approval_issued")
        is True,
        "publication issuance lock has no approval",
    )

    require(
        lock.get("approval_consumed")
        is False,
        (
            "publication issuance lock says "
            "approval was consumed"
        ),
    )

    require(
        lock.get("reissuance_allowed")
        is False,
        "publication issuance lock permits reissuance",
    )


def validate_media_preflight(
    *,
    rest_base: str,
    authorization: str,
    wp_hostname: str,
) -> dict[str, Any]:
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
        "publication preflight media ID mismatch",
    )

    require(
        media_result["source_url"]
        == EXPECTED_MEDIA_SOURCE_URL,
        "publication preflight media URL mismatch",
    )

    binary_result = verify_media_source_binary(
        source_url=media_result[
            "source_url"
        ],
        authorization=authorization,
        wp_hostname=wp_hostname,
    )

    require(
        binary_result["sha256"]
        == EXPECTED_MEDIA_SHA,
        "publication preflight media SHA mismatch",
    )

    duplicates = find_media_duplicates(
        rest_base=rest_base,
        authorization=authorization,
    )

    require(
        duplicates.get("exact_match_count")
        == 1,
        "publication preflight media count mismatch",
    )

    require(
        duplicates.get("matched_media_ids")
        == [EXPECTED_MEDIA_ID],
        "publication preflight media ID set mismatch",
    )

    return {
        **media_result,
        "sha256": binary_result["sha256"],
        "byte_size": binary_result["byte_size"],
        "duplicate_count_verified": 1,
    }


def publish_once(
    *,
    rest_base: str,
    authorization: str,
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
            "status": "publish",
        },
    )

    require(
        isinstance(value, dict),
        "publication POST returned an invalid object",
    )

    return value


def reconcile_published_post(
    *,
    rest_base: str,
    authorization: str,
) -> dict[str, Any]:
    last_error = ""

    for attempt in range(
        1,
        RECONCILIATION_ATTEMPTS + 1,
    ):
        post = get_live_post(
            rest_base=rest_base,
            authorization=authorization,
        )

        try:
            validate_post(
                post,
                expected_status="publish",
            )

            return post

        except Exception as exc:
            last_error = str(exc)

        if attempt < RECONCILIATION_ATTEMPTS:
            time.sleep(1)

    raise PublicationExecutionError(
        (
            "publication result could not be "
            f"reconciled: {last_error}"
        )
    )


def validate_public_url(
    value: str,
    *,
    expected_hostname: str,
) -> None:
    parsed = urllib.parse.urlparse(
        value
    )

    require(
        parsed.scheme == "https",
        "public URL must use HTTPS",
    )

    require(
        (
            parsed.hostname or ""
        ).casefold()
        == expected_hostname.casefold(),
        "public URL hostname mismatch",
    )

    require(
        bool(parsed.path)
        or parsed.query == (
            f"p={EXPECTED_POST_ID}"
        ),
        "public URL path is invalid",
    )


def verify_public_page(
    *,
    public_url: str,
    expected_hostname: str,
) -> dict[str, Any]:
    validate_public_url(
        public_url,
        expected_hostname=expected_hostname,
    )

    last_error = ""

    for attempt in range(
        1,
        RECONCILIATION_ATTEMPTS + 1,
    ):
        request = urllib.request.Request(
            url=public_url,
            method="GET",
            headers={
                "Accept": "text/html",
                "User-Agent": (
                    "ai-media-os-x-r11-"
                    "publication-verification/1.0"
                ),
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=HTTP_TIMEOUT_SECONDS,
            ) as response:
                status_code = int(
                    response.status
                )

                final_url = response.geturl()

                body = response.read(
                    4 * 1024 * 1024
                ).decode(
                    "utf-8",
                    errors="replace",
                )

            validate_public_url(
                final_url,
                expected_hostname=expected_hostname,
            )

            require(
                status_code == 200,
                (
                    "public page status code "
                    f"is {status_code}"
                ),
            )

            require(
                EXPECTED_POST_TITLE in body,
                "public page title is missing",
            )

            require(
                "ebook-new-release-article"
                in body,
                "public article marker is missing",
            )

            require(
                "ebook-pr-disclosure"
                in body,
                "public PR marker is missing",
            )

            require(
                EXPECTED_MEDIA_SOURCE_URL
                in body,
                "public media URL is missing",
            )

            require(
                CURRENT_PRODUCT_HASH in body,
                "public affiliate hash is missing",
            )

            require(
                BLOCKED_OLD_PRODUCT_HASH
                not in body,
                "old affiliate hash appears publicly",
            )

            return {
                "requested_url": public_url,
                "resolved_url": final_url,
                "http_status": status_code,
                "title_verified": True,
                "article_marker_verified": True,
                "pr_disclosure_verified": True,
                "media_url_verified": True,
                "affiliate_hash_verified": True,
            }

        except Exception as exc:
            last_error = str(exc)

        if attempt < RECONCILIATION_ATTEMPTS:
            time.sleep(2)

    raise PublicationExecutionError(
        (
            "public page could not be verified: "
            f"{last_error}"
        )
    )


def run_one_shot(
    *,
    production_database_path: Path,
    approval_gate_pack_path: Path,
    approval_certificate_path: Path,
    issuance_lock_path: Path,
    credential_env_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "execution_claim_created": False,
        "approval_consumed": False,
        "publication_post_attempted": False,
        "publication_reconciled": False,
        "public_page_verified": False,
    }

    try:
        production_database_path = (
            production_database_path.resolve()
        )

        approval_gate_pack_path = (
            approval_gate_pack_path.resolve()
        )

        approval_certificate_path = (
            approval_certificate_path.resolve()
        )

        issuance_lock_path = (
            issuance_lock_path.resolve()
        )

        credential_env_path = (
            credential_env_path.resolve()
        )

        execution_claim_path = (
            execution_claim_path.resolve()
        )

        consumption_lock_path = (
            consumption_lock_path.resolve()
        )

        receipt_path = receipt_path.resolve()

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
                receipt_path,
                "publication receipt",
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
                "wordpress_publication_explicit_"
                "approval_gate_digest_sha256"
            ),
            expected_digest=(
                EXPECTED_APPROVAL_GATE_DIGEST
            ),
            label="publication approval gate",
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
            parsed_rest_base.hostname or ""
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

        media_preflight = (
            validate_media_preflight(
                rest_base=rest_base,
                authorization=authorization,
                wp_hostname=wp_hostname,
            )
        )

        pre_execution_post = get_live_post(
            rest_base=rest_base,
            authorization=authorization,
        )

        pre_execution_result = validate_post(
            pre_execution_post,
            expected_status="draft",
        )

        claimed_at = datetime.now(
            timezone.utc
        ).isoformat()

        claim_payload = {
            "lock_type": (
                "X_R11_WORDPRESS_PUBLICATION_"
                "EXECUTION_CLAIM"
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
            "target_post_id": (
                EXPECTED_POST_ID
            ),
            "required_pre_execution_status": (
                "draft"
            ),
            "required_post_execution_status": (
                "publish"
            ),
            "required_content_sha256": (
                EXPECTED_CONTENT_SHA
            ),
            "required_media_id": (
                EXPECTED_MEDIA_ID
            ),
            "maximum_publication_update_count": 1,
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
                "X_R11_WORDPRESS_PUBLICATION_"
                "APPROVAL_CONSUMPTION"
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
                execution_claim_path
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
        state[
            "publication_post_attempted"
        ] = True

        publication_recovered = False

        try:
            response = publish_once(
                rest_base=rest_base,
                authorization=authorization,
            )

            validate_post(
                response,
                expected_status="publish",
            )

            final_post = get_live_post(
                rest_base=rest_base,
                authorization=authorization,
            )

            final_result = validate_post(
                final_post,
                expected_status="publish",
            )

        except Exception:
            final_post = reconcile_published_post(
                rest_base=rest_base,
                authorization=authorization,
            )

            final_result = validate_post(
                final_post,
                expected_status="publish",
            )

            publication_recovered = True

        state["publication_reconciled"] = True

        require(
            final_result["title"]
            == pre_execution_result["title"],
            "title changed during publication",
        )

        require(
            final_result["slug"]
            == pre_execution_result["slug"],
            "slug changed during publication",
        )

        require(
            final_result["category_ids"]
            == pre_execution_result[
                "category_ids"
            ],
            "category changed during publication",
        )

        require(
            final_result["content_sha256"]
            == pre_execution_result[
                "content_sha256"
            ],
            "content changed during publication",
        )

        public_url = final_result["link"]

        public_page = verify_public_page(
            public_url=public_url,
            expected_hostname=wp_hostname,
        )

        state["public_page_verified"] = True

        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        receipt_payload = {
            "phase": PHASE,
            "status": (
                "PASS_WORDPRESS_PUBLICATION_ONE_SHOT"
            ),
            "execution_state": (
                "WORDPRESS_POST_195_PUBLISHED_"
                "PUBLIC_URL_VERIFIED_X_STILL_BLOCKED"
            ),
            "completed_at": completed_at,
            "approval_request_id": (
                EXPECTED_APPROVAL_REQUEST_ID
            ),
            "source_approval_gate_path": str(
                approval_gate_pack_path
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
                execution_claim_path
            ),
            "consumption_lock_path": str(
                consumption_lock_path
            ),
            "wordpress_media": (
                media_preflight
            ),
            "wordpress_post_before": (
                pre_execution_result
            ),
            "wordpress_post_after": (
                final_result
            ),
            "public_page_verification": (
                public_page
            ),
            "publication_recovered_after_uncertain_post": (
                publication_recovered
            ),
            "approval_consumed": True,
            "reexecution_allowed": False,
            "actual_publication_update_count": 1,
            "wordpress_api_call": True,
            "wordpress_api_method": (
                "POST_ONCE_THEN_GET_VERIFY"
            ),
            "wordpress_write": True,
            "wordpress_post_update": True,
            "wordpress_publication_executed": True,
            "wordpress_post_status": "publish",
            "public_url_available": True,
            "public_url": public_url,
            "x_public_url_replacement_allowed": True,
            "x_final_review_allowed": False,
            "x_post_execution_allowed": False,
            "database_write": False,
            "workflow_write": False,
            "x_api_call": False,
            "x_post": False,
            "production_status": "NO_GO",
            "safety_state": (
                "WORDPRESS_PUBLICATION_COMPLETE_"
                "PUBLIC_URL_VERIFIED_X_POST_BLOCKED"
            ),
            "authorized_next_phase": (
                "X-R11-PRODUCTION-CANDIDATE-1-"
                "WORDPRESS-PUBLICATION-"
                "POST-EXECUTION-VERIFICATION"
            ),
        }

        receipt = {
            **receipt_payload,
            "wordpress_publication_one_shot_"
            "receipt_digest_sha256": (
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
                "FAIL_WORDPRESS_PUBLICATION_ONE_SHOT"
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
            "x_post_execution_allowed": False,
            "database_write": False,
            "workflow_write": False,
            "x_api_call": False,
            "x_post": False,
            "production_status": "NO_GO",
        }

        failure = {
            **failure_payload,
            "wordpress_publication_failure_"
            "receipt_digest_sha256": (
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
            credential_env_path=(
                args.credential_env
            ),
            execution_claim_path=(
                args.execution_claim
            ),
            consumption_lock_path=(
                args.consumption_lock
            ),
            receipt_path=args.receipt,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_PUBLICATION_ONE_SHOT"
                    ),
                    "error": str(exc),
                    "automatic_reexecution_allowed": False,
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
        "wordpress_post_after"
    ]

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
                "wordpress_post_id": (
                    post["post_id"]
                ),
                "wordpress_post_status": (
                    post["status"]
                ),
                "public_url_available": True,
                "public_url": (
                    result["public_url"]
                ),
                "actual_publication_update_count": 1,
                "approval_consumed": True,
                "reexecution_allowed": False,
                "wordpress_write": True,
                "wordpress_publication_executed": True,
                "x_public_url_replacement_allowed": True,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "receipt_path": str(
                    args.receipt.resolve()
                ),
                "receipt_digest_sha256": (
                    result[
                        "wordpress_publication_"
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
