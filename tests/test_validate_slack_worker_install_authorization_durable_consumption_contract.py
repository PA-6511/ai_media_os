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
    "authorization_durable_"
    "consumption_policy.json"
)

validator_path = (
    repo
    / "scripts/"
    "validate_slack_worker_install_"
    "authorization_durable_"
    "consumption_contract.py"
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
        "SQL_B2_4B_5G_3B_1D_2B_6_"
        "DURABLE_CONSUMPTION_CONTRACT: PASS"
        in result.stdout
    )

    assert (
        "FINAL_DECISION: NO_GO"
        in result.stdout
    )


def test_state_root_requires_root_custody() -> None:
    contract = load_policy()[
        "state_root_contract"
    ]

    assert contract["owner"] == "root"
    assert contract["group"] == "root"
    assert contract["mode"] == "0700"

    assert contract[
        "symlink_rejected"
    ] is True

    assert contract[
        "service_user_write_allowed"
    ] is False


def test_global_lock_covers_scan_and_publish() -> None:
    contract = load_policy()[
        "lock_contract"
    ]

    assert contract[
        "exclusive_process_lock_required"
    ] is True

    assert contract[
        "lock_must_cover_scan_and_publish"
    ] is True

    assert contract[
        "lock_bypass_allowed"
    ] is False


def test_single_record_avoids_split_indexes() -> None:
    strategy = load_policy()[
        "single_record_strategy"
    ]

    assert strategy[
        "separate_authorization_id_index_used"
    ] is False

    assert strategy[
        "separate_nonce_index_used"
    ] is False

    assert strategy[
        "one_record_contains_authorization_id_and_nonce"
    ] is True


def test_pending_record_reserves_both_ids() -> None:
    point = load_policy()[
        "consumption_point_contract"
    ]

    assert point[
        "pending_record_reserves_authorization_id"
    ] is True

    assert point[
        "pending_record_reserves_nonce"
    ] is True

    assert point[
        "successful_consumption_is_irreversible"
    ] is True


def test_consumption_point_requires_fsync() -> None:
    point = load_policy()[
        "consumption_point_contract"
    ]

    assert point[
        "pending_record_must_be_fsynced_before_consumption_point"
    ] is True

    assert point[
        "records_directory_must_be_fsynced_at_consumption_point"
    ] is True


def test_pending_crash_state_is_fail_closed() -> None:
    recovery = load_policy()[
        "crash_recovery_contract"
    ]

    assert recovery[
        "pending_record_after_consumption_point"
    ] == (
        "TREAT_AS_CONSUMED_AND_RECONCILE"
    )

    assert recovery[
        "automatic_pending_record_deletion_allowed"
    ] is False

    assert recovery[
        "failure_after_consumption_requires_new_capsule"
    ] is True


def test_unknown_or_malformed_state_blocks() -> None:
    recovery = load_policy()[
        "crash_recovery_contract"
    ]

    assert recovery[
        "malformed_pending_record"
    ] == (
        "BLOCK_ALL_NEW_CONSUMPTION_AND_REVIEW"
    )

    assert recovery[
        "unknown_record_entry"
    ] == (
        "BLOCK_ALL_NEW_CONSUMPTION_AND_REVIEW"
    )


def test_no_writer_or_host_state_is_created() -> None:
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
        "design_only"
    ] is True

    assert governance[
        "authorization_consumed_on_host"
    ] is False

    assert governance[
        "host_consumption_record_created"
    ] is False

    assert governance[
        "durable_writer_implemented"
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
