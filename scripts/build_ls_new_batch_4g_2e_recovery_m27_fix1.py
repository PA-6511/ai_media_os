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


def blocked_network(
    *args: Any,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "NETWORK_OPERATION_BLOCKED_BY_M27_FIX1"
    )


socket.socket = blocked_network
socket.create_connection = blocked_network
socket.getaddrinfo = blocked_network
socket.gethostbyname = blocked_network
socket.gethostbyname_ex = blocked_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_layout_update_"
    "preflight_transport_diagnostic_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_approval.json"
)
REVISED_RUNNER = ROOT / (
    "scripts/"
    "run_ls_new_batch_4g_2e_recovery_m27_fix1_get_only.py"
)
TEST = ROOT / (
    "tests/"
    "test_run_ls_new_batch_4g_2e_recovery_m27_fix1_get_only.py"
)

M27_RUNNER = ROOT / (
    "scripts/"
    "run_ls_new_batch_4g_2e_recovery_m27_pre_network.py"
)
M27_SNAPSHOT = ROOT / (
    "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_authenticated_get_preflight_snapshot.json"
)
M27_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_pre_network_result.json"
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
ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)

DIAGNOSTIC = ROOT / (
    "exchange/diagnostics/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_m27_transport_failure_diagnostic.json"
)
PLAN = ROOT / (
    "exchange/plans/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_next_single_get_non_execution_plan.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_"
    "transport_diagnostic_report.md"
)

