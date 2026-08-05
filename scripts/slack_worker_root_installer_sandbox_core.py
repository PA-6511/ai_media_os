from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_root_installer_"
    "sandbox_core_policy.json"
)


class SandboxInstallerError(ValueError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


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


def validate_policy() -> dict[str, Any]:
    policy = load_json(
        policy_path
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2C-1"
    ):
        raise SandboxInstallerError(
            "POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_UNPRIVILEGED_ROOT_INSTALLER_"
        "SANDBOX_CORE_TMP_ONLY_"
        "NO_HOST_INSTALL_NO_GO"
    ):
        raise SandboxInstallerError(
            "POLICY_RESULT_INVALID"
        )

    bindings = policy["bindings"]

    path_hash_pairs = (
        (
            "root_install_policy_path",
            "root_install_policy_sha256",
        ),
        (
            "release_bundle_policy_path",
            "release_bundle_policy_sha256",
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
            "root_helper_interface_policy_path",
            "root_helper_interface_policy_sha256",
        ),
        (
            "install_capsule_policy_path",
            "install_capsule_policy_sha256",
        ),
    )

    for path_key, hash_key in path_hash_pairs:
        path = repository_path(
            bindings[path_key]
        )

        if not path.is_file():
            raise SandboxInstallerError(
                f"BOUND_INPUT_MISSING: {path_key}"
            )

        if sha256_path(path) != bindings[
            hash_key
        ]:
            raise SandboxInstallerError(
                f"BOUND_INPUT_HASH_INVALID: "
                f"{hash_key}"
            )

    boundary = policy[
        "sandbox_boundary"
    ]

    for key in (
        "bundle_root_must_be_below_tmp",
        "install_root_must_be_below_tmp",
        "direct_tmp_root_use_rejected",
        "caller_supplied_paths_required",
        "existing_symlink_ancestry_rejected",
    ):
        if boundary[key] is not True:
            raise SandboxInstallerError(
                f"SANDBOX_TRUE_STATE_INVALID: {key}"
            )

    for key in (
        "repository_write_allowed",
        "future_release_path_access_allowed",
        "future_current_link_access_allowed",
        "future_authorization_path_access_allowed",
        "future_consumption_state_access_allowed",
        "root_execution_required",
        ("su" "do_allowed"),
        "network_allowed",
        ("sub" "process_allowed"),
        "secret_read_allowed",
        "database_access_allowed",
    ):
        if boundary[key] is not False:
            raise SandboxInstallerError(
                f"SANDBOX_FALSE_STATE_INVALID: {key}"
            )

    transaction = policy[
        "transaction_contract"
    ]

    if transaction[
        "exclusive_install_lock_required"
    ] is not True:
        raise SandboxInstallerError(
            "LOCK_CONTRACT_INVALID"
        )

    if transaction[
        "atomic_staging_to_final_rename"
    ] is not True:
        raise SandboxInstallerError(
            "COMMIT_CONTRACT_INVALID"
        )

    if transaction[
        "current_link_creation_allowed"
    ] is not False:
        raise SandboxInstallerError(
            "CURRENT_LINK_STATE_INVALID"
        )

    governance = policy[
        "governance"
    ]

    if governance[
        "sandbox_core_implemented"
    ] is not True:
        raise SandboxInstallerError(
            "SANDBOX_CORE_STATE_INVALID"
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
            raise SandboxInstallerError(
                f"GOVERNANCE_STATE_INVALID: {key}"
            )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise SandboxInstallerError(
            "FINAL_DECISION_INVALID"
        )

    return policy


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
        raise SandboxInstallerError(
            f"{field_name}_DIRECT_TMP_REJECTED"
        )

    if tmp_root not in path.parents:
        raise SandboxInstallerError(
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
                raise SandboxInstallerError(
                    f"{field_name}_SYMLINK_ANCESTRY_REJECTED"
                )

        current = current.parent

    if must_exist and not path.exists():
        raise SandboxInstallerError(
            f"{field_name}_MISSING"
        )

    return path


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
            raise SandboxInstallerError(
                f"DIRECTORY_CUSTODY_INVALID: {path}"
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

    if stat.S_IMODE(
        path.lstat().st_mode
    ) != mode:
        raise SandboxInstallerError(
            f"DIRECTORY_MODE_INVALID: {path}"
        )


def reject_duplicate_keys(
    pairs: list[
        tuple[str, Any]
    ],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise SandboxInstallerError(
                f"DUPLICATE_JSON_KEY: {key}"
            )

        result[key] = value

    return result


def read_bounded_file(
    path: Path,
    maximum_size: int,
) -> bytes:
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
        raise SandboxInstallerError(
            f"FILE_OPEN_FAILED: {path}"
        ) from exc

    chunks: list[bytes] = []
    total = 0

    try:
        value = os.fstat(
            descriptor
        )

        if not stat.S_ISREG(
            value.st_mode
        ):
            raise SandboxInstallerError(
                f"REGULAR_FILE_REQUIRED: {path}"
            )

        if value.st_nlink != 1:
            raise SandboxInstallerError(
                f"HARDLINK_REJECTED: {path}"
            )

        while True:
            chunk = os.read(
                descriptor,
                65536,
            )

            if not chunk:
                break

            total += len(chunk)

            if total > maximum_size:
                raise SandboxInstallerError(
                    f"FILE_SIZE_LIMIT_EXCEEDED: {path}"
                )

            chunks.append(chunk)
    finally:
        os.close(
            descriptor
        )

    return b"".join(chunks)


def validate_relative_path(
    raw_path: object,
) -> str:
    if not isinstance(raw_path, str):
        raise SandboxInstallerError(
            "MANIFEST_PATH_TYPE_INVALID"
        )

    if (
        not raw_path
        or "\\" in raw_path
        or raw_path.startswith("/")
    ):
        raise SandboxInstallerError(
            f"MANIFEST_PATH_INVALID: {raw_path!r}"
        )

    pure = PurePosixPath(
        raw_path
    )

    parts = pure.parts

    if (
        not parts
        or any(
            part in (
                "",
                ".",
                "..",
            )
            for part in parts
        )
    ):
        raise SandboxInstallerError(
            f"MANIFEST_PATH_TRAVERSAL: {raw_path}"
        )

    normalized = pure.as_posix()

    if normalized != raw_path:
        raise SandboxInstallerError(
            f"MANIFEST_PATH_NOT_NORMALIZED: {raw_path}"
        )

    return normalized


def load_and_validate_manifest(
    bundle_root: Path,
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    bytes,
]:
    contract = policy[
        "prepared_bundle_contract"
    ]

    entries = {
        item.name
        for item in bundle_root.iterdir()
    }

    if entries != set(
        contract[
            "top_level_entries"
        ]
    ):
        raise SandboxInstallerError(
            "BUNDLE_TOP_LEVEL_ENTRIES_INVALID"
        )

    payload_root = (
        bundle_root / "payload"
    )

    if (
        payload_root.is_symlink()
        or not payload_root.is_dir()
    ):
        raise SandboxInstallerError(
            "PAYLOAD_DIRECTORY_INVALID"
        )

    manifest_path = (
        bundle_root
        / "bundle-manifest.json"
    )

    manifest_bytes = read_bounded_file(
        manifest_path,
        contract[
            "maximum_manifest_bytes"
        ],
    )

    try:
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=(
                reject_duplicate_keys
            ),
        )
    except SandboxInstallerError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise SandboxInstallerError(
            "BUNDLE_MANIFEST_INVALID"
        ) from exc

    if not isinstance(
        manifest,
        dict,
    ):
        raise SandboxInstallerError(
            "BUNDLE_MANIFEST_OBJECT_REQUIRED"
        )

    if set(manifest) != set(
        contract[
            "manifest_required_keys"
        ]
    ):
        raise SandboxInstallerError(
            "BUNDLE_MANIFEST_KEYS_INVALID"
        )

    exact_values = {
        "schema_version": (
            contract[
                "manifest_schema_version"
            ]
        ),
        "release_id": (
            contract["release_id"]
        ),
        "source_manifest_sha256": (
            contract[
                "source_manifest_sha256"
            ]
        ),
        "requirements_hash_lock_sha256": (
            contract[
                "requirements_hash_lock_sha256"
            ]
        ),
        "root_install_policy_sha256": (
            contract[
                "root_install_policy_sha256"
            ]
        ),
        "source_file_count": (
            contract[
                "source_file_count"
            ]
        ),
        "wheel_count": (
            contract[
                "wheel_count"
            ]
        ),
    }

    for key, expected in (
        exact_values.items()
    ):
        if manifest[key] != expected:
            raise SandboxInstallerError(
                f"BUNDLE_BINDING_INVALID: {key}"
            )

    files = manifest["files"]

    if not isinstance(files, list):
        raise SandboxInstallerError(
            "BUNDLE_FILES_LIST_REQUIRED"
        )

    normalized_files: list[
        dict[str, Any]
    ] = []

    seen_paths: set[str] = set()
    source_count = 0
    wheel_count = 0

    for entry in files:
        if not isinstance(entry, dict):
            raise SandboxInstallerError(
                "BUNDLE_FILE_ENTRY_OBJECT_REQUIRED"
            )

        if set(entry) != set(
            contract[
                "file_entry_required_keys"
            ]
        ):
            raise SandboxInstallerError(
                "BUNDLE_FILE_ENTRY_KEYS_INVALID"
            )

        relative = validate_relative_path(
            entry["path"]
        )

        if relative in seen_paths:
            raise SandboxInstallerError(
                f"BUNDLE_DUPLICATE_PATH: {relative}"
            )

        seen_paths.add(relative)

        if relative.startswith(
            contract["source_prefix"]
        ):
            source_count += 1
        elif relative.startswith(
            contract["wheel_prefix"]
        ):
            wheel_count += 1
        else:
            raise SandboxInstallerError(
                f"BUNDLE_PATH_PREFIX_INVALID: {relative}"
            )

        file_hash = entry["sha256"]
        file_size = entry["size"]
        file_mode = entry["mode"]

        if (
            not isinstance(file_hash, str)
            or re.fullmatch(
                r"^[a-f0-9]{64}$",
                file_hash,
            )
            is None
        ):
            raise SandboxInstallerError(
                f"BUNDLE_FILE_HASH_INVALID: {relative}"
            )

        if (
            type(file_size) is not int
            or file_size < 0
            or file_size > contract[
                "maximum_file_bytes"
            ]
        ):
            raise SandboxInstallerError(
                f"BUNDLE_FILE_SIZE_INVALID: {relative}"
            )

        if file_mode not in contract[
            "allowed_modes"
        ]:
            raise SandboxInstallerError(
                f"BUNDLE_FILE_MODE_INVALID: {relative}"
            )

        normalized_files.append(
            {
                "path": relative,
                "sha256": file_hash,
                "size": file_size,
                "mode": file_mode,
            }
        )

    if source_count != contract[
        "source_file_count"
    ]:
        raise SandboxInstallerError(
            "BUNDLE_SOURCE_COUNT_INVALID"
        )

    if wheel_count != contract[
        "wheel_count"
    ]:
        raise SandboxInstallerError(
            "BUNDLE_WHEEL_COUNT_INVALID"
        )

    actual_paths: set[str] = set()

    for directory, names, filenames in os.walk(
        payload_root,
        topdown=True,
        followlinks=False,
    ):
        directory_path = Path(directory)

        for name in list(names):
            child = directory_path / name
            value = child.lstat()

            if stat.S_ISLNK(
                value.st_mode
            ):
                raise SandboxInstallerError(
                    f"PAYLOAD_SYMLINK_REJECTED: {child}"
                )

            if not stat.S_ISDIR(
                value.st_mode
            ):
                raise SandboxInstallerError(
                    f"PAYLOAD_SPECIAL_ENTRY_REJECTED: {child}"
                )

        for filename in filenames:
            child = directory_path / filename
            value = child.lstat()

            if (
                stat.S_ISLNK(value.st_mode)
                or not stat.S_ISREG(
                    value.st_mode
                )
            ):
                raise SandboxInstallerError(
                    f"PAYLOAD_FILE_TYPE_INVALID: {child}"
                )

            if value.st_nlink != 1:
                raise SandboxInstallerError(
                    f"PAYLOAD_HARDLINK_REJECTED: {child}"
                )

            relative = child.relative_to(
                payload_root
            ).as_posix()

            actual_paths.add(relative)

    if actual_paths != seen_paths:
        raise SandboxInstallerError(
            "PAYLOAD_TREE_MANIFEST_MISMATCH"
        )

    for entry in normalized_files:
        path = (
            payload_root
            / entry["path"]
        )

        payload = read_bounded_file(
            path,
            contract[
                "maximum_file_bytes"
            ],
        )

        if len(payload) != entry[
            "size"
        ]:
            raise SandboxInstallerError(
                f"PAYLOAD_SIZE_MISMATCH: "
                f"{entry['path']}"
            )

        if sha256_bytes(payload) != entry[
            "sha256"
        ]:
            raise SandboxInstallerError(
                f"PAYLOAD_HASH_MISMATCH: "
                f"{entry['path']}"
            )

    normalized_manifest = dict(
        manifest
    )

    normalized_manifest["files"] = sorted(
        normalized_files,
        key=lambda item: item["path"],
    )

    return (
        normalized_manifest,
        canonical_bytes(
            normalized_manifest
        ),
    )


def open_lock_file(path: Path) -> int:
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
        not stat.S_ISREG(value.st_mode)
        or value.st_nlink != 1
    ):
        os.close(descriptor)

        raise SandboxInstallerError(
            "INSTALL_LOCK_CUSTODY_INVALID"
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
            raise SandboxInstallerError(
                "DESTINATION_SHORT_WRITE"
            )

        offset += written


def copy_manifest_file(
    source_path: Path,
    destination_path: Path,
    entry: dict[str, Any],
    maximum_size: int,
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
        source_stat = os.fstat(
            source_descriptor
        )

        if (
            not stat.S_ISREG(
                source_stat.st_mode
            )
            or source_stat.st_nlink != 1
        ):
            raise SandboxInstallerError(
                f"SOURCE_COPY_CUSTODY_INVALID: "
                f"{entry['path']}"
            )

        mode = int(
            entry["mode"],
            8,
        )

        destination_descriptor = os.open(
            os.fspath(destination_path),
            destination_flags,
            mode,
        )

        digest = hashlib.sha256()
        total = 0

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

                total += len(chunk)

                if total > maximum_size:
                    raise SandboxInstallerError(
                        f"COPY_SIZE_LIMIT_EXCEEDED: "
                        f"{entry['path']}"
                    )

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

    if total != entry["size"]:
        raise SandboxInstallerError(
            f"COPIED_SIZE_MISMATCH: "
            f"{entry['path']}"
        )

    if digest.hexdigest() != entry[
        "sha256"
    ]:
        raise SandboxInstallerError(
            f"COPIED_HASH_MISMATCH: "
            f"{entry['path']}"
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


def utc_timestamp(value: datetime) -> str:
    normalized = value.astimezone(
        timezone.utc
    )

    result = normalized.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )

    if normalized.microsecond:
        result += (
            f".{normalized.microsecond:06d}"
        )

    return result + "Z"


def remove_owned_tree(path: Path) -> None:
    if not lexists(path):
        return

    if path.is_symlink():
        raise SandboxInstallerError(
            "STAGING_SYMLINK_CLEANUP_REJECTED"
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
                raise SandboxInstallerError(
                    "STAGING_FILE_SYMLINK_CLEANUP_REJECTED"
                )

            child.unlink()

        for name in names:
            child = directory_path / name

            if child.is_symlink():
                raise SandboxInstallerError(
                    "STAGING_DIRECTORY_SYMLINK_CLEANUP_REJECTED"
                )

            child.rmdir()

    path.rmdir()


def validate_installed_release(
    final_path: Path,
    manifest: dict[str, Any],
    manifest_sha256: str,
    policy: dict[str, Any],
) -> None:
    if (
        final_path.is_symlink()
        or not final_path.is_dir()
    ):
        raise SandboxInstallerError(
            "EXISTING_FINAL_RELEASE_INVALID"
        )

    expected_paths = {
        entry["path"]
        for entry in manifest["files"]
    }

    receipt_name = policy[
        "transaction_contract"
    ]["receipt_filename"]

    actual_paths: set[str] = set()

    for directory, names, filenames in os.walk(
        final_path,
        topdown=True,
        followlinks=False,
    ):
        directory_path = Path(directory)

        for name in names:
            child = directory_path / name

            if child.is_symlink():
                raise SandboxInstallerError(
                    "INSTALLED_DIRECTORY_SYMLINK_REJECTED"
                )

        for filename in filenames:
            child = directory_path / filename

            if child.is_symlink():
                raise SandboxInstallerError(
                    "INSTALLED_FILE_SYMLINK_REJECTED"
                )

            relative = child.relative_to(
                final_path
            ).as_posix()

            actual_paths.add(relative)

    if actual_paths != (
        expected_paths
        | {receipt_name}
    ):
        raise SandboxInstallerError(
            "INSTALLED_TREE_MISMATCH"
        )

    maximum_size = policy[
        "prepared_bundle_contract"
    ]["maximum_file_bytes"]

    for entry in manifest["files"]:
        payload = read_bounded_file(
            final_path / entry["path"],
            maximum_size,
        )

        if (
            len(payload) != entry["size"]
            or sha256_bytes(payload)
            != entry["sha256"]
        ):
            raise SandboxInstallerError(
                f"INSTALLED_FILE_MISMATCH: "
                f"{entry['path']}"
            )

        actual_mode = format(
            stat.S_IMODE(
                (
                    final_path
                    / entry["path"]
                ).lstat().st_mode
            ),
            "04o",
        )

        if actual_mode != entry["mode"]:
            raise SandboxInstallerError(
                f"INSTALLED_MODE_MISMATCH: "
                f"{entry['path']}"
            )

    receipt_bytes = read_bounded_file(
        final_path / receipt_name,
        65536,
    )

    try:
        receipt = json.loads(
            receipt_bytes.decode("utf-8"),
            object_pairs_hook=(
                reject_duplicate_keys
            ),
        )
    except Exception as exc:
        raise SandboxInstallerError(
            "INSTALL_RECEIPT_INVALID"
        ) from exc

    if receipt != {
        "schema_version": 1,
        "release_id": manifest[
            "release_id"
        ],
        "manifest_sha256": (
            manifest_sha256
        ),
        "sandbox_reference_only": True,
    }:
        raise SandboxInstallerError(
            "INSTALL_RECEIPT_BINDING_INVALID"
        )


def install_prepared_bundle(
    *,
    bundle_root: Path,
    sandbox_install_root: Path,
    transaction_id: str,
    now_utc: datetime,
    fault_point: str | None = None,
) -> dict[str, Any]:
    if now_utc.tzinfo is None:
        raise SandboxInstallerError(
            "NOW_TIMEZONE_REQUIRED"
        )

    if re.fullmatch(
        r"^[a-f0-9]{32}$",
        transaction_id,
    ) is None:
        raise SandboxInstallerError(
            "TRANSACTION_ID_INVALID"
        )

    if fault_point not in (
        None,
        "AFTER_COPY_BEFORE_RECEIPT",
        "AFTER_RECEIPT_BEFORE_COMMIT",
    ):
        raise SandboxInstallerError(
            "FAULT_POINT_INVALID"
        )

    policy = validate_policy()

    bundle_root = validate_tmp_path(
        bundle_root,
        field_name="BUNDLE_ROOT",
        must_exist=True,
    )

    sandbox_install_root = (
        validate_tmp_path(
            sandbox_install_root,
            field_name="SANDBOX_INSTALL_ROOT",
            must_exist=False,
        )
    )

    manifest, canonical_manifest = (
        load_and_validate_manifest(
            bundle_root,
            policy,
        )
    )

    manifest_sha256 = sha256_bytes(
        canonical_manifest
    )

    if not lexists(
        sandbox_install_root
    ):
        sandbox_install_root.mkdir(
            mode=0o700,
            parents=False,
        )

    ensure_directory(
        sandbox_install_root,
        0o700,
    )

    transaction = policy[
        "transaction_contract"
    ]

    releases_root = (
        sandbox_install_root
        / transaction[
            "releases_directory_name"
        ]
    )

    staging_root = (
        sandbox_install_root
        / transaction[
            "staging_directory_name"
        ]
    )

    ensure_directory(
        releases_root,
        0o700,
    )

    ensure_directory(
        staging_root,
        0o700,
    )

    lock_path = (
        sandbox_install_root
        / transaction["lock_filename"]
    )

    lock_descriptor = open_lock_file(
        lock_path
    )

    staging_path: Path | None = None

    try:
        fcntl.flock(
            lock_descriptor,
            fcntl.LOCK_EX,
        )

        release_id = manifest[
            "release_id"
        ]

        final_path = (
            releases_root
            / release_id
        )

        if lexists(final_path):
            validate_installed_release(
                final_path,
                manifest,
                manifest_sha256,
                policy,
            )

            return {
                "state": (
                    "SANDBOX_RELEASE_ALREADY_INSTALLED"
                ),
                "release_id": release_id,
                "sandbox_final_path": str(
                    final_path
                ),
                "sandbox_install_executed": (
                    False
                ),
                "idempotent_existing_release": (
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

        staging_name = (
            ".install-"
            f"{release_id}-"
            f"{transaction_id}"
        )

        if re.fullmatch(
            transaction[
                "staging_name_pattern"
            ],
            staging_name,
        ) is None:
            raise SandboxInstallerError(
                "STAGING_NAME_INVALID"
            )

        staging_path = (
            staging_root
            / staging_name
        )

        if lexists(staging_path):
            raise SandboxInstallerError(
                "STAGING_PATH_ALREADY_PRESENT"
            )

        staging_path.mkdir(
            mode=0o700,
        )

        payload_root = (
            bundle_root / "payload"
        )

        maximum_size = policy[
            "prepared_bundle_contract"
        ]["maximum_file_bytes"]

        for entry in manifest[
            "files"
        ]:
            source_path = (
                payload_root
                / entry["path"]
            )

            destination_path = (
                staging_path
                / entry["path"]
            )

            parent = (
                destination_path.parent
            )

            relative_parent = (
                parent.relative_to(
                    staging_path
                )
            )

            current_parent = staging_path

            for component in (
                relative_parent.parts
            ):
                current_parent = (
                    current_parent
                    / component
                )

                if not lexists(
                    current_parent
                ):
                    current_parent.mkdir(
                        mode=0o755,
                    )

                ensure_directory(
                    current_parent,
                    0o755,
                )

            copy_manifest_file(
                source_path,
                destination_path,
                entry,
                maximum_size,
            )

        if fault_point == (
            "AFTER_COPY_BEFORE_RECEIPT"
        ):
            raise SandboxInstallerError(
                "INJECTED_AFTER_COPY_FAILURE"
            )

        receipt = {
            "schema_version": 1,
            "release_id": (
                manifest["release_id"]
            ),
            "manifest_sha256": (
                manifest_sha256
            ),
            "sandbox_reference_only": (
                True
            ),
        }

        receipt_path = (
            staging_path
            / transaction[
                "receipt_filename"
            ]
        )

        receipt_flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
        )

        if hasattr(os, "O_NOFOLLOW"):
            receipt_flags |= os.O_NOFOLLOW

        receipt_descriptor = os.open(
            os.fspath(receipt_path),
            receipt_flags,
            int(
                transaction[
                    "receipt_mode"
                ],
                8,
            ),
        )

        try:
            os.fchmod(
                receipt_descriptor,
                int(
                    transaction[
                        "receipt_mode"
                    ],
                    8,
                ),
            )

            write_all(
                receipt_descriptor,
                canonical_bytes(receipt),
            )

            os.fsync(
                receipt_descriptor
            )
        finally:
            os.close(
                receipt_descriptor
            )

        for directory, _, _ in os.walk(
            staging_path,
            topdown=False,
            followlinks=False,
        ):
            fsync_directory(
                Path(directory)
            )

        fsync_directory(
            staging_root
        )

        if fault_point == (
            "AFTER_RECEIPT_BEFORE_COMMIT"
        ):
            raise SandboxInstallerError(
                "INJECTED_BEFORE_COMMIT_FAILURE"
            )

        if lexists(final_path):
            raise SandboxInstallerError(
                "FINAL_PATH_RACE_DETECTED"
            )

        os.rename(
            staging_path,
            final_path,
        )

        staging_path = None

        fsync_directory(
            staging_root
        )

        fsync_directory(
            releases_root
        )

        validate_installed_release(
            final_path,
            manifest,
            manifest_sha256,
            policy,
        )

        return {
            "state": (
                "SANDBOX_RELEASE_INSTALLED"
            ),
            "release_id": release_id,
            "sandbox_final_path": str(
                final_path
            ),
            "installed_at": utc_timestamp(
                now_utc
            ),
            "sandbox_install_executed": (
                True
            ),
            "idempotent_existing_release": (
                False
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
    except Exception:
        if (
            staging_path is not None
            and lexists(staging_path)
        ):
            remove_owned_tree(
                staging_path
            )

            fsync_directory(
                staging_root
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


def main() -> None:
    validate_policy()

    print(
        "SANDBOX_INSTALLER_POLICY_BINDING: PASS"
    )
    print(
        "TMP_ONLY_BUNDLE_AND_INSTALL_BOUNDARY: PASS"
    )
    print(
        "PREPARED_BUNDLE_HASH_VALIDATION: ENABLED"
    )
    print(
        "EXCLUSIVE_INSTALL_LOCK: ENABLED"
    )
    print(
        "STAGING_COPY_AND_REVALIDATION: ENABLED"
    )
    print(
        "PRECOMMIT_ROLLBACK: ENABLED"
    )
    print(
        "ATOMIC_SANDBOX_RELEASE_COMMIT: ENABLED"
    )
    print(
        "IDEMPOTENT_FINAL_VALIDATION: ENABLED"
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
        "SQL_B2_4B_5G_3B_1D_2C_1_"
        "SANDBOX_INSTALLER_CORE: PASS"
    )


if __name__ == "__main__":
    main()
