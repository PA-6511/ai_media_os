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
    "reconciliation_policy.json"
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
        "SQL-B2-4B-5G-3B-1D-2B-9"
    ):
        raise SystemExit(
            "POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_PENDING_RECONCILIATION_"
        "AUTHORIZATION_AND_DECISION_"
        "CONTRACT_DESIGN_ONLY_NO_HOST_STATE_NO_GO"
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
            "pending_recovery_correction_policy_path",
            "pending_recovery_correction_policy_sha256",
        ),
        (
            "durable_consumption_policy_path",
            "durable_consumption_policy_sha256",
        ),
        (
            "install_capsule_policy_path",
            "install_capsule_policy_sha256",
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

        loaded[path_key] = load_json(
            path
        )

    correction = loaded[
        "pending_recovery_correction_policy_path"
    ]

    durable = loaded[
        "durable_consumption_policy_path"
    ]

    capsule = loaded[
        "install_capsule_policy_path"
    ]

    root_policy = loaded[
        "root_install_policy_path"
    ]

    if correction["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-8"
    ):
        raise SystemExit(
            "CORRECTION_PHASE_INVALID"
        )

    if durable["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-6"
    ):
        raise SystemExit(
            "DURABLE_PHASE_INVALID"
        )

    if capsule["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-3"
    ):
        raise SystemExit(
            "CAPSULE_PHASE_INVALID"
        )

    if root_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-1"
    ):
        raise SystemExit(
            "ROOT_POLICY_PHASE_INVALID"
        )

    release_id = bindings[
        "release_id"
    ]

    for value in (
        correction["bindings"]["release_id"],
        durable["bindings"]["release_id"],
        capsule[
            "release_binding"
        ]["release_id"],
        root_policy[
            "release_binding"
        ]["release_id"],
    ):
        if value != release_id:
            raise SystemExit(
                "RELEASE_ID_BINDING_INVALID"
            )

    authorization = policy[
        "separate_authorization_contract"
    ]

    require_true(
        authorization,
        "required",
        "distinct_from_install_authorization",
        "root_owned_exact_path_required",
        "regular_file_required",
        "symlink_rejected",
        "single_use_required",
        "nonce_required",
        "expiration_required",
        "pending_filename_binding_required",
        "pending_sha256_binding_required",
        "authorization_id_binding_required",
        "nonce_binding_required",
        "transaction_id_binding_required",
        "release_id_binding_required",
    )

    require_false(
        authorization,
        "arbitrary_operation_allowed",
        "arbitrary_decision_allowed",
        "capsule_issued_in_this_phase",
        "capsule_consumed_in_this_phase",
    )

    if authorization[
        "operation"
    ] != (
        "RECONCILE_PENDING_"
        "AUTHORIZATION_RECORD"
    ):
        raise SystemExit(
            "RECONCILIATION_OPERATION_INVALID"
        )

    if set(
        authorization[
            "allowed_decisions"
        ]
    ) != {
        "KEEP_REPLAY_RESERVED",
        "AUTHORIZE_FINALIZE_AS_CONSUMED",
        "BLOCK_AND_ESCALATE",
    }:
        raise SystemExit(
            "ALLOWED_DECISIONS_INVALID"
        )

    if authorization[
        "maximum_validity_seconds"
    ] != 900:
        raise SystemExit(
            "AUTHORIZATION_LIFETIME_INVALID"
        )

    constraints = policy[
        "authorization_constraints"
    ]

    for key, value in (
        constraints.items()
    ):
        if value is not False:
            raise SystemExit(
                f"AUTHORIZATION_CONSTRAINT_INVALID: {key}"
            )

    semantics = policy[
        "decision_semantics"
    ]

    if set(semantics) != {
        "KEEP_REPLAY_RESERVED",
        "AUTHORIZE_FINALIZE_AS_CONSUMED",
        "BLOCK_AND_ESCALATE",
    }:
        raise SystemExit(
            "DECISION_SEMANTICS_INVALID"
        )

    for decision, values in (
        semantics.items()
    ):
        if values[
            "automatic_install_resume_allowed"
        ] is not False:
            raise SystemExit(
                "AUTOMATIC_INSTALL_RESUME_INVALID: "
                f"{decision}"
            )

        if values[
            "replay_reservation_preserved"
        ] is not True:
            raise SystemExit(
                "REPLAY_RESERVATION_INVALID: "
                f"{decision}"
            )

    if semantics[
        "AUTHORIZE_FINALIZE_AS_CONSUMED"
    ]["pending_delete_allowed"] is not False:
        raise SystemExit(
            "FINALIZE_DELETE_STATE_INVALID"
        )

    decision_record = policy[
        "human_decision_record_contract"
    ]

    require_true(
        decision_record,
        "required",
        "exact_root_required",
        "regular_file_required",
        "symlink_rejected",
        "create_exclusive_required",
        "immutable_after_creation_required",
        "canonical_json_required",
        "duplicate_json_keys_rejected",
        "authorization_binding_required",
        "pending_hash_binding_required",
        "related_install_state_required",
        "rationale_code_required",
        "file_fsync_required",
        "directory_fsync_required",
    )

    require_false(
        decision_record,
        "record_created_in_this_phase",
        "unknown_keys_allowed",
    )

    related_state = policy[
        "related_install_state_contract"
    ]

    if set(
        related_state["allowed_values"]
    ) != {
        "NO_RELEASE_TREE_MUTATION_OBSERVED",
        "PARTIAL_PRECOMMIT_INSTALL_OBSERVED",
        "INSTALLED_UNACTIVATED_OBSERVED",
        "UNKNOWN_REQUIRES_ESCALATION",
    }:
        raise SystemExit(
            "RELATED_INSTALL_STATE_VALUES_INVALID"
        )

    require_true(
        related_state,
        "repository_state_review_required",
        "release_tree_state_review_required",
        "current_link_state_review_required",
        "systemd_state_review_required",
        "production_database_state_review_required",
    )

    require_false(
        related_state,
        "secret_content_read_required",
        "slack_secret_content_read_allowed",
    )

    executor = policy[
        "future_executor_preconditions"
    ]

    require_true(
        executor,
        "exclusive_consumption_lock_required",
        "root_custody_revalidation_required",
        "pending_document_revalidation_required",
        "pending_filename_document_binding_required",
        "pending_sha256_revalidation_required",
        "reconciliation_authorization_validation_required",
        "reconciliation_authorization_consumption_required",
        "human_decision_record_commit_required_before_pending_mutation",
    )

    require_false(
        executor,
        "executor_implemented_in_this_phase",
        "executor_installed_in_this_phase",
        "automatic_pending_deletion_allowed",
        "automatic_install_resume_allowed",
    )

    failure = policy[
        "failure_contract"
    ]

    require_true(
        failure,
        "unknown_pending_state_blocks",
        "authorization_validation_failure_causes_no_pending_mutation",
        "decision_record_failure_causes_no_pending_mutation",
        "failure_after_reconciliation_authorization_consumption_requires_new_reconciliation_authorization",
    )

    require_false(
        failure,
        "decision_record_deletion_for_retry_allowed",
        "reconciliation_authorization_reuse_allowed",
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
        "reconciliation_authorization_issued",
        "reconciliation_authorization_consumed",
        "reconciliation_decision_record_created",
        "reconciliation_executor_implemented",
        "reconciliation_executor_installed",
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
        "SEPARATE_RECONCILIATION_AUTHORIZATION: PASS"
    )
    print(
        "PENDING_HASH_AND_IDENTITY_BINDING: PASS"
    )
    print(
        "HUMAN_DECISION_RECORD_CONTRACT: PASS"
    )
    print(
        "REPLAY_RESERVATION_PRESERVED: PASS"
    )
    print(
        "AUTOMATIC_INSTALL_RESUME_PROHIBITED: PASS"
    )
    print(
        "NEW_INSTALL_CAPSULE_REQUIRED: PASS"
    )
    print(
        "RECONCILIATION_AUTHORIZATION_ISSUED: FALSE"
    )
    print(
        "RECONCILIATION_DECISION_RECORD_CREATED: FALSE"
    )
    print(
        "RECONCILIATION_EXECUTOR_IMPLEMENTED: FALSE"
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
        "SQL_B2_4B_5G_3B_1D_2B_9_"
        "PENDING_RECONCILIATION_CONTRACT: PASS"
    )


if __name__ == "__main__":
    validate()
