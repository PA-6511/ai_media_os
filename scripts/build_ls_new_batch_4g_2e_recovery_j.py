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


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "offline_content_generation_approval_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "offline_content_generation_approval_request.example.json"
)
AUTHORIZATION_PATH = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_authorization.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "offline_content_generation_approval_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_j_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_j_"
    "offline_content_generation_approval_report.md"
)
RESERVED_OUTPUT_PATH = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
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
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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
            f"JSON root must be object: {path}"
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


def resolve_repo_path(value: str) -> Path:
    path = Path(value)

    return (
        path
        if path.is_absolute()
        else ROOT / path
    )


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(
            resolved.relative_to(
                ROOT.resolve()
            )
        )
    except ValueError:
        return str(resolved)


def source_semantic_state(
    source: dict[str, Any],
) -> dict[str, Any]:
    fields = [
        "phase_id",
        "status",
        "decision",
        "approval_label",
        "content_generation_contract_id",
        "content_generation_contract_digest_sha256",
        "content_item_id",
        "work_title",
        "volume_label",
        "article_title",
        "template_contract_id",
        "wordpress_status",
        "advertising_disclosure_required",
        "fabricated_information_allowed",
        "fabricated_synopsis_allowed",
        "fabricated_discount_allowed",
        "fabricated_point_return_allowed",
        "source_retention_required",
        "dmm_latest_alias_recheck_requirement_inherited",
        "dmm_latest_alias_recheck_completed",
        "dmm_url_rendering_before_recheck_allowed",
        "reserved_content_output_path",
        "content_output_exists",
        "article_content_generated",
        "fresh_payload_created",
        "fresh_payload_read",
        "fresh_payload_copied",
        "payload_binding_complete",
        "payload_modified",
        "production_category_id_payload_injected",
        "credential_file_read",
        "network_connection_performed",
        "http_request_performed",
        "wordpress_access_performed",
        "wordpress_write_performed",
        "wordpress_draft_created",
        "execution_allowed",
        "production_status",
        "ready_for_ls_new_batch_4g_2e_recovery_j",
        "ready_for_offline_article_content_generation_approval"
    ]

    return {
        field: source.get(field)
        for field in fields
    }


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-J",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_OFFLINE_CONTENT_GENERATION_"
            "AUTHORIZATION_RECORDING_ONLY"
        ),
        "operation mode mismatch",
    )

    authorization = policy[
        "authorization_contract"
    ]

    require(
        authorization[
            "authorized_next_phase_id"
        ]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "authorized next phase mismatch",
    )
    require(
        authorization["single_use"] is True,
        "authorization must be single use",
    )
    require(
        authorization["authorization_consumed"]
        is False,
        "authorization must be unconsumed",
    )
    require(
        authorization["authorization_reuse_allowed"]
        is False,
        "authorization reuse must be forbidden",
    )
    require(
        authorization["content_output_overwrite_allowed"]
        is False,
        "content output overwrite must be forbidden",
    )

    conditions = policy[
        "next_phase_generation_conditions"
    ]

    require(
        conditions[
            "template_artifact_resolution_required_before_generation"
        ]
        is True,
        "template resolution requirement missing",
    )
    require(
        conditions["template_artifact_resolved"]
        is False,
        "template must remain unresolved in J",
    )
    require(
        conditions[
            "clear_advertising_disclosure_required"
        ]
        is True,
        "advertising disclosure missing",
    )
    require(
        conditions["verified_source_only"]
        is True,
        "verified-source-only requirement missing",
    )

    for field in [
        "fabricated_information_allowed",
        "fabricated_synopsis_allowed",
        "fabricated_story_detail_allowed",
        "fabricated_discount_allowed",
        "fabricated_point_return_allowed",
        "registered_store_links_are_final_affiliate_links",
        "final_affiliate_link_generation_allowed",
        "categories_field_allowed",
        "category_id_10_injection_allowed",
    ]:
        require(
            conditions[field] is False,
            f"{field} must remain false",
        )

    dmm = policy[
        "dmm_recheck_contract"
    ]

    require(
        dmm[
            "latest_alias_recheck_requirement_inherited"
        ]
        is True,
        "DMM requirement inheritance missing",
    )
    require(
        dmm["latest_alias_recheck_completed"]
        is False,
        "DMM recheck must remain incomplete",
    )
    require(
        dmm[
            "dmm_url_rendering_before_recheck_allowed"
        ]
        is False,
        "DMM rendering must remain blocked",
    )

    boundary = policy[
        "execution_boundary"
    ]

    require(
        boundary["authorization_recording_allowed"]
        is True,
        "authorization recording must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "authorization_recording_allowed",
            "production_status",
            "safety_state",
        }:
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    require(
        boundary["production_status"] == "NO_GO",
        "production status must remain NO_GO",
    )

    return [
        "policy_phase_verified",
        "operation_mode_verified",
        "single_use_authorization_required",
        "authorization_unconsumed",
        "authorization_reuse_forbidden",
        "next_phase_k_fixed",
        "template_resolution_required",
        "template_not_resolved_in_current_phase",
        "advertising_disclosure_required",
        "fabrication_prohibitions_verified",
        "final_affiliate_link_generation_blocked",
        "category_injection_blocked",
        "dmm_recheck_requirement_inherited",
        "dmm_rendering_blocked",
        "current_phase_execution_boundary_closed",
    ]


