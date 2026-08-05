#!/usr/bin/python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any


GATE_PATH = Path(
    "/etc/ai-media-os-autostart/"
    "slack-readiness-autostart.approved"
)

INSTALLED_UNIT_PATH = Path(
    "/etc/systemd/system/"
    "ai-media-os-slack-approval-readiness.service"
)

VERIFIER_PATH = Path(
    "/usr/local/libexec/ai-media-os/"
    "slack-autostart-verifier.py"
)


TRUSTED_PATH_ROOT = Path("/")

EXPECTED_SCHEMA_VERSION = 2

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_SLACK_READINESS_AUTOSTART_ONLY"
)

EXPECTED_TARGET_UNIT = (
    "ai-media-os-slack-approval-readiness.service"
)

EXPECTED_SAFETY_SCOPE = (
    "READINESS_DRY_RUN_AUTOSTART_ONLY"
)

MAXIMUM_GATE_BYTES = 16 * 1024
MAXIMUM_UNIT_BYTES = 128 * 1024
MAXIMUM_VERIFIER_BYTES = 512 * 1024

MAXIMUM_VALIDITY = timedelta(hours=24)
MAXIMUM_CLOCK_SKEW = timedelta(minutes=5)

SHA256_PATTERN = re.compile(
    r"^[0-9a-f]{64}$"
)

TOKEN_SHAPE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9-])"
    r"(?:xoxb|xapp)-[A-Za-z0-9-]{20,}"
    r"(?![A-Za-z0-9-])"
)

REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "approval_label",
        "target_unit",
        "installed_unit_sha256",
        "verifier_sha256",
        "approved_by",
        "approved_at",
        "expires_at",
        "production_status",
        "safety_scope",
        "slack_mode",
        "production_database_allowed",
        "automatic_start_allowed",
    }
)


class TrustedVerifierError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TrustedApproval:
    installed_unit_sha256: str
    verifier_sha256: str
    approved_by: str
    approved_at: datetime
    expires_at: datetime


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_parent(
    path: Path,
    *,
    trusted_root: Path,
    expected_uid: int,
    expected_gid: int,
    code_prefix: str,
) -> None:
    if not path.is_absolute():
        raise TrustedVerifierError(
            f"{code_prefix}_PATH_NOT_ABSOLUTE"
        )

    if not trusted_root.is_absolute():
        raise TrustedVerifierError(
            f"{code_prefix}_TRUSTED_ROOT_NOT_ABSOLUTE"
        )

    try:
        relative_parent = (
            path.parent.relative_to(
                trusted_root
            )
        )
    except ValueError as exc:
        raise TrustedVerifierError(
            f"{code_prefix}_PATH_OUTSIDE_TRUSTED_ROOT"
        ) from exc

    if ".." in relative_parent.parts:
        raise TrustedVerifierError(
            f"{code_prefix}_PARENT_TRAVERSAL"
        )

    directories = [
        trusted_root
    ]

    current = trusted_root

    for component in relative_parent.parts:
        current = current / component
        directories.append(current)

    for directory in directories:
        try:
            directory_stat = (
                directory.lstat()
            )
        except FileNotFoundError as exc:
            raise TrustedVerifierError(
                f"{code_prefix}_PARENT_MISSING"
            ) from exc

        if stat.S_ISLNK(
            directory_stat.st_mode
        ):
            raise TrustedVerifierError(
                f"{code_prefix}_PARENT_SYMLINK"
            )

        if not stat.S_ISDIR(
            directory_stat.st_mode
        ):
            raise TrustedVerifierError(
                f"{code_prefix}_PARENT_NOT_DIRECTORY"
            )

        if directory_stat.st_uid != expected_uid:
            raise TrustedVerifierError(
                f"{code_prefix}_PARENT_OWNER_INVALID"
            )

        if directory_stat.st_gid != expected_gid:
            raise TrustedVerifierError(
                f"{code_prefix}_PARENT_GROUP_INVALID"
            )

        directory_mode = stat.S_IMODE(
            directory_stat.st_mode
        )

        if directory_mode & 0o022:
            raise TrustedVerifierError(
                f"{code_prefix}_PARENT_WRITABLE"
            )

