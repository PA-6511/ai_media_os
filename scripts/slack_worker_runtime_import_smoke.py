from __future__ import annotations

import argparse
import builtins
import importlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
from typing import Any


MAXIMUM_CONFIG_BYTES = 131072

SQLALCHEMY_ENGINE_CREATION_EVENTS: list[int] = []

EXACT_CONFIG_KEYS = {
    "schema_version",
    "external_modules",
    "source_modules",
    "expected_packages",
    "forbidden_path_prefixes",
    "pythonpath",
    "working_directory",
}

MODULE_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
)


class SmokeGuardError(ValueError):
    pass


def reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}

    for key, item in pairs:
        if key in value:
            raise SmokeGuardError(
                f"DUPLICATE_JSON_KEY:{key}"
            )

        value[key] = item

    return value


def read_config(
    path: Path,
) -> dict[str, Any]:
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
        raise SmokeGuardError(
            "CONFIG_OPEN_FAILED"
        ) from exc

    chunks: list[bytes] = []
    total = 0

    try:
        value = os.fstat(
            descriptor
        )

        if (
            not os.path.isfile(path)
            or value.st_nlink != 1
        ):
            raise SmokeGuardError(
                "CONFIG_CUSTODY_INVALID"
            )

        while True:
            chunk = os.read(
                descriptor,
                65536,
            )

            if not chunk:
                break

            total += len(chunk)

            if total > MAXIMUM_CONFIG_BYTES:
                raise SmokeGuardError(
                    "CONFIG_SIZE_LIMIT_EXCEEDED"
                )

            chunks.append(chunk)
    finally:
        os.close(descriptor)

    try:
        config = json.loads(
            b"".join(chunks).decode(
                "utf-8"
            ),
            object_pairs_hook=(
                reject_duplicate_keys
            ),
        )
    except SmokeGuardError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise SmokeGuardError(
            "CONFIG_JSON_INVALID"
        ) from exc

    if not isinstance(config, dict):
        raise SmokeGuardError(
            "CONFIG_OBJECT_REQUIRED"
        )

    if set(config) != EXACT_CONFIG_KEYS:
        raise SmokeGuardError(
            "CONFIG_KEYS_INVALID"
        )

    if config["schema_version"] != 1:
        raise SmokeGuardError(
            "CONFIG_SCHEMA_VERSION_INVALID"
        )

    for key in (
        "external_modules",
        "source_modules",
        "forbidden_path_prefixes",
    ):
        value = config[key]

        if (
            not isinstance(value, list)
            or not all(
                isinstance(item, str)
                for item in value
            )
        ):
            raise SmokeGuardError(
                f"CONFIG_LIST_INVALID:{key}"
            )

        if len(value) != len(set(value)):
            raise SmokeGuardError(
                f"CONFIG_DUPLICATE_VALUE:{key}"
            )

    for key in (
        "external_modules",
        "source_modules",
    ):
        for module_name in config[key]:
            if MODULE_PATTERN.fullmatch(
                module_name
            ) is None:
                raise SmokeGuardError(
                    f"MODULE_NAME_INVALID:{module_name}"
                )

    expected_packages = config[
        "expected_packages"
    ]

    if (
        not isinstance(
            expected_packages,
            dict,
        )
        or not all(
            isinstance(name, str)
            and isinstance(version, str)
            and name
            and version
            for name, version
            in expected_packages.items()
        )
    ):
        raise SmokeGuardError(
            "EXPECTED_PACKAGES_INVALID"
        )

    for key in (
        "pythonpath",
        "working_directory",
    ):
        value = config[key]

        if (
            not isinstance(value, str)
            or not os.path.isabs(value)
        ):
            raise SmokeGuardError(
                f"ABSOLUTE_PATH_REQUIRED:{key}"
            )

        path_value = Path(value)

        if (
            path_value.is_symlink()
            or not path_value.is_dir()
        ):
            raise SmokeGuardError(
                f"DIRECTORY_INVALID:{key}"
            )

    normalized_prefixes = []

    for prefix in config[
        "forbidden_path_prefixes"
    ]:
        if not os.path.isabs(prefix):
            raise SmokeGuardError(
                "FORBIDDEN_PREFIX_NOT_ABSOLUTE"
            )

        normalized_prefixes.append(
            os.path.normpath(prefix)
        )

    config[
        "forbidden_path_prefixes"
    ] = normalized_prefixes

    return config


