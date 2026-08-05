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
    "authorization_pending_"
    "recovery_correction_policy.json"
)

validator_path = (
    repo
    / "scripts/"
    "validate_slack_worker_install_"
    "authorization_pending_"
    "recovery_correction.py"
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
        "SQL_B2_4B_5G_3B_1D_2B_8_"
        "PENDING_RECOVERY_CORRECTION: PASS"
        in result.stdout
    )

    assert (
        "FINAL_DECISION: NO_GO"
        in result.stdout
    )


def test_directory_fsync_state_is_not_observable() -> None:
    reason = load_policy()[
        "correction_reason"
    ]

    assert reason[
        "directory_fsync_completion_persisted_as_record_field"
    ] is False

    assert reason[
        "directory_fsync_completion_derivable_from_recovered_namespace"
    ] is False

    assert reason[
        "pending_pre_and_post_consumption_point_distinguishable_after_crash"
    ] is False


def test_all_valid_pending_records_are_fail_closed() -> None:
    recovery = load_policy()[
        "authoritative_recovery_rule"
    ]

    assert recovery[
        "valid_pending_reserves_authorization_id"
    ] is True

    assert recovery[
        "valid_pending_reserves_nonce"
    ] is True

    assert recovery[
        "valid_pending_blocks_new_consumption"
    ] is True

    assert recovery[
        "valid_pending_blocks_same_capsule_retry"
    ] is True


def test_pending_record_is_not_automatically_deleted() -> None:
    recovery = load_policy()[
        "authoritative_recovery_rule"
    ]

    assert recovery[
        "valid_pending_automatic_delete_allowed"
    ] is False

    assert recovery[
        "valid_pending_automatic_finalize_allowed"
    ] is False

    assert recovery[
        "valid_pending_human_reconciliation_required"
    ] is True


def test_malformed_pending_blocks_all_consumption() -> None:
    recovery = load_policy()[
        "authoritative_recovery_rule"
    ]

    assert recovery[
        "malformed_pending_classification"
    ] == (
        "BLOCK_ALL_NEW_CONSUMPTION_"
        "AND_HUMAN_REVIEW"
    )

    assert recovery[
        "malformed_pending_automatic_delete_allowed"
    ] is False


def test_crash_matrix_disallows_automatic_retry() -> None:
    matrix = load_policy()[
        "crash_visibility_matrix"
    ]

    assert len(matrix) == 6

    assert all(
        item[
            "same_capsule_automatic_retry_allowed"
        ] is False
        for item in matrix
    )


def test_post_consumption_pending_requires_review() -> None:
    matrix = load_policy()[
        "crash_visibility_matrix"
    ]

    item = next(
        value
        for value in matrix
        if value["fault_point"] == (
            "AFTER_CONSUMPTION_POINT_"
            "BEFORE_RENAME"
        )
    )

    assert item[
        "classification"
    ] == (
        "REPLAY_RESERVED_"
        "CONSUMED_OR_UNCERTAIN"
    )

    assert item[
        "human_review_required"
    ] is True


def test_sandbox_behavior_is_aligned() -> None:
    alignment = load_policy()[
        "sandbox_alignment"
    ]

    assert alignment[
        "sandbox_pending_entry_blocks"
    ] is True

    assert alignment[
        "sandbox_pending_behavior_is_fail_closed"
    ] is True

    assert alignment[
        "sandbox_behavior_consistent_with_correction"
    ] is True


def test_no_host_recovery_handler_is_implemented() -> None:
    boundary = load_policy()[
        "implementation_boundary"
    ]

    assert all(
        value is False
        for value in boundary.values()
    )


def test_governance_remains_no_go() -> None:
    governance = load_policy()[
        "governance"
    ]

    assert governance[
        "design_correction_only"
    ] is True

    assert governance[
        "host_change_executed"
    ] is False

    assert governance[
        "authorization_consumed_on_host"
    ] is False

    assert governance[
        "root_release_install_authorized"
    ] is False

    assert governance[
        "root_release_install_executed"
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
