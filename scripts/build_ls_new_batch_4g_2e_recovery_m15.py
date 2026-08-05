#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def block_network(
    *args: Any,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "NETWORK_OPERATION_BLOCKED_BY_M15"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_draft_human_review_"
    "no_change_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m15_approval.json"
)

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)
M12_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
M13_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)
M13_SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_response.json"
)
M13_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m13_result.json"
)
M14_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m14_result.json"
)

REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_post_execution_human_review.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m15_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m15_"
    "wordpress_draft_human_review_report.md"
)

EXPECTED_POST_ID = 192
EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
)
EXPECTED_ARTICLE_SHA = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
EXPECTED_PAYLOAD_SHA = (
    "30a70be4110e863a85e2896f69f5b3e5"
    "1d814a6fd82d5489f899d8a244166d8f"
)
EXPECTED_PAYLOAD_DIGEST = (
    "2ab27b59305dbae98f997ca3a4604002"
    "98152f173ef605b534df922c187411c6"
)
EXPECTED_M12_AUTH_SHA = (
    "7c9662a7a13502e165862e4524278992"
    "28794bce6904a0215c45a5b54ba1142b"
)
EXPECTED_M12_AUTH_DIGEST = (
    "d3ede61a71d75cbbc00a594f0a8d319a"
    "ed0e598bd9c061609a52bed7e96d07c3"
)
EXPECTED_M13_RESULT_DIGEST = (
    "34bb7a2cd15cfd829a805c1e974ca62c"
    "c453036132a25c41d7fd17b3ae681e0d"
)
EXPECTED_M13_CONSUMPTION_DIGEST = (
    "a9c96f8fddc4bfebeebce2d535936a21"
    "e9214bb9ac6688e7277aa6def171aaba"
)
EXPECTED_M14_RESULT_DIGEST = (
    "364cf76c3db0d321f9dc31251224393b"
    "403030524bb834cb147dc5f3f4e2ef61"
)
EXPECTED_ATTEMPT_ID = (
    "fb8742ae-b59d-4f59-a4f0-f6eb279e6629"
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


def file_sha(
    path: Path,
) -> str:
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
    expected: str | None = None,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        canonical_digest(comparable)
        == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"DIGEST_EXPECTED_MISMATCH:{field}",
        )

    return stored


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
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
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_text(
    path: Path,
    value: str,
) -> None:
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