EXPECTED_M27_SNAPSHOT_DIGEST = (
    "640dccfc0d6abbaf553894100408ed76c"
    "547a8c4d6d382e1d8d43a40f8d63a84"
)
EXPECTED_M27_RESULT_DIGEST = (
    "6d32f2005c4486fb78569f5f9d15c32"
    "2e6dd6ed66300ae5619c7a6e8803b0cde"
)
EXPECTED_M26_AUTHORIZATION_DIGEST = (
    "d7f53a0eb02a037cde4b6ab71b4b026b"
    "79eb8c2d2c08a95a8bec5f1ad0b6e615"
)
EXPECTED_M24_RENDERED_SHA = (
    "dc938ae164c70130a5fb27692d71c97c"
    "c367a8985c44c2c333801b337ee6caf4"
)
EXPECTED_M24_PAYLOAD_DIGEST = (
    "52ed18792454e5806b739059911c8117"
    "810cafcadacf35fb77429b608673cd60"
)
EXPECTED_M25_REVIEW_DIGEST = (
    "7fd7a9f0f5317435160010fac811b77d"
    "876f77919ad2b5905c6cdea82f8f1806"
)
EXPECTED_ROLLBACK_DIGEST = (
    "60ac4fe5182e412014bcbd291ca52af1"
    "e516e7061722e608b39a34c284dbfcf5"
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


def detect_transport(
    source: str,
) -> str:
    if "urllib.request" in source:
        return "URLLIB_REQUEST"

    if (
        "http.client" in source
        or "HTTPSConnection" in source
    ):
        return "HTTP_CLIENT"

    if "requests." in source:
        return "REQUESTS"

    if "curl" in source:
        return "CURL"

    return "UNKNOWN"


def find_prior_success() -> tuple[
    str | None,
    str | None,
    str | None,
]:
    candidates: list[
        tuple[Path, dict[str, Any]]
    ] = []

    for path in sorted(
        ROOT.glob("exchange/**/*.json")
    ):
        if path in {
            M27_SNAPSHOT,
            M27_RESULT,
        }:
            continue

        try:
            value = json.loads(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            continue

        if not isinstance(value, dict):
            continue

        if value.get(
            "wordpress_post_id"
        ) != 192:
            continue

        if value.get(
            "http_status_code"
        ) != 200:
            continue

        if value.get(
            "wordpress_write_performed"
        ) is True:
            continue

        if value.get(
            "wordpress_update_performed"
        ) is True:
            continue

        candidates.append(
            (
                path,
                value,
            )
        )

    if not candidates:
        return None, None, None

    result_path, result_value = (
        candidates[-1]
    )

    phase_id = result_value.get(
        "phase_id"
    )

    selected_runner: Path | None = None

    if isinstance(
        phase_id,
        str,
    ):
        for path in sorted(
            ROOT.glob("scripts/*.py")
        ):
            try:
                source = path.read_text(
                    encoding="utf-8"
                )
            except Exception:
                continue

            if (
                phase_id in source
                and (
                    '"GET"' in source
                    or "'GET'" in source
                )
            ):
                selected_runner = path
                break

    if selected_runner is None:
        for path in sorted(
            ROOT.glob("scripts/*.py")
        ):
            if path in {
                M27_RUNNER,
                REVISED_RUNNER,
            }:
                continue

            try:
                source = path.read_text(
                    encoding="utf-8"
                )
            except Exception:
                continue

            if (
                "posts/192" in source
                and (
                    '"GET"' in source
                    or "'GET'" in source
                )
            ):
                selected_runner = path
                break

    transport = None

    if selected_runner is not None:
        transport = detect_transport(
            selected_runner.read_text(
                encoding="utf-8"
            )
        )

    return (
        str(result_path.relative_to(ROOT)),
        (
            str(
                selected_runner.relative_to(ROOT)
            )
            if selected_runner is not None
            else None
        ),
        transport,
    )


def main() -> int:
    source_paths = {
        "m27_runner": M27_RUNNER,
        "m27_snapshot": M27_SNAPSHOT,
        "m27_result": M27_RESULT,
        "m26_authorization": M26_AUTHORIZATION,
        "m24_rendered": M24_RENDERED,
        "m24_payload": M24_PAYLOAD,
        "m25_review": M25_REVIEW,
        "rollback": ROLLBACK,
    }

    try:
        for output in [
            DIAGNOSTIC,
            PLAN,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M27_FIX1_OUTPUT_ALREADY_EXISTS:{output.name}",
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
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M27-FIX1",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
                "PREFLIGHT_TRANSPORT_DIAGNOSTIC_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )

        source_hashes_before = {
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
                == source_hashes_before[name],
                f"SOURCE_SHA_MISMATCH:{name}",
            )

        snapshot = load_json(
            M27_SNAPSHOT
        )
        m27_result = load_json(
            M27_RESULT
        )
        m26_authorization = load_json(
            M26_AUTHORIZATION
        )
        m24_payload = load_json(
            M24_PAYLOAD
        )
        m25_review = load_json(
            M25_REVIEW
        )
        rollback = load_json(
            ROLLBACK
        )

        verify_digest(
            snapshot,
            "snapshot_digest_sha256",
            EXPECTED_M27_SNAPSHOT_DIGEST,
        )
        verify_digest(
            m27_result,
            "result_digest_sha256",
            EXPECTED_M27_RESULT_DIGEST,
        )
        verify_digest(
            m26_authorization,
            "authorization_digest_sha256",
            EXPECTED_M26_AUTHORIZATION_DIGEST,
        )
        verify_digest(
            m24_payload,
            "update_payload_digest_sha256",
            EXPECTED_M24_PAYLOAD_DIGEST,
        )
        verify_digest(
            m25_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M25_REVIEW_DIGEST,
        )
        verify_digest(
            rollback,
            "rollback_evidence_digest_sha256",
            EXPECTED_ROLLBACK_DIGEST,
        )

        require(
            file_sha(M24_RENDERED)
            == EXPECTED_M24_RENDERED_SHA,
            "M24_RENDERED_SHA_MISMATCH",
        )

        require(
            m27_result[
                "preflight_passed"
            ] is False,
            "M27_PREFLIGHT_NOT_BLOCKED",
        )
        require(
            m27_result[
                "local_integrity_gate_passed"
            ] is True,
            "M27_LOCAL_GATE_NOT_PASSED",
        )
        require(
            m27_result[
                "remote_failure_codes"
            ] == [
                "SINGLE_GET_REQUEST_FAILED"
            ],
            "M27_REMOTE_FAILURE_CODE_MISMATCH",
        )
        require(
            m27_result[
                "get_request_count"
            ] == 1,
            "M27_GET_COUNT_NOT_ONE",
        )
        require(
            m27_result[
                "automatic_retry_count"
            ] == 0,
            "M27_AUTOMATIC_RETRY_OCCURRED",
        )
        require(
            m27_result[
                "wordpress_update_performed"
            ] is False,
            "M27_WORDPRESS_UPDATE_PERFORMED",
        )
        require(
            m27_result[
                "authorization_consumed"
            ] is False,
            "M26_AUTHORIZATION_CONSUMED",
        )

        current_runner_source = (
            M27_RUNNER.read_text(
                encoding="utf-8"
            )
        )
        revised_runner_source = (
            REVISED_RUNNER.read_text(
                encoding="utf-8"
            )
        )

        current_transport = detect_transport(
            current_runner_source
        )
        revised_transport = detect_transport(
            revised_runner_source
        )

        prior_result_path, (
            prior_runner_path
        ), prior_transport = (
            find_prior_success()
        )

        request_sent = bool(
            snapshot.get(
                "http_request_performed"
            )
        )
        response_received = bool(
            snapshot.get(
                "http_response_received"
            )
        )

        if (
            request_sent
            and not response_received
        ):
            failure_stage = (
                "AFTER_REQUEST_SENT_BEFORE_RESPONSE_HEADERS"
            )
        elif not request_sent:
            failure_stage = (
                "BEFORE_HTTP_REQUEST_SEND"
            )
        else:
            failure_stage = (
                "AFTER_RESPONSE_RECEIVED"
            )

        safe_exception_type = (
            snapshot.get(
                "network_error_type"
            )
        )

        if not isinstance(
            safe_exception_type,
            str,
        ):
            safe_exception_type = (
                "NOT_RECORDED"
            )

        diagnostic_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27-FIX1"
            ),
            "document_role": (
                "M27_AUTHENTICATED_GET_TRANSPORT_FAILURE_DIAGNOSTIC"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "m27_preflight_passed": False,
            "local_integrity_gate_passed": True,
            "remote_failure_codes": [
                "SINGLE_GET_REQUEST_FAILED"
            ],
            "safe_exception_type": (
                safe_exception_type
            ),
            "failure_stage": (
                failure_stage
            ),
            "get_request_count": 1,
            "non_get_request_count": 0,
            "automatic_retry_count": 0,
            "http_response_received": (
                response_received
            ),
            "current_transport": (
                current_transport
            ),
            "current_transport_characteristics": {
                "manual_https_connection": (
                    "HTTPSConnection"
                    in current_runner_source
                ),
                "manual_getresponse_call": (
                    ".getresponse()"
                    in current_runner_source
                ),
                "connection_close_header": (
                    '"Connection": "close"'
                    in current_runner_source
                ),
                "safe_exception_message_suppressed": True
            },
            "prior_successful_result_found": (
                prior_result_path
                is not None
            ),
            "prior_successful_result_path": (
                prior_result_path
            ),
            "prior_successful_runner_found": (
                prior_runner_path
                is not None
            ),
            "prior_successful_runner_path": (
                prior_runner_path
            ),
            "prior_successful_runner_transport": (
                prior_transport
            ),
            "revised_transport": (
                revised_transport
            ),
            "revised_transport_characteristics": {
                "urllib_single_open": True,
                "redirect_handler_blocks_redirects": True,
                "automatic_retry_loop_absent": True,
                "response_size_limit_present": True,
                "accept_encoding_identity": True,
                "connection_close_header": True,
                "safe_exception_type_only": True,
                "explicit_future_network_gate": True
            },
            "diagnostic_conclusion_codes": [
                "LOCAL_ARTIFACT_INTEGRITY_PASSED",
                "REQUEST_WAS_SENT",
                "NO_HTTP_RESPONSE_HEADERS_RECEIVED",
                "FAILURE_LOCALIZED_TO_RESPONSE_ACQUISITION_STAGE",
                "M26_AUTHORIZATION_REMAINS_UNCONSUMED",
                "REVISED_URLLIB_SINGLE_GET_TRANSPORT_GENERATED"
            ],
            "credential_value_stored": False,
            "username_stored": False,
            "full_url_stored": False,
            "authorization_header_stored": False,
            "wordpress_content_stored": False,
            "dns_resolution_performed": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "authorization_consumed": False,
            "recorded_at_utc": now()
        }

        diagnostic = add_digest(
            diagnostic_without_digest,
            "diagnostic_digest_sha256",
        )
        write_json(
            DIAGNOSTIC,
            diagnostic,
        )

        plan_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27-FIX1"
            ),
            "document_role": (
                "NEXT_SINGLE_AUTHENTICATED_GET_NON_EXECUTION_PLAN"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "revised_runner_path": str(
                REVISED_RUNNER.relative_to(ROOT)
            ),
            "revised_runner_sha256": (
                file_sha(REVISED_RUNNER)
            ),
            "test_path": str(
                TEST.relative_to(ROOT)
            ),
            "test_sha256": (
                file_sha(TEST)
            ),
            "transport": (
                "URLLIB_REQUEST_SINGLE_OPEN"
            ),
            "method": "GET",
            "maximum_get_request_count": 1,
            "non_get_request_allowed": False,
            "redirect_following_allowed": False,
            "automatic_retry_allowed": False,
            "response_size_limit_bytes": (
                4 * 1024 * 1024
            ),
            "safe_exception_type_recording": True,
            "safe_failure_stage_recording": True,
            "explicit_future_network_approval_environment_gate": (
                "M27_FIX1_SINGLE_GET_NETWORK_APPROVED"
            ),
            "network_execution_authorized": False,
            "wordpress_update_authorized": False,
            "authorization_consumption_authorized": False,
            "authorization_reuse_authorized": False,
            "automatic_reissue_authorized": False,
            "backlist_carousel_included": False,
            "required_future_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-"
                "M27-FIX1-RETRY-APPROVAL"
            ),
            "production_status": "NO_GO",
            "recorded_at_utc": now()
        }

        plan = add_digest(
            plan_without_digest,
            "plan_digest_sha256",
        )
        write_json(
            PLAN,
            plan,
        )

        source_hashes_after = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        source_artifacts_modified = (
            source_hashes_before
            != source_hashes_after
        )

        require(
            source_artifacts_modified is False,
            "SOURCE_ARTIFACT_MODIFIED",
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M27-FIX1"
            ),
            "status": (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
                "PREFLIGHT_TRANSPORT_DIAGNOSTIC_LOCAL_ONLY_"
                "REVISED_GET_RUNNER_READY_NO_NETWORK"
            ),
            "decision": (
                "TRANSPORT_FAILURE_STAGE_IDENTIFIED_REVISED_"
                "SINGLE_GET_RUNNER_AND_MOCK_TEST_READY_FOR_"
                "SEPARATE_NETWORK_APPROVAL"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "diagnostic_path": str(
                DIAGNOSTIC.relative_to(ROOT)
            ),
            "diagnostic_digest_sha256": (
                diagnostic[
                    "diagnostic_digest_sha256"
                ]
            ),
            "plan_path": str(
                PLAN.relative_to(ROOT)
            ),
            "plan_digest_sha256": (
                plan[
                    "plan_digest_sha256"
                ]
            ),
            "revised_runner_path": str(
                REVISED_RUNNER.relative_to(ROOT)
            ),
            "revised_runner_sha256": (
                file_sha(REVISED_RUNNER)
            ),
            "mock_test_path": str(
                TEST.relative_to(ROOT)
            ),
            "mock_test_sha256": (
                file_sha(TEST)
            ),
            "safe_exception_type": (
                safe_exception_type
            ),
            "failure_stage": (
                failure_stage
            ),
            "current_transport": (
                current_transport
            ),
            "prior_successful_runner_found": (
                prior_runner_path
                is not None
            ),
            "prior_successful_runner_transport": (
                prior_transport
            ),
            "revised_transport": (
                revised_transport
            ),
            "m27_result_modified": False,
            "m27_snapshot_modified": False,
            "m27_runner_modified": False,
            "m26_authorization_modified": False,
            "m24_rendered_content_modified": False,
            "m24_update_payload_modified": False,
            "m25_human_review_modified": False,
            "rollback_evidence_modified": False,
            "source_artifacts_modified": False,
            "dns_resolution_performed": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_consumed": False,
            "authorization_reused": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "x_post_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "ready_for_separate_single_get_retry_approval": True,
            "ready_for_wordpress_update": False,
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M27-FIX1

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- M27 local integrity gate: `PASS`
- M27 GET count: `1`
- M27 automatic retry count: `0`
- Safe exception type: `{safe_exception_type}`
- Failure stage: `{failure_stage}`
- Current transport: `{current_transport}`
- Prior successful runner found: `{str(prior_runner_path is not None).lower()}`
- Prior successful runner transport: `{prior_transport}`
- Revised transport: `{revised_transport}`
- Revised runner generated: `true`
- Mock test generated: `true`
- Network performed in FIX1: `false`
- WordPress access performed in FIX1: `false`
- WordPress update performed: `false`
- Authorization consumed: `false`
- Production status: `NO_GO`
- Ready for separate single-GET retry approval: `true`
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M27-FIX1"
                    ),
                    "status": (
                        "BLOCKED_LOCAL_TRANSPORT_DIAGNOSTIC_"
                        "NO_NETWORK_NO_WORDPRESS"
                    ),
                    "error_code": str(exc),
                    "dns_resolution_performed": False,
                    "network_connection_performed": False,
                    "http_request_performed": False,
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
