from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import pytest


repo = Path(__file__).resolve().parents[1]

module_path = (
    repo
    / "scripts/"
    "slack_worker_install_"
    "authorization_consumption_"
    "reference_model.py"
)

capsule_policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_capsule_policy.json"
)


spec = importlib.util.spec_from_file_location(
    "authorization_consumption_model",
    module_path,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(module)


NOW = datetime(
    2026,
    7,
    15,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def load_capsule_policy() -> dict:
    return json.loads(
        capsule_policy_path.read_text(
            encoding="utf-8"
        )
    )


def valid_document() -> dict:
    policy = load_capsule_policy()

    document_contract = policy[
        "capsule_document_contract"
    ]

    return {
        "schema_version": 1,
        "authorization_id": (
            "auth-"
            "0123456789abcdef"
            "0123456789abcdef"
        ),
        "operation": (
            document_contract[
                "operation_value"
            ]
        ),
        "release_id": (
            document_contract[
                "release_id_value"
            ]
        ),
        "issued_at": (
            "2026-07-15T11:59:30Z"
        ),
        "expires_at": (
            "2026-07-15T12:10:00Z"
        ),
        "nonce": (
            "0123456789abcdef"
            "0123456789abcdef"
            "fedcba9876543210"
            "fedcba9876543210"
        ),
        "issuer": {
            "kind": (
                document_contract[
                    "issuer_kind_value"
                ]
            ),
            "uid": (
                document_contract[
                    "issuer_uid_value"
                ]
            ),
        },
        "bindings": policy[
            "expected_bindings"
        ],
        "constraints": policy[
            "expected_constraints"
        ],
    }


def consume(
    document: dict,
    ledger: dict,
):
    return module.consume_in_memory(
        json.dumps(
            document,
            ensure_ascii=False,
        ),
        now_utc=NOW,
        ledger=ledger,
    )


def test_model_policy_passes() -> None:
    policy, reference = (
        module.validate_model_policy()
    )

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2B-5"
    )

    assert hasattr(
        reference,
        "validate_capsule_document_text",
    )


def test_empty_ledger_shape() -> None:
    assert module.empty_ledger() == {
        "authorization_ids": {},
        "nonces": {},
    }


def test_valid_document_returns_new_ledger() -> None:
    original = module.empty_ledger()

    result, updated = consume(
        valid_document(),
        original,
    )

    assert original == (
        module.empty_ledger()
    )

    assert updated is not original

    assert len(
        updated["authorization_ids"]
    ) == 1

    assert len(
        updated["nonces"]
    ) == 1

    assert result[
        "authorization_consumed_in_memory"
    ] is True

    assert result[
        "authorization_consumed_on_host"
    ] is False

    assert result[
        "input_ledger_mutated"
    ] is False


def test_valid_result_remains_no_go() -> None:
    result, _ = consume(
        valid_document(),
        module.empty_ledger(),
    )

    assert result[
        "root_file_custody_validated"
    ] is False

    assert result[
        "execution_allowed"
    ] is False

    assert result[
        "root_release_install_authorized"
    ] is False

    assert result[
        "root_release_install_executed"
    ] is False

    assert result[
        "final_decision"
    ] == "NO_GO"


def test_same_capsule_replay_is_rejected() -> None:
    document = valid_document()

    _, consumed = consume(
        document,
        module.empty_ledger(),
    )

    with pytest.raises(
        module.ConsumptionReferenceError,
        match=(
            "AUTHORIZATION_ID_REPLAY_REJECTED"
        ),
    ):
        consume(
            document,
            consumed,
        )


def test_duplicate_authorization_id_is_rejected() -> None:
    first = valid_document()

    _, consumed = consume(
        first,
        module.empty_ledger(),
    )

    second = valid_document()

    second["nonce"] = (
        "aaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaaa"
        "bbbbbbbbbbbbbbbb"
        "bbbbbbbbbbbbbbbb"
    )

    with pytest.raises(
        module.ConsumptionReferenceError,
        match=(
            "AUTHORIZATION_ID_REPLAY_REJECTED"
        ),
    ):
        consume(
            second,
            consumed,
        )


def test_duplicate_nonce_is_rejected() -> None:
    first = valid_document()

    _, consumed = consume(
        first,
        module.empty_ledger(),
    )

    second = valid_document()

    second["authorization_id"] = (
        "auth-"
        "aaaaaaaaaaaaaaaa"
        "bbbbbbbbbbbbbbbb"
    )

    with pytest.raises(
        module.ConsumptionReferenceError,
        match="NONCE_REPLAY_REJECTED",
    ):
        consume(
            second,
            consumed,
        )


def test_invalid_document_does_not_change_ledger() -> None:
    ledger = module.empty_ledger()
    before = json.loads(
        json.dumps(ledger)
    )

    document = valid_document()

    document["constraints"] = dict(
        document["constraints"]
    )

    document["constraints"][
        "service_start_allowed"
    ] = True

    with pytest.raises(
        module.ConsumptionReferenceError,
        match="DOCUMENT_REJECTED",
    ):
        consume(document, ledger)

    assert ledger == before


def test_expired_document_does_not_change_ledger() -> None:
    ledger = module.empty_ledger()
    before = json.loads(
        json.dumps(ledger)
    )

    document = valid_document()

    document["issued_at"] = (
        "2026-07-15T11:40:00Z"
    )

    document["expires_at"] = (
        "2026-07-15T11:50:00Z"
    )

    with pytest.raises(
        module.ConsumptionReferenceError,
        match="DOCUMENT_REJECTED",
    ):
        consume(document, ledger)

    assert ledger == before


def test_invalid_ledger_shape_is_rejected() -> None:
    with pytest.raises(
        module.ConsumptionReferenceError,
        match="LEDGER_KEYS_INVALID",
    ):
        consume(
            valid_document(),
            {
                "authorization_ids": {},
            },
        )


def test_record_is_reference_only() -> None:
    document = valid_document()

    result, updated = consume(
        document,
        module.empty_ledger(),
    )

    record = updated[
        "authorization_ids"
    ][document["authorization_id"]]

    assert record[
        "reference_only"
    ] is True

    assert result[
        "host_consumption_record_created"
    ] is False
