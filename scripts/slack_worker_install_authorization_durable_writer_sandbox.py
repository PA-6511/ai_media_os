from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
from types import ModuleType
from typing import Any


repo = Path(__file__).resolve().parents[1]

writer_policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_durable_writer_"
    "sandbox_policy.json"
)


class SandboxWriterError(ValueError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


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


def load_reference_validator(
    path: Path,
) -> ModuleType:
    spec = (
        importlib.util
        .spec_from_file_location(
            "slack_capsule_reference_validator",
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise SandboxWriterError(
            "REFERENCE_VALIDATOR_LOAD_FAILED"
        )

    module = (
        importlib.util
        .module_from_spec(spec)
    )

    spec.loader.exec_module(
        module
    )

    return module


def validate_writer_policy(
) -> tuple[
    dict[str, Any],
    ModuleType,
]:
    policy = load_json(
        writer_policy_path
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-7"
    ):
        raise SandboxWriterError(
            "WRITER_POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_DURABLE_WRITER_SANDBOX_"
        "REFERENCE_IMPLEMENTATION_"
        "TMP_ONLY_NO_HOST_AUTHORIZATION_NO_GO"
    ):
        raise SandboxWriterError(
            "WRITER_POLICY_RESULT_INVALID"
        )

    bindings = policy["bindings"]

    path_hash_pairs = (
        (
            "durable_consumption_policy_path",
            "durable_consumption_policy_sha256",
        ),
        (
            "capsule_policy_path",
            "capsule_policy_sha256",
        ),
        (
            "reference_validator_policy_path",
            "reference_validator_policy_sha256",
        ),
        (
            "reference_validator_source_path",
            "reference_validator_source_sha256",
        ),
    )

    loaded_paths: dict[str, Path] = {}

    for path_key, hash_key in path_hash_pairs:
        path = repository_path(
            bindings[path_key]
        )

        if not path.is_file():
            raise SandboxWriterError(
                f"BOUND_INPUT_MISSING: {path_key}"
            )

        if sha256_path(path) != bindings[
            hash_key
        ]:
            raise SandboxWriterError(
                f"BOUND_INPUT_HASH_INVALID: "
                f"{hash_key}"
            )

        loaded_paths[path_key] = path

    durable_policy = load_json(
        loaded_paths[
            "durable_consumption_policy_path"
        ]
    )

    capsule_policy = load_json(
        loaded_paths[
            "capsule_policy_path"
        ]
    )

    if durable_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-6"
    ):
        raise SandboxWriterError(
            "DURABLE_POLICY_PHASE_INVALID"
        )

    if capsule_policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-2B-3"
    ):
        raise SandboxWriterError(
            "CAPSULE_POLICY_PHASE_INVALID"
        )

    if bindings["release_id"] != (
        durable_policy[
            "bindings"
        ]["release_id"]
    ):
        raise SandboxWriterError(
            "DURABLE_RELEASE_ID_INVALID"
        )

    if bindings["release_id"] != (
        capsule_policy[
            "release_binding"
        ]["release_id"]
    ):
        raise SandboxWriterError(
            "CAPSULE_RELEASE_ID_INVALID"
        )

    boundary = policy[
        "sandbox_boundary"
    ]

    if boundary[
        "required_parent_prefix"
    ] != "/tmp":
        raise SandboxWriterError(
            "SANDBOX_PREFIX_INVALID"
        )

    for key in (
        "exact_sandbox_path_caller_supplied",
        "sandbox_directory_creation_allowed",
        "sandbox_file_creation_allowed",
        "sandbox_file_fsync_allowed",
        "sandbox_directory_fsync_allowed",
        "sandbox_atomic_rename_allowed",
    ):
        if boundary[key] is not True:
            raise SandboxWriterError(
                f"SANDBOX_TRUE_STATE_INVALID: {key}"
            )

    for key in (
        "default_host_state_path_used",
        "future_host_state_root_access_allowed",
        "future_capsule_path_access_allowed",
        "repository_path_write_allowed",
        "root_execution_required",
        "root_custody_validation_claimed",
        "durable_host_consumption_claimed",
    ):
        if boundary[key] is not False:
            raise SandboxWriterError(
                f"SANDBOX_FALSE_STATE_INVALID: {key}"
            )

    governance = policy[
        "governance"
    ]

    if governance[
        "sandbox_reference_only"
    ] is not True:
        raise SandboxWriterError(
            "SANDBOX_REFERENCE_STATE_INVALID"
        )

    for key in (
        "host_change_executed",
        "capsule_issued",
        "capsule_file_created",
        "authorization_consumed_in_sandbox",
        "authorization_consumed_on_host",
        "host_consumption_record_created",
        "durable_host_writer_implemented",
        "durable_host_writer_installed",
        "root_file_custody_validated",
        "root_release_install_authorized",
        "root_release_install_executed",
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
            raise SandboxWriterError(
                f"GOVERNANCE_STATE_INVALID: {key}"
            )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise SandboxWriterError(
            "FINAL_DECISION_INVALID"
        )

    reference = load_reference_validator(
        loaded_paths[
            "reference_validator_source_path"
        ]
    )

    return policy, reference


def reject_duplicate_keys(
    pairs: list[
        tuple[str, Any]
    ],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise SandboxWriterError(
                f"DUPLICATE_RECORD_KEY: {key}"
            )

        result[key] = value

    return result


def canonical_bytes(
    value: dict[str, Any],
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


def is_lexically_present(path: Path) -> bool:
    return os.path.lexists(
        os.fspath(path)
    )


def validate_sandbox_path(
    sandbox_root: Path,
) -> Path:
    sandbox_root = Path(
        os.path.abspath(
            os.fspath(sandbox_root)
        )
    )

    tmp_root = Path("/tmp").resolve()

    if sandbox_root == tmp_root:
        raise SandboxWriterError(
            "TMP_ROOT_DIRECT_USE_REJECTED"
        )

    parent = sandbox_root.parent.resolve(
        strict=True
    )

    if not (
        parent == tmp_root
        or tmp_root in parent.parents
    ):
        raise SandboxWriterError(
            "SANDBOX_OUTSIDE_TMP_REJECTED"
        )

    if (
        is_lexically_present(
            sandbox_root
        )
        and sandbox_root.is_symlink()
    ):
        raise SandboxWriterError(
            "SANDBOX_ROOT_SYMLINK_REJECTED"
        )

    return sandbox_root


def validate_directory(
    path: Path,
    expected_mode: int,
) -> None:
    value = path.lstat()

    if not stat.S_ISDIR(
        value.st_mode
    ):
        raise SandboxWriterError(
            f"DIRECTORY_REQUIRED: {path}"
        )

    if stat.S_ISLNK(
        value.st_mode
    ):
        raise SandboxWriterError(
            f"DIRECTORY_SYMLINK_REJECTED: {path}"
        )

    mode = stat.S_IMODE(
        value.st_mode
    )

    if mode != expected_mode:
        raise SandboxWriterError(
            f"DIRECTORY_MODE_INVALID: "
            f"{path}:{mode:04o}"
        )


def prepare_sandbox_root(
    sandbox_root: Path,
) -> tuple[Path, Path]:
    root = validate_sandbox_path(
        sandbox_root
    )

    root.mkdir(
        mode=0o700,
        exist_ok=True,
    )

    os.chmod(
        root,
        0o700,
    )

    validate_directory(
        root,
        0o700,
    )

    records = root / "records"

    if (
        is_lexically_present(records)
        and records.is_symlink()
    ):
        raise SandboxWriterError(
            "RECORDS_SYMLINK_REJECTED"
        )

    records.mkdir(
        mode=0o700,
        exist_ok=True,
    )

    os.chmod(
        records,
        0o700,
    )

    validate_directory(
        records,
        0o700,
    )

    return root, records


def open_lock_file(
    lock_path: Path,
) -> int:
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_CLOEXEC
    )

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(
            os.fspath(lock_path),
            flags,
            0o600,
        )
    except OSError as exc:
        raise SandboxWriterError(
            "LOCK_OPEN_FAILED"
        ) from exc

    os.fchmod(
        descriptor,
        0o600,
    )

    value = os.fstat(
        descriptor
    )

    if not stat.S_ISREG(
        value.st_mode
    ):
        os.close(descriptor)

        raise SandboxWriterError(
            "LOCK_REGULAR_FILE_REQUIRED"
        )

    if value.st_nlink != 1:
        os.close(descriptor)

        raise SandboxWriterError(
            "LOCK_HARDLINK_REJECTED"
        )

    return descriptor


def read_bounded_fd(
    descriptor: int,
    maximum_size: int,
) -> bytes:
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = os.read(
            descriptor,
            4096,
        )

        if not chunk:
            break

        total += len(chunk)

        if total > maximum_size:
            raise SandboxWriterError(
                "RECORD_SIZE_EXCEEDED"
            )

        chunks.append(chunk)

    return b"".join(chunks)


def parse_record_bytes(
    payload: bytes,
) -> dict[str, Any]:
    try:
        text = payload.decode(
            "utf-8"
        )

        value = json.loads(
            text,
            object_pairs_hook=(
                reject_duplicate_keys
            ),
        )
    except SandboxWriterError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise SandboxWriterError(
            "RECORD_DOCUMENT_INVALID"
        ) from exc

    if not isinstance(value, dict):
        raise SandboxWriterError(
            "RECORD_OBJECT_REQUIRED"
        )

    return value


def open_and_read_record(
    path: Path,
    maximum_size: int,
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
        raise SandboxWriterError(
            f"RECORD_OPEN_FAILED: {path.name}"
        ) from exc

    try:
        value = os.fstat(
            descriptor
        )

        if not stat.S_ISREG(
            value.st_mode
        ):
            raise SandboxWriterError(
                f"RECORD_REGULAR_FILE_REQUIRED: "
                f"{path.name}"
            )

        if value.st_nlink != 1:
            raise SandboxWriterError(
                f"RECORD_HARDLINK_REJECTED: "
                f"{path.name}"
            )

        if stat.S_IMODE(
            value.st_mode
        ) != 0o600:
            raise SandboxWriterError(
                f"RECORD_MODE_INVALID: "
                f"{path.name}"
            )

        payload = read_bounded_fd(
            descriptor,
            maximum_size,
        )
    finally:
        os.close(descriptor)

    return parse_record_bytes(
        payload
    )


def validate_record(
    record: dict[str, Any],
    *,
    policy: dict[str, Any],
    filename: str,
    pending_match: re.Match[str] | None,
    final_match: re.Match[str] | None,
) -> None:
    state = policy[
        "sandbox_state_contract"
    ]

    if set(record) != set(
        state[
            "record_required_keys"
        ]
    ):
        raise SandboxWriterError(
            f"RECORD_KEYS_INVALID: {filename}"
        )

    if record[
        "schema_version"
    ] != 1:
        raise SandboxWriterError(
            f"RECORD_SCHEMA_INVALID: {filename}"
        )

    if record[
        "record_state"
    ] != state[
        "record_state_value"
    ]:
        raise SandboxWriterError(
            f"RECORD_STATE_INVALID: {filename}"
        )

    if record[
        "operation"
    ] != state[
        "operation_value"
    ]:
        raise SandboxWriterError(
            f"RECORD_OPERATION_INVALID: {filename}"
        )

    if record[
        "release_id"
    ] != state[
        "release_id_value"
    ]:
        raise SandboxWriterError(
            f"RECORD_RELEASE_ID_INVALID: {filename}"
        )

    if record[
        "final_release_path"
    ] != state[
        "final_release_path_value"
    ]:
        raise SandboxWriterError(
            f"RECORD_FINAL_PATH_INVALID: {filename}"
        )

    if record[
        "sandbox_reference_only"
    ] is not True:
        raise SandboxWriterError(
            f"RECORD_REFERENCE_FLAG_INVALID: "
            f"{filename}"
        )

    if pending_match is not None:
        if (
            record["authorization_id"]
            != pending_match.group(1)
            or record["nonce"]
            != pending_match.group(2)
            or record["transaction_id"]
            != pending_match.group(3)
        ):
            raise SandboxWriterError(
                f"PENDING_FILENAME_BINDING_INVALID: "
                f"{filename}"
            )

    if final_match is not None:
        if record[
            "authorization_id"
        ] != final_match.group(1):
            raise SandboxWriterError(
                f"FINAL_FILENAME_BINDING_INVALID: "
                f"{filename}"
            )


def scan_records(
    records_root: Path,
    policy: dict[str, Any],
) -> tuple[set[str], set[str]]:
    state = policy[
        "sandbox_state_contract"
    ]

    maximum_size = state[
        "record_maximum_size_bytes"
    ]

    pending_pattern = re.compile(
        r"^\.pending-"
        r"(auth-[a-f0-9]{32})-"
        r"([a-f0-9]{64})-"
        r"([a-f0-9]{32})\.json$"
    )

    final_pattern = re.compile(
        r"^(auth-[a-f0-9]{32})\.json$"
    )

    authorization_ids: set[str] = set()
    nonces: set[str] = set()

    for entry in sorted(
        records_root.iterdir(),
        key=lambda item: item.name,
    ):
        pending_match = (
            pending_pattern.fullmatch(
                entry.name
            )
        )

        final_match = (
            final_pattern.fullmatch(
                entry.name
            )
        )

        if (
            pending_match is None
            and final_match is None
        ):
            raise SandboxWriterError(
                f"UNKNOWN_RECORD_ENTRY: "
                f"{entry.name}"
            )

        record = open_and_read_record(
            entry,
            maximum_size,
        )

        validate_record(
            record,
            policy=policy,
            filename=entry.name,
            pending_match=pending_match,
            final_match=final_match,
        )

        authorization_id = record[
            "authorization_id"
        ]

        nonce = record["nonce"]

        if authorization_id in (
            authorization_ids
        ):
            raise SandboxWriterError(
                "EXISTING_AUTHORIZATION_ID_DUPLICATE"
            )

        if nonce in nonces:
            raise SandboxWriterError(
                "EXISTING_NONCE_DUPLICATE"
            )

        authorization_ids.add(
            authorization_id
        )

        nonces.add(nonce)

        if pending_match is not None:
            raise SandboxWriterError(
                "PENDING_RECORD_PRESENT_BLOCKS_"
                "CONSUMPTION"
            )

    return authorization_ids, nonces


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
            raise SandboxWriterError(
                "RECORD_SHORT_WRITE"
            )

        offset += written


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
        os.fsync(
            descriptor
        )
    finally:
        os.close(
            descriptor
        )


def utc_timestamp(
    value: datetime,
) -> str:
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


def consume_to_sandbox(
    document_text: str,
    *,
    now_utc: datetime,
    transaction_id: str,
    sandbox_root: Path,
) -> dict[str, Any]:
    if now_utc.tzinfo is None:
        raise SandboxWriterError(
            "NOW_TIMEZONE_REQUIRED"
        )

    if re.fullmatch(
        r"^[a-f0-9]{32}$",
        transaction_id,
    ) is None:
        raise SandboxWriterError(
            "TRANSACTION_ID_INVALID"
        )

    policy, reference = (
        validate_writer_policy()
    )

    try:
        validation = (
            reference
            .validate_capsule_document_text(
                document_text,
                now_utc=now_utc,
            )
        )

        document = (
            reference.parse_document(
                document_text
            )
        )
    except Exception as exc:
        reference_error = getattr(
            reference,
            "CapsuleValidationError",
        )

        if isinstance(
            exc,
            reference_error,
        ):
            raise SandboxWriterError(
                f"DOCUMENT_REJECTED: {exc}"
            ) from exc

        raise

    root, records = (
        prepare_sandbox_root(
            sandbox_root
        )
    )

    lock_path = (
        root / "consume.lock"
    )

    lock_descriptor = (
        open_lock_file(
            lock_path
        )
    )

    try:
        fcntl.flock(
            lock_descriptor,
            fcntl.LOCK_EX,
        )

        (
            authorization_ids,
            nonces,
        ) = scan_records(
            records,
            policy,
        )

        authorization_id = document[
            "authorization_id"
        ]

        nonce = document["nonce"]

        if authorization_id in (
            authorization_ids
        ):
            raise SandboxWriterError(
                "AUTHORIZATION_ID_REPLAY_REJECTED"
            )

        if nonce in nonces:
            raise SandboxWriterError(
                "NONCE_REPLAY_REJECTED"
            )

        state = policy[
            "sandbox_state_contract"
        ]

        record = {
            "schema_version": 1,
            "record_state": state[
                "record_state_value"
            ],
            "authorization_id": (
                authorization_id
            ),
            "nonce": nonce,
            "release_id": validation[
                "release_id"
            ],
            "operation": state[
                "operation_value"
            ],
            "capsule_sha256": (
                sha256_bytes(
                    document_text.encode(
                        "utf-8"
                    )
                )
            ),
            "canonical_document_sha256": (
                validation[
                    "canonical_document_sha256"
                ]
            ),
            "consumed_at": utc_timestamp(
                now_utc
            ),
            "transaction_id": (
                transaction_id
            ),
            "final_release_path": state[
                "final_release_path_value"
            ],
            "sandbox_reference_only": (
                True
            ),
        }

        payload = canonical_bytes(
            record
        )

        if len(payload) > state[
            "record_maximum_size_bytes"
        ]:
            raise SandboxWriterError(
                "GENERATED_RECORD_SIZE_EXCEEDED"
            )

        pending_name = (
            ".pending-"
            f"{authorization_id}-"
            f"{nonce}-"
            f"{transaction_id}.json"
        )

        final_name = (
            f"{authorization_id}.json"
        )

        pending_path = (
            records / pending_name
        )

        final_path = (
            records / final_name
        )

        if is_lexically_present(
            pending_path
        ):
            raise SandboxWriterError(
                "PENDING_RECORD_COLLISION"
            )

        if is_lexically_present(
            final_path
        ):
            raise SandboxWriterError(
                "FINAL_RECORD_COLLISION"
            )

        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
        )

        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW

        try:
            descriptor = os.open(
                os.fspath(
                    pending_path
                ),
                flags,
                0o600,
            )
        except OSError as exc:
            raise SandboxWriterError(
                "PENDING_RECORD_CREATE_FAILED"
            ) from exc

        try:
            os.fchmod(
                descriptor,
                0o600,
            )

            write_all(
                descriptor,
                payload,
            )

            os.fsync(
                descriptor
            )
        finally:
            os.close(
                descriptor
            )

        fsync_directory(
            records
        )

        os.rename(
            pending_path,
            final_path,
        )

        fsync_directory(
            records
        )

        result = {
            "validation_passed": True,
            "state": (
                "SANDBOX_DURABLE_CONSUMED_"
                "REFERENCE_ONLY"
            ),
            "authorization_id": (
                authorization_id
            ),
            "release_id": validation[
                "release_id"
            ],
            "sandbox_record_path": str(
                final_path
            ),
            "authorization_consumed_in_sandbox": (
                True
            ),
            "authorization_consumed_on_host": (
                False
            ),
            "host_consumption_record_created": (
                False
            ),
            "root_file_custody_validated": (
                False
            ),
            "execution_allowed": False,
            "root_release_install_authorized": (
                False
            ),
            "root_release_install_executed": (
                False
            ),
            "final_decision": "NO_GO",
        }

        return result
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
    validate_writer_policy()

    print(
        "DURABLE_WRITER_POLICY_BINDING: PASS"
    )
    print(
        "TMP_SANDBOX_ONLY_BOUNDARY: PASS"
    )
    print(
        "EXCLUSIVE_LOCK_PROTOCOL: ENABLED"
    )
    print(
        "PENDING_EXCLUSIVE_CREATE: ENABLED"
    )
    print(
        "FILE_AND_DIRECTORY_FSYNC: ENABLED"
    )
    print(
        "ATOMIC_PENDING_FINAL_RENAME: ENABLED"
    )
    print(
        "HOST_CAPSULE_FILE_READ: FALSE"
    )
    print(
        "AUTHORIZATION_CONSUMED_ON_HOST: FALSE"
    )
    print(
        "HOST_CONSUMPTION_RECORD_CREATED: FALSE"
    )
    print(
        "ROOT_FILE_CUSTODY_VALIDATED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_AUTHORIZED: FALSE"
    )
    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )
    print(
        "SERVICE_START_EXECUTED: FALSE"
    )
    print(
        "UNIT_ENABLE_EXECUTED: FALSE"
    )
    print("FINAL_DECISION: NO_GO")
    print(
        "SQL_B2_4B_5G_3B_1D_2B_7_"
        "DURABLE_WRITER_SANDBOX: PASS"
    )


if __name__ == "__main__":
    main()
