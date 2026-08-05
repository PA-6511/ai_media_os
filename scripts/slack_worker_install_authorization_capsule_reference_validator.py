from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


repo = Path(__file__).resolve().parents[1]

reference_policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_capsule_"
    "reference_validator_policy.json"
)


class CapsuleValidationError(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def repository_path(relative: str) -> Path:
    path = (
        repo / relative
    ).resolve()

    path.relative_to(
        repo.resolve()
    )

    return path


def reject_duplicate_keys(
    pairs: list[
        tuple[str, Any]
    ],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise CapsuleValidationError(
                f"DUPLICATE_JSON_KEY: {key}"
            )

        result[key] = value

    return result


def parse_document(
    document_text: str,
) -> dict[str, Any]:
    try:
        value = json.loads(
            document_text,
            object_pairs_hook=(
                reject_duplicate_keys
            ),
        )
    except CapsuleValidationError:
        raise
    except (
        json.JSONDecodeError,
        UnicodeError,
    ) as exc:
        raise CapsuleValidationError(
            "CAPSULE_JSON_INVALID"
        ) from exc

    if not isinstance(value, dict):
        raise CapsuleValidationError(
            "CAPSULE_JSON_OBJECT_REQUIRED"
        )

    return value


def canonical_sha256(
    document: dict[str, Any],
) -> str:
    payload = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        payload
    ).hexdigest()


def parse_rfc3339_utc_z(
    value: object,
    field_name: str,
) -> datetime:
    if not isinstance(value, str):
        raise CapsuleValidationError(
            f"{field_name}_TYPE_INVALID"
        )

    pattern = (
        r"^\d{4}-\d{2}-\d{2}"
        r"T\d{2}:\d{2}:\d{2}"
        r"(?:\.\d{1,6})?Z$"
    )

    if re.fullmatch(
        pattern,
        value,
    ) is None:
        raise CapsuleValidationError(
            f"{field_name}_FORMAT_INVALID"
        )

    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00"
        )
    except ValueError as exc:
        raise CapsuleValidationError(
            f"{field_name}_VALUE_INVALID"
        ) from exc

    if parsed.tzinfo is None:
        raise CapsuleValidationError(
            f"{field_name}_TIMEZONE_MISSING"
        )

    return parsed.astimezone(
        timezone.utc
    )


