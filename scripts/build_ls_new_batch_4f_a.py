#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_credential_fixture_validator_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_credential_fixture_validation_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_credential_fixture_validation_result.example.json"
)

RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4f_a_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4f_a_credential_fixture_validator_report.md"
)


class ValidationError(RuntimeError):
    pass


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


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-4F-A",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_CREDENTIAL_FIXTURE_VALIDATOR_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    scope = policy.get("validation_scope", {})

    require(
        scope.get("current_mode")
        == "LOCAL_DUMMY_FIXTURE_ONLY",
        "validation mode mismatch",
    )
    require(
        scope.get("production_path_access_allowed") is False,
        "production path access must remain blocked",
    )
    checks.append("fixture_only_scope")

    secret = policy.get("secret_handling", {})

    for field in [
        "value_output_allowed",
        "value_length_output_allowed",
        "value_hash_output_allowed",
        "value_prefix_output_allowed",
        "value_suffix_output_allowed",
        "environment_export_allowed",
        "environment_variable_read_allowed",
    ]:
        require(
            secret.get(field) is False,
            f"{field} must remain false",
        )

    checks.append("secret_output_boundary")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "production_credential_metadata_read_allowed",
        "production_credential_content_read_allowed",
        "credential_value_output_allowed",
        "environment_variable_read_allowed",
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
        == "DESIGN_ONLY_DUMMY_FIXTURE_READ",
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source_preflight(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    source_path_value = request.get(
        "source_preflight_package_path"
    )

    require(
        isinstance(source_path_value, str),
        "source_preflight_package_path must be a string",
    )

    source_path = resolve_repo_path(source_path_value)
    source = load_json(source_path)

    require(
        source.get("phase_id")
        == policy.get("source_phase_id"),
        "source phase mismatch",
    )

    expected_digest = source.get(
        "preflight_package_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source preflight digest is invalid",
    )
    require(
        request.get(
            "source_preflight_package_digest_sha256"
        )
        == expected_digest,
        "request source digest mismatch",
    )

    source_without_digest = copy.deepcopy(source)
    source_without_digest.pop(
        "preflight_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_digest,
        "source preflight package digest verification failed",
    )

    gate = source.get("preexecution_gate", {})

    require(
        gate.get("execution_allowed") is False,
        "source execution gate must remain closed",
    )

    return source, [
        "source_phase_identity",
        "source_preflight_digest_verified",
        "source_execution_gate_closed",
    ]


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> Path:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4F-A",
        "request phase_id mismatch",
    )
    require(
        request.get("validation_mode")
        == "LOCAL_DUMMY_FIXTURE_ONLY",
        "request validation mode mismatch",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    for field in [
        "production_path_access_requested",
        "environment_variable_read_requested",
        "network_access_requested",
        "wordpress_access_requested",
        "secret_output_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    fixture_path_value = request.get("fixture_path")

    require(
        isinstance(fixture_path_value, str),
        "fixture_path must be a string",
    )

    fixture_path = resolve_repo_path(fixture_path_value)
    resolved_fixture = fixture_path.resolve()
    allowed_root = (
        ROOT
        / policy["validation_scope"][
            "allowed_fixture_root"
        ]
    ).resolve()
    production_path = Path(
        policy["validation_scope"][
            "production_credential_path"
        ]
    ).resolve()

    require(
        resolved_fixture != production_path,
        "production credential path is forbidden",
    )
    require(
        resolved_fixture.is_relative_to(allowed_root),
        "fixture path escapes allowed fixture root",
    )

    return resolved_fixture


def parse_fixture(
    fixture_path: Path,
    policy: dict[str, Any],
) -> dict[str, Any]:
    rules = policy["file_rules"]

    require(
        fixture_path.exists(),
        "fixture file does not exist",
    )
    require(
        not fixture_path.is_symlink(),
        "symbolic-link fixture is forbidden",
    )
    require(
        fixture_path.is_file(),
        "fixture must be a regular file",
    )

    file_stat = fixture_path.stat()
    mode = stat.S_IMODE(file_stat.st_mode)
    required_mode = int(
        rules["required_mode_octal"],
        8,
    )

    require(
        mode == required_mode,
        "fixture mode must be 0600",
    )

    if rules["current_user_owner_required"]:
        require(
            file_stat.st_uid == os.getuid(),
            "fixture owner must be current user",
        )

    raw_lines = fixture_path.read_text(
        encoding="utf-8"
    ).splitlines()

    parsed: dict[str, str] = {}
    duplicate_keys: list[str] = []
    invalid_lines: list[int] = []

    for line_number, raw_line in enumerate(
        raw_lines,
        start=1,
    ):
        stripped = raw_line.strip()

        if stripped == "":
            continue

        if stripped.startswith("#"):
            continue

        require(
            not stripped.startswith("export "),
            f"export prefix is forbidden at line {line_number}",
        )

        if "=" not in raw_line:
            invalid_lines.append(line_number)
            continue

        key, value = raw_line.split("=", 1)
        key = key.strip()
        value = value.strip()

        require(
            key != "",
            f"blank key at line {line_number}",
        )

        if key in parsed:
            duplicate_keys.append(key)
            continue

        parsed[key] = value

    require(
        not invalid_lines,
        f"invalid fixture lines: {invalid_lines}",
    )
    require(
        not duplicate_keys,
        f"duplicate fixture keys: {sorted(set(duplicate_keys))}",
    )

    required_keys = set(policy["required_keys"])
    actual_keys = set(parsed)

    missing_keys = sorted(required_keys - actual_keys)
    unknown_keys = sorted(actual_keys - required_keys)
    empty_value_keys = sorted(
        key
        for key, value in parsed.items()
        if value == ""
    )

    require(
        not missing_keys,
        f"required fixture keys missing: {missing_keys}",
    )
    require(
        not unknown_keys,
        f"unknown fixture keys detected: {unknown_keys}",
    )
    require(
        not empty_value_keys,
        f"empty fixture values detected: {empty_value_keys}",
    )

    return {
        "exists": True,
        "regular_file": True,
        "symbolic_link": False,
        "mode_octal": f"{mode:04o}",
        "mode_valid": True,
        "current_user_owner": (
            file_stat.st_uid == os.getuid()
        ),
        "required_keys": sorted(required_keys),
        "present_keys": sorted(actual_keys),
        "missing_keys": [],
        "unknown_keys": [],
        "duplicate_keys": [],
        "empty_value_keys": [],
        "values_output": False,
        "value_lengths_output": False,
        "value_hashes_output": False,
        "environment_exported": False,
    }


def build_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    _, source_checks = verify_source_preflight(
        request,
        policy,
    )
    fixture_path = validate_request(
        request,
        policy,
    )
    fixture_validation = parse_fixture(
        fixture_path,
        policy,
    )

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4F-A",
        "policy_id": policy["policy_id"],
        "validation_package_id": (
            "wp-readonly-credential-fixture-baseline"
        ),
        "validation_mode": (
            "LOCAL_DUMMY_FIXTURE_ONLY"
        ),
        "fixture_path": display_path(fixture_path),
        "production_credential_path_touched": False,
        "production_credential_metadata_read": False,
        "production_credential_content_read": False,
        "fixture_validation": fixture_validation,
        "credential_structure_state": (
            "VALID_DUMMY_FIXTURE"
        ),
        "execution_boundary": {
            "production_credential_metadata_read_allowed": False,
            "production_credential_content_read_allowed": False,
            "credential_value_output_allowed": False,
            "environment_variable_read_allowed": False,
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
                "DESIGN_ONLY_DUMMY_FIXTURE_READ"
            ),
        },
        "verified_checks": source_checks,
    }

    package = copy.deepcopy(package_without_digest)
    package["sanitized_result_digest_sha256"] = (
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
    validation = package["fixture_validation"]

    return {
        "phase_id": "LS-NEW-BATCH-4F-A",
        "status": (
            "PASS_CREDENTIAL_PRESENCE_FIXTURE_BASELINE"
        ),
        "decision": (
            "READ_ONLY_CREDENTIAL_STRUCTURE_FIXED"
        ),
        "policy_id": package["policy_id"],
        "validation_package_id": package[
            "validation_package_id"
        ],
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "validation_mode": package["validation_mode"],
        "fixture_path": package["fixture_path"],
        "fixture_exists": validation["exists"],
        "fixture_regular_file": validation[
            "regular_file"
        ],
        "fixture_mode_octal": validation[
            "mode_octal"
        ],
        "fixture_mode_valid": validation[
            "mode_valid"
        ],
        "current_user_owner": validation[
            "current_user_owner"
        ],
        "required_keys_present": (
            validation["present_keys"]
            == validation["required_keys"]
        ),
        "missing_key_count": 0,
        "unknown_key_count": 0,
        "duplicate_key_count": 0,
        "empty_value_key_count": 0,
        "credential_values_output": False,
        "value_lengths_output": False,
        "value_hashes_output": False,
        "production_credential_path_touched": False,
        "environment_variables_read": False,
        "network_operations_performed": False,
        "wordpress_access_performed": False,
        "sanitized_result_digest_sha256": package[
            "sanitized_result_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity",
                "fixture_root_confinement",
                "production_path_rejection",
                "file_exists_check",
                "regular_file_check",
                "symbolic_link_rejection",
                "owner_check",
                "mode_0600_check",
                "required_key_check",
                "duplicate_key_check",
                "unknown_key_check",
                "empty_value_check",
                "secret_output_absence",
                "environment_export_absence",
                "sanitized_result_digest_generation",
                "execution_gate_closed",
            ]
        ),
        "production_credential_metadata_read_allowed": False,
        "production_credential_content_read_allowed": False,
        "credential_value_output_allowed": False,
        "environment_variable_read_allowed": False,
        "dns_resolution_allowed": False,
        "network_connection_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "DESIGN_ONLY_DUMMY_FIXTURE_READ",
        "ready_for_ls_new_batch_4f_b": True,
        "ready_for_production_credential_presence_check": False,
        "ready_for_production_read_only_lookup": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4F-A Credential Fixture Validator Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Mode: `{result["validation_mode"]}`
- Fixture: `{result["fixture_path"]}`

## File Validation

- Exists: `true`
- Regular file: `true`
- Mode: `{result["fixture_mode_octal"]}`
- Mode valid: `true`
- Current-user owner: `true`

## Key Validation

- Required keys present: `true`
- Missing keys: `0`
- Unknown keys: `0`
- Duplicate keys: `0`
- Empty values: `0`

## Secret Handling

- Credential values output: `false`
- Value lengths output: `false`
- Value hashes output: `false`
- Environment variables read: `false`
- Production credential path touched: `false`

## External Access

- Network operations performed: `false`
- WordPress access performed: `false`

## Verified Checks

{checks}

## Safety Boundary

- Production credential metadata read allowed: `false`
- Production credential content read allowed: `false`
- Credential-value output allowed: `false`
- Environment-variable read allowed: `false`
- DNS resolution allowed: `false`
- Network connection allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress write allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `DESIGN_ONLY_DUMMY_FIXTURE_READ`

## Next State

ダミー認証ファイルに対する構造、必須キー、重複、未知キー、
空値、所有者、パーミッション検査の基準を固定しました。

実 `/etc/ai-media-os/wordpress-readonly-category.env` には触れておらず、
認証値、値の長さ、ハッシュ、部分文字列も出力していません。

次の `LS-NEW-BATCH-4F-B` で、実ファイルに対する非秘密の存在・
所有者・権限・必須キー名確認へ進めます。
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
    parser.add_argument(
        "--check-only",
        action="store_true",
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

        package = build_package(
            request=request,
            policy=policy,
        )

        result = build_result(
            package,
            request_path=request_path,
            output_path=output_path,
            policy_checks=policy_checks,
        )

        if not args.check_only:
            write_json(output_path, package)
            write_json(RESULT_PATH, result)
            write_text(
                REPORT_PATH,
                build_report(result),
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
                    "phase_id": "LS-NEW-BATCH-4F-A",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "production_credential_path_touched": False,
                    "credential_value_output_allowed": False,
                    "environment_variable_read_allowed": False,
                    "wordpress_api_call_allowed": False,
                    "execution_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
