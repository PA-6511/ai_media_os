from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DESIGN_POLICY_RELATIVE = (
    "config/"
    "slack_worker_root_helper_plan_builder_policy.json"
)

EXPECTED_DESIGN_POLICY_SHA256 = (
    "e5ca8c97543cab19231bc41d930306d2463b61c4fc19aa2588630eb54bf89c9b"
)

EXPECTED_PLAN_SHA256 = (
    "f7f71ee447cc55020c4e87b8c2af56dfbaa432fe14af33108cb34792da35872d"
)

EXPECTED_PLAN_BYTES = 3401

EXPECTED_PLAN_KEY_COUNT = 18
EXPECTED_ORDERED_STAGE_COUNT = 17

EXPECTED_SOURCE_PATHS = {
    "root_helper": (
        "config/"
        "slack_worker_root_helper_interface_policy.json"
    ),
    "rollback": (
        "config/"
        "slack_worker_root_install_rollback_policy.json"
    ),
    "authorization": (
        "config/"
        "slack_worker_install_authorization_capsule_policy.json"
    ),
    "durable_consumption": (
        "config/"
        "slack_worker_install_authorization_"
        "durable_consumption_policy.json"
    ),
    "reconciliation": (
        "config/"
        "slack_worker_install_authorization_"
        "pending_reconciliation_policy.json"
    ),
    "assembler": (
        "config/"
        "slack_worker_offline_runtime_assembler_policy.json"
    ),
}

ALLOWED_RELATIVE_PATHS = frozenset(
    {
        DESIGN_POLICY_RELATIVE,
        *EXPECTED_SOURCE_PATHS.values(),
    }
)


class PlanBuilderError(ValueError):
    pass


def reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise PlanBuilderError(
                f"DUPLICATE_JSON_KEY:{key}"
            )

        result[key] = value

    return result


def _validate_allowed_path(
    path: Path,
) -> Path:
    if not isinstance(path, Path):
        raise PlanBuilderError(
            "PATH_OBJECT_REQUIRED"
        )

    allowed_paths = {
        REPO_ROOT / relative
        for relative in ALLOWED_RELATIVE_PATHS
    }

    if path not in allowed_paths:
        raise PlanBuilderError(
            "ARBITRARY_FILE_READ_REJECTED"
        )

    if path.is_symlink():
        raise PlanBuilderError(
            f"BOUND_PATH_SYMLINK_REJECTED:{path}"
        )

    if not path.is_file():
        raise PlanBuilderError(
            f"BOUND_FILE_MISSING:{path}"
        )

    current = path.parent

    while current != REPO_ROOT:
        if current.is_symlink():
            raise PlanBuilderError(
                f"BOUND_PATH_ANCESTRY_SYMLINK:{current}"
            )

        if REPO_ROOT not in current.parents:
            raise PlanBuilderError(
                "BOUND_PATH_ESCAPE_REJECTED"
            )

        current = current.parent

    return path


def load_json(
    path: Path,
) -> dict[str, Any]:
    validated = _validate_allowed_path(
        path
    )

    try:
        value = json.loads(
            validated.read_text(
                encoding="utf-8"
            ),
            object_pairs_hook=(
                reject_duplicate_keys
            ),
        )
    except PlanBuilderError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise PlanBuilderError(
            f"JSON_INVALID:{validated}"
        ) from exc

    if not isinstance(value, dict):
        raise PlanBuilderError(
            f"JSON_OBJECT_REQUIRED:{validated}"
        )

    return value


