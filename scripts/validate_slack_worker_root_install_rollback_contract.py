from __future__ import annotations

import hashlib
import json
from pathlib import Path


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_root_install_"
    "rollback_policy.json"
)

release_policy_path = (
    repo
    / "config/"
    "slack_worker_release_bundle_policy.json"
)

source_manifest_path = (
    repo
    / "config/"
    "slack_worker_release_source_manifest.json"
)

hash_lock_path = (
    repo
    / "config/"
    "slack_worker_release_"
    "requirements_hash_locked.txt"
)

dry_run_evidence_path = (
    repo
    / "exchange/logs/"
    "sql_b2_4b_5g_3b_1d_2a_"
    "release_bundle_dry_run_result.json"
)

preinstall_evidence_path = (
    repo
    / "exchange/logs/"
    "sql_b2_4b_5g_3b_1d_2b_0_"
    "host_preinstall_discovery_result.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def require_true(
    value: dict,
    *keys: str,
) -> None:
    for key in keys:
        if value.get(key) is not True:
            raise SystemExit(
                f"REQUIRED_TRUE_INVALID: {key}"
            )


def require_false(
    value: dict,
    *keys: str,
) -> None:
    for key in keys:
        if value.get(key) is not False:
            raise SystemExit(
                f"REQUIRED_FALSE_INVALID: {key}"
            )


