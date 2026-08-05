#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_category_index_recovery_authorization_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_index_recovery_authorization_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_index_recovery_authorization_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_a_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_a_authorization_report.md"
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(
            f"required file missing: {path}"
        )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise ValidationError(
            f"JSON root must be an object: {path}"
        )

    return value


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        value,
        encoding="utf-8",
    )
    temporary.replace(path)


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(
            resolved.relative_to(ROOT.resolve())
        )
    except ValueError:
        return str(resolved)


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-A",
        "policy phase mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == (
            "NEW_RELEASE_WP_CATEGORY_INDEX_RECOVERY_"
            "AUTHORIZATION_POLICY_V1"
        ),
        "policy identity mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == (
            "ONE_SHOT_CATEGORY_INDEX_RECOVERY_"
            "AUTHORIZATION_GATE"
        ),
        "operation mode mismatch",
    )
    checks.append("authorization_gate_mode")

    source = policy["source_failure_contract"]

    require(
        source["previous_approval_consumed_required"]
        is True,
        "previous approval consumption must be required",
    )
    require(
        source["previous_approval_reuse_allowed"]
        is False,
        "previous approval reuse must be forbidden",
    )
    require(
        source["previous_lock_deletion_allowed"]
        is False,
        "previous lock deletion must be forbidden",
    )
    require(
        source["previous_lock_reuse_allowed"]
        is False,
        "previous lock reuse must be forbidden",
    )
    checks.append("previous_attempt_preserved")

    approval = policy["requested_approval"]

    require(
        approval["approval_label_issued"] is False,
        "approval label must not be issued",
    )
    require(
        approval["approval_label_consumed"] is False,
        "approval label must not be consumed",
    )
    require(
        approval["actual_go_decision_issued"] is False,
        "actual GO must not be issued",
    )
    require(
        approval["human_explicit_approval_required"]
        is True,
        "human approval must be required",
    )
    checks.append("approval_gate_closed")

    scope = policy["planned_http_scope"]

    require(
        scope["maximum_http_requests"] == 1,
        "maximum HTTP requests must be one",
    )
    require(
        scope["maximum_attempts"] == 1,
        "maximum attempts must be one",
    )
    require(
        scope["retry_allowed"] is False,
        "retry must remain disabled",
    )
    require(
        scope["method"] == "GET",
        "only GET may be planned",
    )
    require(
        scope["rest_path"]
        == "/wp-json/wp/v2/categories",
        "REST path mismatch",
    )

    expected_query = {
        "per_page": 100,
        "orderby": "name",
        "order": "asc",
        "hide_empty": "false",
        "_fields": "id,slug,name,count",
    }

    require(
        scope["query_parameters"]
        == expected_query,
        "category-index query mismatch",
    )
    require(
        scope["request_body_allowed"] is False,
        "request body must remain forbidden",
    )
    require(
        scope["redirect_follow_allowed"] is False,
        "redirects must remain disabled",
    )
    require(
        scope["proxy_use_allowed"] is False,
        "proxy use must remain disabled",
    )
    require(
        scope["tls_verification_required"] is True,
        "TLS verification must be required",
    )
    checks.append("category_index_scope")

    boundary = policy["category_index_boundary"]

    for field in [
        "automatic_category_selection_allowed",
        "automatic_category_mapping_allowed",
        "category_mapping_fixation_allowed",
        "production_category_id_payload_injection_allowed",
        "production_category_id_automatic_use_allowed",
        "wordpress_category_creation_allowed",
        "wordpress_draft_preparation_allowed",
        "wordpress_draft_creation_allowed",
    ]:
        require(
            boundary[field] is False,
            f"{field} must remain false",
        )

    require(
        boundary["human_category_review_required"]
        is True,
        "human category review must be required",
    )
    checks.append("category_index_boundary")

    for field, value in policy[
        "current_phase_access"
    ].items():
        require(
            value is False,
            f"{field} must remain false",
        )

    checks.append("current_phase_no_access")

    execution = policy["execution_boundary"]

    for field in [
        "credential_value_output_allowed",
        "environment_variable_export_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "tls_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_index_read_allowed",
        "wordpress_category_creation_allowed",
        "wordpress_post_read_allowed",
        "wordpress_media_read_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "external_api_call_allowed",
        "execution_approval_issued",
        "execution_allowed",
    ]:
        require(
            execution[field] is False,
            f"{field} must remain false",
        )

    require(
        execution["production_status"] == "NO_GO",
        "production status must remain NO_GO",
    )
    checks.append("execution_boundary")

    return checks


