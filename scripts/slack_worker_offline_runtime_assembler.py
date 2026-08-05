from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from types import ModuleType
from typing import Any


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_offline_runtime_assembler_policy.json"
)


class RuntimeAssemblerError(ValueError):
    pass


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


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise RuntimeAssemblerError(
                f"DUPLICATE_JSON_KEY:{key}"
            )

        result[key] = value

    return result


def load_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            ),
            object_pairs_hook=(
                reject_duplicate_keys
            ),
        )
    except RuntimeAssemblerError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeAssemblerError(
            f"JSON_INVALID:{path}"
        ) from exc

    if not isinstance(value, dict):
        raise RuntimeAssemblerError(
            f"JSON_OBJECT_REQUIRED:{path}"
        )

    return value


def sha256_path(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    flags = (
        os.O_RDONLY
        | os.O_CLOEXEC
    )

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(
            os.fspath(path),
            flags,
        )
    except OSError as exc:
        raise RuntimeAssemblerError(
            f"HASH_INPUT_OPEN_FAILED:{path}"
        ) from exc

    try:
        value = os.fstat(
            descriptor
        )

        if (
            not stat.S_ISREG(
                value.st_mode
            )
            or value.st_nlink != 1
        ):
            raise RuntimeAssemblerError(
                f"HASH_INPUT_CUSTODY_INVALID:{path}"
            )

        while True:
            chunk = os.read(
                descriptor,
                65536,
            )

            if not chunk:
                break

            digest.update(chunk)
    finally:
        os.close(descriptor)

    return digest.hexdigest()


def repository_path(
    relative: str,
) -> Path:
    candidate = (
        repo / relative
    ).resolve()

    try:
        candidate.relative_to(
            repo.resolve()
        )
    except ValueError as exc:
        raise RuntimeAssemblerError(
            "REPOSITORY_PATH_ESCAPE"
        ) from exc

    return candidate


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    specification = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeAssemblerError(
            f"MODULE_LOAD_FAILED:{name}"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


def validate_policy(
) -> tuple[
    dict[str, Any],
    ModuleType,
    ModuleType,
]:
    policy = load_json(
        policy_path
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2C-3C"
    ):
        raise RuntimeAssemblerError(
            "POLICY_PHASE_INVALID"
        )

    if policy["revision"] != 2:
        raise RuntimeAssemblerError(
            "POLICY_REVISION_INVALID"
        )

    if policy["result"] != (
        "PASS_OFFLINE_RUNTIME_ASSEMBLER_"
        "TMP_ONLY_SMOKE_REVISION_2_"
        "NO_HOST_INSTALL_NO_GO"
    ):
        raise RuntimeAssemblerError(
            "POLICY_RESULT_INVALID"
        )

    bindings = policy[
        "bindings"
    ]

    path_hash_pairs = (
        (
            "adapter_policy_path",
            "adapter_policy_sha256",
        ),
        (
            "adapter_source_path",
            "adapter_source_sha256",
        ),
        (
            "core_policy_path",
            "core_policy_sha256",
        ),
        (
            "core_source_path",
            "core_source_sha256",
        ),
        (
            "smoke_policy_path",
            "smoke_policy_sha256",
        ),
        (
            "smoke_runner_path",
            "smoke_runner_sha256",
        ),
        (
            "source_manifest_path",
            "source_manifest_sha256",
        ),
        (
            "requirements_lock_path",
            "requirements_lock_sha256",
        ),
        (
            "release_policy_path",
            "release_policy_sha256",
        ),
    )

    resolved: dict[str, Path] = {}

    for path_key, hash_key in (
        path_hash_pairs
    ):
        path = repository_path(
            bindings[path_key]
        )

        if not path.is_file():
            raise RuntimeAssemblerError(
                f"BOUND_INPUT_MISSING:{path_key}"
            )

        if sha256_path(path) != bindings[
            hash_key
        ]:
            raise RuntimeAssemblerError(
                f"BOUND_INPUT_HASH_INVALID:{hash_key}"
            )

        resolved[path_key] = path

    adapter = load_module(
        "runtime_bundle_adapter",
        resolved[
            "adapter_source_path"
        ],
    )

    core = load_module(
        "runtime_installer_core",
        resolved[
            "core_source_path"
        ],
    )

    adapter.validate_policy()
    core.validate_policy()

    smoke_policy = load_json(
        resolved[
            "smoke_policy_path"
        ]
    )

    if smoke_policy["revision"] != 2:
        raise RuntimeAssemblerError(
            "BOUND_SMOKE_REVISION_INVALID"
        )

    if smoke_policy[
        "bindings"
    ]["release_id"] != bindings[
        "release_id"
    ]:
        raise RuntimeAssemblerError(
            "BOUND_SMOKE_RELEASE_INVALID"
        )

    smoke_contract = policy[
        "smoke_contract"
    ]

    if smoke_contract[
        "engine_construction_allowed"
    ] is not True:
        raise RuntimeAssemblerError(
            "ENGINE_CONSTRUCTION_POLICY_INVALID"
        )

    if smoke_contract[
        "engine_creation_count_required"
    ] != 1:
        raise RuntimeAssemblerError(
            "ENGINE_COUNT_POLICY_INVALID"
        )

    if smoke_contract[
        "sqlalchemy_connection_allowed"
    ] is not False:
        raise RuntimeAssemblerError(
            "SQLALCHEMY_CONNECTION_POLICY_INVALID"
        )

    if smoke_contract[
        "sqlite_connection_allowed"
    ] is not False:
        raise RuntimeAssemblerError(
            "SQLITE_CONNECTION_POLICY_INVALID"
        )

    governance = policy[
        "governance"
    ]

    if governance[
        "offline_runtime_assembler_implemented"
    ] is not True:
        raise RuntimeAssemblerError(
            "ASSEMBLER_STATE_INVALID"
        )

    for key in (
        "host_change_executed",
        "root_release_install_authorized",
        "root_release_install_executed",
        "authorization_capsule_issued",
        "authorization_capsule_consumed",
        "host_consumption_record_created",
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
            raise RuntimeAssemblerError(
                f"GOVERNANCE_STATE_INVALID:{key}"
            )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise RuntimeAssemblerError(
            "FINAL_DECISION_INVALID"
        )

    return policy, adapter, core


def lexists(
    path: Path,
) -> bool:
    return os.path.lexists(
        os.fspath(path)
    )


def validate_tmp_path(
    value: Path,
    *,
    field_name: str,
    must_exist: bool,
) -> Path:
    path = Path(
        os.path.abspath(
            os.fspath(value)
        )
    )

    tmp_root = Path("/tmp")

    if path == tmp_root:
        raise RuntimeAssemblerError(
            f"{field_name}_DIRECT_TMP_REJECTED"
        )

    if tmp_root not in path.parents:
        raise RuntimeAssemblerError(
            f"{field_name}_OUTSIDE_TMP_REJECTED"
        )

    current = (
        path
        if lexists(path)
        else path.parent
    )

    while current != tmp_root:
        if lexists(current):
            value_stat = current.lstat()

            if stat.S_ISLNK(
                value_stat.st_mode
            ):
                raise RuntimeAssemblerError(
                    f"{field_name}_SYMLINK_ANCESTRY_REJECTED"
                )

        current = current.parent

    if must_exist:
        if (
            path.is_symlink()
            or not path.is_dir()
        ):
            raise RuntimeAssemblerError(
                f"{field_name}_INVALID"
            )

    return path


def validate_transaction_id(
    transaction_id: str,
) -> None:
    if re.fullmatch(
        r"^[a-f0-9]{32}$",
        transaction_id,
    ) is None:
        raise RuntimeAssemblerError(
            "TRANSACTION_ID_INVALID"
        )


def open_lock(
    path: Path,
) -> int:
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_CLOEXEC
    )

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(
        os.fspath(path),
        flags,
        0o600,
    )

    os.fchmod(
        descriptor,
        0o600,
    )

    value = os.fstat(
        descriptor
    )

    if (
        not stat.S_ISREG(
            value.st_mode
        )
        or value.st_nlink != 1
    ):
        os.close(descriptor)

        raise RuntimeAssemblerError(
            "RUNTIME_LOCK_CUSTODY_INVALID"
        )

    return descriptor


def fsync_directory(
    path: Path,
) -> None:
    flags = (
        os.O_RDONLY
        | os.O_CLOEXEC
    )

    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    descriptor = os.open(
        os.fspath(path),
        flags,
    )

    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_all(
    descriptor: int,
    payload: bytes,
) -> None:
    offset = 0

    while offset < len(payload):
        written = os.write(
            descriptor,
            payload[offset:],
        )

        if written <= 0:
            raise RuntimeAssemblerError(
                "DESTINATION_SHORT_WRITE"
            )

        offset += written


def write_exclusive(
    path: Path,
    payload: bytes,
    mode: int,
) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_CLOEXEC
    )

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(
        os.fspath(path),
        flags,
        mode,
    )

    try:
        os.fchmod(
            descriptor,
            mode,
        )

        write_all(
            descriptor,
            payload,
        )

        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def copy_bound_file(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str,
    mode: int,
) -> None:
    value = source.lstat()

    if (
        stat.S_ISLNK(value.st_mode)
        or not stat.S_ISREG(
            value.st_mode
        )
        or value.st_nlink != 1
    ):
        raise RuntimeAssemblerError(
            f"COPY_SOURCE_CUSTODY_INVALID:{source}"
        )

    source_flags = (
        os.O_RDONLY
        | os.O_CLOEXEC
    )

    destination_flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_CLOEXEC
    )

    if hasattr(os, "O_NOFOLLOW"):
        source_flags |= os.O_NOFOLLOW
        destination_flags |= os.O_NOFOLLOW

    source_descriptor = os.open(
        os.fspath(source),
        source_flags,
    )

    destination_descriptor = os.open(
        os.fspath(destination),
        destination_flags,
        mode,
    )

    digest = hashlib.sha256()

    try:
        os.fchmod(
            destination_descriptor,
            mode,
        )

        while True:
            chunk = os.read(
                source_descriptor,
                65536,
            )

            if not chunk:
                break

            digest.update(chunk)

            write_all(
                destination_descriptor,
                chunk,
            )

        os.fsync(
            destination_descriptor
        )
    finally:
        os.close(
            destination_descriptor
        )

        os.close(
            source_descriptor
        )

    if digest.hexdigest() != (
        expected_sha256
    ):
        raise RuntimeAssemblerError(
            f"COPIED_HASH_MISMATCH:{source}"
        )


