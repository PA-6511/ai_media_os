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
    "X-MANUAL-POSTING-EXPLICIT-APPROVAL-GATE"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_READINESS_DIGEST = (
    "07ffca16168ffed8c5146e9b85642839"
    "783cebc71332e543b72385c04e58beb7"
)

EXPECTED_FINALIZATION_PACK_DIGEST = (
    "1caec5d697a00e5bae41f38ffec317a3"
    "0ff365e98e5d42697020d4ebf98ecd1c"
)

MANUAL_POSTING_REQUEST_ID = (
    "xr11-x-manual-posting-"
    "1caec5d697a00e5bae41f38f"
)

EXPECTED_DRAFT_ID = (
    "xr11-x-draft-public-url-"
    "4842647be85ea1d60aab47fd"
)

EXPECTED_FINALIZATION_ID = (
    "xr11-x-finalized-local-"
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
EXPECTED_CHECK_COUNT = 12

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_"
    "MANUAL_X_POSTING_ONLY"
)

APPROVAL_SCOPE = (
    "ONE_MANUAL_X_POST_EXACT_FROZEN_TEXT_ONLY_"
    "PAID_PARTNERSHIP_DISCLOSURE_REQUIRED"
)

RELATIONSHIP_ATTESTATION = (
    "RAKUTEN_STANDARD_AFFILIATE_"
    "COMMISSION_ONLY_NO_SPECIAL_CAMPAIGN"
)

DISCLOSURE_ATTESTATION = (
    "X_PAID_PARTNERSHIP_"
    "DISCLOSURE_AVAILABLE"
)

