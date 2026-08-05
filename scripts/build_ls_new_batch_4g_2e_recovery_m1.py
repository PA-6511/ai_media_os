#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_authorization_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_authorization_request.example.json"
)
AUTHORIZATION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_authorization.json"
)
PACKAGE = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_authorization_package.example.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m1_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_m1_"
    "dmm_latest_alias_recheck_authorization_report.md"
)
RECHECK_RESULT = (
    ROOT
    / "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_result.json"
)
CONSUMPTION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_consumption.json"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"required file missing: {path}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def write(path: Path, value: dict[str, Any]) -> None:
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
    os.chmod(temporary, 0o600)
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
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def display(path: Path) -> str:
    return str(
        path.resolve().relative_to(
            ROOT.resolve()
        )
    )


def verify_digest(
    value: dict[str, Any],
    field: str,
    expected: str,
    label: str,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        f"{label} digest invalid",
    )
    require(
        stored == expected,
        f"{label} digest mismatch",
    )

    return stored


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M1",
        "policy phase mismatch",
    )

    request = policy["request_contract"]

    require(
        request["target_url"]
        == (
            "https://book.dmm.com/product/"
            "861056/latest/"
        ),
        "target URL mismatch",
    )
    require(
        request["allowed_method"] == "GET",
        "method must be GET",
    )

    for field in [
        "request_body_allowed",
        "query_parameter_addition_allowed",
        "authentication_allowed",
        "login_allowed",
        "cookie_send_allowed",
        "cookie_persistence_allowed",
        "credential_file_read_allowed",
        "session_reuse_allowed",
        "write_operation_allowed",
    ]:
        require(
            request[field] is False,
            f"{field} must remain false",
        )

    redirect = policy["redirect_contract"]

    require(
        redirect["follow_redirects"] is True,
        "redirect following must be enabled",
    )
    require(
        redirect["maximum_redirect_count"] == 5,
        "redirect limit mismatch",
    )
    require(
        redirect["allowed_redirect_hosts"]
        == ["book.dmm.com"],
        "redirect host allowlist mismatch",
    )
    require(
        redirect["cross_host_redirect_allowed"]
        is False,
        "cross-host redirects must be blocked",
    )

    identity = policy[
        "identity_verification_contract"
    ]

    require(
        identity["expected_work_title"]
        == "ダークギャザリング",
        "work title mismatch",
    )
    require(
        identity["expected_volume_number"]
        == 20,
        "volume mismatch",
    )
    require(
        identity["expected_author_name"]
        == "近藤憲一",
        "author mismatch",
    )
    require(
        identity["expected_publisher_name"]
        == "集英社",
        "publisher mismatch",
    )

    canonical = policy[
        "canonical_resolution_contract"
    ]

    require(
        canonical[
            "canonical_product_url_required"
        ]
        is True,
        "canonical URL requirement missing",
    )
    require(
        canonical[
            "latest_alias_as_final_affiliate_link_allowed"
        ]
        is False,
        "latest alias final use must be blocked",
    )

    boundary = policy["execution_boundary"]

    require(
        boundary[
            "authorization_artifact_creation_allowed"
        ]
        is True,
        "authorization creation must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "authorization_artifact_creation_allowed",
            "production_status",
            "safety_state",
        }:
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    parsed = urlparse(
        request["target_url"]
    )

    require(
        parsed.scheme == "https",
        "target scheme mismatch",
    )
    require(
        parsed.hostname == "book.dmm.com",
        "target host mismatch",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "URL userinfo forbidden",
    )

    return [
        "policy_phase_verified",
        "target_url_verified",
        "get_only_verified",
        "authentication_and_cookie_forbidden",
        "redirect_contract_verified",
        "identity_requirements_verified",
        "canonical_resolution_requirement_verified",
        "authorization_only_boundary_verified",
    ]