def validate_source(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    result_path = resolve_repo_path(
        request["source_result_path"]
    )
    lock_path = resolve_repo_path(
        request["source_lock_path"]
    )

    source_result = load_json(result_path)
    source_lock = load_json(lock_path)

    require(
        digest(source_result)
        == request["source_result_digest_sha256"],
        "source result digest mismatch",
    )
    require(
        digest(source_lock)
        == request["source_lock_digest_sha256"],
        "source lock digest mismatch",
    )

    contract = policy["source_failure_contract"]

    require(
        source_result.get("phase_id")
        == policy["source_phase_id"],
        "source phase mismatch",
    )
    require(
        source_result.get("status")
        == contract["required_source_status"],
        "source status mismatch",
    )
    require(
        source_result.get("decision")
        == contract["required_source_decision"],
        "source decision mismatch",
    )
    require(
        source_result.get("http_status")
        == contract["required_http_status"],
        "source HTTP status mismatch",
    )
    require(
        source_result.get("candidate_count")
        == contract["required_candidate_count"],
        "source candidate count mismatch",
    )
    require(
        source_result.get("approval_label_consumed")
        is True,
        "source approval must be consumed",
    )
    require(
        source_result.get("approval_reuse_allowed")
        is False,
        "source approval reuse must be false",
    )
    require(
        source_result.get("candidate_selected")
        is False,
        "source candidate must remain unselected",
    )
    require(
        source_result.get("category_mapping_fixed")
        is False,
        "source mapping must remain unfixed",
    )
    require(
        source_result.get("wordpress_write_performed")
        is False,
        "source WordPress write must be false",
    )
    require(
        source_result.get("production_payload_modified")
        is False,
        "source payload modification must be false",
    )

    require(
        source_lock.get("state")
        == contract["previous_one_shot_lock_state"],
        "source lock state mismatch",
    )
    require(
        source_lock.get("approval_label_consumed")
        is True,
        "source lock approval state mismatch",
    )
    require(
        source_lock.get("http_request_attempt_count")
        == 1,
        "source lock request count mismatch",
    )
    require(
        source_lock.get("result_status")
        == contract["required_source_status"],
        "source lock result status mismatch",
    )

    return [
        "source_result_digest_verified",
        "source_lock_digest_verified",
        "source_empty_candidate_state_verified",
        "source_http_200_verified",
        "previous_approval_consumed",
        "previous_approval_reuse_forbidden",
        "previous_lock_consumed_blocked",
        "previous_lock_preserved",
        "source_candidate_unselected",
        "source_mapping_unfixed",
        "source_wordpress_write_absent",
        "source_payload_modification_absent",
    ]


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-A",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    scope = request.get(
        "requested_approval_scope"
    )

    require(
        isinstance(scope, dict),
        "requested approval scope must be object",
    )
    require(
        scope["requested_approval_label"]
        == policy["requested_approval"][
            "requested_approval_label"
        ],
        "approval label mismatch",
    )
    require(
        scope["maximum_http_requests"] == 1,
        "request-count mismatch",
    )
    require(
        scope["maximum_attempts"] == 1,
        "attempt-count mismatch",
    )
    require(
        scope["retry_allowed"] is False,
        "retry must remain false",
    )
    require(
        scope["method"] == "GET",
        "method must be GET",
    )
    require(
        scope["rest_path"]
        == "/wp-json/wp/v2/categories",
        "REST path mismatch",
    )
    require(
        scope["query_parameters"]
        == policy["planned_http_scope"][
            "query_parameters"
        ],
        "query parameters mismatch",
    )
    require(
        scope["request_body"] is None,
        "request body must remain null",
    )
    require(
        scope["redirect_follow"] is False,
        "redirect following must remain false",
    )
    require(
        scope["proxy_use"] is False,
        "proxy use must remain false",
    )
    require(
        scope["tls_verification"] is True,
        "TLS verification must remain true",
    )

    for field in [
        "previous_one_shot_lock_delete_requested",
        "previous_one_shot_lock_reuse_requested",
        "previous_approval_reuse_requested",
        "credential_file_read_requested",
        "credential_values_output_requested",
        "authorization_header_construction_requested",
        "dns_resolution_requested",
        "network_connection_requested",
        "tls_connection_requested",
        "http_request_requested",
        "wordpress_response_read_requested",
        "wordpress_write_requested",
        "automatic_category_selection_requested",
        "automatic_category_mapping_requested",
        "production_category_id_payload_injection_requested",
        "approval_label_issued",
        "approval_label_consumed",
        "actual_go_decision_issued",
        "execution_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    require(
        request.get("approval_token") is None,
        "approval token must remain null",
    )


