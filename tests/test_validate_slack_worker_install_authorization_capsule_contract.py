from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_capsule_policy.json"
)

validator_path = (
    repo
    / "scripts/"
    "validate_slack_worker_install_"
    "authorization_capsule_contract.py"
)


def load_policy() -> dict:
    return json.loads(
        policy_path.read_text(
            encoding="utf-8"
        )
    )


def test_validator_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(validator_path),
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout
    )

    assert (
        "SQL_B2_4B_5G_3B_1D_2B_3_"
        "AUTHORIZATION_CAPSULE_CONTRACT: PASS"
        in result.stdout
    )

    assert (
        "FINAL_DECISION: NO_GO"
        in result.stdout
    )


def test_capsule_file_requires_root_custody() -> None:
    contract = load_policy()[
        "capsule_file_contract"
    ]

    assert contract[
        "exact_path_required"
    ] is True

    assert contract["owner"] == "root"
    assert contract["group"] == "root"
    assert contract["mode"] == "0600"

    assert contract[
        "regular_file_required"
    ] is True

    assert contract[
        "symlink_rejected"
    ] is True

    assert contract[
        "hardlink_count_must_equal"
    ] == 1


def test_capsule_uses_nofollow_fd_validation() -> None:
    contract = load_policy()[
        "capsule_file_contract"
    ]

    assert contract[
        "open_no_follow_required"
    ] is True

    assert contract[
        "lstat_before_open_required"
    ] is True

    assert contract[
        "fstat_after_open_required"
    ] is True

    assert contract[
        "same_inode_before_after_open_required"
    ] is True

    assert contract[
        "read_from_open_file_descriptor_required"
    ] is True

    assert contract[
        "path_reread_after_validation_allowed"
    ] is False


def test_document_has_exact_operation_and_keys() -> None:
    document = load_policy()[
        "capsule_document_contract"
    ]

    assert document[
        "unknown_top_level_keys_allowed"
    ] is False

    assert document[
        "duplicate_json_keys_rejected"
    ] is True

    assert document[
        "operation_value"
    ] == "INSTALL_RELEASE_ONLY"

    assert document[
        "issuer_uid_value"
    ] == 0

    assert document[
        "trust_anchor"
    ] == (
        "ROOT_OWNED_EXACT_PATH_FILE_CUSTODY"
    )


def test_temporal_window_is_bounded() -> None:
    temporal = load_policy()[
        "temporal_contract"
    ]

    assert temporal[
        "maximum_validity_seconds"
    ] == 900

    assert temporal[
        "expired_capsule_rejected"
    ] is True

    assert temporal[
        "not_yet_valid_capsule_rejected"
    ] is True

    assert temporal[
        "lifetime_exceeding_maximum_rejected"
    ] is True

    assert temporal["utc_required"] is True


def test_constraints_prohibit_activation_and_start() -> None:
    constraints = load_policy()[
        "expected_constraints"
    ]

    assert constraints[
        "install_release_only"
    ] is True

    for key in (
        "current_link_change_allowed",
        "secret_migration_allowed",
        "unit_change_allowed",
        "daemon_reload_allowed",
        "gate_creation_allowed",
        "service_start_allowed",
        "unit_enable_allowed",
        "production_database_write_allowed",
    ):
        assert constraints[key] is False


def test_consumption_is_single_use() -> None:
    consumption = load_policy()[
        "consumption_contract"
    ]

    assert consumption[
        "single_use_required"
    ] is True

    assert consumption[
        "consumption_record_create_exclusive_required"
    ] is True

    assert consumption[
        "authorization_id_index_required"
    ] is True

    assert consumption[
        "nonce_index_required"
    ] is True

    assert consumption[
        "capsule_reuse_allowed"
    ] is False

    assert consumption[
        "nonce_reuse_allowed"
    ] is False


def test_consumption_precedes_release_mutation() -> None:
    consumption = load_policy()[
        "consumption_contract"
    ]

    assert consumption[
        "consumption_control_plane_mutation"
    ] is True

    assert consumption[
        "must_precede_all_release_tree_mutations"
    ] is True

    assert consumption[
        "must_precede_current_link_mutation"
    ] is True

    assert consumption[
        "must_precede_secret_mutation"
    ] is True

    assert consumption[
        "must_precede_unit_mutation"
    ] is True

    assert consumption[
        "must_precede_database_mutation"
    ] is True


def test_failure_after_consumption_needs_new_capsule() -> None:
    failure = load_policy()[
        "failure_contract"
    ]

    assert failure[
        "failure_after_successful_consumption_requires_new_capsule"
    ] is True

    assert failure[
        "consumption_record_deletion_for_retry_allowed"
    ] is False

    assert failure[
        "automatic_expiration_extension_allowed"
    ] is False


def test_no_capsule_is_issued_by_this_phase() -> None:
    issuance = load_policy()[
        "issuance_boundary"
    ]

    assert issuance[
        "capsule_issued_in_this_phase"
    ] is False

    assert issuance[
        "capsule_file_created_in_this_phase"
    ] is False

    assert issuance[
        "issuer_tool_implemented_in_this_phase"
    ] is False

    assert issuance[
        "root_helper_implemented_in_this_phase"
    ] is False


def test_repository_contract_cannot_authorize_install() -> None:
    guarantee = load_policy()[
        "non_authorization_guarantee"
    ]

    assert guarantee[
        "contract_file_is_authorization"
    ] is False

    assert guarantee[
        "repository_file_can_authorize_root_install"
    ] is False

    assert guarantee[
        "root_release_install_allowed"
    ] is False

    assert guarantee[
        "host_mutation_allowed"
    ] is False


def test_governance_remains_no_go() -> None:
    governance = load_policy()[
        "governance"
    ]

    assert governance[
        "design_only"
    ] is True

    assert governance[
        "capsule_issued"
    ] is False

    assert governance[
        "authorization_consumed"
    ] is False

    assert governance[
        "root_release_install_authorized"
    ] is False

    assert governance[
        "root_release_install_executed"
    ] is False

    assert governance[
        "root_helper_installed"
    ] is False

    assert governance[
        "service_start_executed"
    ] is False

    assert governance[
        "unit_enable_executed"
    ] is False

    assert governance[
        "final_decision"
    ] == "NO_GO"
