from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


repo = Path(__file__).resolve().parents[1]

interface_policy_path = (
    repo
    / "config/"
    "slack_worker_root_helper_"
    "interface_policy.json"
)


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


def resolve_repository_path(
    relative: str,
) -> Path:
    candidate = (
        repo / relative
    ).resolve()

    candidate.relative_to(
        repo.resolve()
    )

    return candidate


def validate_contract() -> dict[str, Any]:
    interface = load_json(
        interface_policy_path
    )

    if interface["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-2"
    ):
        raise SystemExit(
            "INTERFACE_PHASE_INVALID"
        )

    if interface["result"] != (
        "PASS_ROOT_HELPER_INTERFACE_"
        "PLAN_ONLY_NO_MUTATION_NO_GO"
    ):
        raise SystemExit(
            "INTERFACE_RESULT_INVALID"
        )

    bindings = interface["bindings"]

    binding_paths = (
        (
            "root_install_policy_path",
            "root_install_policy_sha256",
        ),
        (
            "release_policy_path",
            "release_policy_sha256",
        ),
        (
            "source_manifest_path",
            "source_manifest_sha256",
        ),
        (
            "preinstall_evidence_path",
            "preinstall_evidence_sha256",
        ),
    )

    loaded: dict[str, dict[str, Any]] = {}

    for path_key, hash_key in binding_paths:
        path = resolve_repository_path(
            bindings[path_key]
        )

        if not path.is_file():
            raise SystemExit(
                f"BOUND_INPUT_MISSING: {path_key}"
            )

        if sha256(path) != bindings[
            hash_key
        ]:
            raise SystemExit(
                f"BOUND_INPUT_HASH_INVALID: "
                f"{hash_key}"
            )

        loaded[path_key] = load_json(path)

    root_policy = loaded[
        "root_install_policy_path"
    ]

    source_manifest = loaded[
        "source_manifest_path"
    ]

    preinstall = loaded[
        "preinstall_evidence_path"
    ]

    root_binding = root_policy[
        "release_binding"
    ]

    if bindings["release_id"] != (
        root_binding["release_id"]
    ):
        raise SystemExit(
            "RELEASE_ID_BINDING_INVALID"
        )

    if bindings["release_id"] != (
        source_manifest[
            "release_id_candidate"
        ]
    ):
        raise SystemExit(
            "SOURCE_RELEASE_ID_INVALID"
        )

    if bindings[
        "final_release_path"
    ] != root_binding[
        "final_release_path"
    ]:
        raise SystemExit(
            "FINAL_RELEASE_BINDING_INVALID"
        )

    if bindings[
        "final_release_path"
    ] != preinstall[
        "target_paths"
    ]["candidate_release_path"]:
        raise SystemExit(
            "PREINSTALL_PATH_BINDING_INVALID"
        )

    cli = interface["cli_contract"]

    if cli["allowed_actions"] != [
        "VALIDATE_CONTRACT",
        "RENDER_INSTALL_PLAN",
    ]:
        raise SystemExit(
            "ALLOWED_ACTIONS_INVALID"
        )

    for key in (
        "install_action_exposed",
        "activate_action_exposed",
        "rollback_action_exposed",
        "cleanup_action_exposed",
        "authorization_issue_action_exposed",
        "arbitrary_source_argument_allowed",
        "arbitrary_target_argument_allowed",
    ):
        if cli[key] is not False:
            raise SystemExit(
                f"PROHIBITED_CLI_STATE: {key}"
            )

    plan = interface["plan_contract"]

    if plan["execution_allowed"] is not False:
        raise SystemExit(
            "EXECUTION_UNEXPECTEDLY_ALLOWED"
        )

    if plan[
        "authorization_capsule_issued"
    ] is not False:
        raise SystemExit(
            "AUTHORIZATION_UNEXPECTEDLY_ISSUED"
        )

    if plan[
        "root_helper_implemented"
    ] is not False:
        raise SystemExit(
            "ROOT_HELPER_UNEXPECTEDLY_IMPLEMENTED"
        )

    governance = interface["governance"]

    if governance[
        "root_release_install_authorized"
    ] is not False:
        raise SystemExit(
            "INSTALL_UNEXPECTEDLY_AUTHORIZED"
        )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise SystemExit(
            "FINAL_DECISION_INVALID"
        )

    return interface


