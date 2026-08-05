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


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "X-DRAFT-FINAL-REVIEW-"
    "LOCAL-FINALIZATION-ONE-SHOT"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_APPROVAL_GATE_DIGEST = (
    "7a5bdcc215ddeb23c44010435806bfd0"
    "89658dd84f9508b83245c2b21b6310a9"
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

EXPECTED_DRAFT_ID = (
    "xr11-x-draft-public-url-"
    "4842647be85ea1d60aab47fd"
)

FINALIZATION_ID = (
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


class XDraftLocalFinalizationError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XDraftLocalFinalizationError(
            message
        )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


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
        raise XDraftLocalFinalizationError(
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


def atomic_create_bytes(
    path: Path,
    value: bytes,
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
        raise XDraftLocalFinalizationError(
            f"one-shot artifact already exists: {path}"
        ) from exc

    try:
        os.write(
            descriptor,
            value,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    atomic_create_bytes(
        path,
        (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
    )


def validate_source_text(
    value: str,
) -> None:
    require(
        value == EXPECTED_FINAL_TEXT,
        "approved X draft text mismatch",
    )

    require(
        sha256_bytes(
            value.encode("utf-8")
        )
        == EXPECTED_TEXT_SHA,
        "approved X draft text SHA mismatch",
    )

    require(
        len(value)
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "approved X draft character count mismatch",
    )

    require(
        value.count(
            EXPECTED_PUBLIC_URL
        )
        == 1,
        "approved X draft public URL count mismatch",
    )

    require(
        "{{WORDPRESS_PUBLIC_URL}}"
        not in value,
        "approved X draft still contains a placeholder",
    )


def validate_approval_gate(
    value: dict[str, Any],
) -> str:
    verify_digest(
        value,
        digest_field=(
            "x_draft_final_review_explicit_"
            "approval_gate_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_APPROVAL_GATE_DIGEST
        ),
        label="final review approval gate",
    )

    require(
        value.get("status")
        == (
            "PASS_X_DRAFT_FINAL_REVIEW_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "final review approval gate status mismatch",
    )

    require(
        value.get("approval_gate_state")
        == (
            "READY_AWAITING_ONE_SHOT_"
            "LOCAL_X_DRAFT_FINALIZATION"
        ),
        "final review approval gate state mismatch",
    )

    require(
        value.get("approval_request_id")
        == APPROVAL_REQUEST_ID,
        "final review approval request ID mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "final review source digest mismatch",
    )

    require(
        value.get(
            "human_decision"
        )
        == "APPROVED",
        "final review human decision mismatch",
    )

    require(
        value.get(
            "final_human_review_completed"
        )
        is True,
        "final human review is incomplete",
    )

    require(
        value.get(
            "x_final_review_approval_issued"
        )
        is True,
        "final review approval was not issued",
    )

    require(
        value.get(
            "x_final_review_approval_consumed"
        )
        is False,
        "final review approval was already consumed",
    )

    require(
        value.get(
            "local_finalization_runner_allowed"
        )
        is True,
        "local finalization runner is blocked",
    )

    require(
        value.get(
            "x_post_approval_issued"
        )
        is False,
        "X post approval was unexpectedly issued",
    )

    require(
        value.get(
            "manual_x_posting_allowed"
        )
        is False,
        "manual X posting is unexpectedly allowed",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "X execution is unexpectedly allowed",
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
            value.get(field)
            is False,
            (
                "approval gate records an "
                f"unexpected action: {field}"
            ),
        )

    draft = value.get(
        "x_draft"
    )

    require(
        isinstance(draft, dict),
        "approval gate X draft evidence is missing",
    )

    require(
        draft.get("draft_id")
        == EXPECTED_DRAFT_ID,
        "approval gate X draft ID mismatch",
    )

    require(
        draft.get("text_sha256")
        == EXPECTED_TEXT_SHA,
        "approval gate X draft SHA mismatch",
    )

    require(
        draft.get(
            "literal_character_count"
        )
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "approval gate literal count mismatch",
    )

    require(
        draft.get(
            "estimated_tco_character_count"
        )
        == EXPECTED_TCO_CHARACTER_COUNT,
        "approval gate t.co count mismatch",
    )

    require(
        draft.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "approval gate public URL mismatch",
    )

    certificate_digest = value.get(
        "approval_certificate_digest_sha256"
    )

    require(
        isinstance(certificate_digest, str)
        and len(certificate_digest) == 64,
        "approval certificate digest is invalid",
    )

    return certificate_digest


def validate_certificate(
    value: dict[str, Any],
    *,
    expected_digest: str,
    source_text_path: Path,
) -> None:
    verify_digest(
        value,
        digest_field=(
            "x_draft_final_review_approval_"
            "certificate_digest_sha256"
        ),
        expected_digest=expected_digest,
        label="final review approval certificate",
    )

    require(
        value.get("status")
        == (
            "X_DRAFT_FINAL_REVIEW_APPROVAL_"
            "ISSUED_NOT_CONSUMED"
        ),
        "final review certificate status mismatch",
    )

    require(
        value.get("approval_request_id")
        == APPROVAL_REQUEST_ID,
        "final review certificate request ID mismatch",
    )

    require(
        value.get("approval_label")
        == APPROVAL_LABEL,
        "final review approval label mismatch",
    )

    require(
        value.get("approval_scope")
        == APPROVAL_SCOPE,
        "final review approval scope mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "certificate review digest mismatch",
    )

    require(
        value.get(
            "source_replacement_pack_digest_sha256"
        )
        == EXPECTED_REPLACEMENT_PACK_DIGEST,
        "certificate replacement digest mismatch",
    )

    require(
        value.get(
            "source_wording_gate_digest_sha256"
        )
        == EXPECTED_WORDING_GATE_DIGEST,
        "certificate wording gate digest mismatch",
    )

    require(
        value.get(
            "source_publication_verification_"
            "digest_sha256"
        )
        == EXPECTED_PUBLICATION_VERIFICATION_DIGEST,
        "certificate publication digest mismatch",
    )

    require(
        value.get("x_draft_id")
        == EXPECTED_DRAFT_ID,
        "certificate X draft ID mismatch",
    )

    require(
        Path(
            value["x_draft_text_path"]
        ).resolve()
        == source_text_path,
        "certificate X draft text path mismatch",
    )

    require(
        value.get("x_draft_text_sha256")
        == EXPECTED_TEXT_SHA,
        "certificate X draft SHA mismatch",
    )

    require(
        value.get("x_draft_text")
        == EXPECTED_FINAL_TEXT,
        "certificate X draft text mismatch",
    )

    require(
        value.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "certificate public URL mismatch",
    )

    require(
        value.get(
            "final_human_review_completed"
        )
        is True,
        "certificate final review is incomplete",
    )

    require(
        value.get(
            "local_finalization_runner_allowed"
        )
        is True,
        "certificate blocks local finalization",
    )

    require(
        value.get("approval_consumed")
        is False,
        "certificate approval was already consumed",
    )

    require(
        value.get(
            "local_finalization_executed"
        )
        is False,
        "certificate finalization was already executed",
    )

    require(
        value.get(
            "x_post_approval_issued"
        )
        is False,
        "certificate contains X post approval",
    )

    require(
        value.get(
            "manual_x_posting_allowed"
        )
        is False,
        "certificate permits manual X posting",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "certificate permits X execution",
    )


def validate_issuance_lock(
    value: dict[str, Any],
    *,
    certificate_digest: str,
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_X_DRAFT_FINAL_REVIEW_"
            "APPROVAL_ISSUANCE"
        ),
        "final review issuance lock type mismatch",
    )

    require(
        value.get("approval_request_id")
        == APPROVAL_REQUEST_ID,
        "final review issuance request ID mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "issuance lock review digest mismatch",
    )

    require(
        value.get("approval_label")
        == APPROVAL_LABEL,
        "issuance lock approval label mismatch",
    )

    require(
        value.get("approval_scope")
        == APPROVAL_SCOPE,
        "issuance lock approval scope mismatch",
    )

    require(
        value.get(
            "approval_certificate_digest_sha256"
        )
        == certificate_digest,
        "issuance lock certificate digest mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "issuance lock gate digest mismatch",
    )

    require(
        value.get("approval_issued")
        is True,
        "issuance lock has no approval",
    )

    require(
        value.get("approval_consumed")
        is False,
        "issuance lock approval is already consumed",
    )

    require(
        value.get("reissuance_allowed")
        is False,
        "issuance lock permits reissuance",
    )

    require(
        value.get("x_post_allowed")
        is False,
        "issuance lock permits X posting",
    )


def run_one_shot(
    *,
    production_database_path: Path,
    approval_gate_pack_path: Path,
    approval_certificate_path: Path,
    issuance_lock_path: Path,
    source_text_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    finalized_text_path: Path,
    finalized_pack_path: Path,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "execution_claim_created": False,
        "approval_consumed": False,
        "finalized_text_created": False,
        "finalized_pack_created": False,
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

        source_text_path = (
            source_text_path.resolve()
        )

        execution_claim_path = (
            execution_claim_path.resolve()
        )

        consumption_lock_path = (
            consumption_lock_path.resolve()
        )

        finalized_text_path = (
            finalized_text_path.resolve()
        )

        finalized_pack_path = (
            finalized_pack_path.resolve()
        )

        require(
            sha256_file(
                production_database_path
            )
            == EXPECTED_DATABASE_SHA,
            "production database changed",
        )

        require(
            source_text_path.is_file(),
            "approved X draft text is missing",
        )

        source_bytes = (
            source_text_path.read_bytes()
        )

        require(
            sha256_bytes(source_bytes)
            == EXPECTED_TEXT_SHA,
            "approved X draft file SHA mismatch",
        )

        source_text = source_bytes.decode(
            "utf-8"
        )

        validate_source_text(
            source_text
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
                finalized_text_path,
                "finalized X draft text",
            ),
            (
                finalized_pack_path,
                "finalized X draft pack",
            ),
        ):
            require(
                not path.exists(),
                f"{label} already exists",
            )

        gate = load_json(
            approval_gate_pack_path
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
            source_text_path=(
                source_text_path
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

        claimed_at = datetime.now(
            timezone.utc
        ).isoformat()

        claim_payload = {
            "lock_type": (
                "X_R11_X_DRAFT_FINAL_REVIEW_"
                "LOCAL_FINALIZATION_EXECUTION_CLAIM"
            ),
            "created_at": claimed_at,
            "approval_request_id": (
                APPROVAL_REQUEST_ID
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
            "source_x_draft_id": (
                EXPECTED_DRAFT_ID
            ),
            "source_text_sha256": (
                EXPECTED_TEXT_SHA
            ),
            "finalization_id": (
                FINALIZATION_ID
            ),
            "execution_claimed": True,
            "local_only": True,
            "x_post_allowed": False,
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
                "X_R11_X_DRAFT_FINAL_REVIEW_"
                "APPROVAL_CONSUMPTION"
            ),
            "created_at": claimed_at,
            "approval_request_id": (
                APPROVAL_REQUEST_ID
            ),
            "approval_label": (
                APPROVAL_LABEL
            ),
            "approval_scope": (
                APPROVAL_SCOPE
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
            "consumed_for_local_finalization": True,
            "x_post_allowed": False,
            "reexecution_allowed": False,
        }

        atomic_create_json(
            consumption_lock_path,
            consumption_payload,
        )

        state["approval_consumed"] = True

        atomic_create_bytes(
            finalized_text_path,
            source_bytes,
        )

        state[
            "finalized_text_created"
        ] = True

        require(
            sha256_file(
                finalized_text_path
            )
            == EXPECTED_TEXT_SHA,
            "finalized X draft SHA mismatch",
        )

        require(
            finalized_text_path.read_text(
                encoding="utf-8"
            )
            == EXPECTED_FINAL_TEXT,
            "finalized X draft content mismatch",
        )

        require(
            sha256_file(
                source_text_path
            )
            == EXPECTED_TEXT_SHA,
            "source X draft changed during finalization",
        )

        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        pack_payload = {
            "phase": PHASE,
            "status": (
                "PASS_X_DRAFT_FINAL_REVIEW_"
                "LOCAL_FINALIZATION_ONE_SHOT"
            ),
            "finalization_state": (
                "FINALIZED_LOCAL_X_DRAFT_READY_FOR_"
                "SEPARATE_MANUAL_POSTING_REVIEW"
            ),
            "completed_at": completed_at,
            "finalization_id": (
                FINALIZATION_ID
            ),
            "approval_request_id": (
                APPROVAL_REQUEST_ID
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
            "source_replacement_pack_digest_sha256": (
                EXPECTED_REPLACEMENT_PACK_DIGEST
            ),
            "source_publication_verification_digest_sha256": (
                EXPECTED_PUBLICATION_VERIFICATION_DIGEST
            ),
            "source_wording_gate_digest_sha256": (
                EXPECTED_WORDING_GATE_DIGEST
            ),
            "execution_claim_path": str(
                execution_claim_path
            ),
            "consumption_lock_path": str(
                consumption_lock_path
            ),
            "source_x_draft": {
                "draft_id": (
                    EXPECTED_DRAFT_ID
                ),
                "text_path": str(
                    source_text_path
                ),
                "text_sha256": (
                    EXPECTED_TEXT_SHA
                ),
                "preserved": True,
                "modified": False,
            },
            "finalized_x_draft": {
                "draft_id": (
                    EXPECTED_DRAFT_ID
                ),
                "finalization_id": (
                    FINALIZATION_ID
                ),
                "revision": (
                    "FINAL_REVIEW_APPROVED_LOCAL_V1"
                ),
                "text": (
                    EXPECTED_FINAL_TEXT
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
                "public_url": (
                    EXPECTED_PUBLIC_URL
                ),
                "public_url_count": 1,
                "public_url_placeholder_absent": True,
                "wording_frozen": True,
                "local_finalization_completed": True,
            },
            "final_human_review_completed": True,
            "final_human_decision": "APPROVED",
            "x_final_review_approval_issued": True,
            "x_final_review_approval_consumed": True,
            "approval_consumed": True,
            "local_finalization_executed": True,
            "reexecution_allowed": False,
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
                "FINAL_X_DRAFT_FROZEN_LOCAL_ONLY_"
                "SEPARATE_MANUAL_POSTING_APPROVAL_REQUIRED"
            ),
            "authorized_next_phase": (
                "X-R11-PRODUCTION-CANDIDATE-1-"
                "X-MANUAL-POSTING-READINESS-PREP"
            ),
        }

        pack = {
            **pack_payload,
            "x_draft_final_review_local_"
            "finalization_digest_sha256": (
                canonical_digest(
                    pack_payload
                )
            ),
        }

        atomic_create_json(
            finalized_pack_path,
            pack,
        )

        state[
            "finalized_pack_created"
        ] = True

        return pack

    except Exception as exc:
        failure_payload = {
            "phase": PHASE,
            "status": (
                "FAIL_X_DRAFT_FINAL_REVIEW_"
                "LOCAL_FINALIZATION_ONE_SHOT"
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
            "x_post_approval_issued": False,
            "manual_x_posting_allowed": False,
            "x_post_execution_allowed": False,
            "normal_x_fb_write": False,
            "wordpress_write": False,
            "database_write": False,
            "workflow_write": False,
            "x_api_call": False,
            "x_post": False,
            "production_status": "NO_GO",
        }

        failure = {
            **failure_payload,
            "x_draft_final_review_local_"
            "finalization_failure_digest_sha256": (
                canonical_digest(
                    failure_payload
                )
            ),
        }

        if not finalized_pack_path.exists():
            atomic_write_json(
                finalized_pack_path,
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
        "--source-text",
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
        "--finalized-text",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--finalized-pack",
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
            source_text_path=(
                args.source_text
            ),
            execution_claim_path=(
                args.execution_claim
            ),
            consumption_lock_path=(
                args.consumption_lock
            ),
            finalized_text_path=(
                args.finalized_text
            ),
            finalized_pack_path=(
                args.finalized_pack
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_DRAFT_FINAL_REVIEW_"
                        "LOCAL_FINALIZATION_ONE_SHOT"
                    ),
                    "error": str(exc),
                    "automatic_reexecution_allowed": False,
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

    draft = result[
        "finalized_x_draft"
    ]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "finalization_state": (
                    result["finalization_state"]
                ),
                "finalization_id": (
                    result["finalization_id"]
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
                "x_final_review_approval_consumed": True,
                "local_finalization_executed": True,
                "reexecution_allowed": False,
                "x_post_approval_issued": False,
                "manual_x_posting_allowed": False,
                "x_post_execution_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
                "finalized_text_path": str(
                    args.finalized_text.resolve()
                ),
                "finalized_pack_path": str(
                    args.finalized_pack.resolve()
                ),
                "finalized_pack_digest_sha256": (
                    result[
                        "x_draft_final_review_"
                        "local_finalization_"
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