def ensure_directory(
    path: Path,
    mode: int,
) -> None:
    if lexists(path):
        value = path.lstat()

        if (
            stat.S_ISLNK(value.st_mode)
            or not stat.S_ISDIR(
                value.st_mode
            )
        ):
            raise RuntimeAssemblerError(
                f"DIRECTORY_INVALID:{path}"
            )
    else:
        path.mkdir(
            mode=mode,
            parents=False,
        )

    os.chmod(
        path,
        mode,
    )


def remove_owned_tree(
    path: Path,
) -> None:
    if not lexists(path):
        return

    validated = validate_tmp_path(
        path,
        field_name="CLEANUP_ROOT",
        must_exist=False,
    )

    if validated.is_symlink():
        validated.unlink()
        return

    if validated.is_dir():
        shutil.rmtree(
            validated
        )
        return

    validated.unlink()


def command_environment(
    runtime_root: Path,
    home: Path,
) -> dict[str, str]:
    return {
        "PATH": (
            str(
                runtime_root
                / "venv/bin"
            )
            + ":/usr/bin:/bin"
        ),
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONPATH": str(
            runtime_root / "src"
        ),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": (
            "1"
        ),
        "PIP_CONFIG_FILE": "/dev/null",
        "PIP_NO_CACHE_DIR": "1",
    }


