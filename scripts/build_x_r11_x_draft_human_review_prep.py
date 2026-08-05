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
    "X-DRAFT-HUMAN-REVIEW-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_X_DRAFT_PACK_DIGEST = (
    "869143e190d896c80df3c0ec21df51e2"
    "9ba9528c4b3dbdb9f8b456119b5b76f7"
)

EXPECTED_VERIFICATION_DIGEST = (
    "3271baa516a5d5de36a087195430aade3"
    "788a364aa543670c2044d33f7699514"
)

EXPECTED_DRAFT_TEXT_SHA = (
    "7b571ccea2b70141224efa17cbd3fbff"
    "89383ca5ad5460e7edd110d8af49b6da"
)

EXPECTED_DRAFT_ID = (
    "xr11-x-draft-local-"
    "7b571ccea2b70141224efa17"
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

PUBLIC_URL_PLACEHOLDER = (
    "{{WORDPRESS_PUBLIC_URL}}"
)

WORDING_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_X_DRAFT_"
    "WORDING_REVIEW_ONLY"
)

EXPECTED_CHECK_COUNT = 8

EXPECTED_DRAFT_TEXT = (
    "【新刊】\n"
    "『のあ先輩はともだち。』"
    "第11巻が7月17日に配信開始📚\n"
    "\n"
    "著者：あきやまえんま\n"
    "出版社：集英社\n"
    "\n"
    "楽天Koboの配信情報・価格はこちら\n"
    "{{WORDPRESS_PUBLIC_URL}}\n"
    "\n"
    "#のあ先輩はともだち "
    "#コミック新刊"
)


