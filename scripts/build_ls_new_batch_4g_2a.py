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
    "new_release_wp_actual_read_only_lookup_authorization_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_actual_read_only_lookup_authorization_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_actual_read_only_lookup_authorization_package.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4g_2a_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2a_actual_read_only_lookup_authorization_report.md"
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


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
            f"invalid JSON: {path}: {exc}"
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
    path.parent.mkdir(parents=True, exist_ok=True)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        value,
        encoding="utf-8",
    )
    temporary.replace(path)


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(
            resolved.relative_to(ROOT.resolve())
        )
    except ValueError:
        return str(resolved)


def resolve_repo_path(value: str) -> Path:
    path = Path(value)

    if path.is_absolute():
        return path

    return ROOT / path


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2A",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == (
            "NEW_RELEASE_WP_ACTUAL_READ_ONLY_"
            "LOOKUP_AUTHORIZATION_POLICY_V1"
        ),
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == (
            "ONE_SHOT_ACTUAL_READ_ONLY_"
            "LOOKUP_AUTHORIZATION_GATE"
        ),
        "operation mode mismatch",
    )
    checks.append("authorization_gate_mode")

    approval = policy.get(
        "requested_approval",
        {},
    )

    require(
        approval.get("requested_approval_label")
        == (
            "APPROVED_FOR_ONE_SHOT_"
            "READ_ONLY_CATEGORY_LOOKUP_ONLY"
        ),
        "requested approval label mismatch",
    )
    require(
        approval.get("approval_label_issued")
        is False,
        "approval label must not be issued",
    )
    require(
        approval.get("approval_label_consumed")
        is False,
        "approval label must not be consumed",
    )
    require(
        approval.get(
            "actual_go_decision_issued"
        )
        is False,
        "actual GO must not be issued",
    )
    require(
        approval.get(
            "human_explicit_approval_required"
        )
        is True,
        "human explicit approval must be required",
    )
    checks.append("approval_gate_closed")

    scope = policy.get(
        "one_shot_http_scope",
        {},
    )

    require(
        scope.get("maximum_http_requests") == 1,
        "maximum HTTP requests must be one",
    )
    require(
        scope.get("maximum_attempts") == 1,
        "maximum attempts must be one",
    )
    require(
        scope.get("retry_allowed") is False,
        "retry must remain forbidden",
    )
    require(
        scope.get("allowed_method") == "GET",
        "only GET may be requested",
    )
    require(
        scope.get("allowed_rest_path")
        == "/wp-json/wp/v2/categories",
        "REST path mismatch",
    )
    require(
        scope.get("request_body_allowed")
        is False,
        "request body must remain forbidden",
    )
    require(
        scope.get("redirect_follow_allowed")
        is False,
        "redirect following must remain forbidden",
    )
    require(
        scope.get("proxy_use_allowed")
        is False,
        "proxy use must remain forbidden",
    )
    require(
        scope.get("tls_verification_required")
        is True,
        "TLS verification must be required",
    )
    require(
        scope.get("https_required") is True,
        "HTTPS must be required",
    )
    checks.append("one_shot_http_scope")

    fixture = policy.get(
        "fixture_isolation",
        {},
    )

    require(
        fixture.get("fixture_category_id")
        == 980001,
        "fixture category ID reference mismatch",
    )
    require(
        fixture.get(
            "fixture_category_id_authorized"
        )
        is False,
        "fixture category ID must not be authorized",
    )
    require(
        fixture.get(
            "fixture_category_id_payload_injection_allowed"
        )
        is False,
        "fixture ID payload injection must remain forbidden",
    )
    require(
        fixture.get(
            "fixture_category_id_discard_required"
        )
        is True,
        "fixture category ID must be discarded",
    )
    checks.append("fixture_id_isolation")

    current = policy.get(
        "current_phase_access",
        {},
    )

    for field in [
        "credential_file_metadata_read_allowed",
        "credential_file_content_read_allowed",
        "environment_variable_read_allowed",
        "authorization_header_construction_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "tls_connection_allowed",
        "http_request_allowed",
        "wordpress_response_read_allowed",
    ]:
        require(
            current.get(field) is False,
            f"{field} must remain false",
        )

    checks.append("current_phase_no_access")

    boundary = policy.get(
        "execution_boundary",
        {},
    )

    for field in [
        "credential_value_output_allowed",
        "environment_variable_export_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "tls_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_post_read_allowed",
        "wordpress_media_read_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "x_api_call_allowed",
        "external_api_call_allowed",
        "execution_approval_issued",
        "execution_allowed",
    ]:
        require(
            boundary.get(field) is False,
            f"{field} must remain false",
        )

    require(
        boundary.get("production_status")
        == "NO_GO",
        "production status must remain NO_GO",
    )
    require(
        boundary.get("safety_state")
        == (
            "AWAITING_EXPLICIT_ONE_SHOT_"
            "LOOKUP_APPROVAL"
        ),
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    list[str],
    dict[str, Any],
]:
    source_path_value = request.get(
        "source_implementation_package_path"
    )

    require(
        isinstance(source_path_value, str),
        "source package path must be a string",
    )

    source_path = resolve_repo_path(
        source_path_value
    )
    source = load_json(source_path)

    require(
        source.get("phase_id")
        == policy.get("source_phase_id"),
        "source phase mismatch",
    )
    require(
        source.get("operation_mode")
        == "LOCAL_WORDPRESS_API_MOCK_ONLY",
        "source operation mode mismatch",
    )

    expected_digest = source.get(
        "implementation_package_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source implementation digest is invalid",
    )
    require(
        request.get(
            "source_implementation_package_digest_sha256"
        )
        == expected_digest,
        "request source digest mismatch",
    )

    source_without_digest = copy.deepcopy(
        source
    )
    source_without_digest.pop(
        "implementation_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_digest,
        "source implementation digest verification failed",
    )

    lookup = source.get(
        "lookup_result",
        {},
    )
    mappings = lookup.get("mappings")

    require(
        isinstance(mappings, list)
        and len(mappings) == 1,
        "source must contain exactly one mock mapping",
    )

    mapping = mappings[0]

    require(
        mapping.get("category_slug")
        == "comic-new-release",
        "source category slug mismatch",
    )
    require(
        mapping.get("category_name")
        == "コミック新刊",
        "source category name mismatch",
    )
    require(
        mapping.get(
            "candidate_fixture_category_id"
        )
        == 980001,
        "source fixture category ID mismatch",
    )
    require(
        mapping.get("production_usable")
        is False,
        "source fixture mapping must not be production usable",
    )
    require(
        mapping.get("payload_injection_allowed")
        is False,
        "source fixture payload injection must remain blocked",
    )

    source_boundary = source.get(
        "execution_boundary",
        {},
    )

    require(
        source_boundary.get(
            "network_connection_allowed"
        )
        is False,
        "source network authority must remain closed",
    )
    require(
        source_boundary.get(
            "wordpress_api_call_allowed"
        )
        is False,
        "source WordPress authority must remain closed",
    )
    require(
        source_boundary.get("execution_allowed")
        is False,
        "source execution gate must remain closed",
    )

    return (
        [
            "source_phase_identity",
            "source_implementation_digest_verified",
            "source_mock_matching_verified",
            "source_fixture_id_identified",
            "source_fixture_id_not_production_usable",
            "source_fixture_id_not_injected",
            "source_network_authority_closed",
            "source_wordpress_authority_closed",
            "source_execution_gate_closed",
        ],
        mapping,
    )


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2A",
        "request phase_id mismatch",
    )
    require(
        request.get("operation_mode")
        == (
            "ONE_SHOT_ACTUAL_READ_ONLY_"
            "LOOKUP_AUTHORIZATION_GATE"
        ),
        "request operation mode mismatch",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    requested_scope = request.get(
        "requested_approval_scope"
    )

    require(
        isinstance(requested_scope, dict),
        "requested approval scope must be an object",
    )

    policy_scope = policy[
        "one_shot_http_scope"
    ]

    require(
        requested_scope.get(
            "approval_scope_id"
        )
        == (
            "ONE_SHOT_WORDPRESS_CATEGORY_"
            "LOOKUP_COMIC_NEW_RELEASE"
        ),
        "approval scope ID mismatch",
    )
    require(
        requested_scope.get(
            "requested_approval_label"
        )
        == (
            "APPROVED_FOR_ONE_SHOT_"
            "READ_ONLY_CATEGORY_LOOKUP_ONLY"
        ),
        "approval label mismatch",
    )
    require(
        requested_scope.get(
            "maximum_http_requests"
        )
        == policy_scope[
            "maximum_http_requests"
        ],
        "maximum HTTP requests mismatch",
    )
    require(
        requested_scope.get(
            "maximum_attempts"
        )
        == policy_scope["maximum_attempts"],
        "maximum attempts mismatch",
    )
    require(
        requested_scope.get("retry_allowed")
        is False,
        "retry must remain false",
    )
    require(
        requested_scope.get("method") == "GET",
        "method must be GET",
    )
    require(
        requested_scope.get("rest_path")
        == "/wp-json/wp/v2/categories",
        "REST path mismatch",
    )
    require(
        requested_scope.get("query_parameters")
        == policy_scope[
            "allowed_query_parameters"
        ],
        "query parameters mismatch",
    )
    require(
        requested_scope.get("request_body")
        is None,
        "request body must remain null",
    )
    require(
        requested_scope.get("redirect_follow")
        is False,
        "redirect following must remain false",
    )
    require(
        requested_scope.get("proxy_use")
        is False,
        "proxy use must remain false",
    )
    require(
        requested_scope.get("tls_verification")
        is True,
        "TLS verification must remain true",
    )
    require(
        requested_scope.get("https_required")
        is True,
        "HTTPS requirement must remain true",
    )

    require(
        request.get("target_category")
        == {
            "category_slug": "comic-new-release",
            "category_name": "コミック新刊",
        },
        "target category mismatch",
    )

    require(
        request.get(
            "fixture_category_id_reference"
        )
        == 980001,
        "fixture category ID reference mismatch",
    )
    require(
        request.get(
            "fixture_category_id_authorized"
        )
        is False,
        "fixture category ID must remain unauthorized",
    )
    require(
        request.get(
            "fixture_category_id_payload_injection_requested"
        )
        is False,
        "fixture ID injection must not be requested",
    )

    for field in [
        "credential_file_read_requested",
        "credential_values_output_requested",
        "environment_variable_export_requested",
        "authorization_header_construction_requested",
        "dns_resolution_requested",
        "network_connection_requested",
        "tls_connection_requested",
        "http_request_requested",
        "wordpress_response_read_requested",
        "wordpress_write_requested",
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


def build_authorization_scope(
    policy: dict[str, Any],
) -> dict[str, Any]:
    http_scope = policy[
        "one_shot_http_scope"
    ]
    target = policy["target_category"]

    scope_without_digest = {
        "approval_scope_id": (
            "ONE_SHOT_WORDPRESS_CATEGORY_"
            "LOOKUP_COMIC_NEW_RELEASE"
        ),
        "requested_approval_label": (
            "APPROVED_FOR_ONE_SHOT_"
            "READ_ONLY_CATEGORY_LOOKUP_ONLY"
        ),
        "credential_file_path": (
            policy["credential_contract"][
                "credential_file_path"
            ]
        ),
        "base_url_source": (
            "VERIFIED_PRODUCTION_CREDENTIAL_FILE"
        ),
        "https_required": True,
        "method": http_scope[
            "allowed_method"
        ],
        "rest_path": http_scope[
            "allowed_rest_path"
        ],
        "query_parameters": copy.deepcopy(
            http_scope[
                "allowed_query_parameters"
            ]
        ),
        "target_category": {
            "category_slug": target[
                "category_slug"
            ],
            "category_name": target[
                "category_name"
            ],
        },
        "maximum_http_requests": 1,
        "maximum_attempts": 1,
        "retry_allowed": False,
        "request_body": None,
        "redirect_follow": False,
        "cross_origin_redirect": False,
        "proxy_use": False,
        "timeout_seconds": http_scope[
            "timeout_seconds"
        ],
        "maximum_response_bytes": http_scope[
            "maximum_response_bytes"
        ],
        "tls_verification": True,
        "allowed_http_statuses": [200],
        "required_content_type_prefix": (
            "application/json"
        ),
        "fixture_category_id_reference": 980001,
        "fixture_category_id_authorized": False,
        "fixture_category_id_discard_required": True,
        "production_category_id_payload_injection_allowed": False,
        "wordpress_write_allowed": False,
        "approval_label_issued": False,
        "actual_go_decision_issued": False,
        "execution_allowed": False,
    }

    scope = copy.deepcopy(
        scope_without_digest
    )
    scope["authorization_scope_digest_sha256"] = (
        canonical_digest(scope_without_digest)
    )

    return scope


def build_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    (
        source_checks,
        source_mapping,
    ) = verify_source_package(
        request,
        policy,
    )

    validate_request(
        request,
        policy,
    )

    authorization_scope = (
        build_authorization_scope(policy)
    )

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4G-2A",
        "policy_id": policy["policy_id"],
        "authorization_package_id": (
            "wp-one-shot-read-only-"
            "category-lookup-authorization"
        ),
        "operation_mode": (
            "ONE_SHOT_ACTUAL_READ_ONLY_"
            "LOOKUP_AUTHORIZATION_GATE"
        ),
        "source_mock_mapping_summary": {
            "category_slug": source_mapping[
                "category_slug"
            ],
            "category_name": source_mapping[
                "category_name"
            ],
            "fixture_category_id": source_mapping[
                "candidate_fixture_category_id"
            ],
            "fixture_id_authorized": False,
            "fixture_id_production_usable": False,
            "fixture_id_payload_injection_allowed": False,
            "fixture_id_discard_required": True,
        },
        "authorization_scope": authorization_scope,
        "approval_gate": {
            "state": "AWAITING_EXPLICIT_APPROVAL",
            "requested_approval_label": (
                "APPROVED_FOR_ONE_SHOT_"
                "READ_ONLY_CATEGORY_LOOKUP_ONLY"
            ),
            "approval_label_issued": False,
            "approval_label_consumed": False,
            "actual_go_decision_issued": False,
            "approval_token_generation_allowed": False,
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
            "production_category_id_received": False,
            "production_payload_modified": False,
        },
        "execution_boundary": {
            "credential_file_read_allowed": False,
            "credential_value_output_allowed": False,
            "environment_variable_export_allowed": False,
            "authorization_header_construction_allowed": False,
            "dns_resolution_allowed": False,
            "network_connection_allowed": False,
            "tls_connection_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_category_lookup_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "external_api_call_allowed": False,
            "execution_approval_issued": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "AWAITING_EXPLICIT_ONE_SHOT_"
                "LOOKUP_APPROVAL"
            ),
        },
        "verified_checks": source_checks,
    }

    package = copy.deepcopy(
        package_without_digest
    )
    package[
        "authorization_package_digest_sha256"
    ] = canonical_digest(
        package_without_digest
    )

    return package


