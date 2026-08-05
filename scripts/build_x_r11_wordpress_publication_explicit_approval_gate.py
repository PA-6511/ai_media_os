from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-PUBLICATION-"
    "EXPLICIT-APPROVAL-GATE"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
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

EXPECTED_PUBLICATION_REQUEST_ID = (
    "xr11-wp-publish-"
    "48ca178ad9af187afa505ac4"
)

EXPECTED_POST_ID = 195
EXPECTED_MEDIA_ID = 196
EXPECTED_CATEGORY_ID = 43
EXPECTED_CHECK_COUNT = 12

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

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "PUBLICATION_ONLY"
)

APPROVAL_SCOPE = (
    "ONE_WORDPRESS_POST_195_"
    "PUBLICATION_STATUS_UPDATE_ONLY"
)


class PublicationApprovalGateError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise PublicationApprovalGateError(
            message
        )


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
        raise PublicationApprovalGateError(
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


def verify_digest(
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
        isinstance(recorded, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            recorded,
        )
        is not None,
        f"{label} digest is invalid",
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
        (
            f"{label} canonical digest "
            "verification failed"
        ),
    )


def validate_approval_label(
    value: str,
) -> None:
    require(
        value == APPROVAL_LABEL,
        (
            "approval label must exactly equal "
            f"{APPROVAL_LABEL}"
        ),
    )


def validate_pending_checklist(
    checklist: Any,
) -> None:
    require(
        isinstance(checklist, list),
        "human review checklist is missing",
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
                "remain pending before approval"
            ),
        )

        check_ids.append(check_id)

    require(
        len(set(check_ids))
        == EXPECTED_CHECK_COUNT,
        "human review check IDs are not unique",
    )