def run_allowed_command(
    *,
    role: str,
    command: list[str],
    runtime_root: Path,
    cwd: Path,
    environment: dict[str, str],
    policy: dict[str, Any],
) -> str:
    if not command:
        raise RuntimeAssemblerError(
            "EMPTY_COMMAND"
        )

    system_python = policy[
        "bindings"
    ]["system_python"]

    venv_python = str(
        runtime_root
        / "venv/bin/python"
    )

    if role == "SYSTEM_PYTHON":
        if command != [
            system_python,
            "-m",
            "venv",
            "--symlinks",
            str(
                runtime_root / "venv"
            ),
        ]:
            raise RuntimeAssemblerError(
                "SYSTEM_PYTHON_COMMAND_INVALID"
            )

    elif role == "VENV_PYTHON":
        if command[0] != venv_python:
            raise RuntimeAssemblerError(
                "VENV_PYTHON_COMMAND_INVALID"
            )

        pip_install = (
            len(command) >= 4
            and command[1:4]
            == [
                "-m",
                "pip",
                "install",
            ]
        )

        pip_check = (
            command[1:]
            == [
                "-m",
                "pip",
                "check",
            ]
        )

        smoke_runner = str(
            runtime_root
            / "manifest/"
            "runtime-import-smoke.py"
        )

        smoke = (
            len(command) == 4
            and command[1] == smoke_runner
            and command[2] == "--config"
        )

        if not (
            pip_install
            or pip_check
            or smoke
        ):
            raise RuntimeAssemblerError(
                "VENV_PYTHON_COMMAND_INVALID"
            )
    else:
        raise RuntimeAssemblerError(
            "COMMAND_ROLE_INVALID"
        )

    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=policy[
            "command_contract"
        ]["timeout_seconds"],
        check=False,
    )

    output = result.stdout

    maximum = policy[
        "command_contract"
    ]["maximum_output_bytes"]

    if len(
        output.encode("utf-8")
    ) > maximum:
        output = output[-maximum:]

    if result.returncode != 0:
        raise RuntimeAssemblerError(
            "COMMAND_FAILED:"
            f"{role}:"
            f"{result.returncode}:"
            f"{output[-8000:]}"
        )

    return output


def validate_venv_python(
    runtime_root: Path,
    policy: dict[str, Any],
) -> Path:
    venv_python = (
        runtime_root
        / "venv/bin/python"
    )

    if not lexists(venv_python):
        raise RuntimeAssemblerError(
            "VENV_PYTHON_MISSING"
        )

    if not venv_python.is_symlink():
        raise RuntimeAssemblerError(
            "VENV_PYTHON_SYMLINK_REQUIRED"
        )

    resolved = venv_python.resolve(
        strict=True
    )

    if resolved != Path(
        policy[
            "bindings"
        ]["resolved_system_python"]
    ):
        raise RuntimeAssemblerError(
            "VENV_PYTHON_TARGET_INVALID"
        )

    value = resolved.stat()

    if value.st_uid != 0:
        raise RuntimeAssemblerError(
            "VENV_PYTHON_OWNER_INVALID"
        )

    if value.st_mode & (
        stat.S_IWGRP
        | stat.S_IWOTH
    ):
        raise RuntimeAssemblerError(
            "VENV_PYTHON_TARGET_WRITABLE"
        )

    return venv_python