OFFICIAL_SURFACE_ATTESTATION = (
    "X_WEB_OR_OFFICIAL_APP_"
    "HUMAN_OPERATION_ONLY"
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

RUNTIME_CHECK_IDS = {
    "X_PAID_PARTNERSHIP_DISCLOSURE",
    "DISCLOSURE_VISIBLE_BEFORE_POST",
}

POST_EXECUTION_CHECK_IDS = {
    "POST_EVIDENCE_CAPTURE",
}


class XManualPostingApprovalError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XManualPostingApprovalError(
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
        raise XManualPostingApprovalError(
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
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise XManualPostingApprovalError(
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


def validate_x_account_handle(
    value: str,
) -> None:
    require(
        bool(
            re.fullmatch(
                r"@[A-Za-z0-9_]{1,64}",
                value,
            )
        ),
        (
            "X account handle must begin with @ "
            "and contain only letters, numbers, "
            "or underscore"
        ),
    )


def validate_attestations(
    *,
    relationship_attestation: str,
    disclosure_attestation: str,
    official_surface_attestation: str,
) -> None:
    require(
        relationship_attestation
        == RELATIONSHIP_ATTESTATION,
        "Rakuten relationship attestation mismatch",
    )

    require(
        disclosure_attestation
        == DISCLOSURE_ATTESTATION,
        "X disclosure attestation mismatch",
    )

    require(
        official_surface_attestation
        == OFFICIAL_SURFACE_ATTESTATION,
        "official X surface attestation mismatch",
    )


def validate_finalized_text(
    path: Path,
) -> None:
    require(
        path.is_file(),
        "finalized X draft text is missing",
    )

    require(
        sha256_file(path)
        == EXPECTED_TEXT_SHA,
        "finalized X draft SHA mismatch",
    )

    text = path.read_text(
        encoding="utf-8"
    )

    require(
        text == EXPECTED_FINAL_TEXT,
        "finalized X draft content mismatch",
    )

    require(
        len(text)
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "literal character count mismatch",
    )

    require(
        text.count(
            EXPECTED_PUBLIC_URL
        )
        == 1,
        "public URL count mismatch",
    )

    require(
        "{{WORDPRESS_PUBLIC_URL}}"
        not in text,
        "public URL placeholder remains",
    )


def validate_pending_checklist(
    value: Any,
) -> list[dict[str, Any]]:
    require(
        isinstance(value, list),
        "manual posting checklist must be a list",
    )

    require(
        len(value)
        == EXPECTED_CHECK_COUNT,
        "manual posting checklist count mismatch",
    )

    check_ids: set[str] = set()

    for item in value:
        require(
            isinstance(item, dict),
            "manual posting checklist item is invalid",
        )

        check_id = item.get(
            "check_id"
        )

        require(
            isinstance(check_id, str)
            and check_id,
            "manual posting check ID is missing",
        )

        require(
            item.get("human_decision")
            == "PENDING",
            (
                "manual posting checks must remain "
                "pending before approval"
            ),
        )

        require(
            item.get("blocking")
            is True,
            "manual posting check must be blocking",
        )

        check_ids.add(check_id)

    require(
        len(check_ids)
        == EXPECTED_CHECK_COUNT,
        "manual posting check IDs are not unique",
    )

    require(
        RUNTIME_CHECK_IDS.issubset(
            check_ids
        ),
        "runtime disclosure checks are missing",
    )

    require(
        POST_EXECUTION_CHECK_IDS.issubset(
            check_ids
        ),
        "post-execution evidence check is missing",
    )

    return value


def build_conditionally_approved_checklist(
    checklist: list[dict[str, Any]],
    *,
    x_account_handle: str,
) -> list[dict[str, Any]]:
    approved: list[dict[str, Any]] = []

    for item in checklist:
        check_id = item["check_id"]

        result = dict(item)

        if check_id in RUNTIME_CHECK_IDS:
            result[
                "human_decision"
            ] = "REQUIRED_AT_MANUAL_EXECUTION"

        elif check_id in POST_EXECUTION_CHECK_IDS:
            result[
                "human_decision"
            ] = "REQUIRED_AFTER_POST"

        else:
            result[
                "human_decision"
            ] = "APPROVED"

        if check_id == "X_ACCOUNT_IDENTITY":
            result[
                "verified_x_account_handle"
            ] = x_account_handle

        if check_id == (
            "RAKUTEN_RELATIONSHIP_CLASSIFICATION"
        ):
            result[
                "verified_relationship"
            ] = RELATIONSHIP_ATTESTATION

        approved.append(result)

    return approved


def validate_approved_checklist(
    value: list[dict[str, Any]],
) -> None:
    approved_count = sum(
        item.get("human_decision")
        == "APPROVED"
        for item in value
    )

    runtime_count = sum(
        item.get("human_decision")
        == "REQUIRED_AT_MANUAL_EXECUTION"
        for item in value
    )

    post_count = sum(
        item.get("human_decision")
        == "REQUIRED_AFTER_POST"
        for item in value
    )

    require(
        approved_count == 9,
        "approved pre-post check count mismatch",
    )

    require(
        runtime_count == 2,
        "runtime disclosure check count mismatch",
    )

    require(
        post_count == 1,
        "post-execution check count mismatch",
    )


def validate_evidence_template(
    value: dict[str, Any],
) -> None:
    require(
        value.get("status")
        == "PENDING_MANUAL_X_POST",
        "manual evidence status mismatch",
    )

    require(
        value.get(
            "manual_posting_request_id"
        )
        == MANUAL_POSTING_REQUEST_ID,
        "manual evidence request ID mismatch",
    )

    require(
        value.get(
            "expected_text_sha256"
        )
        == EXPECTED_TEXT_SHA,
        "manual evidence expected SHA mismatch",
    )

    require(
        value.get(
            "expected_public_url"
        )
        == EXPECTED_PUBLIC_URL,
        "manual evidence public URL mismatch",
    )

    require(
        value.get(
            "expected_paid_partnership_disclosure"
        )
        is True,
        "paid partnership disclosure is not required",
    )

    for field in (
        "posted_at_utc",
        "x_post_url",
        "x_post_id",
        "x_account_handle",
        "posting_surface",
        "actual_text_sha256",
        "paid_partnership_disclosure_enabled",
        "paid_partnership_label_visible",
        "screenshot_evidence_path",
        "human_verified_exact_text",
        "human_verified_public_url",
        "human_verified_post_visible",
    ):
        require(
            value.get(field) is None,
            (
                "manual evidence template was "
                f"prematurely populated: {field}"
            ),
        )

    require(
        value.get(
            "normal_x_fb_registration_completed"
        )
        is False,
        "normal X-FB registration already completed",
    )

    require(
        value.get("x_api_call")
        is False,
        "manual evidence records X API use",
    )


def validate_readiness_pack(
    value: dict[str, Any],
    *,
    finalized_text_path: Path,
    evidence_template_path: Path,
) -> list[dict[str, Any]]:
    verify_digest(
        value,
        digest_field=(
            "x_manual_posting_readiness_"
            "prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_READINESS_DIGEST
        ),
        label="manual posting readiness pack",
    )

    require(
        value.get("status")
        == (
            "PASS_X_MANUAL_POSTING_"
            "READINESS_PREP_READY"
        ),
        "manual posting readiness status mismatch",
    )

    require(
        value.get("readiness_state")
        == (
            "AWAITING_EXPLICIT_HUMAN_"
            "MANUAL_X_POSTING_DECISION"
        ),
        "manual posting readiness state mismatch",
    )

    require(
        value.get(
            "manual_posting_request_id"
        )
        == MANUAL_POSTING_REQUEST_ID,
        "manual posting request ID mismatch",
    )

    require(
        value.get(
            "source_finalization_pack_"
            "digest_sha256"
        )
        == EXPECTED_FINALIZATION_PACK_DIGEST,
        "source finalization digest mismatch",
    )

    require(
        Path(
            value[
                "post_execution_"
                "evidence_template_path"
            ]
        ).resolve()
        == evidence_template_path,
        "evidence template path mismatch",
    )

    draft = value.get(
        "finalized_x_draft"
    )

    require(
        isinstance(draft, dict),
        "finalized X draft evidence is missing",
    )

    require(
        draft.get("draft_id")
        == EXPECTED_DRAFT_ID,
        "finalized X draft ID mismatch",
    )

    require(
        draft.get("finalization_id")
        == EXPECTED_FINALIZATION_ID,
        "finalization ID mismatch",
    )

    require(
        draft.get("text")
        == EXPECTED_FINAL_TEXT,
        "readiness X draft text mismatch",
    )

    require(
        draft.get("text_sha256")
        == EXPECTED_TEXT_SHA,
        "readiness X draft SHA mismatch",
    )

    require(
        Path(
            draft["text_path"]
        ).resolve()
        == finalized_text_path,
        "finalized X draft path mismatch",
    )

    require(
        draft.get("wording_frozen")
        is True,
        "X draft wording is not frozen",
    )

    policy = value.get(
        "compliance_policy_snapshot"
    )

    require(
        isinstance(policy, dict),
        "compliance policy snapshot is missing",
    )

    require(
        policy.get(
            "x_paid_partnership_"
            "disclosure_required"
        )
        is True,
        "X paid partnership disclosure is not required",
    )

    require(
        policy.get(
            "rakuten_basic_function_only_"
            "confirmation_required"
        )
        is True,
        "Rakuten relationship confirmation missing",
    )

    require(
        policy.get(
            "rakuten_special_campaign_stop_rule"
        )
        is True,
        "Rakuten special campaign stop rule missing",
    )

    constraints = value.get(
        "manual_posting_constraints"
    )

    require(
        isinstance(constraints, dict),
        "manual posting constraints are missing",
    )

    required_true_fields = (
        "human_operation_only",
        "x_web_or_official_app_only",
        "exact_frozen_text_required",
        "x_paid_partnership_disclosure_required",
        "stop_if_disclosure_unavailable",
        "stop_if_special_rakuten_campaign",
    )

    for field in required_true_fields:
        require(
            constraints.get(field) is True,
            f"manual posting constraint missing: {field}",
        )

    require(
        constraints.get("text_edit_allowed")
        is False,
        "text editing is allowed",
    )

    require(
        constraints.get("url_edit_allowed")
        is False,
        "URL editing is allowed",
    )

    require(
        constraints.get("hashtag_edit_allowed")
        is False,
        "hashtag editing is allowed",
    )

    require(
        constraints.get("x_api_allowed")
        is False,
        "X API is allowed",
    )

    require(
        constraints.get("browser_automation_allowed")
        is False,
        "browser automation is allowed",
    )

    require(
        constraints.get("maximum_manual_post_count")
        == 1,
        "manual post count limit mismatch",
    )

    require(
        value.get("human_decision")
        == "PENDING",
        "manual posting decision is not pending",
    )

    require(
        value.get(
            "manual_posting_review_completed"
        )
        is False,
        "manual posting review already completed",
    )

    require(
        value.get(
            "manual_posting_approval_issued"
        )
        is False,
        "manual posting approval already issued",
    )

    require(
        value.get(
            "manual_x_posting_allowed"
        )
        is False,
        "manual X posting already allowed",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "automated X execution already allowed",
    )

    require(
        value.get("x_api_call")
        is False,
        "readiness pack records X API use",
    )

    require(
        value.get("x_post")
        is False,
        "readiness pack records an X post",
    )

    return validate_pending_checklist(
        value.get(
            "manual_posting_checklist"
        )
    )


def validate_finalization_pack(
    value: dict[str, Any],
) -> None:
    verify_digest(
        value,
        digest_field=(
            "x_draft_final_review_local_"
            "finalization_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_FINALIZATION_PACK_DIGEST
        ),
        label="local finalization pack",
    )

    require(
        value.get("status")
        == (
            "PASS_X_DRAFT_FINAL_REVIEW_"
            "LOCAL_FINALIZATION_ONE_SHOT"
        ),
        "local finalization status mismatch",
    )

    require(
        value.get("finalization_id")
        == EXPECTED_FINALIZATION_ID,
        "local finalization ID mismatch",
    )

    require(
        value.get(
            "x_final_review_approval_consumed"
        )
        is True,
        "final review approval was not consumed",
    )

    require(
        value.get(
            "local_finalization_executed"
        )
        is True,
        "local finalization was not executed",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "local finalization permits rerun",
    )

    require(
        value.get(
            "x_post_approval_issued"
        )
        is False,
        "X posting approval already issued",
    )

    require(
        value.get(
            "manual_x_posting_allowed"
        )
        is False,
        "manual X posting already allowed",
    )

    require(
        value.get("x_api_call")
        is False,
        "finalization pack records X API use",
    )

    require(
        value.get("x_post")
        is False,
        "finalization pack records X posting",
    )


def build_approval_gate(
    *,
    production_database_path: Path,
    readiness_pack_path: Path,
    finalization_pack_path: Path,
    finalized_text_path: Path,
    evidence_template_path: Path,
    approval_label: str,
    x_account_handle: str,
    relationship_attestation: str,
    disclosure_attestation: str,
    official_surface_attestation: str,
    approval_certificate_path: Path,
    approval_gate_path: Path,
    issuance_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    readiness_pack_path = (
        readiness_pack_path.resolve()
    )

    finalization_pack_path = (
        finalization_pack_path.resolve()
    )

    finalized_text_path = (
        finalized_text_path.resolve()
    )

    evidence_template_path = (
        evidence_template_path.resolve()
    )

    approval_certificate_path = (
        approval_certificate_path.resolve()
    )

    approval_gate_path = (
        approval_gate_path.resolve()
    )

    issuance_lock_path = (
        issuance_lock_path.resolve()
    )

    validate_approval_label(
        approval_label
    )

    validate_x_account_handle(
        x_account_handle
    )

    validate_attestations(
        relationship_attestation=(
            relationship_attestation
        ),
        disclosure_attestation=(
            disclosure_attestation
        ),
        official_surface_attestation=(
            official_surface_attestation
        ),
    )

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    validate_finalized_text(
        finalized_text_path
    )

    readiness = load_json(
        readiness_pack_path
    )

    pending_checklist = (
        validate_readiness_pack(
            readiness,
            finalized_text_path=(
                finalized_text_path
            ),
            evidence_template_path=(
                evidence_template_path
            ),
        )
    )

    finalization = load_json(
        finalization_pack_path
    )

    validate_finalization_pack(
        finalization
    )

    evidence_template = load_json(
        evidence_template_path
    )

    validate_evidence_template(
        evidence_template
    )

    for path, label in (
        (
            approval_certificate_path,
            "manual posting approval certificate",
        ),
        (
            approval_gate_path,
            "manual posting approval gate",
        ),
        (
            issuance_lock_path,
            "manual posting issuance lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    reviewed_checklist = (
        build_conditionally_approved_checklist(
            pending_checklist,
            x_account_handle=x_account_handle,
        )
    )

    validate_approved_checklist(
        reviewed_checklist
    )

    issued_at = datetime.now(
        timezone.utc
    ).isoformat()

    certificate_payload = {
        "phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-MANUAL-POSTING-EXPLICIT-APPROVAL"
        ),
        "status": (
            "X_MANUAL_POSTING_APPROVAL_"
            "ISSUED_NOT_CONSUMED"
        ),
        "issued_at": issued_at,
        "manual_posting_request_id": (
            MANUAL_POSTING_REQUEST_ID
        ),
        "approval_label": approval_label,
        "approval_scope": APPROVAL_SCOPE,
        "source_readiness_pack_path": str(
            readiness_pack_path
        ),
        "source_readiness_digest_sha256": (
            EXPECTED_READINESS_DIGEST
        ),
        "source_finalization_pack_path": str(
            finalization_pack_path
        ),
        "source_finalization_pack_digest_sha256": (
            EXPECTED_FINALIZATION_PACK_DIGEST
        ),
        "evidence_template_path": str(
            evidence_template_path
        ),
        "evidence_template_sha256": (
            sha256_file(
                evidence_template_path
            )
        ),
        "x_account_handle": (
            x_account_handle
        ),
        "relationship_attestation": (
            relationship_attestation
        ),
        "disclosure_attestation": (
            disclosure_attestation
        ),
        "official_surface_attestation": (
            official_surface_attestation
        ),
        "x_draft_id": EXPECTED_DRAFT_ID,
        "finalization_id": (
            EXPECTED_FINALIZATION_ID
        ),
        "x_draft_text_path": str(
            finalized_text_path
        ),
        "x_draft_text_sha256": (
            EXPECTED_TEXT_SHA
        ),
        "x_draft_text": (
            EXPECTED_FINAL_TEXT
        ),
        "public_url": EXPECTED_PUBLIC_URL,
        "literal_character_count": (
            EXPECTED_LITERAL_CHARACTER_COUNT
        ),
        "estimated_tco_character_count": (
            EXPECTED_TCO_CHARACTER_COUNT
        ),
        "human_decision": (
            "APPROVED_CONDITIONALLY_"
            "FOR_ONE_MANUAL_X_POST"
        ),
        "manual_posting_review_completed": True,
        "manual_posting_checklist": (
            reviewed_checklist
        ),
        "approved_pre_post_check_count": 9,
        "runtime_disclosure_check_count": 2,
        "post_execution_check_count": 1,
        "runtime_paid_partnership_disclosure_required": True,
        "runtime_paid_partnership_label_visibility_required": True,
        "post_execution_evidence_required": True,
        "manual_posting_approval_issued": True,
        "manual_posting_approval_consumed": False,
        "one_manual_post_allowed": True,
        "maximum_manual_post_count": 1,
        "manual_x_posting_allowed": True,
        "automated_x_posting_allowed": False,
        "x_post_execution_allowed": False,
        "text_edit_allowed": False,
        "url_edit_allowed": False,
        "hashtag_edit_allowed": False,
        "media_attachment_allowed": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "browser_automation": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_MANUAL_X_POST_CONDITIONALLY_APPROVED_"
            "RUNTIME_DISCLOSURE_CHECKS_REQUIRED_"
            "NO_API_NO_AUTOMATION"
        ),
    }

    certificate = {
        **certificate_payload,
        "x_manual_posting_approval_"
        "certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    gate_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_MANUAL_POSTING_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "approval_gate_state": (
            "ONE_MANUAL_X_POST_CONDITIONALLY_AUTHORIZED_"
            "AWAITING_HUMAN_EXECUTION"
        ),
        "generated_at": issued_at,
        "manual_posting_request_id": (
            MANUAL_POSTING_REQUEST_ID
        ),
        "source_readiness_pack_path": str(
            readiness_pack_path
        ),
        "source_readiness_digest_sha256": (
            EXPECTED_READINESS_DIGEST
        ),
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "x_manual_posting_approval_"
                "certificate_digest_sha256"
            ]
        ),
        "x_account_handle": (
            x_account_handle
        ),
        "x_draft": {
            "draft_id": EXPECTED_DRAFT_ID,
            "finalization_id": (
                EXPECTED_FINALIZATION_ID
            ),
            "text_path": str(
                finalized_text_path
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
            "public_url": EXPECTED_PUBLIC_URL,
            "wording_frozen": True,
        },
        "manual_posting_approval_issued": True,
        "manual_posting_approval_consumed": False,
        "one_manual_post_allowed": True,
        "maximum_manual_post_count": 1,
        "manual_x_posting_allowed": True,
        "runtime_paid_partnership_disclosure_required": True,
        "runtime_paid_partnership_label_visibility_required": True,
        "post_execution_evidence_required": True,
        "automated_x_posting_allowed": False,
        "x_post_execution_allowed": False,
        "normal_x_fb_write": False,
        "browser_automation": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "authorized_next_action": (
            "HUMAN_MANUAL_X_POST_ONCE_WITH_"
            "PAID_PARTNERSHIP_DISCLOSURE"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-MANUAL-POSTING-"
            "POST-EXECUTION-EVIDENCE-REGISTRATION"
        ),
    }

    gate = {
        **gate_payload,
        "x_manual_posting_explicit_"
        "approval_gate_digest_sha256": (
            canonical_digest(
                gate_payload
            )
        ),
    }

    issuance_lock = {
        "lock_type": (
            "X_R11_MANUAL_X_POSTING_"
            "APPROVAL_ISSUANCE"
        ),
        "created_at": issued_at,
        "manual_posting_request_id": (
            MANUAL_POSTING_REQUEST_ID
        ),
        "source_readiness_digest_sha256": (
            EXPECTED_READINESS_DIGEST
        ),
        "approval_label": approval_label,
        "approval_scope": APPROVAL_SCOPE,
        "x_account_handle": (
            x_account_handle
        ),
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "x_manual_posting_approval_"
                "certificate_digest_sha256"
            ]
        ),
        "approval_gate_path": str(
            approval_gate_path
        ),
        "approval_gate_digest_sha256": (
            gate[
                "x_manual_posting_explicit_"
                "approval_gate_digest_sha256"
            ]
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "manual_post_count_allowed": 1,
        "manual_post_count_recorded": 0,
        "reissuance_allowed": False,
        "manual_x_posting_allowed": True,
        "x_api_allowed": False,
        "browser_automation_allowed": False,
    }

    atomic_create_json(
        approval_certificate_path,
        certificate,
    )

    atomic_create_json(
        approval_gate_path,
        gate,
    )

    atomic_create_json(
        issuance_lock_path,
        issuance_lock,
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
        "--readiness-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--finalization-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--finalized-text",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--evidence-template",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-label",
        required=True,
    )

    parser.add_argument(
        "--x-account-handle",
        required=True,
    )

    parser.add_argument(
        "--relationship-attestation",
        required=True,
    )

    parser.add_argument(
        "--disclosure-attestation",
        required=True,
    )

    parser.add_argument(
        "--official-surface-attestation",
        required=True,
    )

    parser.add_argument(
        "--approval-certificate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-gate",
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
        result = build_approval_gate(
            production_database_path=(
                args.production_db
            ),
            readiness_pack_path=(
                args.readiness_pack
            ),
            finalization_pack_path=(
                args.finalization_pack
            ),
            finalized_text_path=(
                args.finalized_text
            ),
            evidence_template_path=(
                args.evidence_template
            ),
            approval_label=(
                args.approval_label
            ),
            x_account_handle=(
                args.x_account_handle
            ),
            relationship_attestation=(
                args.relationship_attestation
            ),
            disclosure_attestation=(
                args.disclosure_attestation
            ),
            official_surface_attestation=(
                args.official_surface_attestation
            ),
            approval_certificate_path=(
                args.approval_certificate
            ),
            approval_gate_path=(
                args.approval_gate
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
                        "FAIL_X_MANUAL_POSTING_"
                        "EXPLICIT_APPROVAL_GATE"
                    ),
                    "error": str(exc),
                    "manual_posting_approval_issued": False,
                    "manual_x_posting_allowed": False,
                    "x_post_execution_allowed": False,
                    "browser_automation": False,
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
                "manual_posting_request_id": (
                    result[
                        "manual_posting_request_id"
                    ]
                ),
                "x_account_handle": (
                    result["x_account_handle"]
                ),
                "x_draft_id": (
                    result["x_draft"]["draft_id"]
                ),
                "x_draft_text_sha256": (
                    result[
                        "x_draft"
                    ]["text_sha256"]
                ),
                "manual_posting_approval_issued": True,
                "manual_posting_approval_consumed": False,
                "one_manual_post_allowed": True,
                "manual_x_posting_allowed": True,
                "runtime_paid_partnership_disclosure_required": True,
                "post_execution_evidence_required": True,
                "automated_x_posting_allowed": False,
                "x_post_execution_allowed": False,
                "browser_automation": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
                "approval_gate_path": str(
                    args.approval_gate.resolve()
                ),
                "approval_gate_digest_sha256": (
                    result[
                        "x_manual_posting_explicit_"
                        "approval_gate_digest_sha256"
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
