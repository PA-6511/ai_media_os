#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import getpass
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TARGET = Path(
    "/etc/ai-media-os/credential.env"
)
KEY_NAME = "DMM_AFFILIATE_ID"

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_affiliate_identifier_"
    "secure_registration_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m6_cred1_"
    "secure_registration_approval.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m6_cred1_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m6_cred1_"
    "secure_registration_report.md"
)
PYTEST_OUTPUT = Path(
    "/tmp/"
    "ls_new_batch_4g_2e_recovery_m6_cred1_pytest.txt"
)

COMMITMENT_ITERATIONS = 600000
COMMITMENT_CONTEXT = (
    b"LS-NEW-BATCH-4G-2E-RECOVERY-M6-CRED1"
    b"\x00DMM_AFFILIATE_ID\x00"
)


class RegistrationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RegistrationError(message)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.exists(),
        f"required artifact missing: {path}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def verify_self_digest(
    value: dict[str, Any],
    field: str,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"digest field missing: {field}",
    )
    require(
        digest(comparable) == stored,
        f"digest verification failed: {field}",
    )

    return stored


def strip_optional_quotes(
    value: str,
) -> str:
    value = value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]

    return value


def read_key_values(
    text: str,
    key_name: str = KEY_NAME,
) -> list[str]:
    matches: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        key, separator, raw_value = (
            line.partition("=")
        )

        if separator != "=":
            continue

        if key.strip() != key_name:
            continue

        matches.append(
            strip_optional_quotes(raw_value)
        )

    return matches


def validate_identifier(
    identifier: str,
) -> None:
    require(
        identifier != "",
        "DMM_AFFILIATE_IDENTIFIER_EMPTY",
    )
    require(
        not any(
            character.isspace()
            for character in identifier
        ),
        "DMM_AFFILIATE_IDENTIFIER_WHITESPACE_REJECTED",
    )
    require(
        "://" not in identifier,
        "DMM_AFFILIATE_IDENTIFIER_URL_REJECTED",
    )
    require(
        re.fullmatch(
            r"[A-Za-z0-9]+-[0-9]{3}",
            identifier,
        )
        is not None,
        "DMM_AFFILIATE_IDENTIFIER_FORMAT_INVALID",
    )

    normalized = identifier.casefold()

    forbidden_exact = {
        "aaa-001",
        "test-001",
        "demo-001",
        "dummy-001",
        "sample-001",
        "example-001",
        "placeholder-001",
        "changeme-001",
        "yourid-001",
        "xxxx-001",
        "xxxxx-001",
        "post185-001",
    }

    forbidden_fragments = {
        "dummy",
        "sample",
        "example",
        "placeholder",
        "changeme",
        "yourid",
        "post185",
    }

    require(
        normalized not in forbidden_exact,
        (
            "DMM_AFFILIATE_IDENTIFIER_"
            "EXAMPLE_OR_DUMMY_REJECTED"
        ),
    )
    require(
        not any(
            fragment in normalized
            for fragment in forbidden_fragments
        ),
        (
            "DMM_AFFILIATE_IDENTIFIER_"
            "PLACEHOLDER_FRAGMENT_REJECTED"
        ),
    )


def make_commitment(
    identifier: str,
    salt: bytes,
) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        identifier.encode("utf-8"),
        COMMITMENT_CONTEXT + salt,
        COMMITMENT_ITERATIONS,
    ).hex()


def fsync_directory(
    directory: Path,
) -> None:
    directory_fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def atomic_replace(
    path: Path,
    content: bytes,
    *,
    owner_uid: int,
    owner_gid: int,
) -> None:
    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.m6-cred1.",
            dir=str(path.parent),
        )
    )

    temporary = Path(temporary_name)

    try:
        os.fchmod(
            file_descriptor,
            0o600,
        )
        os.fchown(
            file_descriptor,
            owner_uid,
            owner_gid,
        )

        with os.fdopen(
            file_descriptor,
            "wb",
            closefd=True,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary,
            path,
        )
        fsync_directory(path.parent)

    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass

        try:
            temporary.unlink()
        except FileNotFoundError:
            pass

        raise


def write_owned_json(
    path: Path,
    value: dict[str, Any],
    *,
    owner_uid: int,
    owner_gid: int,
) -> None:
    content = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    file_descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )

    try:
        os.fchown(
            file_descriptor,
            owner_uid,
            owner_gid,
        )

        with os.fdopen(
            file_descriptor,
            "wb",
            closefd=True,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass

        try:
            path.unlink()
        except FileNotFoundError:
            pass

        raise


def write_owned_text(
    path: Path,
    value: str,
    *,
    owner_uid: int,
    owner_gid: int,
) -> None:
    file_descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )

    try:
        os.fchown(
            file_descriptor,
            owner_uid,
            owner_gid,
        )

        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
            closefd=True,
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass

        try:
            path.unlink()
        except FileNotFoundError:
            pass

        raise


