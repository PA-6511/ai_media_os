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
    "X-DRAFT-FINAL-HUMAN-REVIEW-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_REPLACEMENT_PACK_DIGEST = (
    "7eae4a30876f6a411fef085c76ec10b3"
    "29b6d9d864fb534d11dcb90d9ba8cd4a"
)

EXPECTED_PUBLICATION_VERIFICATION_DIGEST = (
    "16e863ba32985294189c2f63314ddf6a"
    "ed7cf9a3ab3ed594568da35d9dba552c"
)

EXPECTED_WORDING_GATE_DIGEST = (
    "b52ca408c72095ea3b958bf28c044804"
    "c1f554ceda5f7b8fa7084539eda6ea8c"
)

EXPECTED_SOURCE_DRAFT_ID = (
    "xr11-x-draft-local-"
    "7b571ccea2b70141224efa17"
)

EXPECTED_FINAL_DRAFT_ID = (
    "xr11-x-draft-public-url-"
    "4842647be85ea1d60aab47fd"
)

EXPECTED_FINAL_TEXT_SHA = (
    "4842647be85ea1d60aab47fd159b85ee"
    "ef23c9632809a617fc2f49c21586e7af"
)

EXPECTED_PUBLIC_URL = (
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
)

EXPECTED_LITERAL_CHARACTER_COUNT = 160
EXPECTED_TCO_CHARACTER_COUNT = 117
TCO_URL_CHARACTER_COUNT = 23
EXPECTED_CHECK_COUNT = 10

PUBLIC_URL_PLACEHOLDER = (
    "{{WORDPRESS_PUBLIC_URL}}"
)

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_X_DRAFT_"
    "FINAL_REVIEW_ONLY"
)

APPROVAL_SCOPE = (
    "ONE_LOCAL_X_DRAFT_FINAL_REVIEW_"
    "ONLY_NO_X_POST"
)

EXPECTED_FINAL_TEXT = (
    "【新刊】\n"
    "『のあ先輩はともだち。』"
    "第11巻が7月17日に配信開始📚\n"
    "\n"
    "著者：あきやまえんま\n"
    "出版社：集英社\n"
    "\n"
    "楽天Koboの配信情報・価格はこちら\n"
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/\n"
    "\n"
    "#のあ先輩はともだち "
    "#コミック新刊"
)

EXPECTED_HASHTAGS = [
    "#のあ先輩はともだち",
    "#コミック新刊",
]


class XDraftFinalHumanReviewError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XDraftFinalHumanReviewError(
            message
        )


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
        raise XDraftFinalHumanReviewError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


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
        f"{label} recorded digest mismatch",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == expected_digest,
        f"{label} canonical digest mismatch",
    )


def verify_any_digest(
    value: dict[str, Any],
    *,
    expected_digest: str,
    label: str,
) -> str:
    candidates = [
        key
        for key, item in value.items()
        if (
            key.endswith("digest_sha256")
            and item == expected_digest
        )
    ]

    require(
        bool(candidates),
        f"{label} digest field is missing",
    )

    for field in candidates:
        payload = {
            key: item
            for key, item in value.items()
            if key != field
        }

        if canonical_digest(
            payload
        ) == expected_digest:
            return field

    raise XDraftFinalHumanReviewError(
        f"{label} canonical digest mismatch"
    )


def estimate_tco_character_count(
    value: str,
) -> int:
    urls = re.findall(
        r"https://[^\s]+",
        value,
    )

    require(
        len(urls) == 1,
        (
            "t.co character estimate requires "
            "exactly one URL"
        ),
    )

    return (
        len(value)
        - len(urls[0])
        + TCO_URL_CHARACTER_COUNT
    )


def extract_hashtags(
    value: str,
) -> list[str]:
    return re.findall(
        r"(?<!\S)#[^\s#]+",
        value,
    )


