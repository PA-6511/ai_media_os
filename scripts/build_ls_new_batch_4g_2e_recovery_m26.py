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
        "NETWORK_OPERATION_BLOCKED_BY_M26"
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
    "update_one_shot_authorization_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m26_approval.json"
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
M25_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m25_result.json"
)
ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)

AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_one_shot_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m26_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m26_"
    "wordpress_update_one_shot_authorization_report.md"
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
EXPECTED_ROLLBACK_DIGEST = (
    "60ac4fe5182e412014bcbd291ca52af1"
    "e516e7061722e608b39a34c284dbfcf5"
)
EXPECTED_M25_RESULT_DIGEST = (
    "b536a2e37cb8b9647980382988389209"
    "8680bd85484758feb847babdf4ecd57e"
)
EXPECTED_FUTURE_REQUIREMENT_DIGEST = (
    "bfa2e1b69c1d5cfe3999ac0048539d1d"
    "4b01d60e9ba9d452a8e65176a5d028a4"
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
        canonical_digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"DIGEST_EXPECTED_MISMATCH:{field}",
        )

    return stored


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
        "m24_rendered": M24_RENDERED,
        "m24_payload": M24_PAYLOAD,
        "m25_review": M25_REVIEW,
        "m25_requirement": M25_REQUIREMENT,
        "m25_result": M25_RESULT,
        "rollback": ROLLBACK,
    }

    try:
        for output in [
            AUTHORIZATION,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M26_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M26",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_ONE_SHOT_AUTHORIZATION_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )
        require(
            approval["wordpress_update_approved"]
            is False,
            "WORDPRESS_UPDATE_APPROVED_IN_M26",
        )
        require(
            approval[
                "authorization_consumption_approved"
            ] is False,
            "AUTHORIZATION_CONSUMPTION_APPROVED",
        )
        require(
            approval[
                "backlist_carousel_in_current_update_approved"
            ] is False,
            "BACKLIST_INCLUDED_APPROVAL_TRUE",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
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
                == source_hashes[name],
                f"SOURCE_SHA_MISMATCH:{name}",
            )

        require(
            source_hashes["m24_rendered"]
            == EXPECTED_RENDERED_SHA,
            "M24_RENDERED_SHA_MISMATCH",
        )

        m24_payload = load_json(
            M24_PAYLOAD
        )
        m25_review = load_json(
            M25_REVIEW
        )
        future_requirement = load_json(
            M25_REQUIREMENT
        )
        m25_result = load_json(
            M25_RESULT
        )
        rollback = load_json(
            ROLLBACK
        )

        verify_digest(
            m24_payload,
            "update_payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            m25_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_REVIEW_DIGEST,
        )
        verify_digest(
            future_requirement,
            "future_requirement_digest_sha256",
            EXPECTED_FUTURE_REQUIREMENT_DIGEST,
        )
        verify_digest(
            m25_result,
            "result_digest_sha256",
            EXPECTED_M25_RESULT_DIGEST,
        )
        verify_digest(
            rollback,
            "rollback_evidence_digest_sha256",
            EXPECTED_ROLLBACK_DIGEST,
        )

        rendered_html = M24_RENDERED.read_text(
            encoding="utf-8"
        )

        request_body = m24_payload[
            "wordpress_request_body"
        ]

        require(
            set(request_body.keys())
            == {
                "content",
                "comment_status",
            },
            "UPDATE_FIELD_SET_MISMATCH",
        )
        require(
            request_body["content"]
            == rendered_html,
            "PAYLOAD_RENDERED_CONTENT_MISMATCH",
        )
        require(
            request_body[
                "comment_status"
            ] == "closed",
            "COMMENT_STATUS_NOT_CLOSED",
        )

        for blocked_field in [
            "title",
            "status",
            "categories",
            "slug",
            "excerpt",
            "featured_media",
        ]:
            require(
                blocked_field not in request_body,
                f"BLOCKED_UPDATE_FIELD_PRESENT:{blocked_field}",
            )

        require(
            m24_payload[
                "execution_allowed"
            ] is False,
            "M24_PAYLOAD_EXECUTION_ALLOWED",
        )
        require(
            m25_review[
                "human_review_completed"
            ] is True,
            "HUMAN_REVIEW_NOT_COMPLETED",
        )
        require(
            m25_review[
                "human_review_verdict"
            ] == "APPROVED_NO_CHANGE_REQUIRED",
            "HUMAN_REVIEW_NOT_APPROVED",
        )
        require(
            m25_review[
                "layout_change_required"
            ] is False,
            "LAYOUT_CHANGE_REQUIRED",
        )
        require(
            m25_result[
                "ready_for_wordpress_update_authorization_gate"
            ] is True,
            "M25_AUTHORIZATION_GATE_NOT_READY",
        )
        require(
            m25_result[
                "ready_for_wordpress_update"
            ] is False,
            "M25_UPDATE_GATE_ALREADY_OPEN",
        )

        require(
            future_requirement[
                "status"
            ] == "FUTURE_REQUIREMENT_RECORDED_NOT_IMPLEMENTED",
            "BACKLIST_REQUIREMENT_STATUS_MISMATCH",
        )
        require(
            future_requirement[
                "implementation_authorized"
            ] is False,
            "BACKLIST_IMPLEMENTATION_AUTHORIZED",
        )
        require(
            future_requirement[
                "included_in_current_wordpress_update"
            ] is False,
            "BACKLIST_INCLUDED_IN_CURRENT_UPDATE",
        )

        for forbidden_marker in [
            "SERIES_BACKLIST_COVER_AFFILIATE_CAROUSEL_V1",
            "LS-NEW-SERIES-BACKLIST-1",
        ]:
            require(
                forbidden_marker
                not in rendered_html,
                "BACKLIST_MARKER_PRESENT_IN_RENDERED_CONTENT",
            )

        request_body_digest = canonical_digest(
            request_body
        )

        authorization_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M26"
            ),
            "authorization_id": (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_ONE_SHOT_AUTHORIZATION_V1"
            ),
            "authorization_label": (
                "AUTHORIZED_FOR_WORDPRESS_POST_192_"
                "TAWAWA_LAYOUT_UPDATE_ONCE_ONLY"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "authorized_operation": (
                "UPDATE_WORDPRESS_POST_CONTENT_"
                "AND_COMMENT_STATUS_ONLY"
            ),
            "expected_current_wordpress_status": "publish",
            "authorized_request_method": "POST",
            "authorized_rest_path": (
                "/wp-json/wp/v2/posts/192"
            ),
            "allowed_request_fields": [
                "content",
                "comment_status",
            ],
            "target_comment_status": "closed",
            "request_body_digest_sha256": (
                request_body_digest
            ),
            "bound_rendered_content_path": str(
                M24_RENDERED.relative_to(ROOT)
            ),
            "bound_rendered_content_sha256": (
                EXPECTED_RENDERED_SHA
            ),
            "bound_update_payload_path": str(
                M24_PAYLOAD.relative_to(ROOT)
            ),
            "bound_update_payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "bound_human_review_path": str(
                M25_REVIEW.relative_to(ROOT)
            ),
            "bound_human_review_evidence_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "bound_rollback_path": str(
                ROLLBACK.relative_to(ROOT)
            ),
            "bound_rollback_evidence_digest_sha256": (
                EXPECTED_ROLLBACK_DIGEST
            ),
            "bound_m25_result_digest_sha256": (
                EXPECTED_M25_RESULT_DIGEST
            ),
            "bound_backlist_future_requirement_digest_sha256": (
                EXPECTED_FUTURE_REQUIREMENT_DIGEST
            ),
            "backlist_carousel_included": False,
            "backlist_carousel_implementation_authorized": False,
            "single_use": True,
            "maximum_update_count": 1,
            "authorization_consumed": False,
            "consumption_count": 0,
            "reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "explicit_execute_now_confirmation_required": True,
            "authenticated_preflight_required": True,
            "required_preflight_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27-PRE-NETWORK"
            ),
            "authorized_execution_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27"
            ),
            "current_phase_execution_allowed": False,
            "current_phase_network_connection_performed": False,
            "current_phase_wordpress_access_performed": False,
            "current_phase_wordpress_update_performed": False,
            "authorization_issued_at_utc": now(),
            "production_status": "NO_GO"
        }

        authorization = add_digest(
            authorization_without_digest,
            "authorization_digest_sha256",
        )

        write_json(
            AUTHORIZATION,
            authorization,
        )

        require(
            stat.S_IMODE(
                AUTHORIZATION.stat().st_mode
            ) == 0o600,
            "AUTHORIZATION_MODE_NOT_0600",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M26"
            ),
            "status": (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "UPDATE_ONE_SHOT_AUTHORIZATION_ISSUED_"
                "LOCAL_ONLY_NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "ONE_SHOT_UPDATE_AUTHORIZATION_RECORDED_"
                "AWAITING_SEPARATE_AUTHENTICATED_PREFLIGHT_"
                "AND_EXPLICIT_EXECUTE_NOW_CONFIRMATION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "authorization_path": str(
                AUTHORIZATION.relative_to(ROOT)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "authorization_id": (
                authorization["authorization_id"]
            ),
            "authorization_issued": True,
            "authorization_consumed": False,
            "consumption_count": 0,
            "single_use": True,
            "maximum_update_count": 1,
            "reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "allowed_update_fields": [
                "content",
                "comment_status",
            ],
            "comment_status_target": "closed",
            "bound_rendered_content_sha256": (
                EXPECTED_RENDERED_SHA
            ),
            "bound_update_payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "bound_human_review_evidence_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "bound_rollback_evidence_digest_sha256": (
                EXPECTED_ROLLBACK_DIGEST
            ),
            "request_body_digest_sha256": (
                request_body_digest
            ),
            "backlist_carousel_future_requirement_preserved": True,
            "backlist_carousel_included_in_update": False,
            "backlist_carousel_implemented": False,
            "source_artifacts_modified": False,
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_consumption_performed": False,
            "authorization_reuse_performed": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "x_post_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ONE_SHOT_AUTHORIZATION_ISSUED_"
                "UNCONSUMED_AWAITING_PREFLIGHT_NO_WORDPRESS_UPDATE"
            ),
            "required_preflight_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27-PRE-NETWORK"
            ),
            "authorized_execution_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27"
            ),
            "ready_for_authenticated_preflight": True,
            "ready_for_execute_now_confirmation": False,
            "ready_for_wordpress_update": False,
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M26

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Authorization issued: `true`
- Authorization consumed: `false`
- Single use: `true`
- Maximum update count: `1`
- Reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- Allowed fields: `content, comment_status`
- Comment status target: `closed`
- Backlist carousel included: `false`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Execution allowed in M26: `false`
- Production status: `NO_GO`
- Required preflight phase: `LS-NEW-BATCH-4G-2E-RECOVERY-M27-PRE-NETWORK`
- Authorized execution phase: `LS-NEW-BATCH-4G-2E-RECOVERY-M27`
- Ready for authenticated preflight: `true`
- Ready for execute-now confirmation: `false`
- Ready for WordPress update: `false`
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M26"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_"
                        "LAYOUT_UPDATE_AUTHORIZATION_NO_WORDPRESS_ACCESS"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_consumed": False,
                    "execution_allowed": False,
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
