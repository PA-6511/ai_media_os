from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import ModuleType
from typing import Any


repo = Path(__file__).resolve().parents[1]

adapter_policy_path = (
    repo
    / "config/"
    "slack_worker_real_release_"
    "bundle_sandbox_adapter_policy.json"
)


class BundleAdapterError(ValueError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()

    flags = (
        os.O_RDONLY
        | os.O_CLOEXEC
    )

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(
        os.fspath(path),
        flags,
    )

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
            raise BundleAdapterError(
                f"HASH_INPUT_CUSTODY_INVALID: {path}"
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
        os.close(
            descriptor
        )

    return digest.hexdigest()


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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(value, dict):
        raise BundleAdapterError(
            f"JSON_OBJECT_REQUIRED: {path}"
        )

    return value


def repository_path(relative: str) -> Path:
    path = (
        repo / relative
    ).resolve()

    path.relative_to(
        repo.resolve()
    )

    return path


def load_sandbox_core(
    path: Path,
) -> ModuleType:
    specification = (
        importlib.util
        .spec_from_file_location(
            "slack_sandbox_installer_core",
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise BundleAdapterError(
            "SANDBOX_CORE_LOAD_FAILED"
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
    dict[str, Any],
    ModuleType,
]:
    policy = load_json(
        adapter_policy_path
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2C-2"
    ):
        raise BundleAdapterError(
            "ADAPTER_POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_REAL_RELEASE_INPUT_TO_"
        "PREPARED_SANDBOX_BUNDLE_ADAPTER_"
        "TMP_ONLY_NO_HOST_INSTALL_NO_GO"
    ):
        raise BundleAdapterError(
            "ADAPTER_POLICY_RESULT_INVALID"
        )

    bindings = policy["bindings"]

    path_hash_pairs = (
        (
            "sandbox_core_policy_path",
            "sandbox_core_policy_sha256",
        ),
        (
            "sandbox_core_source_path",
            "sandbox_core_source_sha256",
        ),
        (
            "source_manifest_path",
            "source_manifest_sha256",
        ),
        (
            "requirements_hash_lock_path",
            "requirements_hash_lock_sha256",
        ),
        (
            "root_install_policy_path",
            "root_install_policy_sha256",
        ),
        (
            "bundle_evidence_path",
            "bundle_evidence_sha256",
        ),
        (
            "wheel_evidence_path",
            "wheel_evidence_sha256",
        ),
    )

    resolved: dict[str, Path] = {}

    for path_key, hash_key in path_hash_pairs:
        path = repository_path(
            bindings[path_key]
        )

        if not path.is_file():
            raise BundleAdapterError(
                f"BOUND_INPUT_MISSING: {path_key}"
            )

        if sha256_path(path) != bindings[
            hash_key
        ]:
            raise BundleAdapterError(
                f"BOUND_INPUT_HASH_INVALID: "
                f"{hash_key}"
            )

        resolved[path_key] = path

    source_manifest = load_json(
        resolved[
            "source_manifest_path"
        ]
    )

    if source_manifest[
        "release_id_candidate"
    ] != bindings["release_id"]:
        raise BundleAdapterError(
            "SOURCE_RELEASE_ID_INVALID"
        )

    if len(
        source_manifest["source_files"]
    ) != bindings[
        "source_file_count"
    ]:
        raise BundleAdapterError(
            "SOURCE_COUNT_INVALID"
        )

    if len(
        source_manifest["wheels"]
    ) != bindings[
        "wheel_count"
    ]:
        raise BundleAdapterError(
            "WHEEL_COUNT_INVALID"
        )

    boundary = policy[
        "implementation_boundary"
    ]

    for key, value in boundary.items():
        if value is not False:
            raise BundleAdapterError(
                f"IMPLEMENTATION_BOUNDARY_INVALID: {key}"
            )

    governance = policy[
        "governance"
    ]

    if governance[
        "sandbox_adapter_implemented"
    ] is not True:
        raise BundleAdapterError(
            "ADAPTER_IMPLEMENTATION_STATE_INVALID"
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
            raise BundleAdapterError(
                f"GOVERNANCE_STATE_INVALID: {key}"
            )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise BundleAdapterError(
            "FINAL_DECISION_INVALID"
        )

    sandbox_core = load_sandbox_core(
        resolved[
            "sandbox_core_source_path"
        ]
    )

    sandbox_core.validate_policy()

    return (
        policy,
        source_manifest,
        sandbox_core,
    )


def lexists(path: Path) -> bool:
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
        raise BundleAdapterError(
            f"{field_name}_DIRECT_TMP_REJECTED"
        )

    if tmp_root not in path.parents:
        raise BundleAdapterError(
            f"{field_name}_OUTSIDE_TMP_REJECTED"
        )

    current = path

    if not lexists(current):
        current = current.parent

    while current != tmp_root:
        if lexists(current):
            value_stat = current.lstat()

            if stat.S_ISLNK(
                value_stat.st_mode
            ):
                raise BundleAdapterError(
                    f"{field_name}_SYMLINK_ANCESTRY_REJECTED"
                )

        current = current.parent

    if must_exist and not path.exists():
        raise BundleAdapterError(
            f"{field_name}_MISSING"
        )

    return path


def validate_relative_path(
    raw_path: object,
) -> str:
    if not isinstance(raw_path, str):
        raise BundleAdapterError(
            "SOURCE_PATH_TYPE_INVALID"
        )

    if (
        not raw_path
        or raw_path.startswith("/")
        or "\\" in raw_path
    ):
        raise BundleAdapterError(
            f"SOURCE_PATH_INVALID: {raw_path!r}"
        )

    value = PurePosixPath(
        raw_path
    )

    if any(
        part in (
            "",
            ".",
            "..",
        )
        for part in value.parts
    ):
        raise BundleAdapterError(
            f"SOURCE_PATH_TRAVERSAL: {raw_path}"
        )

    normalized = value.as_posix()

    if normalized != raw_path:
        raise BundleAdapterError(
            f"SOURCE_PATH_NOT_NORMALIZED: {raw_path}"
        )

    return normalized


def validate_regular_input(
    path: Path,
    *,
    root: Path,
    label: str,
) -> os.stat_result:
    root_absolute = Path(
        os.path.abspath(
            os.fspath(root)
        )
    )

    path_absolute = Path(
        os.path.abspath(
            os.fspath(path)
        )
    )

    try:
        path_absolute.relative_to(
            root_absolute
        )
    except ValueError as exc:
        raise BundleAdapterError(
            f"{label}_OUTSIDE_ROOT"
        ) from exc

    current = path_absolute.parent

    while current != root_absolute:
        value = current.lstat()

        if (
            stat.S_ISLNK(value.st_mode)
            or not stat.S_ISDIR(
                value.st_mode
            )
        ):
            raise BundleAdapterError(
                f"{label}_ANCESTRY_INVALID: {current}"
            )

        current = current.parent

    value = path_absolute.lstat()

    if (
        stat.S_ISLNK(value.st_mode)
        or not stat.S_ISREG(
            value.st_mode
        )
    ):
        raise BundleAdapterError(
            f"{label}_REGULAR_FILE_REQUIRED: "
            f"{path_absolute}"
        )

    if value.st_nlink != 1:
        raise BundleAdapterError(
            f"{label}_HARDLINK_REJECTED: "
            f"{path_absolute}"
        )

    return value


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
            raise BundleAdapterError(
                f"DIRECTORY_INVALID: {path}"
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


def open_lock(path: Path) -> int:
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
        os.close(
            descriptor
        )

        raise BundleAdapterError(
            "ADAPTER_LOCK_CUSTODY_INVALID"
        )

    return descriptor


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
            raise BundleAdapterError(
                "DESTINATION_SHORT_WRITE"
            )

        offset += written


def copy_validated_file(
    source_path: Path,
    destination_path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
    destination_mode: int,
) -> None:
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
        os.fspath(source_path),
        source_flags,
    )

    try:
        source_value = os.fstat(
            source_descriptor
        )

        if (
            not stat.S_ISREG(
                source_value.st_mode
            )
            or source_value.st_nlink != 1
        ):
            raise BundleAdapterError(
                f"COPY_SOURCE_CUSTODY_INVALID: "
                f"{source_path}"
            )

        destination_descriptor = os.open(
            os.fspath(destination_path),
            destination_flags,
            destination_mode,
        )

        digest = hashlib.sha256()
        total = 0

        try:
            os.fchmod(
                destination_descriptor,
                destination_mode,
            )

            while True:
                chunk = os.read(
                    source_descriptor,
                    65536,
                )

                if not chunk:
                    break

                total += len(chunk)
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
    finally:
        os.close(
            source_descriptor
        )

    if total != expected_size:
        raise BundleAdapterError(
            f"COPIED_SIZE_MISMATCH: {source_path}"
        )

    if digest.hexdigest() != expected_sha256:
        raise BundleAdapterError(
            f"COPIED_HASH_MISMATCH: {source_path}"
        )


def fsync_directory(path: Path) -> None:
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
        os.fsync(
            descriptor
        )
    finally:
        os.close(
            descriptor
        )


def remove_owned_tree(path: Path) -> None:
    if not lexists(path):
        return

    if path.is_symlink():
        raise BundleAdapterError(
            "STAGING_ROOT_SYMLINK_REJECTED"
        )

    for directory, names, filenames in os.walk(
        path,
        topdown=False,
        followlinks=False,
    ):
        directory_path = Path(directory)

        for filename in filenames:
            child = directory_path / filename

            if child.is_symlink():
                raise BundleAdapterError(
                    "STAGING_FILE_SYMLINK_REJECTED"
                )

            child.unlink()

        for name in names:
            child = directory_path / name

            if child.is_symlink():
                raise BundleAdapterError(
                    "STAGING_DIRECTORY_SYMLINK_REJECTED"
                )

            child.rmdir()

    path.rmdir()


def prepare_from_inventory(
    *,
    policy: dict[str, Any],
    sandbox_core: ModuleType,
    source_root: Path,
    source_entries: list[dict[str, Any]],
    wheelhouse_root: Path,
    wheel_entries: list[dict[str, Any]],
    output_root: Path,
    transaction_id: str,
    fault_point: str | None = None,
) -> dict[str, Any]:
    if re.fullmatch(
        r"^[a-f0-9]{32}$",
        transaction_id,
    ) is None:
        raise BundleAdapterError(
            "TRANSACTION_ID_INVALID"
        )

    if fault_point not in (
        None,
        "AFTER_SOURCE_COPY",
        "AFTER_MANIFEST_BEFORE_COMMIT",
    ):
        raise BundleAdapterError(
            "FAULT_POINT_INVALID"
        )

    wheelhouse_root = validate_tmp_path(
        wheelhouse_root,
        field_name="WHEELHOUSE_ROOT",
        must_exist=True,
    )

    output_root = validate_tmp_path(
        output_root,
        field_name="OUTPUT_ROOT",
        must_exist=False,
    )

    source_root = Path(
        os.path.abspath(
            os.fspath(source_root)
        )
    )

    if (
        source_root.is_symlink()
        or not source_root.is_dir()
    ):
        raise BundleAdapterError(
            "SOURCE_ROOT_INVALID"
        )

    parent = output_root.parent

    if not parent.is_dir():
        raise BundleAdapterError(
            "OUTPUT_PARENT_MISSING"
        )

    parent_value = parent.lstat()

    if (
        stat.S_ISLNK(
            parent_value.st_mode
        )
        or not stat.S_ISDIR(
            parent_value.st_mode
        )
    ):
        raise BundleAdapterError(
            "OUTPUT_PARENT_INVALID"
        )

    release_id = policy[
        "bindings"
    ]["release_id"]

    mapping = policy[
        "mapping_contract"
    ]

    if len(source_entries) != policy[
        "bindings"
    ]["source_file_count"]:
        raise BundleAdapterError(
            "SOURCE_INVENTORY_COUNT_INVALID"
        )

    if len(wheel_entries) != policy[
        "bindings"
    ]["wheel_count"]:
        raise BundleAdapterError(
            "WHEEL_INVENTORY_COUNT_INVALID"
        )

    lock_name = (
        ".bundle-adapter-"
        f"{release_id}.lock"
    )

    lock_descriptor = open_lock(
        parent / lock_name
    )

    staging_root: Path | None = None

    try:
        fcntl.flock(
            lock_descriptor,
            fcntl.LOCK_EX,
        )

        if lexists(output_root):
            try:
                manifest, canonical = (
                    sandbox_core
                    .load_and_validate_manifest(
                        output_root,
                        sandbox_core.validate_policy(),
                    )
                )
            except Exception as exc:
                raise BundleAdapterError(
                    "EXISTING_OUTPUT_INVALID"
                ) from exc

            if manifest[
                "release_id"
            ] != release_id:
                raise BundleAdapterError(
                    "EXISTING_OUTPUT_RELEASE_INVALID"
                )

            return {
                "state": (
                    "SANDBOX_PREPARED_BUNDLE_"
                    "ALREADY_EXISTS"
                ),
                "release_id": release_id,
                "output_root": str(
                    output_root
                ),
                "manifest_sha256": (
                    sha256_bytes(canonical)
                ),
                "payload_file_count": len(
                    manifest["files"]
                ),
                "adapter_execution_performed": (
                    False
                ),
                "idempotent_existing_output": (
                    True
                ),
                "root_release_install_authorized": (
                    False
                ),
                "root_release_install_executed": (
                    False
                ),
                "authorization_capsule_consumed": (
                    False
                ),
                "current_link_created": False,
                "final_decision": "NO_GO",
            }

        staging_root = (
            parent
            / (
                ".prepare-"
                f"{release_id}-"
                f"{transaction_id}"
            )
        )

        if lexists(staging_root):
            raise BundleAdapterError(
                "STAGING_ROOT_ALREADY_PRESENT"
            )

        staging_root.mkdir(
            mode=0o700,
        )

        payload_root = (
            staging_root / "payload"
        )

        payload_root.mkdir(
            mode=0o755,
        )

        source_payload_root = (
            payload_root / "src"
        )

        wheel_payload_root = (
            payload_root / "wheelhouse"
        )

        source_payload_root.mkdir(
            mode=0o755,
        )

        wheel_payload_root.mkdir(
            mode=0o755,
        )

        manifest_entries: list[
            dict[str, Any]
        ] = []

        seen_destinations: set[str] = set()

        for entry in sorted(
            source_entries,
            key=lambda item: item["path"],
        ):
            relative = validate_relative_path(
                entry["path"]
            )

            expected_size = entry[
                "size"
            ]

            expected_hash = entry[
                "sha256"
            ]

            if (
                type(expected_size) is not int
                or expected_size < 0
            ):
                raise BundleAdapterError(
                    f"SOURCE_SIZE_INVALID: {relative}"
                )

            if (
                not isinstance(
                    expected_hash,
                    str,
                )
                or re.fullmatch(
                    r"^[a-f0-9]{64}$",
                    expected_hash,
                )
                is None
            ):
                raise BundleAdapterError(
                    f"SOURCE_HASH_INVALID: {relative}"
                )

            source_path = (
                source_root / relative
            )

            source_value = (
                validate_regular_input(
                    source_path,
                    root=source_root,
                    label="SOURCE",
                )
            )

            if source_value.st_size != (
                expected_size
            ):
                raise BundleAdapterError(
                    f"SOURCE_SIZE_MISMATCH: {relative}"
                )

            if sha256_path(
                source_path
            ) != expected_hash:
                raise BundleAdapterError(
                    f"SOURCE_HASH_MISMATCH: {relative}"
                )

            destination_relative = (
                mapping[
                    "source_destination_prefix"
                ]
                + relative
            )

            if destination_relative in (
                seen_destinations
            ):
                raise BundleAdapterError(
                    "DESTINATION_DUPLICATE: "
                    f"{destination_relative}"
                )

            seen_destinations.add(
                destination_relative
            )

            destination_path = (
                payload_root
                / destination_relative
            )

            current_parent = (
                source_payload_root
            )

            relative_parent = (
                destination_path.parent
                .relative_to(
                    source_payload_root
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

            copy_validated_file(
                source_path,
                destination_path,
                expected_size=expected_size,
                expected_sha256=expected_hash,
                destination_mode=0o644,
            )

            manifest_entries.append(
                {
                    "path": (
                        destination_relative
                    ),
                    "sha256": expected_hash,
                    "size": expected_size,
                    "mode": "0644",
                }
            )

        if fault_point == (
            "AFTER_SOURCE_COPY"
        ):
            raise BundleAdapterError(
                "INJECTED_AFTER_SOURCE_COPY_FAILURE"
            )

        seen_wheel_names: set[str] = set()

        for entry in sorted(
            wheel_entries,
            key=lambda item: item[
                "filename"
            ],
        ):
            filename = entry[
                "filename"
            ]

            if (
                not isinstance(
                    filename,
                    str,
                )
                or not filename
                or filename
                != Path(filename).name
                or "/" in filename
                or "\\" in filename
            ):
                raise BundleAdapterError(
                    f"WHEEL_FILENAME_INVALID: "
                    f"{filename!r}"
                )

            if filename in seen_wheel_names:
                raise BundleAdapterError(
                    f"WHEEL_FILENAME_DUPLICATE: "
                    f"{filename}"
                )

            seen_wheel_names.add(
                filename
            )

            expected_size = entry[
                "size"
            ]

            expected_hash = entry[
                "sha256"
            ]

            if (
                type(expected_size) is not int
                or expected_size < 0
            ):
                raise BundleAdapterError(
                    f"WHEEL_SIZE_INVALID: {filename}"
                )

            if (
                not isinstance(
                    expected_hash,
                    str,
                )
                or re.fullmatch(
                    r"^[a-f0-9]{64}$",
                    expected_hash,
                )
                is None
            ):
                raise BundleAdapterError(
                    f"WHEEL_HASH_INVALID: {filename}"
                )

            source_path = (
                wheelhouse_root / filename
            )

            source_value = (
                validate_regular_input(
                    source_path,
                    root=wheelhouse_root,
                    label="WHEEL",
                )
            )

            if source_value.st_size != (
                expected_size
            ):
                raise BundleAdapterError(
                    f"WHEEL_SIZE_MISMATCH: {filename}"
                )

            if sha256_path(
                source_path
            ) != expected_hash:
                raise BundleAdapterError(
                    f"WHEEL_HASH_MISMATCH: {filename}"
                )

            destination_relative = (
                mapping[
                    "wheel_destination_prefix"
                ]
                + filename
            )

            if destination_relative in (
                seen_destinations
            ):
                raise BundleAdapterError(
                    "DESTINATION_DUPLICATE: "
                    f"{destination_relative}"
                )

            seen_destinations.add(
                destination_relative
            )

            destination_path = (
                payload_root
                / destination_relative
            )

            copy_validated_file(
                source_path,
                destination_path,
                expected_size=expected_size,
                expected_sha256=expected_hash,
                destination_mode=0o644,
            )

            manifest_entries.append(
                {
                    "path": (
                        destination_relative
                    ),
                    "sha256": expected_hash,
                    "size": expected_size,
                    "mode": "0644",
                }
            )

        core_policy = (
            sandbox_core.validate_policy()
        )

        core_contract = core_policy[
            "prepared_bundle_contract"
        ]

        manifest = {
            "schema_version": (
                core_contract[
                    "manifest_schema_version"
                ]
            ),
            "release_id": release_id,
            "source_manifest_sha256": (
                core_contract[
                    "source_manifest_sha256"
                ]
            ),
            "requirements_hash_lock_sha256": (
                core_contract[
                    "requirements_hash_lock_sha256"
                ]
            ),
            "root_install_policy_sha256": (
                core_contract[
                    "root_install_policy_sha256"
                ]
            ),
            "source_file_count": policy[
                "bindings"
            ]["source_file_count"],
            "wheel_count": policy[
                "bindings"
            ]["wheel_count"],
            "files": sorted(
                manifest_entries,
                key=lambda item: item[
                    "path"
                ],
            ),
        }

        if len(
            manifest["files"]
        ) != mapping[
            "payload_file_count"
        ]:
            raise BundleAdapterError(
                "PREPARED_PAYLOAD_COUNT_INVALID"
            )

        manifest_path = (
            staging_root
            / "bundle-manifest.json"
        )

        manifest_flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
        )

        if hasattr(os, "O_NOFOLLOW"):
            manifest_flags |= os.O_NOFOLLOW

        manifest_descriptor = os.open(
            os.fspath(
                manifest_path
            ),
            manifest_flags,
            0o644,
        )

        try:
            os.fchmod(
                manifest_descriptor,
                0o644,
            )

            write_all(
                manifest_descriptor,
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
                + b"\n",
            )

            os.fsync(
                manifest_descriptor
            )
        finally:
            os.close(
                manifest_descriptor
            )

        for directory, _, _ in os.walk(
            staging_root,
            topdown=False,
            followlinks=False,
        ):
            fsync_directory(
                Path(directory)
            )

        if fault_point == (
            "AFTER_MANIFEST_BEFORE_COMMIT"
        ):
            raise BundleAdapterError(
                "INJECTED_BEFORE_COMMIT_FAILURE"
            )

        if lexists(output_root):
            raise BundleAdapterError(
                "OUTPUT_RACE_DETECTED"
            )

        os.rename(
            staging_root,
            output_root,
        )

        staging_root = None

        fsync_directory(
            parent
        )

        validated_manifest, canonical = (
            sandbox_core
            .load_and_validate_manifest(
                output_root,
                core_policy,
            )
        )

        return {
            "state": (
                "SANDBOX_PREPARED_BUNDLE_CREATED"
            ),
            "release_id": release_id,
            "output_root": str(
                output_root
            ),
            "manifest_sha256": (
                sha256_bytes(canonical)
            ),
            "payload_file_count": len(
                validated_manifest[
                    "files"
                ]
            ),
            "source_file_count": policy[
                "bindings"
            ]["source_file_count"],
            "wheel_count": policy[
                "bindings"
            ]["wheel_count"],
            "adapter_execution_performed": (
                True
            ),
            "idempotent_existing_output": (
                False
            ),
            "legacy_bundle_used": False,
            "root_release_install_authorized": (
                False
            ),
            "root_release_install_executed": (
                False
            ),
            "authorization_capsule_consumed": (
                False
            ),
            "current_link_created": False,
            "final_decision": "NO_GO",
        }
    except Exception:
        if (
            staging_root is not None
            and lexists(staging_root)
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


def prepare_real_bundle(
    *,
    wheelhouse_root: Path,
    output_root: Path,
    transaction_id: str,
    fault_point: str | None = None,
) -> dict[str, Any]:
    (
        policy,
        source_manifest,
        sandbox_core,
    ) = validate_policy()

    return prepare_from_inventory(
        policy=policy,
        sandbox_core=sandbox_core,
        source_root=repo,
        source_entries=source_manifest[
            "source_files"
        ],
        wheelhouse_root=wheelhouse_root,
        wheel_entries=source_manifest[
            "wheels"
        ],
        output_root=output_root,
        transaction_id=transaction_id,
        fault_point=fault_point,
    )


def main() -> None:
    validate_policy()

    print(
        "REAL_INPUT_ADAPTER_POLICY_BINDING: PASS"
    )
    print(
        "SOURCE_MANIFEST_MAPPING: ENABLED"
    )
    print(
        "LOCKED_WHEEL_MAPPING: ENABLED"
    )
    print(
        "OUTPUT_MODE_NORMALIZATION_0644: ENABLED"
    )
    print(
        "LEGACY_RELEASE_TREE_COPY: FALSE"
    )
    print(
        "LEGACY_CURRENT_LINK_COPY: FALSE"
    )
    print(
        "LEGACY_VIRTUAL_ENVIRONMENT_COPY: FALSE"
    )
    print(
        "TMP_PREPARED_BUNDLE_ONLY: TRUE"
    )
    print(
        "ROOT_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "AUTHORIZATION_CAPSULE_CONSUMED: FALSE"
    )
    print(
        "CURRENT_LINK_CREATED: FALSE"
    )
    print(
        "SERVICE_START_EXECUTED: FALSE"
    )
    print(
        "UNIT_ENABLE_EXECUTED: FALSE"
    )
    print("FINAL_DECISION: NO_GO")
    print(
        "SQL_B2_4B_5G_3B_1D_2C_2_"
        "REAL_BUNDLE_SANDBOX_ADAPTER: PASS"
    )


if __name__ == "__main__":
    main()
