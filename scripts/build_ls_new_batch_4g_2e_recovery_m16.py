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
        "NETWORK_OPERATION_BLOCKED_BY_M16"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_publication_one_shot_"
    "authorization_gate_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m16_approval.json"
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
M13_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m13_result.json"
)
M14_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m14_result.json"
)
M15_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_post_execution_human_review.json"
)
M15_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m15_result.json"
)

AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m16_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m16_"
    "wordpress_publication_authorization_gate_report.md"
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
EXPECTED_M15_REVIEW_DIGEST = (
    "be8aafa191df793ecbe2695b662378fe"
    "f078ce42ae4169a93651a9d2b6141d4c"
)
EXPECTED_M15_RESULT_DIGEST = (
    "03d777e3e34c4d68c4b55027db87f7b"
    "20cee59f947640f3d68b125d6c79f5b06"
)
EXPECTED_M13_ATTEMPT_ID = (
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
        "m13_result": M13_RESULT,
        "m14_result": M14_RESULT,
        "m15_review": M15_REVIEW,
        "m15_result": M15_RESULT,
    }

    try:
        for output in [
            AUTHORIZATION,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M16_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M16",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["operation_mode"]
            == "LOCAL_PUBLICATION_AUTHORIZATION_ISSUANCE_ONLY",
            "POLICY_OPERATION_MODE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_PUBLICATION_ONE_SHOT_"
                "AUTHORIZATION_GATE_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )
        require(
            approval["authorization_issue_approved"]
            is True,
            "AUTHORIZATION_ISSUE_NOT_APPROVED",
        )
        require(
            approval["authorization_consumption_approved"]
            is False,
            "AUTHORIZATION_CONSUMPTION_APPROVED",
        )
        require(
            approval["wordpress_publish_approved"]
            is False,
            "WORDPRESS_PUBLISH_APPROVED",
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
            source_hashes["m12_authorization"]
            == EXPECTED_M12_AUTH_SHA,
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
                M13_RESULT.stat().st_mode
            ) == 0o600,
            "M13_RESULT_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M15_REVIEW.stat().st_mode
            ) == 0o600,
            "M15_REVIEW_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M15_RESULT.stat().st_mode
            ) == 0o600,
            "M15_RESULT_MODE_NOT_0600",
        )

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        m12_auth = load_json(M12_AUTH)
        m13_consumption = load_json(
            M13_CONSUMPTION
        )
        m13_result = load_json(M13_RESULT)
        m14_result = load_json(M14_RESULT)
        m15_review = load_json(M15_REVIEW)
        m15_result = load_json(M15_RESULT)

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
            m13_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M13_CONSUMPTION_DIGEST,
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
        verify_digest(
            m15_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M15_REVIEW_DIGEST,
        )
        verify_digest(
            m15_result,
            "result_digest_sha256",
            EXPECTED_M15_RESULT_DIGEST,
        )

        require(
            payload["title"] == EXPECTED_TITLE,
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
            payload["post_status"] == "draft",
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

        require(
            m13_result["wordpress_post_id"]
            == EXPECTED_POST_ID,
            "M13_POST_ID_MISMATCH",
        )
        require(
            m13_result["execution_attempt_id"]
            == EXPECTED_M13_ATTEMPT_ID,
            "M13_ATTEMPT_ID_MISMATCH",
        )
        require(
            m13_result["authorization_consumed"]
            is True,
            "M13_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            m13_result["authorization_reuse_allowed"]
            is False,
            "M13_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m13_result["automatic_retry_allowed"]
            is False,
            "M13_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m13_result["automatic_reissue_allowed"]
            is False,
            "M13_AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            m13_result["wordpress_published"]
            is False,
            "M13_WORDPRESS_PUBLISHED",
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
            m14_result["post_id"] == EXPECTED_POST_ID,
            "M14_POST_ID_MISMATCH",
        )
        require(
            m14_result["post_status"] == "draft",
            "M14_POST_STATUS_NOT_DRAFT",
        )
        require(
            m14_result["title_exact_match"]
            is True,
            "M14_TITLE_MISMATCH",
        )
        require(
            m14_result["content_exact_match"]
            is True,
            "M14_CONTENT_MISMATCH",
        )
        require(
            m14_result["category_id_10_verified"]
            is True,
            "M14_CATEGORY_MISMATCH",
        )
        require(
            m14_result["wordpress_write_performed"]
            is False,
            "M14_WRITE_PERFORMED",
        )
        require(
            m14_result["wordpress_published"]
            is False,
            "M14_PUBLISHED",
        )

        require(
            m15_review["wordpress_post_id"]
            == EXPECTED_POST_ID,
            "M15_REVIEW_POST_ID_MISMATCH",
        )
        require(
            m15_review["review_verdict"]
            == "APPROVED_NO_CHANGE_REQUIRED",
            "M15_REVIEW_VERDICT_MISMATCH",
        )
        require(
            m15_review["human_review_complete"]
            is True,
            "M15_HUMAN_REVIEW_INCOMPLETE",
        )
        require(
            m15_review["title_confirmed"]
            is True,
            "M15_TITLE_NOT_CONFIRMED",
        )
        require(
            m15_review["draft_status_confirmed"]
            is True,
            "M15_DRAFT_STATUS_NOT_CONFIRMED",
        )
        require(
            m15_review["category_confirmed"]
            is True,
            "M15_CATEGORY_NOT_CONFIRMED",
        )
        require(
            m15_review["body_layout_confirmed"]
            is True,
            "M15_BODY_LAYOUT_NOT_CONFIRMED",
        )
        require(
            m15_review["dmm_button_display_confirmed"]
            is True,
            "M15_DMM_BUTTON_NOT_CONFIRMED",
        )
        require(
            m15_review["secret_information_non_exposure_confirmed"]
            is True,
            "M15_SECRET_NON_EXPOSURE_NOT_CONFIRMED",
        )
        require(
            m15_review["publish_action_not_performed"]
            is True,
            "M15_PUBLISH_ACTION_PERFORMED",
        )
        require(
            m15_review["change_required"]
            is False,
            "M15_CHANGE_REQUIRED",
        )

        require(
            m15_result["status"]
            == (
                "PASS_WORDPRESS_DRAFT_HUMAN_"
                "REVIEW_RECORDED_NO_CHANGE_"
                "REQUIRED_NO_WORDPRESS_ACCESS"
            ),
            "M15_RESULT_STATUS_MISMATCH",
        )
        require(
            m15_result[
                "ready_for_separate_wordpress_publication_authorization_gate"
            ] is True,
            "M15_PUBLICATION_AUTHORIZATION_GATE_NOT_READY",
        )
        require(
            m15_result["ready_for_wordpress_publish"]
            is False,
            "M15_PUBLISH_GATE_ALREADY_OPEN",
        )
        require(
            m15_result["network_connection_performed"]
            is False,
            "M15_NETWORK_PERFORMED",
        )
        require(
            m15_result["wordpress_access_performed"]
            is False,
            "M15_WORDPRESS_ACCESS_PERFORMED",
        )
        require(
            m15_result["wordpress_write_performed"]
            is False,
            "M15_WORDPRESS_WRITE_PERFORMED",
        )
        require(
            m15_result["wordpress_published"]
            is False,
            "M15_WORDPRESS_PUBLISHED",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path) == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        authorization_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M16"
            ),
            "document_role": (
                "WORDPRESS_PUBLICATION_ONE_SHOT_AUTHORIZATION"
            ),
            "authorization_id": (
                "WORDPRESS_PUBLICATION_ONE_SHOT_AUTHORIZATION_V1"
            ),
            "authorization_scope": (
                "PUBLISH_EXISTING_WORDPRESS_DRAFT_192_ONCE_ONLY"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "expected_title": EXPECTED_TITLE,
            "expected_category_id": 10,
            "required_current_post_status": "draft",
            "allowed_target_post_status": "publish",
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "maximum_publish_count": 1,
            "explicit_execute_now_confirmation_required": True,
            "planned_preflight_phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M17-PRE-NETWORK"
            ),
            "planned_execution_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
            ),
            "m15_result_digest_sha256": (
                EXPECTED_M15_RESULT_DIGEST
            ),
            "m15_human_review_digest_sha256": (
                EXPECTED_M15_REVIEW_DIGEST
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
            "wordpress_get_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_publish_performed": False,
            "credential_accessed": False,
            "authorization_consumed_in_this_phase": False,
            "m13_rerun_performed": False,
            "m14_rerun_performed": False,
            "m15_rerun_performed": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "ready_for_wordpress_publication_preflight": True,
            "ready_for_wordpress_publication_execute_now_gate": False,
            "ready_for_wordpress_publish": False,
            "issued_by": "HUMAN_OPERATOR_APPROVED_GATE",
            "issued_at_utc": now()
        }

        authorization = copy.deepcopy(
            authorization_without_digest
        )
        authorization[
            "authorization_digest_sha256"
        ] = canonical_digest(
            authorization_without_digest
        )

        write_json(
            AUTHORIZATION,
            authorization,
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M16"
            ),
            "status": (
                "PASS_WORDPRESS_PUBLICATION_ONE_SHOT_"
                "AUTHORIZATION_GATE_FIXED_NO_NETWORK_NO_WORDPRESS"
            ),
            "decision": (
                "WORDPRESS_PUBLICATION_AUTHORIZATION_"
                "RECORDED_AWAITING_SEPARATE_PREFLIGHT_"
                "AND_EXPLICIT_EXECUTE_NOW_CONFIRMATION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "authorization_id": (
                "WORDPRESS_PUBLICATION_ONE_SHOT_AUTHORIZATION_V1"
            ),
            "authorization_path": str(
                AUTHORIZATION.relative_to(ROOT)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "maximum_publish_count": 1,
            "explicit_execute_now_confirmation_required": True,
            "planned_preflight_phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M17-PRE-NETWORK"
            ),
            "planned_execution_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
            ),
            "m15_result_digest_sha256": (
                EXPECTED_M15_RESULT_DIGEST
            ),
            "m15_human_review_digest_sha256": (
                EXPECTED_M15_REVIEW_DIGEST
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
            "wordpress_get_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_publish_performed": False,
            "credential_accessed": False,
            "authorization_consumed_in_this_phase": False,
            "m13_rerun_performed": False,
            "m14_rerun_performed": False,
            "m15_rerun_performed": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "WORDPRESS_PUBLICATION_AUTHORIZATION_"
                "ISSUED_UNCONSUMED_AWAITING_PREFLIGHT"
            ),
            "ready_for_wordpress_publication_preflight": True,
            "ready_for_wordpress_publication_execute_now_gate": False,
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M16

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Authorization ID: `WORDPRESS_PUBLICATION_ONE_SHOT_AUTHORIZATION_V1`
- Authorization single use: `true`
- Authorization consumed: `false`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- Maximum publish count: `1`
- Explicit execute-now confirmation required: `true`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress write performed: `false`
- WordPress publish performed: `false`
- Credential accessed: `false`
- Production status: `NO_GO`
- Ready for publication preflight: `true`
- Ready for publication execute-now gate: `false`
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M16"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_PUBLICATION_"
                        "AUTHORIZATION_GATE_NO_NETWORK_NO_WORDPRESS"
                    ),
                    "error_code": str(exc),
                    "authorization_issued": False,
                    "authorization_consumed": False,
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_write_performed": False,
                    "wordpress_publish_performed": False,
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