def build_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = validate_source(
        request,
        policy,
    )
    validate_request(
        request,
        policy,
    )

    scope_without_digest = {
        "approval_scope_id": policy[
            "requested_approval"
        ]["approval_scope_id"],
        "requested_approval_label": policy[
            "requested_approval"
        ]["requested_approval_label"],
        "maximum_http_requests": 1,
        "maximum_attempts": 1,
        "retry_allowed": False,
        "method": "GET",
        "rest_path": "/wp-json/wp/v2/categories",
        "query_parameters": copy.deepcopy(
            policy["planned_http_scope"][
                "query_parameters"
            ]
        ),
        "request_body": None,
        "redirect_follow": False,
        "proxy_use": False,
        "tls_verification": True,
        "https_required": True,
        "automatic_category_selection_allowed": False,
        "automatic_category_mapping_allowed": False,
        "payload_injection_allowed": False,
        "wordpress_write_allowed": False,
        "approval_label_issued": False,
        "actual_go_decision_issued": False,
        "execution_allowed": False,
    }

    scope = copy.deepcopy(
        scope_without_digest
    )
    scope[
        "category_index_scope_digest_sha256"
    ] = digest(scope_without_digest)

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4G-2E-RECOVERY-A",
        "policy_id": policy["policy_id"],
        "authorization_package_id": (
            "wp-one-shot-category-index-"
            "recovery-authorization"
        ),
        "operation_mode": policy[
            "operation_mode"
        ],
        "previous_attempt_state": {
            "status": (
                "BLOCKED_WORDPRESS_CATEGORY_"
                "CANDIDATE_LIST_EMPTY"
            ),
            "approval_consumed": True,
            "approval_reusable": False,
            "one_shot_lock_state": (
                "CONSUMED_COMPLETED_BLOCKED"
            ),
            "lock_deletion_allowed": False,
            "lock_reuse_allowed": False,
        },
        "category_index_scope": scope,
        "approval_gate": {
            "state": "AWAITING_EXPLICIT_APPROVAL",
            "requested_approval_label": policy[
                "requested_approval"
            ]["requested_approval_label"],
            "approval_label_issued": False,
            "approval_label_consumed": False,
            "actual_go_decision_issued": False,
            "approval_token": None,
            "human_explicit_approval_required": True,
            "execution_allowed": False,
        },
        "current_phase_activity": {
            "credential_file_read": False,
            "credential_values_loaded": False,
            "credential_values_output": False,
            "authorization_header_constructed": False,
            "dns_resolution_performed": False,
            "network_connection_performed": False,
            "tls_connection_performed": False,
            "http_request_performed": False,
            "wordpress_response_read": False,
            "wordpress_write_performed": False,
            "category_list_received": False,
            "category_selected": False,
            "category_mapping_fixed": False,
            "production_payload_modified": False,
        },
        "verified_checks": source_checks,
    }

    package = copy.deepcopy(
        package_without_digest
    )
    package[
        "authorization_package_digest_sha256"
    ] = digest(package_without_digest)

    return package


