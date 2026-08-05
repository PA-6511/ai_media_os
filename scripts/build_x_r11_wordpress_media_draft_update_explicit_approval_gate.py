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
    "WORDPRESS-MEDIA-DRAFT-UPDATE-"
    "EXPLICIT-APPROVAL-GATE"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
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

EXPECTED_POST_ID = 195
EXPECTED_CHECK_COUNT = 10

EXPECTED_MEDIA_FILENAME = (
    "noa-senpai-wa-tomodachi-"
    "11-cover.jpg"
)

MEDIA_URL_PLACEHOLDER = (
    "{{WORDPRESS_MEDIA_SOURCE_URL}}"
)

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "MEDIA_AND_DRAFT_UPDATE_ONLY"
)

APPROVAL_SCOPE = (
    "ONE_WORDPRESS_MEDIA_UPLOAD_AND_"
    "ONE_DRAFT_CONTENT_UPDATE_ONLY"
)


class MediaDraftUpdateApprovalError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise MediaDraftUpdateApprovalError(
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
        raise MediaDraftUpdateApprovalError(
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


def validate_media_request(
    value: Any,
) -> None:
    require(
        isinstance(value, dict),
        "media upload request preview is missing",
    )

    require(
        value.get("api_method")
        == "POST_ONCE",
        "media upload method mismatch",
    )

    require(
        value.get("resource")
        == "/wp-json/wp/v2/media",
        "media upload resource mismatch",
    )

    require(
        value.get("filename")
        == EXPECTED_MEDIA_FILENAME,
        "media filename mismatch",
    )

    require(
        value.get("content_type")
        == "image/jpeg",
        "media content type mismatch",
    )

    require(
        value.get("maximum_create_count")
        == 1,
        "media maximum create count must equal one",
    )

    require(
        value.get("execution_allowed")
        is False,
        (
            "source review must not already "
            "allow media execution"
        ),
    )

    binary_path = Path(
        value["binary_path"]
    ).resolve()

    require(
        binary_path.is_file(),
        "media binary file is missing",
    )

    require(
        sha256_file(binary_path)
        == EXPECTED_MEDIA_SHA,
        "media binary SHA mismatch",
    )


def validate_draft_update_request(
    value: Any,
) -> None:
    require(
        isinstance(value, dict),
        "draft update request preview is missing",
    )

    require(
        value.get("api_method")
        == "POST_ONCE",
        "draft update method mismatch",
    )

    require(
        value.get("resource")
        == "/wp-json/wp/v2/posts/195",
        "draft update resource mismatch",
    )

    require(
        value.get("post_status_must_remain")
        == "draft",
        "draft status lock mismatch",
    )

    require(
        value.get("original_content_sha256")
        == EXPECTED_ORIGINAL_CONTENT_SHA,
        "original content SHA mismatch",
    )

    require(
        value.get(
            "media_source_url_placeholder"
        )
        == MEDIA_URL_PLACEHOLDER,
        "media URL placeholder mismatch",
    )

    require(
        value.get("placeholder_count")
        == 1,
        "media URL placeholder count mismatch",
    )

    require(
        value.get("remote_source_url_removed")
        is True,
        "remote cover URL was not removed",
    )

    require(
        value.get("execution_allowed")
        is False,
        (
            "source review must not already "
            "allow draft update execution"
        ),
    )

    preview_path = Path(
        value["content_preview_path"]
    ).resolve()

    require(
        preview_path.is_file(),
        "draft content preview is missing",
    )

    require(
        sha256_file(preview_path)
        == value.get(
            "content_preview_sha256"
        ),
        "draft content preview SHA mismatch",
    )

    preview_text = preview_path.read_text(
        encoding="utf-8"
    )

    require(
        preview_text.count(
            MEDIA_URL_PLACEHOLDER
        )
        == 1,
        (
            "draft content preview must contain "
            "one media URL placeholder"
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
        raise MediaDraftUpdateApprovalError(
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
            "wordpress_media_draft_update_"
            "human_review_prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_REVIEW_DIGEST
        ),
        label=(
            "media and draft update "
            "human review prep"
        ),
    )

    require(
        review.get("status")
        == (
            "PASS_WORDPRESS_MEDIA_DRAFT_"
            "UPDATE_HUMAN_REVIEW_PREP_READY"
        ),
        "human review prep did not pass",
    )

    require(
        review.get("human_review_state")
        == (
            "AWAITING_EXPLICIT_HUMAN_MEDIA_"
            "AND_DRAFT_UPDATE_DECISION"
        ),
        "human review state mismatch",
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
        review.get("human_review_completed")
        is False,
        "human review is already complete",
    )

    require(
        review.get("approval_issued")
        is False,
        "approval was already issued",
    )

    require(
        review.get("approval_consumed")
        is False,
        "approval was already consumed",
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
        machine_precheck.get(
            "media_binary_verified"
        )
        is True,
        "media binary verification failed",
    )

    require(
        machine_precheck.get(
            "content_preview_verified"
        )
        is True,
        "content preview verification failed",
    )

    require(
        machine_precheck.get(
            "post_status_locked_to_draft"
        )
        is True,
        "post status is not locked to draft",
    )

    require(
        machine_precheck.get(
            "publication_blocked"
        )
        is True,
        "publication is not blocked",
    )

    checklist = review.get(
        "human_review_checklist"
    )

    validate_pending_checklist(
        checklist
    )

    wordpress_post = review.get(
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
        wordpress_post.get(
            "public_url_available"
        )
        is False,
        "public URL must remain unavailable",
    )

    cover_media = review.get(
        "cover_media"
    )

    require(
        isinstance(cover_media, dict),
        "cover media evidence is missing",
    )

    require(
        cover_media.get("sha256")
        == EXPECTED_MEDIA_SHA,
        "cover media SHA mismatch",
    )

    require(
        cover_media.get("filename")
        == EXPECTED_MEDIA_FILENAME,
        "cover media filename mismatch",
    )

    require(
        cover_media.get("mime_type")
        == "image/jpeg",
        "cover media MIME type mismatch",
    )

    require(
        cover_media.get("width")
        == 300,
        "cover media width mismatch",
    )

    require(
        cover_media.get("height")
        == 373,
        "cover media height mismatch",
    )

    validate_media_request(
        review.get(
            "media_upload_request_preview"
        )
    )

    validate_draft_update_request(
        review.get(
            "draft_content_update_preview"
        )
    )

    for field in (
        "media_upload_allowed",
        "draft_content_update_allowed",
        "wordpress_publication_allowed",
        "public_url_available",
        "x_public_url_replacement_allowed",
        "x_post_execution_allowed",
        "wordpress_api_call",
        "wordpress_write",
        "wordpress_media_write",
        "wordpress_post_update",
        "database_write",
        "workflow_write",
        "x_api_call",
        "x_post",
    ):
        require(
            review.get(field) is False,
            (
                "unexpected allowed/write state: "
                f"{field}"
            ),
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

    request_id = (
        "xr11-wp-media-draft-update-"
        + EXPECTED_REVIEW_DIGEST[:24]
    )

    certificate_payload = {
        "phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-MEDIA-DRAFT-UPDATE-"
            "EXPLICIT-APPROVAL"
        ),
        "status": (
            "WORDPRESS_MEDIA_DRAFT_UPDATE_"
            "APPROVAL_ISSUED_NOT_CONSUMED"
        ),
        "issued_at": approved_at,
        "approval_request_id": request_id,
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
        "wordpress_post_id": (
            EXPECTED_POST_ID
        ),
        "wordpress_post_status_required": (
            "draft"
        ),
        "media_sha256": (
            EXPECTED_MEDIA_SHA
        ),
        "media_filename": (
            EXPECTED_MEDIA_FILENAME
        ),
        "maximum_media_create_count": 1,
        "maximum_draft_update_count": 1,
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
        "media_upload_executed": False,
        "draft_content_update_executed": False,
        "wordpress_publication_allowed": False,
        "public_url_available": False,
        "x_public_url_replacement_allowed": False,
        "x_post_execution_allowed": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_update": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "MEDIA_AND_DRAFT_UPDATE_APPROVED_"
            "RUNNER_NOT_EXECUTED"
        ),
    }

    certificate = {
        **certificate_payload,
        "wordpress_media_draft_update_"
        "approval_certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    gate_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_MEDIA_DRAFT_UPDATE_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "approval_gate_state": (
            "READY_AWAITING_ONE_SHOT_MEDIA_"
            "UPLOAD_AND_DRAFT_UPDATE_EXECUTION"
        ),
        "generated_at": approved_at,
        "approval_request_id": request_id,
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
                "wordpress_media_draft_update_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "human_decision": "APPROVED",
        "human_review_completed": True,
        "approval_issued": True,
        "approval_consumed": False,
        "runner_execution_allowed": True,
        "wordpress_post": {
            "post_id": EXPECTED_POST_ID,
            "status": "draft",
            "public_url_available": False,
        },
        "execution_limits": {
            "maximum_media_create_count": 1,
            "maximum_draft_update_count": 1,
            "target_post_id": EXPECTED_POST_ID,
            "required_final_post_status": "draft",
            "publication_in_same_execution_allowed": (
                False
            ),
            "x_post_in_same_execution_allowed": (
                False
            ),
        },
        "media_upload_allowed": True,
        "draft_content_update_allowed": True,
        "wordpress_publication_allowed": False,
        "public_url_available": False,
        "x_public_url_replacement_allowed": False,
        "x_post_execution_allowed": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_update": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_MEDIA_AND_ONE_DRAFT_UPDATE_"
            "APPROVED_NOT_EXECUTED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-MEDIA-DRAFT-UPDATE-"
            "ONE-SHOT-EXECUTION"
        ),
    }

    gate = {
        **gate_payload,
        "wordpress_media_draft_update_"
        "explicit_approval_gate_digest_sha256": (
            canonical_digest(
                gate_payload
            )
        ),
    }

    issuance_lock_payload = {
        "lock_type": (
            "X_R11_WORDPRESS_MEDIA_DRAFT_"
            "UPDATE_APPROVAL_ISSUANCE"
        ),
        "created_at": approved_at,
        "approval_request_id": request_id,
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_label": approval_label,
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "wordpress_media_draft_update_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "approval_gate_pack_path": str(
            approval_gate_pack_path
        ),
        "approval_gate_digest_sha256": (
            gate[
                "wordpress_media_draft_update_"
                "explicit_approval_gate_digest_sha256"
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
        result = (
            build_explicit_approval_gate(
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
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_MEDIA_DRAFT_"
                        "UPDATE_EXPLICIT_APPROVAL_GATE"
                    ),
                    "error": str(exc),
                    "approval_issued": False,
                    "approval_consumed": False,
                    "wordpress_api_call": False,
                    "wordpress_write": False,
                    "wordpress_publication_allowed": False,
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
                "approval_gate_state": (
                    result[
                        "approval_gate_state"
                    ]
                ),
                "approval_request_id": (
                    result[
                        "approval_request_id"
                    ]
                ),
                "wordpress_post_id": 195,
                "wordpress_post_status": "draft",
                "human_decision": "APPROVED",
                "approval_issued": True,
                "approval_consumed": False,
                "runner_execution_allowed": True,
                "media_upload_allowed": True,
                "draft_content_update_allowed": True,
                "wordpress_publication_allowed": False,
                "x_post_execution_allowed": False,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "approval_gate_pack_path": str(
                    args.approval_gate_pack.resolve()
                ),
                "approval_gate_digest_sha256": (
                    result[
                        "wordpress_media_draft_update_"
                        "explicit_approval_gate_digest_sha256"
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
