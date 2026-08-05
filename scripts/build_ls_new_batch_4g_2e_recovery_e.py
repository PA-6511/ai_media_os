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
    "new_release_wp_fresh_payload_binding_plan_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_payload_"
    "binding_plan_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_payload_"
    "binding_plan_package.example.json"
)
PLAN_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_payload_binding_plan.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_e_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_e_"
    "fresh_payload_binding_plan_report.md"
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


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-E",
        "policy phase mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == (
            "NEW_RELEASE_WP_FRESH_PAYLOAD_"
            "BINDING_PLAN_POLICY_V1"
        ),
        "policy identity mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == (
            "APPROVED_FRESH_PAYLOAD_BINDING_"
            "PLAN_RECORDING_ONLY"
        ),
        "operation mode mismatch",
    )
    checks.append("plan_recording_mode")

    approval = policy[
        "plan_approval_contract"
    ]

    require(
        approval["required_approval_label"]
        == "FRESH_PAYLOAD_BINDING_PLAN_APPROVED",
        "approval label mismatch",
    )
    require(
        approval["human_explicit_approval_required"]
        is True,
        "human approval must be required",
    )
    require(
        approval["legacy_post185_exclusion_approved"]
        is True,
        "legacy exclusion approval missing",
    )
    require(
        approval[
            "fresh_payload_copy_binding_plan_approved"
        ]
        is True,
        "copy-binding plan approval missing",
    )

    for field in [
        "payload_creation_authorized",
        "payload_binding_authorized",
        "wordpress_execution_authorized",
    ]:
        require(
            approval[field] is False,
            f"{field} must remain false",
        )

    checks.append("plan_approval_contract")

    legacy = policy[
        "legacy_exclusion_contract"
    ]

    require(
        legacy["exclude_legacy_post185_lineage"]
        is True,
        "legacy post185 lineage must be excluded",
    )
    require(
        legacy["excluded_wordpress_post_id"]
        == 185,
        "excluded post ID mismatch",
    )

    for field in [
        "legacy_artifact_modification_allowed",
        "legacy_artifact_payload_binding_allowed",
        "legacy_artifact_category_injection_allowed",
        "legacy_artifact_reuse_as_fresh_payload_allowed",
    ]:
        require(
            legacy[field] is False,
            f"{field} must remain false",
        )

    checks.append("legacy_exclusion_contract")

    source = policy[
        "fresh_payload_source_contract"
    ]

    require(
        source["required_status"] == "draft",
        "future payload status must be draft",
    )
    require(
        source["source_must_remain_immutable"]
        is True,
        "source payload must remain immutable",
    )
    require(
        source["source_must_not_be_result_log"]
        is True,
        "result logs must be excluded",
    )
    require(
        source[
            "source_must_not_reference_published_post_185"
        ]
        is True,
        "published post185 references must be excluded",
    )
    checks.append("future_fresh_payload_contract")

    binding = policy[
        "offline_binding_contract"
    ]

    require(
        binding["binding_operation"]
        == "COPY_SOURCE_AND_SET_CATEGORIES_ONLY",
        "binding operation mismatch",
    )
    require(
        binding["only_mutable_json_pointer"]
        == "/categories",
        "mutable JSON pointer mismatch",
    )
    require(
        binding["categories_after_binding"]
        == [10],
        "binding category mismatch",
    )
    require(
        binding["source_overwrite_allowed"]
        is False,
        "source overwrite must be forbidden",
    )
    require(
        binding["semantic_diff_must_be_categories_only"]
        is True,
        "semantic diff must be categories only",
    )
    require(
        binding["wordpress_submission_allowed_after_binding"]
        is False,
        "WordPress submission must remain forbidden",
    )
    checks.append("offline_copy_binding_contract")

    current = policy[
        "current_phase_activity"
    ]

    for field, value in current.items():
        require(
            value is False,
            f"current activity {field} must be false",
        )

    checks.append("current_phase_no_activity")

    execution = policy[
        "execution_boundary"
    ]

    for field, value in execution.items():
        if field in {
            "production_status",
            "safety_state",
        }:
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    require(
        execution["production_status"] == "NO_GO",
        "production status must remain NO_GO",
    )
    checks.append("execution_boundary")

    return checks