class XDraftHumanReviewPrepError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XDraftHumanReviewPrepError(
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
        raise XDraftHumanReviewPrepError(
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
            "check_id": "NEW_RELEASE_LABEL",
            "description": (
                "新刊告知であることが明確"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "TITLE_AND_VOLUME",
            "description": (
                "作品名と第11巻の表記が正しい"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "RELEASE_DATE",
            "description": (
                "7月17日配信開始の表記が正しい"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "AUTHOR_AND_PUBLISHER",
            "description": (
                "著者と出版社の表記が正しい"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "STORE_CALL_TO_ACTION",
            "description": (
                "楽天Koboへの案内文が適切"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "HASHTAGS",
            "description": (
                "作品名とコミック新刊の"
                "ハッシュタグが適切"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "CHARACTER_LIMIT",
            "description": (
                "公開URL置換後も280文字以内"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "PUBLIC_URL_PLACEHOLDER",
            "description": (
                "現在は公開URL未確定のため"
                "プレースホルダーのままである"
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


def validate_reviewable_draft_text(
    draft_text: str,
) -> dict[str, Any]:
    require(
        draft_text == EXPECTED_DRAFT_TEXT,
        "X draft text differs from fixed text",
    )

    require(
        sha256_text(draft_text)
        == EXPECTED_DRAFT_TEXT_SHA,
        "X draft text SHA mismatch",
    )

    require(
        draft_text.count(
            PUBLIC_URL_PLACEHOLDER
        )
        == 1,
        (
            "public URL placeholder count "
            "must equal one"
        ),
    )

    require(
        "https://" not in draft_text,
        (
            "literal public URL must not exist "
            "before publication"
        ),
    )

    required_fragments = (
        "【新刊】",
        "のあ先輩はともだち。",
        "第11巻",
        "7月17日",
        "あきやまえんま",
        "集英社",
        "楽天Kobo",
        "#のあ先輩はともだち",
        "#コミック新刊",
    )

    missing = [
        fragment
        for fragment in required_fragments
        if fragment not in draft_text
    ]

    require(
        not missing,
        (
            "required X draft fragments "
            "are missing: "
            + ", ".join(missing)
        ),
    )

    literal_count = len(
        draft_text
    )

    estimated_count = (
        literal_count
        - len(PUBLIC_URL_PLACEHOLDER)
        + 23
    )

    require(
        estimated_count <= 280,
        (
            "estimated X character count "
            f"exceeds 280: {estimated_count}"
        ),
    )

    return {
        "exact_text_verified": True,
        "text_sha256_verified": True,
        "public_url_placeholder_count": 1,
        "literal_public_url_absent": True,
        "literal_character_count": (
            literal_count
        ),
        "estimated_character_count_with_tco_url": (
            estimated_count
        ),
        "character_limit_passed": True,
    }


def build_human_review_prep(
    *,
    production_database_path: Path,
    x_draft_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    x_draft_pack_path = (
        x_draft_pack_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    source = load_json(
        x_draft_pack_path
    )

    verify_digest(
        source,
        digest_field=(
            "x_draft_local_generation_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_X_DRAFT_PACK_DIGEST
        ),
        label="X draft local generation pack",
    )

    require(
        source.get("status")
        == "PASS_X_DRAFT_LOCAL_GENERATION",
        "X draft local generation did not pass",
    )

    require(
        source.get("x_draft_state")
        == (
            "LOCAL_DRAFT_GENERATED_"
            "PUBLIC_URL_AND_HUMAN_REVIEW_REQUIRED"
        ),
        "X draft state mismatch",
    )

    require(
        source.get(
            "source_verification_digest_sha256"
        )
        == EXPECTED_VERIFICATION_DIGEST,
        "source verification digest mismatch",
    )

    wordpress_post = source.get(
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
        (
            "public URL must remain unavailable "
            "while WordPress status is draft"
        ),
    )

    require(
        wordpress_post.get(
            "public_url_placeholder"
        )
        == PUBLIC_URL_PLACEHOLDER,
        "public URL placeholder mismatch",
    )

    x_draft = source.get(
        "x_draft"
    )

    require(
        isinstance(x_draft, dict),
        "X draft evidence is missing",
    )

    require(
        x_draft.get("draft_id")
        == EXPECTED_DRAFT_ID,
        "X draft ID mismatch",
    )

    draft_text = x_draft.get(
        "text"
    )

    require(
        isinstance(draft_text, str),
        "X draft text is missing",
    )

    text_validation = (
        validate_reviewable_draft_text(
            draft_text
        )
    )

    require(
        x_draft.get("text_sha256")
        == EXPECTED_DRAFT_TEXT_SHA,
        "recorded X draft text SHA mismatch",
    )

    draft_text_path = Path(
        x_draft["text_path"]
    ).resolve()

    require(
        draft_text_path.is_file(),
        "X draft text file is missing",
    )

    file_text = draft_text_path.read_text(
        encoding="utf-8"
    )

    require(
        file_text == draft_text + "\n",
        (
            "X draft text file differs from "
            "the fixed draft text"
        ),
    )

    require(
        source.get(
            "x_draft_generation_completed"
        )
        is True,
        "X draft generation is incomplete",
    )

    require(
        source.get(
            "x_human_review_completed"
        )
        is False,
        "X human review is already complete",
    )

    require(
        source.get(
            "x_post_approval_issued"
        )
        is False,
        "X post approval was already issued",
    )

    for field in (
        "x_api_call",
        "x_post",
        "normal_x_fb_write",
        "wordpress_api_call",
        "wordpress_write",
        "database_write",
        "workflow_write",
    ):
        require(
            source.get(field) is False,
            (
                "unexpected write or API state: "
                f"{field}"
            ),
        )

    affiliate = source.get(
        "affiliate_evidence"
    )

    require(
        isinstance(affiliate, dict),
        "affiliate evidence is missing",
    )

    require(
        affiliate.get(
            "affiliate_url_verified"
        )
        is True,
        "affiliate URL is not verified",
    )

    require(
        affiliate.get(
            "affiliate_url_embedded_in_primary_text"
        )
        is False,
        (
            "raw affiliate URL must not be "
            "embedded in the primary X text"
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
            "PASS_X_DRAFT_HUMAN_"
            "REVIEW_PREP_READY"
        ),
        "human_review_state": (
            "AWAITING_EXPLICIT_HUMAN_"
            "WORDING_DECISION"
        ),
        "prepared_at": prepared_at,
        "source_x_draft_pack_path": str(
            x_draft_pack_path
        ),
        "source_x_draft_pack_digest_sha256": (
            EXPECTED_X_DRAFT_PACK_DIGEST
        ),
        "source_verification_digest_sha256": (
            EXPECTED_VERIFICATION_DIGEST
        ),
        "wordpress_post": {
            "post_id": EXPECTED_POST_ID,
            "title": EXPECTED_TITLE,
            "slug": EXPECTED_SLUG,
            "status": "draft",
            "public_url_available": False,
            "publication_allowed": False,
        },
        "x_draft": {
            "draft_id": EXPECTED_DRAFT_ID,
            "text": draft_text,
            "text_path": str(
                draft_text_path
            ),
            "text_sha256": (
                EXPECTED_DRAFT_TEXT_SHA
            ),
            "text_validation": (
                text_validation
            ),
        },
        "machine_precheck": {
            "passed": True,
            "check_count": (
                EXPECTED_CHECK_COUNT
            ),
            "public_url_unresolved": True,
            "raw_affiliate_url_absent": True,
            "character_limit_passed": True,
        },
        "human_review_checklist": checklist,
        "approval_label_if_approved": (
            WORDING_APPROVAL_LABEL
        ),
        "approval_scope_if_approved": (
            "X_DRAFT_WORDING_REVIEW_ONLY"
        ),
        "human_decision": "PENDING",
        "human_review_completed": False,
        "wording_approval_issued": False,
        "wording_approval_consumed": False,
        "public_url_replacement_allowed": False,
        "final_x_review_allowed": False,
        "x_post_approval_issued": False,
        "x_post_execution_allowed": False,
        "wordpress_publication_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "production_status": "NO_GO",
        "safety_state": (
            "X_WORDING_REVIEW_PENDING_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
    }

    review = {
        **review_payload,
        "x_draft_human_review_prep_"
        "digest_sha256": (
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
        "--x-draft-pack",
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
            x_draft_pack_path=(
                args.x_draft_pack
            ),
            output_path=args.output,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_DRAFT_HUMAN_"
                        "REVIEW_PREP"
                    ),
                    "error": str(exc),
                    "human_review_completed": False,
                    "wording_approval_issued": False,
                    "x_api_call": False,
                    "x_post": False,
                    "wordpress_write": False,
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
                    result[
                        "human_review_state"
                    ]
                ),
                "draft_id": (
                    result[
                        "x_draft"
                    ]["draft_id"]
                ),
                "wordpress_post_id": 195,
                "wordpress_post_status": "draft",
                "machine_precheck_passed": True,
                "human_check_count": (
                    EXPECTED_CHECK_COUNT
                ),
                "human_decision": "PENDING",
                "public_url_unresolved": True,
                "wording_approval_issued": False,
                "x_post_execution_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "approval_label_if_approved": (
                    WORDING_APPROVAL_LABEL
                ),
                "review_pack_path": str(
                    args.output.resolve()
                ),
                "review_digest_sha256": (
                    result[
                        "x_draft_human_review_"
                        "prep_digest_sha256"
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