def validate_publication_preview(
    value: Any,
) -> None:
    require(
        isinstance(value, dict),
        "publication request preview is missing",
    )

    require(
        value.get("request_id")
        == EXPECTED_PUBLICATION_REQUEST_ID,
        "publication request ID mismatch",
    )

    require(
        value.get("api_method")
        == "POST_ONCE",
        "publication API method mismatch",
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
            "publication maximum update count "
            "must equal one"
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
            "source review must not already "
            "permit execution"
        ),
    )


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
        raise PublicationApprovalGateError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(
            descriptor,
            data,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_explicit_approval_gate(
    *,
    production_database_path: Path,
    review_pack_path: Path,
    approval_label: str,
    approval_certificate_path: Path,
    approval_gate_pack_path: Path,
    issuance_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    review_pack_path = (
        review_pack_path.resolve()
    )

    approval_certificate_path = (
        approval_certificate_path.resolve()
    )

    approval_gate_pack_path = (
        approval_gate_pack_path.resolve()
    )

    issuance_lock_path = (
        issuance_lock_path.resolve()
    )

    validate_approval_label(
        approval_label
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
            approval_certificate_path,
            "approval certificate",
        ),
        (
            approval_gate_pack_path,
            "approval gate pack",
        ),
        (
            issuance_lock_path,
            "approval issuance lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    review = load_json(
        review_pack_path
    )

    verify_digest(
        review,
        digest_field=(
            "wordpress_publication_human_review_"
            "prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_REVIEW_DIGEST
        ),
        label="publication human review prep",
    )

    require(
        review.get("status")
        == (
            "PASS_WORDPRESS_PUBLICATION_"
            "HUMAN_REVIEW_PREP_READY"
        ),
        "publication human review prep did not pass",
    )

    require(
        review.get("human_review_state")
        == (
            "AWAITING_EXPLICIT_HUMAN_"
            "PUBLICATION_DECISION"
        ),
        "publication human review state mismatch",
    )

    require(
        review.get(
            "source_readiness_prep_digest_sha256"
        )
        == EXPECTED_READINESS_DIGEST,
        "source readiness digest mismatch",
    )

    require(
        review.get(
            "source_post_execution_"
            "verification_digest_sha256"
        )
        == EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST,
        (
            "source post-execution verification "
            "digest mismatch"
        ),
    )

    require(
        review.get(
            "approval_label_if_approved"
        )
        == APPROVAL_LABEL,
        "review approval label mismatch",
    )

    require(
        review.get(
            "approval_scope_if_approved"
        )
        == APPROVAL_SCOPE,
        "review approval scope mismatch",
    )

    require(
        review.get("human_decision")
        == "PENDING",
        "human decision is not pending",
    )

    require(
        review.get(
            "human_review_completed"
        )
        is False,
        "human review is already complete",
    )

    require(
        review.get(
            "publication_approval_issued"
        )
        is False,
        "publication approval was already issued",
    )

    require(
        review.get(
            "publication_approval_consumed"
        )
        is False,
        "publication approval was already consumed",
    )

    require(
        review.get(
            "publication_execution_allowed"
        )
        is False,
        "publication execution is already allowed",
    )

    require(
        review.get(
            "wordpress_publication_allowed"
        )
        is False,
        "WordPress publication is already allowed",
    )

    require(
        review.get(
            "public_url_available"
        )
        is False,
        "public URL is unexpectedly available",
    )

    require(
        review.get(
            "x_post_execution_allowed"
        )
        is False,
        "X post execution is unexpectedly allowed",
    )

    require(
        review.get(
            "wordpress_api_method"
        )
        == "GET_ONLY",
        "source review API method mismatch",
    )

    require(
        review.get("wordpress_write")
        is False,
        "source review recorded a WordPress write",
    )

    machine_precheck = review.get(
        "machine_precheck"
    )

    require(
        isinstance(machine_precheck, dict),
        "machine precheck is missing",
    )

    require(
        machine_precheck.get("passed")
        is True,
        "machine precheck did not pass",
    )

    require(
        machine_precheck.get("check_count")
        == EXPECTED_CHECK_COUNT,
        "machine precheck count mismatch",
    )

    for field in (
        "post_status_is_draft",
        "content_sha256_verified",
        "media_sha256_verified",
        "pr_disclosure_verified",
        "affiliate_url_verified",
        "publication_request_is_status_only",
        "x_execution_blocked",
    ):
        require(
            machine_precheck.get(field)
            is True,
            (
                "machine precheck failed: "
                f"{field}"
            ),
        )

    require(
        machine_precheck.get(
            "media_duplicate_count_verified"
        )
        == 1,
        (
            "machine precheck media duplicate "
            "count mismatch"
        ),
    )

    checklist = review.get(
        "human_review_checklist"
    )

    validate_pending_checklist(
        checklist
    )

    publication_preview = review.get(
        "publication_request_preview"
    )

    validate_publication_preview(
        publication_preview
    )

    post = review.get(
        "wordpress_post"
    )

    require(
        isinstance(post, dict),
        "WordPress post evidence is missing",
    )

    require(
        post.get("post_id")
        == EXPECTED_POST_ID,
        "WordPress post ID mismatch",
    )

    require(
        post.get("title")
        == EXPECTED_POST_TITLE,
        "WordPress post title mismatch",
    )

    require(
        post.get("slug")
        == EXPECTED_POST_SLUG,
        "WordPress post slug mismatch",
    )

    require(
        post.get("status")
        == "draft",
        "WordPress post must remain draft",
    )

    require(
        post.get("category_ids")
        == [EXPECTED_CATEGORY_ID],
        "WordPress category mismatch",
    )

    require(
        post.get("content_sha256")
        == EXPECTED_CONTENT_SHA,
        "WordPress content SHA mismatch",
    )

    content_preview_path = Path(
        post["content_preview_path"]
    ).resolve()

    require(
        content_preview_path.is_file(),
        "publication content preview is missing",
    )

    require(
        sha256_file(
            content_preview_path
        )
        == EXPECTED_CONTENT_SHA,
        "publication content preview SHA mismatch",
    )

    media = review.get(
        "wordpress_media"
    )

    require(
        isinstance(media, dict),
        "WordPress media evidence is missing",
    )

    require(
        media.get("media_id")
        == EXPECTED_MEDIA_ID,
        "WordPress media ID mismatch",
    )

    require(
        media.get("source_url")
        == EXPECTED_MEDIA_SOURCE_URL,
        "WordPress media source URL mismatch",
    )

    require(
        media.get("sha256")
        == EXPECTED_MEDIA_SHA,
        "WordPress media SHA mismatch",
    )

    require(
        media.get(
            "duplicate_count_verified"
        )
        == 1,
        "WordPress media duplicate count mismatch",
    )

    approved_at = datetime.now(
        timezone.utc
    ).isoformat()

    approved_checklist = [
        {
            **item,
            "human_decision": "APPROVED",
        }
        for item in checklist
    ]

    certificate_payload = {
        "phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-PUBLICATION-"
            "EXPLICIT-APPROVAL"
        ),
        "status": (
            "WORDPRESS_PUBLICATION_APPROVAL_"
            "ISSUED_NOT_CONSUMED"
        ),
        "issued_at": approved_at,
        "approval_request_id": (
            EXPECTED_PUBLICATION_REQUEST_ID
        ),
        "approval_label": approval_label,
        "approval_scope": APPROVAL_SCOPE,
        "source_review_pack_path": str(
            review_pack_path
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "source_readiness_digest_sha256": (
            EXPECTED_READINESS_DIGEST
        ),
        "source_post_execution_verification_digest_sha256": (
            EXPECTED_POST_EXECUTION_VERIFICATION_DIGEST
        ),
        "wordpress_post_id": (
            EXPECTED_POST_ID
        ),
        "required_pre_execution_status": (
            "draft"
        ),
        "required_post_execution_status": (
            "publish"
        ),
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
            EXPECTED_CONTENT_SHA
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
        "maximum_publication_update_count": 1,
        "publication_payload": {
            "status": "publish",
        },
        "content_change_allowed": False,
        "title_change_allowed": False,
        "slug_change_allowed": False,
        "category_change_allowed": False,
        "media_change_allowed": False,
        "human_decision": "APPROVED",
        "human_review_completed": True,
        "approved_check_count": (
            EXPECTED_CHECK_COUNT
        ),
        "human_review_checklist": (
            approved_checklist
        ),
        "runner_execution_allowed": True,
        "approval_consumed": False,
        "publication_executed": False,
        "x_post_execution_allowed": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PUBLICATION_APPROVED_"
            "RUNNER_NOT_EXECUTED"
        ),
    }

    certificate = {
        **certificate_payload,
        "wordpress_publication_approval_"
        "certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    gate_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_PUBLICATION_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "approval_gate_state": (
            "READY_AWAITING_ONE_SHOT_"
            "WORDPRESS_PUBLICATION_EXECUTION"
        ),
        "generated_at": approved_at,
        "approval_request_id": (
            EXPECTED_PUBLICATION_REQUEST_ID
        ),
        "source_review_pack_path": str(
            review_pack_path
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "wordpress_publication_approval_"
                "certificate_digest_sha256"
            ]
        ),
        "human_decision": "APPROVED",
        "human_review_completed": True,
        "publication_approval_issued": True,
        "publication_approval_consumed": False,
        "runner_execution_allowed": True,
        "wordpress_post": {
            "post_id": EXPECTED_POST_ID,
            "title": EXPECTED_POST_TITLE,
            "slug": EXPECTED_POST_SLUG,
            "status": "draft",
            "category_ids": [
                EXPECTED_CATEGORY_ID
            ],
            "content_sha256": (
                EXPECTED_CONTENT_SHA
            ),
        },
        "wordpress_media": {
            "media_id": EXPECTED_MEDIA_ID,
            "source_url": (
                EXPECTED_MEDIA_SOURCE_URL
            ),
            "sha256": (
                EXPECTED_MEDIA_SHA
            ),
        },
        "execution_limits": {
            "maximum_publication_update_count": 1,
            "target_post_id": EXPECTED_POST_ID,
            "required_pre_execution_status": (
                "draft"
            ),
            "required_post_execution_status": (
                "publish"
            ),
            "publication_payload": {
                "status": "publish",
            },
            "content_change_allowed": False,
            "title_change_allowed": False,
            "slug_change_allowed": False,
            "category_change_allowed": False,
            "media_change_allowed": False,
            "x_post_in_same_execution_allowed": (
                False
            ),
        },
        "publication_execution_allowed": True,
        "wordpress_publication_allowed": True,
        "wordpress_post_update_allowed": True,
        "public_url_available": False,
        "x_public_url_replacement_allowed": False,
        "x_final_review_allowed": False,
        "x_post_execution_allowed": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_post_update": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_WORDPRESS_PUBLICATION_"
            "APPROVED_NOT_EXECUTED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-PUBLICATION-"
            "ONE-SHOT-EXECUTION"
        ),
    }

    gate = {
        **gate_payload,
        "wordpress_publication_explicit_"
        "approval_gate_digest_sha256": (
            canonical_digest(
                gate_payload
            )
        ),
    }

    issuance_lock_payload = {
        "lock_type": (
            "X_R11_WORDPRESS_PUBLICATION_"
            "APPROVAL_ISSUANCE"
        ),
        "created_at": approved_at,
        "approval_request_id": (
            EXPECTED_PUBLICATION_REQUEST_ID
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_label": approval_label,
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "wordpress_publication_approval_"
                "certificate_digest_sha256"
            ]
        ),
        "approval_gate_pack_path": str(
            approval_gate_pack_path
        ),
        "approval_gate_digest_sha256": (
            gate[
                "wordpress_publication_explicit_"
                "approval_gate_digest_sha256"
            ]
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "reissuance_allowed": False,
    }

    atomic_create_json(
        approval_certificate_path,
        certificate,
    )

    atomic_create_json(
        approval_gate_pack_path,
        gate,
    )

    atomic_create_json(
        issuance_lock_path,
        issuance_lock_payload,
    )

    return gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--review-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-label",
        required=True,
    )

    parser.add_argument(
        "--approval-certificate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-gate-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--issuance-lock",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = build_explicit_approval_gate(
            production_database_path=(
                args.production_db
            ),
            review_pack_path=(
                args.review_pack
            ),
            approval_label=(
                args.approval_label
            ),
            approval_certificate_path=(
                args.approval_certificate
            ),
            approval_gate_pack_path=(
                args.approval_gate_pack
            ),
            issuance_lock_path=(
                args.issuance_lock
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_PUBLICATION_"
                        "EXPLICIT_APPROVAL_GATE"
                    ),
                    "error": str(exc),
                    "publication_approval_issued": False,
                    "publication_approval_consumed": False,
                    "wordpress_api_call": False,
                    "wordpress_write": False,
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
                "approval_gate_state": (
                    result["approval_gate_state"]
                ),
                "approval_request_id": (
                    result["approval_request_id"]
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
                "human_decision": "APPROVED",
                "publication_approval_issued": True,
                "publication_approval_consumed": False,
                "runner_execution_allowed": True,
                "publication_execution_allowed": True,
                "wordpress_publication_allowed": True,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "public_url_available": False,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "approval_gate_pack_path": str(
                    args.approval_gate_pack.resolve()
                ),
                "approval_gate_digest_sha256": (
                    result[
                        "wordpress_publication_"
                        "explicit_approval_gate_"
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