def build_plan(
    interface: dict[str, Any],
) -> dict[str, Any]:
    bindings = interface["bindings"]
    contract = interface[
        "plan_contract"
    ]

    return {
        "phase": interface["phase"],
        "operation": contract[
            "operation"
        ],
        "release_id": bindings[
            "release_id"
        ],
        "install_root": bindings[
            "install_root"
        ],
        "release_root": bindings[
            "release_root"
        ],
        "final_release_path": bindings[
            "final_release_path"
        ],
        "current_link": bindings[
            "current_link"
        ],
        "source_file_count": bindings[
            "source_file_count"
        ],
        "wheel_count": bindings[
            "wheel_count"
        ],
        "ordered_stages": contract[
            "ordered_stages"
        ],
        "commit_point": contract[
            "commit_point"
        ],
        "execution_allowed": False,
        "authorization_capsule_required": (
            True
        ),
        "authorization_capsule_issued": (
            False
        ),
        "root_helper_implemented": False,
        "host_mutation_allowed": False,
        "current_link_change_allowed": (
            False
        ),
        "secret_migration_allowed": False,
        "systemd_operation_allowed": False,
        "service_start_allowed": False,
        "unit_enable_allowed": False,
        "production_database_write_allowed": (
            False
        ),
        "final_decision": "NO_GO",
    }


def render_text(
    plan: dict[str, Any],
) -> str:
    lines = [
        (
            "ROOT_HELPER_INTERFACE: "
            "PLAN_ONLY"
        ),
        (
            "RELEASE_ID: "
            f"{plan['release_id']}"
        ),
        (
            "FINAL_RELEASE_PATH: "
            f"{plan['final_release_path']}"
        ),
        (
            "ORDERED_STAGE_COUNT: "
            f"{len(plan['ordered_stages'])}"
        ),
        (
            "COMMIT_POINT: "
            f"{plan['commit_point']}"
        ),
        "EXECUTION_ALLOWED: FALSE",
        (
            "AUTHORIZATION_CAPSULE_"
            "ISSUED: FALSE"
        ),
        "ROOT_HELPER_IMPLEMENTED: FALSE",
        "HOST_MUTATION_ALLOWED: FALSE",
        "CURRENT_LINK_CHANGE_ALLOWED: FALSE",
        "SERVICE_START_ALLOWED: FALSE",
        "UNIT_ENABLE_ALLOWED: FALSE",
        "FINAL_DECISION: NO_GO",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or render the "
            "non-mutating Slack Worker "
            "root-install plan."
        )
    )

    parser.add_argument(
        "--action",
        required=True,
        choices=(
            "validate",
            "render-plan",
        ),
    )

    parser.add_argument(
        "--format",
        choices=(
            "text",
            "json",
        ),
        default="text",
    )

    arguments = parser.parse_args()

    interface = validate_contract()

    if arguments.action == "validate":
        print(
            "ROOT_HELPER_INTERFACE_BINDING: PASS"
        )
        print(
            "ROOT_HELPER_PLAN_ONLY_BOUNDARY: PASS"
        )
        print(
            "ROOT_RELEASE_INSTALL_AUTHORIZED: "
            "FALSE"
        )
        print(
            "AUTHORIZATION_CAPSULE_ISSUED: FALSE"
        )
        print(
            "ROOT_HELPER_IMPLEMENTED: FALSE"
        )
        print(
            "HOST_MUTATION_ALLOWED: FALSE"
        )
        print(
            "SERVICE_START_ALLOWED: FALSE"
        )
        print(
            "UNIT_ENABLE_ALLOWED: FALSE"
        )
        print("FINAL_DECISION: NO_GO")
        print(
            "SQL_B2_4B_5G_3B_1D_2B_2_"
            "ROOT_HELPER_INTERFACE: PASS"
        )

        return

    plan = build_plan(interface)

    if arguments.format == "json":
        print(
            json.dumps(
                plan,
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_text(plan))


if __name__ == "__main__":
    main()
