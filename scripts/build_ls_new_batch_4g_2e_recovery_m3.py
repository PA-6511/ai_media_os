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

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_authorization_policy.json"
)
REQUEST = ROOT / (
    "exchange/examples/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_authorization_request.example.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "authorization.json"
)
PACKAGE = ROOT / (
    "exchange/examples/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_authorization_package.example.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m3_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m3_"
    "post_parser_fix_dmm_recheck_authorization_report.md"
)
PLANNED_RECHECK_RESULT = ROOT / (
    "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "result.json"
)
PLANNED_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "consumption.json"
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
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def write_text(
    path: Path,
    value: str,
) -> None:
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


def verify_self_digest(
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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M3",
        "policy phase mismatch",
    )

    authorization = policy[
        "authorization_contract"
    ]

    require(
        authorization["single_use"] is True,
        "single-use requirement missing",
    )
    require(
        authorization["authorization_consumed"]
        is False,
        "authorization must be unconsumed",
    )
    require(
        authorization[
            "old_m1_authorization_reuse_allowed"
        ]
        is False,
        "old authorization reuse must be blocked",
    )

    parser = policy["parser_binding"]

    require(
        parser["required_runner_sha256"]
        == (
            "adfe2cbb8478458e8940eb0d67de4aa8"
            "e223ba6923353a2f0f0dc4d35e37e35f"
        ),
        "remediated runner hash mismatch",
    )
    require(
        parser[
            "required_fix_evidence_digest_sha256"
        ]
        == (
            "8f46f1da365be87d4308fdb8327422003"
            "f65ee323dfc2ee7b938348a6af9c807"
        ),
        "fix evidence digest mismatch",
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
        "authentication_allowed",
        "login_allowed",
        "cookie_send_allowed",
        "cookie_persistence_allowed",
        "credential_file_read_allowed",
        "proxy_environment_use_allowed",
        "automatic_retry_allowed",
        "write_operation_allowed",
    ]:
        require(
            request[field] is False,
            f"{field} must remain false",
        )

    redirect = policy["redirect_contract"]

    require(
        redirect["maximum_redirect_count"] == 5,
        "redirect count mismatch",
    )
    require(
        redirect["allowed_redirect_hosts"]
        == ["book.dmm.com"],
        "redirect host mismatch",
    )
    require(
        redirect["cross_host_redirect_allowed"]
        is False,
        "cross-host redirect must be blocked",
    )

    boundary = policy["execution_boundary"]

    require(
        boundary[
            "new_authorization_artifact_creation_allowed"
        ]
        is True,
        "new authorization creation must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "new_authorization_artifact_creation_allowed",
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
        "new_separate_authorization_contract_verified",
        "remediated_parser_binding_verified",
        "target_url_verified",
        "get_only_verified",
        "authentication_cookie_and_retry_forbidden",
        "redirect_contract_verified",
        "identity_contract_verified",
        "canonical_contract_verified",
        "historical_preservation_contract_verified",
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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M3",
        "request phase mismatch",
    )

    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "operation mode mismatch",
    )

    for field in [
        "new_authorization_creation_requested",
        "single_use_get_authorization_requested",
        "remediated_parser_binding_requested",
        "identity_verification_contract_requested",
        "canonical_resolution_contract_requested",
        "failure_contract_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "old_authorization_reuse_requested",
        "actual_network_recheck_requested",
        "new_authorization_consumption_requested",
        "new_recheck_result_creation_requested",
        "new_consumption_evidence_creation_requested",
        "authentication_requested",
        "cookie_send_requested",
        "cookie_persistence_requested",
        "login_requested",
        "credential_file_read_requested",
        "request_body_requested",
        "write_operation_requested",
        "automatic_retry_requested",
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

    json_specs = {
        "fix_result": (
            "m2_fix1_result_path",
            "m2_fix1_result_file_sha256",
            "fix_evidence_digest_sha256",
            "m2_fix1_artifact_digest_sha256",
        ),
        "old_recheck": (
            "old_m2_recheck_result_path",
            "old_m2_recheck_result_file_sha256",
            "dmm_recheck_result_digest_sha256",
            "old_m2_recheck_result_artifact_digest_sha256",
        ),
        "old_consumption": (
            "old_m2_consumption_path",
            "old_m2_consumption_file_sha256",
            "consumption_evidence_digest_sha256",
            "old_m2_consumption_artifact_digest_sha256",
        ),
        "old_execute_approval": (
            "old_m2_execute_approval_path",
            "old_m2_execute_approval_file_sha256",
            "approval_evidence_digest_sha256",
            "old_m2_execute_approval_artifact_digest_sha256",
        ),
        "old_m1_authorization": (
            "old_m1_authorization_path",
            "old_m1_authorization_file_sha256",
            "authorization_digest_sha256",
            "old_m1_authorization_artifact_digest_sha256",
        ),
        "article": (
            "generated_article_path",
            "generated_article_file_sha256",
            "article_content_digest_sha256",
            "generated_article_artifact_digest_sha256",
        ),
        "plan": (
            "store_link_plan_path",
            "store_link_plan_file_sha256",
            "store_link_finalization_plan_digest_sha256",
            "store_link_plan_artifact_digest_sha256",
        ),
    }

    values: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}

    for label, (
        path_field,
        hash_field,
        digest_field,
        digest_reference_field,
    ) in json_specs.items():
        path = resolve(
            bindings[path_field]
        )

        require(
            path.exists(),
            f"source missing: {label}",
        )
        require(
            file_sha256(path)
            == bindings[hash_field],
            f"source file hash mismatch: {label}",
        )

        value = load(path)

        verify_self_digest(
            value,
            digest_field,
            bindings[digest_reference_field],
            label,
        )

        values[label] = value
        paths[label] = path

    old_result_path = resolve(
        bindings["old_m2_result_path"]
    )

    require(
        old_result_path.exists(),
        "old M2 result missing",
    )
    require(
        file_sha256(old_result_path)
        == bindings[
            "old_m2_result_file_sha256"
        ],
        "old M2 result hash mismatch",
    )

    old_m2_result = load(
        old_result_path
    )

    paths["old_m2_result"] = (
        old_result_path
    )

    runner_path = resolve(
        bindings["remediated_runner_path"]
    )

    require(
        runner_path.exists(),
        "remediated runner missing",
    )
    require(
        file_sha256(runner_path)
        == bindings[
            "remediated_runner_file_sha256"
        ],
        "remediated runner hash mismatch",
    )
    require(
        file_sha256(runner_path)
        == policy["parser_binding"][
            "required_runner_sha256"
        ],
        "runner not bound to policy",
    )

    paths["runner"] = runner_path

    require(
        values["fix_result"]["status"]
        == (
            "PASS_DMM_RECHECK_PARSER_NULL_SAFE_"
            "REMEDIATION_NO_NETWORK_NO_NEW_AUTHORIZATION"
        ),
        "M2 Fix1 status mismatch",
    )
    require(
        old_m2_result[
            "authorization_consumed"
        ]
        is True,
        "old authorization not consumed",
    )
    require(
        old_m2_result[
            "authorization_reuse_allowed"
        ]
        is False,
        "old authorization reuse not blocked",
    )
    require(
        values["old_consumption"][
            "consumption_is_authoritative"
        ]
        is True,
        "old consumption not authoritative",
    )
    require(
        values["old_consumption"][
            "authorization_reuse_allowed"
        ]
        is False,
        "old consumption allows reuse",
    )
    require(
        values["old_recheck"]["network"][
            "response_body_sha256"
        ]
        == bindings[
            "historical_response_body_sha256"
        ],
        "historical response SHA mismatch",
    )

    approval = load(
        resolve(request["approval_path"])
    )
    comparable = copy.deepcopy(approval)
    stored = comparable.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
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
            "FRESH_DMM_RECHECK_AFTER_PARSER_"
            "REMEDIATION_AUTHORIZATION_APPROVED"
        ),
        "approval label mismatch",
    )
    require(
        approval["human_explicit_approval"]
        is True,
        "explicit human approval missing",
    )

    return (
        approval,
        paths,
        [
            "request_scope_verified",
            "source_file_hashes_verified",
            "source_artifact_digests_verified",
            "m2_fix1_result_verified",
            "remediated_runner_hash_verified",
            "old_m2_failure_evidence_verified",
            "old_authorization_consumed_verified",
            "old_authorization_reuse_blocked",
            "historical_response_sha_verified",
            "generated_article_preserved",
            "store_link_plan_preserved",
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
            and digest(without_digest) == stored,
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

    write_json(
        AUTHORIZATION,
        authorization,
    )

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

        hashes_before = {
            label: file_sha256(path)
            for label, path
            in source_paths.items()
        }

        require(
            not PLANNED_RECHECK_RESULT.exists(),
            "post-fix recheck result already exists",
        )
        require(
            not PLANNED_CONSUMPTION.exists(),
            "post-fix consumption already exists",
        )

        stable_authorization = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_POST_PARSER_REMEDIATION_"
                "ONE_SHOT_READ_ONLY_RECHECK_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M3"
            ),
            "authorization_id": (
                "DMM_LATEST_ALIAS_861056_POST_PARSER_"
                "FIX_ONE_SHOT_READ_ONLY_RECHECK_"
                "AUTHORIZATION_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "dmm_series_id": "861056",
            "authorized_next_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M4"
            ),
            "authorized_operation": (
                "ONE_SHOT_READ_ONLY_GET_DMM_LATEST_"
                "ALIAS_RECHECK_WITH_REMEDIATED_PARSER"
            ),
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "old_authorization_reuse_allowed": False,
            "parser_binding": {
                "runner_path": request[
                    "source_bindings"
                ]["remediated_runner_path"],
                "runner_file_sha256": request[
                    "source_bindings"
                ]["remediated_runner_file_sha256"],
                "fix_result_path": request[
                    "source_bindings"
                ]["m2_fix1_result_path"],
                "fix_evidence_digest_sha256": request[
                    "source_bindings"
                ]["m2_fix1_artifact_digest_sha256"],
                "null_safe_meta_fallback_verified": True,
                "runner_change_after_authorization_allowed": False
            },
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
                "proxy_environment_use_allowed": False,
                "automatic_retry_allowed": False,
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
            "identity_requirements": {
                "expected_work_title": (
                    "ダークギャザリング"
                ),
                "expected_volume_label": "第20巻",
                "expected_volume_number": 20,
                "expected_author_name": "近藤憲一",
                "expected_publisher_name": "集英社",
                "expected_series_id": "861056",
                "all_required_identity_fields_must_match": True,
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
                "recheck_result_path": request[
                    "planned_recheck_result_path"
                ],
                "consumption_evidence_path": request[
                    "planned_consumption_evidence_path"
                ]
            },
            "historical_failure_lineage": {
                "old_m1_authorization_path": request[
                    "source_bindings"
                ]["old_m1_authorization_path"],
                "old_m2_recheck_result_path": request[
                    "source_bindings"
                ]["old_m2_recheck_result_path"],
                "old_m2_consumption_path": request[
                    "source_bindings"
                ]["old_m2_consumption_path"],
                "old_response_body_sha256": request[
                    "source_bindings"
                ]["historical_response_body_sha256"],
                "historical_artifacts_modification_allowed": False
            },
            "failure_actions": {
                "communication_failure": (
                    "HIDE_DMM_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                ),
                "identity_mismatch": (
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
                "POST_REMEDIATION_DMM_RECHECK_"
                "AUTHORIZATION_RECORDED_UNCONSUMED"
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
                == hashes_before[label],
                f"source artifact modified: {label}",
            )

        require(
            not PLANNED_RECHECK_RESULT.exists(),
            "recheck result unexpectedly created",
        )
        require(
            not PLANNED_CONSUMPTION.exists(),
            "consumption unexpectedly created",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M3"
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
            "old_authorization_reused": False,
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
            "post_fix_dmm_recheck_authorization_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M3"
            ),
            "status": (
                "PASS_DMM_RECHECK_POST_REMEDIATION_"
                "ONE_SHOT_AUTHORIZATION_FIXED_NO_NETWORK"
            ),
            "decision": (
                "NEW_DMM_RECHECK_AUTHORIZATION_RECORDED_"
                "AWAITING_EXPLICIT_EXECUTE_NOW_CONFIRMATION"
            ),
            "approval_label": (
                "FRESH_DMM_RECHECK_AFTER_PARSER_"
                "REMEDIATION_AUTHORIZATION_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "dmm_series_id": "861056",
            "target_url": (
                "https://book.dmm.com/product/"
                "861056/latest/"
            ),
            "authorization_id": authorization[
                "authorization_id"
            ],
            "authorization_path": package[
                "authorization_path"
            ],
            "authorization_file_sha256": package[
                "authorization_file_sha256"
            ],
            "authorization_digest_sha256": package[
                "authorization_digest_sha256"
            ],
            "post_fix_dmm_recheck_authorization_package_digest_sha256": (
                package[
                    "post_fix_dmm_recheck_authorization_package_digest_sha256"
                ]
            ),
            "authorization_created_in_this_run": (
                created
            ),
            "single_use": True,
            "allowed_method": "GET",
            "remediated_parser_bound": True,
            "remediated_runner_file_sha256": (
                authorization[
                    "parser_binding"
                ]["runner_file_sha256"]
            ),
            "authentication_allowed": False,
            "cookie_send_allowed": False,
            "cookie_persistence_allowed": False,
            "login_allowed": False,
            "automatic_retry_allowed": False,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "old_authorization_reused": False,
            "old_authorization_reuse_allowed": False,
            "redirect_contract_fixed": True,
            "identity_verification_contract_fixed": True,
            "canonical_resolution_contract_fixed": True,
            "failure_and_hide_contract_fixed": True,
            "historical_m2_evidence_preserved": True,
            "historical_response_body_sha256_preserved": True,
            "actual_network_recheck_performed": False,
            "recheck_result_created": False,
            "new_consumption_evidence_created": False,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "source_artifacts_modified": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "POST_REMEDIATION_DMM_RECHECK_"
                "AUTHORIZATION_RECORDED_UNCONSUMED_"
                "AWAITING_EXECUTE_NOW_CONFIRMATION"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m4": True,
            "ready_for_post_fix_dmm_recheck_execute_now_confirmation": True,
            "ready_for_actual_dmm_recheck": False,
            "ready_for_final_affiliate_link_generation": False,
            "ready_for_article_url_injection": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "new_authorization_artifact_verified",
                    "new_authorization_digest_verified",
                    "new_authorization_unconsumed",
                    "old_authorization_not_reused",
                    "new_recheck_result_absent",
                    "new_consumption_evidence_absent",
                    "historical_evidence_preserved",
                    "source_artifacts_preserved",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "production_gate_closed",
                ]
            ),
        }

        write_json(PACKAGE, package)
        write_json(RESULT, result)

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M3

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Target: `{result["target_url"]}`
- Method: `GET`
- New authorization ID: `{result["authorization_id"]}`

## Parser Binding

- Remediated parser bound: `true`
- Runner SHA-256: `{result["remediated_runner_file_sha256"]}`
- M2-FIX1 evidence bound: `true`

## Authorization State

- Single use: `true`
- Consumed: `false`
- Reuse allowed: `false`
- Old authorization reused: `false`
- Automatic retry allowed: `false`

## Historical Preservation

- Old M1 authorization modified: `false`
- Old M2 result modified: `false`
- Old M2 recheck result modified: `false`
- Old M2 consumption modified: `false`
- Historical response SHA-256 modified: `false`

## Current Boundary

- Network recheck performed: `false`
- Recheck result created: `false`
- Consumption evidence created: `false`
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-M3"
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

        write_json(RESULT, failure)

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