def _secure_read(
    path: Path,
    *,
    trusted_root: Path,
    expected_uid: int,
    expected_gid: int,
    expected_mode: int,
    maximum_bytes: int,
    code_prefix: str,
) -> bytes:
    _validate_parent(
        path,
        trusted_root=trusted_root,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        code_prefix=code_prefix,
    )

    flags = os.O_RDONLY | os.O_CLOEXEC

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        file_descriptor = os.open(
            path,
            flags,
        )
    except FileNotFoundError as exc:
        raise TrustedVerifierError(
            f"{code_prefix}_MISSING"
        ) from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise TrustedVerifierError(
                f"{code_prefix}_SYMLINK"
            ) from exc

        raise TrustedVerifierError(
            f"{code_prefix}_OPEN_FAILED"
        ) from exc

    try:
        initial_stat = os.fstat(
            file_descriptor
        )

        if not stat.S_ISREG(
            initial_stat.st_mode
        ):
            raise TrustedVerifierError(
                f"{code_prefix}_NOT_REGULAR_FILE"
            )

        if initial_stat.st_uid != expected_uid:
            raise TrustedVerifierError(
                f"{code_prefix}_OWNER_INVALID"
            )

        if initial_stat.st_gid != expected_gid:
            raise TrustedVerifierError(
                f"{code_prefix}_GROUP_INVALID"
            )

        file_mode = stat.S_IMODE(
            initial_stat.st_mode
        )

        if file_mode != expected_mode:
            raise TrustedVerifierError(
                f"{code_prefix}_MODE_INVALID"
            )

        if initial_stat.st_size > maximum_bytes:
            raise TrustedVerifierError(
                f"{code_prefix}_TOO_LARGE"
            )

        chunks: list[bytes] = []
        total_size = 0

        while True:
            chunk = os.read(
                file_descriptor,
                64 * 1024,
            )

            if not chunk:
                break

            chunks.append(chunk)
            total_size += len(chunk)

            if total_size > maximum_bytes:
                raise TrustedVerifierError(
                    f"{code_prefix}_TOO_LARGE"
                )

        final_stat = os.fstat(
            file_descriptor
        )

        if (
            initial_stat.st_dev
            != final_stat.st_dev
            or initial_stat.st_ino
            != final_stat.st_ino
            or initial_stat.st_size
            != final_stat.st_size
        ):
            raise TrustedVerifierError(
                f"{code_prefix}_CHANGED_DURING_READ"
            )

        data = b"".join(chunks)

        if len(data) != final_stat.st_size:
            raise TrustedVerifierError(
                f"{code_prefix}_SIZE_MISMATCH"
            )

        return data
    finally:
        os.close(file_descriptor)


