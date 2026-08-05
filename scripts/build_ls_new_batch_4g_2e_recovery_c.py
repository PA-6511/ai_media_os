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
    "new_release_wp_category_index_human_review_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_index_human_review_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_index_human_review_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_c_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_c_human_review_report.md"
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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-C",
        "policy phase mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == (
            "NEW_RELEASE_WP_CATEGORY_INDEX_"
            "HUMAN_REVIEW_POLICY_V1"
        ),
        "policy identity mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == (
            "HUMAN_CATEGORY_SELECTION_"
            "EVIDENCE_ONLY"
        ),
        "operation mode mismatch",
    )
    checks.append("human_review_evidence_mode")

    review = policy[
        "human_review_contract"
    ]

    require(
        review["required_approval_label"]
        == "CATEGORY_INDEX_HUMAN_REVIEW_APPROVED",
        "approval label mismatch",
    )
    require(
        review["selected_category_id"] == 10,
        "selected category ID mismatch",
    )
    require(
        review["selected_category_name"]
        == "最新巻",
        "selected category name mismatch",
    )
    require(
        review["human_selection_required"]
        is True,
        "human selection must be required",
    )
    require(
        review["automatic_selection_allowed"]
        is False,
        "automatic selection must be forbidden",
    )
    checks.append("human_selection_contract")

    boundary = policy[
        "selection_boundary"
    ]

    for field in [
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

    checks.append("selection_boundary")

    for field, value in policy[
        "current_phase_access"
    ].items():
        require(
            value is False,
            f"{field} must remain false",
        )

    checks.append("current_phase_no_access")

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


def validate_source_and_approval(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
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
    source_lock = load_json(
        resolve_repo_path(
            request["source_lock_path"]
        )
    )
    approval = load_json(
        resolve_repo_path(
            request["approval_path"]
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
        digest(source_lock)
        == request[
            "source_lock_digest_sha256"
        ],
        "source lock digest mismatch",
    )
    require(
        digest(approval)
        == request[
            "approval_digest_sha256"
        ],
        "approval file digest mismatch",
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
        source_result.get("http_status")
        == source_contract[
            "required_http_status"
        ],
        "source HTTP status mismatch",
    )
    require(
        source_result.get("category_count")
        == source_contract[
            "required_category_count"
        ],
        "source category count mismatch",
    )
    require(
        source_result.get("x_wp_total_pages")
        == source_contract[
            "required_total_pages"
        ],
        "source page count mismatch",
    )
    require(
        source_result.get(
            "approval_label_consumed"
        )
        is True,
        "source approval must be consumed",
    )
    require(
        source_result.get(
            "approval_reuse_allowed"
        )
        is False,
        "source approval reuse must be false",
    )
    require(
        source_result.get(
            "category_selected"
        )
        is False,
        "source must remain unselected",
    )
    require(
        source_result.get(
            "category_mapping_fixed"
        )
        is False,
        "source mapping must remain unfixed",
    )
    require(
        source_result.get(
            "wordpress_write_performed"
        )
        is False,
        "source WordPress write must be false",
    )

    require(
        source_lock.get("state")
        == source_contract[
            "required_source_lock_state"
        ],
        "source lock state mismatch",
    )
    require(
        source_lock.get(
            "approval_label_consumed"
        )
        is True,
        "source lock approval state mismatch",
    )
    require(
        source_lock.get(
            "http_request_attempt_count"
        )
        == 1,
        "source lock request count mismatch",
    )

    require(
        approval.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-C",
        "approval phase mismatch",
    )
    require(
        approval.get("approval_label")
        == policy[
            "human_review_contract"
        ]["required_approval_label"],
        "human review approval label mismatch",
    )
    require(
        approval.get(
            "human_explicit_approval"
        )
        is True,
        "human explicit approval missing",
    )
    require(
        approval.get("approved_by")
        == "HUMAN_OPERATOR",
        "approval actor mismatch",
    )
    require(
        approval.get(
            "approval_reuse_allowed"
        )
        is False,
        "approval reuse must be forbidden",
    )
    require(
        approval.get("execution_allowed")
        is False,
        "human-review approval must not authorize execution",
    )

    stored_approval_digest = approval.get(
        "approval_evidence_digest_sha256"
    )
    approval_without_digest = copy.deepcopy(
        approval
    )
    approval_without_digest.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        isinstance(
            stored_approval_digest,
            str,
        )
        and digest(
            approval_without_digest
        )
        == stored_approval_digest,
        "approval evidence digest invalid",
    )

    category_index = source_result.get(
        "category_index"
    )

    require(
        isinstance(category_index, dict),
        "source category index missing",
    )

    categories = category_index.get(
        "categories"
    )

    require(
        isinstance(categories, list),
        "source category list missing",
    )

    selected = [
        item
        for item in categories
        if (
            isinstance(item, dict)
            and item.get("id") == 10
            and item.get("name") == "最新巻"
        )
    ]

    require(
        len(selected) == 1,
        "selected category not uniquely present",
    )

    source_category = selected[0]
    source_category_without_digest = (
        copy.deepcopy(source_category)
    )
    stored_source_category_digest = (
        source_category_without_digest.pop(
            "category_digest_sha256",
            None,
        )
    )

    require(
        isinstance(
            stored_source_category_digest,
            str,
        )
        and digest(
            source_category_without_digest
        )
        == stored_source_category_digest,
        "source category digest invalid",
    )

    selection = approval.get("selection")

    require(
        isinstance(selection, dict),
        "approval selection missing",
    )
    require(
        selection.get("category_id") == 10,
        "approved category ID mismatch",
    )
    require(
        selection.get("category_name")
        == "最新巻",
        "approved category name mismatch",
    )
    require(
        selection.get(
            "source_category_digest_sha256"
        )
        == stored_source_category_digest,
        "approved source category digest mismatch",
    )
    require(
        selection.get("human_selected")
        is True,
        "human-selected flag missing",
    )
    require(
        selection.get(
            "automatic_selection_performed"
        )
        is False,
        "automatic selection must be false",
    )
    require(
        selection.get(
            "category_mapping_fixed"
        )
        is False,
        "mapping must remain unfixed",
    )
    require(
        selection.get(
            "payload_injection_allowed"
        )
        is False,
        "payload injection must remain forbidden",
    )
    require(
        selection.get(
            "wordpress_write_allowed"
        )
        is False,
        "WordPress write must remain forbidden",
    )

    return (
        source_result,
        source_lock,
        approval,
        [
            "source_result_digest_verified",
            "source_lock_digest_verified",
            "approval_file_digest_verified",
            "source_phase_verified",
            "source_status_verified",
            "source_category_index_verified",
            "source_one_shot_lock_preserved",
            "source_approval_consumed",
            "source_category_unselected",
            "source_mapping_unfixed",
            "source_wordpress_write_absent",
            "human_explicit_approval_verified",
            "approval_evidence_digest_verified",
            "selected_category_uniquely_present",
            "selected_category_digest_verified",
            "selected_category_id_verified",
            "selected_category_name_verified",
            "human_selection_verified",
            "automatic_selection_absent",
            "payload_injection_forbidden",
            "wordpress_write_forbidden",
        ],
    )


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-C",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    selected = request.get(
        "selected_category"
    )

    require(
        isinstance(selected, dict),
        "selected category request missing",
    )
    require(
        selected.get("id") == 10,
        "request category ID mismatch",
    )
    require(
        selected.get("name") == "最新巻",
        "request category name mismatch",
    )
    require(
        selected.get("purpose")
        == "コミック新刊・新巻配信開始記事",
        "request category purpose mismatch",
    )
    require(
        request.get(
            "human_selection_recording_requested"
        )
        is True,
        "human selection recording must be requested",
    )

    for field in [
        "automatic_category_selection_requested",
        "automatic_category_mapping_requested",
        "category_mapping_fixation_requested",
        "production_category_id_payload_injection_requested",
        "wordpress_category_creation_requested",
        "wordpress_write_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "production_payload_modification_requested",
        "execution_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )


def build_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    (
        source_result,
        source_lock,
        approval,
        verified_checks,
    ) = validate_source_and_approval(
        request,
        policy,
    )
    validate_request(
        request,
        policy,
    )

    source_categories = source_result[
        "category_index"
    ]["categories"]

    selected_source = next(
        item
        for item in source_categories
        if (
            item["id"] == 10
            and item["name"] == "最新巻"
        )
    )

    decision_without_digest = {
        "category_id": 10,
        "category_name": "最新巻",
        "category_slug": selected_source[
            "slug"
        ],
        "category_purpose": (
            "コミック新刊・新巻配信開始記事"
        ),
        "source_category_digest_sha256": (
            selected_source[
                "category_digest_sha256"
            ]
        ),
        "human_selected": True,
        "automatic_selection_performed": False,
        "automatic_mapping_performed": False,
        "category_mapping_fixed": False,
        "production_usable": False,
        "payload_injection_allowed": False,
        "wordpress_write_allowed": False,
        "human_review_complete": True,
    }

    decision = copy.deepcopy(
        decision_without_digest
    )
    decision[
        "human_selection_decision_digest_sha256"
    ] = digest(
        decision_without_digest
    )

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-C"
        ),
        "policy_id": policy["policy_id"],
        "human_review_package_id": (
            "wp-category-index-human-review-"
            "latest-volume-selection"
        ),
        "operation_mode": policy[
            "operation_mode"
        ],
        "source_state": {
            "phase_id": source_result[
                "phase_id"
            ],
            "status": source_result[
                "status"
            ],
            "category_count": source_result[
                "category_count"
            ],
            "source_lock_state": source_lock[
                "state"
            ],
            "source_approval_consumed": True,
            "source_approval_reusable": False,
        },
        "human_approval": {
            "approval_label": approval[
                "approval_label"
            ],
            "approved_by": approval[
                "approved_by"
            ],
            "human_explicit_approval": True,
            "approval_recorded": True,
            "approval_reuse_allowed": False,
            "selection_change_requires_new_approval": True,
            "execution_allowed": False,
        },
        "human_selection_decision": decision,
        "current_phase_activity": {
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_response_read": False,
            "wordpress_write_performed": False,
            "wordpress_category_created": False,
            "automatic_category_selection_performed": False,
            "automatic_category_mapping_performed": False,
            "category_mapping_fixed": False,
            "production_payload_modified": False,
            "production_category_id_payload_injected": False,
        },
        "verified_checks": verified_checks,
    }

    package = copy.deepcopy(
        package_without_digest
    )
    package[
        "human_review_package_digest_sha256"
    ] = digest(package_without_digest)

    return package