def validate_final_text(
    value: str,
) -> dict[str, Any]:
    require(
        value == EXPECTED_FINAL_TEXT,
        "final X draft text mismatch",
    )

    require(
        sha256_text(value)
        == EXPECTED_FINAL_TEXT_SHA,
        "final X draft SHA mismatch",
    )

    require(
        PUBLIC_URL_PLACEHOLDER
        not in value,
        "public URL placeholder remains",
    )

    require(
        value.count(
            EXPECTED_PUBLIC_URL
        )
        == 1,
        "public URL count must equal one",
    )

    require(
        len(value)
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "literal character count mismatch",
    )

    tco_count = (
        estimate_tco_character_count(
            value
        )
    )

    require(
        tco_count
        == EXPECTED_TCO_CHARACTER_COUNT,
        "estimated t.co character count mismatch",
    )

    hashtags = extract_hashtags(
        value
    )

    require(
        hashtags == EXPECTED_HASHTAGS,
        "X hashtag set or order mismatch",
    )

    lines = value.splitlines()

    require(
        len(lines) == 10,
        "final X draft line count mismatch",
    )

    require(
        lines[0] == "【新刊】",
        "X draft headline mismatch",
    )

    require(
        "『のあ先輩はともだち。』第11巻"
        in lines[1],
        "work title or volume is missing",
    )

    require(
        "7月17日に配信開始"
        in lines[1],
        "release date wording is missing",
    )

    require(
        lines[3]
        == "著者：あきやまえんま",
        "author wording mismatch",
    )

    require(
        lines[4]
        == "出版社：集英社",
        "publisher wording mismatch",
    )

    require(
        lines[6]
        == "楽天Koboの配信情報・価格はこちら",
        "affiliate guidance wording mismatch",
    )

    require(
        lines[7] == EXPECTED_PUBLIC_URL,
        "public URL line mismatch",
    )

    return {
        "text_sha256": (
            EXPECTED_FINAL_TEXT_SHA
        ),
        "literal_character_count": (
            EXPECTED_LITERAL_CHARACTER_COUNT
        ),
        "estimated_tco_character_count": (
            EXPECTED_TCO_CHARACTER_COUNT
        ),
        "line_count": 10,
        "public_url": EXPECTED_PUBLIC_URL,
        "public_url_count": 1,
        "public_url_placeholder_absent": True,
        "headline_verified": True,
        "title_and_volume_verified": True,
        "release_date_verified": True,
        "author_verified": True,
        "publisher_verified": True,
        "affiliate_guidance_verified": True,
        "hashtags": hashtags,
        "hashtag_count": len(hashtags),
    }


def validate_replacement_pack(
    value: dict[str, Any],
) -> None:
    verify_digest(
        value,
        digest_field=(
            "x_draft_public_url_replacement_"
            "local_prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_REPLACEMENT_PACK_DIGEST
        ),
        label="public URL replacement pack",
    )

    require(
        value.get("status")
        == (
            "PASS_X_DRAFT_PUBLIC_URL_"
            "REPLACEMENT_LOCAL_PREP"
        ),
        "replacement pack status mismatch",
    )

    require(
        value.get("replacement_state")
        == (
            "PUBLIC_URL_REPLACED_LOCAL_DRAFT_"
            "GENERATED_FINAL_HUMAN_REVIEW_REQUIRED"
        ),
        "replacement pack state mismatch",
    )

    require(
        value.get("source_x_draft_id")
        == EXPECTED_SOURCE_DRAFT_ID,
        "source X draft ID mismatch",
    )

    require(
        value.get(
            "source_wording_gate_digest_sha256"
        )
        == EXPECTED_WORDING_GATE_DIGEST,
        "source wording gate digest mismatch",
    )

    require(
        value.get(
            "source_publication_verification_"
            "digest_sha256"
        )
        == EXPECTED_PUBLICATION_VERIFICATION_DIGEST,
        (
            "source publication verification "
            "digest mismatch"
        ),
    )

    draft = value.get(
        "x_draft"
    )

    require(
        isinstance(draft, dict),
        "replacement X draft evidence is missing",
    )

    require(
        draft.get("draft_id")
        == EXPECTED_FINAL_DRAFT_ID,
        "replacement X draft ID mismatch",
    )

    require(
        draft.get("text")
        == EXPECTED_FINAL_TEXT,
        "replacement X draft text mismatch",
    )

    require(
        draft.get("text_sha256")
        == EXPECTED_FINAL_TEXT_SHA,
        "replacement X draft SHA mismatch",
    )

    require(
        draft.get(
            "literal_character_count"
        )
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "replacement literal count mismatch",
    )

    require(
        draft.get(
            "estimated_tco_character_count"
        )
        == EXPECTED_TCO_CHARACTER_COUNT,
        "replacement t.co count mismatch",
    )

    require(
        draft.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "replacement public URL mismatch",
    )

    require(
        draft.get("public_url_count")
        == 1,
        "replacement public URL count mismatch",
    )

    require(
        draft.get(
            "public_url_placeholder_absent"
        )
        is True,
        "replacement placeholder remains",
    )

    require(
        draft.get(
            "wording_outside_url_unchanged"
        )
        is True,
        "replacement changed approved wording",
    )

    require(
        value.get(
            "source_x_draft_preserved"
        )
        is True,
        "source X draft was not preserved",
    )

    require(
        value.get(
            "source_x_draft_modified"
        )
        is False,
        "source X draft was modified",
    )

    require(
        value.get(
            "public_url_replacement_completed"
        )
        is True,
        "public URL replacement was not completed",
    )

    require(
        value.get(
            "final_human_review_required"
        )
        is True,
        "final human review is not required",
    )

    require(
        value.get(
            "final_human_review_completed"
        )
        is False,
        "final human review is already complete",
    )

    require(
        value.get(
            "x_final_review_allowed"
        )
        is False,
        "final X review is already allowed",
    )

    require(
        value.get(
            "x_post_approval_issued"
        )
        is False,
        "X post approval was already issued",
    )

    for field in (
        "x_post_execution_allowed",
        "normal_x_fb_write",
        "wordpress_write",
        "database_write",
        "workflow_write",
        "x_api_call",
        "x_post",
    ):
        require(
            value.get(field)
            is False,
            (
                "replacement pack records an "
                f"unexpected action: {field}"
            ),
        )

    require(
        value.get("production_status")
        == "NO_GO",
        "replacement production status mismatch",
    )


