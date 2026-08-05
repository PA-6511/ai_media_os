#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_production_credential_validator_design_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_credential_validator_design_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_credential_validator_design_package.example.json"
)

RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4f_b_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4f_b_production_credential_validator_design_report.md"
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
        policy.get("phase_id") == "LS-NEW-BATCH-4F-B",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("current_mode")
        == "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY",
        "current mode mismatch",
    )
    checks.append("design_only_mode")

    current_access = policy.get(
        "current_phase_access",
        {},
    )

    require(
        current_access.get(
            "production_path_string_reference_allowed"
        )
        is True,
        "production path string reference must be allowed",
    )

    for field in [
        "production_file_exists_check_allowed",
        "production_file_lstat_allowed",
        "production_file_stat_allowed",
        "production_file_metadata_read_allowed",
        "production_file_content_open_allowed",
        "production_file_content_read_allowed",
        "production_key_name_parse_allowed",
        "production_empty_value_check_allowed",
        "environment_variable_read_allowed",
        "environment_export_allowed",
    ]:
        require(
            current_access.get(field) is False,
            f"{field} must remain false",
        )

    checks.append("current_access_boundary")

    future = policy.get(
        "future_non_secret_validation",
        {},
    )

    for field in [
        "credential_values_may_be_loaded_into_memory",
        "credential_values_may_be_exported",
        "credential_values_may_be_output",
        "credential_value_lengths_may_be_output",
        "credential_value_hashes_may_be_output",
        "credential_value_prefixes_may_be_output",
        "credential_value_suffixes_may_be_output",
    ]:
        require(
            future.get(field) is False,
            f"{field} must remain false",
        )

    checks.append("future_secret_boundary")

    gate = policy.get("block_gate", {})

    require(
        gate.get("state")
        == "BLOCKED_VALIDATOR_DESIGN_ONLY",
        "block gate state mismatch",
    )
    require(
        gate.get("production_credential_presence_verified")
        is False,
        "production presence must remain unverified",
    )
    require(
        gate.get("execution_allowed") is False,
        "execution must remain blocked",
    )
    checks.append("block_gate")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "production_credential_exists_check_allowed",
        "production_credential_lstat_allowed",
        "production_credential_stat_allowed",
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
        == "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY",
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source_fixture_result(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    source_path_value = request.get(
        "source_fixture_validation_package_path"
    )

    require(
        isinstance(source_path_value, str),
        "source fixture package path must be a string",
    )

    source_path = resolve_repo_path(source_path_value)
    source = load_json(source_path)

    require(
        source.get("phase_id")
        == policy.get("source_phase_id"),
        "source phase mismatch",
    )
    require(
        source.get("validation_mode")
        == "LOCAL_DUMMY_FIXTURE_ONLY",
        "source validation mode mismatch",
    )
    require(
        source.get("credential_structure_state")
        == "VALID_DUMMY_FIXTURE",
        "source fixture structure was not validated",
    )

    expected_digest = source.get(
        "sanitized_result_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source sanitized digest is invalid",
    )
    require(
        request.get(
            "source_fixture_result_digest_sha256"
        )
        == expected_digest,
        "request source digest mismatch",
    )

    source_without_digest = copy.deepcopy(source)
    source_without_digest.pop(
        "sanitized_result_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_digest,
        "source fixture result digest verification failed",
    )

    require(
        source.get("production_credential_path_touched")
        is False,
        "source must not have touched production credential path",
    )
    require(
        source.get("production_credential_metadata_read")
        is False,
        "source must not have read production metadata",
    )
    require(
        source.get("production_credential_content_read")
        is False,
        "source must not have read production content",
    )

    return [
        "source_phase_identity",
        "source_fixture_structure_verified",
        "source_sanitized_digest_verified",
        "source_production_path_untouched",
    ]


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4F-B",
        "request phase_id mismatch",
    )
    require(
        request.get("design_mode")
        == "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY",
        "request design mode mismatch",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    contract = policy[
        "production_credential_contract"
    ]

    require(
        request.get("production_credential_path")
        == contract["credential_file_path"],
        "production credential path mismatch",
    )

    require(
        request.get("planned_checks")
        == contract["allowed_future_checks"],
        "planned checks mismatch",
    )

    for field in [
        "production_file_exists_check_requested",
        "production_file_lstat_requested",
        "production_file_stat_requested",
        "production_file_metadata_read_requested",
        "production_file_content_open_requested",
        "production_file_content_read_requested",
        "production_key_name_parse_requested",
        "production_empty_value_check_requested",
        "environment_variable_read_requested",
        "network_access_requested",
        "wordpress_access_requested",
        "secret_output_requested",
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

    return contract


def build_validator_plan(
    contract: dict[str, Any],
) -> dict[str, Any]:
    plan_without_digest = {
        "validator_mode": (
            "NON_SECRET_PRODUCTION_CREDENTIAL_CHECK"
        ),
        "target_path": contract["credential_file_path"],
        "expected_owner": contract["expected_owner"],
        "expected_group": contract["expected_group"],
        "required_mode_octal": contract[
            "required_mode_octal"
        ],
        "required_keys": contract["required_keys"],
        "planned_checks": contract[
            "allowed_future_checks"
        ],
        "future_output_schema": {
            "exists": "boolean",
            "regular_file": "boolean",
            "symbolic_link": "boolean",
            "owner_matches": "boolean",
            "group_matches": "boolean",
            "mode_octal": "string",
            "mode_matches": "boolean",
            "required_keys_present": "boolean",
            "missing_key_names": "list[string]",
            "unknown_key_names": "list[string]",
            "duplicate_key_names": "list[string]",
            "empty_value_key_names": "list[string]",
            "credential_values_output": "constant_false",
            "value_lengths_output": "constant_false",
            "value_hashes_output": "constant_false"
        },
        "future_failure_behavior": {
            "missing_file": "BLOCK",
            "symbolic_link": "BLOCK",
            "wrong_owner": "BLOCK",
            "wrong_group": "BLOCK",
            "wrong_mode": "BLOCK",
            "missing_key": "BLOCK",
            "unknown_key": "BLOCK",
            "duplicate_key": "BLOCK",
            "empty_value": "BLOCK"
        },
        "current_phase_execution": {
            "exists_check_performed": False,
            "lstat_performed": False,
            "stat_performed": False,
            "metadata_read": False,
            "content_opened": False,
            "content_read": False,
            "key_names_parsed": False,
            "empty_values_checked": False,
            "environment_variables_read": False
        },
        "credential_values_may_be_loaded_into_memory": False,
        "credential_values_may_be_output": False,
        "network_operations_allowed": False,
        "wordpress_operations_allowed": False
    }

    plan = copy.deepcopy(plan_without_digest)
    plan["validator_plan_digest_sha256"] = (
        canonical_digest(plan_without_digest)
    )

    return plan


def build_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source_fixture_result(
        request,
        policy,
    )
    contract = validate_request(
        request,
        policy,
    )
    validator_plan = build_validator_plan(contract)

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4F-B",
        "policy_id": policy["policy_id"],
        "design_package_id": (
            "wp-production-credential-validator-design"
        ),
        "design_mode": (
            "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY"
        ),
        "production_credential_path_reference": contract[
            "credential_file_path"
        ],
        "production_credential_path_touched": False,
        "production_file_exists_checked": False,
        "production_file_lstat_performed": False,
        "production_file_stat_performed": False,
        "production_file_metadata_read": False,
        "production_file_content_opened": False,
        "production_file_content_read": False,
        "production_key_names_parsed": False,
        "production_empty_values_checked": False,
        "validator_plan": validator_plan,
        "verification_state": {
            "fixture_baseline_complete": True,
            "validator_design_complete": True,
            "production_credential_presence_verified": False,
            "production_credential_metadata_verified": False,
            "production_credential_structure_verified": False,
            "production_read_only_lookup_ready": False
        },
        "block_gate": {
            "state": "BLOCKED_VALIDATOR_DESIGN_ONLY",
            "explicit_actual_check_phase_required": True,
            "execution_approval_issued": False,
            "approval_token": None,
            "execution_allowed": False
        },
        "execution_boundary": {
            "production_credential_exists_check_allowed": False,
            "production_credential_lstat_allowed": False,
            "production_credential_stat_allowed": False,
            "production_credential_metadata_read_allowed": False,
            "production_credential_content_read_allowed": False,
            "credential_value_output_allowed": False,
            "environment_variable_read_allowed": False,
            "dns_resolution_allowed": False,
            "network_connection_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_category_lookup_allowed": False,
            "wordpress_database_read_allowed": False,
            "wordpress_database_write_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "external_api_call_allowed": False,
            "execution_approval_issued": False,
            "approval_token_present": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY"
            )
        },
        "verified_checks": source_checks
    }

    package = copy.deepcopy(package_without_digest)
    package["design_package_digest_sha256"] = (
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
    verification = package["verification_state"]
    plan_execution = package[
        "validator_plan"
    ]["current_phase_execution"]

    return {
        "phase_id": "LS-NEW-BATCH-4F-B",
        "status": (
            "PASS_PRODUCTION_CREDENTIAL_VALIDATOR_"
            "DESIGN_BLOCKED"
        ),
        "decision": (
            "NON_SECRET_VALIDATOR_PLAN_FIXED_"
            "PRODUCTION_FILE_UNTOUCHED"
        ),
        "policy_id": package["policy_id"],
        "design_package_id": package[
            "design_package_id"
        ],
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "design_mode": package["design_mode"],
        "production_credential_path_reference": package[
            "production_credential_path_reference"
        ],
        "fixture_baseline_complete": verification[
            "fixture_baseline_complete"
        ],
        "validator_design_complete": verification[
            "validator_design_complete"
        ],
        "production_credential_path_touched": False,
        "production_file_exists_checked": plan_execution[
            "exists_check_performed"
        ],
        "production_file_lstat_performed": plan_execution[
            "lstat_performed"
        ],
        "production_file_stat_performed": plan_execution[
            "stat_performed"
        ],
        "production_file_metadata_read": plan_execution[
            "metadata_read"
        ],
        "production_file_content_opened": plan_execution[
            "content_opened"
        ],
        "production_file_content_read": plan_execution[
            "content_read"
        ],
        "production_key_names_parsed": plan_execution[
            "key_names_parsed"
        ],
        "production_empty_values_checked": plan_execution[
            "empty_values_checked"
        ],
        "credential_values_output": False,
        "value_lengths_output": False,
        "value_hashes_output": False,
        "environment_variables_read": False,
        "production_credential_presence_verified": False,
        "production_credential_metadata_verified": False,
        "production_credential_structure_verified": False,
        "block_gate_state": package[
            "block_gate"
        ]["state"],
        "validator_plan_digest_sha256": package[
            "validator_plan"
        ]["validator_plan_digest_sha256"],
        "design_package_digest_sha256": package[
            "design_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity",
                "production_path_exact_match",
                "planned_check_contract",
                "exists_check_not_performed",
                "lstat_not_performed",
                "stat_not_performed",
                "metadata_not_read",
                "content_not_opened",
                "content_not_read",
                "key_names_not_parsed",
                "empty_values_not_checked",
                "secret_output_absence",
                "future_output_schema_fixed",
                "future_failure_behavior_fixed",
                "validator_plan_digest_generation",
                "design_package_digest_generation",
                "block_gate_fixed"
            ]
        ),
        "production_credential_exists_check_allowed": False,
        "production_credential_lstat_allowed": False,
        "production_credential_stat_allowed": False,
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
        "safety_state": (
            "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY"
        ),
        "ready_for_ls_new_batch_4f_c": True,
        "ready_for_actual_non_secret_presence_check": False,
        "ready_for_production_read_only_lookup": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4F-B Production Credential Validator Design Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Mode: `{result["design_mode"]}`
- Target path reference: `{result["production_credential_path_reference"]}`

## Baseline State

- Fixture baseline complete: `true`
- Validator design complete: `true`
- Production credential presence verified: `false`
- Production credential metadata verified: `false`
- Production credential structure verified: `false`

## Production File Access

- Production path touched: `false`
- Exists check performed: `false`
- lstat performed: `false`
- stat performed: `false`
- Metadata read: `false`
- Content opened: `false`
- Content read: `false`
- Key names parsed: `false`
- Empty values checked: `false`

## Secret Handling

- Credential values output: `false`
- Value lengths output: `false`
- Value hashes output: `false`
- Environment variables read: `false`

## Gate State

- Block gate: `{result["block_gate_state"]}`
- Execution allowed: `false`

## Integrity

- Validator plan digest: `{result["validator_plan_digest_sha256"]}`
- Design package digest: `{result["design_package_digest_sha256"]}`

## Verified Checks

{checks}

## Safety Boundary

- Production credential exists check allowed: `false`
- Production credential lstat allowed: `false`
- Production credential stat allowed: `false`
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
- Safety state: `PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY`

## Next State

実認証ファイルに対する非秘密検証項目、出力形式、
失敗時の強制ブロック条件を固定しました。

実ファイルの存在確認、lstat、stat、所有者・権限確認、
内容open、キー名解析、空値確認はまだ実行していません。

次の `LS-NEW-BATCH-4F-C` で明示承認された場合に限り、
秘密値を一切出力しない実ファイル存在・メタデータ・
必須キー構造確認へ進めます。
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
                    "phase_id": "LS-NEW-BATCH-4F-B",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "production_credential_path_touched": False,
                    "production_credential_metadata_read_allowed": False,
                    "production_credential_content_read_allowed": False,
                    "credential_value_output_allowed": False,
                    "wordpress_api_call_allowed": False,
                    "execution_allowed": False
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
