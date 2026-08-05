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
    "authorization_pending_"
    "reconciliation_reference_"
    "validator.py"
)

reconciliation_policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_pending_"
    "reconciliation_policy.json"
)


spec = importlib.util.spec_from_file_location(
    "pending_reconciliation_reference_validator",
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


def load_policy() -> dict:
    return json.loads(
        reconciliation_policy_path.read_text(
            encoding="utf-8"
        )
    )


def valid_document() -> dict:
    policy = load_policy()

    contract = policy[
        "authorization_document_contract"
    ]

    authorization_id = (
        "auth-"
        "0123456789abcdef"
        "0123456789abcdef"
    )

    nonce = (
        "0123456789abcdef"
        "0123456789abcdef"
        "fedcba9876543210"
        "fedcba9876543210"
    )

    transaction_id = (
        "00112233445566778899aabbccddeeff"
    )

    pending_filename = (
        ".pending-"
        f"{authorization_id}-"
        f"{nonce}-"
        f"{transaction_id}.json"
    )

    return {
        "schema_version": 1,
        "reconciliation_authorization_id": (
            "recon-auth-"
            "0123456789abcdef"
            "fedcba9876543210"
        ),
        "operation": (
            contract[
                "operation_value"
            ]
        ),
        "release_id": (
            contract[
                "release_id_value"
            ]
        ),
        "pending_filename": (
            pending_filename
        ),
        "pending_sha256": (
            "a" * 64
        ),
        "authorization_id": (
            authorization_id
        ),
        "nonce": nonce,
        "transaction_id": (
            transaction_id
        ),
        "allowed_decision": (
            "KEEP_REPLAY_RESERVED"
        ),
        "issued_at": (
            "2026-07-15T11:59:30Z"
        ),
        "expires_at": (
            "2026-07-15T12:10:00Z"
        ),
        "issuer": {
            "kind": (
                contract[
                    "issuer_kind_value"
                ]
            ),
            "uid": (
                contract[
                    "issuer_uid_value"
                ]
            ),
        },
        "constraints": policy[
            "authorization_constraints"
        ],
    }


def validate(document: dict) -> dict:
    return (
        module
        .validate_reconciliation_document_text(
            json.dumps(
                document,
                ensure_ascii=False,
            ),
            now_utc=NOW,
        )
    )


def test_reference_policy_passes() -> None:
    reference, reconciliation = (
        module.validate_reference_policy()
    )

    assert reference["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2B-10"
    )

    assert reconciliation["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2B-9"
    )


def test_valid_document_remains_no_go() -> None:
    result = validate(
        valid_document()
    )

    assert result[
        "validation_passed"
    ] is True

    assert result[
        "root_file_custody_validated"
    ] is False

    assert result[
        "reconciliation_authorization_consumed"
    ] is False

    assert result[
        "reconciliation_decision_record_created"
    ] is False

    assert result[
        "pending_record_modified"
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


def test_duplicate_key_is_rejected() -> None:
    text = json.dumps(
        valid_document()
    )

    text = text.replace(
        '"schema_version": 1',
        (
            '"schema_version": 1, '
            '"schema_version": 1'
        ),
        1,
    )

    with pytest.raises(
        module.ReconciliationValidationError,
        match="DUPLICATE_JSON_KEY",
    ):
        (
            module
            .validate_reconciliation_document_text(
                text,
                now_utc=NOW,
            )
        )


def test_unknown_key_is_rejected() -> None:
    document = valid_document()
    document["unexpected"] = True

    with pytest.raises(
        module.ReconciliationValidationError,
        match="TOP_LEVEL_KEYS_INVALID",
    ):
        validate(document)


def test_invalid_decision_is_rejected() -> None:
    document = valid_document()

    document[
        "allowed_decision"
    ] = "DELETE_PENDING"

    with pytest.raises(
        module.ReconciliationValidationError,
        match="ALLOWED_DECISION_INVALID",
    ):
        validate(document)


def test_pending_authorization_binding_is_required() -> None:
    document = valid_document()

    document["authorization_id"] = (
        "auth-"
        "aaaaaaaaaaaaaaaa"
        "bbbbbbbbbbbbbbbb"
    )

    with pytest.raises(
        module.ReconciliationValidationError,
        match=(
            "PENDING_AUTHORIZATION_ID_BINDING_INVALID"
        ),
    ):
        validate(document)


def test_pending_nonce_binding_is_required() -> None:
    document = valid_document()

    document["nonce"] = (
        "a" * 64
    )

    with pytest.raises(
        module.ReconciliationValidationError,
        match="PENDING_NONCE_BINDING_INVALID",
    ):
        validate(document)


def test_pending_transaction_binding_is_required() -> None:
    document = valid_document()

    document["transaction_id"] = (
        "f" * 32
    )

    with pytest.raises(
        module.ReconciliationValidationError,
        match=(
            "PENDING_TRANSACTION_ID_BINDING_INVALID"
        ),
    ):
        validate(document)


def test_invalid_pending_sha256_is_rejected() -> None:
    document = valid_document()

    document["pending_sha256"] = (
        "not-a-hash"
    )

    with pytest.raises(
        module.ReconciliationValidationError,
        match="PENDING_SHA256_INVALID",
    ):
        validate(document)


def test_wrong_constraint_is_rejected() -> None:
    document = valid_document()

    document["constraints"] = dict(
        document["constraints"]
    )

    document["constraints"][
        "service_start_allowed"
    ] = True

    with pytest.raises(
        module.ReconciliationValidationError,
        match="CONSTRAINTS_VALUE_INVALID",
    ):
        validate(document)


def test_expired_document_is_rejected() -> None:
    document = valid_document()

    document["issued_at"] = (
        "2026-07-15T11:40:00Z"
    )

    document["expires_at"] = (
        "2026-07-15T11:50:00Z"
    )

    with pytest.raises(
        module.ReconciliationValidationError,
        match="AUTHORIZATION_EXPIRED",
    ):
        validate(document)


def test_excessive_lifetime_is_rejected() -> None:
    document = valid_document()

    document["issued_at"] = (
        "2026-07-15T11:59:00Z"
    )

    document["expires_at"] = (
        "2026-07-15T12:20:00Z"
    )

    with pytest.raises(
        module.ReconciliationValidationError,
        match="AUTHORIZATION_LIFETIME_EXCEEDED",
    ):
        validate(document)


def test_naive_now_is_rejected() -> None:
    document = valid_document()

    with pytest.raises(
        module.ReconciliationValidationError,
        match="NOW_TIMEZONE_REQUIRED",
    ):
        (
            module
            .validate_reconciliation_document_text(
                json.dumps(document),
                now_utc=datetime(
                    2026,
                    7,
                    15,
                    12,
                    0,
                    0,
                ),
            )
        )
