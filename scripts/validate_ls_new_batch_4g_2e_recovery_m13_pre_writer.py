#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import pwd
import socket
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _network_blocked(
    *args: Any,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "NETWORK_OPERATION_BLOCKED_BY_M13_PRE_WRITER"
    )


socket.socket = _network_blocked
socket.create_connection = _network_blocked
socket.getaddrinfo = _network_blocked
socket.gethostbyname = _network_blocked
socket.gethostbyname_ex = _network_blocked


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_writer_credential_"
    "nonsecret_preflight_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_writer_approval.json"
)

M12_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
M13_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)

WRITER_CREDENTIAL = Path(
    "/etc/ai-media-os/credential.env"
)
READONLY_CREDENTIAL = Path(
    "/etc/ai-media-os/wordpress-readonly-category.env"
)

RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_writer_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_writer_report.md"
)

EXPECTED_M12_AUTH_SHA = (
    "7c9662a7a13502e165862e4524278992"
    "28794bce6904a0215c45a5b54ba1142b"
)
EXPECTED_M12_AUTH_DIGEST = (
    "d3ede61a71d75cbbc00a594f0a8d319a"
    "ed0e598bd9c061609a52bed7e96d07c3"
)

REQUIRED_KEYS = (
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def now() -> str:
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


def file_sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON_ROOT_NOT_OBJECT:{path.name}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    field: str,
    expected: str | None = None,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        digest(comparable) == stored,
        f"DIGEST_VERIFICATION_FAILED:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"EXPECTED_DIGEST_MISMATCH:{field}",
        )

    return stored


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_text(
    path: Path,
    value: str,
) -> None:
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def normalized_nonempty(
    raw_value: str,
) -> bool:
    value = raw_value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    return value != ""


def inspect_required_keys(
    path: Path,
) -> tuple[
    dict[str, int],
    dict[str, bool],
]:
    counts = {
        key: 0
        for key in REQUIRED_KEYS
    }
    nonempty = {
        key: False
        for key in REQUIRED_KEYS
    }

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for raw_line in handle:
            require(
                "\x00" not in raw_line,
                "CREDENTIAL_FILE_CONTAINS_NUL",
            )

            line = raw_line.strip()

            if (
                not line
                or line.startswith("#")
            ):
                continue

            if line.startswith("export "):
                line = line[7:].lstrip()

            key, separator, raw_value = (
                line.partition("=")
            )
            key = key.strip()

            if (
                separator == "="
                and key in counts
            ):
                counts[key] += 1

                if normalized_nonempty(
                    raw_value
                ):
                    nonempty[key] = True

    return counts, nonempty