def _reject_duplicate_fields(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise TrustedVerifierError(
                "GATE_DUPLICATE_FIELD"
            )

        result[key] = value

    return result


def _reject_nonfinite_number(
    _value: str,
) -> None:
    raise TrustedVerifierError(
        "GATE_NONFINITE_NUMBER"
    )


def _load_gate_payload(
    raw_bytes: bytes,
) -> dict[str, Any]:
    try:
        raw_text = raw_bytes.decode(
            "utf-8"
        )
    except UnicodeDecodeError as exc:
        raise TrustedVerifierError(
            "GATE_NOT_UTF8"
        ) from exc

    if TOKEN_SHAPE_PATTERN.search(raw_text):
        raise TrustedVerifierError(
            "GATE_CREDENTIAL_SHAPE_DETECTED"
        )

    try:
        payload = json.loads(
            raw_text,
            object_pairs_hook=(
                _reject_duplicate_fields
            ),
            parse_constant=(
                _reject_nonfinite_number
            ),
        )
    except TrustedVerifierError:
        raise
    except json.JSONDecodeError as exc:
        raise TrustedVerifierError(
            "GATE_INVALID_JSON"
        ) from exc

    if not isinstance(payload, dict):
        raise TrustedVerifierError(
            "GATE_NOT_OBJECT"
        )

    actual_fields = frozenset(
        payload.keys()
    )

    if actual_fields != REQUIRED_FIELDS:
        missing = (
            REQUIRED_FIELDS - actual_fields
        )

        if missing:
            raise TrustedVerifierError(
                "GATE_REQUIRED_FIELD_MISSING"
            )

        raise TrustedVerifierError(
            "GATE_UNEXPECTED_FIELD"
        )

    return payload


def _expect_exact(
    payload: dict[str, Any],
    field_name: str,
    expected: Any,
) -> None:
    actual = payload[field_name]

    if type(actual) is not type(expected):
        raise TrustedVerifierError(
            f"GATE_{field_name.upper()}_TYPE_INVALID"
        )

    if actual != expected:
        raise TrustedVerifierError(
            f"GATE_{field_name.upper()}_INVALID"
        )


def _parse_datetime(
    value: Any,
    field_name: str,
) -> datetime:
    if not isinstance(value, str):
        raise TrustedVerifierError(
            f"GATE_{field_name.upper()}_TYPE_INVALID"
        )

    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = (
            normalized[:-1] + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError as exc:
        raise TrustedVerifierError(
            f"GATE_{field_name.upper()}_INVALID"
        ) from exc

    if parsed.tzinfo is None:
        raise TrustedVerifierError(
            f"GATE_{field_name.upper()}_TIMEZONE_MISSING"
        )

    return parsed.astimezone(
        timezone.utc
    )


def _validate_sha256_field(
    payload: dict[str, Any],
    field_name: str,
) -> str:
    value = payload[field_name]

    if (
        not isinstance(value, str)
        or not SHA256_PATTERN.fullmatch(value)
    ):
        raise TrustedVerifierError(
            f"GATE_{field_name.upper()}_INVALID"
        )

    return value


def validate_autostart_approval(
    *,
    gate_path: Path = GATE_PATH,
    installed_unit_path: Path = (
        INSTALLED_UNIT_PATH
    ),
    verifier_path: Path = VERIFIER_PATH,
    trusted_root: Path = TRUSTED_PATH_ROOT,
    now: datetime | None = None,
    expected_uid: int = 0,
    expected_gid: int = 0,
) -> TrustedApproval:
    gate_bytes = _secure_read(
        gate_path,
        trusted_root=trusted_root,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=0o644,
        maximum_bytes=MAXIMUM_GATE_BYTES,
        code_prefix="GATE",
    )

    payload = _load_gate_payload(
        gate_bytes
    )

    _expect_exact(
        payload,
        "schema_version",
        EXPECTED_SCHEMA_VERSION,
    )

    _expect_exact(
        payload,
        "approval_label",
        EXPECTED_APPROVAL_LABEL,
    )

    _expect_exact(
        payload,
        "target_unit",
        EXPECTED_TARGET_UNIT,
    )

    _expect_exact(
        payload,
        "production_status",
        "NO_GO",
    )

    _expect_exact(
        payload,
        "safety_scope",
        EXPECTED_SAFETY_SCOPE,
    )

    _expect_exact(
        payload,
        "slack_mode",
        "DRY_RUN",
    )

    _expect_exact(
        payload,
        "production_database_allowed",
        False,
    )

    _expect_exact(
        payload,
        "automatic_start_allowed",
        True,
    )

    expected_unit_sha256 = (
        _validate_sha256_field(
            payload,
            "installed_unit_sha256",
        )
    )

    expected_verifier_sha256 = (
        _validate_sha256_field(
            payload,
            "verifier_sha256",
        )
    )

    unit_bytes = _secure_read(
        installed_unit_path,
        trusted_root=trusted_root,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=0o644,
        maximum_bytes=MAXIMUM_UNIT_BYTES,
        code_prefix="INSTALLED_UNIT",
    )

    verifier_bytes = _secure_read(
        verifier_path,
        trusted_root=trusted_root,
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_mode=0o755,
        maximum_bytes=MAXIMUM_VERIFIER_BYTES,
        code_prefix="VERIFIER",
    )

    if _sha256(unit_bytes) != (
        expected_unit_sha256
    ):
        raise TrustedVerifierError(
            "INSTALLED_UNIT_SHA256_MISMATCH"
        )

    if _sha256(verifier_bytes) != (
        expected_verifier_sha256
    ):
        raise TrustedVerifierError(
            "VERIFIER_SHA256_MISMATCH"
        )

    approved_by = payload[
        "approved_by"
    ]

    if not isinstance(approved_by, str):
        raise TrustedVerifierError(
            "GATE_APPROVED_BY_TYPE_INVALID"
        )

    if (
        not approved_by
        or approved_by != approved_by.strip()
        or len(approved_by) > 128
        or any(
            ord(character) < 32
            or ord(character) == 127
            for character in approved_by
        )
    ):
        raise TrustedVerifierError(
            "GATE_APPROVED_BY_INVALID"
        )

    approved_at = _parse_datetime(
        payload["approved_at"],
        "approved_at",
    )

    expires_at = _parse_datetime(
        payload["expires_at"],
        "expires_at",
    )

    now_value = (
        now
        if now is not None
        else datetime.now(timezone.utc)
    )

    if now_value.tzinfo is None:
        raise TrustedVerifierError(
            "CURRENT_TIME_TIMEZONE_MISSING"
        )

    now_value = now_value.astimezone(
        timezone.utc
    )

    if approved_at > (
        now_value + MAXIMUM_CLOCK_SKEW
    ):
        raise TrustedVerifierError(
            "GATE_APPROVAL_NOT_YET_VALID"
        )

    if expires_at <= approved_at:
        raise TrustedVerifierError(
            "GATE_EXPIRY_ORDER_INVALID"
        )

    if expires_at <= now_value:
        raise TrustedVerifierError(
            "GATE_APPROVAL_EXPIRED"
        )

    if (
        expires_at - approved_at
        > MAXIMUM_VALIDITY
    ):
        raise TrustedVerifierError(
            "GATE_VALIDITY_TOO_LONG"
        )

    return TrustedApproval(
        installed_unit_sha256=(
            expected_unit_sha256
        ),
        verifier_sha256=(
            expected_verifier_sha256
        ),
        approved_by=approved_by,
        approved_at=approved_at,
        expires_at=expires_at,
    )


def _sanitize_environment() -> None:
    os.environ.clear()

    os.environ.update(
        {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
        }
    )


def _print_no_go(code: str) -> None:
    print(
        "AUTOSTART_APPROVAL: "
        f"NOT_APPROVED ({code})"
    )
    print("FINAL_DECISION: NO_GO")
    print("PRODUCTION_STATUS: NO_GO")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the root-managed Slack "
            "readiness autostart approval gate."
        )
    )

    parser.add_argument(
        "--check-autostart",
        action="store_true",
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    parse_args()

    if sys.flags.isolated != 1:
        _print_no_go(
            "PYTHON_NOT_ISOLATED"
        )

        return 3

    _sanitize_environment()

    try:
        validate_autostart_approval()
    except TrustedVerifierError as exc:
        _print_no_go(exc.code)

        return 3

    print("AUTOSTART_APPROVAL: APPROVED")
    print(
        "AUTOSTART_SCOPE: "
        "READINESS_DRY_RUN_ONLY"
    )
    print(
        "FINAL_DECISION: "
        "GO_READINESS_AUTOSTART_ONLY"
    )
    print("PRODUCTION_STATUS: NO_GO")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
