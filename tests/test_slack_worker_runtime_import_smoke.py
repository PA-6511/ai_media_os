from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest


repo = Path(__file__).resolve().parents[1]

runner = (
    repo
    / "scripts/"
    "slack_worker_runtime_import_smoke.py"
)

policy_path = (
    repo
    / "config/"
    "slack_worker_runtime_import_"
    "smoke_component_policy.json"
)


def write_module(
    root: Path,
    name: str,
    source: str,
) -> None:
    (
        root / f"{name}.py"
    ).write_text(
        source,
        encoding="utf-8",
    )


def write_config(
    tmp_path: Path,
    *,
    source_module: str,
    forbidden_prefix: Path,
) -> Path:
    modules = tmp_path / "modules"
    modules.mkdir(
        exist_ok=True,
    )

    config = {
        "schema_version": 1,
        "external_modules": [
            "json",
        ],
        "source_modules": [
            source_module,
        ],
        "expected_packages": {},
        "forbidden_path_prefixes": [
            str(forbidden_prefix),
        ],
        "pythonpath": str(modules),
        "working_directory": str(
            modules
        ),
    }

    path = tmp_path / "config.json"

    path.write_text(
        json.dumps(
            config,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def run_smoke(
    config: Path,
) -> subprocess.CompletedProcess[str]:
    sqlalchemy_spec = importlib.util.find_spec(
        "sqlalchemy"
    )
    assert sqlalchemy_spec is not None
    assert sqlalchemy_spec.origin is not None
    dependency_root = Path(
        sqlalchemy_spec.origin
    ).resolve().parents[1]
    subprocess_guard = (
        repo / "tests/pytest_subprocess_guard"
    )
    environment = {
        "PATH": os.environ.get(
            "PATH",
            "/usr/bin:/bin",
        ),
        "HOME": str(
            config.parent
        ),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "APP_ENV": "test",
        "AI_MEDIA_OS_TESTING": "1",
        "PYTHONPATH": os.pathsep.join(
            (
                str(subprocess_guard),
                str(repo),
                str(dependency_root),
            )
        ),
    }
    if os.environ.get("VIRTUAL_ENV"):
        environment["VIRTUAL_ENV"] = os.environ[
            "VIRTUAL_ENV"
        ]

    return subprocess.run(
        [
            sys.executable,
            str(runner),
            "--config",
            str(config),
        ],
        cwd=config.parent,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def test_policy_contract() -> None:
    policy = json.loads(
        policy_path.read_text(
            encoding="utf-8"
        )
    )

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2C-3B"
    )

    assert policy[
        "guard_contract"
    ][
        "entrypoint_execution_allowed"
    ] is False

    assert policy[
        "guard_contract"
    ][
        "sqlalchemy_engine_creation_allowed"
    ] is True

    assert policy[
        "guard_contract"
    ][
        "sqlalchemy_connection_allowed"
    ] is False

    assert policy[
        "guard_contract"
    ][
        "sqlite_dbapi2_connection_allowed"
    ] is False

    assert policy[
        "governance"
    ][
        "offline_runtime_assembler_implemented"
    ] is False

    assert policy[
        "governance"
    ]["final_decision"] == "NO_GO"


def test_safe_module_import_passes(
    tmp_path: Path,
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()

    write_module(
        modules,
        "safe_module",
        "VALUE = 1\n",
    )

    config = write_config(
        tmp_path,
        source_module="safe_module",
        forbidden_prefix=(
            tmp_path / "forbidden"
        ),
    )

    result = run_smoke(config)

    assert result.returncode == 0, (
        result.stdout
        + result.stderr
    )

    output = json.loads(
        result.stdout.strip()
    )

    assert output["status"] == "PASS"
    assert output["network_used"] is False
    assert output[
        "database_connected"
    ] is False
    assert output[
        "secret_path_read"
    ] is False
    assert output[
        "subprocess_started"
    ] is False
    assert output[
        "entrypoint_executed"
    ] is False


@pytest.mark.parametrize(
    ("module_name", "source"),
    [
        (
            "network_module",
            (
                "import socket\n"
                "socket.socket()\n"
            ),
        ),
        (
            "database_module",
            (
                "import sqlite3\n"
                "sqlite3.connect(':memory:')\n"
            ),
        ),
        (
            "process_module",
            (
                "import subprocess\n"
                "subprocess.run(['/bin/true'])\n"
            ),
        ),
    ],
)
def test_prohibited_operation_fails(
    tmp_path: Path,
    module_name: str,
    source: str,
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()

    write_module(
        modules,
        module_name,
        source,
    )

    config = write_config(
        tmp_path,
        source_module=module_name,
        forbidden_prefix=(
            tmp_path / "forbidden"
        ),
    )

    result = run_smoke(config)

    assert result.returncode == 1
    assert (
        "RUNTIME_SMOKE_"
        "PROHIBITED_OPERATION"
    ) in result.stderr


def test_forbidden_path_access_fails(
    tmp_path: Path,
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()

    forbidden = (
        tmp_path / "forbidden"
    )

    source = (
        "from pathlib import Path\n"
        f"Path({str(forbidden / 'x')!r})"
        ".write_text('x')\n"
    )

    write_module(
        modules,
        "path_module",
        source,
    )

    config = write_config(
        tmp_path,
        source_module="path_module",
        forbidden_prefix=forbidden,
    )

    result = run_smoke(config)

    assert result.returncode == 1

    assert (
        "RUNTIME_SMOKE_FORBIDDEN_PATH"
    ) in result.stderr

    assert not os.path.lexists(
        forbidden / "x"
    )


def test_unknown_config_key_rejected(
    tmp_path: Path,
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()

    write_module(
        modules,
        "safe_module",
        "VALUE = 1\n",
    )

    config = write_config(
        tmp_path,
        source_module="safe_module",
        forbidden_prefix=(
            tmp_path / "forbidden"
        ),
    )

    value = json.loads(
        config.read_text(
            encoding="utf-8"
        )
    )

    value["unexpected"] = True

    config.write_text(
        json.dumps(value),
        encoding="utf-8",
    )

    result = run_smoke(config)

    assert result.returncode == 1
    assert (
        "CONFIG_KEYS_INVALID"
    ) in result.stderr


def test_sqlalchemy_engine_construction_allowed(
    tmp_path: Path,
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()

    write_module(
        modules,
        "engine_module",
        (
            "import sqlalchemy\n"
            "import os\n"
            "assert os.environ.get("
            "'AI_MEDIA_OS_PYTEST_SUBPROCESS_GUARD_LOADED'"
            ") == '1'\n"
            "ENGINE = sqlalchemy.create_engine("
            "'sqlite:///:memory:'"
            ")\n"
        ),
    )

    config = write_config(
        tmp_path,
        source_module="engine_module",
        forbidden_prefix=(
            tmp_path / "forbidden"
        ),
    )

    result = run_smoke(config)

    assert result.returncode == 0, (
        result.stdout
        + result.stderr
    )

    output = json.loads(
        result.stdout.strip()
    )

    assert output["status"] == "PASS"

    assert output[
        "sqlalchemy_engine_creation_count"
    ] == 1

    assert output[
        "database_connected"
    ] is False


def test_sqlalchemy_engine_connection_rejected(
    tmp_path: Path,
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()

    write_module(
        modules,
        "engine_connect_module",
        (
            "import sqlalchemy\n"
            "import os\n"
            "assert os.environ.get("
            "'AI_MEDIA_OS_PYTEST_SUBPROCESS_GUARD_LOADED'"
            ") == '1'\n"
            "ENGINE = sqlalchemy.create_engine("
            "'sqlite:///:memory:'"
            ")\n"
            "ENGINE.connect()\n"
        ),
    )

    config = write_config(
        tmp_path,
        source_module="engine_connect_module",
        forbidden_prefix=(
            tmp_path / "forbidden"
        ),
    )

    result = run_smoke(config)

    assert result.returncode == 1

    assert (
        "RUNTIME_SMOKE_"
        "SQLALCHEMY_CONNECTION_OPERATION"
    ) in result.stderr


def test_sqlite_dbapi2_connection_rejected(
    tmp_path: Path,
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()

    write_module(
        modules,
        "sqlite_dbapi2_module",
        (
            "import sqlite3\n"
            "sqlite3.dbapi2.connect("
            "':memory:'"
            ")\n"
        ),
    )

    config = write_config(
        tmp_path,
        source_module="sqlite_dbapi2_module",
        forbidden_prefix=(
            tmp_path / "forbidden"
        ),
    )

    result = run_smoke(config)

    assert result.returncode == 1

    assert (
        "RUNTIME_SMOKE_"
        "PROHIBITED_OPERATION"
    ) in result.stderr