def main() -> int:
    source_paths = {
        "article": ARTICLE,
        "payload": PAYLOAD,
        "m12_authorization": M12_AUTH,
        "m13_consumption": M13_CONSUMPTION,
        "m13_secret_response": (
            M13_SECRET_RESPONSE
        ),
        "m13_result": M13_RESULT,
        "m14_result": M14_RESULT,
    }

    try:
        for output in [
            REVIEW,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M15_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M15"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_DRAFT_HUMAN_REVIEW_"
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval[
                "human_explicit_approval"
            ] is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        require(
            source_hashes["article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["payload"]
            == EXPECTED_PAYLOAD_SHA,
            "PAYLOAD_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes[
                "m12_authorization"
            ] == EXPECTED_M12_AUTH_SHA,
            "M12_AUTHORIZATION_FILE_SHA_MISMATCH",
        )

        require(
            stat.S_IMODE(
                PAYLOAD.stat().st_mode
            ) == 0o600,
            "PAYLOAD_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M13_CONSUMPTION.stat().st_mode
            ) == 0o600,
            "M13_CONSUMPTION_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M13_SECRET_RESPONSE.stat().st_mode
            ) == 0o600,
            "M13_SECRET_RESPONSE_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M13_RESULT.stat().st_mode
            ) == 0o600,
            "M13_RESULT_MODE_NOT_0600",
        )

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        m12_auth = load_json(M12_AUTH)
        consumption = load_json(
            M13_CONSUMPTION
        )
        secret_response = load_json(
            M13_SECRET_RESPONSE
        )
        m13_result = load_json(
            M13_RESULT
        )
        m14_result = load_json(
            M14_RESULT
        )

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            m12_auth,
            "authorization_digest_sha256",
            EXPECTED_M12_AUTH_DIGEST,
        )
        verify_digest(
            consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M13_CONSUMPTION_DIGEST,
        )
        verify_digest(
            secret_response,
            "secret_response_digest_sha256",
        )
        verify_digest(
            m13_result,
            "result_digest_sha256",
            EXPECTED_M13_RESULT_DIGEST,
        )
        verify_digest(
            m14_result,
            "result_digest_sha256",
            EXPECTED_M14_RESULT_DIGEST,
        )

        require(
            m14_result["status"]
            == (
                "PASS_WORDPRESS_DRAFT_POST_EXECUTION_"
                "EVIDENCE_VERIFIED_GET_ONLY_NO_WRITE"
            ),
            "M14_STATUS_MISMATCH",
        )
        require(
            m14_result["post_id"]
            == EXPECTED_POST_ID,
            "M14_POST_ID_MISMATCH",
        )
        require(
            m14_result[
                "post_id_verified"
            ] is True,
            "M14_POST_ID_NOT_VERIFIED",
        )
        require(
            m14_result["post_status"]
            == "draft",
            "M14_STATUS_NOT_DRAFT",
        )
        require(
            m14_result[
                "title_exact_match"
            ] is True,
            "M14_TITLE_MISMATCH",
        )
        require(
            m14_result[
                "content_exact_match"
            ] is True,
            "M14_CONTENT_MISMATCH",
        )
        require(
            m14_result[
                "category_id_10_verified"
            ] is True,
            "M14_CATEGORY_MISMATCH",
        )
        require(
            m14_result[
                "wordpress_write_performed"
            ] is False,
            "M14_WRITE_PERFORMED",
        )
        require(
            m14_result[
                "ready_for_human_wordpress_draft_review"
            ] is True,
            "M14_HUMAN_REVIEW_NOT_READY",
        )
        require(
            m14_result[
                "ready_for_wordpress_publish"
            ] is False,
            "M14_PUBLISH_GATE_OPEN",
        )

        require(
            m13_result["status"]
            == (
                "PASS_WORDPRESS_DRAFT_CREATED_"
                "ONE_SHOT_AUTHORIZATION_CONSUMED_"
                "NO_PUBLISH_NO_RETRY"
            ),
            "M13_STATUS_MISMATCH",
        )
        require(
            m13_result[
                "wordpress_post_id"
            ] == EXPECTED_POST_ID,
            "M13_POST_ID_MISMATCH",
        )
        require(
            m13_result[
                "execution_attempt_id"
            ] == EXPECTED_ATTEMPT_ID,
            "M13_ATTEMPT_ID_MISMATCH",
        )
        require(
            m13_result[
                "authorization_consumed"
            ] is True,
            "M13_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            m13_result[
                "authorization_reuse_allowed"
            ] is False,
            "M13_REUSE_ALLOWED",
        )
        require(
            m13_result[
                "automatic_retry_allowed"
            ] is False,
            "M13_RETRY_ALLOWED",
        )
        require(
            m13_result[
                "automatic_reissue_allowed"
            ] is False,
            "M13_REISSUE_ALLOWED",
        )
        require(
            m13_result[
                "wordpress_published"
            ] is False,
            "M13_PUBLISHED_TRUE",
        )

        require(
            consumption[
                "execution_attempt_id"
            ] == EXPECTED_ATTEMPT_ID,
            "CONSUMPTION_ATTEMPT_ID_MISMATCH",
        )
        require(
            consumption[
                "authorization_consumed"
            ] is True,
            "CONSUMPTION_STATE_FALSE",
        )
        require(
            consumption[
                "authorization_reuse_allowed"
            ] is False,
            "CONSUMPTION_REUSE_ALLOWED",
        )
        require(
            consumption[
                "automatic_retry_allowed"
            ] is False,
            "CONSUMPTION_RETRY_ALLOWED",
        )
        require(
            consumption[
                "automatic_reissue_allowed"
            ] is False,
            "CONSUMPTION_REISSUE_ALLOWED",
        )

        require(
            secret_response[
                "execution_attempt_id"
            ] == EXPECTED_ATTEMPT_ID,
            "SECRET_RESPONSE_ATTEMPT_ID_MISMATCH",
        )
        require(
            secret_response[
                "response_received"
            ] is True,
            "SECRET_RESPONSE_NOT_RECEIVED",
        )
        require(
            secret_response[
                "http_status"
            ] == 201,
            "SECRET_RESPONSE_HTTP_STATUS_MISMATCH",
        )

        require(
            payload["title"]
            == EXPECTED_TITLE,
            "PAYLOAD_TITLE_MISMATCH",
        )
        require(
            payload["title"]
            == article["article_title"],
            "ARTICLE_TITLE_MISMATCH",
        )
        require(
            payload["content_html"]
            == article["content_html"],
            "ARTICLE_CONTENT_MISMATCH",
        )
        require(
            payload["status"] == "draft",
            "PAYLOAD_STATUS_NOT_DRAFT",
        )
        require(
            payload["post_status"]
            == "draft",
            "PAYLOAD_POST_STATUS_NOT_DRAFT",
        )
        require(
            payload["publish"] is False,
            "PAYLOAD_PUBLISH_TRUE",
        )
        require(
            payload["category_id"] == 10,
            "PAYLOAD_CATEGORY_ID_MISMATCH",
        )
        require(
            payload["categories"] == [10],
            "PAYLOAD_CATEGORIES_MISMATCH",
        )

        attestation = approval[
            "human_review_attestation"
        ]

        expected_attestation = {
            "title_confirmed": True,
            "draft_status_confirmed": True,
            "category_confirmed": True,
            "body_layout_confirmed": True,
            "dmm_button_display_confirmed": True,
            "dmm_button_enabled_state_confirmed": True,
            "secret_information_non_exposure_confirmed": True,
            "publish_action_not_performed": True,
            "change_required": False,
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
        }

        require(
            attestation
            == expected_attestation,
            "HUMAN_REVIEW_ATTESTATION_MISMATCH",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        review_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M15"
            ),
            "document_role": (
                "WORDPRESS_DRAFT_POST_EXECUTION_"
                "HUMAN_REVIEW_EVIDENCE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "reviewed_by": "HUMAN_OPERATOR",
            "review_method": (
                "WORDPRESS_ADMIN_VISUAL_REVIEW"
            ),
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "human_review_complete": True,
            "title_confirmed": True,
            "draft_status_confirmed": True,
            "category_confirmed": True,
            "body_layout_confirmed": True,
            "dmm_button_display_confirmed": True,
            "dmm_button_enabled_state_confirmed": True,
            "secret_information_non_exposure_confirmed": True,
            "publish_action_not_performed": True,
            "change_required": False,
            "change_request_created": False,
            "m14_result_digest_sha256": (
                EXPECTED_M14_RESULT_DIGEST
            ),
            "m13_result_digest_sha256": (
                EXPECTED_M13_RESULT_DIGEST
            ),
            "m13_consumption_digest_sha256": (
                EXPECTED_M13_CONSUMPTION_DIGEST
            ),
            "m13_execution_attempt_id": (
                EXPECTED_ATTEMPT_ID
            ),
            "payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "article_file_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "m12_authorization_file_sha256": (
                EXPECTED_M12_AUTH_SHA
            ),
            "m12_authorization_digest_sha256": (
                EXPECTED_M12_AUTH_DIGEST
            ),
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_updated": False,
            "wordpress_published": False,
            "authorization_issued": False,
            "authorization_consumed_in_this_phase": False,
            "m13_rerun_performed": False,
            "m14_rerun_performed": False,
            "x_post_performed": False,
            "credential_accessed": False,
            "credential_values_output": False,
            "full_payload_output": False,
            "full_post_content_output": False,
            "full_wordpress_response_output": False,
            "full_affiliate_url_output": False,
            "dmm_identifier_output": False,
            "production_status": "NO_GO",
            "ready_for_separate_wordpress_publication_authorization_gate": True,
            "ready_for_wordpress_publish": False,
            "reviewed_at_utc": now()
        }

        review = copy.deepcopy(
            review_without_digest
        )
        review[
            "human_review_evidence_digest_sha256"
        ] = canonical_digest(
            review_without_digest
        )

        write_json(REVIEW, review)

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M15"
            ),
            "status": (
                "PASS_WORDPRESS_DRAFT_HUMAN_"
                "REVIEW_RECORDED_NO_CHANGE_"
                "REQUIRED_NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "HUMAN_REVIEW_APPROVED_READY_"
                "FOR_SEPARATE_WORDPRESS_"
                "PUBLICATION_AUTHORIZATION_GATE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "human_review_complete": True,
            "change_required": False,
            "human_review_path": str(
                REVIEW.relative_to(ROOT)
            ),
            "human_review_evidence_digest_sha256": (
                review[
                    "human_review_evidence_digest_sha256"
                ]
            ),
            "m14_result_digest_sha256": (
                EXPECTED_M14_RESULT_DIGEST
            ),
            "m13_result_digest_sha256": (
                EXPECTED_M13_RESULT_DIGEST
            ),
            "m13_consumption_digest_sha256": (
                EXPECTED_M13_CONSUMPTION_DIGEST
            ),
            "payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "source_artifacts_modified": False,
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_updated": False,
            "wordpress_published": False,
            "authorization_issued": False,
            "authorization_consumed_in_this_phase": False,
            "m13_rerun_performed": False,
            "m14_rerun_performed": False,
            "x_post_performed": False,
            "credential_accessed": False,
            "secret_values_output": False,
            "production_status": "NO_GO",
            "safety_state": (
                "WORDPRESS_DRAFT_HUMAN_REVIEW_"
                "APPROVED_NO_CHANGE_REQUIRED_"
                "AWAITING_SEPARATE_PUBLICATION_GATE"
            ),
            "ready_for_separate_wordpress_publication_authorization_gate": True,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        result = copy.deepcopy(
            result_without_digest
        )
        result[
            "result_digest_sha256"
        ] = canonical_digest(
            result_without_digest
        )

        write_json(RESULT, result)

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M15

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Human review complete: `true`
- Review verdict: `APPROVED_NO_CHANGE_REQUIRED`
- Change required: `false`
- Title confirmed: `true`
- Draft status confirmed: `true`
- Category confirmed: `true`
- Body layout confirmed: `true`
- DMM button display confirmed: `true`
- DMM button enabled state confirmed: `true`
- Secret information non-exposure confirmed: `true`
- Publish action performed: `false`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress write performed: `false`
- Authorization consumed in this phase: `false`
- Production status: `NO_GO`
- Ready for separate WordPress publication authorization gate: `true`
- Ready for WordPress publish: `false`
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
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M15"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_DRAFT_"
                        "HUMAN_REVIEW_EVIDENCE_RECORDING"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_write_performed": False,
                    "wordpress_published": False,
                    "authorization_consumed_in_this_phase": False,
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
