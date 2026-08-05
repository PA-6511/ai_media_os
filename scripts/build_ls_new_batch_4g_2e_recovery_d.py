#!/usr/bin/env python3

from __future__ import annotations

import argparse
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
    "new_release_wp_production_category_"
    "mapping_fixation_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_"
    "mapping_fixation_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_"
    "mapping_fixation_package.example.json"
)
MAPPING_PATH = (
    ROOT
    / "config/"
    "new_release_wp_production_category_mapping.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_d_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_d_"
    "mapping_fixation_report.md"
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-D",
        "policy phase mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == (
            "NEW_RELEASE_WP_PRODUCTION_CATEGORY_"
            "MAPPING_FIXATION_POLICY_V1"
        ),
        "policy identity mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == (
            "APPROVED_PRODUCTION_CATEGORY_"
            "MAPPING_FIXATION_ONLY"
        ),
        "operation mode mismatch",
    )
    checks.append("mapping_fixation_mode")

    approval = policy[
        "mapping_fixation_approval_contract"
    ]

    require(
        approval["required_approval_label"]
        == (
            "PRODUCTION_CATEGORY_MAPPING_"
            "FIXATION_APPROVED"
        ),
        "approval label mismatch",
    )
    require(
        approval["approved_category_id"] == 10,
        "approved category ID mismatch",
    )
    require(
        approval["approved_category_name"]
        == "最新巻",
        "approved category name mismatch",
    )
    require(
        approval["human_explicit_approval_required"]
        is True,
        "human approval must be required",
    )
    require(
        approval["execution_authorization_included"]
        is False,
        "execution authorization must not be included",
    )
    checks.append("mapping_fixation_approval_contract")

    mapping = policy["mapping_contract"]

    require(
        mapping["mapping_id"]
        == (
            "COMIC_NEW_RELEASE_LATEST_VOLUME_"
            "TO_WP_CATEGORY_10"
        ),
        "mapping identity mismatch",
    )
    require(
        mapping["production_category_id"] == 10,
        "mapping category ID mismatch",
    )
    require(
        mapping["production_category_name"]
        == "最新巻",
        "mapping category name mismatch",
    )
    require(
        mapping["mapping_fixed"] is True,
        "mapping must be fixed",
    )
    require(
        mapping["automatic_mapping_performed"]
        is False,
        "automatic mapping must remain false",
    )
    require(
        mapping[
            "mapping_change_allowed_without_new_approval"
        ]
        is False,
        "unapproved mapping changes must be forbidden",
    )
    require(
        mapping["payload_binding_allowed_in_current_phase"]
        is False,
        "payload binding must remain forbidden",
    )
    require(
        mapping[
            "production_category_id_payload_injection_allowed"
        ]
        is False,
        "payload injection must remain forbidden",
    )
    require(
        mapping["wordpress_write_allowed"]
        is False,
        "WordPress write must remain forbidden",
    )
    checks.append("production_mapping_contract")

    for field, value in policy[
        "current_phase_access"
    ].items():
        require(
            value is False,
            f"{field} must remain false",
        )

    checks.append("current_phase_no_external_access")

    execution = policy[
        "execution_boundary"
    ]

    for field in [
        "credential_value_output_allowed",
        "environment_variable_export_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "tls_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_creation_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "production_payload_modification_allowed",
        "production_category_id_payload_injection_allowed",
        "wordpress_draft_preparation_allowed",
        "wordpress_draft_creation_allowed",
        "execution_allowed",
    ]:
        require(
            execution[field] is False,
            f"{field} must remain false",
        )

    require(
        execution["production_status"]
        == "NO_GO",
        "production status must remain NO_GO",
    )
    checks.append("execution_boundary")

    return checks


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-D",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    mapping = request.get("mapping")

    require(
        isinstance(mapping, dict),
        "mapping request missing",
    )
    require(
        mapping.get("mapping_id")
        == policy["mapping_contract"][
            "mapping_id"
        ],
        "request mapping identity mismatch",
    )
    require(
        mapping.get("article_scope_id")
        == policy["mapping_contract"][
            "article_scope_id"
        ],
        "request article scope mismatch",
    )
    require(
        mapping.get("production_category_id")
        == 10,
        "request category ID mismatch",
    )
    require(
        mapping.get("production_category_name")
        == "最新巻",
        "request category name mismatch",
    )
    require(
        request.get("mapping_fixation_requested")
        is True,
        "mapping fixation must be requested",
    )

    for field in [
        "automatic_category_selection_requested",
        "automatic_category_mapping_requested",
        "mapping_change_without_new_approval_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "wordpress_category_creation_requested",
        "wordpress_write_requested",
        "production_payload_modification_requested",
        "wordpress_draft_creation_requested",
        "execution_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )


def validate_source_and_approval(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    source_result = load_json(
        resolve_repo_path(
            request["source_result_path"]
        )
    )
    source_package = load_json(
        resolve_repo_path(
            request["source_package_path"]
        )
    )
    source_approval = load_json(
        resolve_repo_path(
            request["source_approval_path"]
        )
    )
    mapping_approval = load_json(
        resolve_repo_path(
            request[
                "mapping_fixation_approval_path"
            ]
        )
    )

    require(
        digest(source_result)
        == request[
            "source_result_digest_sha256"
        ],
        "source result digest mismatch",
    )
    require(
        digest(source_package)
        == request[
            "source_package_digest_sha256"
        ],
        "source package file digest mismatch",
    )
    require(
        digest(source_approval)
        == request[
            "source_approval_digest_sha256"
        ],
        "source approval file digest mismatch",
    )
    require(
        digest(mapping_approval)
        == request[
            "mapping_fixation_approval_digest_sha256"
        ],
        "mapping approval file digest mismatch",
    )

    source_contract = policy[
        "source_contract"
    ]

    require(
        source_result.get("phase_id")
        == policy["source_phase_id"],
        "source phase mismatch",
    )
    require(
        source_result.get("status")
        == source_contract[
            "required_source_status"
        ],
        "source status mismatch",
    )
    require(
        source_result.get("decision")
        == source_contract[
            "required_source_decision"
        ],
        "source decision mismatch",
    )
    require(
        source_result.get("approval_label")
        == source_contract[
            "required_human_review_approval_label"
        ],
        "source human-review label mismatch",
    )
    require(
        source_result.get("human_selection_recorded")
        is True,
        "source human selection missing",
    )
    require(
        source_result.get("selected_category_id")
        == 10,
        "source category ID mismatch",
    )
    require(
        source_result.get("selected_category_name")
        == "最新巻",
        "source category name mismatch",
    )
    require(
        source_result.get(
            "selected_category_purpose"
        )
        == "コミック新刊・新巻配信開始記事",
        "source category purpose mismatch",
    )
    require(
        source_result.get("category_mapping_fixed")
        is False,
        "source mapping must remain unfixed",
    )
    require(
        source_result.get(
            "production_category_id_payload_injected"
        )
        is False,
        "source payload injection must be false",
    )
    require(
        source_result.get("http_request_performed")
        is False,
        "source HTTP request must be false",
    )
    require(
        source_result.get("wordpress_write_performed")
        is False,
        "source WordPress write must be false",
    )

    stored_package_digest = source_package.get(
        "human_review_package_digest_sha256"
    )
    package_without_digest = copy.deepcopy(
        source_package
    )
    package_without_digest.pop(
        "human_review_package_digest_sha256",
        None,
    )

    require(
        stored_package_digest
        == source_result[
            "human_review_package_digest_sha256"
        ],
        "source package digest reference mismatch",
    )
    require(
        digest(package_without_digest)
        == stored_package_digest,
        "source package digest invalid",
    )

    decision = source_package.get(
        "human_selection_decision"
    )

    require(
        isinstance(decision, dict),
        "source selection decision missing",
    )

    stored_decision_digest = decision.get(
        "human_selection_decision_digest_sha256"
    )
    decision_without_digest = copy.deepcopy(
        decision
    )
    decision_without_digest.pop(
        "human_selection_decision_digest_sha256",
        None,
    )

    require(
        stored_decision_digest
        == source_result[
            "human_selection_decision_digest_sha256"
        ],
        "source decision digest reference mismatch",
    )
    require(
        digest(decision_without_digest)
        == stored_decision_digest,
        "source selection decision digest invalid",
    )

    source_approval_without_digest = copy.deepcopy(
        source_approval
    )
    source_approval_digest = (
        source_approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(source_approval_digest, str)
        and digest(source_approval_without_digest)
        == source_approval_digest,
        "source human-review approval digest invalid",
    )

    require(
        source_approval.get("approval_label")
        == "CATEGORY_INDEX_HUMAN_REVIEW_APPROVED",
        "source human-review approval label mismatch",
    )
    require(
        source_approval.get("execution_allowed")
        is False,
        "source human-review approval must not execute",
    )

    mapping_approval_without_digest = copy.deepcopy(
        mapping_approval
    )
    mapping_approval_digest = (
        mapping_approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(mapping_approval_digest, str)
        and digest(
            mapping_approval_without_digest
        )
        == mapping_approval_digest,
        "mapping fixation approval digest invalid",
    )
    require(
        mapping_approval.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-D",
        "mapping approval phase mismatch",
    )
    require(
        mapping_approval.get("approval_label")
        == (
            "PRODUCTION_CATEGORY_MAPPING_"
            "FIXATION_APPROVED"
        ),
        "mapping approval label mismatch",
    )
    require(
        mapping_approval.get(
            "human_explicit_approval"
        )
        is True,
        "mapping human approval missing",
    )
    require(
        mapping_approval.get("approved_by")
        == "HUMAN_OPERATOR",
        "mapping approval actor mismatch",
    )
    require(
        mapping_approval.get("execution_allowed")
        is False,
        "mapping approval must not authorize execution",
    )

    approved_mapping = mapping_approval.get(
        "approved_mapping"
    )

    require(
        isinstance(approved_mapping, dict),
        "approved mapping missing",
    )
    require(
        approved_mapping.get("production_category_id")
        == 10,
        "approved mapping category ID mismatch",
    )
    require(
        approved_mapping.get(
            "production_category_name"
        )
        == "最新巻",
        "approved mapping category name mismatch",
    )
    require(
        approved_mapping.get(
            "mapping_fixation_approved"
        )
        is True,
        "mapping fixation approval flag missing",
    )
    require(
        approved_mapping.get(
            "automatic_mapping_performed"
        )
        is False,
        "automatic mapping must be false",
    )
    require(
        approved_mapping.get(
            "payload_binding_approved"
        )
        is False,
        "payload binding must remain unapproved",
    )
    require(
        approved_mapping.get(
            "payload_injection_allowed"
        )
        is False,
        "payload injection must remain forbidden",
    )
    require(
        approved_mapping.get(
            "wordpress_write_allowed"
        )
        is False,
        "WordPress write must remain forbidden",
    )

    require(
        approved_mapping.get(
            "source_category_digest_sha256"
        )
        == source_result[
            "source_category_digest_sha256"
        ],
        "approved source category digest mismatch",
    )

    return (
        source_result,
        source_package,
        source_approval,
        mapping_approval,
        [
            "source_result_digest_verified",
            "source_package_file_digest_verified",
            "source_approval_file_digest_verified",
            "mapping_approval_file_digest_verified",
            "source_phase_verified",
            "source_status_verified",
            "source_human_selection_verified",
            "source_category_id_verified",
            "source_category_name_verified",
            "source_category_purpose_verified",
            "source_mapping_unfixed_verified",
            "source_payload_injection_absent",
            "source_http_unperformed",
            "source_wordpress_write_absent",
            "source_package_digest_verified",
            "source_selection_decision_digest_verified",
            "source_human_review_approval_verified",
            "mapping_fixation_human_approval_verified",
            "mapping_fixation_approval_digest_verified",
            "approved_mapping_identity_verified",
            "approved_mapping_category_verified",
            "automatic_mapping_absent",
            "payload_binding_unapproved",
            "payload_injection_forbidden",
            "wordpress_write_forbidden",
        ],
    )


def ensure_mapping_artifact(
    *,
    source_result: dict[str, Any],
    mapping_approval: dict[str, Any],
    mapping_path: Path,
) -> tuple[dict[str, Any], bool]:
    approved_mapping = mapping_approval[
        "approved_mapping"
    ]

    stable_mapping = {
        "schema_version": "1.0.0",
        "mapping_id": (
            "COMIC_NEW_RELEASE_LATEST_VOLUME_"
            "TO_WP_CATEGORY_10"
        ),
        "article_scope_id": (
            "COMIC_NEW_RELEASE_LATEST_VOLUME_"
            "DISTRIBUTION_START"
        ),
        "article_scope_label": (
            "コミック新刊・新巻配信開始記事"
        ),
        "production_category_id": 10,
        "production_category_name": "最新巻",
        "production_category_slug": source_result[
            "selected_category_slug"
        ],
        "mapping_source": (
            "HUMAN_REVIEW_APPROVED_REAL_"
            "WORDPRESS_CATEGORY_INDEX"
        ),
        "source_phase_id": source_result[
            "phase_id"
        ],
        "source_category_digest_sha256": source_result[
            "source_category_digest_sha256"
        ],
        "source_human_selection_decision_digest_sha256": (
            source_result[
                "human_selection_decision_digest_sha256"
            ]
        ),
        "source_human_review_package_digest_sha256": (
            source_result[
                "human_review_package_digest_sha256"
            ]
        ),
        "mapping_fixation_approval_label": (
            mapping_approval["approval_label"]
        ),
        "mapping_fixation_approval_digest_sha256": (
            mapping_approval[
                "approval_evidence_digest_sha256"
            ]
        ),
        "mapping_fixed": True,
        "human_mapping_fixation_approved": True,
        "automatic_category_selection_performed": False,
        "automatic_category_mapping_performed": False,
        "mapping_change_requires_new_human_approval": True,
        "mapping_change_allowed_without_new_approval": False,
        "payload_binding_complete": False,
        "production_category_id_payload_injection_allowed": False,
        "wordpress_write_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CATEGORY_MAPPING_FIXED_"
            "PAYLOAD_NOT_BOUND"
        ),
    }

    require(
        approved_mapping[
            "production_category_slug"
        ]
        == stable_mapping[
            "production_category_slug"
        ],
        "approved mapping slug mismatch",
    )

    if mapping_path.exists():
        existing = load_json(mapping_path)
        existing_without_digest = copy.deepcopy(
            existing
        )
        stored_digest = existing_without_digest.pop(
            "mapping_artifact_digest_sha256",
            None,
        )
        fixed_at = existing_without_digest.pop(
            "mapping_fixed_at_utc",
            None,
        )

        require(
            isinstance(stored_digest, str)
            and len(stored_digest) == 64,
            "existing mapping digest invalid",
        )
        require(
            isinstance(fixed_at, str)
            and fixed_at != "",
            "existing mapping fixation timestamp invalid",
        )

        comparable = copy.deepcopy(
            existing_without_digest
        )

        require(
            comparable == stable_mapping,
            "existing mapping artifact semantic mismatch",
        )

        artifact_without_digest = copy.deepcopy(
            existing
        )
        artifact_without_digest.pop(
            "mapping_artifact_digest_sha256",
            None,
        )

        require(
            digest(artifact_without_digest)
            == stored_digest,
            "existing mapping artifact digest mismatch",
        )

        return existing, False

    artifact_without_digest = copy.deepcopy(
        stable_mapping
    )
    artifact_without_digest[
        "mapping_fixed_at_utc"
    ] = utc_now()

    artifact = copy.deepcopy(
        artifact_without_digest
    )
    artifact[
        "mapping_artifact_digest_sha256"
    ] = digest(artifact_without_digest)

    write_json(
        mapping_path,
        artifact,
    )

    return artifact, True


def build_package(
    *,
    policy: dict[str, Any],
    request: dict[str, Any],
    mapping_artifact: dict[str, Any],
    mapping_created: bool,
    verified_checks: list[str],
) -> dict[str, Any]:
    decision_without_digest = {
        "mapping_id": mapping_artifact[
            "mapping_id"
        ],
        "article_scope_id": mapping_artifact[
            "article_scope_id"
        ],
        "article_scope_label": mapping_artifact[
            "article_scope_label"
        ],
        "production_category_id": mapping_artifact[
            "production_category_id"
        ],
        "production_category_name": mapping_artifact[
            "production_category_name"
        ],
        "production_category_slug": mapping_artifact[
            "production_category_slug"
        ],
        "mapping_fixed": True,
        "mapping_artifact_created_in_this_run": (
            mapping_created
        ),
        "human_mapping_fixation_approved": True,
        "automatic_category_selection_performed": False,
        "automatic_category_mapping_performed": False,
        "mapping_change_requires_new_human_approval": True,
        "payload_binding_complete": False,
        "production_category_id_payload_injected": False,
        "wordpress_write_performed": False,
        "production_payload_modified": False,
        "execution_allowed": False,
    }

    decision = copy.deepcopy(
        decision_without_digest
    )
    decision[
        "mapping_fixation_decision_digest_sha256"
    ] = digest(decision_without_digest)

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-D"
        ),
        "policy_id": policy["policy_id"],
        "mapping_fixation_package_id": (
            "wp-production-category-mapping-"
            "fixation-latest-volume"
        ),
        "operation_mode": policy[
            "operation_mode"
        ],
        "mapping_artifact_path": display_path(
            MAPPING_PATH
        ),
        "mapping_artifact_digest_sha256": (
            mapping_artifact[
                "mapping_artifact_digest_sha256"
            ]
        ),
        "mapping_fixation_decision": decision,
        "current_phase_activity": {
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_response_read": False,
            "wordpress_category_created": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "automatic_category_selection_performed": False,
            "automatic_category_mapping_performed": False,
            "production_payload_modified": False,
            "production_category_id_payload_injected": False,
        },
        "verified_checks": verified_checks,
    }

    package = copy.deepcopy(
        package_without_digest
    )
    package[
        "mapping_fixation_package_digest_sha256"
    ] = digest(package_without_digest)

    return package