def build_result(
    package: dict[str, Any],
    request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    selection = package[
        "human_selection_decision"
    ]
    activity = package[
        "current_phase_activity"
    ]

    return {
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-C"
        ),
        "status": (
            "PASS_CATEGORY_INDEX_HUMAN_REVIEW_"
            "RECORDED_NO_NETWORK"
        ),
        "decision": (
            "CATEGORY_ID_10_LATEST_VOLUME_"
            "SELECTED_BY_HUMAN_MAPPING_NOT_FIXED"
        ),
        "policy_id": package[
            "policy_id"
        ],
        "human_review_package_id": package[
            "human_review_package_id"
        ],
        "request_path": display_path(
            request_path
        ),
        "output_path": display_path(
            output_path
        ),
        "approval_label": package[
            "human_approval"
        ]["approval_label"],
        "human_explicit_approval": True,
        "human_selection_recorded": True,
        "selected_category_id": selection[
            "category_id"
        ],
        "selected_category_name": selection[
            "category_name"
        ],
        "selected_category_slug": selection[
            "category_slug"
        ],
        "selected_category_purpose": selection[
            "category_purpose"
        ],
        "source_category_digest_sha256": selection[
            "source_category_digest_sha256"
        ],
        "human_selection_decision_digest_sha256": selection[
            "human_selection_decision_digest_sha256"
        ],
        "human_review_package_digest_sha256": package[
            "human_review_package_digest_sha256"
        ],
        "automatic_category_selection_performed": activity[
            "automatic_category_selection_performed"
        ],
        "automatic_category_mapping_performed": activity[
            "automatic_category_mapping_performed"
        ],
        "category_mapping_fixed": activity[
            "category_mapping_fixed"
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
        "wordpress_response_read": activity[
            "wordpress_response_read"
        ],
        "wordpress_category_created": activity[
            "wordpress_category_created"
        ],
        "wordpress_write_performed": activity[
            "wordpress_write_performed"
        ],
        "production_payload_modified": activity[
            "production_payload_modified"
        ],
        "production_category_id_payload_injected": activity[
            "production_category_id_payload_injected"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity_verified",
                "human_selection_recording_requested",
                "selected_category_purpose_verified",
                "selection_decision_digest_generated",
                "human_review_package_digest_generated",
                "automatic_selection_not_performed",
                "automatic_mapping_not_performed",
                "mapping_not_fixed",
                "credential_file_unread",
                "network_unaccessed",
                "wordpress_unaccessed",
                "wordpress_category_not_created",
                "wordpress_write_not_performed",
                "production_payload_not_modified",
                "category_id_not_injected",
                "execution_gate_closed",
            ]
        ),
        "approval_reuse_allowed": False,
        "selection_change_requires_new_approval": True,
        "category_mapping_fixation_allowed": False,
        "production_category_id_payload_injection_allowed": False,
        "wordpress_category_creation_allowed": False,
        "wordpress_write_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "HUMAN_CATEGORY_SELECTION_RECORDED_"
            "MAPPING_NOT_FIXED"
        ),
        "ready_for_ls_new_batch_4g_2e_recovery_d": True,
        "ready_for_category_mapping_fixation": True,
        "ready_for_payload_injection": False,
        "ready_for_wordpress_draft": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(
    result: dict[str, Any],
) -> str:
    return f"""# LS-NEW-BATCH-4G-2E-RECOVERY-C Human Category Review

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Approval label: `{result["approval_label"]}`
- Human selection recorded: `true`

## Selected Category

- Category ID: `{result["selected_category_id"]}`
- Category name: `{result["selected_category_name"]}`
- Category slug: `{result["selected_category_slug"]}`
- Purpose: `{result["selected_category_purpose"]}`

## Selection Boundary

- Human selected: `true`
- Automatic category selection performed: `false`
- Automatic category mapping performed: `false`
- Category mapping fixed: `false`
- Production category ID injected: `false`

## Current Activity

- Credential file read: `false`
- Network connection performed: `false`
- HTTP request performed: `false`
- WordPress response read: `false`
- WordPress category created: `false`
- WordPress write performed: `false`
- Production payload modified: `false`

## Next State

The human category selection is recorded, but the production
category mapping is not fixed. A separate fixation phase is required.
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
        policy = load_json(
            POLICY_PATH
        )
        request = load_json(
            request_path
        )

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
                "LS-NEW-BATCH-4G-2E-RECOVERY-C"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_write_performed": False,
            "category_mapping_fixed": False,
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
