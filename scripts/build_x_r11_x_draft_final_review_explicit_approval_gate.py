from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    "X-DRAFT-FINAL-REVIEW-"
    "EXPLICIT-APPROVAL-GATE"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_REVIEW_DIGEST = (
    "d5112969c7ba2a6fa2f02f8da4e5d270"
    "1f8426d60d0355c2906d84d960f632ba"
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

EXPECTED_DRAFT_ID = (
    "xr11-x-draft-public-url-"
    "4842647be85ea1d60aab47fd"
)

EXPECTED_TEXT_SHA = (
    "4842647be85ea1d60aab47fd159b85ee"
    "ef23c9632809a617fc2f49c21586e7af"
)

EXPECTED_PUBLIC_URL = (
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
)

EXPECTED_LITERAL_CHARACTER_COUNT = 160
EXPECTED_TCO_CHARACTER_COUNT = 117
EXPECTED_CHECK_COUNT = 10

APPROVAL_REQUEST_ID = (
    "xr11-x-final-review-"
    "d5112969c7ba2a6fa2f02f8d"
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


class XDraftFinalReviewApprovalError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XDraftFinalReviewApprovalError(
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
        raise XDraftFinalReviewApprovalError(
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
    require(
        value.get(digest_field)
        == expected_digest,
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
                "remain pending before approval"
            ),
        )

        check_ids.append(check_id)

    require(
        len(set(check_ids))
        == EXPECTED_CHECK_COUNT,
        "final review check IDs are not unique",
    )


def validate_draft(
    value: Any,
) -> None:
    require(
        isinstance(value, dict),
        "final X draft evidence is missing",
    )

    require(
        value.get("draft_id")
        == EXPECTED_DRAFT_ID,
        "final X draft ID mismatch",
    )

    require(
        value.get("revision")
        == "PUBLIC_URL_BOUND_V1",
        "final X draft revision mismatch",
    )

    require(
        value.get("text")
        == EXPECTED_FINAL_TEXT,
        "final X draft text mismatch",
    )

    require(
        value.get("text_sha256")
        == EXPECTED_TEXT_SHA,
        "final X draft SHA mismatch",
    )

    require(
        value.get(
            "literal_character_count"
        )
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "literal character count mismatch",
    )

    require(
        value.get(
            "estimated_tco_character_count"
        )
        == EXPECTED_TCO_CHARACTER_COUNT,
        "estimated t.co count mismatch",
    )

    require(
        value.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "final X draft public URL mismatch",
    )

    require(
        value.get("public_url_count")
        == 1,
        "final X draft public URL count mismatch",
    )

    require(
        value.get(
            "public_url_placeholder_absent"
        )
        is True,
        "public URL placeholder remains",
    )

    require(
        value.get("hashtags")
        == [
            "#のあ先輩はともだち",
            "#コミック新刊",
        ],
        "final X draft hashtags mismatch",
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
        "generation lock type mismatch",
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
        value.get(
            "replacement_x_draft_id"
        )
        == EXPECTED_DRAFT_ID,
        "generation lock draft ID mismatch",
    )

    require(
        value.get(
            "replacement_text_sha256"
        )
        == EXPECTED_TEXT_SHA,
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
        "generation lock is incomplete",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "generation lock permits rerun",
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
        raise XDraftFinalReviewApprovalError(
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
    replacement_text_path: Path,
    generation_lock_path: Path,
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

    replacement_text_path = (
        replacement_text_path.resolve()
    )

    generation_lock_path = (
        generation_lock_path.resolve()
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

    require(
        replacement_text_path.is_file(),
        "final X draft text file is missing",
    )

    require(
        sha256_file(
            replacement_text_path
        )
        == EXPECTED_TEXT_SHA,
        "final X draft text file SHA mismatch",
    )

    require(
        replacement_text_path.read_text(
            encoding="utf-8"
        )
        == EXPECTED_FINAL_TEXT,
        "final X draft text file content mismatch",
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
            "x_draft_final_human_review_"
            "prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_REVIEW_DIGEST
        ),
        label="final X draft human review prep",
    )

    require(
        review.get("status")
        == (
            "PASS_X_DRAFT_FINAL_HUMAN_"
            "REVIEW_PREP_READY"
        ),
        "final human review prep status mismatch",
    )

    require(
        review.get("human_review_state")
        == (
            "AWAITING_EXPLICIT_HUMAN_"
            "FINAL_X_DRAFT_DECISION"
        ),
        "final human review state mismatch",
    )

    require(
        review.get(
            "source_replacement_pack_"
            "digest_sha256"
        )
        == EXPECTED_REPLACEMENT_PACK_DIGEST,
        "source replacement pack digest mismatch",
    )

    require(
        review.get(
            "source_wording_gate_digest_sha256"
        )
        == EXPECTED_WORDING_GATE_DIGEST,
        "source wording gate digest mismatch",
    )

    require(
        review.get(
            "source_publication_verification_"
            "digest_sha256"
        )
        == EXPECTED_PUBLICATION_VERIFICATION_DIGEST,
        (
            "source publication verification "
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
        "final human decision is not pending",
    )

    require(
        review.get(
            "final_human_review_required"
        )
        is True,
        "final human review is not required",
    )

    require(
        review.get(
            "final_human_review_completed"
        )
        is False,
        "final human review is already complete",
    )

    require(
        review.get(
            "x_final_review_approval_issued"
        )
        is False,
        "final review approval was already issued",
    )

    require(
        review.get(
            "x_final_review_approval_consumed"
        )
        is False,
        "final review approval was already consumed",
    )

    require(
        review.get(
            "x_post_approval_issued"
        )
        is False,
        "X post approval was already issued",
    )

    require(
        review.get(
            "manual_x_posting_allowed"
        )
        is False,
        "manual X posting is already allowed",
    )

    require(
        review.get(
            "x_post_execution_allowed"
        )
        is False,
        "X execution is already allowed",
    )

    for field in (
        "normal_x_fb_write",
        "wordpress_api_call",
        "wordpress_write",
        "database_write",
        "workflow_write",
        "x_api_call",
        "x_post",
    ):
        require(
            review.get(field)
            is False,
            (
                "review pack records an "
                f"unexpected action: {field}"
            ),
        )

    require(
        review.get("production_status")
        == "NO_GO",
        "review production status mismatch",
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
        "replacement_pack_digest_verified",
        "generation_lock_verified",
        "wording_approval_verified",
        "wordpress_publication_verified",
        "text_sha256_verified",
        "public_url_verified",
        "public_url_placeholder_absent",
        "character_count_verified",
        "hashtags_verified",
        "x_execution_blocked",
    ):
        require(
            machine_precheck.get(field)
            is True,
            f"machine precheck failed: {field}",
        )

    checklist = review.get(
        "human_review_checklist"
    )

    validate_pending_checklist(
        checklist
    )

    draft = review.get(
        "x_draft"
    )

    validate_draft(
        draft
    )

    require(
        Path(
            draft["text_path"]
        ).resolve()
        == replacement_text_path,
        "final X draft text path mismatch",
    )

    generation_lock = load_json(
        generation_lock_path
    )

    validate_generation_lock(
        generation_lock
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
            "X-DRAFT-FINAL-REVIEW-"
            "EXPLICIT-APPROVAL"
        ),
        "status": (
            "X_DRAFT_FINAL_REVIEW_APPROVAL_"
            "ISSUED_NOT_CONSUMED"
        ),
        "issued_at": approved_at,
        "approval_request_id": (
            APPROVAL_REQUEST_ID
        ),
        "approval_label": approval_label,
        "approval_scope": APPROVAL_SCOPE,
        "source_review_pack_path": str(
            review_pack_path
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "source_replacement_pack_digest_sha256": (
            EXPECTED_REPLACEMENT_PACK_DIGEST
        ),
        "source_wording_gate_digest_sha256": (
            EXPECTED_WORDING_GATE_DIGEST
        ),
        "source_publication_verification_digest_sha256": (
            EXPECTED_PUBLICATION_VERIFICATION_DIGEST
        ),
        "x_draft_id": EXPECTED_DRAFT_ID,
        "x_draft_text_path": str(
            replacement_text_path
        ),
        "x_draft_text_sha256": (
            EXPECTED_TEXT_SHA
        ),
        "x_draft_text": (
            EXPECTED_FINAL_TEXT
        ),
        "public_url": (
            EXPECTED_PUBLIC_URL
        ),
        "literal_character_count": (
            EXPECTED_LITERAL_CHARACTER_COUNT
        ),
        "estimated_tco_character_count": (
            EXPECTED_TCO_CHARACTER_COUNT
        ),
        "human_decision": "APPROVED",
        "final_human_review_completed": True,
        "approved_check_count": (
            EXPECTED_CHECK_COUNT
        ),
        "human_review_checklist": (
            approved_checklist
        ),
        "local_finalization_runner_allowed": True,
        "approval_consumed": False,
        "local_finalization_executed": False,
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
            "FINAL_X_DRAFT_REVIEW_APPROVED_"
            "LOCAL_FINALIZATION_NOT_EXECUTED_"
            "X_POST_BLOCKED"
        ),
    }

    certificate = {
        **certificate_payload,
        "x_draft_final_review_approval_"
        "certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    gate_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_DRAFT_FINAL_REVIEW_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "approval_gate_state": (
            "READY_AWAITING_ONE_SHOT_"
            "LOCAL_X_DRAFT_FINALIZATION"
        ),
        "generated_at": approved_at,
        "approval_request_id": (
            APPROVAL_REQUEST_ID
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
                "x_draft_final_review_approval_"
                "certificate_digest_sha256"
            ]
        ),
        "human_decision": "APPROVED",
        "final_human_review_completed": True,
        "x_final_review_approval_issued": True,
        "x_final_review_approval_consumed": False,
        "local_finalization_runner_allowed": True,
        "x_draft": {
            "draft_id": (
                EXPECTED_DRAFT_ID
            ),
            "text_path": str(
                replacement_text_path
            ),
            "text_sha256": (
                EXPECTED_TEXT_SHA
            ),
            "literal_character_count": (
                EXPECTED_LITERAL_CHARACTER_COUNT
            ),
            "estimated_tco_character_count": (
                EXPECTED_TCO_CHARACTER_COUNT
            ),
            "public_url": (
                EXPECTED_PUBLIC_URL
            ),
        },
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
            "FINAL_X_DRAFT_REVIEW_APPROVED_"
            "ONE_LOCAL_FINALIZATION_ALLOWED_"
            "X_POST_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-DRAFT-FINAL-REVIEW-"
            "LOCAL-FINALIZATION-ONE-SHOT"
        ),
    }

    gate = {
        **gate_payload,
        "x_draft_final_review_explicit_"
        "approval_gate_digest_sha256": (
            canonical_digest(
                gate_payload
            )
        ),
    }

    issuance_lock_payload = {
        "lock_type": (
            "X_R11_X_DRAFT_FINAL_REVIEW_"
            "APPROVAL_ISSUANCE"
        ),
        "created_at": approved_at,
        "approval_request_id": (
            APPROVAL_REQUEST_ID
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_label": approval_label,
        "approval_scope": APPROVAL_SCOPE,
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "x_draft_final_review_approval_"
                "certificate_digest_sha256"
            ]
        ),
        "approval_gate_pack_path": str(
            approval_gate_pack_path
        ),
        "approval_gate_digest_sha256": (
            gate[
                "x_draft_final_review_explicit_"
                "approval_gate_digest_sha256"
            ]
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "reissuance_allowed": False,
        "x_post_allowed": False,
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
            replacement_text_path=(
                args.replacement_text
            ),
            generation_lock_path=(
                args.generation_lock
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
                        "FAIL_X_DRAFT_FINAL_REVIEW_"
                        "EXPLICIT_APPROVAL_GATE"
                    ),
                    "error": str(exc),
                    "x_final_review_approval_issued": False,
                    "x_post_approval_issued": False,
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
                "x_draft_id": (
                    result[
                        "x_draft"
                    ]["draft_id"]
                ),
                "x_draft_text_sha256": (
                    result[
                        "x_draft"
                    ]["text_sha256"]
                ),
                "human_decision": "APPROVED",
                "final_human_review_completed": True,
                "x_final_review_approval_issued": True,
                "x_final_review_approval_consumed": False,
                "local_finalization_runner_allowed": True,
                "x_post_approval_issued": False,
                "manual_x_posting_allowed": False,
                "x_post_execution_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
                "approval_gate_pack_path": str(
                    args.approval_gate_pack.resolve()
                ),
                "approval_gate_digest_sha256": (
                    result[
                        "x_draft_final_review_"
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
