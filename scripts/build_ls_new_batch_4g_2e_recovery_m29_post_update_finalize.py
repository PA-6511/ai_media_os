#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def block_network(
    *args: Any,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "NETWORK_OPERATION_BLOCKED_BY_M29_FINALIZATION"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_layout_"
    "post_update_finalization_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m29_post_update_finalize_approval.json"
)

M27_CONSUMPTION = ROOT / (
    "exchange/consumptions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_consumption.json"
)
M27_EXECUTION_SNAPSHOT = ROOT / (
    "exchange/executions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_execution_snapshot.json"
)
M27_EXECUTION_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_execute_result.json"
)

M28_VERIFICATION = ROOT / (
    "exchange/verifications/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "post_update_get_verification.json"
)
M28_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m28_post_update_verify_result.json"
)

M26_AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_authorization.json"
)
M27_CONFIRMATION = ROOT / (
    "exchange/confirmations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "execute_now_confirmation.json"
)

M24_RENDERED = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.html"
)
M24_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_payload_v1.json"
)

M25_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_human_review_approved.json"
)
M25_REQUIREMENT = ROOT / (
    "exchange/requirements/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_backlist_cover_affiliate_carousel_"
    "future_requirement.json"
)

ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)

FINALIZATION = ROOT / (
    "exchange/finalizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "post_update_finalization.json"
)
CLOSURE = ROOT / (
    "exchange/closures/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_series_closure.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m29_post_update_finalize_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m29_"
    "post_update_finalization_report.md"
)

EXPECTED_POST_ID = 192
EXPECTED_STATUS = "publish"
EXPECTED_TITLE = "ダークギャザリング 第20巻｜配信開始"
EXPECTED_CATEGORIES = [10]
EXPECTED_COMMENT_STATUS = "closed"

EXPECTED_CONTENT_SHA = (
    "dc938ae164c70130a5fb27692d71c97c"
    "c367a8985c44c2c333801b337ee6caf4"
)
EXPECTED_CONSUMPTION_DIGEST = (
    "ade807888265e7b1fa1fdc49abb65bf2"
    "deda2d7607530c1a0ad99195f71eac4a"
)
EXPECTED_EXECUTION_SNAPSHOT_DIGEST = (
    "bd08a01aa548cb1da45bbc891e08ef69"
    "26216b28ed43019dd8f5c06dd9367366"
)
EXPECTED_EXECUTION_RESULT_DIGEST = (
    "1d1f123851bd3e1bd8754c896d0cbd4d"
    "a7f0fc71874203e5f6558b67167a1651"
)
EXPECTED_VERIFICATION_DIGEST = (
    "42eeb0f7923801a767f4a1d72986fdd3"
    "570495295e2d9d3cc8dcbefa0057ea7a"
)
EXPECTED_M28_RESULT_DIGEST = (
    "70bbf8c7db7b138261591b031b66bf80"
    "afd1744ebfdd051ba2c2cab8fffeb49e"
)
EXPECTED_AUTHORIZATION_DIGEST = (
    "d7f53a0eb02a037cde4b6ab71b4b026b"
    "79eb8c2d2c08a95a8bec5f1ad0b6e615"
)
EXPECTED_CONFIRMATION_DIGEST = (
    "74cc04d1d01a5ae81a2367ed098ce17b"
    "a4896db8e1ac713a8014fd2c01cc1c64"
)
EXPECTED_PAYLOAD_DIGEST = (
    "52ed18792454e5806b739059911c8117"
    "810cafcadacf35fb77429b608673cd60"
)
EXPECTED_REVIEW_DIGEST = (
    "7fd7a9f0f5317435160010fac811b77d"
    "876f77919ad2b5905c6cdea82f8f1806"
)
EXPECTED_REQUIREMENT_DIGEST = (
    "bfa2e1b69c1d5cfe3999ac0048539d1d"
    "4b01d60e9ba9d452a8e65176a5d028a4"
)
EXPECTED_ROLLBACK_DIGEST = (
    "60ac4fe5182e412014bcbd291ca52af1"
    "e516e7061722e608b39a34c284dbfcf5"
)
EXPECTED_REQUEST_BODY_DIGEST = (
    "02f5f89d916e328f0b020ebfefafcb39"
    "1e1c4b0a511d4b2277e37fa225fc81e7"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    code: str,
) -> None:
    if not condition:
        raise ValidationError(code)


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def canonical_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.exists() and path.is_file(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )
    require(
        not path.is_symlink(),
        f"JSON_SYMLINK_REJECTED:{path.name}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise ValidationError(
            f"JSON_PARSE_FAILED:{path.name}"
        ) from None

    require(
        isinstance(value, dict),
        f"JSON_ROOT_NOT_OBJECT:{path.name}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    field: str,
    expected: str,
) -> None:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        canonical_digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )
    require(
        stored == expected,
        f"DIGEST_EXPECTED_MISMATCH:{field}",
    )