def validate_generation_lock(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_X_DRAFT_PUBLIC_URL_"
            "REPLACEMENT_LOCAL_GENERATION"
        ),
        "replacement generation lock type mismatch",
    )

    require(
        value.get(
            "source_publication_verification_"
            "digest_sha256"
        )
        == EXPECTED_PUBLICATION_VERIFICATION_DIGEST,
        "generation lock source digest mismatch",
    )

    require(
        value.get("source_x_draft_id")
        == EXPECTED_SOURCE_DRAFT_ID,
        "generation lock source draft mismatch",
    )

    require(
        value.get(
            "replacement_x_draft_id"
        )
        == EXPECTED_FINAL_DRAFT_ID,
        "generation lock replacement draft mismatch",
    )

    require(
        value.get(
            "replacement_text_sha256"
        )
        == EXPECTED_FINAL_TEXT_SHA,
        "generation lock text SHA mismatch",
    )

    require(
        value.get(
            "replacement_pack_digest_sha256"
        )
        == EXPECTED_REPLACEMENT_PACK_DIGEST,
        "generation lock pack digest mismatch",
    )

    require(
        value.get("generation_completed")
        is True,
        "replacement generation did not complete",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "replacement generation lock permits rerun",
    )


def validate_wording_gate(
    value: dict[str, Any],
) -> None:
    verify_any_digest(
        value,
        expected_digest=(
            EXPECTED_WORDING_GATE_DIGEST
        ),
        label="X wording review gate",
    )

    require(
        value.get("status")
        == (
            "PASS_X_DRAFT_WORDING_REVIEW_"
            "APPROVED_PUBLIC_URL_PENDING"
        ),
        "X wording gate status mismatch",
    )

    require(
        value.get("wording_gate_state")
        == (
            "WORDING_FIXED_AWAITING_"
            "WORDPRESS_PUBLICATION_AND_PUBLIC_URL"
        ),
        "X wording gate state mismatch",
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
        "X wording was not approved",
    )

    require(
        human_review.get(
            "approval_consumed"
        )
        is True,
        "X wording approval was not consumed",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "wording gate permits X posting",
    )