def validate_request_and_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-E",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )
    require(
        request.get("plan_recording_requested")
        is True,
        "plan recording must be requested",
    )
    require(
        request.get(
            "legacy_post185_exclusion_requested"
        )
        is True,
        "legacy exclusion must be requested",
    )

    for field in [
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
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    source_result_path = resolve_repo_path(
        request["source_result_path"]
    )
    mapping_path = resolve_repo_path(
        request["mapping_artifact_path"]
    )
    source_approval_path = resolve_repo_path(
        request["source_mapping_approval_path"]
    )
    plan_approval_path = resolve_repo_path(
        request["plan_approval_path"]
    )

    source_result = load_json(source_result_path)
    mapping = load_json(mapping_path)
    source_approval = load_json(
        source_approval_path
    )
    plan_approval = load_json(
        plan_approval_path
    )

    require(
        digest(source_result)
        == request["source_result_digest_sha256"],
        "source result digest mismatch",
    )
    require(
        file_sha256(mapping_path)
        == request["mapping_file_sha256"],
        "mapping file SHA-256 mismatch",
    )
    require(
        digest(source_approval)
        == request[
            "source_mapping_approval_digest_sha256"
        ],
        "source approval file digest mismatch",
    )
    require(
        digest(plan_approval)
        == request["plan_approval_digest_sha256"],
        "plan approval file digest mismatch",
    )

    contract = policy[
        "source_mapping_contract"
    ]

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
        source_result.get("mapping_id")
        == contract["required_mapping_id"],
        "source mapping identity mismatch",
    )
    require(
        source_result.get("production_category_id")
        == 10,
        "source category ID mismatch",
    )
    require(
        source_result.get("production_category_name")
        == "最新巻",
        "source category name mismatch",
    )
    require(
        source_result.get(
            "production_category_mapping_fixed"
        )
        is True,
        "source mapping must be fixed",
    )
    require(
        source_result.get("payload_binding_complete")
        is False,
        "source payload must remain unbound",
    )
    require(
        source_result.get(
            "production_category_id_payload_injected"
        )
        is False,
        "source category injection must be false",
    )
    require(
        source_result.get("http_request_performed")
        is False,
        "source HTTP activity must be false",
    )
    require(
        source_result.get("wordpress_write_performed")
        is False,
        "source WordPress write must be false",
    )

    mapping_without_digest = copy.deepcopy(mapping)
    stored_mapping_digest = (
        mapping_without_digest.pop(
            "mapping_artifact_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_mapping_digest, str)
        and digest(mapping_without_digest)
        == stored_mapping_digest,
        "mapping artifact digest invalid",
    )
    require(
        stored_mapping_digest
        == request[
            "mapping_artifact_digest_sha256"
        ],
        "mapping artifact digest reference mismatch",
    )
    require(
        mapping.get("mapping_fixed") is True,
        "mapping artifact must be fixed",
    )
    require(
        mapping.get("production_category_id") == 10,
        "mapping artifact category ID mismatch",
    )
    require(
        mapping.get("payload_binding_complete")
        is False,
        "mapping artifact payload binding must be false",
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
        "source mapping approval digest invalid",
    )

    plan_approval_without_digest = copy.deepcopy(
        plan_approval
    )
    stored_plan_approval_digest = (
        plan_approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(
            stored_plan_approval_digest,
            str,
        )
        and digest(plan_approval_without_digest)
        == stored_plan_approval_digest,
        "plan approval digest invalid",
    )
    require(
        plan_approval.get("approval_label")
        == "FRESH_PAYLOAD_BINDING_PLAN_APPROVED",
        "plan approval label mismatch",
    )
    require(
        plan_approval.get("human_explicit_approval")
        is True,
        "human plan approval missing",
    )
    require(
        plan_approval.get("execution_allowed")
        is False,
        "plan approval must not authorize execution",
    )

    request_legacy = request.get(
        "legacy_inspection_evidence"
    )

    require(
        isinstance(request_legacy, list)
        and len(request_legacy) == 3,
        "legacy inspection evidence mismatch",
    )

    for item in request_legacy:
        require(
            isinstance(item, dict),
            "legacy evidence item invalid",
        )

        legacy_path = resolve_repo_path(
            item["path"]
        )

        require(
            legacy_path.exists(),
            "legacy evidence file missing",
        )
        require(
            file_sha256(legacy_path)
            == item["file_sha256"],
            "legacy evidence file changed",
        )
        require(
            item["independent_payload_path_found"]
            is False,
            "legacy payload path must remain absent",
        )
        require(
            item["payload_body_found"] is False,
            "legacy payload body must remain absent",
        )
        require(
            item["categories_payload_found"]
            is False,
            "legacy categories payload must remain absent",
        )
        require(
            item["eligible_as_fresh_payload"]
            is False,
            "legacy file must remain ineligible",
        )
        require(
            item["modification_allowed"] is False,
            "legacy modification must remain forbidden",
        )

    return (
        source_result,
        mapping,
        source_approval,
        plan_approval,
        [
            "request_identity_verified",
            "plan_recording_requested",
            "legacy_post185_exclusion_requested",
            "source_result_digest_verified",
            "mapping_file_sha256_verified",
            "mapping_artifact_digest_verified",
            "source_mapping_approval_verified",
            "fresh_payload_plan_approval_verified",
            "source_mapping_fixed_verified",
            "source_payload_unbound_verified",
            "source_category_injection_absent",
            "source_http_unperformed",
            "source_wordpress_write_absent",
            "legacy_inspection_files_verified",
            "legacy_payload_references_absent",
            "legacy_payload_bodies_absent",
            "legacy_categories_payloads_absent",
            "legacy_artifacts_ineligible",
            "legacy_artifact_modification_forbidden",
            "fresh_payload_creation_not_requested",
            "payload_binding_not_requested",
            "category_injection_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
            "execution_not_requested",
        ],
    )


def stable_plan(
    *,
    mapping: dict[str, Any],
    plan_approval: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "plan_id": (
            "FRESH_NEW_RELEASE_PAYLOAD_OFFLINE_"
            "CATEGORY_BINDING_PLAN_V1"
        ),
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-E"
        ),
        "template_contract_id": (
            "POST185_STANDARD_TEMPLATE_V1_FIXED"
        ),
        "article_scope_id": (
            "COMIC_NEW_RELEASE_LATEST_VOLUME_"
            "DISTRIBUTION_START"
        ),
        "article_scope_label": (
            "コミック新刊・新巻配信開始記事"
        ),
        "mapping": {
            "mapping_id": mapping["mapping_id"],
            "mapping_artifact_path": (
                "config/"
                "new_release_wp_production_category_mapping.json"
            ),
            "mapping_artifact_digest_sha256": (
                mapping[
                    "mapping_artifact_digest_sha256"
                ]
            ),
            "production_category_id": 10,
            "production_category_name": "最新巻",
            "mapping_fixed": True,
        },
        "legacy_exclusion": {
            "legacy_post185_lineage_excluded": True,
            "legacy_title": "月曜日のたわわ",
            "legacy_volume": "第15巻",
            "legacy_wordpress_post_id": 185,
            "legacy_artifact_reuse_allowed": False,
            "legacy_artifact_modification_allowed": False,
            "verified_inspection_evidence": copy.deepcopy(
                request[
                    "legacy_inspection_evidence"
                ]
            ),
        },
        "future_source_contract": {
            "source_root": (
                "exchange/payloads/new_release/fresh"
            ),
            "source_must_be_created_after_plan_fixation": True,
            "source_must_be_new_json_object": True,
            "required_fields": [
                "title",
                "content",
                "status"
            ],
            "required_status": "draft",
            "categories_allowed_before_binding": [
                "ABSENT",
                "EMPTY_LIST"
            ],
            "source_file_sha256_required": True,
            "source_payload_digest_required": True,
            "source_must_remain_immutable": True,
            "source_must_not_be_result_log": True,
            "source_must_not_be_confirmation_log": True,
            "source_must_not_reference_post_185": True,
            "human_review_required_before_binding": True,
        },
        "offline_binding_contract": {
            "operation": (
                "COPY_SOURCE_AND_SET_CATEGORIES_ONLY"
            ),
            "destination_root": (
                "exchange/payloads/new_release/bound"
            ),
            "destination_must_be_new_file": True,
            "source_overwrite_allowed": False,
            "only_mutable_json_pointer": "/categories",
            "categories_after_binding": [
                10
            ],
            "semantic_diff_must_be_categories_only": True,
            "source_file_sha256_must_be_recorded": True,
            "destination_file_sha256_must_be_recorded": True,
            "human_review_required_after_binding": True,
            "wordpress_submission_allowed": False,
            "wordpress_draft_creation_allowed": False,
            "wordpress_publish_allowed": False,
        },
        "approval": {
            "approval_label": plan_approval[
                "approval_label"
            ],
            "approval_evidence_digest_sha256": (
                plan_approval[
                    "approval_evidence_digest_sha256"
                ]
            ),
            "human_explicit_approval": True,
            "approval_reuse_allowed": False,
            "plan_change_requires_new_human_approval": True,
            "execution_allowed": False,
        },
        "current_state": {
            "fresh_payload_exists": False,
            "fresh_payload_created": False,
            "fresh_payload_read": False,
            "fresh_payload_copied": False,
            "payload_binding_complete": False,
            "payload_modified": False,
            "category_id_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "FRESH_PAYLOAD_BINDING_PLAN_FIXED_"
                "NO_PAYLOAD_EXISTS"
            ),
        },
    }


