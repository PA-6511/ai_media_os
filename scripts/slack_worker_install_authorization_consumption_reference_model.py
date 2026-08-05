from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


repo = Path(__file__).resolve().parents[1]

model_policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_consumption_"
    "reference_policy.json"
)


class ConsumptionReferenceError(
    ValueError
):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def repository_path(
    relative: str,
) -> Path:
    path = (
        repo / relative
    ).resolve()

    path.relative_to(
        repo.resolve()
    )

    return path


def load_reference_validator(
    path: Path,
) -> ModuleType:
    spec = (
        importlib.util
        .spec_from_file_location(
            "slack_capsule_reference_validator",
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise ConsumptionReferenceError(
            "REFERENCE_VALIDATOR_LOAD_FAILED"
        )

    module = (
        importlib.util
        .module_from_spec(spec)
    )

    spec.loader.exec_module(
        module
    )

    return module


def validate_model_policy(
) -> tuple[
    dict[str, Any],
    ModuleType,
]:
    policy = load_json(
        model_policy_path
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-5"
    ):
        raise ConsumptionReferenceError(
            "MODEL_POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_AUTHORIZATION_CONSUMPTION_"
        "STATE_MACHINE_REFERENCE_MODEL_"
        "IN_MEMORY_ONLY_NO_HOST_STATE_NO_GO"
    ):
        raise ConsumptionReferenceError(
            "MODEL_POLICY_RESULT_INVALID"
        )

    bindings = policy[
        "bindings"
    ]

    path_hash_pairs = (
        (
            "capsule_policy_path",
            "capsule_policy_sha256",
        ),
        (
            "reference_validator_policy_path",
            "reference_validator_policy_sha256",
        ),
        (
            "reference_validator_source_path",
            "reference_validator_source_sha256",
        ),
        (
            "root_install_policy_path",
            "root_install_policy_sha256",
        ),
    )

    loaded_paths: dict[
        str,
        Path,
    ] = {}

    for path_key, hash_key in (
        path_hash_pairs
    ):
        path = repository_path(
            bindings[path_key]
        )

        if not path.is_file():
            raise ConsumptionReferenceError(
                f"BOUND_INPUT_MISSING: {path_key}"
            )

        if sha256(path) != bindings[
            hash_key
        ]:
            raise ConsumptionReferenceError(
                f"BOUND_INPUT_HASH_INVALID: "
                f"{hash_key}"
            )

        loaded_paths[path_key] = path

    capsule_policy = load_json(
        loaded_paths[
            "capsule_policy_path"
        ]
    )

    reference_policy = load_json(
        loaded_paths[
            "reference_validator_policy_path"
        ]
    )

    root_policy = load_json(
        loaded_paths[
            "root_install_policy_path"
        ]
    )

    if capsule_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-3"
    ):
        raise ConsumptionReferenceError(
            "CAPSULE_POLICY_PHASE_INVALID"
        )

    if reference_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-4"
    ):
        raise ConsumptionReferenceError(
            "REFERENCE_POLICY_PHASE_INVALID"
        )

    if root_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-1"
    ):
        raise ConsumptionReferenceError(
            "ROOT_POLICY_PHASE_INVALID"
        )

    if bindings["release_id"] != (
        capsule_policy[
            "release_binding"
        ]["release_id"]
    ):
        raise ConsumptionReferenceError(
            "RELEASE_ID_BINDING_INVALID"
        )

    scope = policy[
        "reference_model_scope"
    ]

    required_true = (
        "document_input_in_memory_only",
        "ledger_input_in_memory_only",
        "reference_document_validator_required",
        "copy_on_write_ledger_required",
        "successful_result_returns_new_ledger",
        "validation_failure_returns_no_ledger",
        "duplicate_authorization_id_rejected",
        "duplicate_nonce_rejected",
    )

    for key in required_true:
        if scope[key] is not True:
            raise ConsumptionReferenceError(
                f"MODEL_SCOPE_TRUE_INVALID: {key}"
            )

    required_false = (
        "input_ledger_mutation_allowed",
        "host_capsule_file_read_allowed",
        "root_file_custody_validation_claimed",
        "durable_consumption_claimed",
        "authorization_issue_allowed",
        "host_authorization_consumption_allowed",
        "root_release_install_authorized",
    )

    for key in required_false:
        if scope[key] is not False:
            raise ConsumptionReferenceError(
                f"MODEL_SCOPE_FALSE_INVALID: {key}"
            )

    implementation = policy[
        "implementation_boundary"
    ]

    for key, value in (
        implementation.items()
    ):
        if value is not False:
            raise ConsumptionReferenceError(
                f"IMPLEMENTATION_BOUNDARY_INVALID: "
                f"{key}"
            )

    governance = policy[
        "governance"
    ]

    if governance[
        "design_and_test_only"
    ] is not True:
        raise ConsumptionReferenceError(
            "DESIGN_TEST_STATE_INVALID"
        )

    for key in (
        "host_change_executed",
        "capsule_issued",
        "capsule_file_created",
        "authorization_consumed_in_memory",
        "authorization_consumed_on_host",
        "host_consumption_record_created",
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
            raise ConsumptionReferenceError(
                f"GOVERNANCE_STATE_INVALID: {key}"
            )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise ConsumptionReferenceError(
            "FINAL_DECISION_INVALID"
        )

    reference_module = (
        load_reference_validator(
            loaded_paths[
                "reference_validator_source_path"
            ]
        )
    )

    return policy, reference_module


def empty_ledger(
) -> dict[str, dict[str, Any]]:
    return {
        "authorization_ids": {},
        "nonces": {},
    }


def normalize_ledger(
    ledger: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if set(ledger) != {
        "authorization_ids",
        "nonces",
    }:
        raise ConsumptionReferenceError(
            "LEDGER_KEYS_INVALID"
        )

    authorization_ids = ledger[
        "authorization_ids"
    ]

    nonces = ledger["nonces"]

    if not isinstance(
        authorization_ids,
        Mapping,
    ):
        raise ConsumptionReferenceError(
            "AUTHORIZATION_LEDGER_MAPPING_REQUIRED"
        )

    if not isinstance(
        nonces,
        Mapping,
    ):
        raise ConsumptionReferenceError(
            "NONCE_LEDGER_MAPPING_REQUIRED"
        )

    return {
        "authorization_ids": dict(
            authorization_ids
        ),
        "nonces": dict(nonces),
    }


def consume_in_memory(
    document_text: str,
    *,
    now_utc: datetime,
    ledger: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
]:
    policy, reference = (
        validate_model_policy()
    )

    current = normalize_ledger(
        ledger
    )

    try:
        validation = (
            reference
            .validate_capsule_document_text(
                document_text,
                now_utc=now_utc,
            )
        )

        document = (
            reference.parse_document(
                document_text
            )
        )
    except Exception as exc:
        capsule_error = getattr(
            reference,
            "CapsuleValidationError",
        )

        if isinstance(
            exc,
            capsule_error,
        ):
            raise ConsumptionReferenceError(
                f"DOCUMENT_REJECTED: {exc}"
            ) from exc

        raise

    authorization_id = document[
        "authorization_id"
    ]

    nonce = document["nonce"]

    if authorization_id in (
        current[
            "authorization_ids"
        ]
    ):
        raise ConsumptionReferenceError(
            "AUTHORIZATION_ID_REPLAY_REJECTED"
        )

    if nonce in current["nonces"]:
        raise ConsumptionReferenceError(
            "NONCE_REPLAY_REJECTED"
        )

    normalized_now = now_utc.astimezone(
        timezone.utc
    )

    consumed_at = normalized_now.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )

    if normalized_now.microsecond:
        consumed_at += (
            f".{normalized_now.microsecond:06d}"
        )

    consumed_at += "Z"

    record = {
        "release_id": validation[
            "release_id"
        ],
        "consumed_at": consumed_at,
        "canonical_document_sha256": (
            validation[
                "canonical_document_sha256"
            ]
        ),
        "reference_only": True,
    }

    updated_authorization_ids = dict(
        current["authorization_ids"]
    )

    updated_nonces = dict(
        current["nonces"]
    )

    updated_authorization_ids[
        authorization_id
    ] = record

    updated_nonces[nonce] = {
        "authorization_id": (
            authorization_id
        ),
        "release_id": validation[
            "release_id"
        ],
        "consumed_at": consumed_at,
        "reference_only": True,
    }

    updated_ledger = {
        "authorization_ids": (
            updated_authorization_ids
        ),
        "nonces": updated_nonces,
    }

    result = {
        "validation_passed": True,
        "state": (
            "CONSUMED_IN_MEMORY_REFERENCE_ONLY"
        ),
        "authorization_id": (
            authorization_id
        ),
        "release_id": validation[
            "release_id"
        ],
        "canonical_document_sha256": (
            validation[
                "canonical_document_sha256"
            ]
        ),
        "input_ledger_mutated": False,
        "authorization_consumed_in_memory": (
            True
        ),
        "authorization_consumed_on_host": (
            False
        ),
        "host_consumption_record_created": (
            False
        ),
        "root_file_custody_validated": (
            False
        ),
        "execution_allowed": False,
        "root_release_install_authorized": (
            False
        ),
        "root_release_install_executed": (
            False
        ),
        "final_decision": "NO_GO",
    }

    if policy[
        "state_machine"
    ][
        "install_authorized_state_reachable"
    ] is not False:
        raise ConsumptionReferenceError(
            "INSTALL_STATE_UNEXPECTEDLY_REACHABLE"
        )

    return result, updated_ledger


def main() -> None:
    validate_model_policy()

    print(
        "CONSUMPTION_MODEL_POLICY_BINDING: PASS"
    )
    print(
        "REFERENCE_DOCUMENT_VALIDATOR_BINDING: PASS"
    )
    print(
        "COPY_ON_WRITE_LEDGER_MODEL: PASS"
    )
    print(
        "AUTHORIZATION_ID_REPLAY_REJECTION: ENABLED"
    )
    print(
        "NONCE_REPLAY_REJECTION: ENABLED"
    )
    print(
        "HOST_CAPSULE_FILE_READ: FALSE"
    )
    print(
        "HOST_CONSUMPTION_RECORD_CREATED: FALSE"
    )
    print(
        "AUTHORIZATION_CONSUMED_ON_HOST: FALSE"
    )
    print(
        "ROOT_FILE_CUSTODY_VALIDATED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "HOST_MUTATION_EXECUTED: FALSE"
    )
    print(
        "SERVICE_START_EXECUTED: FALSE"
    )
    print(
        "UNIT_ENABLE_EXECUTED: FALSE"
    )
    print("FINAL_DECISION: NO_GO")
    print(
        "SQL_B2_4B_5G_3B_1D_2B_5_"
        "CONSUMPTION_REFERENCE_MODEL: PASS"
    )


if __name__ == "__main__":
    main()
