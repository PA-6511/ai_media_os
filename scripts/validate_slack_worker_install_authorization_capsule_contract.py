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
    "authorization_capsule_policy.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        payload
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
        "SQL-B2-4B-5G-3B-1D-2B-3"
    ):
        raise SystemExit(
            "POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_INSTALL_AUTHORIZATION_"
        "CAPSULE_CONTRACT_DESIGN_ONLY_"
        "NOT_ISSUED_NO_GO"
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

    path_hash_pairs = (
        (
            "root_install_policy_path",
            "root_install_policy_sha256",
        ),
        (
            "root_helper_interface_policy_path",
            "root_helper_interface_policy_sha256",
        ),
        (
            "source_manifest_path",
            "source_manifest_sha256",
        ),
        (
            "requirements_hash_lock_path",
            "requirements_hash_lock_sha256",
        ),
        (
            "preinstall_evidence_path",
            "preinstall_evidence_sha256",
        ),
    )

    loaded: dict[str, dict[str, Any]] = {}

    for path_key, hash_key in path_hash_pairs:
        path = repository_path(
            binding[path_key]
        )

        if not path.is_file():
            raise SystemExit(
                f"BOUND_INPUT_MISSING: {path_key}"
            )

        if sha256(path) != binding[
            hash_key
        ]:
            raise SystemExit(
                f"BOUND_INPUT_HASH_INVALID: "
                f"{hash_key}"
            )

        if path.suffix == ".json":
            loaded[path_key] = load_json(
                path
            )

    root_policy = loaded[
        "root_install_policy_path"
    ]

    interface_policy = loaded[
        "root_helper_interface_policy_path"
    ]

    source_manifest = loaded[
        "source_manifest_path"
    ]

    preinstall = loaded[
        "preinstall_evidence_path"
    ]

    root_binding = root_policy[
        "release_binding"
    ]

    root_authorization = root_policy[
        "authorization_capsule_contract"
    ]

    if binding["release_id"] != (
        root_binding["release_id"]
    ):
        raise SystemExit(
            "ROOT_RELEASE_ID_BINDING_INVALID"
        )

    if binding["release_id"] != (
        source_manifest[
            "release_id_candidate"
        ]
    ):
        raise SystemExit(
            "SOURCE_RELEASE_ID_BINDING_INVALID"
        )

    if binding[
        "final_release_path"
    ] != root_binding[
        "final_release_path"
    ]:
        raise SystemExit(
            "FINAL_RELEASE_PATH_INVALID"
        )

    if binding[
        "final_release_path"
    ] != preinstall[
        "target_paths"
    ]["candidate_release_path"]:
        raise SystemExit(
            "PREINSTALL_PATH_INVALID"
        )

    if binding["capsule_path"] != (
        root_authorization[
            "candidate_path"
        ]
    ):
        raise SystemExit(
            "CAPSULE_PATH_BINDING_INVALID"
        )

    if binding[
        "consumption_state_root"
    ] != root_authorization[
        "consumption_state_root"
    ]:
        raise SystemExit(
            "CONSUMPTION_ROOT_BINDING_INVALID"
        )

    wheel_hashes = root_binding[
        "wheel_hashes"
    ]

    if len(wheel_hashes) != 5:
        raise SystemExit(
            "WHEEL_HASH_COUNT_INVALID"
        )

    if binding[
        "wheel_hash_set_sha256"
    ] != canonical_sha256(
        wheel_hashes
    ):
        raise SystemExit(
            "WHEEL_HASH_SET_BINDING_INVALID"
        )

    if interface_policy[
        "plan_contract"
    ]["execution_allowed"] is not False:
        raise SystemExit(
            "INTERFACE_EXECUTION_STATE_INVALID"
        )

    file_contract = policy[
        "capsule_file_contract"
    ]

    require_true(
        file_contract,
        "exact_path_required",
        "regular_file_required",
        "symlink_rejected",
        "open_no_follow_required",
        "open_close_on_exec_required",
        "lstat_before_open_required",
        "fstat_after_open_required",
        "same_inode_before_after_open_required",
        "read_from_open_file_descriptor_required",
    )

    require_false(
        file_contract,
        "arbitrary_capsule_path_allowed",
        "path_reread_after_validation_allowed",
    )

    if file_contract["owner"] != "root":
        raise SystemExit(
            "CAPSULE_OWNER_INVALID"
        )

    if file_contract["group"] != "root":
        raise SystemExit(
            "CAPSULE_GROUP_INVALID"
        )

    if file_contract["mode"] != "0600":
        raise SystemExit(
            "CAPSULE_MODE_INVALID"
        )

    if file_contract[
        "hardlink_count_must_equal"
    ] != 1:
        raise SystemExit(
            "CAPSULE_NLINK_INVALID"
        )

    document = policy[
        "capsule_document_contract"
    ]

    require_true(
        document,
        "json_object_required",
        "duplicate_json_keys_rejected",
        "rfc3339_utc_z_required",
        "canonical_json_required_for_state_hash",
    )

    require_false(
        document,
        "unknown_top_level_keys_allowed",
        "cryptographic_signature_required",
    )

    expected_top_keys = {
        "schema_version",
        "authorization_id",
        "operation",
        "release_id",
        "issued_at",
        "expires_at",
        "nonce",
        "issuer",
        "bindings",
        "constraints",
    }

    if set(
        document["top_level_keys"]
    ) != expected_top_keys:
        raise SystemExit(
            "CAPSULE_TOP_LEVEL_KEYS_INVALID"
        )

    if document[
        "operation_value"
    ] != "INSTALL_RELEASE_ONLY":
        raise SystemExit(
            "CAPSULE_OPERATION_INVALID"
        )

    if document[
        "release_id_value"
    ] != binding["release_id"]:
        raise SystemExit(
            "CAPSULE_RELEASE_ID_INVALID"
        )

    if document[
        "issuer_kind_value"
    ] != "HUMAN_ROOT_OPERATOR":
        raise SystemExit(
            "CAPSULE_ISSUER_KIND_INVALID"
        )

    if document[
        "issuer_uid_value"
    ] != 0:
        raise SystemExit(
            "CAPSULE_ISSUER_UID_INVALID"
        )

    if document["trust_anchor"] != (
        "ROOT_OWNED_EXACT_PATH_FILE_CUSTODY"
    ):
        raise SystemExit(
            "CAPSULE_TRUST_ANCHOR_INVALID"
        )

    expected_bindings = policy[
        "expected_bindings"
    ]

    if expected_bindings[
        "wheel_hash_set_sha256"
    ] != binding[
        "wheel_hash_set_sha256"
    ]:
        raise SystemExit(
            "EXPECTED_WHEEL_BINDING_INVALID"
        )

    if expected_bindings[
        "final_release_path"
    ] != binding[
        "final_release_path"
    ]:
        raise SystemExit(
            "EXPECTED_PATH_BINDING_INVALID"
        )

    constraints = policy[
        "expected_constraints"
    ]

    if constraints[
        "install_release_only"
    ] is not True:
        raise SystemExit(
            "INSTALL_ONLY_CONSTRAINT_INVALID"
        )

    require_false(
        constraints,
        "current_link_change_allowed",
        "secret_migration_allowed",
        "unit_change_allowed",
        "daemon_reload_allowed",
        "gate_creation_allowed",
        "service_start_allowed",
        "unit_enable_allowed",
        "production_database_write_allowed",
    )

    temporal = policy[
        "temporal_contract"
    ]

    if temporal[
        "maximum_validity_seconds"
    ] != 900:
        raise SystemExit(
            "MAXIMUM_VALIDITY_INVALID"
        )

    require_true(
        temporal,
        "expired_capsule_rejected",
        "not_yet_valid_capsule_rejected",
        "lifetime_exceeding_maximum_rejected",
        "utc_required",
        "wall_clock_checked_before_consumption",
        "wall_clock_rechecked_immediately_before_consumption",
    )

    identity = policy[
        "identity_contract"
    ]

    require_true(
        identity,
        "authorization_id_unique_required",
        "nonce_unique_required",
        "authorization_id_and_nonce_must_differ",
        "release_id_exact_match_required",
        "operation_exact_match_required",
        "all_bindings_exact_match_required",
        "all_constraints_exact_match_required",
    )

    sequence = policy[
        "verification_sequence"
    ]

    if sequence[-3:] != [
        "ATOMically_RECORD_AUTHORIZATION_CONSUMPTION",
        "FSYNC_CONSUMPTION_RECORD_AND_DIRECTORY",
        "BEGIN_BOUND_INSTALL_TRANSACTION",
    ]:
        raise SystemExit(
            "CONSUMPTION_SEQUENCE_INVALID"
        )

    consumption = policy[
        "consumption_contract"
    ]

    require_true(
        consumption,
        "single_use_required",
        "consumption_record_required",
        "consumption_record_regular_file_required",
        "consumption_record_symlink_rejected",
        "consumption_record_create_exclusive_required",
        "authorization_id_index_required",
        "nonce_index_required",
        "capsule_sha256_record_required",
        "canonical_document_sha256_record_required",
        "release_id_record_required",
        "consumed_at_record_required",
        "atomic_record_creation_required",
        "record_fsync_required",
        "directory_fsync_required",
        "consumption_control_plane_mutation",
        "must_precede_all_release_tree_mutations",
        "must_precede_current_link_mutation",
        "must_precede_secret_mutation",
        "must_precede_unit_mutation",
        "must_precede_database_mutation",
    )

    require_false(
        consumption,
        "capsule_reuse_allowed",
        "nonce_reuse_allowed",
        "authorization_id_reuse_allowed",
    )

    failure = policy[
        "failure_contract"
    ]

    require_true(
        failure,
        "validation_failure_causes_no_host_mutation",
        "consumption_failure_causes_no_release_tree_mutation",
        "failure_after_successful_consumption_requires_new_capsule",
        "unknown_consumption_state_requires_human_review",
    )

    require_false(
        failure,
        "consumption_record_deletion_for_retry_allowed",
        "automatic_capsule_rewrite_allowed",
        "automatic_expiration_extension_allowed",
    )

    issuance = policy[
        "issuance_boundary"
    ]

    require_true(
        issuance,
        "authorization_requires_separate_future_human_action",
    )

    require_false(
        issuance,
        "capsule_issued_in_this_phase",
        "capsule_file_created_in_this_phase",
        "issuer_tool_implemented_in_this_phase",
        "issuer_tool_installed_in_this_phase",
        "root_helper_implemented_in_this_phase",
        "root_helper_installed_in_this_phase",
        "sudoers_rule_installed_in_this_phase",
    )

    guarantee = policy[
        "non_authorization_guarantee"
    ]

    require_false(
        guarantee,
        "contract_file_is_authorization",
        "report_file_is_authorization",
        "test_file_is_authorization",
        "validator_file_is_authorization",
        "repository_file_can_authorize_root_install",
        "root_release_install_allowed",
        "host_mutation_allowed",
        "current_link_change_allowed",
        "secret_migration_allowed",
        "unit_change_allowed",
        "daemon_reload_allowed",
        "gate_creation_allowed",
        "service_start_allowed",
        "unit_enable_allowed",
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
        "capsule_issued",
        "capsule_file_created",
        "authorization_consumed",
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
        "AUTHORIZATION_CAPSULE_RELEASE_BINDING: PASS"
    )
    print(
        "ROOT_FILE_CUSTODY_CONTRACT: PASS"
    )
    print(
        "EXACT_CAPSULE_DOCUMENT_CONTRACT: PASS"
    )
    print(
        "TEMPORAL_AND_NONCE_CONTRACT: PASS"
    )
    print(
        "SINGLE_USE_CONSUMPTION_CONTRACT: PASS"
    )
    print(
        "CONSUMPTION_BEFORE_RELEASE_MUTATION: PASS"
    )
    print(
        "FAILURE_REQUIRES_NEW_CAPSULE: PASS"
    )
    print(
        "CAPSULE_ISSUED: FALSE"
    )
    print(
        "AUTHORIZATION_CONSUMED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "ROOT_HELPER_IMPLEMENTED: FALSE"
    )
    print(
        "ROOT_HELPER_INSTALLED: FALSE"
    )
    print(
        "SERVICE_START_EXECUTED: FALSE"
    )
    print(
        "UNIT_ENABLE_EXECUTED: FALSE"
    )
    print("FINAL_DECISION: NO_GO")
    print(
        "SQL_B2_4B_5G_3B_1D_2B_3_"
        "AUTHORIZATION_CAPSULE_CONTRACT: PASS"
    )


if __name__ == "__main__":
    validate()
