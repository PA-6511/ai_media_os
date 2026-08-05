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
        "NETWORK_OPERATION_BLOCKED_BY_M27_EXECUTE_NOW_CONFIRMATION"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_layout_update_"
    "execute_now_confirmation_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m27_execute_now_confirmation_approval.json"
)

M27_RETRY_SNAPSHOT = ROOT / (
    "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_revised_single_get_retry_snapshot.json"
)
M27_RETRY_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_retry_approval_result.json"
)
M26_AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_one_shot_authorization.json"
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

CONFIRMATION = ROOT / (
    "exchange/confirmations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "execute_now_confirmation.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_execute_now_confirmation_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m27_"
    "execute_now_confirmation_report.md"
)

EXPECTED_SNAPSHOT_DIGEST = (
    "2a86005667e2dbbb3a93fadb72ed60ae"
    "1840de625e2ad6b55dad30671134a384"
)
EXPECTED_RETRY_RESULT_DIGEST = (
    "a127d49abcdeb6784e1602cb339a0e1d"
    "ebb7268675183ad03a8c49c20f611ab4"
)
EXPECTED_AUTHORIZATION_DIGEST = (
    "d7f53a0eb02a037cde4b6ab71b4b026b"
    "79eb8c2d2c08a95a8bec5f1ad0b6e615"
)
EXPECTED_RENDERED_SHA = (
    "dc938ae164c70130a5fb27692d71c97c"
    "c367a8985c44c2c333801b337ee6caf4"
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


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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
    sources = {
        "m27_retry_snapshot": M27_RETRY_SNAPSHOT,
        "m27_retry_result": M27_RETRY_RESULT,
        "m26_authorization": M26_AUTHORIZATION,
        "m24_rendered": M24_RENDERED,
        "m24_payload": M24_PAYLOAD,
        "m25_review": M25_REVIEW,
        "m25_requirement": M25_REQUIREMENT,
        "rollback": ROLLBACK,
    }

    try:
        for output in [
            CONFIRMATION,
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
                "M27-EXECUTE-NOW-CONFIRMATION"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_EXECUTE_NOW_CONFIRMED"
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
            for name, path in sources.items()
        }

        for name, path in sources.items():
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

        snapshot = load_json(
            M27_RETRY_SNAPSHOT
        )
        retry_result = load_json(
            M27_RETRY_RESULT
        )
        authorization = load_json(
            M26_AUTHORIZATION
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
            snapshot,
            "snapshot_digest_sha256",
            EXPECTED_SNAPSHOT_DIGEST,
        )
        verify_digest(
            retry_result,
            "result_digest_sha256",
            EXPECTED_RETRY_RESULT_DIGEST,
        )
        verify_digest(
            authorization,
            "authorization_digest_sha256",
            EXPECTED_AUTHORIZATION_DIGEST,
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
            == EXPECTED_RENDERED_SHA,
            "M24_RENDERED_SHA_MISMATCH",
        )

        require(
            retry_result[
                "preflight_passed"
            ] is True,
            "M27_RETRY_PREFLIGHT_NOT_PASSED",
        )
        require(
            retry_result[
                "http_status_code"
            ] == 200,
            "M27_RETRY_HTTP_NOT_200",
        )

        for field in [
            "current_post_id_matches",
            "current_status_is_publish",
            "current_title_matches",
            "current_categories_match",
            "current_content_matches_rollback",
            "update_content_matches_m24",
            "request_body_digest_matches",
            "ready_for_execute_now_confirmation",
        ]:
            require(
                retry_result[field] is True,
                f"M27_RETRY_CHECK_FALSE:{field}",
            )

        require(
            retry_result[
                "current_comment_status"
            ] == "open",
            "CURRENT_COMMENT_STATUS_NOT_OPEN",
        )
        require(
            retry_result[
                "wordpress_write_performed"
            ] is False,
            "PREFLIGHT_WORDPRESS_WRITE_PERFORMED",
        )
        require(
            retry_result[
                "wordpress_update_performed"
            ] is False,
            "PREFLIGHT_WORDPRESS_UPDATE_PERFORMED",
        )
        require(
            retry_result[
                "authorization_consumed"
            ] is False,
            "PREFLIGHT_AUTHORIZATION_CONSUMED",
        )

        require(
            authorization[
                "wordpress_post_id"
            ] == 192,
            "AUTHORIZATION_POST_ID_MISMATCH",
        )
        require(
            authorization[
                "authorization_consumed"
            ] is False,
            "AUTHORIZATION_ALREADY_CONSUMED",
        )
        require(
            authorization[
                "consumption_count"
            ] == 0,
            "AUTHORIZATION_CONSUMPTION_COUNT_NOT_ZERO",
        )
        require(
            authorization["single_use"]
            is True,
            "AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            authorization[
                "maximum_update_count"
            ] == 1,
            "MAXIMUM_UPDATE_COUNT_NOT_ONE",
        )
        require(
            authorization[
                "reuse_allowed"
            ] is False,
            "AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            authorization[
                "automatic_retry_allowed"
            ] is False,
            "AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            authorization[
                "automatic_reissue_allowed"
            ] is False,
            "AUTOMATIC_REISSUE_ALLOWED",
        )

        rendered = M24_RENDERED.read_text(
            encoding="utf-8"
        )
        request_body = payload[
            "wordpress_request_body"
        ]

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
            == rendered,
            "REQUEST_CONTENT_MISMATCH",
        )
        require(
            request_body[
                "comment_status"
            ] == "closed",
            "REQUEST_COMMENT_STATUS_NOT_CLOSED",
        )
        require(
            canonical_digest(request_body)
            == EXPECTED_REQUEST_BODY_DIGEST,
            "REQUEST_BODY_DIGEST_MISMATCH",
        )

        for field in [
            "title",
            "status",
            "categories",
            "slug",
            "excerpt",
            "featured_media",
        ]:
            require(
                field not in request_body,
                f"FORBIDDEN_FIELD_PRESENT:{field}",
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

        confirmation_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-"
                "M27-EXECUTE-NOW-CONFIRMATION"
            ),
            "document_role": (
                "WORDPRESS_ONE_SHOT_UPDATE_"
                "EXECUTE_NOW_CONFIRMATION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "confirmation_label": (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_EXECUTE_NOW_CONFIRMED"
            ),
            "execute_now_confirmation_recorded": True,
            "confirmation_consumed": False,
            "confirmed_future_execution_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE"
            ),
            "confirmed_update_fields": [
                "content",
                "comment_status",
            ],
            "expected_pre_update_comment_status": "open",
            "target_comment_status": "closed",
            "bound_snapshot_digest_sha256": (
                EXPECTED_SNAPSHOT_DIGEST
            ),
            "bound_preflight_result_digest_sha256": (
                EXPECTED_RETRY_RESULT_DIGEST
            ),
            "bound_authorization_digest_sha256": (
                EXPECTED_AUTHORIZATION_DIGEST
            ),
            "bound_rendered_content_sha256": (
                EXPECTED_RENDERED_SHA
            ),
            "bound_update_payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "bound_human_review_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "bound_rollback_digest_sha256": (
                EXPECTED_ROLLBACK_DIGEST
            ),
            "bound_request_body_digest_sha256": (
                EXPECTED_REQUEST_BODY_DIGEST
            ),
            "single_use": True,
            "maximum_update_count": 1,
            "authorization_consumed": False,
            "authorization_consumption_count": 0,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "backlist_carousel_included": False,
            "title_change_allowed": False,
            "status_change_allowed": False,
            "categories_change_allowed": False,
            "slug_change_allowed": False,
            "excerpt_change_allowed": False,
            "featured_media_change_allowed": False,
            "wordpress_access_performed": False,
            "wordpress_get_performed": False,
            "wordpress_post_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "authorization_consumed_in_current_phase": False,
            "separate_execution_approval_required": True,
            "production_status": "NO_GO",
            "confirmed_at_utc": now()
        }

        confirmation = add_digest(
            confirmation_without_digest,
            "confirmation_digest_sha256",
        )
        write_json(
            CONFIRMATION,
            confirmation,
        )

        source_hashes_after = {
            name: file_sha(path)
            for name, path in sources.items()
        }

        require(
            source_hashes_before
            == source_hashes_after,
            "SOURCE_ARTIFACTS_MODIFIED",
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-"
                "M27-EXECUTE-NOW-CONFIRMATION"
            ),
            "status": (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
                "EXECUTE_NOW_CONFIRMATION_RECORDED_LOCAL_ONLY_"
                "NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "EXECUTE_NOW_CONFIRMATION_RECORDED_AWAITING_"
                "SEPARATE_ONE_SHOT_UPDATE_EXECUTION_APPROVAL"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "confirmation_path": str(
                CONFIRMATION.relative_to(ROOT)
            ),
            "confirmation_digest_sha256": (
                confirmation[
                    "confirmation_digest_sha256"
                ]
            ),
            "execute_now_confirmation_recorded": True,
            "confirmation_consumed": False,
            "preflight_passed": True,
            "preflight_http_status_code": 200,
            "current_comment_status": "open",
            "target_comment_status": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status",
            ],
            "single_use": True,
            "maximum_update_count": 1,
            "authorization_issued": True,
            "authorization_consumed": False,
            "consumption_count": 0,
            "authorization_reused": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "backlist_carousel_included": False,
            "source_artifacts_modified": False,
            "dns_resolution_performed": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_get_performed": False,
            "wordpress_post_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_consumption_performed": False,
            "x_post_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "required_next_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE"
            ),
            "ready_for_separate_one_shot_update_execution_approval": True,
            "ready_for_wordpress_update_in_current_phase": False,
            "ready_for_wordpress_publish": False,
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE-NOW-CONFIRMATION

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Execute-now confirmation recorded: `true`
- Confirmation consumed: `false`
- Preflight HTTP status: `200`
- Current comment status: `open`
- Target comment status: `closed`
- Allowed update fields: `content, comment_status`
- Single use: `true`
- Maximum update count: `1`
- Authorization consumed: `false`
- Backlist carousel included: `false`
- Network performed: `false`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Production status: `NO_GO`
- Required next phase: `LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE`
- Ready for separate execution approval: `true`
- Ready for WordPress update in current phase: `false`
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
                        "M27-EXECUTE-NOW-CONFIRMATION"
                    ),
                    "status": (
                        "BLOCKED_EXECUTE_NOW_CONFIRMATION_"
                        "NO_NETWORK_NO_WORDPRESS"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_consumed": False,
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
