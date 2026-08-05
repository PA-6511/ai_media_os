from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_pending_"
    "recovery_correction_policy.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def repository_path(relative: str) -> Path:
    path = (
        repo / relative
    ).resolve()

    path.relative_to(
        repo.resolve()
    )

    return path


def require_true(
    value: dict[str, Any],
    *keys: str,
) -> None:
    for key in keys:
        if value.get(key) is not True:
            raise SystemExit(
                f"REQUIRED_TRUE_INVALID: {key}"
            )


def require_false(
    value: dict[str, Any],
    *keys: str,
) -> None:
    for key in keys:
        if value.get(key) is not False:
            raise SystemExit(
                f"REQUIRED_FALSE_INVALID: {key}"
            )


def validate() -> None:
    policy = load_json(
        policy_path
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-8"
    ):
        raise SystemExit(
            "POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_PENDING_RECOVERY_"
        "FAIL_CLOSED_CLASSIFICATION_"
        "CORRECTION_DESIGN_ONLY_"
        "NO_HOST_STATE_NO_GO"
    ):
        raise SystemExit(
            "POLICY_RESULT_INVALID"
        )

    if policy["schema_version"] != 1:
        raise SystemExit(
            "SCHEMA_VERSION_INVALID"
        )

    bindings = policy["bindings"]

    path_hash_pairs = (
        (
            "durable_consumption_policy_path",
            "durable_consumption_policy_sha256",
        ),
        (
            "sandbox_writer_policy_path",
            "sandbox_writer_policy_sha256",
        ),
        (
            "sandbox_writer_source_path",
            "sandbox_writer_source_sha256",
        ),
        (
            "capsule_policy_path",
            "capsule_policy_sha256",
        ),
    )

    loaded: dict[str, dict[str, Any]] = {}

    for path_key, hash_key in path_hash_pairs:
        path = repository_path(
            bindings[path_key]
        )

        if not path.is_file():
            raise SystemExit(
                f"BOUND_INPUT_MISSING: {path_key}"
            )

        if sha256(path) != bindings[
            hash_key
        ]:
            raise SystemExit(
                f"BOUND_INPUT_HASH_INVALID: {hash_key}"
            )

        if path.suffix == ".json":
            loaded[path_key] = load_json(
                path
            )

    durable = loaded[
        "durable_consumption_policy_path"
    ]

    sandbox = loaded[
        "sandbox_writer_policy_path"
    ]

    capsule = loaded[
        "capsule_policy_path"
    ]

    if durable["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-6"
    ):
        raise SystemExit(
            "DURABLE_PHASE_INVALID"
        )

    if sandbox["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-7"
    ):
        raise SystemExit(
            "SANDBOX_PHASE_INVALID"
        )

    if capsule["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-3"
    ):
        raise SystemExit(
            "CAPSULE_PHASE_INVALID"
        )

    if bindings["release_id"] != (
        durable["bindings"]["release_id"]
    ):
        raise SystemExit(
            "RELEASE_ID_BINDING_INVALID"
        )

    reason = policy[
        "correction_reason"
    ]

    require_true(
        reason,
        "unified_fail_closed_pending_classification_required",
    )

    require_false(
        reason,
        "directory_fsync_completion_persisted_as_record_field",
        "directory_fsync_completion_derivable_from_recovered_namespace",
        "pending_pre_and_post_consumption_point_distinguishable_after_crash",
        "historical_pre_post_classification_safe_for_direct_recovery_use",
    )

    recovery = policy[
        "authoritative_recovery_rule"
    ]

    require_true(
        recovery,
        "applies_to_future_host_implementation",
        "valid_pending_reserves_authorization_id",
        "valid_pending_reserves_nonce",
        "valid_pending_blocks_new_consumption",
        "valid_pending_blocks_same_capsule_retry",
        "valid_pending_human_reconciliation_required",
        "malformed_pending_reserves_visible_filename_identifiers",
        "unknown_entry_blocks_all_new_consumption",
    )

    require_false(
        recovery,
        "historical_contract_files_modified",
        "valid_pending_automatic_delete_allowed",
        "valid_pending_automatic_finalize_allowed",
        "malformed_pending_automatic_delete_allowed",
    )

    if recovery[
        "valid_pending_classification"
    ] != (
        "REPLAY_RESERVED_"
        "CONSUMED_OR_UNCERTAIN_"
        "HUMAN_RECONCILIATION_REQUIRED"
    ):
        raise SystemExit(
            "VALID_PENDING_CLASSIFICATION_INVALID"
        )

    reconciliation = policy[
        "reconciliation_contract"
    ]

    require_true(
        reconciliation,
        "exclusive_lock_required",
        "root_custody_revalidation_required",
        "pending_filename_validation_required",
        "pending_document_validation_required",
        "filename_document_binding_required",
        "authorization_and_nonce_replay_scan_required",
        "related_install_transaction_state_review_required",
        "human_decision_record_required",
        "separate_reconciliation_authorization_required",
    )

    require_false(
        reconciliation,
        "automatic_retry_authorization_allowed",
        "automatic_consumption_record_deletion_allowed",
        "automatic_new_capsule_issuance_allowed",
    )

    matrix = policy[
        "crash_visibility_matrix"
    ]

    if len(matrix) != 6:
        raise SystemExit(
            "CRASH_MATRIX_COUNT_INVALID"
        )

    fault_points = {
        item["fault_point"]
        for item in matrix
    }

    expected_fault_points = {
        "BEFORE_PENDING_CREATE",
        (
            "AFTER_PENDING_CREATE_"
            "BEFORE_PENDING_FILE_FSYNC"
        ),
        (
            "AFTER_PENDING_FILE_FSYNC_"
            "BEFORE_RECORDS_DIRECTORY_FSYNC"
        ),
        (
            "AFTER_CONSUMPTION_POINT_"
            "BEFORE_RENAME"
        ),
        (
            "AFTER_RENAME_BEFORE_"
            "POST_RENAME_DIRECTORY_FSYNC"
        ),
        (
            "AFTER_POST_RENAME_"
            "DIRECTORY_FSYNC"
        ),
    }

    if fault_points != expected_fault_points:
        raise SystemExit(
            "CRASH_MATRIX_POINTS_INVALID"
        )

    for item in matrix:
        if item[
            "same_capsule_automatic_retry_allowed"
        ] is not False:
            raise SystemExit(
                "AUTOMATIC_RETRY_STATE_INVALID: "
                f"{item['fault_point']}"
            )

    alignment = policy[
        "sandbox_alignment"
    ]

    require_true(
        alignment,
        "sandbox_pending_entry_blocks",
        "sandbox_pending_behavior_is_fail_closed",
        "sandbox_behavior_consistent_with_correction",
        "sandbox_test_state_only",
    )

    require_false(
        alignment,
        "sandbox_writer_modified_in_this_phase",
    )

    if sandbox[
        "writer_protocol"
    ]["pending_entry_blocks"] is not True:
        raise SystemExit(
            "SANDBOX_PENDING_BEHAVIOR_INVALID"
        )

    implementation = policy[
        "implementation_boundary"
    ]

    for key, value in (
        implementation.items()
    ):
        if value is not False:
            raise SystemExit(
                f"IMPLEMENTATION_BOUNDARY_INVALID: {key}"
            )

    for key, value in policy[
        "non_start_guarantee"
    ].items():
        if value is not False:
            raise SystemExit(
                f"NON_START_STATE_INVALID: {key}"
            )

    governance = policy[
        "governance"
    ]

    if governance[
        "design_correction_only"
    ] is not True:
        raise SystemExit(
            "DESIGN_CORRECTION_STATE_INVALID"
        )

    for key in (
        "host_change_executed",
        "capsule_issued",
        "capsule_file_created",
        "authorization_consumed_on_host",
        "host_consumption_record_created",
        "host_recovery_handler_implemented",
        "host_recovery_handler_installed",
        "reconciliation_tool_implemented",
        "reconciliation_tool_installed",
        "root_file_custody_validated",
        "root_release_install_authorized",
        "root_release_install_executed",
        "root_helper_implemented",
        "root_helper_installed",
        "root_ownership_applied",
        "current_host_link_created",
        "secret_migration_executed",
        "unit_change_executed",
        "daemon_reload_executed",
        "gate_creation_executed",
        "service_start_executed",
        "unit_enable_executed",
    ):
        if governance[key] is not False:
            raise SystemExit(
                f"GOVERNANCE_STATE_INVALID: {key}"
            )

    if governance[
        "production_status"
    ] != "NO_GO":
        raise SystemExit(
            "PRODUCTION_STATUS_INVALID"
        )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise SystemExit(
            "FINAL_DECISION_INVALID"
        )

    print(
        "PENDING_RECOVERY_OBSERVABILITY_CORRECTION: PASS"
    )
    print(
        "UNIFIED_FAIL_CLOSED_PENDING_RULE: PASS"
    )
    print(
        "AUTHORIZATION_ID_REPLAY_RESERVATION: PASS"
    )
    print(
        "NONCE_REPLAY_RESERVATION: PASS"
    )
    print(
        "AUTOMATIC_PENDING_DELETE_PROHIBITED: PASS"
    )
    print(
        "HUMAN_RECONCILIATION_REQUIRED: PASS"
    )
    print(
        "SANDBOX_PENDING_BEHAVIOR_ALIGNED: PASS"
    )
    print(
        "HOST_RECOVERY_HANDLER_IMPLEMENTED: FALSE"
    )
    print(
        "AUTHORIZATION_CONSUMED_ON_HOST: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "SERVICE_START_EXECUTED: FALSE"
    )
    print(
        "UNIT_ENABLE_EXECUTED: FALSE"
    )
    print("FINAL_DECISION: NO_GO")
    print(
        "SQL_B2_4B_5G_3B_1D_2B_8_"
        "PENDING_RECOVERY_CORRECTION: PASS"
    )


if __name__ == "__main__":
    validate()