def build_result(
    package: dict[str, Any],
    *,
    request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    gate = package["approval_gate"]
    activity = package[
        "current_phase_activity"
    ]
    scope = package[
        "authorization_scope"
    ]

    return {
        "phase_id": "LS-NEW-BATCH-4G-2A",
        "status": (
            "PASS_ONE_SHOT_READ_ONLY_LOOKUP_"
            "AUTHORIZATION_GATE_READY_NO_NETWORK"
        ),
        "decision": (
            "AWAITING_EXPLICIT_APPROVAL_"
            "FOR_ONE_SHOT_GET"
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
        "approval_gate_state": gate["state"],
        "requested_approval_label": gate[
            "requested_approval_label"
        ],
        "approval_label_issued": gate[
            "approval_label_issued"
        ],
        "approval_label_consumed": gate[
            "approval_label_consumed"
        ],
        "actual_go_decision_issued": gate[
            "actual_go_decision_issued"
        ],
        "approval_token_present": False,
        "human_explicit_approval_required": gate[
            "human_explicit_approval_required"
        ],
        "http_method": scope["method"],
        "rest_path": scope["rest_path"],
        "target_category_slug": scope[
            "target_category"
        ]["category_slug"],
        "target_category_name": scope[
            "target_category"
        ]["category_name"],
        "maximum_http_requests": scope[
            "maximum_http_requests"
        ],
        "maximum_attempts": scope[
            "maximum_attempts"
        ],
        "retry_allowed": scope[
            "retry_allowed"
        ],
        "redirect_follow": scope[
            "redirect_follow"
        ],
        "proxy_use": scope["proxy_use"],
        "tls_verification": scope[
            "tls_verification"
        ],
        "fixture_category_id_reference": scope[
            "fixture_category_id_reference"
        ],
        "fixture_category_id_authorized": scope[
            "fixture_category_id_authorized"
        ],
        "fixture_category_id_discard_required": scope[
            "fixture_category_id_discard_required"
        ],
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
        "production_category_id_received": activity[
            "production_category_id_received"
        ],
        "production_payload_modified": activity[
            "production_payload_modified"
        ],
        "authorization_scope_digest_sha256": scope[
            "authorization_scope_digest_sha256"
        ],
        "authorization_package_digest_sha256": package[
            "authorization_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity",
                "approval_scope_identity",
                "approval_label_requested_not_issued",
                "actual_go_not_issued",
                "approval_token_absent",
                "one_shot_request_count_fixed",
                "single_attempt_fixed",
                "retry_disabled",
                "get_method_locked",
                "category_endpoint_locked",
                "category_query_locked",
                "request_body_absent",
                "redirect_follow_disabled",
                "proxy_use_disabled",
                "tls_verification_required",
                "https_required",
                "target_category_locked",
                "fixture_category_id_unauthorized",
                "fixture_category_id_discard_required",
                "production_payload_injection_blocked",
                "credential_file_unread",
                "authorization_header_unconstructed",
                "network_unaccessed",
                "wordpress_unaccessed",
                "wordpress_write_forbidden",
                "authorization_scope_digest_generated",
                "authorization_package_digest_generated",
                "execution_gate_closed",
            ]
        ),
        "credential_file_read_allowed": False,
        "credential_value_output_allowed": False,
        "environment_variable_export_allowed": False,
        "authorization_header_construction_allowed": False,
        "dns_resolution_allowed": False,
        "network_connection_allowed": False,
        "tls_connection_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "AWAITING_EXPLICIT_ONE_SHOT_"
            "LOOKUP_APPROVAL"
        ),
        "ready_for_explicit_actual_lookup_approval": True,
        "ready_for_ls_new_batch_4g_2b": False,
        "ready_for_actual_read_only_lookup": False,
        "ready_for_category_id_resolution": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(
    result: dict[str, Any],
) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4G-2A One-Shot Read-Only Lookup Authorization Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Approval gate: `{result["approval_gate_state"]}`
- Requested approval label: `{result["requested_approval_label"]}`

## One-Shot Scope

- Method: `{result["http_method"]}`
- REST path: `{result["rest_path"]}`
- Target slug: `{result["target_category_slug"]}`
- Target name: `{result["target_category_name"]}`
- Maximum HTTP requests: `{result["maximum_http_requests"]}`
- Maximum attempts: `{result["maximum_attempts"]}`
- Retry allowed: `{str(result["retry_allowed"]).lower()}`
- Redirect follow: `{str(result["redirect_follow"]).lower()}`
- Proxy use: `{str(result["proxy_use"]).lower()}`
- TLS verification: `{str(result["tls_verification"]).lower()}`

## Approval State

- Approval label issued: `false`
- Approval label consumed: `false`
- Actual GO decision issued: `false`
- Approval token present: `false`
- Human explicit approval required: `true`

## Fixture Isolation

- Fixture category ID: `{result["fixture_category_id_reference"]}`
- Fixture ID authorized: `false`
- Fixture ID discard required: `true`
- Production payload modified: `false`

## Current Access State

- Credential file read: `false`
- Credential values loaded: `false`
- Credential values output: `false`
- Authorization header constructed: `false`
- DNS resolution performed: `false`
- Network connection performed: `false`
- TLS connection performed: `false`
- HTTP request performed: `false`
- WordPress response read: `false`
- WordPress write performed: `false`

## Verified Checks

{checks}

## Safety Boundary

- Credential file read allowed: `false`
- Authorization-header construction allowed: `false`
- Network connection allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress write allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `AWAITING_EXPLICIT_ONE_SHOT_LOOKUP_APPROVAL`

## Next State

実GETの対象、メソッド、クエリ、最大回数、失敗時停止、
認証値非出力、リダイレクト禁止、プロキシ禁止を固定しました。

このPhaseでは認証ファイル、DNS、TLS、HTTP、WordPressには
アクセスしていません。

`LS-NEW-BATCH-4G-2B` へ進むには、
`APPROVED_FOR_ONE_SHOT_READ_ONLY_CATEGORY_LOOKUP_ONLY`
に相当する人間の明示承認が必要です。
"""


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def parse_args() -> argparse.Namespace:
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
    parser.add_argument(
        "--check-only",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

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
            request=request,
            policy=policy,
        )
        result = build_result(
            package,
            request_path=request_path,
            output_path=output_path,
            policy_checks=policy_checks,
        )

        if not args.check_only:
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
            "phase_id": "LS-NEW-BATCH-4G-2A",
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "approval_label_issued": False,
            "actual_go_decision_issued": False,
            "approval_token_present": False,
            "credential_file_read": False,
            "credential_values_output": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_response_read": False,
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
