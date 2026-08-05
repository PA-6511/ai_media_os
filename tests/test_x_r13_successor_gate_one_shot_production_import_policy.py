from __future__ import annotations

import copy
import json
import os
import sqlite3
from pathlib import Path

import pytest

from scripts import run_x_r13_one_shot_production_import as runner
from scripts.build_x_r9_preflight_approval_pack import canonical_digest


REPO = Path(
    os.environ.get(
        "AI_MEDIA_OS_REPO",
        ".",
    )
).resolve()

POLICY_PATH = Path(
    os.environ.get(
        "X_R13_SUCCESSOR_POLICY_PATH",
        str(
            REPO
            / "config"
            / "x_r13_successor_gate_one_shot_production_import_policy.json"
        ),
    )
).resolve()

SUCCESSOR_GATE_PATH = (
    REPO
    / "exchange"
    / "diagnostics"
    / "x_draft_module"
    / "x_r13_formal_production_import_gate_reconciliation"
    / "4310000887411"
    / "x_r13_reconciled_production_import_gate.json"
)

PREDECESSOR_GATE_PATH = (
    REPO
    / "exchange"
    / "diagnostics"
    / "x_draft_module"
    / "x_r13_production_import_approval_gate_prep"
    / "4310000887411"
    / "x_r13_production_import_approval_gate.json"
)

SUCCESSOR_DIGEST_FIELD = 'x_r13_reconciled_production_import_gate_digest_sha256'
SUCCESSOR_DIGEST = 'eea4347b90722c7ee405f21fb0443aae1c11406943267f373d85323d18303c1c'
SUCCESSOR_STATUS = 'READY_X_R13_MEDALIST_15_RECONCILED_PRODUCTION_IMPORT_GATE_CLOSED_PENDING_POST_RECONCILIATION_HUMAN_REVIEW'
SUCCESSOR_GATE_STATE = 'RECONCILED_CLOSED_PENDING_POST_RECONCILIATION_HUMAN_REVIEW'


def load_json(path: Path) -> dict:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert isinstance(value, dict)
    return value


def load_policy() -> dict:
    return load_json(POLICY_PATH)


def load_successor_gate() -> dict:
    return load_json(SUCCESSOR_GATE_PATH)


def recompute_gate_digest(
    gate: dict,
) -> None:
    payload = {
        key: value
        for key, value in gate.items()
        if key != SUCCESSOR_DIGEST_FIELD
    }

    gate[SUCCESSOR_DIGEST_FIELD] = (
        canonical_digest(payload)
    )


def test_successor_policy_canonical_digest_valid() -> None:
    policy = load_policy()

    recorded = policy["policy_digest_sha256"]

    payload = {
        key: value
        for key, value in policy.items()
        if key != "policy_digest_sha256"
    }

    assert canonical_digest(payload) == recorded

    assert (
        policy["source_binding"][
            "production_import_gate_digest_sha256"
        ]
        == SUCCESSOR_DIGEST
    )

    assert (
        policy["runtime_contract"][
            "gate_digest_field"
        ]
        == SUCCESSOR_DIGEST_FIELD
    )

    assert (
        policy["runtime_contract"][
            "required_gate_status"
        ]
        == SUCCESSOR_STATUS
    )

    assert (
        policy["runtime_contract"][
            "required_gate_state"
        ]
        == SUCCESSOR_GATE_STATE
    )

    runner.validate_policy(policy)


def test_successor_gate_validate_gate_passes() -> None:
    policy = load_policy()
    gate = load_successor_gate()

    runner.validate_policy(policy)
    runner.validate_gate(gate, policy)


def test_predecessor_gate_rejected_by_successor_policy() -> None:
    policy = load_policy()
    predecessor = load_json(
        PREDECESSOR_GATE_PATH
    )

    with pytest.raises(runner.RunnerError):
        runner.validate_gate(
            predecessor,
            policy,
        )


def test_successor_gate_digest_tamper_rejected() -> None:
    policy = load_policy()
    gate = load_successor_gate()

    gate["candidate"]["display_title"] = (
        "TAMPERED"
    )

    with pytest.raises(runner.RunnerError):
        runner.validate_gate(gate, policy)


def test_successor_gate_status_mismatch_rejected() -> None:
    policy = load_policy()
    gate = load_successor_gate()

    gate["status"] = "UNEXPECTED_STATUS"
    recompute_gate_digest(gate)

    with pytest.raises(runner.RunnerError):
        runner.validate_gate(gate, policy)


def test_successor_gate_state_mismatch_rejected() -> None:
    policy = load_policy()
    gate = load_successor_gate()

    gate["gate_state"] = "UNEXPECTED_GATE_STATE"
    recompute_gate_digest(gate)

    with pytest.raises(runner.RunnerError):
        runner.validate_gate(gate, policy)


def test_successor_gate_open_state_rejected() -> None:
    policy = load_policy()
    gate = copy.deepcopy(
        load_successor_gate()
    )

    gate["gate_state"] = (
        "OPEN_FOR_PRODUCTION_IMPORT"
    )

    gate["current_state"]["gate_open"] = True

    recompute_gate_digest(gate)

    with pytest.raises(runner.RunnerError):
        runner.validate_gate(gate, policy)


def test_policy_and_gate_validation_do_not_access_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = load_policy()
    gate = load_successor_gate()

    def reject_database_access(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "database access is forbidden"
        )

    monkeypatch.setattr(
        sqlite3,
        "connect",
        reject_database_access,
    )

    runner.validate_policy(policy)
    runner.validate_gate(gate, policy)
