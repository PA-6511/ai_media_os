from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
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
    "X-MANUAL-POSTING-CORRECTIVE-"
    "EVIDENCE-REGISTRATION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_READINESS_DIGEST = (
    "07ffca16168ffed8c5146e9b85642839"
    "783cebc71332e543b72385c04e58beb7"
)

EXPECTED_OLD_APPROVAL_GATE_DIGEST = (
    "ac8fbb29f3d1b0c365c5f6ac22fe54c0"
    "0c956ab308ff4bd7b28a8be3d3f35b08"
)

EXPECTED_FINALIZATION_PACK_DIGEST = (
    "1caec5d697a00e5bae41f38ffec317a3"
    "0ff365e98e5d42697020d4ebf98ecd1c"
)

EXPECTED_OLD_TEXT_SHA = (
    "4842647be85ea1d60aab47fd159b85ee"
    "ef23c9632809a617fc2f49c21586e7af"
)

EXPECTED_OLD_PUBLIC_URL = (
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
)

MANUAL_POSTING_REQUEST_ID = (
    "xr11-x-manual-posting-"
    "1caec5d697a00e5bae41f38f"
)

REVISION = (
    "CORRECTIVE_DIRECT_AFFILIATE_V1"
)

LINK_ROUTE = "DIRECT_AFFILIATE"
STORE = "RAKUTEN_KOBO"

EXPECTED_X_ACCOUNT_HANDLE = (
    "@mz_GK7_DM2"
)

EXPECTED_X_POST_ID = (
    "2078417820015333645"
)

EXPECTED_X_POST_URL = (
    "https://x.com/mz_GK7_DM2/"
    "status/2078417820015333645"
)

EXPECTED_AFFILIATE_URL = (
    "https://a.r10.to/hPKo3p"
)

EXPECTED_POSTED_AT_UTC = (
    "2026-07-18T09:53:18.084Z"
)

EXPECTED_SCREENSHOT_SHA256 = (
    "53ae94d796d73d98ec87c85b9dd2f05"
    "a15c6ad1d83d825c75b4e583de27006c0"
)

EXPECTED_SCREENSHOT_WIDTH = 598
EXPECTED_SCREENSHOT_HEIGHT = 373

EXPECTED_CORRECTIVE_TEXT = (
    "【PR・新刊】\n"
    "『のあ先輩はともだち。』"
    "11巻 配信開始📚\n"
    "あきやまえんま／集英社\n"
    "\n"
    "Kobo：https://a.r10.to/hPKo3p\n"
    "\n"
    "#のあ先輩はともだち "
    "#あきやまえんま"
)

EXPECTED_CORRECTIVE_TEXT_SHA = (
    "125481ce9a0a1ad8972c2f855e9d2bb5"
    "5f4e3215152ba6ba0fa626e489a81d67"
)

EXPECTED_LITERAL_CHARACTER_COUNT = 92
EXPECTED_TCO_CHARACTER_COUNT = 92

PAID_PARTNERSHIP_ATTESTATION = (
    "PAID_PARTNERSHIP_ON"
)

TEXT_ATTESTATION = (
    "SCREENSHOT_VISIBLE_CONTENT_CONSISTENT_"
    "WITH_CORRECTIVE_TRANSCRIPTION"
)

POST_VISIBLE_ATTESTATION = (
    "POST_VISIBLE_AT_SUPPLIED_X_URL"
)

SCREENSHOT_SOURCE = (
    "USER_PROVIDED_CHAT_ATTACHMENT_"
    "CAPTURE_8_PNG"
)

TWITTER_EPOCH_MS = 1288834974657


