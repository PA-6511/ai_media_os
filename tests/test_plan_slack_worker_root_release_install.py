from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_root_helper_"
    "interface_policy.json"
)

planner_path = (
    repo
    / "scripts/"
    "plan_slack_worker_root_"
    "release_install.py"
)


def load_policy() -> dict:
    return json.loads(
        policy_path.read_text(
            encoding="utf-8"
        )
    )


def run_planner(
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(planner_path),
            *arguments,
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_validate_action_passes() -> None:
    result = run_planner(
        "--action",
        "validate",
    )

    assert result.returncode == 0, (
        result.stdout
    )

    assert (
        "SQL_B2_4B_5G_3B_1D_2B_2_"
        "ROOT_HELPER_INTERFACE: PASS"
        in result.stdout
    )

    assert (
        "FINAL_DECISION: NO_GO"
        in result.stdout
    )


def test_render_plan_json_is_no_go() -> None:
    result = run_planner(
        "--action",
        "render-plan",
        "--format",
        "json",
    )

    assert result.returncode == 0, (
        result.stdout
    )

    plan = json.loads(
        result.stdout
    )

    assert plan[
        "execution_allowed"
    ] is False

    assert plan[
        "authorization_capsule_issued"
    ] is False

    assert plan[
        "root_helper_implemented"
    ] is False

    assert plan[
        "host_mutation_allowed"
    ] is False

    assert plan[
        "final_decision"
    ] == "NO_GO"


def test_plan_stage_order_matches_contract() -> None:
    policy = load_policy()

    root_policy_path = (
        repo
        / policy["bindings"][
            "root_install_policy_path"
        ]
    )

    root_policy = json.loads(
        root_policy_path.read_text(
            encoding="utf-8"
        )
    )

    assert policy[
        "plan_contract"
    ]["ordered_stages"] == root_policy[
        "install_transaction"
    ]["ordered_stages"]

    assert policy[
        "plan_contract"
    ]["commit_point"] == root_policy[
        "install_transaction"
    ]["commit_point"]


def test_no_install_cli_action_is_exposed() -> None:
    result = run_planner(
        "--help",
    )

    assert result.returncode == 0

    assert "--install" not in (
        result.stdout
    )

    assert "--activate" not in (
        result.stdout
    )

    assert "--rollback" not in (
        result.stdout
    )


def test_planner_imports_are_non_mutating() -> None:
    source = planner_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    imported = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name.split(".")[0]
                for alias in node.names
            )

        if isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module:
                imported.add(
                    node.module.split(".")[0]
                )

    assert imported <= {
        "__future__",
        "argparse",
        "hashlib",
        "json",
        "pathlib",
        "typing",
    }


def test_planner_has_no_mutation_calls() -> None:
    source = planner_path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    forbidden_attributes = {
        "write_text",
        "write_bytes",
        "mkdir",
        "makedirs",
        "unlink",
        "remove",
        "rmdir",
        "rename",
        "replace",
        "chmod",
        "chown",
        "touch",
        "symlink_to",
        "hardlink_to",
        "copy",
        "copy2",
        "copyfile",
        "move",
        "run",
        "call",
        "check_call",
        "check_output",
        "Popen",
    }

    detected = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr
        in forbidden_attributes
    }

    assert detected == set()


def test_planner_source_has_no_secret_or_db_access() -> None:
    source = planner_path.read_text(
        encoding="utf-8"
    )

    forbidden = (
        "slack.env",
        "credential.env",
        "database.env",
        "sqlite3",
        "sqlalchemy",
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
    )

    for value in forbidden:
        assert value not in source


def test_interface_governance_remains_no_go() -> None:
    governance = load_policy()[
        "governance"
    ]

    assert governance[
        "design_and_plan_only"
    ] is True

    assert governance[
        "host_change_executed"
    ] is False

    assert governance[
        "root_release_install_authorized"
    ] is False

    assert governance[
        "authorization_capsule_issued"
    ] is False

    assert governance[
        "root_helper_installed"
    ] is False

    assert governance[
        "service_start_executed"
    ] is False

    assert governance[
        "unit_enable_executed"
    ] is False

    assert governance[
        "final_decision"
    ] == "NO_GO"
