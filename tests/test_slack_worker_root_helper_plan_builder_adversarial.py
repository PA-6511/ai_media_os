from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


repo = Path(__file__).resolve().parents[1]

script_path = (
    repo
    / "scripts/"
    "slack_worker_root_helper_plan_builder.py"
)

implementation_policy_path = (
    repo
    / "config/"
    "slack_worker_root_helper_plan_builder_"
    "implementation_policy.json"
)

expected_plan_sha256 = (
    "f7f71ee447cc55020c4e87b8c2af56df"
    "baa432fe14af33108cb34792da35872d"
)

expected_plan_bytes = 3401


specification = (
    importlib.util.spec_from_file_location(
        "adversarial_root_helper_plan_builder",
        script_path,
    )
)

assert specification is not None
assert specification.loader is not None

builder = importlib.util.module_from_spec(
    specification
)

specification.loader.exec_module(
    builder
)


def expect_rejection(
    operation,
) -> None:
    with pytest.raises(
        builder.PlanBuilderError
    ):
        operation()


def run_cli(
    arguments: list[str],
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            str(script_path),
            *arguments,
        ],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_adversarial_paths_and_duplicate_keys() -> None:
    operations = [
        lambda: builder.repository_path(
            "/etc/ai-media-os/slack.env"
        ),
        lambda: builder.repository_path(
            "../config/slack.env"
        ),
        lambda: builder.repository_path(
            ""
        ),
        lambda: builder.repository_path(
            "README.md"
        ),
        lambda: builder.load_json(
            Path(
                "/etc/ai-media-os/slack.env"
            )
        ),
        lambda: builder.reject_duplicate_keys(
            [
                ("duplicate", 1),
                ("duplicate", 2),
            ]
        ),
    ]

    for operation in operations:
        expect_rejection(
            operation
        )


def test_adversarial_plan_mutations() -> None:
    baseline = builder.build_plan_document()

    builder.validate_plan_document(
        baseline
    )

    mutations: list[dict[str, object]] = []

    execution_enabled = copy.deepcopy(
        baseline
    )
    execution_enabled[
        "execution_allowed"
    ] = True
    mutations.append(
        execution_enabled
    )

    authorization_issued = copy.deepcopy(
        baseline
    )
    authorization_issued[
        "authorization_capsule_issued"
    ] = True
    mutations.append(
        authorization_issued
    )

    release_changed = copy.deepcopy(
        baseline
    )
    release_changed[
        "release_id"
    ] = "attacker-controlled-release"
    mutations.append(
        release_changed
    )

    stage_reordered = copy.deepcopy(
        baseline
    )
    stages = stage_reordered[
        "ordered_stages"
    ]

    assert isinstance(stages, list)

    stages[0], stages[1] = (
        stages[1],
        stages[0],
    )

    mutations.append(
        stage_reordered
    )

    source_hash_changed = copy.deepcopy(
        baseline
    )

    input_bindings = source_hash_changed[
        "input_bindings"
    ]

    assert isinstance(
        input_bindings,
        dict,
    )

    assembler_binding = input_bindings[
        "assembler"
    ]

    assert isinstance(
        assembler_binding,
        dict,
    )

    assembler_binding[
        "sha256"
    ] = "0" * 64

    mutations.append(
        source_hash_changed
    )

    key_removed = copy.deepcopy(
        baseline
    )
    key_removed.pop(
        "final_decision"
    )
    mutations.append(
        key_removed
    )

    key_added = copy.deepcopy(
        baseline
    )
    key_added[
        "execution_trigger"
    ] = True
    mutations.append(
        key_added
    )

    service_start_allowed = copy.deepcopy(
        baseline
    )

    constraints = service_start_allowed[
        "constraints"
    ]

    assert isinstance(
        constraints,
        dict,
    )

    constraints[
        "service_start_allowed"
    ] = True

    mutations.append(
        service_start_allowed
    )

    for mutation in mutations:
        expect_rejection(
            lambda value=mutation: (
                builder.validate_plan_document(
                    value
                )
            )
        )


def test_adversarial_cli_rejections() -> None:
    invalid_cases = [
        [],
        [
            "--action",
            "INSTALL_RELEASE",
        ],
        [
            "--action",
            "ROLLBACK",
        ],
        [
            "--action",
            "ACTIVATE",
        ],
        [
            "--action",
            "RENDER_INSTALL_PLAN",
            "--output",
            "/tmp/plan.json",
        ],
        [
            "--action",
            "RENDER_INSTALL_PLAN",
            "--source",
            "/tmp/source",
        ],
        [
            "--action",
            "RENDER_INSTALL_PLAN",
            "--authorization",
            "/tmp/capsule.json",
        ],
    ]

    for arguments in invalid_cases:
        result = run_cli(
            arguments
        )

        assert result.returncode != 0
        assert result.stdout == b""


def test_adversarial_scope_and_determinism() -> None:
    implementation_policy = json.loads(
        implementation_policy_path.read_text(
            encoding="utf-8"
        )
    )

    assert implementation_policy[
        "governance"
    ]["final_decision"] == "NO_GO"

    payload_first = (
        builder.render_install_plan()
    )

    payload_second = (
        builder.render_install_plan()
    )

    assert payload_first == payload_second
    assert len(
        payload_first
    ) == expected_plan_bytes

    assert hashlib.sha256(
        payload_first
    ).hexdigest() == expected_plan_sha256

    source = script_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    forbidden_import_roots = {
        "ctypes",
        "fcntl",
        "http",
        "os",
        "requests",
        "shutil",
        "socket",
        "sqlite3",
        "subprocess",
        "tempfile",
        "urllib",
    }

    actual_import_roots: set[str] = set()

    for node in tree.body:
        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                actual_import_roots.add(
                    alias.name.split(
                        ".",
                        1,
                    )[0]
                )

        if isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module == "__future__":
                continue

            if node.module is not None:
                actual_import_roots.add(
                    node.module.split(
                        ".",
                        1,
                    )[0]
                )

    assert not (
        actual_import_roots
        & forbidden_import_roots
    )

    forbidden_methods = {
        "write_text",
        "write_bytes",
        "mkdir",
        "unlink",
        "rename",
        "replace",
        "chmod",
        "symlink_to",
        "hardlink_to",
        "touch",
    }

    forbidden_names = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "open",
    }

    for node in ast.walk(tree):
        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if isinstance(
            node.func,
            ast.Attribute,
        ):
            assert (
                node.func.attr
                not in forbidden_methods
            )

        if isinstance(
            node.func,
            ast.Name,
        ):
            assert (
                node.func.id
                not in forbidden_names
            )