def ensure_plan_artifact(
    *,
    mapping: dict[str, Any],
    plan_approval: dict[str, Any],
    request: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    stable = stable_plan(
        mapping=mapping,
        plan_approval=plan_approval,
        request=request,
    )

    if PLAN_PATH.exists():
        existing = load_json(PLAN_PATH)
        existing_without_digest = copy.deepcopy(
            existing
        )
        stored_digest = existing_without_digest.pop(
            "plan_artifact_digest_sha256",
            None,
        )
        fixed_at = existing_without_digest.pop(
            "plan_fixed_at_utc",
            None,
        )

        require(
            isinstance(stored_digest, str)
            and len(stored_digest) == 64,
            "existing plan digest invalid",
        )
        require(
            isinstance(fixed_at, str)
            and fixed_at != "",
            "existing plan timestamp invalid",
        )
        require(
            existing_without_digest == stable,
            "existing plan semantic mismatch",
        )

        artifact_without_digest = copy.deepcopy(
            existing
        )
        artifact_without_digest.pop(
            "plan_artifact_digest_sha256",
            None,
        )

        require(
            digest(artifact_without_digest)
            == stored_digest,
            "existing plan artifact digest mismatch",
        )

        return existing, False

    artifact_without_digest = copy.deepcopy(
        stable
    )
    artifact_without_digest[
        "plan_fixed_at_utc"
    ] = utc_now()

    artifact = copy.deepcopy(
        artifact_without_digest
    )
    artifact[
        "plan_artifact_digest_sha256"
    ] = digest(artifact_without_digest)

    write_json(
        PLAN_PATH,
        artifact,
    )

    return artifact, True


def build_package(
    *,
    policy: dict[str, Any],
    plan: dict[str, Any],
    plan_created: bool,
    verified_checks: list[str],
) -> dict[str, Any]:
    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-E"
        ),
        "policy_id": policy["policy_id"],
        "binding_plan_package_id": (
            "fresh-new-release-payload-"
            "offline-category-binding-plan"
        ),
        "operation_mode": policy[
            "operation_mode"
        ],
        "plan_artifact_path": display_path(
            PLAN_PATH
        ),
        "plan_artifact_digest_sha256": plan[
            "plan_artifact_digest_sha256"
        ],
        "plan_created_in_this_run": plan_created,
        "legacy_post185_lineage_excluded": True,
        "production_category_id": 10,
        "production_category_name": "最新巻",
        "binding_operation": (
            "COPY_SOURCE_AND_SET_CATEGORIES_ONLY"
        ),
        "only_mutable_json_pointer": "/categories",
        "categories_after_binding": [
            10
        ],
        "current_phase_activity": {
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
        },
        "verified_checks": verified_checks,
    }

    package = copy.deepcopy(
        package_without_digest
    )
    package[
        "binding_plan_package_digest_sha256"
    ] = digest(package_without_digest)

    return package