def build_result(
    *,
    package: dict[str, Any],
    request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    decision = package[
        "mapping_fixation_decision"
    ]
    activity = package[
        "current_phase_activity"
    ]

    return {
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-D"
        ),
        "status": (
            "PASS_PRODUCTION_CATEGORY_MAPPING_FIXED_"
            "NO_NETWORK_NO_PAYLOAD_INJECTION"
        ),
        "decision": (
            "CATEGORY_ID_10_LATEST_VOLUME_MAPPING_"
            "FIXED_AWAITING_PAYLOAD_BINDING_GATE"
        ),
        "policy_id": package["policy_id"],
        "mapping_fixation_package_id": package[
            "mapping_fixation_package_id"
        ],
        "request_path": display_path(
            request_path
        ),
        "output_path": display_path(
            output_path
        ),
        "mapping_artifact_path": package[
            "mapping_artifact_path"
        ],
        "mapping_id": decision[
            "mapping_id"
        ],
        "article_scope_id": decision[
            "article_scope_id"
        ],
        "article_scope_label": decision[
            "article_scope_label"
        ],
        "production_category_id": decision[
            "production_category_id"
        ],
        "production_category_name": decision[
            "production_category_name"
        ],
        "production_category_slug": decision[
            "production_category_slug"
        ],
        "human_mapping_fixation_approved": True,
        "production_category_mapping_fixed": True,
        "mapping_artifact_created_in_this_run": decision[
            "mapping_artifact_created_in_this_run"
        ],
        "automatic_category_selection_performed": activity[
            "automatic_category_selection_performed"
        ],
        "automatic_category_mapping_performed": activity[
            "automatic_category_mapping_performed"
        ],
        "mapping_change_requires_new_human_approval": True,
        "mapping_change_allowed_without_new_approval": False,
        "payload_binding_complete": False,
        "credential_file_read": activity[
            "credential_file_read"
        ],
        "network_connection_performed": activity[
            "network_connection_performed"
        ],
        "http_request_performed": activity[
            "http_request_performed"
        ],
        "wordpress_response_read": activity[
            "wordpress_response_read"
        ],
        "wordpress_category_created": activity[
            "wordpress_category_created"
        ],
        "wordpress_write_performed": activity[
            "wordpress_write_performed"
        ],
        "wordpress_draft_created": activity[
            "wordpress_draft_created"
        ],
        "production_payload_modified": activity[
            "production_payload_modified"
        ],
        "production_category_id_payload_injected": activity[
            "production_category_id_payload_injected"
        ],
        "mapping_artifact_digest_sha256": package[
            "mapping_artifact_digest_sha256"
        ],
        "mapping_fixation_decision_digest_sha256": decision[
            "mapping_fixation_decision_digest_sha256"
        ],
        "mapping_fixation_package_digest_sha256": package[
            "mapping_fixation_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity_verified",
                "mapping_fixation_requested",
                "mapping_artifact_semantic_identity_verified",
                "mapping_artifact_digest_verified",
                "production_category_id_10_fixed",
                "production_category_name_latest_volume_fixed",
                "article_scope_fixed",
                "human_mapping_fixation_approval_verified",
                "automatic_category_selection_not_performed",
                "automatic_category_mapping_not_performed",
                "mapping_change_requires_new_approval",
                "payload_binding_not_performed",
                "credential_file_unread",
                "network_unaccessed",
                "wordpress_unaccessed",
                "wordpress_category_not_created",
                "wordpress_write_not_performed",
                "wordpress_draft_not_created",
                "production_payload_not_modified",
                "category_id_not_injected",
                "execution_gate_closed",
            ]
        ),
        "approval_reuse_allowed": False,
        "payload_binding_allowed": False,
        "production_category_id_payload_injection_allowed": False,
        "wordpress_category_creation_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CATEGORY_MAPPING_FIXED_"
            "PAYLOAD_NOT_BOUND"
        ),
        "ready_for_ls_new_batch_4g_2e_recovery_e": True,
        "ready_for_payload_binding_gate": True,
        "ready_for_payload_injection": False,
        "ready_for_wordpress_draft": False,
        "ready_for_wordpress_write": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(
    result: dict[str, Any],
) -> str:
    return f"""# LS-NEW-BATCH-4G-2E-RECOVERY-D Production Category Mapping Fixation

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Human mapping fixation approved: `true`
- Production category mapping fixed: `true`

## Fixed Mapping

- Mapping ID: `{result["mapping_id"]}`
- Article scope: `{result["article_scope_label"]}`
- Production category ID: `{result["production_category_id"]}`
- Production category name: `{result["production_category_name"]}`
- Production category slug: `{result["production_category_slug"]}`

## Mapping Boundary

- Automatic category selection performed: `false`
- Automatic category mapping performed: `false`
- Mapping changes without new approval: `false`
- Payload binding complete: `false`
- Production category ID injected: `false`

## External Activity

- Credential file read: `false`
- Network connection performed: `false`
- HTTP request performed: `false`
- WordPress response read: `false`
- WordPress category created: `false`
- WordPress write performed: `false`
- WordPress draft created: `false`

## Production Boundary

- Production payload modified: `false`
- Payload injection allowed: `false`
- WordPress write allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`

## Next State

The production category mapping is fixed in the repository.
A separate payload-binding gate is required before any draft payload
may reference category ID 10.
"""


def resolve_path(path: Path) -> Path:
    return (
        path
        if path.is_absolute()
        else ROOT / path
    )


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
        validate_request(
            request,
            policy,
        )

        (
            source_result,
            _source_package,
            _source_approval,
            mapping_approval,
            source_checks,
        ) = validate_source_and_approval(
            request,
            policy,
        )

        mapping_artifact, mapping_created = (
            ensure_mapping_artifact(
                source_result=source_result,
                mapping_approval=mapping_approval,
                mapping_path=MAPPING_PATH,
            )
        )

        package = build_package(
            policy=policy,
            request=request,
            mapping_artifact=mapping_artifact,
            mapping_created=mapping_created,
            verified_checks=source_checks,
        )
        result = build_result(
            package=package,
            request_path=request_path,
            output_path=output_path,
            policy_checks=policy_checks,
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-D"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "production_category_mapping_fixed": False,
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_write_performed": False,
            "production_payload_modified": False,
            "production_category_id_payload_injected": False,
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