def validate_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Path],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M1",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "operation mode mismatch",
    )

    for field in [
        "authorization_creation_requested",
        "single_use_get_authorization_requested",
        "redirect_contract_definition_requested",
        "identity_verification_contract_definition_requested",
        "canonical_resolution_contract_definition_requested",
        "failure_contract_definition_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "actual_network_recheck_requested",
        "authorization_consumption_requested",
        "recheck_result_creation_requested",
        "recheck_consumption_evidence_creation_requested",
        "authentication_requested",
        "cookie_send_requested",
        "cookie_persistence_requested",
        "login_requested",
        "credential_file_read_requested",
        "final_affiliate_link_generation_requested",
        "article_modification_requested",
        "article_url_injection_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "network_connection_requested",
        "http_request_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_publish_requested",
        "execution_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    bindings = request["source_bindings"]

    specifications = {
        "m0_result": (
            "m0_result_path",
            "m0_result_file_sha256",
            None,
            None,
        ),
        "m0_fix1": (
            "m0_fix1_path",
            "m0_fix1_file_sha256",
            "fix_evidence_digest_sha256",
            "m0_fix1_artifact_digest_sha256",
        ),
        "plan": (
            "store_link_finalization_plan_path",
            "store_link_finalization_plan_file_sha256",
            "store_link_finalization_plan_digest_sha256",
            "store_link_finalization_plan_artifact_digest_sha256",
        ),
        "article": (
            "generated_article_path",
            "generated_article_file_sha256",
            "article_content_digest_sha256",
            "generated_article_artifact_digest_sha256",
        ),
        "review": (
            "content_human_review_path",
            "content_human_review_file_sha256",
            "human_review_digest_sha256",
            "content_human_review_artifact_digest_sha256",
        ),
        "generation_consumption": (
            "generation_consumption_path",
            "generation_consumption_file_sha256",
            "consumption_evidence_digest_sha256",
            "generation_consumption_artifact_digest_sha256",
        ),
        "input": (
            "article_input_path",
            "article_input_file_sha256",
            "article_input_digest_sha256",
            "article_input_artifact_digest_sha256",
        ),
    }

    values: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}

    for label, (
        path_field,
        file_hash_field,
        digest_field,
        digest_reference_field,
    ) in specifications.items():
        path = resolve(
            bindings[path_field]
        )

        require(
            file_sha256(path)
            == bindings[file_hash_field],
            f"{label} file hash mismatch",
        )

        value = load(path)

        if digest_field is not None:
            verify_digest(
                value,
                digest_field,
                bindings[
                    digest_reference_field
                ],
                label,
            )

        paths[label] = path
        values[label] = value

    require(
        values["m0_result"]["status"]
        == (
            "PASS_FRESH_STORE_LINK_FINALIZATION_PLAN_"
            "FIXED_NO_LINK_GENERATION_NO_NETWORK"
        ),
        "M0 status mismatch",
    )
    require(
        values["m0_fix1"]["status"]
        == (
            "PASS_M0_ARTICLE_STORE_NAVIGATION_"
            "SCHEMA_KEY_REFERENCE_CORRECTED"
        ),
        "M0 Fix1 status mismatch",
    )

    dmm = values["plan"]["stores"][
        "dmm_books"
    ]

    require(
        dmm["verification_source"]["url"]
        == request["target_url"],
        "registered DMM target mismatch",
    )
    require(
        dmm["recheck"]["required"] is True,
        "DMM recheck requirement missing",
    )
    require(
        dmm["recheck"]["completed"] is False,
        "DMM recheck unexpectedly completed",
    )

    article_navigation = values[
        "article"
    ]["store_navigation"]

    require(
        article_navigation[
            "dmm_url_included"
        ]
        is False,
        "DMM URL already included",
    )
    require(
        article_navigation[
            "final_affiliate_urls_included"
        ]
        is False,
        "affiliate URLs already included",
    )

    approval = load(
        resolve(request["approval_path"])
    )
    approval_comparable = copy.deepcopy(
        approval
    )
    approval_stored = approval_comparable.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        isinstance(approval_stored, str)
        and digest(approval_comparable)
        == approval_stored,
        "approval digest invalid",
    )
    require(
        digest(approval)
        == request[
            "approval_file_digest_sha256"
        ],
        "approval file digest mismatch",
    )
    require(
        approval["approval_label"]
        == (
            "FRESH_DMM_LATEST_ALIAS_"
            "RECHECK_AUTHORIZATION_APPROVED"
        ),
        "approval label mismatch",
    )

    return (
        approval,
        paths,
        [
            "request_scope_verified",
            "source_file_hashes_verified",
            "source_artifact_digests_verified",
            "m0_result_verified",
            "m0_fix1_verified",
            "registered_dmm_target_verified",
            "dmm_recheck_pending_verified",
            "generated_article_has_no_dmm_url",
            "human_authorization_approval_verified",
            "network_not_requested",
            "wordpress_not_requested",
        ],
    )