def build_result(
    package: dict[str, Any],
    request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    activity = package[
        "current_phase_activity"
    ]
    gate = package["approval_gate"]
    scope = package[
        "category_index_scope"
    ]

    return {
        "phase_id": "LS-NEW-BATCH-4G-2E-RECOVERY-A",
        "status": (
            "PASS_CATEGORY_INDEX_RECOVERY_"
            "AUTHORIZATION_GATE_READY_NO_NETWORK"
        ),
        "decision": (
            "AWAITING_EXPLICIT_APPROVAL_FOR_"
            "ONE_SHOT_CATEGORY_INDEX_GET"
        ),
        "policy_id": package["policy_id"],
        "authorization_package_id": package[
            "authorization_package_id"
        ],
        "request_path": display_path(
            request_path
        ),
        "output_path": display_path(
            output_path
        ),
        "operation_mode": package[
            "operation_mode"
        ],
        "previous_approval_consumed": True,
        "previous_approval_reusable": False,
        "previous_lock_state": (
            "CONSUMED_COMPLETED_BLOCKED"
        ),
        "previous_lock_deletion_allowed": False,
        "previous_lock_reuse_allowed": False,
        "approval_gate_state": gate["state"],
        "requested_approval_label": gate[
            "requested_approval_label"
        ],
        "approval_label_issued": False,
        "approval_label_consumed": False,
        "actual_go_decision_issued": False,
        "approval_token_present": False,
        "human_explicit_approval_required": True,
        "http_method": scope["method"],
        "rest_path": scope["rest_path"],
        "query_parameters": scope[
            "query_parameters"
        ],
        "maximum_http_requests": 1,
        "maximum_attempts": 1,
        "retry_allowed": False,
        "credential_file_read": activity[
            "credential_file_read"
        ],
        "credential_values_loaded": activity[
            "credential_values_loaded"
        ],
        "credential_values_output": activity[
            "credential_values_output"
        ],
        "authorization_header_constructed": activity[
            "authorization_header_constructed"
        ],
        "dns_resolution_performed": activity[
            "dns_resolution_performed"
        ],
        "network_connection_performed": activity[
            "network_connection_performed"
        ],
        "tls_connection_performed": activity[
            "tls_connection_performed"
        ],
        "http_request_performed": activity[
            "http_request_performed"
        ],
        "wordpress_response_read": activity[
            "wordpress_response_read"
        ],
        "wordpress_write_performed": activity[
            "wordpress_write_performed"
        ],
        "category_list_received": activity[
            "category_list_received"
        ],
        "category_selected": activity[
            "category_selected"
        ],
        "category_mapping_fixed": activity[
            "category_mapping_fixed"
        ],
        "production_payload_modified": activity[
            "production_payload_modified"
        ],
        "category_index_scope_digest_sha256": scope[
            "category_index_scope_digest_sha256"
        ],
        "authorization_package_digest_sha256": package[
            "authorization_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity",
                "new_approval_scope_identity",
                "new_approval_label_not_issued",
                "new_actual_go_not_issued",
                "new_approval_token_absent",
                "one_shot_request_count_fixed",
                "single_attempt_fixed",
                "retry_disabled",
                "get_method_locked",
                "category_index_endpoint_locked",
                "category_index_query_locked",
                "request_body_absent",
                "redirect_follow_disabled",
                "proxy_use_disabled",
                "tls_verification_required",
                "automatic_category_selection_blocked",
                "automatic_category_mapping_blocked",
                "payload_injection_blocked",
                "credential_file_unread",
                "network_unaccessed",
                "wordpress_unaccessed",
                "wordpress_write_forbidden",
                "category_index_scope_digest_generated",
                "authorization_package_digest_generated",
                "execution_gate_closed",
            ]
        ),
        "credential_file_read_allowed": False,
        "credential_value_output_allowed": False,
        "network_connection_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_index_read_allowed": False,
        "wordpress_category_creation_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "AWAITING_EXPLICIT_CATEGORY_"
            "INDEX_RECOVERY_APPROVAL"
        ),
        "ready_for_explicit_category_index_recovery_approval": True,
        "ready_for_ls_new_batch_4g_2e_recovery_b": False,
        "ready_for_actual_category_index_read": False,
        "ready_for_category_human_review": False,
        "ready_for_category_mapping_fixation": False,
        "ready_for_payload_injection": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    return f"""# LS-NEW-BATCH-4G-2E-RECOVERY-A Authorization Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Approval gate: `{result["approval_gate_state"]}`

## Previous Attempt

- Previous approval consumed: `true`
- Previous approval reusable: `false`
- Previous lock state: `CONSUMED_COMPLETED_BLOCKED`
- Previous lock deletion allowed: `false`
- Previous lock reuse allowed: `false`

## Planned Category Index Read

- Method: `GET`
- REST path: `/wp-json/wp/v2/categories`
- Per page: `100`
- Order by: `name`
- Order: `asc`
- Include empty categories: `true`
- Maximum requests: `1`
- Maximum attempts: `1`
- Retry allowed: `false`

## Current Activity

- Credential file read: `false`
- Network connection performed: `false`
- HTTP request performed: `false`
- WordPress response read: `false`
- WordPress write performed: `false`
- Category list received: `false`
- Category selected: `false`
- Category mapping fixed: `false`
- Production payload modified: `false`

## Approval State

- Requested approval label: `{result["requested_approval_label"]}`
- Approval label issued: `false`
- Actual GO decision issued: `false`
- Execution allowed: `false`
"""


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--request",
        type=Path,
        default=DEFAULT_REQUEST_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    args = parser.parse_args()

    request_path = resolve_path(
        args.request
    )
    output_path = resolve_path(
        args.output
    )

    try:
        policy = load_json(POLICY_PATH)
        request = load_json(request_path)

        policy_checks = validate_policy(
            policy
        )
        package = build_package(
            request,
            policy,
        )
        result = build_result(
            package,
            request_path,
            output_path,
            policy_checks,
        )

        write_json(
            output_path,
            package,
        )
        write_json(
            RESULT_PATH,
            result,
        )
        write_text(
            REPORT_PATH,
            build_report(result),
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
        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-A"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "approval_label_issued": False,
            "actual_go_decision_issued": False,
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
        }

        write_json(
            RESULT_PATH,
            result,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
