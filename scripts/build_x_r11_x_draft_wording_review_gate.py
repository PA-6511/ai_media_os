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
    "X-DRAFT-WORDING-REVIEW-GATE"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_REVIEW_DIGEST = (
    "0f1b0ae9ae069b5d9250074bb5543dfc"
    "95a680804b0319abe06e85665a092a1d"
)

EXPECTED_X_DRAFT_PACK_DIGEST = (
    "869143e190d896c80df3c0ec21df51e2"
    "9ba9528c4b3dbdb9f8b456119b5b76f7"
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
EXPECTED_CHECK_COUNT = 8

PUBLIC_URL_PLACEHOLDER = (
    "{{WORDPRESS_PUBLIC_URL}}"
)

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_X_DRAFT_"
    "WORDING_REVIEW_ONLY"
)

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


class XDraftWordingGateError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XDraftWordingGateError(
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
        raise XDraftWordingGateError(
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
            "human review checklist must "
            f"contain {EXPECTED_CHECK_COUNT} checks"
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
                "remain in pending state"
            ),
        )

        check_ids.append(check_id)

    require(
        len(set(check_ids))
        == EXPECTED_CHECK_COUNT,
        "human review check IDs are not unique",
    )


def validate_fixed_draft(
    draft: dict[str, Any],
) -> None:
    require(
        draft.get("draft_id")
        == EXPECTED_DRAFT_ID,
        "X draft ID mismatch",
    )

    text = draft.get("text")

    require(
        isinstance(text, str),
        "X draft text is missing",
    )

    require(
        text == EXPECTED_DRAFT_TEXT,
        "X draft text differs from fixed wording",
    )

    require(
        sha256_text(text)
        == EXPECTED_DRAFT_TEXT_SHA,
        "X draft text SHA mismatch",
    )

    require(
        draft.get("text_sha256")
        == EXPECTED_DRAFT_TEXT_SHA,
        "recorded X draft SHA mismatch",
    )

    require(
        text.count(
            PUBLIC_URL_PLACEHOLDER
        )
        == 1,
        (
            "public URL placeholder count "
            "must equal one"
        ),
    )

    require(
        "https://" not in text,
        (
            "literal public URL must not exist "
            "before WordPress publication"
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
        raise XDraftWordingGateError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_wording_gate(
    *,
    production_database_path: Path,
    review_pack_path: Path,
    approval_label: str,
    approval_certificate_path: Path,
    wording_gate_pack_path: Path,
    consumption_lock_path: Path,
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

    wording_gate_pack_path = (
        wording_gate_pack_path.resolve()
    )

    consumption_lock_path = (
        consumption_lock_path.resolve()
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
            wording_gate_pack_path,
            "wording gate pack",
        ),
        (
            consumption_lock_path,
            "consumption lock",
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
            "x_draft_human_review_prep_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_REVIEW_DIGEST
        ),
        label="X draft human review prep",
    )

    require(
        review.get("status")
        == (
            "PASS_X_DRAFT_HUMAN_"
            "REVIEW_PREP_READY"
        ),
        "X draft human review prep did not pass",
    )

    require(
        review.get("human_review_state")
        == (
            "AWAITING_EXPLICIT_HUMAN_"
            "WORDING_DECISION"
        ),
        "human review state mismatch",
    )

    require(
        review.get(
            "source_x_draft_pack_digest_sha256"
        )
        == EXPECTED_X_DRAFT_PACK_DIGEST,
        "source X draft pack digest mismatch",
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
        == "X_DRAFT_WORDING_REVIEW_ONLY",
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
            "wording_approval_issued"
        )
        is False,
        "wording approval was already issued",
    )

    require(
        review.get(
            "public_url_replacement_allowed"
        )
        is False,
        (
            "public URL replacement must "
            "remain blocked"
        ),
    )

    require(
        review.get(
            "x_post_execution_allowed"
        )
        is False,
        "X post execution must remain blocked",
    )

    require(
        review.get(
            "wordpress_publication_allowed"
        )
        is False,
        (
            "WordPress publication must "
            "remain blocked"
        ),
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
            "public_url_unresolved"
        )
        is True,
        "public URL must remain unresolved",
    )

    require(
        machine_precheck.get(
            "character_limit_passed"
        )
        is True,
        "X character-limit check did not pass",
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

    require(
        wordpress_post.get(
            "publication_allowed"
        )
        is False,
        "WordPress publication is not allowed",
    )

    draft = review.get(
        "x_draft"
    )

    require(
        isinstance(draft, dict),
        "X draft evidence is missing",
    )

    validate_fixed_draft(
        draft
    )

    approved_checklist = [
        {
            **item,
            "human_decision": "APPROVED",
        }
        for item in checklist
    ]

    approved_at = datetime.now(
        timezone.utc
    ).isoformat()

    certificate_payload = {
        "phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-DRAFT-WORDING-EXPLICIT-APPROVAL"
        ),
        "status": (
            "X_DRAFT_WORDING_REVIEW_"
            "APPROVAL_ISSUED_AND_CONSUMED"
        ),
        "issued_at": approved_at,
        "approval_label": approval_label,
        "approval_scope": (
            "X_DRAFT_WORDING_REVIEW_ONLY"
        ),
        "source_review_pack_path": str(
            review_pack_path
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "draft_id": EXPECTED_DRAFT_ID,
        "draft_text_sha256": (
            EXPECTED_DRAFT_TEXT_SHA
        ),
        "human_decision": "APPROVED",
        "human_review_completed": True,
        "human_review_checklist": (
            approved_checklist
        ),
        "approval_consumed": True,
        "public_url_replacement_allowed": False,
        "wordpress_publication_allowed": False,
        "x_post_execution_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "wordpress_write": False,
        "database_write": False,
        "production_status": "NO_GO",
    }

    certificate = {
        **certificate_payload,
        "x_draft_wording_review_approval_"
        "certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    gate_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_DRAFT_WORDING_REVIEW_"
            "APPROVED_PUBLIC_URL_PENDING"
        ),
        "wording_gate_state": (
            "WORDING_FIXED_AWAITING_"
            "WORDPRESS_PUBLICATION_AND_PUBLIC_URL"
        ),
        "generated_at": approved_at,
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
                "x_draft_wording_review_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "human_review": {
            "decision": "APPROVED",
            "completed": True,
            "approved_check_count": (
                EXPECTED_CHECK_COUNT
            ),
            "approval_label": approval_label,
            "approval_consumed": True,
        },
        "wordpress_post": {
            "post_id": EXPECTED_POST_ID,
            "status": "draft",
            "public_url_available": False,
            "publication_allowed": False,
        },
        "x_draft": {
            "draft_id": EXPECTED_DRAFT_ID,
            "text": EXPECTED_DRAFT_TEXT,
            "text_sha256": (
                EXPECTED_DRAFT_TEXT_SHA
            ),
            "public_url_placeholder": (
                PUBLIC_URL_PLACEHOLDER
            ),
            "wording_fixed": True,
        },
        "remaining_requirements": [
            "WORDPRESS_MEDIA_UPLOAD",
            "WORDPRESS_PUBLICATION_REVIEW",
            "WORDPRESS_PUBLICATION_APPROVAL",
            "WORDPRESS_PUBLIC_URL_VERIFICATION",
            "X_PUBLIC_URL_REPLACEMENT",
            "FINAL_X_REVIEW",
            "EXPLICIT_X_POST_APPROVAL",
        ],
        "public_url_replacement_allowed": False,
        "wordpress_media_upload_allowed": False,
        "wordpress_publication_allowed": False,
        "x_final_review_allowed": False,
        "x_post_approval_issued": False,
        "x_post_execution_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "production_status": "NO_GO",
        "safety_state": (
            "X_WORDING_FIXED_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-MEDIA-PUBLICATION-"
            "READINESS-PREP"
        ),
    }

    gate = {
        **gate_payload,
        "x_draft_wording_review_gate_"
        "digest_sha256": (
            canonical_digest(
                gate_payload
            )
        ),
    }

    lock_payload = {
        "lock_type": (
            "X_R11_X_DRAFT_WORDING_REVIEW_"
            "APPROVAL_CONSUMPTION"
        ),
        "created_at": approved_at,
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_label": approval_label,
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "x_draft_wording_review_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "wording_gate_pack_path": str(
            wording_gate_pack_path
        ),
        "wording_gate_digest_sha256": (
            gate[
                "x_draft_wording_review_gate_"
                "digest_sha256"
            ]
        ),
        "approval_consumed": True,
        "reexecution_allowed": False,
    }

    atomic_create_json(
        approval_certificate_path,
        certificate,
    )

    atomic_create_json(
        wording_gate_pack_path,
        gate,
    )

    atomic_create_json(
        consumption_lock_path,
        lock_payload,
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
        "--wording-gate-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--consumption-lock",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = build_wording_gate(
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
            wording_gate_pack_path=(
                args.wording_gate_pack
            ),
            consumption_lock_path=(
                args.consumption_lock
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_DRAFT_WORDING_"
                        "REVIEW_GATE"
                    ),
                    "error": str(exc),
                    "wording_approval_consumed": False,
                    "wordpress_publication_allowed": False,
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
                "wording_gate_state": (
                    result["wording_gate_state"]
                ),
                "draft_id": (
                    result["x_draft"]["draft_id"]
                ),
                "wordpress_post_id": 195,
                "wordpress_post_status": "draft",
                "human_decision": "APPROVED",
                "wording_approval_consumed": True,
                "wording_fixed": True,
                "public_url_available": False,
                "public_url_replacement_allowed": False,
                "wordpress_publication_allowed": False,
                "x_post_execution_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "wording_gate_pack_path": str(
                    args.wording_gate_pack.resolve()
                ),
                "wording_gate_digest_sha256": (
                    result[
                        "x_draft_wording_review_"
                        "gate_digest_sha256"
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
