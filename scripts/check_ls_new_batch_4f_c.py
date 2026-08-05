#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import errno
import grp
import hashlib
import json
import os
import pwd
import stat
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_production_credential_nonsecret_check_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_credential_nonsecret_check_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_credential_nonsecret_check_result.example.json"
)

RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4f_c_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4f_c_production_credential_nonsecret_check_report.md"
)


class ValidationError(RuntimeError):
    pass


class BlockedCheck(RuntimeError):
    def __init__(
        self,
        *,
        status: str,
        reason: str,
        evidence: dict[str, Any],
    ) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.evidence = evidence


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"required file missing: {path}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise ValidationError(
            f"JSON root must be an object: {path}"
        )

    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return str(resolved)


def resolve_repo_path(value: str) -> Path:
    path = Path(value)

    if path.is_absolute():
        return path

    return ROOT / path


def base_evidence(
    credential_path: Path,
) -> dict[str, Any]:
    return {
        "credential_file_path": str(credential_path),
        "exists": False,
        "lstat_performed": False,
        "regular_file": False,
        "symbolic_link": False,
        "owner_name": None,
        "group_name": None,
        "owner_matches": False,
        "group_matches": False,
        "mode_octal": None,
        "mode_matches": False,
        "content_opened": False,
        "key_names_parsed": False,
        "required_keys_present": False,
        "present_key_names": [],
        "missing_key_names": [],
        "unknown_key_names": [],
        "duplicate_key_names": [],
        "empty_value_key_names": [],
        "credential_values_output": False,
        "credential_value_lengths_output": False,
        "credential_value_hashes_output": False,
        "raw_content_output": False,
        "environment_variables_read": False,
        "environment_variables_exported": False,
        "network_operations_performed": False,
        "wordpress_access_performed": False,
    }


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-4F-C",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_PRODUCTION_CREDENTIAL_NONSECRET_CHECK_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("check_mode")
        == "ACTUAL_PRODUCTION_FILE_NONSECRET_CHECK",
        "check mode mismatch",
    )
    checks.append("nonsecret_check_mode")

    secret = policy.get("secret_handling", {})

    for field in [
        "credential_values_loaded_into_environment_allowed",
        "credential_values_retained_after_line_parse_allowed",
        "credential_values_output_allowed",
        "credential_value_lengths_output_allowed",
        "credential_value_hashes_output_allowed",
        "credential_value_prefixes_output_allowed",
        "credential_value_suffixes_output_allowed",
        "raw_file_content_output_allowed",
        "secret_exception_text_allowed",
    ]:
        require(
            secret.get(field) is False,
            f"{field} must remain false",
        )

    checks.append("secret_handling_boundary")

    boundary = policy.get("execution_boundary", {})

    require(
        boundary.get("credential_metadata_read_allowed")
        is True,
        "credential metadata read must be allowed",
    )
    require(
        boundary.get("credential_structure_read_allowed")
        is True,
        "credential structure read must be allowed",
    )

    for field in [
        "credential_value_output_allowed",
        "environment_variable_read_allowed",
        "environment_variable_export_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_database_read_allowed",
        "wordpress_database_write_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "external_api_call_allowed",
        "execution_approval_issued",
        "approval_token_generation_allowed",
        "execution_allowed",
    ]:
        require(
            boundary.get(field) is False,
            f"{field} must remain false",
        )

    require(
        boundary.get("production_status") == "NO_GO",
        "production status must remain NO_GO",
    )
    require(
        boundary.get("safety_state")
        == "NONSECRET_CREDENTIAL_FILE_CHECK_ONLY",
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source_design(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    source_path_value = request.get(
        "source_design_package_path"
    )

    require(
        isinstance(source_path_value, str),
        "source design package path must be a string",
    )

    source_path = resolve_repo_path(source_path_value)
    source = load_json(source_path)

    require(
        source.get("phase_id")
        == policy.get("source_phase_id"),
        "source phase mismatch",
    )
    require(
        source.get("design_mode")
        == "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY",
        "source design mode mismatch",
    )

    expected_digest = source.get(
        "design_package_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source design digest is invalid",
    )
    require(
        request.get(
            "source_design_package_digest_sha256"
        )
        == expected_digest,
        "request source digest mismatch",
    )

    source_without_digest = copy.deepcopy(source)
    source_without_digest.pop(
        "design_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_digest,
        "source design package digest verification failed",
    )
    require(
        source.get("production_credential_path_touched")
        is False,
        "source design must not have touched production path",
    )

    return [
        "source_phase_identity",
        "source_design_digest_verified",
        "source_validator_design_complete",
        "source_production_path_untouched",
    ]


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> Path:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4F-C",
        "request phase_id mismatch",
    )
    require(
        request.get("check_mode")
        == "ACTUAL_PRODUCTION_FILE_NONSECRET_CHECK",
        "request check mode mismatch",
    )
    require(
        request.get("explicit_nonsecret_check_authorized")
        is True,
        "explicit non-secret check authorization is required",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    contract = policy["credential_contract"]

    require(
        request.get("credential_file_path")
        == contract["credential_file_path"],
        "credential file path mismatch",
    )

    expected_checks = [
        "EXISTS",
        "LSTAT",
        "REGULAR_FILE",
        "NOT_SYMBOLIC_LINK",
        "OWNER",
        "GROUP",
        "MODE",
        "REQUIRED_KEY_NAMES",
        "DUPLICATE_KEY_NAMES",
        "UNKNOWN_KEY_NAMES",
        "NONEMPTY_VALUE_STATUS",
    ]

    require(
        request.get("allowed_checks") == expected_checks,
        "allowed checks mismatch",
    )

    for field in [
        "credential_value_output_requested",
        "credential_value_length_output_requested",
        "credential_value_hash_output_requested",
        "raw_content_output_requested",
        "environment_variable_read_requested",
        "environment_variable_export_requested",
        "network_access_requested",
        "wordpress_access_requested",
        "execution_approval_issued",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    require(
        request.get("approval_token") is None,
        "approval token must remain null",
    )

    return Path(contract["credential_file_path"])


def safe_owner_name(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return f"UID_{uid}"


def safe_group_name(gid: int) -> str:
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return f"GID_{gid}"


def parse_key_structure_from_fd(
    fd: int,
    *,
    required_keys: set[str],
) -> dict[str, Any]:
    parsed_keys: set[str] = set()
    duplicate_keys: set[str] = set()
    unknown_keys: set[str] = set()
    empty_value_keys: set[str] = set()
    invalid_line_numbers: list[int] = []

    with os.fdopen(
        fd,
        mode="r",
        encoding="utf-8",
        errors="strict",
        closefd=True,
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            stripped = raw_line.strip()

            if stripped == "" or stripped.startswith("#"):
                continue

            if stripped.startswith("export "):
                invalid_line_numbers.append(line_number)
                continue

            if "=" not in raw_line:
                invalid_line_numbers.append(line_number)
                continue

            key_part, value_part = raw_line.split("=", 1)
            key = key_part.strip()

            if key == "":
                invalid_line_numbers.append(line_number)
                continue

            value_is_empty = value_part.strip() == ""

            if key in parsed_keys:
                duplicate_keys.add(key)
            else:
                parsed_keys.add(key)

            if key not in required_keys:
                unknown_keys.add(key)

            if value_is_empty:
                empty_value_keys.add(key)

            # Value is deliberately not retained after this line.

    return {
        "present_key_names": sorted(parsed_keys),
        "missing_key_names": sorted(
            required_keys - parsed_keys
        ),
        "unknown_key_names": sorted(unknown_keys),
        "duplicate_key_names": sorted(duplicate_keys),
        "empty_value_key_names": sorted(empty_value_keys),
        "invalid_line_numbers": invalid_line_numbers,
    }


def perform_nonsecret_check(
    credential_path: Path,
    policy: dict[str, Any],
) -> dict[str, Any]:
    evidence = base_evidence(credential_path)
    failures = policy["failure_states"]
    contract = policy["credential_contract"]

    try:
        file_stat = os.lstat(credential_path)
    except FileNotFoundError:
        raise BlockedCheck(
            status=failures["missing_file"],
            reason=(
                "Production credential file does not exist. "
                "No credential content was read."
            ),
            evidence=evidence,
        )
    except OSError as exc:
        raise BlockedCheck(
            status="BLOCKED_PRODUCTION_CREDENTIAL_LSTAT_FAILED",
            reason=(
                "Production credential lstat failed without "
                "reading credential content."
            ),
            evidence=evidence,
        ) from exc

    evidence["exists"] = True
    evidence["lstat_performed"] = True
    evidence["symbolic_link"] = stat.S_ISLNK(
        file_stat.st_mode
    )

    if evidence["symbolic_link"]:
        raise BlockedCheck(
            status=failures["symbolic_link"],
            reason=(
                "Production credential path is a symbolic link."
            ),
            evidence=evidence,
        )

    evidence["regular_file"] = stat.S_ISREG(
        file_stat.st_mode
    )

    if not evidence["regular_file"]:
        raise BlockedCheck(
            status=failures["not_regular_file"],
            reason=(
                "Production credential path is not a regular file."
            ),
            evidence=evidence,
        )

    evidence["owner_name"] = safe_owner_name(
        file_stat.st_uid
    )
    evidence["group_name"] = safe_group_name(
        file_stat.st_gid
    )
    evidence["owner_matches"] = (
        evidence["owner_name"] == contract["expected_owner"]
    )
    evidence["group_matches"] = (
        evidence["group_name"] == contract["expected_group"]
    )

    mode = stat.S_IMODE(file_stat.st_mode)
    evidence["mode_octal"] = f"{mode:04o}"
    evidence["mode_matches"] = (
        evidence["mode_octal"]
        == contract["required_mode_octal"]
    )

    if not evidence["owner_matches"]:
        raise BlockedCheck(
            status=failures["owner_mismatch"],
            reason="Production credential owner mismatch.",
            evidence=evidence,
        )

    if not evidence["group_matches"]:
        raise BlockedCheck(
            status=failures["group_mismatch"],
            reason="Production credential group mismatch.",
            evidence=evidence,
        )

    if not evidence["mode_matches"]:
        raise BlockedCheck(
            status=failures["mode_mismatch"],
            reason=(
                "Production credential mode mismatch. "
                "Required mode is 0600."
            ),
            evidence=evidence,
        )

    open_flags = os.O_RDONLY

    if hasattr(os, "O_NOFOLLOW"):
        open_flags |= os.O_NOFOLLOW

    if hasattr(os, "O_CLOEXEC"):
        open_flags |= os.O_CLOEXEC

    try:
        fd = os.open(credential_path, open_flags)
    except OSError as exc:
        status = (
            failures["symbolic_link"]
            if exc.errno == errno.ELOOP
            else "BLOCKED_PRODUCTION_CREDENTIAL_OPEN_FAILED"
        )

        raise BlockedCheck(
            status=status,
            reason=(
                "Production credential file could not be opened "
                "for sanitized structure validation."
            ),
            evidence=evidence,
        ) from exc

    evidence["content_opened"] = True

    try:
        opened_stat = os.fstat(fd)

        if (
            opened_stat.st_dev != file_stat.st_dev
            or opened_stat.st_ino != file_stat.st_ino
        ):
            os.close(fd)
            raise BlockedCheck(
                status=(
                    "BLOCKED_PRODUCTION_CREDENTIAL_"
                    "FILE_CHANGED_DURING_CHECK"
                ),
                reason=(
                    "Production credential file changed between "
                    "lstat and open."
                ),
                evidence=evidence,
            )

        structure = parse_key_structure_from_fd(
            fd,
            required_keys=set(contract["required_keys"]),
        )
        fd = -1

    finally:
        if fd >= 0:
            os.close(fd)

    evidence["key_names_parsed"] = True
    evidence.update(
        {
            "present_key_names": structure[
                "present_key_names"
            ],
            "missing_key_names": structure[
                "missing_key_names"
            ],
            "unknown_key_names": structure[
                "unknown_key_names"
            ],
            "duplicate_key_names": structure[
                "duplicate_key_names"
            ],
            "empty_value_key_names": structure[
                "empty_value_key_names"
            ],
        }
    )

    if structure["invalid_line_numbers"]:
        raise BlockedCheck(
            status=failures["invalid_line"],
            reason=(
                "Production credential file contains invalid "
                "non-secret line structure."
            ),
            evidence=evidence,
        )

    if evidence["missing_key_names"]:
        raise BlockedCheck(
            status=failures["missing_keys"],
            reason=(
                "Required production credential key names "
                "are missing."
            ),
            evidence=evidence,
        )

    if evidence["unknown_key_names"]:
        raise BlockedCheck(
            status=failures["unknown_keys"],
            reason=(
                "Unknown production credential key names "
                "were detected."
            ),
            evidence=evidence,
        )

    if evidence["duplicate_key_names"]:
        raise BlockedCheck(
            status=failures["duplicate_keys"],
            reason=(
                "Duplicate production credential key names "
                "were detected."
            ),
            evidence=evidence,
        )

    if evidence["empty_value_key_names"]:
        raise BlockedCheck(
            status=failures["empty_values"],
            reason=(
                "One or more production credential values "
                "are empty."
            ),
            evidence=evidence,
        )

    evidence["required_keys_present"] = True

    return evidence


def build_success_package(
    evidence: dict[str, Any],
    policy: dict[str, Any],
    source_checks: list[str],
) -> dict[str, Any]:
    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4F-C",
        "policy_id": policy["policy_id"],
        "check_package_id": (
            "wp-production-credential-nonsecret-check"
        ),
        "check_mode": (
            "ACTUAL_PRODUCTION_FILE_NONSECRET_CHECK"
        ),
        "status": (
            "PASS_PRODUCTION_CREDENTIAL_"
            "NONSECRET_CHECK"
        ),
        "decision": (
            "PRODUCTION_CREDENTIAL_STRUCTURE_READY_"
            "NO_SECRET_OUTPUT"
        ),
        "sanitized_evidence": evidence,
        "verification_state": {
            "production_credential_presence_verified": True,
            "production_credential_metadata_verified": True,
            "production_credential_structure_verified": True,
            "credential_values_verified_nonempty_only": True,
            "credential_values_loaded_into_environment": False,
            "credential_values_output": False,
            "production_read_only_lookup_ready": False
        },
        "execution_boundary": {
            "credential_value_output_allowed": False,
            "environment_variable_read_allowed": False,
            "environment_variable_export_allowed": False,
            "dns_resolution_allowed": False,
            "network_connection_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_category_lookup_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "external_api_call_allowed": False,
            "execution_approval_issued": False,
            "approval_token_present": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "NONSECRET_CREDENTIAL_FILE_CHECK_ONLY"
            )
        },
        "verified_checks": source_checks,
    }

    package = copy.deepcopy(package_without_digest)
    package["sanitized_check_digest_sha256"] = (
        canonical_digest(package_without_digest)
    )

    return package


def build_result(
    package: dict[str, Any],
    *,
    request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    evidence = package["sanitized_evidence"]

    return {
        "phase_id": "LS-NEW-BATCH-4F-C",
        "status": package["status"],
        "decision": package["decision"],
        "policy_id": package["policy_id"],
        "check_package_id": package["check_package_id"],
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "credential_file_path": evidence[
            "credential_file_path"
        ],
        "exists": evidence["exists"],
        "lstat_performed": evidence["lstat_performed"],
        "regular_file": evidence["regular_file"],
        "symbolic_link": evidence["symbolic_link"],
        "owner_name": evidence["owner_name"],
        "group_name": evidence["group_name"],
        "owner_matches": evidence["owner_matches"],
        "group_matches": evidence["group_matches"],
        "mode_octal": evidence["mode_octal"],
        "mode_matches": evidence["mode_matches"],
        "content_opened": evidence["content_opened"],
        "key_names_parsed": evidence["key_names_parsed"],
        "required_keys_present": evidence[
            "required_keys_present"
        ],
        "present_key_names": evidence[
            "present_key_names"
        ],
        "missing_key_count": len(
            evidence["missing_key_names"]
        ),
        "unknown_key_count": len(
            evidence["unknown_key_names"]
        ),
        "duplicate_key_count": len(
            evidence["duplicate_key_names"]
        ),
        "empty_value_key_count": len(
            evidence["empty_value_key_names"]
        ),
        "credential_values_output": False,
        "credential_value_lengths_output": False,
        "credential_value_hashes_output": False,
        "raw_content_output": False,
        "environment_variables_read": False,
        "environment_variables_exported": False,
        "network_operations_performed": False,
        "wordpress_access_performed": False,
        "production_credential_presence_verified": True,
        "production_credential_metadata_verified": True,
        "production_credential_structure_verified": True,
        "sanitized_check_digest_sha256": package[
            "sanitized_check_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity",
                "explicit_nonsecret_check_authorization",
                "production_file_exists",
                "lstat_completed",
                "symbolic_link_rejected",
                "regular_file_verified",
                "owner_verified",
                "group_verified",
                "mode_0600_verified",
                "safe_open_nofollow",
                "file_identity_rechecked_after_open",
                "required_key_names_verified",
                "duplicate_key_names_absent",
                "unknown_key_names_absent",
                "empty_values_absent",
                "credential_values_not_retained",
                "secret_output_absent",
                "environment_export_absent",
                "network_access_absent",
                "wordpress_access_absent",
                "sanitized_check_digest_generated",
                "execution_gate_closed",
            ]
        ),
        "credential_value_output_allowed": False,
        "environment_variable_read_allowed": False,
        "environment_variable_export_allowed": False,
        "dns_resolution_allowed": False,
        "network_connection_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "NONSECRET_CREDENTIAL_FILE_CHECK_ONLY",
        "ready_for_ls_new_batch_4g": True,
        "ready_for_read_only_lookup_preflight": True,
        "ready_for_production_read_only_lookup": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_blocked_result(
    blocked: BlockedCheck,
    *,
    request_path: Path,
) -> dict[str, Any]:
    evidence = blocked.evidence

    return {
        "phase_id": "LS-NEW-BATCH-4F-C",
        "status": blocked.status,
        "decision": "PRODUCTION_CREDENTIAL_CHECK_BLOCKED",
        "reason": blocked.reason,
        "request_path": display_path(request_path),
        "credential_file_path": evidence[
            "credential_file_path"
        ],
        "exists": evidence["exists"],
        "lstat_performed": evidence["lstat_performed"],
        "regular_file": evidence["regular_file"],
        "symbolic_link": evidence["symbolic_link"],
        "owner_name": evidence["owner_name"],
        "group_name": evidence["group_name"],
        "owner_matches": evidence["owner_matches"],
        "group_matches": evidence["group_matches"],
        "mode_octal": evidence["mode_octal"],
        "mode_matches": evidence["mode_matches"],
        "content_opened": evidence["content_opened"],
        "key_names_parsed": evidence["key_names_parsed"],
        "present_key_names": evidence[
            "present_key_names"
        ],
        "missing_key_names": evidence[
            "missing_key_names"
        ],
        "unknown_key_names": evidence[
            "unknown_key_names"
        ],
        "duplicate_key_names": evidence[
            "duplicate_key_names"
        ],
        "empty_value_key_names": evidence[
            "empty_value_key_names"
        ],
        "credential_values_output": False,
        "credential_value_lengths_output": False,
        "credential_value_hashes_output": False,
        "raw_content_output": False,
        "environment_variables_read": False,
        "network_operations_performed": False,
        "wordpress_access_performed": False,
        "production_credential_presence_verified": False,
        "production_credential_metadata_verified": False,
        "production_credential_structure_verified": False,
        "credential_value_output_allowed": False,
        "environment_variable_read_allowed": False,
        "dns_resolution_allowed": False,
        "network_connection_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "NONSECRET_CREDENTIAL_FILE_CHECK_ONLY",
        "ready_for_ls_new_batch_4g": False,
        "ready_for_read_only_lookup_preflight": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    return f"""# LS-NEW-BATCH-4F-C Production Credential Non-Secret Check

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Credential file: `{result["credential_file_path"]}`

## File Check

- Exists: `{str(result["exists"]).lower()}`
- lstat performed: `{str(result["lstat_performed"]).lower()}`
- Regular file: `{str(result["regular_file"]).lower()}`
- Symbolic link: `{str(result["symbolic_link"]).lower()}`
- Owner: `{result["owner_name"]}`
- Group: `{result["group_name"]}`
- Owner matches: `{str(result["owner_matches"]).lower()}`
- Group matches: `{str(result["group_matches"]).lower()}`
- Mode: `{result["mode_octal"]}`
- Mode matches: `{str(result["mode_matches"]).lower()}`

## Structure Check

- Content opened: `{str(result["content_opened"]).lower()}`
- Key names parsed: `{str(result["key_names_parsed"]).lower()}`
- Required keys present: `{str(result.get("required_keys_present", False)).lower()}`

## Secret Handling

- Credential values output: `false`
- Value lengths output: `false`
- Value hashes output: `false`
- Raw content output: `false`
- Environment variables read: `false`

## External Access

- Network operations performed: `false`
- WordPress access performed: `false`

## Safety Boundary

- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress write allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `NONSECRET_CREDENTIAL_FILE_CHECK_ONLY`
"""


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--request",
        type=Path,
        default=DEFAULT_REQUEST_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    request_path = resolve_path(args.request)
    output_path = resolve_path(args.output)

    try:
        policy = load_json(POLICY_PATH)
        request = load_json(request_path)

        policy_checks = validate_policy(policy)
        source_checks = verify_source_design(
            request,
            policy,
        )
        credential_path = validate_request(
            request,
            policy,
        )

        evidence = perform_nonsecret_check(
            credential_path,
            policy,
        )

        package = build_success_package(
            evidence,
            policy,
            source_checks,
        )
        result = build_result(
            package,
            request_path=request_path,
            output_path=output_path,
            policy_checks=policy_checks,
        )

        write_json(output_path, package)
        write_json(RESULT_PATH, result)
        write_text(REPORT_PATH, build_report(result))

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except BlockedCheck as blocked:
        result = build_blocked_result(
            blocked,
            request_path=request_path,
        )

        write_json(RESULT_PATH, result)
        write_text(REPORT_PATH, build_report(result))

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 3

    except ValidationError as exc:
        result = {
            "phase_id": "LS-NEW-BATCH-4F-C",
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "credential_values_output": False,
            "environment_variables_read": False,
            "network_operations_performed": False,
            "wordpress_access_performed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_allowed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
        }

        write_json(RESULT_PATH, result)

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