def install_guards(
    forbidden_prefixes: list[str],
) -> None:
    original_builtin_open = builtins.open
    original_io_open = io.open
    original_os_open = os.open
    original_path_open = Path.open

    def check_path(value: object) -> None:
        try:
            candidate = os.path.abspath(
                os.fspath(value)
            )
        except TypeError:
            return

        for prefix in forbidden_prefixes:
            if (
                candidate == prefix
                or candidate.startswith(
                    prefix + os.sep
                )
            ):
                raise RuntimeError(
                    "RUNTIME_SMOKE_FORBIDDEN_PATH"
                )

    def guarded_builtin_open(
        file: object,
        *args: object,
        **kwargs: object,
    ):
        check_path(file)

        return original_builtin_open(
            file,
            *args,
            **kwargs,
        )

    def guarded_io_open(
        file: object,
        *args: object,
        **kwargs: object,
    ):
        check_path(file)

        return original_io_open(
            file,
            *args,
            **kwargs,
        )

    def guarded_path_open(
        self: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ):
        check_path(self)

        return original_path_open(
            self,
            mode,
            buffering,
            encoding,
            errors,
            newline,
        )

    def guarded_os_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        check_path(path)

        if dir_fd is None:
            return original_os_open(
                path,
                flags,
                mode,
            )

        return original_os_open(
            path,
            flags,
            mode,
            dir_fd=dir_fd,
        )

    def deny_operation(
        *args: object,
        **kwargs: object,
    ) -> None:
        raise RuntimeError(
            "RUNTIME_SMOKE_PROHIBITED_OPERATION"
        )

    def deny_sqlalchemy_connection(
        *args: object,
        **kwargs: object,
    ) -> None:
        raise RuntimeError(
            "RUNTIME_SMOKE_SQLALCHEMY_CONNECTION_OPERATION"
        )

    # SQLALCHEMY_PRELOAD_BEFORE_GUARDS
    try:
        importlib.import_module(
            "sqlalchemy"
        )

        importlib.import_module(
            "sqlalchemy.engine.create"
        )

        importlib.import_module(
            "sqlalchemy.engine.base"
        )
    except ImportError:
        pass

    builtins.open = guarded_builtin_open
    io.open = guarded_io_open
    os.open = guarded_os_open
    Path.open = guarded_path_open

    socket.socket = deny_operation
    socket.create_connection = (
        deny_operation
    )

    sqlite3.connect = deny_operation

    sqlite3_dbapi2 = getattr(
        sqlite3,
        "dbapi2",
        None,
    )

    if sqlite3_dbapi2 is not None:
        setattr(
            sqlite3_dbapi2,
            "connect",
            deny_operation,
        )

    subprocess.Popen = deny_operation
    subprocess.run = deny_operation
    subprocess.call = deny_operation
    subprocess.check_call = deny_operation
    subprocess.check_output = deny_operation

    os.system = deny_operation
    os.popen = deny_operation

    sqlalchemy_module = sys.modules.get(
        "sqlalchemy"
    )

    sqlalchemy_create_module = (
        sys.modules.get(
            "sqlalchemy.engine.create"
        )
    )

    original_create_engine = None

    if sqlalchemy_create_module is not None:
        original_create_engine = getattr(
            sqlalchemy_create_module,
            "create_engine",
            None,
        )

    if (
        original_create_engine is None
        and sqlalchemy_module is not None
    ):
        original_create_engine = getattr(
            sqlalchemy_module,
            "create_engine",
            None,
        )

    if original_create_engine is not None:
        def observed_create_engine(
            *args: object,
            **kwargs: object,
        ):
            SQLALCHEMY_ENGINE_CREATION_EVENTS.append(
                1
            )

            return original_create_engine(
                *args,
                **kwargs,
            )

        if sqlalchemy_module is not None:
            setattr(
                sqlalchemy_module,
                "create_engine",
                observed_create_engine,
            )

        if sqlalchemy_create_module is not None:
            setattr(
                sqlalchemy_create_module,
                "create_engine",
                observed_create_engine,
            )

    sqlalchemy_engine_module = (
        sys.modules.get(
            "sqlalchemy.engine"
        )
    )

    engine_class = None

    if sqlalchemy_engine_module is not None:
        engine_class = getattr(
            sqlalchemy_engine_module,
            "Engine",
            None,
        )

    if engine_class is None:
        sqlalchemy_engine_base_module = (
            sys.modules.get(
                "sqlalchemy.engine.base"
            )
        )

        if (
            sqlalchemy_engine_base_module
            is not None
        ):
            engine_class = getattr(
                sqlalchemy_engine_base_module,
                "Engine",
                None,
            )

    if engine_class is not None:
        for method_name in (
            "connect",
            "raw_connection",
            "begin",
        ):
            setattr(
                engine_class,
                method_name,
                deny_sqlalchemy_connection,
            )


def execute_smoke(
    config: dict[str, Any],
) -> dict[str, Any]:
    sys.dont_write_bytecode = True

    pythonpath = config[
        "pythonpath"
    ]

    if pythonpath not in sys.path:
        sys.path.insert(
            0,
            pythonpath,
        )

    os.chdir(
        config["working_directory"]
    )

    for module_name in config[
        "external_modules"
    ]:
        importlib.import_module(
            module_name
        )

    versions = {
        package_name: (
            importlib.metadata.version(
                package_name
            )
        )
        for package_name in config[
            "expected_packages"
        ]
    }

    if versions != config[
        "expected_packages"
    ]:
        raise SmokeGuardError(
            "PACKAGE_VERSION_MISMATCH"
        )

    install_guards(
        config[
            "forbidden_path_prefixes"
        ]
    )

    for module_name in config[
        "source_modules"
    ]:
        importlib.import_module(
            module_name
        )

    return {
        "status": "PASS",
        "external_module_count": len(
            config["external_modules"]
        ),
        "source_module_count": len(
            config["source_modules"]
        ),
        "package_versions": versions,
        "sqlalchemy_engine_creation_count": len(
            SQLALCHEMY_ENGINE_CREATION_EVENTS
        ),
        "network_used": False,
        "database_connected": False,
        "secret_path_read": False,
        "subprocess_started": False,
        "entrypoint_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True,
    )

    arguments = parser.parse_args()

    try:
        config = read_config(
            Path(arguments.config)
        )

        result = execute_smoke(
            config
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": (
                        type(exc).__name__
                    ),
                    "error": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1

    print(
        json.dumps(
            result,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