def add_digest(
    value: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = canonical_digest(value)
    return result


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )


def main() -> int:
    source_paths = {
        "m27_consumption": M27_CONSUMPTION,
        "m27_execution_snapshot": M27_EXECUTION_SNAPSHOT,
        "m27_execution_result": M27_EXECUTION_RESULT,
        "m28_verification": M28_VERIFICATION,
        "m28_result": M28_RESULT,
        "m26_authorization": M26_AUTHORIZATION,
        "execute_now_confirmation": M27_CONFIRMATION,
        "m24_rendered": M24_RENDERED,
        "m24_payload": M24_PAYLOAD,
        "m25_review": M25_REVIEW,
        "m25_requirement": M25_REQUIREMENT,
        "rollback": ROLLBACK,
    }

    try:
        for output in [
            FINALIZATION,
            CLOSURE,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        approval_copy = copy.deepcopy(
            approval
        )
        approval_digest = approval_copy.pop(
            "approval_evidence_digest_sha256",
            None,
        )

        require(
            canonical_digest(approval_copy)
            == approval_digest,
            "APPROVAL_DIGEST_MISMATCH",
        )
        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-RECOVERY-"
                "M29-POST-UPDATE-FINALIZE"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
                "POST_UPDATE_FINALIZATION_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )

        source_hashes_before = {
            name: file_sha(path)
            for name, path
            in source_paths.items()
        }

        for name, path in source_paths.items():
            binding = approval[
                "source_bindings"
            ][name]

            require(
                binding["path"]
                == str(path.relative_to(ROOT)),
                f"SOURCE_PATH_MISMATCH:{name}",
            )
            require(
                binding["file_sha256"]
                == source_hashes_before[name],
                f"SOURCE_SHA_MISMATCH:{name}",
            )

        consumption = load_json(
            M27_CONSUMPTION
        )
        execution_snapshot = load_json(
            M27_EXECUTION_SNAPSHOT
        )
        execution_result = load_json(
            M27_EXECUTION_RESULT
        )
        verification = load_json(
            M28_VERIFICATION
        )
        m28_result = load_json(
            M28_RESULT
        )
        authorization = load_json(
            M26_AUTHORIZATION
        )
        confirmation = load_json(
            M27_CONFIRMATION
        )
        payload = load_json(
            M24_PAYLOAD
        )
        review = load_json(
            M25_REVIEW
        )
        requirement = load_json(
            M25_REQUIREMENT
        )
        rollback = load_json(
            ROLLBACK
        )

        verify_digest(
            consumption,
            "consumption_digest_sha256",
            EXPECTED_CONSUMPTION_DIGEST,
        )
        verify_digest(
            execution_snapshot,
            "snapshot_digest_sha256",
            EXPECTED_EXECUTION_SNAPSHOT_DIGEST,
        )
        verify_digest(
            execution_result,
            "result_digest_sha256",
            EXPECTED_EXECUTION_RESULT_DIGEST,
        )
        verify_digest(
            verification,
            "verification_digest_sha256",
            EXPECTED_VERIFICATION_DIGEST,
        )
        verify_digest(
            m28_result,
            "result_digest_sha256",
            EXPECTED_M28_RESULT_DIGEST,
        )
        verify_digest(
            authorization,
            "authorization_digest_sha256",
            EXPECTED_AUTHORIZATION_DIGEST,
        )
        verify_digest(
            confirmation,
            "confirmation_digest_sha256",
            EXPECTED_CONFIRMATION_DIGEST,
        )
        verify_digest(
            payload,
            "update_payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            review,
            "human_review_evidence_digest_sha256",
            EXPECTED_REVIEW_DIGEST,
        )
        verify_digest(
            requirement,
            "future_requirement_digest_sha256",
            EXPECTED_REQUIREMENT_DIGEST,
        )
        verify_digest(
            rollback,
            "rollback_evidence_digest_sha256",
            EXPECTED_ROLLBACK_DIGEST,
        )

        require(
            file_sha(M24_RENDERED)
            == EXPECTED_CONTENT_SHA,
            "M24_RENDERED_SHA_MISMATCH",
        )

        require(
            consumption[
                "authorization_consumed"
            ] is True,
            "AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            consumption[
                "confirmation_consumed"
            ] is True,
            "CONFIRMATION_NOT_CONSUMED",
        )
        require(
            consumption[
                "authorization_consumption_count"
            ] == 1,
            "AUTHORIZATION_CONSUMPTION_COUNT_NOT_ONE",
        )
        require(
            consumption[
                "confirmation_consumption_count"
            ] == 1,
            "CONFIRMATION_CONSUMPTION_COUNT_NOT_ONE",
        )
        require(
            consumption[
                "authorization_reuse_allowed"
            ] is False,
            "AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            consumption[
                "automatic_retry_allowed"
            ] is False,
            "AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            consumption[
                "automatic_reissue_allowed"
            ] is False,
            "AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            consumption[
                "second_post_allowed"
            ] is False,
            "SECOND_POST_ALLOWED",
        )

        require(
            execution_result[
                "status"
            ] == (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_ONE_SHOT_POST_RESPONSE_VALIDATED_"
                "AWAITING_GET_ONLY_VERIFICATION"
            ),
            "M27_STATUS_MISMATCH",
        )
        require(
            execution_result[
                "outcome"
            ] == "VALIDATED_HTTP_200_UPDATE_RESPONSE",
            "M27_OUTCOME_MISMATCH",
        )
        require(
            execution_result[
                "response_validated"
            ] is True,
            "M27_RESPONSE_NOT_VALIDATED",
        )
        require(
            execution_result[
                "http_status_code"
            ] == 200,
            "M27_HTTP_NOT_200",
        )
        require(
            execution_result[
                "post_request_count"
            ] == 1,
            "M27_POST_COUNT_NOT_ONE",
        )
        require(
            execution_result[
                "automatic_retry_count"
            ] == 0,
            "M27_RETRY_COUNT_NOT_ZERO",
        )
        require(
            execution_result[
                "second_post_performed"
            ] is False,
            "M27_SECOND_POST_PERFORMED",
        )
        require(
            execution_result[
                "wordpress_update_performed"
            ] is True,
            "M27_UPDATE_NOT_PERFORMED",
        )
        require(
            execution_result[
                "ready_for_retry"
            ] is False,
            "M27_RETRY_GATE_OPEN",
        )
        require(
            execution_result[
                "ready_for_second_post"
            ] is False,
            "M27_SECOND_POST_GATE_OPEN",
        )

        for field in [
            "response_post_id_matches",
            "response_status_is_publish",
            "response_title_matches",
            "response_categories_match",
            "response_comment_status_is_closed",
            "response_content_matches_m24",
        ]:
            require(
                execution_result[field] is True,
                f"M27_RESPONSE_CHECK_FALSE:{field}",
            )

        require(
            execution_snapshot[
                "response_post_id"
            ] == EXPECTED_POST_ID,
            "M27_SNAPSHOT_POST_ID_MISMATCH",
        )
        require(
            execution_snapshot[
                "response_status"
            ] == EXPECTED_STATUS,
            "M27_SNAPSHOT_STATUS_MISMATCH",
        )
        require(
            execution_snapshot[
                "response_title"
            ] == EXPECTED_TITLE,
            "M27_SNAPSHOT_TITLE_MISMATCH",
        )
        require(
            sorted(
                execution_snapshot[
                    "response_category_ids"
                ]
            ) == EXPECTED_CATEGORIES,
            "M27_SNAPSHOT_CATEGORIES_MISMATCH",
        )
        require(
            execution_snapshot[
                "response_comment_status"
            ] == EXPECTED_COMMENT_STATUS,
            "M27_SNAPSHOT_COMMENT_STATUS_MISMATCH",
        )
        require(
            execution_snapshot[
                "response_content_sha256"
            ] == EXPECTED_CONTENT_SHA,
            "M27_SNAPSHOT_CONTENT_SHA_MISMATCH",
        )

        require(
            m28_result[
                "status"
            ] == (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
                "POST_UPDATE_GET_VERIFICATION_FINAL_STATE_MATCHED_"
                "NO_WRITE"
            ),
            "M28_STATUS_MISMATCH",
        )
        require(
            m28_result[
                "final_state_verified"
            ] is True,
            "M28_FINAL_STATE_NOT_VERIFIED",
        )
        require(
            m28_result[
                "http_status_code"
            ] == 200,
            "M28_HTTP_NOT_200",
        )
        require(
            m28_result[
                "get_request_count"
            ] == 1,
            "M28_GET_COUNT_NOT_ONE",
        )
        require(
            m28_result[
                "automatic_retry_count"
            ] == 0,
            "M28_RETRY_COUNT_NOT_ZERO",
        )
        require(
            m28_result[
                "second_post_performed"
            ] is False,
            "M28_SECOND_POST_PERFORMED",
        )
        require(
            m28_result[
                "wordpress_write_performed"
            ] is False,
            "M28_WRITE_PERFORMED",
        )
        require(
            m28_result[
                "wordpress_update_performed"
            ] is False,
            "M28_UPDATE_PERFORMED",
        )
        require(
            m28_result[
                "ready_for_local_finalization"
            ] is True,
            "M28_FINALIZATION_GATE_NOT_READY",
        )
        require(
            m28_result[
                "ready_for_retry"
            ] is False,
            "M28_RETRY_GATE_OPEN",
        )
        require(
            m28_result[
                "ready_for_second_post"
            ] is False,
            "M28_SECOND_POST_GATE_OPEN",
        )

        for field in [
            "final_post_id_matches",
            "final_status_is_publish",
            "final_title_matches",
            "final_categories_match",
            "final_comment_status_is_closed",
            "final_content_matches_m24",
        ]:
            require(
                m28_result[field] is True,
                f"M28_FINAL_CHECK_FALSE:{field}",
            )

        require(
            verification[
                "observed_post_id"
            ] == EXPECTED_POST_ID,
            "M28_VERIFICATION_POST_ID_MISMATCH",
        )
        require(
            verification[
                "observed_status"
            ] == EXPECTED_STATUS,
            "M28_VERIFICATION_STATUS_MISMATCH",
        )
        require(
            verification[
                "observed_title"
            ] == EXPECTED_TITLE,
            "M28_VERIFICATION_TITLE_MISMATCH",
        )
        require(
            sorted(
                verification[
                    "observed_category_ids"
                ]
            ) == EXPECTED_CATEGORIES,
            "M28_VERIFICATION_CATEGORIES_MISMATCH",
        )
        require(
            verification[
                "observed_comment_status"
            ] == EXPECTED_COMMENT_STATUS,
            "M28_VERIFICATION_COMMENT_STATUS_MISMATCH",
        )
        require(
            verification[
                "observed_content_sha256"
            ] == EXPECTED_CONTENT_SHA,
            "M28_VERIFICATION_CONTENT_SHA_MISMATCH",
        )

        require(
            authorization[
                "wordpress_post_id"
            ] == EXPECTED_POST_ID,
            "AUTHORIZATION_POST_ID_MISMATCH",
        )
        require(
            authorization[
                "authorization_consumed"
            ] is False,
            "ORIGINAL_AUTHORIZATION_ARTIFACT_CHANGED",
        )
        require(
            authorization[
                "consumption_count"
            ] == 0,
            "ORIGINAL_AUTHORIZATION_CONSUMPTION_CHANGED",
        )
        require(
            authorization[
                "single_use"
            ] is True,
            "AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            authorization[
                "maximum_update_count"
            ] == 1,
            "AUTHORIZATION_MAXIMUM_UPDATE_NOT_ONE",
        )
        require(
            authorization[
                "reuse_allowed"
            ] is False,
            "AUTHORIZATION_REUSE_ALLOWED_ORIGINAL",
        )
        require(
            authorization[
                "automatic_retry_allowed"
            ] is False,
            "AUTHORIZATION_RETRY_ALLOWED_ORIGINAL",
        )
        require(
            authorization[
                "automatic_reissue_allowed"
            ] is False,
            "AUTHORIZATION_REISSUE_ALLOWED_ORIGINAL",
        )

        require(
            confirmation[
                "execute_now_confirmation_recorded"
            ] is True,
            "CONFIRMATION_NOT_RECORDED",
        )
        require(
            confirmation[
                "confirmation_consumed"
            ] is False,
            "ORIGINAL_CONFIRMATION_ARTIFACT_CHANGED",
        )
        require(
            confirmation[
                "single_use"
            ] is True,
            "CONFIRMATION_NOT_SINGLE_USE",
        )
        require(
            confirmation[
                "maximum_update_count"
            ] == 1,
            "CONFIRMATION_MAXIMUM_UPDATE_NOT_ONE",
        )
        require(
            confirmation[
                "authorization_reuse_allowed"
            ] is False,
            "CONFIRMATION_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            confirmation[
                "automatic_retry_allowed"
            ] is False,
            "CONFIRMATION_RETRY_ALLOWED",
        )
        require(
            confirmation[
                "automatic_reissue_allowed"
            ] is False,
            "CONFIRMATION_REISSUE_ALLOWED",
        )

        rendered_html = M24_RENDERED.read_text(
            encoding="utf-8"
        )
        request_body = payload.get(
            "wordpress_request_body"
        )

        require(
            isinstance(request_body, dict),
            "REQUEST_BODY_NOT_OBJECT",
        )
        require(
            set(request_body.keys())
            == {
                "content",
                "comment_status",
            },
            "REQUEST_FIELD_SET_MISMATCH",
        )
        require(
            request_body["content"]
            == rendered_html,
            "REQUEST_CONTENT_MISMATCH",
        )
        require(
            request_body[
                "comment_status"
            ] == EXPECTED_COMMENT_STATUS,
            "REQUEST_COMMENT_STATUS_NOT_CLOSED",
        )
        require(
            canonical_digest(request_body)
            == EXPECTED_REQUEST_BODY_DIGEST,
            "REQUEST_BODY_DIGEST_MISMATCH",
        )

        require(
            review[
                "human_review_completed"
            ] is True,
            "HUMAN_REVIEW_NOT_COMPLETED",
        )
        require(
            review[
                "human_review_verdict"
            ] == "APPROVED_NO_CHANGE_REQUIRED",
            "HUMAN_REVIEW_NOT_APPROVED",
        )

        require(
            requirement[
                "implementation_authorized"
            ] is False,
            "BACKLIST_IMPLEMENTATION_AUTHORIZED",
        )
        require(
            requirement[
                "included_in_current_wordpress_update"
            ] is False,
            "BACKLIST_INCLUDED_IN_CURRENT_UPDATE",
        )

        source_hashes_after = {
            name: file_sha(path)
            for name, path
            in source_paths.items()
        }

        require(
            source_hashes_before
            == source_hashes_after,
            "SOURCE_ARTIFACTS_MODIFIED",
        )

        finalization_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-"
                "M29-POST-UPDATE-FINALIZE"
            ),
            "document_role": (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
                "POST_UPDATE_FINAL_COMPLETION_EVIDENCE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": EXPECTED_POST_ID,
            "update_series_id": (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_SERIES_V1"
            ),
            "update_completed": True,
            "post_response_validated": True,
            "independent_get_verification_completed": True,
            "final_state_verified": True,
            "final_status": EXPECTED_STATUS,
            "final_title": EXPECTED_TITLE,
            "final_category_ids": EXPECTED_CATEGORIES,
            "final_comment_status": EXPECTED_COMMENT_STATUS,
            "final_content_sha256": EXPECTED_CONTENT_SHA,
            "bound_consumption_digest_sha256": (
                EXPECTED_CONSUMPTION_DIGEST
            ),
            "bound_execution_snapshot_digest_sha256": (
                EXPECTED_EXECUTION_SNAPSHOT_DIGEST
            ),
            "bound_execution_result_digest_sha256": (
                EXPECTED_EXECUTION_RESULT_DIGEST
            ),
            "bound_verification_digest_sha256": (
                EXPECTED_VERIFICATION_DIGEST
            ),
            "bound_m28_result_digest_sha256": (
                EXPECTED_M28_RESULT_DIGEST
            ),
            "bound_authorization_digest_sha256": (
                EXPECTED_AUTHORIZATION_DIGEST
            ),
            "bound_confirmation_digest_sha256": (
                EXPECTED_CONFIRMATION_DIGEST
            ),
            "bound_update_payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "bound_human_review_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "bound_backlist_requirement_digest_sha256": (
                EXPECTED_REQUIREMENT_DIGEST
            ),
            "bound_rollback_digest_sha256": (
                EXPECTED_ROLLBACK_DIGEST
            ),
            "bound_request_body_digest_sha256": (
                EXPECTED_REQUEST_BODY_DIGEST
            ),
            "authorization_consumed": True,
            "confirmation_consumed": True,
            "authorization_consumption_count": 1,
            "confirmation_consumption_count": 1,
            "original_authorization_artifact_immutable": True,
            "original_confirmation_artifact_immutable": True,
            "consumption_recorded_by_separate_immutable_evidence": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "second_post_allowed": False,
            "m27_execute_rerun_allowed": False,
            "m28_verify_rerun_allowed": False,
            "current_update_series_reexecution_allowed": False,
            "rollback_evidence_retained": True,
            "backlist_future_requirement_carried_forward": True,
            "backlist_carousel_implemented_in_current_series": False,
            "backlist_carousel_included_in_current_update": False,
            "backlist_carousel_implementation_authorized": False,
            "suggested_future_backlist_phase": (
                "LS-NEW-SERIES-BACKLIST-1"
            ),
            "source_artifacts_modified": False,
            "dns_resolution_performed": False,
            "network_connection_performed": False,
            "http_communication_performed": False,
            "wordpress_access_performed": False,
            "wordpress_get_performed": False,
            "wordpress_post_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_consumption_performed_in_current_phase": False,
            "x_post_performed": False,
            "current_update_series_closed": True,
            "production_status": "NO_GO",
            "finalized_at_utc": now()
        }

        finalization = add_digest(
            finalization_without_digest,
            "finalization_digest_sha256",
        )
        write_json(
            FINALIZATION,
            finalization,
        )

        closure_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-"
                "M29-POST-UPDATE-FINALIZE"
            ),
            "document_role": (
                "PERMANENT_WORDPRESS_ONE_SHOT_UPDATE_SERIES_CLOSURE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": EXPECTED_POST_ID,
            "update_series_id": (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_SERIES_V1"
            ),
            "closure_state": (
                "CLOSED_COMPLETED_AND_INDEPENDENTLY_VERIFIED"
            ),
            "closure_permanent": True,
            "finalization_digest_sha256": (
                finalization[
                    "finalization_digest_sha256"
                ]
            ),
            "authorization_consumed": True,
            "confirmation_consumed": True,
            "consumption_count": 1,
            "authorization_reuse_permanently_closed": True,
            "automatic_retry_permanently_closed": True,
            "automatic_reissue_permanently_closed": True,
            "second_post_permanently_closed": True,
            "m27_execute_rerun_permanently_closed": True,
            "m28_verify_rerun_permanently_closed": True,
            "current_update_series_reexecution_permanently_closed": True,
            "additional_wordpress_update_authorized": False,
            "additional_wordpress_post_authorized": False,
            "rollback_evidence_retained": True,
            "backlist_future_requirement_carried_forward": True,
            "backlist_implementation_authorized": False,
            "required_next_phase_for_current_update_series": None,
            "suggested_separate_future_phase": (
                "LS-NEW-SERIES-BACKLIST-1"
            ),
            "ready_for_retry": False,
            "ready_for_second_post": False,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "production_status": "NO_GO",
            "closed_at_utc": now()
        }

        closure = add_digest(
            closure_without_digest,
            "closure_digest_sha256",
        )
        write_json(
            CLOSURE,
            closure,
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-"
                "M29-POST-UPDATE-FINALIZE"
            ),
            "status": (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
                "POST_UPDATE_FINALIZATION_RECORDED_LOCAL_ONLY_"
                "SERIES_CLOSED_NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "ONE_SHOT_UPDATE_AND_INDEPENDENT_GET_VERIFICATION_"
                "FINALIZED_RETRY_REISSUE_AND_SECOND_POST_"
                "PERMANENTLY_CLOSED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": EXPECTED_POST_ID,
            "finalization_path": str(
                FINALIZATION.relative_to(ROOT)
            ),
            "finalization_digest_sha256": (
                finalization[
                    "finalization_digest_sha256"
                ]
            ),
            "closure_path": str(
                CLOSURE.relative_to(ROOT)
            ),
            "closure_digest_sha256": (
                closure[
                    "closure_digest_sha256"
                ]
            ),
            "update_completed": True,
            "post_response_validated": True,
            "independent_get_verification_completed": True,
            "final_state_verified": True,
            "final_status_is_publish": True,
            "final_title_matches": True,
            "final_categories_match": True,
            "final_comment_status_is_closed": True,
            "final_content_matches_m24": True,
            "authorization_consumed": True,
            "confirmation_consumed": True,
            "authorization_consumption_count": 1,
            "confirmation_consumption_count": 1,
            "authorization_reused": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "second_post_performed": False,
            "authorization_reuse_permanently_closed": True,
            "automatic_retry_permanently_closed": True,
            "automatic_reissue_permanently_closed": True,
            "second_post_permanently_closed": True,
            "current_update_series_reexecution_permanently_closed": True,
            "source_artifacts_modified": False,
            "rollback_evidence_retained": True,
            "backlist_future_requirement_carried_forward": True,
            "backlist_carousel_implemented": False,
            "backlist_carousel_included_in_current_update": False,
            "backlist_carousel_implementation_authorized": False,
            "suggested_future_backlist_phase": (
                "LS-NEW-SERIES-BACKLIST-1"
            ),
            "dns_resolution_performed": False,
            "network_connection_performed": False,
            "http_communication_performed": False,
            "wordpress_access_performed": False,
            "wordpress_get_performed": False,
            "wordpress_post_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_consumption_performed_in_current_phase": False,
            "x_post_performed": False,
            "current_update_series_closed": True,
            "required_next_phase_for_current_update_series": None,
            "ready_for_retry": False,
            "ready_for_second_post": False,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "production_status": "NO_GO",
            "completed_at_utc": now()
        }

        result = add_digest(
            result_without_digest,
            "result_digest_sha256",
        )
        write_json(
            RESULT,
            result,
        )

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M29-POST-UPDATE-FINALIZE

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Update completed: `true`
- POST response validated: `true`
- Independent GET verification completed: `true`
- Final state verified: `true`
- Final status: `publish`
- Final category ID: `10`
- Final comment status: `closed`
- Final content matches M24: `true`
- Authorization consumed: `true`
- Confirmation consumed: `true`
- Consumption count: `1`
- Authorization reuse permanently closed: `true`
- Automatic retry permanently closed: `true`
- Automatic reissue permanently closed: `true`
- Second POST permanently closed: `true`
- Current update-series reexecution permanently closed: `true`
- Rollback evidence retained: `true`
- Backlist future requirement carried forward: `true`
- Backlist implemented in current series: `false`
- Network performed in M29: `false`
- WordPress access performed in M29: `false`
- WordPress update performed in M29: `false`
- Current update series closed: `true`
- Required next phase for current update series: `none`
- Production status: `NO_GO`
""",
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-"
                        "M29-POST-UPDATE-FINALIZE"
                    ),
                    "status": (
                        "BLOCKED_POST_UPDATE_FINALIZATION_"
                        "NO_NETWORK_NO_WORDPRESS"
                    ),
                    "safe_error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_consumption_performed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