def canonical_bytes(
    value: object,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_path(
    path: Path,
) -> str:
    validated = _validate_allowed_path(
        path
    )

    return hashlib.sha256(
        validated.read_bytes()
    ).hexdigest()


def repository_path(
    relative: str,
) -> Path:
    if (
        not isinstance(relative, str)
        or relative not in ALLOWED_RELATIVE_PATHS
    ):
        raise PlanBuilderError(
            "REPOSITORY_PATH_NOT_ALLOWLISTED"
        )

    path = REPO_ROOT / relative

    return _validate_allowed_path(
        path
    )


def _require_false(
    value: dict[str, Any],
    keys: tuple[str, ...],
    *,
    label: str,
) -> None:
    for key in keys:
        if value.get(key) is not False:
            raise PlanBuilderError(
                f"{label}_FALSE_REQUIRED:{key}"
            )


def validate_policy() -> dict[str, Any]:
    policy_path = repository_path(
        DESIGN_POLICY_RELATIVE
    )

    if sha256_path(
        policy_path
    ) != EXPECTED_DESIGN_POLICY_SHA256:
        raise PlanBuilderError(
            "DESIGN_POLICY_HASH_INVALID"
        )

    policy = load_json(
        policy_path
    )

    if policy.get("phase") != (
        "SQL-B2-4B-5G-3B-1D-2D-1A"
    ):
        raise PlanBuilderError(
            "DESIGN_POLICY_PHASE_INVALID"
        )

    if policy.get("result") != (
        "PASS_UNPRIVILEGED_ROOT_HELPER_"
        "PLAN_BUILDER_POLICY_DESIGN_ONLY_"
        "NO_EXECUTION_NO_GO"
    ):
        raise PlanBuilderError(
            "DESIGN_POLICY_RESULT_INVALID"
        )

    runtime = policy.get(
        "planner_runtime_contract"
    )

    if not isinstance(runtime, dict):
        raise PlanBuilderError(
            "RUNTIME_CONTRACT_MISSING"
        )

    if runtime.get(
        "implementation_type"
    ) != "UNPRIVILEGED_PLAN_BUILDER":
        raise PlanBuilderError(
            "IMPLEMENTATION_TYPE_INVALID"
        )

    if runtime.get(
        "allowed_actions"
    ) != [
        "VALIDATE_CONTRACT",
        "RENDER_INSTALL_PLAN",
    ]:
        raise PlanBuilderError(
            "ALLOWED_ACTIONS_INVALID"
        )

    if runtime.get(
        "stdout_output_allowed"
    ) is not True:
        raise PlanBuilderError(
            "STDOUT_OUTPUT_NOT_ALLOWED"
        )

    if runtime.get(
        "stderr_error_output_allowed"
    ) is not True:
        raise PlanBuilderError(
            "STDERR_OUTPUT_NOT_ALLOWED"
        )

    _require_false(
        runtime,
        (
            "root_execution_required",
            "sudo_invocation_allowed",
            "shell_execution_allowed",
            "subprocess_allowed",
            "network_access_allowed",
            "database_access_allowed",
            "secret_file_read_allowed",
            "filesystem_write_allowed",
            "filesystem_delete_allowed",
            "filesystem_rename_allowed",
            "filesystem_permission_change_allowed",
            "symlink_creation_allowed",
            "environment_secret_access_allowed",
        ),
        label="RUNTIME_CONTRACT",
    )

    document = policy.get(
        "plan_document_contract"
    )

    if not isinstance(document, dict):
        raise PlanBuilderError(
            "PLAN_DOCUMENT_CONTRACT_MISSING"
        )

    expected_keys = [
        "schema_version",
        "plan_version",
        "phase",
        "release_id",
        "operation",
        "execution_allowed",
        "authorization_capsule_required",
        "authorization_capsule_issued",
        "root_helper_candidate_path",
        "final_release_path",
        "install_lock_path",
        "staging_path_template",
        "commit_point",
        "ordered_stages",
        "input_bindings",
        "constraints",
        "non_authorization_guarantee",
        "final_decision",
    ]

    if document.get(
        "exact_top_level_keys"
    ) != expected_keys:
        raise PlanBuilderError(
            "PLAN_DOCUMENT_KEYS_INVALID"
        )

    if document.get(
        "canonical_json_required"
    ) is not True:
        raise PlanBuilderError(
            "CANONICAL_JSON_NOT_REQUIRED"
        )

    if document.get(
        "deterministic_output_required"
    ) is not True:
        raise PlanBuilderError(
            "DETERMINISTIC_OUTPUT_NOT_REQUIRED"
        )

    if document.get(
        "authorization_capsule_required"
    ) is not True:
        raise PlanBuilderError(
            "AUTHORIZATION_REQUIREMENT_INVALID"
        )

    _require_false(
        document,
        (
            "timestamp_field_allowed",
            "nonce_field_allowed",
            "authorization_document_allowed",
            "execution_trigger_allowed",
            "execution_allowed",
            "authorization_capsule_issued",
        ),
        label="PLAN_DOCUMENT_CONTRACT",
    )

    if document.get(
        "final_decision"
    ) != "NO_GO":
        raise PlanBuilderError(
            "PLAN_DOCUMENT_FINAL_DECISION_INVALID"
        )

    bindings = policy.get(
        "bindings"
    )

    if not isinstance(bindings, dict):
        raise PlanBuilderError(
            "POLICY_BINDINGS_MISSING"
        )

    source_policies = bindings.get(
        "source_policies"
    )

    if (
        not isinstance(source_policies, dict)
        or set(source_policies)
        != set(EXPECTED_SOURCE_PATHS)
    ):
        raise PlanBuilderError(
            "SOURCE_POLICY_BINDING_SET_INVALID"
        )

    for name, expected_relative in (
        EXPECTED_SOURCE_PATHS.items()
    ):
        binding = source_policies.get(
            name
        )

        if not isinstance(binding, dict):
            raise PlanBuilderError(
                f"SOURCE_BINDING_INVALID:{name}"
            )

        if set(binding) != {
            "path",
            "sha256",
            "phase",
        }:
            raise PlanBuilderError(
                f"SOURCE_BINDING_KEYS_INVALID:{name}"
            )

        if binding.get(
            "path"
        ) != expected_relative:
            raise PlanBuilderError(
                f"SOURCE_PATH_INVALID:{name}"
            )

        source_path = repository_path(
            expected_relative
        )

        if sha256_path(
            source_path
        ) != binding.get(
            "sha256"
        ):
            raise PlanBuilderError(
                f"SOURCE_HASH_INVALID:{name}"
            )

        source_policy = load_json(
            source_path
        )

        if source_policy.get(
            "phase"
        ) != binding.get(
            "phase"
        ):
            raise PlanBuilderError(
                f"SOURCE_PHASE_INVALID:{name}"
            )

        governance = source_policy.get(
            "governance"
        )

        if (
            not isinstance(governance, dict)
            or governance.get(
                "final_decision"
            ) != "NO_GO"
        ):
            raise PlanBuilderError(
                f"SOURCE_STATE_INVALID:{name}"
            )

    fixed = policy.get(
        "fixed_plan_values"
    )

    if not isinstance(fixed, dict):
        raise PlanBuilderError(
            "FIXED_PLAN_VALUES_MISSING"
        )

    if bindings.get(
        "release_id"
    ) != fixed.get(
        "release_id"
    ):
        raise PlanBuilderError(
            "RELEASE_ID_BINDING_INVALID"
        )

    if bindings.get(
        "commit_point"
    ) != fixed.get(
        "commit_point"
    ):
        raise PlanBuilderError(
            "COMMIT_POINT_BINDING_INVALID"
        )

    if bindings.get(
        "ordered_stages"
    ) != fixed.get(
        "ordered_stages"
    ):
        raise PlanBuilderError(
            "ORDERED_STAGE_BINDING_INVALID"
        )

    if len(
        bindings.get(
            "ordered_stages",
            [],
        )
    ) != EXPECTED_ORDERED_STAGE_COUNT:
        raise PlanBuilderError(
            "ORDERED_STAGE_COUNT_INVALID"
        )

    governance = policy.get(
        "governance"
    )

    if not isinstance(governance, dict):
        raise PlanBuilderError(
            "GOVERNANCE_MISSING"
        )

    if governance.get(
        "plan_builder_policy_created"
    ) is not True:
        raise PlanBuilderError(
            "PLAN_POLICY_STATE_INVALID"
        )

    _require_false(
        governance,
        (
            "plan_builder_implemented",
            "plan_rendered",
            "root_helper_implemented",
            "root_helper_installed",
            "root_release_install_authorized",
            "root_release_install_executed",
            "authorization_capsule_issued",
            "authorization_capsule_consumed",
            "durable_consumption_record_created",
            "host_change_executed",
            "current_host_link_created",
            "secret_migration_executed",
            "systemd_operation_executed",
            "service_start_executed",
            "unit_enable_executed",
        ),
        label="DESIGN_GOVERNANCE",
    )

    if governance.get(
        "production_status"
    ) != "NO_GO":
        raise PlanBuilderError(
            "PRODUCTION_STATUS_INVALID"
        )

    if governance.get(
        "final_decision"
    ) != "NO_GO":
        raise PlanBuilderError(
            "FINAL_DECISION_INVALID"
        )

    return policy


def _expected_plan_from_policy(
    policy: dict[str, Any],
) -> dict[str, Any]:
    bindings = policy[
        "bindings"
    ]

    document = policy[
        "plan_document_contract"
    ]

    fixed = policy[
        "fixed_plan_values"
    ]

    return {
        "schema_version": (
            document[
                "schema_version"
            ]
        ),
        "plan_version": (
            document[
                "plan_version"
            ]
        ),
        "phase": (
            document[
                "phase"
            ]
        ),
        "release_id": (
            bindings[
                "release_id"
            ]
        ),
        "operation": (
            document[
                "operation"
            ]
        ),
        "execution_allowed": False,
        "authorization_capsule_required": True,
        "authorization_capsule_issued": False,
        "root_helper_candidate_path": (
            bindings[
                "root_helper_candidate_path"
            ]
        ),
        "final_release_path": (
            bindings[
                "final_release_path"
            ]
        ),
        "install_lock_path": (
            bindings[
                "install_lock_path"
            ]
        ),
        "staging_path_template": (
            bindings[
                "staging_path_template"
            ]
        ),
        "commit_point": (
            bindings[
                "commit_point"
            ]
        ),
        "ordered_stages": (
            bindings[
                "ordered_stages"
            ]
        ),
        "input_bindings": (
            bindings[
                "source_policies"
            ]
        ),
        "constraints": (
            fixed[
                "constraints"
            ]
        ),
        "non_authorization_guarantee": (
            fixed[
                "non_authorization_guarantee"
            ]
        ),
        "final_decision": "NO_GO",
    }


def build_plan_document() -> dict[str, Any]:
    policy = validate_policy()

    return _expected_plan_from_policy(
        policy
    )


def validate_plan_document(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise PlanBuilderError(
            "PLAN_OBJECT_REQUIRED"
        )

    policy = validate_policy()

    expected = _expected_plan_from_policy(
        policy
    )

    exact_keys = policy[
        "plan_document_contract"
    ]["exact_top_level_keys"]

    if list(plan) != exact_keys:
        raise PlanBuilderError(
            "PLAN_KEY_ORDER_INVALID"
        )

    if len(plan) != (
        EXPECTED_PLAN_KEY_COUNT
    ):
        raise PlanBuilderError(
            "PLAN_KEY_COUNT_INVALID"
        )

    if plan != expected:
        raise PlanBuilderError(
            "PLAN_CONTENT_INVALID"
        )

    if plan[
        "execution_allowed"
    ] is not False:
        raise PlanBuilderError(
            "PLAN_EXECUTION_INVALID"
        )

    if plan[
        "authorization_capsule_issued"
    ] is not False:
        raise PlanBuilderError(
            "PLAN_AUTHORIZATION_STATE_INVALID"
        )

    if plan[
        "authorization_capsule_required"
    ] is not True:
        raise PlanBuilderError(
            "PLAN_AUTHORIZATION_REQUIREMENT_INVALID"
        )

    if len(
        plan[
            "ordered_stages"
        ]
    ) != EXPECTED_ORDERED_STAGE_COUNT:
        raise PlanBuilderError(
            "PLAN_STAGE_COUNT_INVALID"
        )

    constraints = plan[
        "constraints"
    ]

    if constraints.get(
        "install_release_only"
    ) is not True:
        raise PlanBuilderError(
            "INSTALL_ONLY_CONSTRAINT_INVALID"
        )

    for key, value in constraints.items():
        if (
            key != "install_release_only"
            and value is not False
        ):
            raise PlanBuilderError(
                f"PLAN_CONSTRAINT_INVALID:{key}"
            )

    for key, value in plan[
        "non_authorization_guarantee"
    ].items():
        if value is not False:
            raise PlanBuilderError(
                "NON_AUTHORIZATION_INVALID:"
                f"{key}"
            )

    payload = canonical_bytes(
        plan
    )

    if len(payload) != EXPECTED_PLAN_BYTES:
        raise PlanBuilderError(
            "PLAN_BYTE_COUNT_INVALID"
        )

    if hashlib.sha256(
        payload
    ).hexdigest() != EXPECTED_PLAN_SHA256:
        raise PlanBuilderError(
            "PLAN_SHA256_INVALID"
        )

    return plan


def render_install_plan() -> bytes:
    plan = build_plan_document()

    validate_plan_document(
        plan
    )

    return canonical_bytes(
        plan
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=(
            "slack-worker-root-helper-"
            "plan-builder"
        ),
        allow_abbrev=False,
    )

    parser.add_argument(
        "--action",
        required=True,
        choices=(
            "VALIDATE_CONTRACT",
            "RENDER_INSTALL_PLAN",
        ),
    )

    arguments = parser.parse_args()

    try:
        if arguments.action == (
            "VALIDATE_CONTRACT"
        ):
            validate_policy()

            plan = build_plan_document()

            validate_plan_document(
                plan
            )

            result = {
                "action": (
                    "VALIDATE_CONTRACT"
                ),
                "design_policy_sha256": (
                    EXPECTED_DESIGN_POLICY_SHA256
                ),
                "expected_plan_sha256": (
                    EXPECTED_PLAN_SHA256
                ),
                "execution_allowed": False,
                "authorization_capsule_issued": (
                    False
                ),
                "root_release_install_authorized": (
                    False
                ),
                "root_release_install_executed": (
                    False
                ),
                "status": "PASS",
                "final_decision": "NO_GO",
            }

            sys.stdout.buffer.write(
                canonical_bytes(
                    result
                )
            )

            return

        sys.stdout.buffer.write(
            render_install_plan()
        )
    except PlanBuilderError as exc:
        error = {
            "error": str(exc),
            "status": "FAIL",
        }

        sys.stderr.write(
            canonical_bytes(
                error
            ).decode("utf-8")
        )

        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
