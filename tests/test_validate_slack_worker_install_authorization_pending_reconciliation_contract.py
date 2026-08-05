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
    "reconciliation_policy.json"
)

validator_path = (
    repo
    / "scripts/"
    "validate_slack_worker_install_"
    "authorization_pending_"
    "reconciliation_contract.py"
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
        "SQL_B2_4B_5G_3B_1D_2B_9_"
        "PENDING_RECONCILIATION_CONTRACT: PASS"
        in result.stdout
    )

    assert (
        "FINAL_DECISION: NO_GO"
        in result.stdout
    )


def test_reconciliation_uses_distinct_authorization() -> None:
    contract = load_policy()[
        "separate_authorization_contract"
    ]

    assert contract["required"] is True

    assert contract[
        "distinct_from_install_authorization"
    ] is True

    assert contract[
        "operation"
    ] == (
        "RECONCILE_PENDING_"
        "AUTHORIZATION_RECORD"
    )

    assert contract[
        "capsule_issued_in_this_phase"
    ] is False


def test_reconciliation_binds_pending_identity() -> None:
    contract = load_policy()[
        "separate_authorization_contract"
    ]

    assert contract[
        "pending_filename_binding_required"
    ] is True

    assert contract[
        "pending_sha256_binding_required"
    ] is True

    assert contract[
        "authorization_id_binding_required"
    ] is True

    assert contract[
        "nonce_binding_required"
    ] is True

    assert contract[
        "transaction_id_binding_required"
    ] is True


def test_no_decision_can_resume_install() -> None:
    semantics = load_policy()[
        "decision_semantics"
    ]

    assert all(
        values[
            "automatic_install_resume_allowed"
        ] is False
        for values in semantics.values()
    )


def test_replay_reservation_is_never_removed() -> None:
    semantics = load_policy()[
        "decision_semantics"
    ]

    assert all(
        values[
            "replay_reservation_preserved"
        ] is True
        for values in semantics.values()
    )


def test_finalize_does_not_delete_pending() -> None:
    semantics = load_policy()[
        "decision_semantics"
    ][
        "AUTHORIZE_FINALIZE_AS_CONSUMED"
    ]

    assert semantics[
        "pending_delete_allowed"
    ] is False

    assert semantics[
        "future_atomic_pending_to_final_allowed"
    ] is True

    assert semantics[
        "new_install_capsule_required_for_future_install"
    ] is True


def test_human_decision_record_is_immutable() -> None:
    record = load_policy()[
        "human_decision_record_contract"
    ]

    assert record["required"] is True

    assert record[
        "create_exclusive_required"
    ] is True

    assert record[
        "immutable_after_creation_required"
    ] is True

    assert record[
        "authorization_binding_required"
    ] is True

    assert record[
        "pending_hash_binding_required"
    ] is True


def test_secret_contents_are_not_required() -> None:
    state = load_policy()[
        "related_install_state_contract"
    ]

    assert state[
        "secret_content_read_required"
    ] is False

    assert state[
        "slack_secret_content_read_allowed"
    ] is False


def test_executor_requires_decision_before_mutation() -> None:
    executor = load_policy()[
        "future_executor_preconditions"
    ]

    assert executor[
        "human_decision_record_commit_required_before_pending_mutation"
    ] is True

    assert executor[
        "automatic_pending_deletion_allowed"
    ] is False

    assert executor[
        "automatic_install_resume_allowed"
    ] is False


def test_no_executor_or_host_state_is_created() -> None:
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
        "reconciliation_authorization_issued"
    ] is False

    assert governance[
        "reconciliation_decision_record_created"
    ] is False

    assert governance[
        "reconciliation_executor_implemented"
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