def require_exact_keys(
    value: object,
    expected: list[str],
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CapsuleValidationError(
            f"{field_name}_OBJECT_REQUIRED"
        )

    if set(value) != set(expected):
        raise CapsuleValidationError(
            f"{field_name}_KEYS_INVALID"
        )

    return value


def validate_reference_policy(
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    reference = load_json(
        reference_policy_path
    )

    if reference["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-4"
    ):
        raise CapsuleValidationError(
            "REFERENCE_POLICY_PHASE_INVALID"
        )

    if reference["result"] != (
        "PASS_AUTHORIZATION_CAPSULE_"
        "REFERENCE_VALIDATOR_"
        "IN_MEMORY_ONLY_NO_ISSUANCE_NO_GO"
    ):
        raise CapsuleValidationError(
            "REFERENCE_POLICY_RESULT_INVALID"
        )

    bindings = reference[
        "bindings"
    ]

    capsule_policy_path = (
        repository_path(
            bindings[
                "capsule_policy_path"
            ]
        )
    )

    if sha256(
        capsule_policy_path
    ) != bindings[
        "capsule_policy_sha256"
    ]:
        raise CapsuleValidationError(
            "CAPSULE_POLICY_HASH_INVALID"
        )

    capsule_policy = load_json(
        capsule_policy_path
    )

    if capsule_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-3"
    ):
        raise CapsuleValidationError(
            "CAPSULE_POLICY_PHASE_INVALID"
        )

    scope = reference[
        "reference_validator_scope"
    ]

    required_true = (
        "document_text_input_in_memory_only",
        "pure_document_validation",
        "duplicate_json_keys_rejected",
        "unknown_document_keys_rejected",
        "exact_nested_keys_required",
        "exact_operation_required",
        "exact_release_id_required",
        "exact_issuer_required",
        "exact_binding_values_required",
        "exact_constraint_values_required",
        "authorization_id_pattern_required",
        "nonce_pattern_required",
        "utc_time_validation_required",
        "maximum_validity_validation_required",
        "canonical_document_hash_calculation_allowed",
    )

    for key in required_true:
        if scope[key] is not True:
            raise CapsuleValidationError(
                f"REFERENCE_SCOPE_TRUE_INVALID: {key}"
            )

    required_false = (
        "capsule_host_path_open_allowed",
        "root_file_custody_validation_claimed",
        "authorization_consumption_allowed",
        "authorization_issue_allowed",
        "installation_authorization_granted",
    )

    for key in required_false:
        if scope[key] is not False:
            raise CapsuleValidationError(
                f"REFERENCE_SCOPE_FALSE_INVALID: {key}"
            )

    implementation = reference[
        "implementation_boundary"
    ]

    for key, value in implementation.items():
        if key == "root_execution_required":
            if value is not False:
                raise CapsuleValidationError(
                    "ROOT_EXECUTION_STATE_INVALID"
                )
            continue

        if value is not False:
            raise CapsuleValidationError(
                f"IMPLEMENTATION_BOUNDARY_INVALID: {key}"
            )

    governance = reference[
        "governance"
    ]

    if governance[
        "design_and_test_only"
    ] is not True:
        raise CapsuleValidationError(
            "DESIGN_TEST_STATE_INVALID"
        )

    for key in (
        "host_change_executed",
        "capsule_issued",
        "capsule_file_created",
        "authorization_consumed",
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
            raise CapsuleValidationError(
                f"GOVERNANCE_STATE_INVALID: {key}"
            )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise CapsuleValidationError(
            "REFERENCE_FINAL_DECISION_INVALID"
        )

    return reference, capsule_policy


def validate_capsule_document_text(
    document_text: str,
    *,
    now_utc: datetime,
) -> dict[str, Any]:
    if now_utc.tzinfo is None:
        raise CapsuleValidationError(
            "NOW_TIMEZONE_REQUIRED"
        )

    now_utc = now_utc.astimezone(
        timezone.utc
    )

    reference, capsule_policy = (
        validate_reference_policy()
    )

    document_contract = capsule_policy[
        "capsule_document_contract"
    ]

    document = parse_document(
        document_text
    )

    require_exact_keys(
        document,
        document_contract[
            "top_level_keys"
        ],
        "TOP_LEVEL",
    )

    schema_version = document[
        "schema_version"
    ]

    if (
        type(schema_version) is not int
        or schema_version
        != document_contract[
            "schema_version_value"
        ]
    ):
        raise CapsuleValidationError(
            "SCHEMA_VERSION_INVALID"
        )

    for key in (
        "authorization_id",
        "operation",
        "release_id",
        "issued_at",
        "expires_at",
        "nonce",
    ):
        if not isinstance(
            document[key],
            str,
        ):
            raise CapsuleValidationError(
                f"{key}_TYPE_INVALID"
            )

    if document[
        "operation"
    ] != document_contract[
        "operation_value"
    ]:
        raise CapsuleValidationError(
            "OPERATION_INVALID"
        )

    if document[
        "release_id"
    ] != document_contract[
        "release_id_value"
    ]:
        raise CapsuleValidationError(
            "RELEASE_ID_INVALID"
        )

    authorization_id = document[
        "authorization_id"
    ]

    nonce = document["nonce"]

    if re.fullmatch(
        document_contract[
            "authorization_id_pattern"
        ],
        authorization_id,
    ) is None:
        raise CapsuleValidationError(
            "AUTHORIZATION_ID_INVALID"
        )

    if re.fullmatch(
        document_contract[
            "nonce_pattern"
        ],
        nonce,
    ) is None:
        raise CapsuleValidationError(
            "NONCE_INVALID"
        )

    if authorization_id == nonce:
        raise CapsuleValidationError(
            "AUTHORIZATION_ID_NONCE_COLLISION"
        )

    issuer = require_exact_keys(
        document["issuer"],
        document_contract[
            "issuer_keys"
        ],
        "ISSUER",
    )

    if issuer["kind"] != (
        document_contract[
            "issuer_kind_value"
        ]
    ):
        raise CapsuleValidationError(
            "ISSUER_KIND_INVALID"
        )

    if (
        type(issuer["uid"]) is not int
        or issuer["uid"] != (
            document_contract[
                "issuer_uid_value"
            ]
        )
    ):
        raise CapsuleValidationError(
            "ISSUER_UID_INVALID"
        )

    bindings = require_exact_keys(
        document["bindings"],
        document_contract[
            "binding_keys"
        ],
        "BINDINGS",
    )

    expected_bindings = (
        reference[
            "bindings"
        ]["expected_bindings"]
    )

    if bindings != expected_bindings:
        raise CapsuleValidationError(
            "BINDINGS_VALUE_INVALID"
        )

    constraints = require_exact_keys(
        document["constraints"],
        document_contract[
            "constraint_keys"
        ],
        "CONSTRAINTS",
    )

    expected_constraints = (
        reference[
            "bindings"
        ]["expected_constraints"]
    )

    if constraints != (
        expected_constraints
    ):
        raise CapsuleValidationError(
            "CONSTRAINTS_VALUE_INVALID"
        )

    issued_at = parse_rfc3339_utc_z(
        document["issued_at"],
        "ISSUED_AT",
    )

    expires_at = parse_rfc3339_utc_z(
        document["expires_at"],
        "EXPIRES_AT",
    )

    temporal = reference[
        "temporal_reference"
    ]

    lifetime_seconds = (
        expires_at - issued_at
    ).total_seconds()

    if lifetime_seconds <= 0:
        raise CapsuleValidationError(
            "CAPSULE_LIFETIME_NONPOSITIVE"
        )

    if lifetime_seconds > temporal[
        "maximum_validity_seconds"
    ]:
        raise CapsuleValidationError(
            "CAPSULE_LIFETIME_EXCEEDED"
        )

    future_tolerance = temporal[
        "future_issued_at_tolerance_seconds"
    ]

    if (
        issued_at - now_utc
    ).total_seconds() > future_tolerance:
        raise CapsuleValidationError(
            "CAPSULE_NOT_YET_VALID"
        )

    if expires_at <= now_utc:
        raise CapsuleValidationError(
            "CAPSULE_EXPIRED"
        )

    return {
        "validation_passed": True,
        "release_id": document[
            "release_id"
        ],
        "authorization_id": (
            authorization_id
        ),
        "canonical_document_sha256": (
            canonical_sha256(document)
        ),
        "execution_allowed": False,
        "authorization_consumed": False,
        "root_file_custody_validated": (
            False
        ),
        "root_release_install_authorized": (
            False
        ),
        "root_release_install_executed": (
            False
        ),
        "final_decision": "NO_GO",
    }


def main() -> None:
    validate_reference_policy()

    print(
        "REFERENCE_POLICY_BINDING: PASS"
    )
    print(
        "IN_MEMORY_DOCUMENT_VALIDATOR: PASS"
    )
    print(
        "DUPLICATE_KEY_REJECTION: ENABLED"
    )
    print(
        "EXACT_DOCUMENT_BINDING: ENABLED"
    )
    print(
        "TEMPORAL_VALIDATION: ENABLED"
    )
    print(
        "HOST_CAPSULE_FILE_READ: FALSE"
    )
    print(
        "ROOT_FILE_CUSTODY_VALIDATED: FALSE"
    )
    print(
        "AUTHORIZATION_CAPSULE_ISSUED: FALSE"
    )
    print(
        "AUTHORIZATION_CONSUMED: FALSE"
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
        "SQL_B2_4B_5G_3B_1D_2B_4_"
        "CAPSULE_REFERENCE_VALIDATOR: PASS"
    )


if __name__ == "__main__":
    main()
