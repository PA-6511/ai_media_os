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
    "authorization_durable_"
    "consumption_policy.json"
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
        "SQL-B2-4B-5G-3B-1D-2B-6"
    ):
        raise SystemExit(
            "POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_DURABLE_AUTHORIZATION_"
        "CONSUMPTION_STATE_CONTRACT_"
        "DESIGN_ONLY_NO_HOST_STATE_NO_GO"
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
            "capsule_policy_path",
            "capsule_policy_sha256",
        ),
        (
            "reference_model_policy_path",
            "reference_model_policy_sha256",
        ),
        (
            "reference_model_source_path",
            "reference_model_source_sha256",
        ),
        (
            "root_install_policy_path",
            "root_install_policy_sha256",
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

    capsule = loaded[
        "capsule_policy_path"
    ]

    reference = loaded[
        "reference_model_policy_path"
    ]

    root_policy = loaded[
        "root_install_policy_path"
    ]

    if capsule["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-3"
    ):
        raise SystemExit(
            "CAPSULE_PHASE_INVALID"
        )

    if reference["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-5"
    ):
        raise SystemExit(
            "REFERENCE_PHASE_INVALID"
        )

    if root_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-1"
    ):
        raise SystemExit(
            "ROOT_PHASE_INVALID"
        )

    if bindings["release_id"] != (
        capsule[
            "release_binding"
        ]["release_id"]
    ):
        raise SystemExit(
            "RELEASE_ID_BINDING_INVALID"
        )

    if bindings["state_root"] != (
        capsule[
            "release_binding"
        ]["consumption_state_root"]
    ):
        raise SystemExit(
            "STATE_ROOT_BINDING_INVALID"
        )

    if bindings["state_root"] != (
        reference[
            "bindings"
        ]["future_consumption_state_root"]
    ):
        raise SystemExit(
            "REFERENCE_STATE_ROOT_INVALID"
        )

    state_root = policy[
        "state_root_contract"
    ]

    require_true(
        state_root,
        "exact_path_required",
        "directory_required",
        "symlink_rejected",
        "root_owned_ancestry_required",
    )

    require_false(
        state_root,
        "arbitrary_state_root_allowed",
        "group_writable_ancestry_allowed",
        "world_writable_ancestry_allowed",
        "service_user_write_allowed",
    )

    if (
        state_root["owner"] != "root"
        or state_root["group"] != "root"
        or state_root["mode"] != "0700"
    ):
        raise SystemExit(
            "STATE_ROOT_CUSTODY_INVALID"
        )

    records = policy[
        "records_directory_contract"
    ]

    if records["exact_path"] != (
        bindings["records_root"]
    ):
        raise SystemExit(
            "RECORDS_ROOT_INVALID"
        )

    require_true(
        records,
        "directory_required",
        "symlink_rejected",
    )

    require_false(
        records,
        "unknown_entry_allowed",
        "automatic_unknown_entry_deletion_allowed",
    )

    lock = policy["lock_contract"]

    if lock["exact_path"] != (
        bindings["lock_path"]
    ):
        raise SystemExit(
            "LOCK_PATH_INVALID"
        )

    require_true(
        lock,
        "regular_file_required",
        "symlink_rejected",
        "open_no_follow_required",
        "exclusive_process_lock_required",
        "lock_must_cover_scan_and_publish",
        "lock_timeout_causes_rejection",
    )

    require_false(
        lock,
        "lock_bypass_allowed",
    )

    if lock[
        "hardlink_count_must_equal"
    ] != 1:
        raise SystemExit(
            "LOCK_NLINK_INVALID"
        )

    strategy = policy[
        "single_record_strategy"
    ]

    require_true(
        strategy,
        "one_record_contains_authorization_id_and_nonce",
        "global_locked_scan_enforces_authorization_id_uniqueness",
        "global_locked_scan_enforces_nonce_uniqueness",
        "pending_records_participate_in_uniqueness_scan",
        "final_records_participate_in_uniqueness_scan",
    )

    require_false(
        strategy,
        "separate_authorization_id_index_used",
        "separate_nonce_index_used",
        "multi_file_index_transaction_required",
    )

    naming = policy[
        "record_naming_contract"
    ]

    require_true(
        naming,
        "pending_name_contains_authorization_id",
        "pending_name_contains_nonce",
        "pending_name_contains_transaction_id",
        "final_name_contains_authorization_id",
    )

    require_false(
        naming,
        "arbitrary_filename_allowed",
    )

    document = policy[
        "record_document_contract"
    ]

    if document[
        "record_state_value"
    ] != "DURABLE_CONSUMED":
        raise SystemExit(
            "RECORD_STATE_INVALID"
        )

    if document[
        "operation_value"
    ] != "INSTALL_RELEASE_ONLY":
        raise SystemExit(
            "RECORD_OPERATION_INVALID"
        )

    if document[
        "release_id_value"
    ] != bindings["release_id"]:
        raise SystemExit(
            "RECORD_RELEASE_ID_INVALID"
        )

    if document[
        "reference_only_value"
    ] is not False:
        raise SystemExit(
            "REFERENCE_ONLY_STATE_INVALID"
        )

    creation = policy[
        "file_creation_contract"
    ]

    require_true(
        creation,
        "regular_file_required",
        "open_create_exclusive_required",
        "open_no_follow_required",
        "open_close_on_exec_required",
        "write_through_open_fd_required",
        "bounded_write_required",
        "short_write_handling_required",
        "file_fsync_required",
        "records_directory_fsync_required",
        "same_directory_atomic_rename_required",
    )

    require_false(
        creation,
        "cross_filesystem_rename_allowed",
    )

    point = policy[
        "consumption_point_contract"
    ]

    if point["consumption_point"] != (
        "FSYNC_RECORDS_DIRECTORY_"
        "CONSUMPTION_POINT"
    ):
        raise SystemExit(
            "CONSUMPTION_POINT_INVALID"
        )

    require_true(
        point,
        "pending_record_must_be_complete_before_consumption_point",
        "pending_record_must_be_fsynced_before_consumption_point",
        "records_directory_must_be_fsynced_at_consumption_point",
        "pending_record_reserves_authorization_id",
        "pending_record_reserves_nonce",
        "final_record_reserves_authorization_id",
        "final_record_reserves_nonce",
        "successful_consumption_is_irreversible",
    )

    recovery = policy[
        "crash_recovery_contract"
    ]

    require_true(
        recovery,
        "failure_after_consumption_requires_new_capsule",
    )

    require_false(
        recovery,
        "automatic_pending_record_deletion_allowed",
        "automatic_final_record_deletion_allowed",
        "consumption_record_deletion_for_retry_allowed",
    )

    expected_protocol = [
        "VALIDATE_STATE_ROOT_ANCESTRY",
        "OPEN_OR_CREATE_ROOT_LOCK_FILE",
        "ACQUIRE_EXCLUSIVE_PROCESS_LOCK",
        "VALIDATE_RECORDS_DIRECTORY_CUSTODY",
        "SCAN_ALL_PENDING_AND_FINAL_RECORDS",
        "REJECT_UNKNOWN_OR_MALFORMED_RECORDS",
        "REJECT_DUPLICATE_AUTHORIZATION_ID",
        "REJECT_DUPLICATE_NONCE",
        "CREATE_EXCLUSIVE_PENDING_RECORD",
        "WRITE_CANONICAL_RECORD_THROUGH_OPEN_FD",
        "FSYNC_PENDING_RECORD",
        "FSYNC_RECORDS_DIRECTORY_CONSUMPTION_POINT",
        "ATOMIC_RENAME_PENDING_TO_FINAL",
        "FSYNC_RECORDS_DIRECTORY_AFTER_RENAME",
        "RELEASE_EXCLUSIVE_PROCESS_LOCK",
    ]

    if policy[
        "ordered_protocol"
    ] != expected_protocol:
        raise SystemExit(
            "ORDERED_PROTOCOL_INVALID"
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
        "design_only"
    ] is not True:
        raise SystemExit(
            "DESIGN_ONLY_STATE_INVALID"
        )

    for key in (
        "host_change_executed",
        "capsule_issued",
        "capsule_file_created",
        "authorization_consumed_on_host",
        "host_consumption_record_created",
        "durable_writer_implemented",
        "durable_writer_installed",
        "state_root_created",
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
        "DURABLE_CONSUMPTION_RELEASE_BINDING: PASS"
    )
    print(
        "ROOT_STATE_CUSTODY_CONTRACT: PASS"
    )
    print(
        "SINGLE_RECORD_UNIQUENESS_STRATEGY: PASS"
    )
    print(
        "PENDING_RECORD_FAIL_CLOSED_CONTRACT: PASS"
    )
    print(
        "FSYNC_CONSUMPTION_POINT_CONTRACT: PASS"
    )
    print(
        "CRASH_RECOVERY_REQUIRES_NEW_CAPSULE: PASS"
    )
    print(
        "DURABLE_WRITER_IMPLEMENTED: FALSE"
    )
    print(
        "STATE_ROOT_CREATED: FALSE"
    )
    print(
        "HOST_CONSUMPTION_RECORD_CREATED: FALSE"
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
        "SQL_B2_4B_5G_3B_1D_2B_6_"
        "DURABLE_CONSUMPTION_CONTRACT: PASS"
    )


if __name__ == "__main__":
    validate()