def validate_request_and_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-J",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    true_fields = [
        "authorization_recording_requested",
        "single_use_authorization_requested",
        "next_phase_offline_content_generation_authorized",
        "template_contract_inheritance_requested",
        "template_artifact_resolution_requirement_requested",
        "advertising_disclosure_requirement_requested",
        "verified_source_only_requirement_requested",
        "fabrication_prohibition_requested",
        "source_retention_requirement_requested",
        "dmm_recheck_requirement_inheritance_requested",
    ]

    for field in true_fields:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    false_fields = [
        "dmm_recheck_execution_requested",
        "article_content_generation_requested",
        "content_output_creation_requested",
        "final_affiliate_link_generation_requested",
        "fresh_payload_creation_requested",
        "fresh_payload_read_requested",
        "fresh_payload_copy_requested",
        "payload_binding_requested",
        "payload_modification_requested",
        "production_category_id_payload_injection_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_draft_creation_requested",
        "execution_requested",
    ]

    for field in false_fields:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    source_result = load_json(
        resolve_repo_path(
            request["source_result_path"]
        )
    )
    source_contract_path = resolve_repo_path(
        request["source_contract_path"]
    )
    source_contract = load_json(
        source_contract_path
    )
    approval = load_json(
        resolve_repo_path(
            request[
                "offline_generation_approval_path"
            ]
        )
    )

    require(
        digest(source_semantic_state(source_result))
        == request[
            "source_result_semantic_digest_sha256"
        ],
        "source result semantic digest mismatch",
    )
    require(
        source_result.get("status")
        == (
            "PASS_FRESH_ARTICLE_CONTENT_GENERATION_"
            "CONTRACT_FIXED_NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
        ),
        "source status mismatch",
    )
    require(
        source_result.get("content_output_exists")
        is False,
        "source content output already exists",
    )
    require(
        source_result.get("article_content_generated")
        is False,
        "source content already generated",
    )
    require(
        source_result.get("fresh_payload_created")
        is False,
        "source payload already created",
    )
    require(
        source_result.get(
            "production_category_id_payload_injected"
        )
        is False,
        "source category already injected",
    )
    require(
        source_result.get("wordpress_write_performed")
        is False,
        "source WordPress write detected",
    )
    require(
        source_result.get("execution_allowed")
        is False,
        "source execution unexpectedly allowed",
    )

    require(
        file_sha256(source_contract_path)
        == request["source_contract_file_sha256"],
        "source contract file changed",
    )

    contract_without_digest = copy.deepcopy(
        source_contract
    )
    stored_contract_digest = contract_without_digest.pop(
        "content_generation_contract_digest_sha256",
        None,
    )

    require(
        isinstance(stored_contract_digest, str)
        and digest(contract_without_digest)
        == stored_contract_digest,
        "source contract digest invalid",
    )
    require(
        stored_contract_digest
        == request[
            "source_contract_artifact_digest_sha256"
        ],
        "source contract digest reference mismatch",
    )
    require(
        source_contract.get("article_content_generated")
        is False,
        "source contract content state mismatch",
    )
    require(
        source_contract.get("content_output_created")
        is False,
        "source contract output state mismatch",
    )

    approval_without_digest = copy.deepcopy(
        approval
    )
    stored_approval_digest = (
        approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_approval_digest, str)
        and digest(approval_without_digest)
        == stored_approval_digest,
        "offline generation approval digest invalid",
    )
    require(
        digest(approval)
        == request[
            "offline_generation_approval_digest_sha256"
        ],
        "offline generation approval file digest mismatch",
    )
    require(
        approval.get("approval_label")
        == (
            "FRESH_ARTICLE_OFFLINE_"
            "CONTENT_GENERATION_APPROVED"
        ),
        "offline generation approval label mismatch",
    )
    require(
        approval.get("human_explicit_approval")
        is True,
        "human approval missing",
    )
    require(
        approval["authorization_scope"][
            "authorized_next_phase_id"
        ]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "approval next phase mismatch",
    )
    require(
        approval["authorization_scope"]["single_use"]
        is True,
        "approval must be single use",
    )
    require(
        approval["authorization_scope"][
            "authorization_consumed"
        ]
        is False,
        "approval already consumed",
    )
    require(
        approval.get("execution_allowed")
        is False,
        "approval must not authorize J execution",
    )

    require(
        not resolve_repo_path(
            request["reserved_content_output_path"]
        ).exists(),
        "reserved content output already exists",
    )

    for path_field, hash_field in [
        (
            "source_input_path",
            "source_input_file_sha256",
        ),
        (
            "source_review_path",
            "source_review_file_sha256",
        ),
    ]:
        path = resolve_repo_path(
            request[path_field]
        )

        require(
            file_sha256(path)
            == request[hash_field],
            f"{path_field} changed",
        )

    return (
        source_result,
        source_contract,
        approval,
        [
            "request_identity_verified",
            "authorization_recording_requested",
            "single_use_authorization_requested",
            "next_phase_generation_authorized",
            "template_inheritance_requested",
            "template_resolution_requirement_requested",
            "advertising_disclosure_requested",
            "verified_source_only_requested",
            "fabrication_prohibition_requested",
            "source_retention_requested",
            "dmm_requirement_inheritance_requested",
            "source_result_semantic_digest_verified",
            "source_result_safe_state_verified",
            "source_contract_file_verified",
            "source_contract_digest_verified",
            "offline_generation_approval_verified",
            "source_input_file_preserved",
            "source_review_file_preserved",
            "reserved_content_output_absent",
            "content_generation_not_requested_in_j",
            "content_output_not_requested_in_j",
            "payload_generation_not_requested",
            "category_injection_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
            "execution_not_requested",
        ],
    )