def ensure_authorization(
    stable: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if AUTHORIZATION.exists():
        existing = load(AUTHORIZATION)
        comparable = copy.deepcopy(existing)
        stored = comparable.pop(
            "authorization_digest_sha256",
            None,
        )
        authorized_at = comparable.pop(
            "authorized_at_utc",
            None,
        )

        require(
            isinstance(authorized_at, str)
            and authorized_at,
            "existing authorization timestamp invalid",
        )
        require(
            comparable == stable,
            "existing authorization semantic mismatch",
        )

        without_digest = copy.deepcopy(
            existing
        )
        without_digest.pop(
            "authorization_digest_sha256",
            None,
        )

        require(
            isinstance(stored, str)
            and digest(without_digest)
            == stored,
            "existing authorization digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(stable)
    without_digest[
        "authorized_at_utc"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    authorization = copy.deepcopy(
        without_digest
    )
    authorization[
        "authorization_digest_sha256"
    ] = digest(without_digest)

    write(AUTHORIZATION, authorization)

    return authorization, True


def main() -> int:
    try:
        policy = load(POLICY)
        request = load(REQUEST)

        policy_checks = validate_policy(
            policy
        )
        (
            approval,
            source_paths,
            source_checks,
        ) = validate_sources(
            request,
            policy,
        )

        source_hashes_before = {
            label: file_sha256(path)
            for label, path
            in source_paths.items()
        }

        stable_authorization = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_LATEST_ALIAS_ONE_SHOT_"
                "READ_ONLY_RECHECK_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M1"
            ),
            "authorization_id": (
                "DMM_LATEST_ALIAS_861056_ONE_SHOT_"
                "READ_ONLY_RECHECK_AUTHORIZATION_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "dmm_series_id": "861056",
            "authorized_next_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M2"
            ),
            "authorized_operation": (
                "ONE_SHOT_READ_ONLY_GET_"
                "DMM_LATEST_ALIAS_RECHECK"
            ),
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "target_request": {
                "method": "GET",
                "url": (
                    "https://book.dmm.com/product/"
                    "861056/latest/"
                ),
                "scheme": "https",
                "initial_host": "book.dmm.com",
                "request_body_allowed": False,
                "authentication_allowed": False,
                "login_allowed": False,
                "cookie_send_allowed": False,
                "cookie_persistence_allowed": False,
                "credential_file_read_allowed": False,
                "write_operation_allowed": False,
                "allowed_request_headers": [
                    "Accept",
                    "Accept-Language",
                    "User-Agent",
                ],
                "forbidden_request_headers": [
                    "Authorization",
                    "Cookie",
                    "Proxy-Authorization",
                    "X-Api-Key",
                    "X-CSRF-Token",
                ]
            },
            "redirect_requirements": {
                "follow_redirects": True,
                "maximum_redirect_count": 5,
                "allowed_schemes": [
                    "https"
                ],
                "allowed_hosts": [
                    "book.dmm.com"
                ],
                "cross_host_redirect_allowed": False,
                "https_downgrade_allowed": False,
                "redirect_chain_recording_required": True,
                "final_url_recording_required": True
            },
            "response_requirements": {
                "accepted_final_http_statuses": [
                    200
                ],
                "http_status_recording_required": True,
                "response_body_sha256_required": True,
                "full_response_body_persistence_allowed": False,
                "minimal_extraction_only": True
            },
            "identity_requirements": {
                "expected_work_title": (
                    "ダークギャザリング"
                ),
                "expected_volume_label": "第20巻",
                "expected_volume_number": 20,
                "expected_author_name": "近藤憲一",
                "expected_publisher_name": "集英社",
                "expected_series_id": "861056",
                "work_title_match_required": True,
                "volume_match_required": True,
                "author_match_required": True,
                "publisher_match_required": True,
                "series_identity_match_required": True,
                "missing_required_field_is_failure": True
            },
            "canonical_resolution_requirements": {
                "canonical_product_url_required": True,
                "allowed_scheme": "https",
                "allowed_hosts": [
                    "book.dmm.com"
                ],
                "canonical_url_must_not_equal_latest_alias": True,
                "canonical_url_must_bind_to_expected_series": True,
                "latest_alias_as_final_affiliate_link_allowed": False
            },
            "planned_evidence": {
                "recheck_result_path": (
                    "exchange/rechecks/new_release/fresh/"
                    "new-release-comic-20260703-001."
                    "dmm_latest_alias_recheck_result.json"
                ),
                "consumption_evidence_path": (
                    "exchange/authorizations/new_release/fresh/"
                    "new-release-comic-20260703-001."
                    "dmm_latest_alias_recheck_consumption.json"
                )
            },
            "failure_actions": {
                "communication_failure": (
                    "HIDE_DMM_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                ),
                "identity_mismatch": (
                    "HIDE_DMM_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                ),
                "required_identity_field_missing": (
                    "HIDE_DMM_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                ),
                "canonical_product_unresolved": (
                    "HIDE_DMM_SLOT_AND_KEEP_DMM_LINK_UNAVAILABLE"
                ),
                "redirect_to_unapproved_host": (
                    "ABORT_AND_HIDE_DMM_SLOT"
                ),
                "automatic_fallback_url_allowed": False,
                "dummy_url_allowed": False
            },
            "approval_path": request[
                "approval_path"
            ],
            "approval_digest_sha256": approval[
                "approval_evidence_digest_sha256"
            ],
            "source_bindings": request[
                "source_bindings"
            ],
            "actual_network_recheck_performed": False,
            "authorization_consumption_evidence_created": False,
            "recheck_result_created": False,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_RECHECK_AUTHORIZATION_RECORDED_"
                "UNCONSUMED_AWAITING_EXECUTE_NOW_CONFIRMATION"
            )
        }

        authorization, created = (
            ensure_authorization(
                stable_authorization
            )
        )

        for label, path in source_paths.items():
            require(
                file_sha256(path)
                == source_hashes_before[label],
                f"source modified: {label}",
            )

        require(
            not RECHECK_RESULT.exists(),
            "recheck result unexpectedly exists",
        )
        require(
            not CONSUMPTION.exists(),
            "recheck consumption unexpectedly exists",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M1"
            ),
            "policy_id": policy["policy_id"],
            "authorization_path": display(
                AUTHORIZATION
            ),
            "authorization_file_sha256": (
                file_sha256(AUTHORIZATION)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "authorization_created_in_this_run": (
                created
            ),
            "authorization_consumed": False,
            "actual_network_recheck_performed": False,
            "source_artifacts_modified": False,
            "final_affiliate_link_generated": False,
            "fresh_payload_created": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "verified_checks": (
                policy_checks
                + source_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "dmm_recheck_authorization_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M1"
            ),
            "status": (
                "PASS_DMM_LATEST_ALIAS_ONE_SHOT_READ_ONLY_"
                "RECHECK_AUTHORIZATION_FIXED_NO_NETWORK"
            ),
            "decision": (
                "DMM_RECHECK_AUTHORIZATION_RECORDED_"
                "AWAITING_EXPLICIT_EXECUTE_NOW_CONFIRMATION"
            ),
            "approval_label": (
                "FRESH_DMM_LATEST_ALIAS_"
                "RECHECK_AUTHORIZATION_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "dmm_series_id": "861056",
            "target_url": (
                "https://book.dmm.com/product/"
                "861056/latest/"
            ),
            "authorization_path": package[
                "authorization_path"
            ],
            "authorization_file_sha256": package[
                "authorization_file_sha256"
            ],
            "authorization_digest_sha256": package[
                "authorization_digest_sha256"
            ],
            "dmm_recheck_authorization_package_digest_sha256": (
                package[
                    "dmm_recheck_authorization_package_digest_sha256"
                ]
            ),
            "authorization_created_in_this_run": (
                created
            ),
            "single_use": True,
            "allowed_method": "GET",
            "authentication_allowed": False,
            "cookie_send_allowed": False,
            "cookie_persistence_allowed": False,
            "login_allowed": False,
            "credential_file_read": False,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "redirect_contract_fixed": True,
            "identity_verification_contract_fixed": True,
            "canonical_resolution_contract_fixed": True,
            "failure_and_hide_contract_fixed": True,
            "actual_network_recheck_performed": False,
            "recheck_result_created": False,
            "recheck_consumption_evidence_created": False,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "source_artifacts_modified": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_RECHECK_AUTHORIZATION_RECORDED_"
                "UNCONSUMED_AWAITING_EXECUTE_NOW_CONFIRMATION"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m2": True,
            "ready_for_dmm_recheck_execute_now_confirmation": True,
            "ready_for_actual_dmm_recheck": False,
            "ready_for_final_affiliate_link_generation": False,
            "ready_for_article_url_injection": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "authorization_artifact_verified",
                    "authorization_digest_verified",
                    "authorization_unconsumed",
                    "recheck_result_absent",
                    "recheck_consumption_evidence_absent",
                    "source_artifacts_preserved",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "production_gate_closed",
                ]
            ),
        }

        write(PACKAGE, package)
        write(RESULT, result)

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M1

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Target: `{result["target_url"]}`
- Method: `GET`
- Single use: `true`

## Request Restrictions

- Authentication: `false`
- Login: `false`
- Cookie send: `false`
- Cookie persistence: `false`
- Request body: `false`
- Write operation: `false`

## Verification Requirements

- Redirect chain: required
- Final HTTP status: required
- Work title: required
- Volume: required
- Author: required
- Publisher: required
- Canonical product URL: required

## Current Boundary

- Authorization consumed: `false`
- Network recheck performed: `false`
- Recheck result created: `false`
- Final affiliate link generated: `false`
- Article modified: `false`
- Payload created: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
"""

        write_text(REPORT, report)

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except ValidationError as exc:
        failure = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M1"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "authorization_consumed": False,
            "actual_network_recheck_performed": False,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "fresh_payload_created": False,
            "network_connection_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO"
        }

        write(RESULT, failure)

        print(
            json.dumps(
                failure,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