def verify_target_metadata(
    *,
    owner_uid: int,
) -> os.stat_result:
    require(
        TARGET.exists(),
        "CREDENTIAL_FILE_MISSING",
    )
    require(
        not TARGET.is_symlink(),
        "CREDENTIAL_FILE_SYMLINK_REJECTED",
    )
    require(
        TARGET.is_file(),
        "CREDENTIAL_FILE_NOT_REGULAR",
    )

    target_stat = TARGET.stat()
    mode = stat.S_IMODE(
        target_stat.st_mode
    )

    require(
        mode == 0o600,
        "CREDENTIAL_FILE_MODE_NOT_0600",
    )
    require(
        target_stat.st_uid == owner_uid,
        "CREDENTIAL_FILE_OWNER_MISMATCH",
    )

    return target_stat


def main() -> int:
    parser = argparse.ArgumentParser(
        add_help=True
    )
    parser.add_argument(
        "--register",
        action="store_true",
    )
    parser.add_argument(
        "--target-uid",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--target-gid",
        required=True,
        type=int,
    )
    arguments = parser.parse_args()

    if not arguments.register:
        print(
            "REGISTRATION_FLAG_REQUIRED",
            file=sys.stderr,
        )
        return 2

    owner_uid = arguments.target_uid
    owner_gid = arguments.target_gid

    original_bytes: bytes | None = None
    credential_replaced = False

    try:
        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        approval_digest = verify_self_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["execution_boundary"][
                "credential_registration_allowed"
            ]
            is True,
            "credential registration not allowed",
        )
        require(
            policy["execution_boundary"][
                "m6_authorization_creation_allowed"
            ]
            is False,
            "M6 authorization boundary must remain closed",
        )
        require(
            policy["execution_boundary"][
                "network_connection_allowed"
            ]
            is False,
            "network boundary must remain closed",
        )

        original_stat = verify_target_metadata(
            owner_uid=owner_uid,
        )
        original_bytes = TARGET.read_bytes()

        try:
            original_text = original_bytes.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise RegistrationError(
                "CREDENTIAL_FILE_NOT_UTF8"
            ) from exc

        existing_values = read_key_values(
            original_text
        )

        require(
            len(existing_values) == 0,
            (
                "DMM_AFFILIATE_IDENTIFIER_KEY_"
                "ALREADY_EXISTS_OR_DUPLICATED"
            ),
        )

        first_input = getpass.getpass(
            "DMM affiliate ID "
            "(hidden input): "
        )
        second_input = getpass.getpass(
            "Re-enter DMM affiliate ID "
            "(hidden confirmation): "
        )

        require(
            first_input == second_input,
            (
                "DMM_AFFILIATE_IDENTIFIER_"
                "CONFIRMATION_MISMATCH"
            ),
        )

        identifier = first_input
        validate_identifier(identifier)

        separator = (
            ""
            if original_text.endswith("\n")
            or original_text == ""
            else "\n"
        )

        updated_text = (
            original_text
            + separator
            + f"{KEY_NAME}={identifier}\n"
        )

        salt = os.urandom(32)
        commitment = make_commitment(
            identifier,
            salt,
        )

        atomic_replace(
            TARGET,
            updated_text.encode("utf-8"),
            owner_uid=owner_uid,
            owner_gid=owner_gid,
        )
        credential_replaced = True

        updated_stat = verify_target_metadata(
            owner_uid=owner_uid,
        )
        updated_text_verified = (
            TARGET.read_text(encoding="utf-8")
        )
        updated_values = read_key_values(
            updated_text_verified
        )

        require(
            len(updated_values) == 1,
            (
                "POST_REGISTRATION_KEY_COUNT_"
                "MUST_BE_ONE"
            ),
        )
        require(
            updated_values[0] == identifier,
            (
                "POST_REGISTRATION_IDENTIFIER_"
                "BINDING_MISMATCH"
            ),
        )

        validate_identifier(
            updated_values[0]
        )

        require(
            make_commitment(
                updated_values[0],
                salt,
            )
            == commitment,
            "COMMITMENT_VERIFICATION_FAILED",
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M6-CRED1"
            ),
            "status": (
                "PASS_DMM_AFFILIATE_IDENTIFIER_"
                "SECURELY_REGISTERED_NO_SECRET_"
                "OUTPUT_NO_NETWORK"
            ),
            "decision": (
                "DMM_AFFILIATE_IDENTIFIER_READY_"
                "FOR_M6_AUTHORIZATION_GATE_RETRY"
            ),
            "approval_label": (
                "DMM_AFFILIATE_IDENTIFIER_"
                "SECURE_REGISTRATION_APPROVED"
            ),
            "credential_target": {
                "path": str(TARGET),
                "key": KEY_NAME,
                "key_count_before": 0,
                "key_count_after": 1,
                "source_is_regular_file": True,
                "source_is_symlink": False,
                "source_mode": (
                    f"{stat.S_IMODE(updated_stat.st_mode):04o}"
                ),
                "source_owner_uid": (
                    updated_stat.st_uid
                ),
                "source_owner_gid": (
                    updated_stat.st_gid
                ),
                "source_owner_matches_target_user": True
            },
            "identifier_validation": {
                "format_validated": True,
                "empty_rejected": True,
                "whitespace_rejected": True,
                "url_rejected": True,
                "dummy_or_placeholder_rejected": True,
                "confirmation_match_verified": True,
                "identifier_value_output": False,
                "identifier_value_persisted_in_evidence": False
            },
            "identifier_commitment": {
                "algorithm": (
                    "PBKDF2-HMAC-SHA256"
                ),
                "iterations": (
                    COMMITMENT_ITERATIONS
                ),
                "salt_hex": salt.hex(),
                "commitment_hex": commitment,
                "identifier_value_present": False
            },
            "policy_path": str(
                POLICY.relative_to(ROOT)
            ),
            "policy_file_sha256": (
                file_sha256(POLICY)
            ),
            "approval_path": str(
                APPROVAL.relative_to(ROOT)
            ),
            "approval_digest_sha256": (
                approval_digest
            ),
            "atomic_replacement_performed": True,
            "original_credentials_preserved": True,
            "m6_authorization_created": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "fresh_payload_created": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_IDENTIFIER_REGISTERED_"
                "AWAITING_M6_AUTHORIZATION_GATE"
            ),
            "ready_for_m6_authorization_gate_retry": True,
            "ready_for_final_affiliate_link_generation": False,
            "completed_at_utc": utc_now(),
            "pre_registration_test_result": (
                PYTEST_OUTPUT.read_text(
                    encoding="utf-8"
                ).strip()
                if PYTEST_OUTPUT.exists()
                else "NOT_RECORDED"
            )
        }

        result = copy.deepcopy(
            result_without_digest
        )
        result[
            "result_digest_sha256"
        ] = digest(result_without_digest)

        write_owned_json(
            RESULT,
            result,
            owner_uid=owner_uid,
            owner_gid=owner_gid,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M6-CRED1

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Credential path: `{TARGET}`
- Credential key: `{KEY_NAME}`
- Key count before: `0`
- Key count after: `1`
- Mode: `0600`
- Owner UID: `{updated_stat.st_uid}`
- Hidden input used: `true`
- Confirmation input used: `true`
- Identifier format validated: `true`
- Identifier value output: `false`
- Identifier value persisted in evidence: `false`
- Atomic replacement: `true`
- M6 authorization created: `false`
- Network accessed: `false`
- Final affiliate link generated: `false`
- Article modified: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for M6 authorization gate retry: `true`
"""

        write_owned_text(
            REPORT,
            report,
            owner_uid=owner_uid,
            owner_gid=owner_gid,
        )

        del first_input
        del second_input
        del identifier
        del updated_values

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except Exception as exc:
        rollback_succeeded = False

        if (
            credential_replaced
            and original_bytes is not None
        ):
            try:
                atomic_replace(
                    TARGET,
                    original_bytes,
                    owner_uid=owner_uid,
                    owner_gid=owner_gid,
                )
                rollback_succeeded = True
            except Exception:
                rollback_succeeded = False

        for path in [RESULT, REPORT]:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

        error_code = (
            str(exc)
            if isinstance(
                exc,
                RegistrationError,
            )
            else (
                "UNEXPECTED_SECURE_"
                "REGISTRATION_FAILURE"
            )
        )

        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M6-CRED1"
                    ),
                    "status": (
                        "BLOCKED_DMM_AFFILIATE_"
                        "IDENTIFIER_SECURE_REGISTRATION"
                    ),
                    "error": error_code,
                    "credential_replacement_attempted": (
                        credential_replaced
                    ),
                    "credential_rollback_succeeded": (
                        rollback_succeeded
                    ),
                    "identifier_value_output": False,
                    "identifier_value_persisted_in_evidence": False,
                    "m6_authorization_created": False,
                    "network_connection_performed": False,
                    "final_affiliate_link_generated": False,
                    "article_modified": False,
                    "wordpress_access_performed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
