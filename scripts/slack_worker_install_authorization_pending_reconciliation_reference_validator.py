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
    "authorization_pending_"
    "reconciliation_reference_"
    "validator_policy.json"
)


class ReconciliationValidationError(
    ValueError
):
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
            raise ReconciliationValidationError(
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
    except ReconciliationValidationError:
        raise
    except (
        json.JSONDecodeError,
        UnicodeError,
    ) as exc:
        raise ReconciliationValidationError(
            "RECONCILIATION_JSON_INVALID"
        ) from exc

    if not isinstance(value, dict):
        raise ReconciliationValidationError(
            "RECONCILIATION_JSON_OBJECT_REQUIRED"
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


def require_exact_keys(
    value: object,
    expected: list[str],
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReconciliationValidationError(
            f"{field_name}_OBJECT_REQUIRED"
        )

    if set(value) != set(expected):
        raise ReconciliationValidationError(
            f"{field_name}_KEYS_INVALID"
        )

    return value


def parse_rfc3339_utc_z(
    value: object,
    field_name: str,
) -> datetime:
    if not isinstance(value, str):
        raise ReconciliationValidationError(
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
        raise ReconciliationValidationError(
            f"{field_name}_FORMAT_INVALID"
        )

    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00"
        )
    except ValueError as exc:
        raise ReconciliationValidationError(
            f"{field_name}_VALUE_INVALID"
        ) from exc

    return parsed.astimezone(
        timezone.utc
    )


def validate_reference_policy(
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    reference = load_json(
        reference_policy_path
    )

    if reference["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-10"
    ):
        raise ReconciliationValidationError(
            "REFERENCE_POLICY_PHASE_INVALID"
        )

    if reference["result"] != (
        "PASS_PENDING_RECONCILIATION_"
        "AUTHORIZATION_REFERENCE_VALIDATOR_"
        "IN_MEMORY_ONLY_NOT_CONSUMED_NO_GO"
    ):
        raise ReconciliationValidationError(
            "REFERENCE_POLICY_RESULT_INVALID"
        )

    bindings = reference["bindings"]

    policy_path = repository_path(
        bindings[
            "reconciliation_policy_path"
        ]
    )

    if sha256(policy_path) != bindings[
        "reconciliation_policy_sha256"
    ]:
        raise ReconciliationValidationError(
            "RECONCILIATION_POLICY_HASH_INVALID"
        )

    reconciliation = load_json(
        policy_path
    )

    if reconciliation["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-9"
    ):
        raise ReconciliationValidationError(
            "RECONCILIATION_POLICY_PHASE_INVALID"
        )

    if bindings["release_id"] != (
        reconciliation[
            "bindings"
        ]["release_id"]
    ):
        raise ReconciliationValidationError(
            "RELEASE_ID_BINDING_INVALID"
        )

    scope = reference[
        "reference_validator_scope"
    ]

    required_true = (
        "document_text_input_in_memory_only",
        "duplicate_json_keys_rejected",
        "unknown_keys_rejected",
        "exact_document_keys_required",
        "exact_operation_required",
        "exact_release_id_required",
        "exact_issuer_required",
        "exact_constraints_required",
        "allowed_decision_required",
        "pending_filename_pattern_required",
        "pending_filename_identity_binding_required",
        "pending_sha256_pattern_required",
        "authorization_id_pattern_required",
        "nonce_pattern_required",
        "transaction_id_pattern_required",
        "utc_time_validation_required",
        "maximum_validity_validation_required",
        "canonical_document_sha256_calculation_allowed",
    )

    for key in required_true:
        if scope[key] is not True:
            raise ReconciliationValidationError(
                f"REFERENCE_TRUE_STATE_INVALID: {key}"
            )

    required_false = (
        "host_authorization_path_read_allowed",
        "root_file_custody_validation_claimed",
        "authorization_consumption_allowed",
        "decision_record_creation_allowed",
        "pending_record_mutation_allowed",
        "installation_authorization_granted",
    )

    for key in required_false:
        if scope[key] is not False:
            raise ReconciliationValidationError(
                f"REFERENCE_FALSE_STATE_INVALID: {key}"
            )

    for key, value in reference[
        "implementation_boundary"
    ].items():
        if value is not False:
            raise ReconciliationValidationError(
                f"IMPLEMENTATION_BOUNDARY_INVALID: {key}"
            )

    governance = reference[
        "governance"
    ]

    if governance[
        "design_and_test_only"
    ] is not True:
        raise ReconciliationValidationError(
            "DESIGN_TEST_STATE_INVALID"
        )

    for key in (
        "host_change_executed",
        "reconciliation_authorization_issued",
        "reconciliation_authorization_consumed",
        "reconciliation_decision_record_created",
        "root_file_custody_validated",
        "pending_record_modified",
        "pending_record_deleted",
        "pending_record_finalized",
        "root_release_install_authorized",
        "root_release_install_executed",
        "root_helper_implemented",
        "root_helper_installed",
        "current_host_link_created",
        "secret_migration_executed",
        "unit_change_executed",
        "daemon_reload_executed",
        "gate_creation_executed",
        "service_start_executed",
        "unit_enable_executed",
    ):
        if governance[key] is not False:
            raise ReconciliationValidationError(
                f"GOVERNANCE_STATE_INVALID: {key}"
            )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise ReconciliationValidationError(
            "FINAL_DECISION_INVALID"
        )

    return reference, reconciliation


def validate_reconciliation_document_text(
    document_text: str,
    *,
    now_utc: datetime,
) -> dict[str, Any]:
    if now_utc.tzinfo is None:
        raise ReconciliationValidationError(
            "NOW_TIMEZONE_REQUIRED"
        )

    now_utc = now_utc.astimezone(
        timezone.utc
    )

    reference, reconciliation = (
        validate_reference_policy()
    )

    contract = reconciliation[
        "authorization_document_contract"
    ]

    separate = reconciliation[
        "separate_authorization_contract"
    ]

    document = parse_document(
        document_text
    )

    require_exact_keys(
        document,
        contract["required_keys"],
        "TOP_LEVEL",
    )

    schema_version = document[
        "schema_version"
    ]

    if (
        type(schema_version) is not int
        or schema_version
        != contract[
            "schema_version_value"
        ]
    ):
        raise ReconciliationValidationError(
            "SCHEMA_VERSION_INVALID"
        )

    string_fields = (
        "reconciliation_authorization_id",
        "operation",
        "release_id",
        "pending_filename",
        "pending_sha256",
        "authorization_id",
        "nonce",
        "transaction_id",
        "allowed_decision",
        "issued_at",
        "expires_at",
    )

    for key in string_fields:
        if not isinstance(
            document[key],
            str,
        ):
            raise ReconciliationValidationError(
                f"{key}_TYPE_INVALID"
            )

    if document[
        "operation"
    ] != contract[
        "operation_value"
    ]:
        raise ReconciliationValidationError(
            "OPERATION_INVALID"
        )

    if document[
        "release_id"
    ] != contract[
        "release_id_value"
    ]:
        raise ReconciliationValidationError(
            "RELEASE_ID_INVALID"
        )

    if document[
        "allowed_decision"
    ] not in separate[
        "allowed_decisions"
    ]:
        raise ReconciliationValidationError(
            "ALLOWED_DECISION_INVALID"
        )

    if re.fullmatch(
        contract[
            "reconciliation_authorization_id_pattern"
        ],
        document[
            "reconciliation_authorization_id"
        ],
    ) is None:
        raise ReconciliationValidationError(
            "RECONCILIATION_AUTHORIZATION_ID_INVALID"
        )

    pending_match = re.fullmatch(
        contract[
            "pending_filename_pattern"
        ],
        document[
            "pending_filename"
        ],
    )

    if pending_match is None:
        raise ReconciliationValidationError(
            "PENDING_FILENAME_INVALID"
        )

    if document[
        "authorization_id"
    ] != pending_match.group(1):
        raise ReconciliationValidationError(
            "PENDING_AUTHORIZATION_ID_BINDING_INVALID"
        )

    if document[
        "nonce"
    ] != pending_match.group(2):
        raise ReconciliationValidationError(
            "PENDING_NONCE_BINDING_INVALID"
        )

    if document[
        "transaction_id"
    ] != pending_match.group(3):
        raise ReconciliationValidationError(
            "PENDING_TRANSACTION_ID_BINDING_INVALID"
        )

    if re.fullmatch(
        r"^auth-[a-f0-9]{32}$",
        document["authorization_id"],
    ) is None:
        raise ReconciliationValidationError(
            "AUTHORIZATION_ID_INVALID"
        )

    if re.fullmatch(
        r"^[a-f0-9]{64}$",
        document["nonce"],
    ) is None:
        raise ReconciliationValidationError(
            "NONCE_INVALID"
        )

    if re.fullmatch(
        contract[
            "transaction_id_pattern"
        ],
        document["transaction_id"],
    ) is None:
        raise ReconciliationValidationError(
            "TRANSACTION_ID_INVALID"
        )

    if re.fullmatch(
        contract[
            "pending_sha256_pattern"
        ],
        document["pending_sha256"],
    ) is None:
        raise ReconciliationValidationError(
            "PENDING_SHA256_INVALID"
        )

    issuer = require_exact_keys(
        document["issuer"],
        [
            "kind",
            "uid",
        ],
        "ISSUER",
    )

    if issuer["kind"] != (
        contract[
            "issuer_kind_value"
        ]
    ):
        raise ReconciliationValidationError(
            "ISSUER_KIND_INVALID"
        )

    if (
        type(issuer["uid"]) is not int
        or issuer["uid"] != (
            contract[
                "issuer_uid_value"
            ]
        )
    ):
        raise ReconciliationValidationError(
            "ISSUER_UID_INVALID"
        )

    constraints = require_exact_keys(
        document["constraints"],
        list(
            reference[
                "bindings"
            ]["expected_constraints"]
        ),
        "CONSTRAINTS",
    )

    if constraints != reference[
        "bindings"
    ]["expected_constraints"]:
        raise ReconciliationValidationError(
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

    lifetime = (
        expires_at - issued_at
    ).total_seconds()

    if lifetime <= 0:
        raise ReconciliationValidationError(
            "AUTHORIZATION_LIFETIME_NONPOSITIVE"
        )

    if lifetime > temporal[
        "maximum_validity_seconds"
    ]:
        raise ReconciliationValidationError(
            "AUTHORIZATION_LIFETIME_EXCEEDED"
        )

    if (
        issued_at - now_utc
    ).total_seconds() > temporal[
        "future_issued_at_tolerance_seconds"
    ]:
        raise ReconciliationValidationError(
            "AUTHORIZATION_NOT_YET_VALID"
        )

    if expires_at <= now_utc:
        raise ReconciliationValidationError(
            "AUTHORIZATION_EXPIRED"
        )

    return {
        "validation_passed": True,
        "reconciliation_authorization_id": (
            document[
                "reconciliation_authorization_id"
            ]
        ),
        "release_id": document[
            "release_id"
        ],
        "pending_filename": document[
            "pending_filename"
        ],
        "pending_sha256": document[
            "pending_sha256"
        ],
        "allowed_decision": document[
            "allowed_decision"
        ],
        "canonical_document_sha256": (
            canonical_sha256(document)
        ),
        "root_file_custody_validated": (
            False
        ),
        "reconciliation_authorization_consumed": (
            False
        ),
        "reconciliation_decision_record_created": (
            False
        ),
        "pending_record_modified": False,
        "pending_record_deleted": False,
        "pending_record_finalized": False,
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
        "RECONCILIATION_REFERENCE_POLICY_BINDING: PASS"
    )
    print(
        "IN_MEMORY_AUTHORIZATION_VALIDATOR: PASS"
    )
    print(
        "PENDING_FILENAME_IDENTITY_BINDING: ENABLED"
    )
    print(
        "PENDING_SHA256_VALIDATION: ENABLED"
    )
    print(
        "ALLOWED_DECISION_VALIDATION: ENABLED"
    )
    print(
        "TEMPORAL_VALIDATION: ENABLED"
    )
    print(
        "HOST_AUTHORIZATION_FILE_READ: FALSE"
    )
    print(
        "ROOT_FILE_CUSTODY_VALIDATED: FALSE"
    )
    print(
        "RECONCILIATION_AUTHORIZATION_CONSUMED: FALSE"
    )
    print(
        "RECONCILIATION_DECISION_RECORD_CREATED: FALSE"
    )
    print(
        "PENDING_RECORD_MODIFIED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "SERVICE_START_EXECUTED: FALSE"
    )
    print(
        "UNIT_ENABLE_EXECUTED: FALSE"
    )
    print("FINAL_DECISION: NO_GO")
    print(
        "SQL_B2_4B_5G_3B_1D_2B_10_"
        "RECONCILIATION_REFERENCE_VALIDATOR: PASS"
    )


if __name__ == "__main__":
    main()
