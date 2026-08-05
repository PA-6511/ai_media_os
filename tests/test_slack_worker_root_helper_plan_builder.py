from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
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

specification = (
    importlib.util
    .spec_from_file_location(
        "root_helper_plan_builder",
        script_path,
    )
)

assert specification is not None
assert specification.loader is not None

builder = (
    importlib.util
    .module_from_spec(
        specification
    )
)

specification.loader.exec_module(
    builder
)


EXPECTED_PLAN_SHA256 = (
    "f7f71ee447cc55020c4e87b8c2af56dfbaa432fe14af33108cb34792da35872d"
)


def test_validate_policy() -> None:
    policy = builder.validate_policy()

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2D-1A"
    )

    assert policy[
        "governance"
    ]["final_decision"] == "NO_GO"


def test_plan_hash_and_size() -> None:
    payload = builder.render_install_plan()

    assert len(payload) == 3401

    assert hashlib.sha256(
        payload
    ).hexdigest() == EXPECTED_PLAN_SHA256


def test_plan_key_order() -> None:
    policy = builder.validate_policy()
    plan = builder.build_plan_document()

    assert list(plan) == policy[
        "plan_document_contract"
    ]["exact_top_level_keys"]

    assert len(plan) == 18


def test_plan_non_execution_boundary() -> None:
    plan = builder.build_plan_document()

    assert plan[
        "execution_allowed"
    ] is False

    assert plan[
        "authorization_capsule_required"
    ] is True

    assert plan[
        "authorization_capsule_issued"
    ] is False

    assert plan[
        "final_decision"
    ] == "NO_GO"


def test_plan_stage_contract() -> None:
    plan = builder.build_plan_document()

    assert len(
        plan[
            "ordered_stages"
        ]
    ) == 17

    assert plan[
        "commit_point"
    ] == (
        "ATOMIC_RENAME_STAGING_TO_FINAL_RELEASE"
    )


def test_render_is_deterministic() -> None:
    first = builder.render_install_plan()
    second = builder.render_install_plan()

    assert first == second
    assert first.endswith(b"\n")
    assert first.count(b"\n") == 1


def test_repository_path_rejects_unlisted() -> None:
    with pytest.raises(
        builder.PlanBuilderError,
        match=(
            "REPOSITORY_PATH_NOT_ALLOWLISTED"
        ),
    ):
        builder.repository_path(
            "/etc/ai-media-os/slack.env"
        )


def test_duplicate_keys_rejected() -> None:
    with pytest.raises(
        builder.PlanBuilderError,
        match="DUPLICATE_JSON_KEY:a",
    ):
        builder.reject_duplicate_keys(
            [
                ("a", 1),
                ("a", 2),
            ]
        )


def test_cli_validate_contract(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script_path),
            "--action",
            "VALIDATE_CONTRACT",
        ],
    )

    builder.main()

    stdout, stderr = (
        capfd.readouterr()
    )

    assert stderr == ""

    result = json.loads(
        stdout
    )

    assert result["status"] == "PASS"
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "authorization_capsule_issued"
    ] is False
    assert result[
        "root_release_install_executed"
    ] is False
    assert result[
        "final_decision"
    ] == "NO_GO"


def test_cli_render_plan(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script_path),
            "--action",
            "RENDER_INSTALL_PLAN",
        ],
    )

    builder.main()

    stdout, stderr = (
        capfd.readouterr()
    )

    assert stderr == ""

    payload = stdout.encode(
        "utf-8"
    )

    assert hashlib.sha256(
        payload
    ).hexdigest() == EXPECTED_PLAN_SHA256


def test_public_surface() -> None:
    source = script_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    public_functions = sorted(
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and not node.name.startswith("_")
    )

    assert public_functions == sorted(
        [
            "reject_duplicate_keys",
            "load_json",
            "canonical_bytes",
            "sha256_path",
            "repository_path",
            "validate_policy",
            "build_plan_document",
            "validate_plan_document",
            "render_install_plan",
            "main",
        ]
    )

    public_classes = sorted(
        node.name
        for node in tree.body
        if isinstance(
            node,
            ast.ClassDef,
        )
        and not node.name.startswith("_")
    )

    assert public_classes == [
        "PlanBuilderError"
    ]


def test_import_and_write_boundary() -> None:
    source = script_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    import_roots: set[str] = set()

    for node in tree.body:
        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:
                import_roots.add(
                    alias.name.split(
                        ".",
                        1,
                    )[0]
                )

        if isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module == (
                "__future__"
            ):
                continue

            if node.module is not None:
                import_roots.add(
                    node.module.split(
                        ".",
                        1,
                    )[0]
                )

    assert import_roots == {
        "argparse",
        "hashlib",
        "json",
        "pathlib",
        "sys",
        "typing",
    }

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

        if (
            isinstance(
                node.func,
                ast.Attribute,
            )
            and node.func.attr
            in forbidden_methods
        ):
            pytest.fail(
                "forbidden filesystem method: "
                f"{node.func.attr}"
            )

        if (
            isinstance(
                node.func,
                ast.Name,
            )
            and node.func.id
            in forbidden_names
        ):
            pytest.fail(
                "forbidden dynamic or file API: "
                f"{node.func.id}"
            )

    for forbidden_token_name in (
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
    ):
        assert forbidden_token_name not in source


def test_implementation_policy_binding() -> None:
    policy = json.loads(
        implementation_policy_path.read_text(
            encoding="utf-8"
        )
    )

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2D-1B"
    )

    assert policy[
        "bindings"
    ][
        "implementation_script_sha256"
    ] == hashlib.sha256(
        script_path.read_bytes()
    ).hexdigest()

    assert policy[
        "bindings"
    ][
        "expected_plan_sha256"
    ] == EXPECTED_PLAN_SHA256

    assert policy[
        "governance"
    ][
        "root_helper_implemented"
    ] is False

    assert policy[
        "governance"
    ][
        "root_release_install_executed"
    ] is False

    assert policy[
        "governance"
    ][
        "final_decision"
    ] == "NO_GO"