def ensure_authorization(
    stable: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if AUTHORIZATION_PATH.exists():
        existing = load_json(
            AUTHORIZATION_PATH
        )
        comparable = copy.deepcopy(
            existing
        )
        stored_digest = comparable.pop(
            "authorization_digest_sha256",
            None,
        )
        created_at = comparable.pop(
            "authorized_at_utc",
            None,
        )

        require(
            isinstance(created_at, str)
            and created_at != "",
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
            isinstance(stored_digest, str)
            and digest(without_digest)
            == stored_digest,
            "existing authorization digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(
        stable
    )
    without_digest[
        "authorized_at_utc"
    ] = utc_now()

    authorization = copy.deepcopy(
        without_digest
    )
    authorization[
        "authorization_digest_sha256"
    ] = digest(without_digest)

    write_json(
        AUTHORIZATION_PATH,
        authorization,
    )

    return authorization, True


def main() -> int:
    try:
        policy = load_json(
            POLICY_PATH
        )
        request = load_json(
            REQUEST_PATH
        )

        policy_checks = validate_policy(
            policy
        )

        (
            source_result,
            source_contract,
            approval,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        require(
            not RESERVED_OUTPUT_PATH.exists(),
            "reserved content output exists before authorization",
        )

        stable_authorization = {
            "schema_version": "1.0.0",
            "document_role": (
                "ONE_SHOT_OFFLINE_ARTICLE_CONTENT_"
                "GENERATION_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-J"
            ),
            "authorization_id": (
                "DARK_GATHERING_VOLUME_20_"
                "OFFLINE_CONTENT_GENERATION_AUTHORIZATION_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "authorized_next_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "authorized_operation": (
                "CREATE_ONE_OFFLINE_ARTICLE_CONTENT_DRAFT"
            ),
            "reserved_content_output_path": (
                "exchange/content/new_release/fresh/"
                "new-release-comic-20260703-001.article.json"
            ),
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "template_artifact_resolution_required": True,
            "template_artifact_resolved": False,
            "single_use": True,
            "authorization_consumed": False,
            "consumption_evidence_required": True,
            "consumption_evidence_path": (
                "exchange/authorizations/new_release/fresh/"
                "new-release-comic-20260703-001."
                "offline_content_generation_consumption.json"
            ),
            "authorization_reuse_allowed": False,
            "different_article_use_allowed": False,
            "different_output_path_use_allowed": False,
            "source_artifact_overwrite_allowed": False,
            "content_output_overwrite_allowed": False,
            "advertising_disclosure": {
                "required": True,
                "allowed_labels": [
                    "PR",
                    "広告"
                ],
                "must_appear_before_store_navigation": True
            },
            "factuality_rules": {
                "verified_source_only": True,
                "fabricated_information_allowed": False,
                "fabricated_synopsis_allowed": False,
                "fabricated_story_detail_allowed": False,
                "fabricated_discount_allowed": False,
                "fabricated_point_return_allowed": False
            },
            "source_retention_required": True,
            "registered_store_links_are_final_affiliate_links": False,
            "final_affiliate_link_generation_allowed": False,
            "dmm_recheck": {
                "requirement_inherited": True,
                "completed": False,
                "url_rendering_allowed": False,
                "final_link_use_allowed": False,
                "required_before_payload_generation": True
            },
            "categories_field_allowed": False,
            "production_category_id_payload_injection_allowed": False,
            "source_lineage": {
                "content_generation_contract_path": (
                    request["source_contract_path"]
                ),
                "content_generation_contract_digest_sha256": (
                    request[
                        "source_contract_artifact_digest_sha256"
                    ]
                ),
                "offline_generation_approval_digest_sha256": (
                    approval[
                        "approval_evidence_digest_sha256"
                    ]
                ),
                "article_input_path": (
                    request["source_input_path"]
                ),
                "article_input_digest_sha256": (
                    request[
                        "source_input_artifact_digest_sha256"
                    ]
                ),
                "human_review_path": (
                    request["source_review_path"]
                ),
                "human_review_digest_sha256": (
                    request[
                        "source_review_artifact_digest_sha256"
                    ]
                )
            },
            "current_phase_article_content_generated": False,
            "current_phase_content_output_created": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "current_phase_execution_allowed": False,
            "next_phase_generation_authorized": True,
            "production_status": "NO_GO",
            "safety_state": (
                "ONE_SHOT_OFFLINE_CONTENT_GENERATION_"
                "AUTHORIZED_FOR_RECOVERY_K_ONLY"
            )
        }

        authorization, created = (
            ensure_authorization(
                stable_authorization
            )
        )

        require(
            not RESERVED_OUTPUT_PATH.exists(),
            "content output created during approval phase",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-J"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "authorization_artifact_path": (
                display_path(AUTHORIZATION_PATH)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "authorization_created_in_this_run": (
                created
            ),
            "authorized_next_phase_id": (
                authorization[
                    "authorized_next_phase_id"
                ]
            ),
            "authorized_operation": (
                authorization[
                    "authorized_operation"
                ]
            ),
            "single_use": True,
            "authorization_consumed": False,
            "template_artifact_resolution_required": True,
            "template_artifact_resolved": False,
            "reserved_content_output_path": (
                display_path(RESERVED_OUTPUT_PATH)
            ),
            "content_output_exists": False,
            "current_phase_article_content_generated": False,
            "next_phase_generation_authorized": True,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "verified_checks": (
                policy_checks
                + source_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "offline_generation_approval_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-J"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_OFFLINE_CONTENT_"
                "GENERATION_AUTHORIZATION_RECORDED_"
                "NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "ONE_SHOT_OFFLINE_CONTENT_GENERATION_"
                "AUTHORIZED_FOR_RECOVERY_K_ONLY"
            ),
            "approval_label": (
                "FRESH_ARTICLE_OFFLINE_"
                "CONTENT_GENERATION_APPROVED"
            ),
            "authorization_artifact_path": (
                package[
                    "authorization_artifact_path"
                ]
            ),
            "authorization_digest_sha256": (
                package[
                    "authorization_digest_sha256"
                ]
            ),
            "offline_generation_approval_package_digest_sha256": (
                package[
                    "offline_generation_approval_package_digest_sha256"
                ]
            ),
            "authorization_created_in_this_run": (
                created
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "authorized_next_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "authorized_operation": (
                "CREATE_ONE_OFFLINE_ARTICLE_CONTENT_DRAFT"
            ),
            "single_use_authorization": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "template_artifact_resolution_required": True,
            "template_artifact_resolved": False,
            "advertising_disclosure_required": True,
            "verified_source_only": True,
            "fabricated_information_allowed": False,
            "fabricated_synopsis_allowed": False,
            "fabricated_story_detail_allowed": False,
            "fabricated_discount_allowed": False,
            "fabricated_point_return_allowed": False,
            "source_retention_required": True,
            "registered_store_links_are_final_affiliate_links": False,
            "final_affiliate_link_generation_allowed": False,
            "dmm_latest_alias_recheck_requirement_inherited": True,
            "dmm_latest_alias_recheck_completed": False,
            "dmm_url_rendering_before_recheck_allowed": False,
            "reserved_content_output_path": (
                package[
                    "reserved_content_output_path"
                ]
            ),
            "content_output_exists": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "fresh_payload_read": False,
            "fresh_payload_copied": False,
            "payload_binding_complete": False,
            "payload_modified": False,
            "production_category_id_payload_injected": False,
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "current_phase_execution_allowed": False,
            "next_phase_generation_authorized": True,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ONE_SHOT_OFFLINE_CONTENT_GENERATION_"
                "AUTHORIZED_FOR_RECOVERY_K_ONLY"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_k": True,
            "ready_for_template_artifact_resolution": True,
            "ready_for_one_shot_offline_article_content_generation": True,
            "ready_for_fresh_payload_generation": False,
            "ready_for_offline_payload_binding": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "authorization_artifact_verified",
                    "authorization_digest_verified",
                    "single_use_authorization_recorded",
                    "authorization_unconsumed",
                    "authorization_reuse_blocked",
                    "next_phase_k_only",
                    "template_resolution_still_required",
                    "reserved_content_output_absent",
                    "current_phase_content_not_generated",
                    "fresh_payload_not_created",
                    "category_id_not_injected",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "current_phase_execution_gate_closed",
                ]
            ),
        }

        write_json(
            PACKAGE_PATH,
            package,
        )
        write_json(
            RESULT_PATH,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-J Offline Content Generation Approval

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Work: `{result["work_title"]}`
- Volume: `{result["volume_label"]}`

## Authorization

- Authorized next phase: `{result["authorized_next_phase_id"]}`
- Authorized operation: `{result["authorized_operation"]}`
- Single use: `true`
- Authorization consumed: `false`
- Authorization reuse allowed: `false`
- Template resolution required: `true`
- Template resolved: `false`

## Generation Conditions

- Advertising disclosure required: `true`
- Verified sources only: `true`
- Fabricated information allowed: `false`
- Final affiliate-link generation allowed: `false`
- DMM recheck completed: `false`
- DMM URL rendering allowed: `false`

## Current Phase Boundary

- Content output exists: `false`
- Article content generated: `false`
- Fresh payload created: `false`
- Category ID injected: `false`
- Network connection performed: `false`
- WordPress write performed: `false`
- Current phase execution allowed: `false`
"""

        write_text(
            REPORT_PATH,
            report,
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
        failure = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-J"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "offline_content_generation_authorization_recorded": False,
            "article_content_generated": False,
            "content_output_created": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO"
        }

        write_json(
            RESULT_PATH,
            failure,
        )

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