def build_smoke_config(
    runtime_root: Path,
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "external_modules": policy[
            "smoke_contract"
        ]["external_modules"],
        "source_modules": policy[
            "smoke_contract"
        ]["source_modules"],
        "expected_packages": policy[
            "offline_install_contract"
        ]["exact_expected_packages"],
        "forbidden_path_prefixes": policy[
            "smoke_contract"
        ]["forbidden_path_prefixes"],
        "pythonpath": str(
            runtime_root / "src"
        ),
        "working_directory": str(
            runtime_root / "src"
        ),
    }


def parse_smoke_output(
    output: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    lines = [
        line
        for line in output.splitlines()
        if line.strip()
    ]

    if not lines:
        raise RuntimeAssemblerError(
            "SMOKE_OUTPUT_EMPTY"
        )

    try:
        value = json.loads(
            lines[-1]
        )
    except json.JSONDecodeError as exc:
        raise RuntimeAssemblerError(
            "SMOKE_OUTPUT_INVALID"
        ) from exc

    if value.get("status") != "PASS":
        raise RuntimeAssemblerError(
            "SMOKE_STATUS_INVALID"
        )

    contract = policy[
        "smoke_contract"
    ]

    if value[
        "external_module_count"
    ] != len(
        contract[
            "external_modules"
        ]
    ):
        raise RuntimeAssemblerError(
            "SMOKE_EXTERNAL_COUNT_INVALID"
        )

    if value[
        "source_module_count"
    ] != len(
        contract[
            "source_modules"
        ]
    ):
        raise RuntimeAssemblerError(
            "SMOKE_SOURCE_COUNT_INVALID"
        )

    if value[
        "package_versions"
    ] != policy[
        "offline_install_contract"
    ]["exact_expected_packages"]:
        raise RuntimeAssemblerError(
            "SMOKE_PACKAGE_SET_INVALID"
        )

    if value[
        "sqlalchemy_engine_creation_count"
    ] != contract[
        "engine_creation_count_required"
    ]:
        raise RuntimeAssemblerError(
            "SMOKE_ENGINE_COUNT_INVALID"
        )

    for key in (
        "network_used",
        "database_connected",
        "secret_path_read",
        "subprocess_started",
        "entrypoint_executed",
    ):
        if value[key] is not False:
            raise RuntimeAssemblerError(
                f"SMOKE_BOUNDARY_INVALID:{key}"
            )

    return value


def run_runtime_checks(
    *,
    runtime_root: Path,
    config_path: Path,
    home: Path,
    policy: dict[str, Any],
) -> dict[str, Any]:
    venv_python = validate_venv_python(
        runtime_root,
        policy,
    )

    environment = command_environment(
        runtime_root,
        home,
    )

    run_allowed_command(
        role="VENV_PYTHON",
        command=[
            str(venv_python),
            "-m",
            "pip",
            "check",
        ],
        runtime_root=runtime_root,
        cwd=runtime_root / "src",
        environment=environment,
        policy=policy,
    )

    output = run_allowed_command(
        role="VENV_PYTHON",
        command=[
            str(venv_python),
            str(
                runtime_root
                / "manifest/"
                "runtime-import-smoke.py"
            ),
            "--config",
            str(config_path),
        ],
        runtime_root=runtime_root,
        cwd=runtime_root / "src",
        environment=environment,
        policy=policy,
    )

    return parse_smoke_output(
        output,
        policy,
    )


def validate_payload(
    runtime_root: Path,
    policy: dict[str, Any],
) -> str:
    layout = policy[
        "runtime_layout"
    ]

    manifest_root = (
        runtime_root
        / layout[
            "manifest_root"
        ]
    )

    prepared_manifest_path = (
        manifest_root
        / layout[
            "prepared_manifest_filename"
        ]
    )

    prepared_manifest = load_json(
        prepared_manifest_path
    )

    files = prepared_manifest.get(
        "files"
    )

    if (
        not isinstance(files, list)
        or len(files) != policy[
            "bindings"
        ][
            "prepared_payload_file_count"
        ]
    ):
        raise RuntimeAssemblerError(
            "RUNTIME_PAYLOAD_COUNT_INVALID"
        )

    expected_paths: set[str] = set()

    for entry in files:
        relative = entry["path"]

        if relative in expected_paths:
            raise RuntimeAssemblerError(
                f"RUNTIME_PAYLOAD_DUPLICATE:{relative}"
            )

        expected_paths.add(relative)

        path = runtime_root / relative

        if (
            path.is_symlink()
            or not path.is_file()
        ):
            raise RuntimeAssemblerError(
                f"RUNTIME_PAYLOAD_FILE_INVALID:{relative}"
            )

        value = path.lstat()

        if value.st_nlink != 1:
            raise RuntimeAssemblerError(
                f"RUNTIME_PAYLOAD_HARDLINK_INVALID:{relative}"
            )

        if value.st_size != entry[
            "size"
        ]:
            raise RuntimeAssemblerError(
                f"RUNTIME_PAYLOAD_SIZE_INVALID:{relative}"
            )

        if sha256_path(path) != entry[
            "sha256"
        ]:
            raise RuntimeAssemblerError(
                f"RUNTIME_PAYLOAD_HASH_INVALID:{relative}"
            )

        actual_mode = format(
            stat.S_IMODE(
                value.st_mode
            ),
            "04o",
        )

        if actual_mode != entry[
            "mode"
        ]:
            raise RuntimeAssemblerError(
                f"RUNTIME_PAYLOAD_MODE_INVALID:{relative}"
            )

    actual_paths: set[str] = set()

    for root_name in (
        layout[
            "source_root"
        ],
        layout[
            "wheelhouse_root"
        ],
    ):
        root = (
            runtime_root / root_name
        )

        if (
            root.is_symlink()
            or not root.is_dir()
        ):
            raise RuntimeAssemblerError(
                f"RUNTIME_PAYLOAD_ROOT_INVALID:{root_name}"
            )

        for directory, names, filenames in os.walk(
            root,
            topdown=True,
            followlinks=False,
        ):
            directory_path = Path(
                directory
            )

            for name in names:
                child = (
                    directory_path
                    / name
                )

                if child.is_symlink():
                    raise RuntimeAssemblerError(
                        f"RUNTIME_PAYLOAD_SYMLINK:{child}"
                    )

            for filename in filenames:
                child = (
                    directory_path
                    / filename
                )

                actual_paths.add(
                    child.relative_to(
                        runtime_root
                    ).as_posix()
                )

    if actual_paths != expected_paths:
        raise RuntimeAssemblerError(
            "RUNTIME_PAYLOAD_TREE_MISMATCH"
        )

    metadata_bindings = (
        (
            layout[
                "source_manifest_filename"
            ],
            "source_manifest_sha256",
        ),
        (
            layout[
                "requirements_lock_filename"
            ],
            "requirements_lock_sha256",
        ),
        (
            layout[
                "smoke_runner_filename"
            ],
            "smoke_runner_sha256",
        ),
    )

    for filename, hash_key in (
        metadata_bindings
    ):
        path = (
            manifest_root / filename
        )

        if sha256_path(path) != policy[
            "bindings"
        ][hash_key]:
            raise RuntimeAssemblerError(
                f"RUNTIME_METADATA_HASH_INVALID:{filename}"
            )

    permanent_config = (
        manifest_root
        / layout[
            "smoke_config_filename"
        ]
    )

    if load_json(
        permanent_config
    ) != build_smoke_config(
        runtime_root,
        policy,
    ):
        raise RuntimeAssemblerError(
            "RUNTIME_SMOKE_CONFIG_INVALID"
        )

    return sha256_path(
        prepared_manifest_path
    )


def validate_runtime_output(
    runtime_root: Path,
    policy: dict[str, Any],
) -> dict[str, Any]:
    if (
        runtime_root.is_symlink()
        or not runtime_root.is_dir()
    ):
        raise RuntimeAssemblerError(
            "RUNTIME_OUTPUT_INVALID"
        )

    layout = policy[
        "runtime_layout"
    ]

    expected_top_level = {
        layout["source_root"],
        layout["wheelhouse_root"],
        layout[
            "virtual_environment_root"
        ],
        layout["manifest_root"],
        layout["receipt_filename"],
    }

    actual_top_level = {
        item.name
        for item in runtime_root.iterdir()
    }

    if actual_top_level != (
        expected_top_level
    ):
        raise RuntimeAssemblerError(
            "RUNTIME_TOP_LEVEL_INVALID"
        )

    prepared_manifest_hash = (
        validate_payload(
            runtime_root,
            policy,
        )
    )

    validate_venv_python(
        runtime_root,
        policy,
    )

    receipt_path = (
        runtime_root
        / layout[
            "receipt_filename"
        ]
    )

    receipt = load_json(
        receipt_path
    )

    if receipt[
        "release_id"
    ] != policy[
        "bindings"
    ]["release_id"]:
        raise RuntimeAssemblerError(
            "RUNTIME_RECEIPT_RELEASE_INVALID"
        )

    if receipt[
        "prepared_manifest_sha256"
    ] != prepared_manifest_hash:
        raise RuntimeAssemblerError(
            "RUNTIME_RECEIPT_MANIFEST_INVALID"
        )

    temporary_home = Path(
        tempfile.mkdtemp(
            prefix=(
                ".runtime-validation-home-"
            ),
            dir=runtime_root.parent,
        )
    )

    try:
        smoke_result = run_runtime_checks(
            runtime_root=runtime_root,
            config_path=(
                runtime_root
                / layout[
                    "manifest_root"
                ]
                / layout[
                    "smoke_config_filename"
                ]
            ),
            home=temporary_home,
            policy=policy,
        )
    finally:
        remove_owned_tree(
            temporary_home
        )

    if receipt[
        "smoke_result_sha256"
    ] != sha256_bytes(
        canonical_bytes(
            smoke_result
        )
    ):
        raise RuntimeAssemblerError(
            "RUNTIME_RECEIPT_SMOKE_INVALID"
        )

    if receipt[
        "installed_packages"
    ] != policy[
        "offline_install_contract"
    ]["exact_expected_packages"]:
        raise RuntimeAssemblerError(
            "RUNTIME_RECEIPT_PACKAGES_INVALID"
        )

    if receipt[
        "sqlalchemy_engine_creation_count"
    ] != 1:
        raise RuntimeAssemblerError(
            "RUNTIME_RECEIPT_ENGINE_COUNT_INVALID"
        )

    if receipt[
        "sandbox_reference_only"
    ] is not True:
        raise RuntimeAssemblerError(
            "RUNTIME_RECEIPT_BOUNDARY_INVALID"
        )

    return {
        "receipt": receipt,
        "smoke_result": smoke_result,
    }


def utc_timestamp(
    value: datetime,
) -> str:
    return (
        value.astimezone(
            timezone.utc
        )
        .isoformat(
            timespec="seconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )


def assemble_prepared_runtime(
    *,
    prepared_bundle_root: Path,
    runtime_output_root: Path,
    transaction_id: str,
    now_utc: datetime,
    fault_point: str | None = None,
) -> dict[str, Any]:
    if now_utc.tzinfo is None:
        raise RuntimeAssemblerError(
            "NOW_TIMEZONE_REQUIRED"
        )

    validate_transaction_id(
        transaction_id
    )

    policy, _, core = (
        validate_policy()
    )

    allowed_faults = set(
        policy[
            "transaction_contract"
        ]["fault_points"]
    )

    if (
        fault_point is not None
        and fault_point
        not in allowed_faults
    ):
        raise RuntimeAssemblerError(
            "FAULT_POINT_INVALID"
        )

    prepared_bundle_root = (
        validate_tmp_path(
            prepared_bundle_root,
            field_name=(
                "PREPARED_BUNDLE_ROOT"
            ),
            must_exist=True,
        )
    )

    runtime_output_root = (
        validate_tmp_path(
            runtime_output_root,
            field_name=(
                "RUNTIME_OUTPUT_ROOT"
            ),
            must_exist=False,
        )
    )

    parent = runtime_output_root.parent

    if (
        parent.is_symlink()
        or not parent.is_dir()
    ):
        raise RuntimeAssemblerError(
            "RUNTIME_OUTPUT_PARENT_INVALID"
        )

    core_policy = (
        core.validate_policy()
    )

    manifest, _ = (
        core.load_and_validate_manifest(
            prepared_bundle_root,
            core_policy,
        )
    )

    release_id = policy[
        "bindings"
    ]["release_id"]

    if manifest[
        "release_id"
    ] != release_id:
        raise RuntimeAssemblerError(
            "PREPARED_RELEASE_ID_INVALID"
        )

    lock_descriptor = open_lock(
        parent
        / (
            ".offline-runtime-"
            f"{release_id}.lock"
        )
    )

    staging_root: Path | None = None

    try:
        fcntl.flock(
            lock_descriptor,
            fcntl.LOCK_EX,
        )

        if lexists(
            runtime_output_root
        ):
            validation = (
                validate_runtime_output(
                    runtime_output_root,
                    policy,
                )
            )

            return {
                "state": (
                    "SANDBOX_RUNTIME_ALREADY_ASSEMBLED"
                ),
                "release_id": release_id,
                "runtime_assembly_executed": (
                    False
                ),
                "venv_created": False,
                "offline_wheel_install_executed": (
                    False
                ),
                "import_smoke_executed": True,
                "sqlalchemy_engine_creation_count": (
                    validation[
                        "smoke_result"
                    ][
                        "sqlalchemy_engine_creation_count"
                    ]
                ),
                "installed_packages": (
                    validation[
                        "receipt"
                    ][
                        "installed_packages"
                    ]
                ),
                "root_release_install_authorized": (
                    False
                ),
                "root_release_install_executed": (
                    False
                ),
                "current_link_created": False,
                "final_decision": "NO_GO",
            }

        staging_root = (
            parent
            / (
                ".offline-runtime-"
                f"{release_id}-"
                f"{transaction_id}"
            )
        )

        if lexists(staging_root):
            raise RuntimeAssemblerError(
                "RUNTIME_STAGING_PRESENT"
            )

        staging_root.mkdir(
            mode=0o700,
        )

        layout = policy[
            "runtime_layout"
        ]

        for directory_name in (
            layout[
                "source_root"
            ],
            layout[
                "wheelhouse_root"
            ],
            layout[
                "manifest_root"
            ],
        ):
            (
                staging_root
                / directory_name
            ).mkdir(
                mode=0o755,
            )

        maximum_size = core_policy[
            "prepared_bundle_contract"
        ]["maximum_file_bytes"]

        for entry in manifest[
            "files"
        ]:
            source_path = (
                prepared_bundle_root
                / "payload"
                / entry["path"]
            )

            destination_path = (
                staging_root
                / entry["path"]
            )

            current_parent = (
                staging_root
            )

            relative_parent = (
                destination_path.parent
                .relative_to(
                    staging_root
                )
            )

            for component in (
                relative_parent.parts
            ):
                current_parent = (
                    current_parent
                    / component
                )

                ensure_directory(
                    current_parent,
                    0o755,
                )

            core.copy_manifest_file(
                source_path,
                destination_path,
                entry,
                maximum_size,
            )

        if fault_point == (
            "AFTER_PAYLOAD_COPY"
        ):
            raise RuntimeAssemblerError(
                "INJECTED_AFTER_PAYLOAD_COPY"
            )

        manifest_root = (
            staging_root
            / layout[
                "manifest_root"
            ]
        )

        prepared_manifest_source = (
            prepared_bundle_root
            / "bundle-manifest.json"
        )

        metadata_sources = (
            (
                prepared_manifest_source,
                manifest_root
                / layout[
                    "prepared_manifest_filename"
                ],
                sha256_path(
                    prepared_manifest_source
                ),
            ),
            (
                repository_path(
                    policy[
                        "bindings"
                    ][
                        "source_manifest_path"
                    ]
                ),
                manifest_root
                / layout[
                    "source_manifest_filename"
                ],
                policy[
                    "bindings"
                ][
                    "source_manifest_sha256"
                ],
            ),
            (
                repository_path(
                    policy[
                        "bindings"
                    ][
                        "requirements_lock_path"
                    ]
                ),
                manifest_root
                / layout[
                    "requirements_lock_filename"
                ],
                policy[
                    "bindings"
                ][
                    "requirements_lock_sha256"
                ],
            ),
            (
                repository_path(
                    policy[
                        "bindings"
                    ][
                        "smoke_runner_path"
                    ]
                ),
                manifest_root
                / layout[
                    "smoke_runner_filename"
                ],
                policy[
                    "bindings"
                ][
                    "smoke_runner_sha256"
                ],
            ),
        )

        for (
            source_path,
            destination_path,
            expected_hash,
        ) in metadata_sources:
            copy_bound_file(
                source_path,
                destination_path,
                expected_sha256=(
                    expected_hash
                ),
                mode=0o644,
            )

        permanent_config = (
            build_smoke_config(
                runtime_output_root,
                policy,
            )
        )

        staging_config = (
            build_smoke_config(
                staging_root,
                policy,
            )
        )

        permanent_config_path = (
            manifest_root
            / layout[
                "smoke_config_filename"
            ]
        )

        staging_config_path = (
            manifest_root
            / layout[
                "temporary_smoke_config_filename"
            ]
        )

        write_exclusive(
            permanent_config_path,
            canonical_bytes(
                permanent_config
            ),
            0o644,
        )

        write_exclusive(
            staging_config_path,
            canonical_bytes(
                staging_config
            ),
            0o600,
        )

        command_home = (
            staging_root
            / ".runtime-command-home"
        )

        command_home.mkdir(
            mode=0o700,
        )

        environment = (
            command_environment(
                staging_root,
                command_home,
            )
        )

        run_allowed_command(
            role="SYSTEM_PYTHON",
            command=[
                policy[
                    "bindings"
                ]["system_python"],
                "-m",
                "venv",
                "--symlinks",
                str(
                    staging_root
                    / "venv"
                ),
            ],
            runtime_root=staging_root,
            cwd=staging_root,
            environment=environment,
            policy=policy,
        )

        venv_python = (
            validate_venv_python(
                staging_root,
                policy,
            )
        )

        if fault_point == (
            "AFTER_VENV_CREATE"
        ):
            raise RuntimeAssemblerError(
                "INJECTED_AFTER_VENV_CREATE"
            )

        run_allowed_command(
            role="VENV_PYTHON",
            command=[
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(
                    staging_root
                    / "wheelhouse"
                ),
                "--require-hashes",
                "--no-deps",
                "--no-cache-dir",
                "--disable-pip-version-check",
                "-r",
                str(
                    manifest_root
                    / layout[
                        "requirements_lock_filename"
                    ]
                ),
            ],
            runtime_root=staging_root,
            cwd=staging_root,
            environment=environment,
            policy=policy,
        )

        if fault_point == (
            "AFTER_WHEEL_INSTALL"
        ):
            raise RuntimeAssemblerError(
                "INJECTED_AFTER_WHEEL_INSTALL"
            )

        smoke_result = (
            run_runtime_checks(
                runtime_root=(
                    staging_root
                ),
                config_path=(
                    staging_config_path
                ),
                home=command_home,
                policy=policy,
            )
        )

        if fault_point == (
            "AFTER_SMOKE"
        ):
            raise RuntimeAssemblerError(
                "INJECTED_AFTER_SMOKE"
            )

        staging_config_path.unlink()

        remove_owned_tree(
            command_home
        )

        prepared_manifest_hash = (
            sha256_path(
                manifest_root
                / layout[
                    "prepared_manifest_filename"
                ]
            )
        )

        receipt = {
            "schema_version": 1,
            "release_id": release_id,
            "smoke_revision": 2,
            "prepared_manifest_sha256": (
                prepared_manifest_hash
            ),
            "source_manifest_sha256": (
                policy[
                    "bindings"
                ][
                    "source_manifest_sha256"
                ]
            ),
            "requirements_lock_sha256": (
                policy[
                    "bindings"
                ][
                    "requirements_lock_sha256"
                ]
            ),
            "smoke_policy_sha256": (
                policy[
                    "bindings"
                ][
                    "smoke_policy_sha256"
                ]
            ),
            "smoke_runner_sha256": (
                policy[
                    "bindings"
                ][
                    "smoke_runner_sha256"
                ]
            ),
            "installed_packages": (
                smoke_result[
                    "package_versions"
                ]
            ),
            "sqlalchemy_engine_creation_count": (
                smoke_result[
                    "sqlalchemy_engine_creation_count"
                ]
            ),
            "smoke_result_sha256": (
                sha256_bytes(
                    canonical_bytes(
                        smoke_result
                    )
                )
            ),
            "assembled_at": (
                utc_timestamp(
                    now_utc
                )
            ),
            "sandbox_reference_only": True,
        }

        write_exclusive(
            staging_root
            / layout[
                "receipt_filename"
            ],
            canonical_bytes(
                receipt
            ),
            0o600,
        )

        for directory, _, _ in os.walk(
            staging_root,
            topdown=False,
            followlinks=False,
        ):
            fsync_directory(
                Path(directory)
            )

        if lexists(
            runtime_output_root
        ):
            raise RuntimeAssemblerError(
                "RUNTIME_OUTPUT_RACE"
            )

        os.rename(
            staging_root,
            runtime_output_root,
        )

        staging_root = None

        fsync_directory(
            parent
        )

        validation = (
            validate_runtime_output(
                runtime_output_root,
                policy,
            )
        )

        return {
            "state": (
                "SANDBOX_RUNTIME_ASSEMBLED"
            ),
            "release_id": release_id,
            "runtime_assembly_executed": True,
            "venv_created": True,
            "offline_wheel_install_executed": (
                True
            ),
            "import_smoke_executed": True,
            "sqlalchemy_engine_creation_count": (
                validation[
                    "smoke_result"
                ][
                    "sqlalchemy_engine_creation_count"
                ]
            ),
            "installed_packages": (
                validation[
                    "receipt"
                ][
                    "installed_packages"
                ]
            ),
            "root_release_install_authorized": (
                False
            ),
            "root_release_install_executed": (
                False
            ),
            "current_link_created": False,
            "final_decision": "NO_GO",
        }
    except Exception:
        if (
            staging_root is not None
            and lexists(
                staging_root
            )
        ):
            remove_owned_tree(
                staging_root
            )

            fsync_directory(
                parent
            )

        raise
    finally:
        try:
            fcntl.flock(
                lock_descriptor,
                fcntl.LOCK_UN,
            )
        finally:
            os.close(
                lock_descriptor
            )


def assemble_real_runtime(
    *,
    wheelhouse_root: Path,
    runtime_output_root: Path,
    transaction_id: str,
    now_utc: datetime,
    fault_point: str | None = None,
) -> dict[str, Any]:
    validate_transaction_id(
        transaction_id
    )

    policy, adapter, _ = (
        validate_policy()
    )

    runtime_output_root = (
        validate_tmp_path(
            runtime_output_root,
            field_name=(
                "RUNTIME_OUTPUT_ROOT"
            ),
            must_exist=False,
        )
    )

    parent = runtime_output_root.parent

    if (
        parent.is_symlink()
        or not parent.is_dir()
    ):
        raise RuntimeAssemblerError(
            "RUNTIME_OUTPUT_PARENT_INVALID"
        )

    work_root = (
        parent
        / (
            ".offline-runtime-work-"
            f"{policy['bindings']['release_id']}-"
            f"{transaction_id}"
        )
    )

    if lexists(work_root):
        raise RuntimeAssemblerError(
            "RUNTIME_WORK_ROOT_PRESENT"
        )

    work_root.mkdir(
        mode=0o700,
    )

    try:
        prepared_root = (
            work_root / "prepared"
        )

        adapter.prepare_real_bundle(
            wheelhouse_root=(
                wheelhouse_root
            ),
            output_root=(
                prepared_root
            ),
            transaction_id=(
                transaction_id
            ),
        )

        return assemble_prepared_runtime(
            prepared_bundle_root=(
                prepared_root
            ),
            runtime_output_root=(
                runtime_output_root
            ),
            transaction_id=(
                transaction_id
            ),
            now_utc=now_utc,
            fault_point=fault_point,
        )
    finally:
        if lexists(work_root):
            remove_owned_tree(
                work_root
            )

            fsync_directory(
                parent
            )


def main() -> None:
    validate_policy()

    print(
        "OFFLINE_RUNTIME_POLICY_BINDING: PASS"
    )
    print(
        "SMOKE_REVISION: 2"
    )
    print(
        "ENGINE_CONSTRUCTION_ALLOWED: TRUE"
    )
    print(
        "EXPECTED_ENGINE_CREATION_COUNT: 1"
    )
    print(
        "DATABASE_CONNECTION_ALLOWED: FALSE"
    )
    print(
        "FRESH_VENV_REQUIRED: TRUE"
    )
    print(
        "OFFLINE_HASH_LOCKED_INSTALL: ENABLED"
    )
    print(
        "HOST_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "CURRENT_LINK_CREATED: FALSE"
    )
    print(
        "FINAL_DECISION: NO_GO"
    )
    print(
        "SQL_B2_4B_5G_3B_1D_2C_3C_"
        "OFFLINE_RUNTIME_ASSEMBLER_REVISION_2: PASS"
    )


if __name__ == "__main__":
    main()