class CorrectiveEvidenceError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise CorrectiveEvidenceError(
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
        raise CorrectiveEvidenceError(
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
        raise CorrectiveEvidenceError(
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


def parse_x_post_url(
    value: str,
) -> tuple[str, str]:
    match = re.fullmatch(
        (
            r"https://x\.com/"
            r"([A-Za-z0-9_]+)/status/([0-9]+)"
        ),
        value,
    )

    require(
        match is not None,
        "X post URL format mismatch",
    )

    handle = f"@{match.group(1)}"
    post_id = match.group(2)

    return handle, post_id


def snowflake_timestamp_utc(
    post_id: str,
) -> str:
    milliseconds = (
        (int(post_id) >> 22)
        + TWITTER_EPOCH_MS
    )

    value = datetime.fromtimestamp(
        milliseconds / 1000,
        tz=timezone.utc,
    )

    return (
        value.isoformat(
            timespec="milliseconds"
        )
        .replace("+00:00", "Z")
    )


def validate_corrective_text(
    path: Path,
) -> str:
    require(
        path.is_file(),
        "corrective transcription is missing",
    )

    value = path.read_text(
        encoding="utf-8"
    )

    require(
        value == EXPECTED_CORRECTIVE_TEXT,
        "corrective transcription mismatch",
    )

    require(
        sha256_text(value)
        == EXPECTED_CORRECTIVE_TEXT_SHA,
        "corrective transcription SHA mismatch",
    )

    require(
        len(value)
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "corrective literal character count mismatch",
    )

    require(
        value.count(
            EXPECTED_AFFILIATE_URL
        )
        == 1,
        "affiliate URL count must equal one",
    )

    require(
        EXPECTED_OLD_PUBLIC_URL
        not in value,
        "old blog landing URL remains",
    )

    require(
        value.startswith("【PR・新刊】\n"),
        "visible PR prefix is missing",
    )

    require(
        "{{WORDPRESS_PUBLIC_URL}}"
        not in value,
        "public URL placeholder remains",
    )

    return value


def validate_attestations(
    *,
    paid_partnership_attestation: str,
    text_attestation: str,
    post_visible_attestation: str,
) -> None:
    require(
        paid_partnership_attestation
        == PAID_PARTNERSHIP_ATTESTATION,
        "paid partnership attestation mismatch",
    )

    require(
        text_attestation
        == TEXT_ATTESTATION,
        "corrective text attestation mismatch",
    )

    require(
        post_visible_attestation
        == POST_VISIBLE_ATTESTATION,
        "post visibility attestation mismatch",
    )


def validate_screenshot_metadata(
    *,
    sha256: str,
    width: int,
    height: int,
    source: str,
) -> None:
    require(
        sha256
        == EXPECTED_SCREENSHOT_SHA256,
        "screenshot SHA mismatch",
    )

    require(
        width
        == EXPECTED_SCREENSHOT_WIDTH,
        "screenshot width mismatch",
    )

    require(
        height
        == EXPECTED_SCREENSHOT_HEIGHT,
        "screenshot height mismatch",
    )

    require(
        source == SCREENSHOT_SOURCE,
        "screenshot source mismatch",
    )


def validate_readiness_pack(
    value: dict[str, Any],
) -> None:
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
        "readiness pack status mismatch",
    )

    require(
        value.get(
            "manual_posting_request_id"
        )
        == MANUAL_POSTING_REQUEST_ID,
        "readiness request ID mismatch",
    )

    require(
        value.get(
            "manual_posting_approval_issued"
        )
        is False,
        "readiness pack already records approval",
    )

    require(
        value.get(
            "manual_x_posting_allowed"
        )
        is False,
        "readiness pack already permits posting",
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


def validate_old_approval_gate(
    value: dict[str, Any],
) -> str:
    verify_digest(
        value,
        digest_field=(
            "x_manual_posting_explicit_"
            "approval_gate_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_OLD_APPROVAL_GATE_DIGEST
        ),
        label="old manual posting approval gate",
    )

    require(
        value.get("status")
        == (
            "PASS_X_MANUAL_POSTING_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "old approval gate status mismatch",
    )

    require(
        value.get(
            "manual_posting_request_id"
        )
        == MANUAL_POSTING_REQUEST_ID,
        "old approval request ID mismatch",
    )

    require(
        value.get("x_account_handle")
        == EXPECTED_X_ACCOUNT_HANDLE,
        "old approval X account mismatch",
    )

    draft = value.get("x_draft")

    require(
        isinstance(draft, dict),
        "old approval X draft is missing",
    )

    require(
        draft.get("text_sha256")
        == EXPECTED_OLD_TEXT_SHA,
        "old approval text SHA mismatch",
    )

    require(
        draft.get("public_url")
        == EXPECTED_OLD_PUBLIC_URL,
        "old approval public URL mismatch",
    )

    require(
        value.get(
            "manual_posting_approval_issued"
        )
        is True,
        "old manual posting approval was not issued",
    )

    require(
        value.get(
            "manual_posting_approval_consumed"
        )
        is False,
        "old manual posting approval was consumed",
    )

    require(
        value.get(
            "one_manual_post_allowed"
        )
        is True,
        "old approval did not allow one manual post",
    )

    require(
        value.get(
            "manual_x_posting_allowed"
        )
        is True,
        "old approval did not permit manual posting",
    )

    require(
        value.get(
            "automated_x_posting_allowed"
        )
        is False,
        "old approval permits automated posting",
    )

    require(
        value.get("x_api_call")
        is False,
        "old approval records X API use",
    )

    require(
        value.get("x_post")
        is False,
        "old approval gate performed an X post",
    )

    certificate_digest = value.get(
        "approval_certificate_digest_sha256"
    )

    require(
        isinstance(certificate_digest, str)
        and len(certificate_digest) == 64,
        "old approval certificate digest invalid",
    )

    return certificate_digest


def validate_old_certificate(
    value: dict[str, Any],
    *,
    expected_digest: str,
) -> None:
    verify_digest(
        value,
        digest_field=(
            "x_manual_posting_approval_"
            "certificate_digest_sha256"
        ),
        expected_digest=expected_digest,
        label="old manual posting certificate",
    )

    require(
        value.get("status")
        == (
            "X_MANUAL_POSTING_APPROVAL_"
            "ISSUED_NOT_CONSUMED"
        ),
        "old approval certificate status mismatch",
    )

    require(
        value.get(
            "manual_posting_request_id"
        )
        == MANUAL_POSTING_REQUEST_ID,
        "old certificate request ID mismatch",
    )

    require(
        value.get("x_account_handle")
        == EXPECTED_X_ACCOUNT_HANDLE,
        "old certificate X account mismatch",
    )

    require(
        value.get("x_draft_text_sha256")
        == EXPECTED_OLD_TEXT_SHA,
        "old certificate text SHA mismatch",
    )

    require(
        value.get("public_url")
        == EXPECTED_OLD_PUBLIC_URL,
        "old certificate public URL mismatch",
    )

    require(
        value.get(
            "manual_posting_approval_consumed"
        )
        is False,
        "old certificate approval was consumed",
    )

    require(
        value.get("x_api_call")
        is False,
        "old certificate records X API use",
    )

    require(
        value.get("x_post")
        is False,
        "old certificate records X posting",
    )


def validate_old_issuance_lock(
    value: dict[str, Any],
    *,
    certificate_digest: str,
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_MANUAL_X_POSTING_"
            "APPROVAL_ISSUANCE"
        ),
        "old issuance lock type mismatch",
    )

    require(
        value.get(
            "manual_posting_request_id"
        )
        == MANUAL_POSTING_REQUEST_ID,
        "old issuance request ID mismatch",
    )

    require(
        value.get(
            "source_readiness_digest_sha256"
        )
        == EXPECTED_READINESS_DIGEST,
        "old issuance readiness digest mismatch",
    )

    require(
        value.get(
            "approval_certificate_digest_sha256"
        )
        == certificate_digest,
        "old issuance certificate digest mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_OLD_APPROVAL_GATE_DIGEST,
        "old issuance gate digest mismatch",
    )

    require(
        value.get("approval_issued")
        is True,
        "old approval was not issued",
    )

    require(
        value.get("approval_consumed")
        is False,
        "old issuance approval was consumed",
    )

    require(
        value.get("reissuance_allowed")
        is False,
        "old issuance lock permits reissuance",
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


def register_corrective_evidence(
    *,
    production_database_path: Path,
    readiness_pack_path: Path,
    old_approval_gate_path: Path,
    old_approval_certificate_path: Path,
    old_issuance_lock_path: Path,
    finalization_pack_path: Path,
    corrective_text_path: Path,
    x_post_url: str,
    affiliate_url: str,
    paid_partnership_attestation: str,
    text_attestation: str,
    post_visible_attestation: str,
    screenshot_sha256: str,
    screenshot_width: int,
    screenshot_height: int,
    screenshot_source: str,
    evidence_pack_path: Path,
    supersession_lock_path: Path,
    registration_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    readiness_pack_path = (
        readiness_pack_path.resolve()
    )

    old_approval_gate_path = (
        old_approval_gate_path.resolve()
    )

    old_approval_certificate_path = (
        old_approval_certificate_path.resolve()
    )

    old_issuance_lock_path = (
        old_issuance_lock_path.resolve()
    )

    finalization_pack_path = (
        finalization_pack_path.resolve()
    )

    corrective_text_path = (
        corrective_text_path.resolve()
    )

    evidence_pack_path = (
        evidence_pack_path.resolve()
    )

    supersession_lock_path = (
        supersession_lock_path.resolve()
    )

    registration_lock_path = (
        registration_lock_path.resolve()
    )

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    require(
        affiliate_url
        == EXPECTED_AFFILIATE_URL,
        "affiliate URL mismatch",
    )

    handle, post_id = parse_x_post_url(
        x_post_url
    )

    require(
        x_post_url == EXPECTED_X_POST_URL,
        "X post URL mismatch",
    )

    require(
        handle == EXPECTED_X_ACCOUNT_HANDLE,
        "X post account mismatch",
    )

    require(
        post_id == EXPECTED_X_POST_ID,
        "X post ID mismatch",
    )

    require(
        snowflake_timestamp_utc(post_id)
        == EXPECTED_POSTED_AT_UTC,
        "X Snowflake timestamp mismatch",
    )

    validate_attestations(
        paid_partnership_attestation=(
            paid_partnership_attestation
        ),
        text_attestation=text_attestation,
        post_visible_attestation=(
            post_visible_attestation
        ),
    )

    validate_screenshot_metadata(
        sha256=screenshot_sha256,
        width=screenshot_width,
        height=screenshot_height,
        source=screenshot_source,
    )

    corrective_text = (
        validate_corrective_text(
            corrective_text_path
        )
    )

    readiness = load_json(
        readiness_pack_path
    )

    validate_readiness_pack(
        readiness
    )

    old_gate = load_json(
        old_approval_gate_path
    )

    certificate_digest = (
        validate_old_approval_gate(
            old_gate
        )
    )

    old_certificate = load_json(
        old_approval_certificate_path
    )

    validate_old_certificate(
        old_certificate,
        expected_digest=certificate_digest,
    )

    old_issuance = load_json(
        old_issuance_lock_path
    )

    validate_old_issuance_lock(
        old_issuance,
        certificate_digest=(
            certificate_digest
        ),
    )

    finalization = load_json(
        finalization_pack_path
    )

    validate_finalization_pack(
        finalization
    )

    for path, label in (
        (
            evidence_pack_path,
            "corrective evidence pack",
        ),
        (
            supersession_lock_path,
            "approval supersession lock",
        ),
        (
            registration_lock_path,
            "corrective registration lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    registered_at = datetime.now(
        timezone.utc
    ).isoformat()

    posted_at_utc = datetime.fromisoformat(
        EXPECTED_POSTED_AT_UTC.replace(
            "Z",
            "+00:00",
        )
    )

    posted_at_jst = posted_at_utc.astimezone(
        timezone(
            timedelta(hours=9)
        )
    ).isoformat(
        timespec="milliseconds"
    )

    evidence_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_MANUAL_POSTING_CORRECTIVE_"
            "EVIDENCE_REGISTERED"
        ),
        "registration_state": (
            "DIRECT_AFFILIATE_POST_RECORDED_"
            "OLD_APPROVAL_SUPERSEDED_"
            "NO_RETROACTIVE_APPROVAL"
        ),
        "registered_at": registered_at,
        "revision": REVISION,
        "link_route": LINK_ROUTE,
        "store": STORE,
        "manual_posting_request_id": (
            MANUAL_POSTING_REQUEST_ID
        ),
        "x_post": {
            "observed_manual_post": True,
            "post_visible": True,
            "post_url": EXPECTED_X_POST_URL,
            "post_id": EXPECTED_X_POST_ID,
            "x_account_handle": (
                EXPECTED_X_ACCOUNT_HANDLE
            ),
            "posted_at_utc": (
                EXPECTED_POSTED_AT_UTC
            ),
            "posted_at_jst": posted_at_jst,
            "posting_surface": (
                "X_WEB_OR_OFFICIAL_APP_"
                "HUMAN_OPERATION"
            ),
            "affiliate_url": (
                EXPECTED_AFFILIATE_URL
            ),
            "affiliate_url_visible": True,
            "affiliate_product_card_visible": True,
            "pr_prefix_visible": True,
            "visible_pr_prefix": "【PR・新刊】",
        },
        "corrective_transcription": {
            "evidence_mode": (
                "CANONICAL_TRANSCRIPTION_"
                "WITH_HUMAN_VISUAL_ATTESTATION"
            ),
            "text": corrective_text,
            "text_path": str(
                corrective_text_path
            ),
            "text_sha256": (
                EXPECTED_CORRECTIVE_TEXT_SHA
            ),
            "literal_character_count": (
                EXPECTED_LITERAL_CHARACTER_COUNT
            ),
            "estimated_tco_character_count": (
                EXPECTED_TCO_CHARACTER_COUNT
            ),
            "exact_x_source_export_available": False,
            "screenshot_content_consistent": True,
            "human_text_attestation": (
                text_attestation
            ),
        },
        "screenshot_evidence": {
            "source": screenshot_source,
            "sha256": screenshot_sha256,
            "width": screenshot_width,
            "height": screenshot_height,
            "binary_stored_in_repository": False,
            "post_visible": True,
            "x_account_handle_visible": True,
            "pr_prefix_visible": True,
            "affiliate_short_url_visible": True,
            "rakuten_product_card_visible": True,
            "paid_partnership_label_visible": False,
            "paid_partnership_label_visual_state": (
                "NOT_VISIBLE_IN_SUPPLIED_SCREENSHOT"
            ),
        },
        "paid_partnership_evidence": {
            "setting_attested_on": True,
            "human_attestation": (
                paid_partnership_attestation
            ),
            "visual_label_verified": False,
            "verification_method": (
                "HUMAN_ATTESTATION_PLUS_VISIBLE_PR_TEXT"
            ),
            "evidence_strength": (
                "PARTIAL_VISUAL_PLUS_HUMAN_ATTESTATION"
            ),
        },
        "governance_deviation": {
            "detected": True,
            "old_approved_revision": (
                "FINAL_REVIEW_APPROVED_LOCAL_V1"
            ),
            "old_approved_link_route": (
                "BLOG_LANDING"
            ),
            "old_approved_text_sha256": (
                EXPECTED_OLD_TEXT_SHA
            ),
            "old_approved_public_url": (
                EXPECTED_OLD_PUBLIC_URL
            ),
            "actual_registered_revision": REVISION,
            "actual_link_route": LINK_ROUTE,
            "actual_text_sha256": (
                EXPECTED_CORRECTIVE_TEXT_SHA
            ),
            "actual_affiliate_url": (
                EXPECTED_AFFILIATE_URL
            ),
            "text_changed_after_old_approval": True,
            "link_route_changed_after_old_approval": True,
            "old_approval_applicable_to_actual_post": False,
            "retroactive_approval": False,
            "corrective_evidence_only": True,
        },
        "old_manual_posting_approval": {
            "approval_gate_path": str(
                old_approval_gate_path
            ),
            "approval_gate_digest_sha256": (
                EXPECTED_OLD_APPROVAL_GATE_DIGEST
            ),
            "approval_certificate_path": str(
                old_approval_certificate_path
            ),
            "approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "issuance_lock_path": str(
                old_issuance_lock_path
            ),
            "approval_issued": True,
            "approval_consumed": False,
            "superseded": True,
            "reuse_allowed": False,
            "reissuance_allowed": False,
            "disposition": (
                "SUPERSEDED_NOT_CONSUMED_"
                "NOT_REUSABLE"
            ),
        },
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
        "post_execution_evidence_registered": True,
        "manual_post_count_observed": 1,
        "new_manual_posting_approval_issued": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "browser_automation": False,
        "x_api_call": False,
        "x_post_executed_by_this_phase": False,
        "production_status": "NO_GO",
        "safety_state": (
            "CORRECTIVE_EVIDENCE_REGISTERED_"
            "OLD_APPROVAL_INVALIDATED_"
            "NO_ADDITIONAL_X_POST_ALLOWED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-POST-METRICS-BASELINE-PREP"
        ),
    }

    evidence = {
        **evidence_payload,
        "x_manual_posting_corrective_"
        "evidence_digest_sha256": (
            canonical_digest(
                evidence_payload
            )
        ),
    }

    evidence_digest = evidence[
        "x_manual_posting_corrective_"
        "evidence_digest_sha256"
    ]

    supersession_lock = {
        "lock_type": (
            "X_R11_MANUAL_X_POSTING_"
            "APPROVAL_SUPERSESSION"
        ),
        "created_at": registered_at,
        "manual_posting_request_id": (
            MANUAL_POSTING_REQUEST_ID
        ),
        "old_approval_gate_digest_sha256": (
            EXPECTED_OLD_APPROVAL_GATE_DIGEST
        ),
        "old_approval_consumed": False,
        "old_approval_superseded": True,
        "old_approval_reuse_allowed": False,
        "old_approval_reissuance_allowed": False,
        "superseded_reason": (
            "ACTUAL_POST_USED_CORRECTIVE_"
            "DIRECT_AFFILIATE_REVISION"
        ),
        "retroactive_approval": False,
        "registered_x_post_id": (
            EXPECTED_X_POST_ID
        ),
        "corrective_revision": REVISION,
        "corrective_evidence_path": str(
            evidence_pack_path
        ),
        "corrective_evidence_digest_sha256": (
            evidence_digest
        ),
    }

    registration_lock = {
        "lock_type": (
            "X_R11_MANUAL_X_POSTING_"
            "CORRECTIVE_EVIDENCE_REGISTRATION"
        ),
        "created_at": registered_at,
        "x_post_id": EXPECTED_X_POST_ID,
        "x_post_url": EXPECTED_X_POST_URL,
        "revision": REVISION,
        "corrective_evidence_path": str(
            evidence_pack_path
        ),
        "corrective_evidence_digest_sha256": (
            evidence_digest
        ),
        "registration_completed": True,
        "reregistration_allowed": False,
        "additional_x_post_allowed": False,
    }

    atomic_create_json(
        evidence_pack_path,
        evidence,
    )

    atomic_create_json(
        supersession_lock_path,
        supersession_lock,
    )

    atomic_create_json(
        registration_lock_path,
        registration_lock,
    )

    return evidence


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
        "--old-approval-gate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--old-approval-certificate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--old-issuance-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--finalization-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--corrective-text",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--x-post-url",
        required=True,
    )

    parser.add_argument(
        "--affiliate-url",
        required=True,
    )

    parser.add_argument(
        "--paid-partnership-attestation",
        required=True,
    )

    parser.add_argument(
        "--text-attestation",
        required=True,
    )

    parser.add_argument(
        "--post-visible-attestation",
        required=True,
    )

    parser.add_argument(
        "--screenshot-sha256",
        required=True,
    )

    parser.add_argument(
        "--screenshot-width",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--screenshot-height",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--screenshot-source",
        required=True,
    )

    parser.add_argument(
        "--evidence-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--supersession-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--registration-lock",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = register_corrective_evidence(
            production_database_path=(
                args.production_db
            ),
            readiness_pack_path=(
                args.readiness_pack
            ),
            old_approval_gate_path=(
                args.old_approval_gate
            ),
            old_approval_certificate_path=(
                args.old_approval_certificate
            ),
            old_issuance_lock_path=(
                args.old_issuance_lock
            ),
            finalization_pack_path=(
                args.finalization_pack
            ),
            corrective_text_path=(
                args.corrective_text
            ),
            x_post_url=args.x_post_url,
            affiliate_url=args.affiliate_url,
            paid_partnership_attestation=(
                args.paid_partnership_attestation
            ),
            text_attestation=(
                args.text_attestation
            ),
            post_visible_attestation=(
                args.post_visible_attestation
            ),
            screenshot_sha256=(
                args.screenshot_sha256
            ),
            screenshot_width=(
                args.screenshot_width
            ),
            screenshot_height=(
                args.screenshot_height
            ),
            screenshot_source=(
                args.screenshot_source
            ),
            evidence_pack_path=(
                args.evidence_pack
            ),
            supersession_lock_path=(
                args.supersession_lock
            ),
            registration_lock_path=(
                args.registration_lock
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_MANUAL_POSTING_"
                        "CORRECTIVE_EVIDENCE_REGISTRATION"
                    ),
                    "error": str(exc),
                    "automatic_rerun_allowed": False,
                    "retroactive_approval": False,
                    "database_write": False,
                    "x_api_call": False,
                    "x_post_executed_by_this_phase": False,
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
                "registration_state": (
                    result["registration_state"]
                ),
                "revision": result["revision"],
                "link_route": result["link_route"],
                "store": result["store"],
                "x_post_url": (
                    result["x_post"]["post_url"]
                ),
                "x_post_id": (
                    result["x_post"]["post_id"]
                ),
                "x_account_handle": (
                    result[
                        "x_post"
                    ]["x_account_handle"]
                ),
                "affiliate_url": (
                    result[
                        "x_post"
                    ]["affiliate_url"]
                ),
                "corrective_text_sha256": (
                    result[
                        "corrective_transcription"
                    ]["text_sha256"]
                ),
                "paid_partnership_setting_attested": True,
                "paid_partnership_label_visual_state": (
                    result[
                        "screenshot_evidence"
                    ][
                        "paid_partnership_"
                        "label_visual_state"
                    ]
                ),
                "old_approval_consumed": False,
                "old_approval_superseded": True,
                "old_approval_reuse_allowed": False,
                "retroactive_approval": False,
                "post_execution_evidence_registered": True,
                "new_manual_posting_approval_issued": False,
                "database_write": False,
                "x_api_call": False,
                "x_post_executed_by_this_phase": False,
                "production_status": "NO_GO",
                "evidence_pack_path": str(
                    args.evidence_pack.resolve()
                ),
                "evidence_digest_sha256": (
                    result[
                        "x_manual_posting_corrective_"
                        "evidence_digest_sha256"
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