def build_result(
    *,
    package: dict[str, Any],
    request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    activity = package[
        "current_phase_activity"
    ]

    return {
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-E"
        ),
        "status": (
            "PASS_FRESH_PAYLOAD_BINDING_PLAN_FIXED_"
            "NO_PAYLOAD_NO_NETWORK"
        ),
        "decision": (
            "LEGACY_POST185_EXCLUDED_FRESH_PAYLOAD_"
            "COPY_BINDING_PLAN_RECORDED"
        ),
        "policy_id": package["policy_id"],
        "binding_plan_package_id": package[
            "binding_plan_package_id"
        ],
        "request_path": display_path(
            request_path
        ),
        "output_path": display_path(
            output_path
        ),
        "plan_artifact_path": package[
            "plan_artifact_path"
        ],
        "plan_artifact_digest_sha256": package[
            "plan_artifact_digest_sha256"
        ],
        "binding_plan_package_digest_sha256": package[
            "binding_plan_package_digest_sha256"
        ],
        "plan_created_in_this_run": package[
            "plan_created_in_this_run"
        ],
        "approval_label": (
            "FRESH_PAYLOAD_BINDING_PLAN_APPROVED"
        ),
        "human_explicit_approval": True,
        "legacy_post185_lineage_excluded": True,
        "legacy_artifact_reuse_allowed": False,
        "legacy_artifact_modification_allowed": False,
        "production_category_id": 10,
        "production_category_name": "最新巻",
        "binding_operation": package[
            "binding_operation"
        ],
        "only_mutable_json_pointer": package[
            "only_mutable_json_pointer"
        ],
        "categories_after_binding": package[
            "categories_after_binding"
        ],
        "source_overwrite_allowed": False,
        "fresh_payload_created": activity[
            "fresh_payload_created"
        ],
        "fresh_payload_read": activity[
            "fresh_payload_read"
        ],
        "fresh_payload_copied": activity[
            "fresh_payload_copied"
        ],
        "payload_binding_complete": activity[
            "payload_binding_complete"
        ],
        "payload_modified": activity[
            "payload_modified"
        ],
        "production_category_id_payload_injected": activity[
            "production_category_id_payload_injected"
        ],
        "credential_file_read": activity[
            "credential_file_read"
        ],
        "network_connection_performed": activity[
            "network_connection_performed"
        ],
        "http_request_performed": activity[
            "http_request_performed"
        ],
        "wordpress_access_performed": activity[
            "wordpress_access_performed"
        ],
        "wordpress_write_performed": activity[
            "wordpress_write_performed"
        ],
        "wordpress_draft_created": activity[
            "wordpress_draft_created"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "plan_artifact_semantic_identity_verified",
                "plan_artifact_digest_verified",
                "legacy_post185_lineage_excluded",
                "legacy_artifacts_preserved",
                "future_source_root_fixed",
                "future_destination_root_fixed",
                "copy_only_binding_operation_fixed",
                "categories_only_diff_fixed",
                "category_id_10_binding_value_fixed",
                "source_overwrite_forbidden",
                "fresh_payload_not_created",
                "fresh_payload_not_read",
                "fresh_payload_not_copied",
                "payload_binding_not_performed",
                "category_id_not_injected",
                "network_unaccessed",
                "wordpress_unaccessed",
                "wordpress_write_not_performed",
                "execution_gate_closed",
            ]
        ),
        "plan_change_requires_new_human_approval": True,
        "fresh_payload_creation_allowed": False,
        "fresh_payload_read_allowed": False,
        "fresh_payload_copy_allowed": False,
        "payload_binding_allowed": False,
        "production_category_id_payload_injection_allowed": False,
        "wordpress_access_allowed": False,
        "wordpress_write_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "FRESH_PAYLOAD_BINDING_PLAN_FIXED_"
            "NO_PAYLOAD_EXISTS"
        ),
        "ready_for_ls_new_batch_4g_2e_recovery_f": True,
        "ready_for_fresh_payload_generation_input_gate": True,
        "ready_for_fresh_payload_generation": False,
        "ready_for_offline_payload_binding": False,
        "ready_for_payload_injection": False,
        "ready_for_wordpress_draft": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    return f"""# LS-NEW-BATCH-4G-2E-RECOVERY-E Fresh Payload Binding Plan

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Human approval: `true`
- Legacy post185 lineage excluded: `true`

## Fixed Future Binding Plan

- Production category ID: `{result["production_category_id"]}`
- Production category name: `{result["production_category_name"]}`
- Operation: `{result["binding_operation"]}`
- Only mutable JSON pointer: `{result["only_mutable_json_pointer"]}`
- Categories after binding: `[10]`
- Source overwrite allowed: `false`

## Legacy Boundary

- Legacy artifact reuse allowed: `false`
- Legacy artifact modification allowed: `false`
- Legacy result-log category injection allowed: `false`

## Current Activity

- Fresh payload created: `false`
- Fresh payload read: `false`
- Fresh payload copied: `false`
- Payload binding complete: `false`
- Payload modified: `false`
- Category ID injected: `false`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress write performed: `false`

## Next State

A separate phase must identify or generate a fresh new-release draft
payload before any offline copy or category binding may occur.
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

        (
            _source_result,
            mapping,
            _source_approval,
            plan_approval,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        plan, plan_created = ensure_plan_artifact(
            mapping=mapping,
            plan_approval=plan_approval,
            request=request,
        )

        package = build_package(
            policy=policy,
            plan=plan,
            plan_created=plan_created,
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-E"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "fresh_payload_created": False,
            "fresh_payload_read": False,
            "fresh_payload_copied": False,
            "payload_binding_complete": False,
            "payload_modified": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
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