def validate() -> None:
    policy = json.loads(
        policy_path.read_text(
            encoding="utf-8"
        )
    )

    release_policy = json.loads(
        release_policy_path.read_text(
            encoding="utf-8"
        )
    )

    source_manifest = json.loads(
        source_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    dry_run = json.loads(
        dry_run_evidence_path.read_text(
            encoding="utf-8"
        )
    )

    preinstall = json.loads(
        preinstall_evidence_path.read_text(
            encoding="utf-8"
        )
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-1"
    ):
        raise SystemExit(
            "POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_ROOT_RELEASE_INSTALL_"
        "ROLLBACK_CONTRACT_DESIGN_ONLY_"
        "NO_HOST_CHANGE_NO_GO"
    ):
        raise SystemExit(
            "POLICY_RESULT_INVALID"
        )

    if policy["schema_version"] != 1:
        raise SystemExit(
            "SCHEMA_VERSION_INVALID"
        )

    binding = policy[
        "release_binding"
    ]

    release_id = source_manifest[
        "release_id_candidate"
    ]

    if binding["release_id"] != release_id:
        raise SystemExit(
            "RELEASE_ID_BINDING_INVALID"
        )

    if binding[
        "final_release_path"
    ] != release_policy[
        "release_layout"
    ]["release_path_candidate"]:
        raise SystemExit(
            "FINAL_RELEASE_PATH_INVALID"
        )

    if binding[
        "final_release_path"
    ] != preinstall[
        "target_paths"
    ]["candidate_release_path"]:
        raise SystemExit(
            "PREINSTALL_PATH_BINDING_INVALID"
        )

    hash_bindings = (
        (
            "source_manifest_sha256",
            source_manifest_path,
        ),
        (
            "requirements_hash_lock_sha256",
            hash_lock_path,
        ),
        (
            "dry_run_evidence_sha256",
            dry_run_evidence_path,
        ),
        (
            "preinstall_evidence_sha256",
            preinstall_evidence_path,
        ),
    )

    for key, path in hash_bindings:
        if binding[key] != sha256(path):
            raise SystemExit(
                f"HASH_BINDING_INVALID: {key}"
            )

    if binding["source_file_count"] != 16:
        raise SystemExit(
            "SOURCE_FILE_COUNT_INVALID"
        )

    if binding["wheel_count"] != 5:
        raise SystemExit(
            "WHEEL_COUNT_INVALID"
        )

    if len(
        binding["wheel_hashes"]
    ) != 5:
        raise SystemExit(
            "WHEEL_HASH_COUNT_INVALID"
        )

    authorization = policy[
        "authorization_capsule_contract"
    ]

    require_true(
        authorization,
        "required",
        "regular_file_required",
        "symlink_rejected",
        "single_use_required",
        "nonce_required",
        "expiration_required",
        "exact_release_id_binding_required",
        "source_manifest_sha256_binding_required",
        "requirements_lock_sha256_binding_required",
        "wheel_hash_set_binding_required",
        "consume_before_first_host_mutation",
    )

    require_false(
        authorization,
        "issued_in_this_phase",
        "reuse_after_failure_allowed",
        "current_link_change_allowed",
        "secret_migration_allowed",
        "unit_change_allowed",
        "daemon_reload_allowed",
        "gate_creation_allowed",
        "service_start_allowed",
        "unit_enable_allowed",
        "production_database_write_allowed",
    )

    if authorization[
        "allowed_operation"
    ] != "INSTALL_RELEASE_ONLY":
        raise SystemExit(
            "AUTHORIZATION_OPERATION_INVALID"
        )

    custody = policy[
        "input_custody_contract"
    ]

    require_true(
        custody,
        "repository_source_is_service_user_writable",
        "temporary_wheelhouse_is_service_user_writable",
        "root_private_staging_copy_required",
        "source_open_no_follow_required",
        "wheel_open_no_follow_required",
        "regular_file_validation_required",
        "copy_then_sha256_validation_required",
        "staged_source_manifest_validation_required",
        "staged_wheel_exact_set_validation_required",
        "staged_wheel_sha256_validation_required",
        "root_private_wheelhouse_required",
        "pip_no_index_required",
        "pip_no_deps_required",
        "pip_require_hashes_required",
    )

    require_false(
        custody,
        "direct_runtime_use_of_candidate_source_allowed",
        "direct_pip_install_from_candidate_wheelhouse_allowed",
        "pip_network_access_allowed",
    )

    transaction = policy[
        "install_transaction"
    ]

    if transaction[
        "transaction_type"
    ] != "INSTALL_ONLY":
        raise SystemExit(
            "TRANSACTION_TYPE_INVALID"
        )

    require_true(
        transaction,
        "current_link_must_not_change",
        "service_state_must_remain_inactive",
        "unit_file_state_must_remain_disabled",
        "autostart_gate_must_remain_absent",
    )

    require_false(
        transaction,
        "current_link_creation_in_install_transaction_allowed",
        "secret_copy_in_install_transaction_allowed",
        "systemd_operation_in_install_transaction_allowed",
    )

    if transaction[
        "commit_point"
    ] != (
        "ATOMIC_RENAME_STAGING_TO_"
        "FINAL_RELEASE"
    ):
        raise SystemExit(
            "COMMIT_POINT_INVALID"
        )

    if len(
        transaction["ordered_stages"]
    ) != 17:
        raise SystemExit(
            "INSTALL_STAGE_COUNT_INVALID"
        )

    paths = policy["path_contract"]

    require_true(
        paths,
        "staging_must_be_direct_child_of_release_root",
        "atomic_same_filesystem_rename_required",
    )

    require_false(
        paths,
        "final_tree_group_writable_allowed",
        "final_tree_world_writable_allowed",
        "final_tree_unapproved_symlink_allowed",
        "cross_filesystem_publish_allowed",
    )

    idempotency = policy[
        "idempotency_contract"
    ]

    require_true(
        idempotency,
        "exclusive_lock_required",
        "final_release_absent_before_new_install_required",
        "matching_existing_release_may_be_treated_as_success",
    )

    require_false(
        idempotency,
        "mismatching_existing_release_overwrite_allowed",
        "staging_directory_collision_allowed",
        "authorization_nonce_reuse_allowed",
        "blind_cleanup_allowed",
    )

    partial = policy[
        "partial_install_detection"
    ]

    if partial[
        "automatic_deletion_of_unknown_path_allowed"
    ] is not False:
        raise SystemExit(
            "UNKNOWN_PATH_CLEANUP_INVALID"
        )

    rollback = policy[
        "rollback_contract"
    ]

    require_true(
        rollback,
        "cleanup_requires_exact_transaction_binding",
        "cleanup_requires_separate_authorization",
        "rollback_must_not_touch_other_releases",
    )

    require_true(
        rollback["before_commit_point"],
        "remove_transaction_staging_directory",
    )

    require_false(
        rollback["before_commit_point"],
        "remove_final_release",
        "change_current_link",
        "service_operation_allowed",
    )

    require_true(
        rollback["at_or_after_commit_point"],
        "classify_as_installed_unactivated",
        "postcommit_reconciliation_required_on_error",
        "current_link_remains_unchanged",
    )

    require_false(
        rollback["at_or_after_commit_point"],
        "automatic_final_release_deletion_allowed",
        "service_operation_allowed",
    )

    activation = policy[
        "activation_boundary_contract"
    ]

    require_true(
        activation,
        "activation_is_separate_transaction",
        "activation_authorization_must_be_distinct_from_install_authorization",
        "release_reverification_before_activation_required",
        "previous_current_target_record_required",
        "temporary_link_in_same_directory_required",
        "atomic_link_replacement_required",
        "target_must_be_direct_child_of_release_root",
        "target_must_be_root_owned",
        "target_must_not_be_service_user_writable",
        "post_activation_verification_required",
        "atomic_previous_target_restore_required_on_failure",
        "remove_current_if_no_previous_target_required_on_failure",
    )

    require_false(
        activation,
        "activation_authorized_in_this_phase",
        "service_start_after_activation_allowed",
        "unit_enable_after_activation_allowed",
    )

    helper = policy[
        "future_root_helper_contract"
    ]

    require_true(
        helper,
        "helper_required",
        "release_id_must_match_contract",
        "authorization_capsule_required",
    )

    require_false(
        helper,
        "helper_implemented_in_this_phase",
        "service_user_write_allowed",
        "arbitrary_command_execution_allowed",
        "shell_evaluation_allowed",
        "arbitrary_source_path_argument_allowed",
        "arbitrary_target_path_argument_allowed",
        "direct_interactive_sudo_in_automation_allowed",
        "sudoers_rule_install_allowed_in_this_phase",
    )

    require_false(
        policy["non_start_guarantee"],
        "systemctl_start_allowed",
        "systemctl_restart_allowed",
        "systemctl_try_restart_allowed",
        "systemctl_enable_allowed",
        "systemctl_enable_now_allowed",
        "systemctl_daemon_reload_allowed",
        "unit_file_write_allowed",
        "autostart_gate_creation_allowed",
        "secret_file_migration_allowed",
        "production_database_write_allowed",
    )

    governance = policy[
        "governance"
    ]

    require_true(
        governance,
        "design_only",
    )

    require_false(
        governance,
        "host_change_executed",
        "root_release_install_executed",
        "root_release_install_authorized",
        "authorization_capsule_issued",
        "future_root_helper_installed",
        "root_ownership_applied",
        "current_host_link_created",
        "secret_migration_executed",
        "unit_change_executed",
        "daemon_reload_executed",
        "gate_creation_executed",
        "service_start_executed",
        "unit_enable_executed",
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

    if dry_run[
        "decision"
    ]["final_decision"] != "NO_GO":
        raise SystemExit(
            "DRY_RUN_DECISION_INVALID"
        )

    if preinstall[
        "decision"
    ]["root_release_install_authorized"] is not False:
        raise SystemExit(
            "PREINSTALL_AUTHORIZATION_INVALID"
        )

    print(
        "ROOT_INSTALL_RELEASE_BINDING: PASS"
    )
    print(
        "SINGLE_USE_AUTHORIZATION_CONTRACT: PASS"
    )
    print(
        "ROOT_INPUT_CUSTODY_CONTRACT: PASS"
    )
    print(
        "ATOMIC_INSTALL_TRANSACTION: PASS"
    )
    print(
        "IDEMPOTENCY_AND_PARTIAL_DETECTION: PASS"
    )
    print(
        "ROLLBACK_BOUNDARY_CONTRACT: PASS"
    )
    print(
        "SEPARATE_ACTIVATION_BOUNDARY: PASS"
    )
    print(
        "FUTURE_ROOT_HELPER_BOUNDARY: PASS"
    )
    print(
        "SERVICE_NON_START_GUARANTEE: PASS"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "AUTHORIZATION_CAPSULE_ISSUED: FALSE"
    )
    print(
        "FUTURE_ROOT_HELPER_INSTALLED: FALSE"
    )
    print(
        "SERVICE_START_EXECUTED: FALSE"
    )
    print(
        "UNIT_ENABLE_EXECUTED: FALSE"
    )
    print("FINAL_DECISION: NO_GO")
    print(
        "SQL_B2_4B_5G_3B_1D_2B_1_"
        "ROOT_INSTALL_ROLLBACK_CONTRACT: PASS"
    )


if __name__ == "__main__":
    validate()
