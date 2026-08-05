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


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-MEDIA-DRAFT-UPDATE-"
    "HUMAN-REVIEW-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_READINESS_PREP_DIGEST = (
    "5aa7223ed42f04ab393ed21fa93f23081"
    "eb143a8b4360b5082492c9fe62c788a"
)

EXPECTED_WORDING_GATE_DIGEST = (
    "b52ca408c72095ea3b958bf28c044804"
    "c1f554ceda5f7b8fa7084539eda6ea8c"
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

EXPECTED_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_MEDIA_FILENAME = (
    "noa-senpai-wa-tomodachi-"
    "11-cover.jpg"
)

EXPECTED_MEDIA_ALT = (
    "のあ先輩はともだち。 "
    "第11巻 書影"
)

REMOTE_COVER_URL = (
    "https://shop.r10s.jp/"
    "rakutenkobo-ebooks/cabinet/6437/"
    "2000020786437.jpg"
)

MEDIA_URL_PLACEHOLDER = (
    "{{WORDPRESS_MEDIA_SOURCE_URL}}"
)

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "MEDIA_AND_DRAFT_UPDATE_ONLY"
)

EXPECTED_CHECK_COUNT = 10


class MediaDraftUpdateReviewError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise MediaDraftUpdateReviewError(
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
        raise MediaDraftUpdateReviewError(
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


def build_review_checklist() -> list[dict[str, str]]:
    return [
        {
            "check_id": "MEDIA_SOURCE_POLICY",
            "description": (
                "書影の取得元と利用方法を確認し、"
                "外部画像の直接参照を使用しない"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "MEDIA_BINARY_SHA",
            "description": (
                "書影JPEGのSHA-256が固定値と一致"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "MEDIA_DIMENSIONS",
            "description": (
                "書影サイズが300×373である"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "MEDIA_FILENAME",
            "description": (
                "WordPress登録ファイル名が適切"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "MEDIA_METADATA",
            "description": (
                "タイトル・代替テキスト・説明文が適切"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "TARGET_POST",
            "description": (
                "更新対象が投稿ID 195の下書きだけである"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "REMOTE_URL_REMOVAL",
            "description": (
                "楽天の書影URLが更新本文から除去されている"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "MEDIA_PLACEHOLDER",
            "description": (
                "WordPressメディアURL置換位置が1箇所だけ"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "DRAFT_STATUS_LOCK",
            "description": (
                "本文更新後も投稿状態をdraftに維持する"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "EXECUTION_BOUNDARY",
            "description": (
                "メディア作成1件・下書き更新1回までで、"
                "公開とX投稿を実行しない"
            ),
            "human_decision": "PENDING",
        },
    ]


def validate_pending_checklist(
    checklist: Any,
) -> None:
    require(
        isinstance(checklist, list),
        "review checklist must be a list",
    )

    require(
        len(checklist)
        == EXPECTED_CHECK_COUNT,
        (
            "review checklist must contain "
            f"{EXPECTED_CHECK_COUNT} checks"
        ),
    )

    check_ids: list[str] = []

    for item in checklist:
        require(
            isinstance(item, dict),
            "review checklist item is invalid",
        )

        check_id = item.get(
            "check_id"
        )

        require(
            isinstance(check_id, str)
            and check_id,
            "review check ID is missing",
        )

        require(
            item.get("human_decision")
            == "PENDING",
            (
                "review checklist item must "
                "remain pending"
            ),
        )

        check_ids.append(check_id)

    require(
        len(set(check_ids))
        == EXPECTED_CHECK_COUNT,
        "review check IDs are not unique",
    )


def validate_local_media(
    *,
    path: Path,
    expected_size: int,
) -> dict[str, Any]:
    require(
        path.is_file(),
        "local media file is missing",
    )

    value = path.read_bytes()

    require(
        value.startswith(b"\xff\xd8\xff"),
        "local media file is not a JPEG",
    )

    require(
        len(value) == expected_size,
        "local media byte size mismatch",
    )

    digest = sha256_file(
        path
    )

    require(
        digest == EXPECTED_MEDIA_SHA,
        "local media SHA mismatch",
    )

    return {
        "local_media_file_verified": True,
        "jpeg_magic_verified": True,
        "byte_size_verified": True,
        "sha256_verified": True,
    }


def validate_content_preview(
    *,
    path: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    require(
        path.is_file(),
        "content preview is missing",
    )

    text = path.read_text(
        encoding="utf-8"
    )

    require(
        sha256_text(text)
        == expected_sha256,
        "content preview SHA mismatch",
    )

    require(
        text.count(
            MEDIA_URL_PLACEHOLDER
        )
        == 1,
        (
            "media URL placeholder count "
            "must equal one"
        ),
    )

    require(
        REMOTE_COVER_URL not in text,
        (
            "remote cover URL remains in "
            "content preview"
        ),
    )

    require(
        "ebook-cover-image" in text,
        "cover-image marker is missing",
    )

    require(
        (
            'alt="'
            + EXPECTED_MEDIA_ALT
            + '"'
        )
        in text,
        "cover alt text is missing",
    )

    return {
        "content_preview_file_verified": True,
        "content_preview_sha_verified": True,
        "media_url_placeholder_count": 1,
        "remote_cover_url_absent": True,
        "cover_marker_verified": True,
        "cover_alt_text_verified": True,
    }


def build_human_review_prep(
    *,
    production_database_path: Path,
    readiness_prep_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    readiness_prep_path = (
        readiness_prep_path.resolve()
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
            "wordpress_media_publication_"
            "readiness_prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_READINESS_PREP_DIGEST
        ),
        label="media publication readiness prep",
    )

    require(
        readiness.get("status")
        == (
            "PASS_WORDPRESS_MEDIA_"
            "PUBLICATION_READINESS_PREP"
        ),
        "media readiness prep did not pass",
    )

    require(
        readiness.get("readiness_state")
        == (
            "MEDIA_BINARY_FIXED_AWAITING_"
            "EXPLICIT_MEDIA_UPLOAD_AND_"
            "DRAFT_UPDATE_APPROVAL"
        ),
        "media readiness state mismatch",
    )

    require(
        readiness.get(
            "source_wording_gate_digest_sha256"
        )
        == EXPECTED_WORDING_GATE_DIGEST,
        "source wording gate digest mismatch",
    )

    wordpress_post = readiness.get(
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
        wordpress_post.get("title")
        == EXPECTED_TITLE,
        "WordPress post title mismatch",
    )

    require(
        wordpress_post.get("slug")
        == EXPECTED_SLUG,
        "WordPress post slug mismatch",
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

    cover_media = readiness.get(
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
        cover_media.get("alt_text")
        == EXPECTED_MEDIA_ALT,
        "cover media alt text mismatch",
    )

    require(
        cover_media.get(
            "source_hotlink_approved"
        )
        is False,
        "source-image hotlink is unexpectedly approved",
    )

    require(
        cover_media.get(
            "expected_width"
        )
        == 300,
        "cover width mismatch",
    )

    require(
        cover_media.get(
            "expected_height"
        )
        == 373,
        "cover height mismatch",
    )

    local_media_path = Path(
        cover_media[
            "local_media_path"
        ]
    ).resolve()

    media_validation = validate_local_media(
        path=local_media_path,
        expected_size=int(
            cover_media["byte_size"]
        ),
    )

    media_request = readiness.get(
        "media_upload_request_preview"
    )

    require(
        isinstance(media_request, dict),
        "media upload request preview is missing",
    )

    require(
        media_request.get("api_method")
        == "POST_ONCE",
        "media upload method mismatch",
    )

    require(
        media_request.get("resource")
        == "/wp-json/wp/v2/media",
        "media upload resource mismatch",
    )

    require(
        media_request.get(
            "maximum_create_count"
        )
        == 1,
        "maximum media create count mismatch",
    )

    require(
        media_request.get(
            "execution_allowed"
        )
        is False,
        "media upload is unexpectedly allowed",
    )

    draft_update = readiness.get(
        "draft_content_update_preview"
    )

    require(
        isinstance(draft_update, dict),
        "draft update preview is missing",
    )

    require(
        draft_update.get("api_method")
        == "POST_ONCE",
        "draft update method mismatch",
    )

    require(
        draft_update.get("resource")
        == "/wp-json/wp/v2/posts/195",
        "draft update resource mismatch",
    )

    require(
        draft_update.get(
            "post_status_must_remain"
        )
        == "draft",
        "draft update status lock mismatch",
    )

    require(
        draft_update.get(
            "original_content_sha256"
        )
        == EXPECTED_ORIGINAL_CONTENT_SHA,
        "original content SHA mismatch",
    )

    require(
        draft_update.get(
            "media_source_url_placeholder"
        )
        == MEDIA_URL_PLACEHOLDER,
        "media URL placeholder mismatch",
    )

    require(
        draft_update.get(
            "placeholder_count"
        )
        == 1,
        "media placeholder count mismatch",
    )

    require(
        draft_update.get(
            "remote_source_url_removed"
        )
        is True,
        "remote source URL was not removed",
    )

    require(
        draft_update.get(
            "execution_allowed"
        )
        is False,
        "draft update is unexpectedly allowed",
    )

    content_preview_path = Path(
        draft_update[
            "content_preview_path"
        ]
    ).resolve()

    content_validation = (
        validate_content_preview(
            path=content_preview_path,
            expected_sha256=draft_update[
                "content_preview_sha256"
            ],
        )
    )

    constraints = readiness.get(
        "execution_constraints"
    )

    require(
        isinstance(constraints, dict),
        "execution constraints are missing",
    )

    require(
        constraints.get(
            "media_upload_count_maximum"
        )
        == 1,
        "media upload maximum mismatch",
    )

    require(
        constraints.get(
            "post_update_count_maximum"
        )
        == 1,
        "post update maximum mismatch",
    )

    require(
        constraints.get(
            "post_id_must_equal"
        )
        == EXPECTED_POST_ID,
        "target post constraint mismatch",
    )

    require(
        constraints.get(
            "post_status_must_remain"
        )
        == "draft",
        "post status constraint mismatch",
    )

    require(
        constraints.get(
            "failure_stops_all"
        )
        is True,
        "failure-stop constraint is missing",
    )

    require(
        constraints.get(
            "publication_in_same_execution_allowed"
        )
        is False,
        "publication is unexpectedly permitted",
    )

    for field in (
        "media_upload_allowed",
        "draft_content_update_allowed",
        "wordpress_publication_allowed",
        "x_public_url_replacement_allowed",
        "x_post_execution_allowed",
        "wordpress_write",
        "wordpress_media_write",
        "wordpress_post_update",
        "database_write",
        "workflow_write",
        "x_api_call",
        "x_post",
    ):
        require(
            readiness.get(field)
            is False,
            (
                "unexpected allowed/write state: "
                f"{field}"
            ),
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
            "PASS_WORDPRESS_MEDIA_DRAFT_"
            "UPDATE_HUMAN_REVIEW_PREP_READY"
        ),
        "human_review_state": (
            "AWAITING_EXPLICIT_HUMAN_MEDIA_"
            "AND_DRAFT_UPDATE_DECISION"
        ),
        "prepared_at": prepared_at,
        "source_readiness_prep_path": str(
            readiness_prep_path
        ),
        "source_readiness_prep_digest_sha256": (
            EXPECTED_READINESS_PREP_DIGEST
        ),
        "source_wording_gate_digest_sha256": (
            EXPECTED_WORDING_GATE_DIGEST
        ),
        "wordpress_post": {
            "post_id": EXPECTED_POST_ID,
            "title": EXPECTED_TITLE,
            "slug": EXPECTED_SLUG,
            "status": "draft",
            "public_url_available": False,
        },
        "cover_media": {
            "local_media_path": str(
                local_media_path
            ),
            "filename": EXPECTED_MEDIA_FILENAME,
            "sha256": EXPECTED_MEDIA_SHA,
            "byte_size": cover_media[
                "byte_size"
            ],
            "mime_type": "image/jpeg",
            "width": 300,
            "height": 373,
            "alt_text": EXPECTED_MEDIA_ALT,
            "validation": media_validation,
        },
        "media_upload_request_preview": (
            media_request
        ),
        "draft_content_update_preview": {
            **draft_update,
            "validation": content_validation,
        },
        "machine_precheck": {
            "passed": True,
            "check_count": (
                EXPECTED_CHECK_COUNT
            ),
            "media_binary_verified": True,
            "content_preview_verified": True,
            "post_status_locked_to_draft": True,
            "publication_blocked": True,
        },
        "human_review_checklist": checklist,
        "approval_label_if_approved": (
            APPROVAL_LABEL
        ),
        "approval_scope_if_approved": (
            "ONE_WORDPRESS_MEDIA_UPLOAD_AND_"
            "ONE_DRAFT_CONTENT_UPDATE_ONLY"
        ),
        "human_decision": "PENDING",
        "human_review_completed": False,
        "approval_issued": False,
        "approval_consumed": False,
        "media_upload_allowed": False,
        "draft_content_update_allowed": False,
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
            "MEDIA_AND_DRAFT_UPDATE_"
            "HUMAN_REVIEW_PENDING_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-MEDIA-DRAFT-UPDATE-"
            "EXPLICIT-APPROVAL-GATE"
        ),
    }

    review = {
        **review_payload,
        "wordpress_media_draft_update_"
        "human_review_prep_digest_sha256": (
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
            output_path=args.output,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_MEDIA_DRAFT_"
                        "UPDATE_HUMAN_REVIEW_PREP"
                    ),
                    "error": str(exc),
                    "human_review_completed": False,
                    "approval_issued": False,
                    "media_upload_allowed": False,
                    "draft_content_update_allowed": False,
                    "wordpress_publication_allowed": False,
                    "wordpress_write": False,
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
                "human_review_state": (
                    result["human_review_state"]
                ),
                "wordpress_post_id": (
                    result[
                        "wordpress_post"
                    ]["post_id"]
                ),
                "wordpress_post_status": "draft",
                "media_sha256": (
                    result[
                        "cover_media"
                    ]["sha256"]
                ),
                "machine_precheck_passed": True,
                "human_check_count": (
                    EXPECTED_CHECK_COUNT
                ),
                "human_decision": "PENDING",
                "approval_issued": False,
                "media_upload_allowed": False,
                "draft_content_update_allowed": False,
                "wordpress_publication_allowed": False,
                "wordpress_write": False,
                "x_post_execution_allowed": False,
                "production_status": "NO_GO",
                "approval_label_if_approved": (
                    APPROVAL_LABEL
                ),
                "review_pack_path": str(
                    args.output.resolve()
                ),
                "review_digest_sha256": (
                    result[
                        "wordpress_media_draft_update_"
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