def main() -> int:
    try:
        for output in [
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        require(
            not M13_CONSUMPTION.exists(),
            "M13_CONSUMPTION_ALREADY_EXISTS",
        )

        policy = load(POLICY)
        approval = load(APPROVAL)
        m12_auth = load(M12_AUTH)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            approval["approval_label"]
            == (
                "WORDPRESS_WRITER_CREDENTIAL_"
                "NONSECRET_PREFLIGHT_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M13-PRE-WRITER"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["execution_boundary"][
                "network_connection_allowed"
            ] is False,
            "NETWORK_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "m12_authorization_consumption_allowed"
            ] is False,
            "M12_CONSUMPTION_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "wordpress_access_allowed"
            ] is False,
            "WORDPRESS_ACCESS_BOUNDARY_OPEN",
        )

        require(
            file_sha(M12_AUTH)
            == EXPECTED_M12_AUTH_SHA,
            "M12_AUTHORIZATION_FILE_SHA_MISMATCH",
        )

        verify_digest(
            m12_auth,
            "authorization_digest_sha256",
            EXPECTED_M12_AUTH_DIGEST,
        )

        require(
            m12_auth["authorization_id"]
            == (
                "WORDPRESS_DRAFT_CREATION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "M12_AUTHORIZATION_ID_MISMATCH",
        )
        require(
            m12_auth["single_use"] is True,
            "M12_AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            m12_auth["authorization_consumed"]
            is False,
            "M12_AUTHORIZATION_ALREADY_CONSUMED",
        )
        require(
            m12_auth[
                "authorization_reuse_allowed"
            ] is False,
            "M12_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m12_auth[
                "automatic_retry_allowed"
            ] is False,
            "M12_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m12_auth[
                "automatic_reissue_allowed"
            ] is False,
            "M12_AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            m12_auth[
                "planned_execution_phase_id"
            ] == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M13"
            ),
            "M12_PLANNED_EXECUTION_PHASE_MISMATCH",
        )
        require(
            m12_auth[
                "actual_wordpress_access_allowed"
            ] is False,
            "M12_WORDPRESS_ACCESS_ALREADY_ALLOWED",
        )
        require(
            m12_auth[
                "actual_wordpress_draft_creation_allowed"
            ] is False,
            "M12_DRAFT_CREATION_ALREADY_ALLOWED",
        )

        require(
            WRITER_CREDENTIAL.exists(),
            "WRITER_CREDENTIAL_MISSING",
        )

        before = WRITER_CREDENTIAL.lstat()

        require(
            not stat.S_ISLNK(
                before.st_mode
            ),
            "WRITER_CREDENTIAL_SYMLINK_REJECTED",
        )
        require(
            stat.S_ISREG(
                before.st_mode
            ),
            "WRITER_CREDENTIAL_NOT_REGULAR_FILE",
        )
        require(
            stat.S_IMODE(
                before.st_mode
            ) == 0o600,
            "WRITER_CREDENTIAL_MODE_NOT_0600",
        )
        require(
            before.st_uid == os.geteuid(),
            "WRITER_CREDENTIAL_NOT_OWNED_BY_EXECUTION_USER",
        )

        owner_name = pwd.getpwuid(
            before.st_uid
        ).pw_name

        require(
            owner_name == "deploy",
            "WRITER_CREDENTIAL_OWNER_NOT_DEPLOY",
        )

        counts, nonempty = (
            inspect_required_keys(
                WRITER_CREDENTIAL
            )
        )

        require(
            all(
                counts[key] == 1
                for key in REQUIRED_KEYS
            ),
            "REQUIRED_WRITER_KEY_COUNT_MISMATCH",
        )
        require(
            all(
                nonempty[key]
                for key in REQUIRED_KEYS
            ),
            "REQUIRED_WRITER_VALUE_EMPTY",
        )

        after = WRITER_CREDENTIAL.lstat()

        require(
            (
                before.st_ino,
                before.st_mode,
                before.st_uid,
                before.st_gid,
                before.st_size,
                before.st_mtime_ns,
            )
            == (
                after.st_ino,
                after.st_mode,
                after.st_uid,
                after.st_gid,
                after.st_size,
                after.st_mtime_ns,
            ),
            "WRITER_CREDENTIAL_METADATA_CHANGED",
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M13-PRE-WRITER"
            ),
            "status": (
                "PASS_WORDPRESS_WRITER_CREDENTIAL_"
                "NONSECRET_PREFLIGHT_NO_NETWORK_"
                "NO_WORDPRESS_NO_AUTH_CONSUMPTION"
            ),
            "decision": (
                "WRITER_CREDENTIAL_STRUCTURE_READY_"
                "M12_AUTHORIZATION_REMAINS_UNCONSUMED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "writer_credential_path": (
                "/etc/ai-media-os/credential.env"
            ),
            "writer_credential_exists": True,
            "writer_credential_regular_file": True,
            "writer_credential_symlink": False,
            "writer_credential_mode_0600": True,
            "writer_credential_owner_deploy": True,
            "writer_credential_owned_by_execution_user": True,
            "required_key_count_exactly_one": True,
            "required_values_nonempty": True,
            "required_keys_checked": [
                "WORDPRESS_BASE_URL",
                "WORDPRESS_USERNAME",
                "WORDPRESS_APP_PASSWORD",
            ],
            "credential_file_modified": False,
            "credential_values_output": False,
            "credential_value_lengths_output": False,
            "credential_value_masks_output": False,
            "credential_value_prefixes_output": False,
            "credential_value_suffixes_output": False,
            "credential_value_hashes_output": False,
            "credential_file_hash_computed": False,
            "credential_file_content_output": False,
            "authorization_header_created": False,
            "authorization_header_output": False,
            "environment_export_performed": False,
            "readonly_credential_path": (
                "/etc/ai-media-os/"
                "wordpress-readonly-category.env"
            ),
            "readonly_credential_accessed": False,
            "readonly_credential_modified": False,
            "readonly_credential_used_for_writer": False,
            "m12_authorization_file_sha256": (
                EXPECTED_M12_AUTH_SHA
            ),
            "m12_authorization_digest_sha256": (
                EXPECTED_M12_AUTH_DIGEST
            ),
            "m12_authorization_consumed": False,
            "m12_authorization_reuse_allowed": False,
            "m12_automatic_retry_allowed": False,
            "m12_automatic_reissue_allowed": False,
            "m13_consumption_artifact_exists": False,
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_permission_check_performed": False,
            "wordpress_duplicate_check_performed": False,
            "wordpress_category_check_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "WRITER_CREDENTIAL_STRUCTURE_READY_"
                "M12_AUTHORIZATION_UNCONSUMED"
            ),
            "ready_for_writer_network_preflight_gate": True,
            "ready_for_wordpress_draft_creation": False,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        result = copy.deepcopy(
            result_without_digest
        )
        result[
            "result_digest_sha256"
        ] = digest(result_without_digest)

        write_json(RESULT, result)

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M13-PRE-WRITER

- Status: `{result["status"]}`
- Writer credential exists: `true`
- Regular file: `true`
- Symlink: `false`
- Mode: `0600`
- Owner: `deploy`
- Required key count exactly one: `true`
- Required values nonempty: `true`
- Credential values output: `false`
- Credential file hash computed: `false`
- Credential file modified: `false`
- Environment export performed: `false`
- Read-only credential accessed: `false`
- Read-only credential used for writer: `false`
- M12 authorization consumed: `false`
- Network accessed: `false`
- DNS resolved: `false`
- HTTP requested: `false`
- WordPress accessed: `false`
- WordPress draft created: `false`
- Production status: `NO_GO`
- Ready for writer network preflight gate: `true`
""",
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M13-PRE-WRITER"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_WRITER_"
                        "CREDENTIAL_NONSECRET_PREFLIGHT"
                    ),
                    "error_code": str(exc),
                    "credential_values_output": False,
                    "credential_file_hash_computed": False,
                    "credential_file_modified": False,
                    "environment_export_performed": False,
                    "readonly_credential_accessed": False,
                    "m12_authorization_consumed": False,
                    "network_connection_performed": False,
                    "dns_resolution_performed": False,
                    "http_request_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_draft_created": False,
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
