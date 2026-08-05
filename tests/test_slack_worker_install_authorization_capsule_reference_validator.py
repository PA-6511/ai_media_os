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
    "authorization_capsule_"
    "reference_validator.py"
)

policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_capsule_policy.json"
)


spec = importlib.util.spec_from_file_location(
    "capsule_reference_validator",
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
        policy_path.read_text(
            encoding="utf-8"
        )
    )


def valid_document() -> dict:
    policy = load_policy()

    document = policy[
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
            document["operation_value"]
        ),
        "release_id": (
            document["release_id_value"]
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
                document[
                    "issuer_kind_value"
                ]
            ),
            "uid": (
                document[
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


def validate(
    document: dict,
) -> dict:
    return (
        module
        .validate_capsule_document_text(
            json.dumps(
                document,
                ensure_ascii=False,
            ),
            now_utc=NOW,
        )
    )


def test_reference_policy_passes() -> None:
    reference, policy = (
        module.validate_reference_policy()
    )

    assert reference["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2B-4"
    )

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2B-3"
    )


def test_valid_document_is_still_no_go() -> None:
    result = validate(
        valid_document()
    )

    assert result[
        "validation_passed"
    ] is True

    assert result[
        "execution_allowed"
    ] is False

    assert result[
        "authorization_consumed"
    ] is False

    assert result[
        "root_file_custody_validated"
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


def test_duplicate_json_key_is_rejected() -> None:
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
        module.CapsuleValidationError,
        match="DUPLICATE_JSON_KEY",
    ):
        (
            module
            .validate_capsule_document_text(
                text,
                now_utc=NOW,
            )
        )


def test_unknown_top_level_key_is_rejected() -> None:
    document = valid_document()
    document["unexpected"] = True

    with pytest.raises(
        module.CapsuleValidationError,
        match="TOP_LEVEL_KEYS_INVALID",
    ):
        validate(document)


def test_wrong_binding_is_rejected() -> None:
    document = valid_document()

    document["bindings"] = dict(
        document["bindings"]
    )

    document["bindings"][
        "final_release_path"
    ] = "/invalid/release"

    with pytest.raises(
        module.CapsuleValidationError,
        match="BINDINGS_VALUE_INVALID",
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
        module.CapsuleValidationError,
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
        module.CapsuleValidationError,
        match="CAPSULE_EXPIRED",
    ):
        validate(document)


def test_not_yet_valid_document_is_rejected() -> None:
    document = valid_document()

    document["issued_at"] = (
        "2026-07-15T12:01:00Z"
    )

    document["expires_at"] = (
        "2026-07-15T12:10:00Z"
    )

    with pytest.raises(
        module.CapsuleValidationError,
        match="CAPSULE_NOT_YET_VALID",
    ):
        validate(document)


def test_excessive_lifetime_is_rejected() -> None:
    document = valid_document()

    document["issued_at"] = (
        "2026-07-15T11:59:30Z"
    )

    document["expires_at"] = (
        "2026-07-15T12:20:00Z"
    )

    with pytest.raises(
        module.CapsuleValidationError,
        match="CAPSULE_LIFETIME_EXCEEDED",
    ):
        validate(document)


def test_invalid_authorization_id_is_rejected() -> None:
    document = valid_document()

    document["authorization_id"] = (
        "auth-not-valid"
    )

    with pytest.raises(
        module.CapsuleValidationError,
        match="AUTHORIZATION_ID_INVALID",
    ):
        validate(document)


def test_invalid_nonce_is_rejected() -> None:
    document = valid_document()

    document["nonce"] = "abc"

    with pytest.raises(
        module.CapsuleValidationError,
        match="NONCE_INVALID",
    ):
        validate(document)


def test_naive_now_is_rejected() -> None:
    document = valid_document()

    with pytest.raises(
        module.CapsuleValidationError,
        match="NOW_TIMEZONE_REQUIRED",
    ):
        (
            module
            .validate_capsule_document_text(
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
