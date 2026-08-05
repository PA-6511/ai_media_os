from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_root_install_"
    "rollback_policy.json"
)

validator_path = (
    repo
    / "scripts/"
    "validate_slack_worker_root_"
    "install_rollback_contract.py"
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
        "SQL_B2_4B_5G_3B_1D_2B_1_"
        "ROOT_INSTALL_ROLLBACK_CONTRACT: PASS"
        in result.stdout
    )

    assert (
        "FINAL_DECISION: NO_GO"
        in result.stdout
    )


def test_single_use_authorization_required() -> None:
    authorization = load_policy()[
        "authorization_capsule_contract"
    ]

    assert authorization["required"] is True
    assert authorization[
        "issued_in_this_phase"
    ] is False
    assert authorization[
        "single_use_required"
    ] is True
    assert authorization[
        "consume_before_first_host_mutation"
    ] is True
    assert authorization[
        "reuse_after_failure_allowed"
    ] is False


def test_candidate_inputs_not_directly_trusted() -> None:
    custody = load_policy()[
        "input_custody_contract"
    ]

    assert custody[
        "repository_source_is_service_user_writable"
    ] is True

    assert custody[
        "temporary_wheelhouse_is_service_user_writable"
    ] is True

    assert custody[
        "direct_runtime_use_of_candidate_source_allowed"
    ] is False

    assert custody[
        "direct_pip_install_from_candidate_wheelhouse_allowed"
    ] is False

    assert custody[
        "root_private_staging_copy_required"
    ] is True


def test_install_publish_is_atomic() -> None:
    policy = load_policy()

    assert policy[
        "install_transaction"
    ]["commit_point"] == (
        "ATOMIC_RENAME_STAGING_TO_"
        "FINAL_RELEASE"
    )

    assert policy[
        "path_contract"
    ]["atomic_same_filesystem_rename_required"] is True

    assert policy[
        "path_contract"
    ]["cross_filesystem_publish_allowed"] is False


def test_install_does_not_activate() -> None:
    transaction = load_policy()[
        "install_transaction"
    ]

    assert transaction[
        "transaction_type"
    ] == "INSTALL_ONLY"

    assert transaction[
        "current_link_must_not_change"
    ] is True

    assert transaction[
        "current_link_creation_in_install_transaction_allowed"
    ] is False


def test_partial_install_not_blindly_deleted() -> None:
    policy = load_policy()

    assert policy[
        "partial_install_detection"
    ][
        "automatic_deletion_of_unknown_path_allowed"
    ] is False

    assert policy[
        "idempotency_contract"
    ]["blind_cleanup_allowed"] is False


def test_rollback_is_commit_point_aware() -> None:
    rollback = load_policy()[
        "rollback_contract"
    ]

    assert rollback[
        "before_commit_point"
    ][
        "remove_transaction_staging_directory"
    ] is True

    assert rollback[
        "before_commit_point"
    ]["change_current_link"] is False

    assert rollback[
        "at_or_after_commit_point"
    ][
        "automatic_final_release_deletion_allowed"
    ] is False

    assert rollback[
        "at_or_after_commit_point"
    ][
        "classify_as_installed_unactivated"
    ] is True


def test_activation_is_separate() -> None:
    activation = load_policy()[
        "activation_boundary_contract"
    ]

    assert activation[
        "activation_is_separate_transaction"
    ] is True

    assert activation[
        "activation_authorized_in_this_phase"
    ] is False

    assert activation[
        "activation_authorization_must_be_distinct_from_install_authorization"
    ] is True

    assert activation[
        "service_start_after_activation_allowed"
    ] is False


def test_root_helper_not_implemented() -> None:
    helper = load_policy()[
        "future_root_helper_contract"
    ]

    assert helper[
        "helper_required"
    ] is True

    assert helper[
        "helper_implemented_in_this_phase"
    ] is False

    assert helper[
        "arbitrary_command_execution_allowed"
    ] is False

    assert helper[
        "shell_evaluation_allowed"
    ] is False

    assert helper[
        "sudoers_rule_install_allowed_in_this_phase"
    ] is False


def test_service_operations_prohibited() -> None:
    guarantee = load_policy()[
        "non_start_guarantee"
    ]

    assert all(
        value is False
        for value in guarantee.values()
    )


def test_design_remains_no_go() -> None:
    governance = load_policy()[
        "governance"
    ]

    assert governance["design_only"] is True
    assert governance[
        "host_change_executed"
    ] is False
    assert governance[
        "root_release_install_authorized"
    ] is False
    assert governance[
        "authorization_capsule_issued"
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