def validate_publication_verification(
    value: dict[str, Any],
) -> None:
    verify_digest(
        value,
        digest_field=(
            "wordpress_publication_"
            "post_execution_verification_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_PUBLICATION_VERIFICATION_DIGEST
        ),
        label="WordPress publication verification",
    )

    require(
        value.get("status")
        == (
            "PASS_WORDPRESS_PUBLICATION_"
            "POST_EXECUTION_VERIFICATION"
        ),
        "publication verification status mismatch",
    )

    require(
        value.get("verification_state")
        == (
            "WORDPRESS_POST_195_PUBLISH_AND_"
            "PUBLIC_URL_VERIFIED_"
            "X_URL_REPLACEMENT_READY"
        ),
        "publication verification state mismatch",
    )

    require(
        value.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "verified public URL mismatch",
    )

    require(
        value.get("public_url_available")
        is True,
        "public URL is unavailable",
    )

    require(
        value.get(
            "x_public_url_replacement_allowed"
        )
        is True,
        "public URL replacement was not allowed",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "publication verification permits X posting",
    )


def build_review_checklist() -> list[dict[str, str]]:
    return [
        {
            "check_id": "HEADLINE_FORMAT",
            "description": (
                "先頭の【新刊】表記と改行配置が正しい"
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
                "著者名と出版社名が正しい"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "PUBLIC_URL",
            "description": (
                "公開URLが投稿ID195の記事へ接続する"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "URL_PLACEHOLDER",
            "description": (
                "公開URLプレースホルダーが残っていない"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "CHARACTER_COUNT",
            "description": (
                "t.co換算117文字でX上限内である"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "HASHTAGS",
            "description": (
                "2個のハッシュタグが適切である"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "WORDING_FREEZE",
            "description": (
                "URL以外の承認済み文面が変わっていない"
            ),
            "human_decision": "PENDING",
        },
        {
            "check_id": "MANUAL_POST_BOUNDARY",
            "description": (
                "この確認はX投稿やX API実行を許可しない"
            ),
            "human_decision": "PENDING",
        },
    ]


def validate_pending_checklist(
    value: Any,
) -> None:
    require(
        isinstance(value, list),
        "final review checklist must be a list",
    )

    require(
        len(value)
        == EXPECTED_CHECK_COUNT,
        (
            "final review checklist must contain "
            f"{EXPECTED_CHECK_COUNT} checks"
        ),
    )

    check_ids: list[str] = []

    for item in value:
        require(
            isinstance(item, dict),
            "final review checklist item is invalid",
        )

        check_id = item.get(
            "check_id"
        )

        require(
            isinstance(check_id, str)
            and check_id,
            "final review check ID is missing",
        )

        require(
            item.get("human_decision")
            == "PENDING",
            (
                "final review checklist must "
                "remain pending"
            ),
        )

        check_ids.append(check_id)

    require(
        len(set(check_ids))
        == EXPECTED_CHECK_COUNT,
        "final review check IDs are not unique",
    )


def build_final_review_prep(
    *,
    production_database_path: Path,
    replacement_pack_path: Path,
    replacement_text_path: Path,
    generation_lock_path: Path,
    wording_gate_path: Path,
    publication_verification_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    replacement_pack_path = (
        replacement_pack_path.resolve()
    )

    replacement_text_path = (
        replacement_text_path.resolve()
    )

    generation_lock_path = (
        generation_lock_path.resolve()
    )

    wording_gate_path = (
        wording_gate_path.resolve()
    )

    publication_verification_path = (
        publication_verification_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    replacement_pack = load_json(
        replacement_pack_path
    )

    validate_replacement_pack(
        replacement_pack
    )

    generation_lock = load_json(
        generation_lock_path
    )

    validate_generation_lock(
        generation_lock
    )

    wording_gate = load_json(
        wording_gate_path
    )

    validate_wording_gate(
        wording_gate
    )

    publication_verification = load_json(
        publication_verification_path
    )

    validate_publication_verification(
        publication_verification
    )

    require(
        replacement_text_path.is_file(),
        "public URL-bound X draft text is missing",
    )

    require(
        sha256_file(
            replacement_text_path
        )
        == EXPECTED_FINAL_TEXT_SHA,
        "public URL-bound X draft file SHA mismatch",
    )

    final_text = replacement_text_path.read_text(
        encoding="utf-8"
    )

    text_validation = validate_final_text(
        final_text
    )

    replacement_draft = (
        replacement_pack.get(
            "x_draft"
        )
    )

    require(
        isinstance(replacement_draft, dict),
        "replacement pack draft evidence is missing",
    )

    require(
        Path(
            replacement_draft["text_path"]
        ).resolve()
        == replacement_text_path,
        "replacement text path mismatch",
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
            "PASS_X_DRAFT_FINAL_HUMAN_"
            "REVIEW_PREP_READY"
        ),
        "human_review_state": (
            "AWAITING_EXPLICIT_HUMAN_"
            "FINAL_X_DRAFT_DECISION"
        ),
        "prepared_at": prepared_at,
        "source_replacement_pack_path": str(
            replacement_pack_path
        ),
        "source_replacement_pack_digest_sha256": (
            EXPECTED_REPLACEMENT_PACK_DIGEST
        ),
        "source_generation_lock_path": str(
            generation_lock_path
        ),
        "source_wording_gate_path": str(
            wording_gate_path
        ),
        "source_wording_gate_digest_sha256": (
            EXPECTED_WORDING_GATE_DIGEST
        ),
        "source_publication_verification_path": str(
            publication_verification_path
        ),
        "source_publication_verification_digest_sha256": (
            EXPECTED_PUBLICATION_VERIFICATION_DIGEST
        ),
        "wordpress_post": {
            "post_id": 195,
            "status": "publish",
            "public_url": EXPECTED_PUBLIC_URL,
            "public_http_status": 200,
        },
        "x_draft": {
            "draft_id": (
                EXPECTED_FINAL_DRAFT_ID
            ),
            "revision": "PUBLIC_URL_BOUND_V1",
            "text": final_text,
            "text_path": str(
                replacement_text_path
            ),
            **text_validation,
        },
        "machine_precheck": {
            "passed": True,
            "check_count": (
                EXPECTED_CHECK_COUNT
            ),
            "replacement_pack_digest_verified": True,
            "generation_lock_verified": True,
            "wording_approval_verified": True,
            "wordpress_publication_verified": True,
            "text_sha256_verified": True,
            "public_url_verified": True,
            "public_url_placeholder_absent": True,
            "character_count_verified": True,
            "hashtags_verified": True,
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
        "final_human_review_required": True,
        "final_human_review_completed": False,
        "x_final_review_approval_issued": False,
        "x_final_review_approval_consumed": False,
        "x_post_approval_issued": False,
        "manual_x_posting_allowed": False,
        "x_post_execution_allowed": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "FINAL_X_DRAFT_HUMAN_REVIEW_PENDING_"
            "ALL_X_EXECUTION_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-DRAFT-FINAL-REVIEW-"
            "EXPLICIT-APPROVAL-GATE"
        ),
    }

    review = {
        **review_payload,
        "x_draft_final_human_review_"
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
        "--replacement-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--replacement-text",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--generation-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--wording-gate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--publication-verification",
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
        result = build_final_review_prep(
            production_database_path=(
                args.production_db
            ),
            replacement_pack_path=(
                args.replacement_pack
            ),
            replacement_text_path=(
                args.replacement_text
            ),
            generation_lock_path=(
                args.generation_lock
            ),
            wording_gate_path=(
                args.wording_gate
            ),
            publication_verification_path=(
                args.publication_verification
            ),
            output_path=args.output,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_DRAFT_FINAL_HUMAN_"
                        "REVIEW_PREP"
                    ),
                    "error": str(exc),
                    "final_human_review_completed": False,
                    "x_final_review_approval_issued": False,
                    "manual_x_posting_allowed": False,
                    "x_post_execution_allowed": False,
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

    draft = result[
        "x_draft"
    ]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "human_review_state": (
                    result["human_review_state"]
                ),
                "x_draft_id": (
                    draft["draft_id"]
                ),
                "x_draft_text_sha256": (
                    draft["text_sha256"]
                ),
                "literal_character_count": (
                    draft[
                        "literal_character_count"
                    ]
                ),
                "estimated_tco_character_count": (
                    draft[
                        "estimated_tco_character_count"
                    ]
                ),
                "public_url": (
                    draft["public_url"]
                ),
                "machine_precheck_passed": True,
                "human_check_count": (
                    EXPECTED_CHECK_COUNT
                ),
                "human_decision": "PENDING",
                "final_human_review_completed": False,
                "x_final_review_approval_issued": False,
                "x_post_approval_issued": False,
                "manual_x_posting_allowed": False,
                "x_post_execution_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
                "approval_label_if_approved": (
                    APPROVAL_LABEL
                ),
                "review_pack_path": str(
                    args.output.resolve()
                ),
                "review_digest_sha256": (
                    result[
                        "x_draft_final_human_review_"
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
