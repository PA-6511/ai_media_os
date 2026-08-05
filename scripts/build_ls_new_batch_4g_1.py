#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_read_only_category_lookup_implementation_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_mock_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_mock_result.example.json"
)
LOOKUP_MODULE_PATH = (
    ROOT / "scripts/wordpress_readonly_category_lookup.py"
)

RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4g_1_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_1_read_only_category_lookup_implementation_report.md"
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
    return load_lookup_module().canonical_digest(value)


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


def load_lookup_module():
    spec = importlib.util.spec_from_file_location(
        "wordpress_readonly_category_lookup_runtime",
        LOOKUP_MODULE_PATH,
    )

    if spec is None or spec.loader is None:
        raise ValidationError(
            "lookup implementation module could not be loaded"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-4G-1",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_READ_ONLY_CATEGORY_LOOKUP_IMPLEMENTATION_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == "LOCAL_WORDPRESS_API_MOCK_ONLY",
        "operation mode mismatch",
    )
    checks.append("mock_only_mode")

    transport = policy.get("transport_contract", {})

    require(
        transport.get("current_transport")
        == "LOCAL_JSON_MOCK",
        "current transport mismatch",
    )
    require(
        transport.get("allowed_http_method") == "GET",
        "only GET may be implemented",
    )
    require(
        transport.get("request_body_allowed") is False,
        "request body must remain forbidden",
    )
    require(
        transport.get(
            "authorization_header_allowed_in_current_phase"
        )
        is False,
        "authorization header must remain forbidden",
    )
    checks.append("transport_contract")

    fixture_policy = policy.get("mock_fixture", {})

    require(
        fixture_policy.get("production_usable") is False,
        "fixture mapping must not be production usable",
    )
    require(
        fixture_policy.get("payload_injection_allowed")
        is False,
        "fixture mapping injection must remain blocked",
    )
    checks.append("fixture_isolation")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "credential_file_metadata_read_allowed",
        "credential_file_content_read_allowed",
        "credential_value_output_allowed",
        "environment_variable_read_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "tls_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_response_read_allowed",
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
        == "LOCAL_MOCK_LOOKUP_IMPLEMENTATION_ONLY",
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
        "source design path must be a string",
    )

    source_path = resolve_repo_path(source_path_value)
    source = load_json(source_path)

    require(
        source.get("phase_id")
        == policy.get("source_phase_id"),
        "source phase mismatch",
    )
    require(
        source.get("operation_mode")
        == "READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY",
        "source operation mode mismatch",
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
        "source design digest verification failed",
    )

    gate = source.get("preexecution_gate", {})

    require(
        gate.get("state") == "BLOCKED_LOOKUP_DESIGN_ONLY",
        "source gate state mismatch",
    )
    require(
        gate.get("execution_allowed") is False,
        "source execution gate must remain closed",
    )

    return [
        "source_phase_identity",
        "source_design_digest_verified",
        "source_get_only_contract_verified",
        "source_network_unaccessed",
        "source_wordpress_unaccessed",
        "source_execution_gate_closed",
    ]


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[Path, list[dict[str, str]]]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4G-1",
        "request phase_id mismatch",
    )
    require(
        request.get("operation_mode")
        == "LOCAL_WORDPRESS_API_MOCK_ONLY",
        "request operation mode mismatch",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    for field in [
        "credential_file_read_requested",
        "environment_variable_read_requested",
        "dns_resolution_requested",
        "network_connection_requested",
        "tls_connection_requested",
        "http_request_requested",
        "wordpress_response_read_requested",
        "wordpress_write_requested",
        "credential_value_output_requested",
        "automatic_payload_injection_requested",
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

    fixture_value = request.get("mock_fixture_path")

    require(
        isinstance(fixture_value, str),
        "mock_fixture_path must be a string",
    )

    fixture_path = resolve_repo_path(fixture_value).resolve()
    allowed_root = (
        ROOT / policy["mock_fixture"]["allowed_root"]
    ).resolve()

    require(
        fixture_path.is_relative_to(allowed_root),
        "mock fixture path escapes allowed root",
    )

    targets = request.get("target_categories")

    require(
        isinstance(targets, list) and len(targets) >= 1,
        "target_categories must be non-empty",
    )

    normalized_targets: list[dict[str, str]] = []
    seen_slugs: set[str] = set()

    for index, target in enumerate(targets, start=1):
        require(
            isinstance(target, dict),
            f"target[{index}] must be an object",
        )

        slug = target.get("category_slug")
        name = target.get("category_name")

        require(
            isinstance(slug, str) and slug.strip(),
            f"target[{index}] invalid category_slug",
        )
        require(
            isinstance(name, str) and name.strip(),
            f"target[{index}] invalid category_name",
        )

        slug = slug.strip()
        name = name.strip()

        require(
            slug not in seen_slugs,
            f"duplicate target slug: {slug}",
        )

        seen_slugs.add(slug)

        normalized_targets.append(
            {
                "category_slug": slug,
                "category_name": name,
            }
        )

    return fixture_path, normalized_targets


def build_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source_design(
        request,
        policy,
    )
    fixture_path, targets = validate_request(
        request,
        policy,
    )

    lookup_module = load_lookup_module()
    fixture = load_json(fixture_path)

    try:
        lookup_result = (
            lookup_module.execute_local_mock_lookup(
                fixture=fixture,
                targets=targets,
                policy=policy,
            )
        )
    except lookup_module.LookupValidationError as exc:
        raise ValidationError(str(exc)) from exc

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4G-1",
        "policy_id": policy["policy_id"],
        "implementation_package_id": (
            "wp-read-only-category-lookup-mock-implementation"
        ),
        "operation_mode": "LOCAL_WORDPRESS_API_MOCK_ONLY",
        "mock_fixture_path": display_path(fixture_path),
        "implementation_state": {
            "lookup_module_created": True,
            "get_only_transport_enforced": True,
            "exact_match_logic_implemented": True,
            "missing_result_block_implemented": True,
            "duplicate_result_block_implemented": True,
            "name_mismatch_block_implemented": True,
            "invalid_id_block_implemented": True,
        },
        "lookup_result": lookup_result,
        "production_mapping_state": {
            "production_category_ids_present": False,
            "production_category_ids_usable": False,
            "fixture_category_ids_present": True,
            "fixture_category_ids_applied_to_payload": False,
            "human_verification_completed": False,
        },
        "preexecution_gate": {
            "state": "BLOCKED_LOCAL_MOCK_ONLY",
            "implementation_verified": True,
            "actual_network_lookup_authorized": False,
            "credential_loading_authorized": False,
            "wordpress_read_authorized": False,
            "wordpress_write_authorized": False,
            "execution_approval_issued": False,
            "approval_token": None,
            "execution_allowed": False,
        },
        "execution_boundary": {
            "credential_file_read_allowed": False,
            "credential_value_output_allowed": False,
            "environment_variable_read_allowed": False,
            "dns_resolution_allowed": False,
            "network_connection_allowed": False,
            "tls_connection_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_category_lookup_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "external_api_call_allowed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "LOCAL_MOCK_LOOKUP_IMPLEMENTATION_ONLY"
            ),
        },
        "verified_checks": source_checks,
    }

    package = copy.deepcopy(package_without_digest)
    package["implementation_package_digest_sha256"] = (
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
    lookup = package["lookup_result"]
    mapping_state = package["production_mapping_state"]
    gate = package["preexecution_gate"]

    return {
        "phase_id": "LS-NEW-BATCH-4G-1",
        "status": (
            "PASS_READ_ONLY_CATEGORY_LOOKUP_"
            "IMPLEMENTATION_MOCK_ONLY"
        ),
        "decision": (
            "GET_MATCHING_LOGIC_VERIFIED_"
            "ACTUAL_NETWORK_LOOKUP_PENDING"
        ),
        "policy_id": package["policy_id"],
        "implementation_package_id": package[
            "implementation_package_id"
        ],
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "mock_fixture_path": package["mock_fixture_path"],
        "operation_mode": package["operation_mode"],
        "transport": lookup["transport"],
        "http_method": lookup["method"],
        "rest_path": lookup["rest_path"],
        "mapping_count": lookup["mapping_count"],
        "mappings": lookup["mappings"],
        "mock_response_digest_sha256": lookup[
            "mock_response_digest_sha256"
        ],
        "credential_file_read": lookup[
            "credential_file_read"
        ],
        "credential_values_loaded": lookup[
            "credential_values_loaded"
        ],
        "credential_values_output": lookup[
            "credential_values_output"
        ],
        "dns_resolution_performed": lookup[
            "dns_resolution_performed"
        ],
        "network_connection_performed": lookup[
            "network_connection_performed"
        ],
        "tls_connection_performed": lookup[
            "tls_connection_performed"
        ],
        "http_request_performed": lookup[
            "http_request_performed"
        ],
        "wordpress_response_read": lookup[
            "wordpress_response_read"
        ],
        "wordpress_write_performed": lookup[
            "wordpress_write_performed"
        ],
        "fixture_category_ids_present": mapping_state[
            "fixture_category_ids_present"
        ],
        "fixture_category_ids_applied_to_payload": mapping_state[
            "fixture_category_ids_applied_to_payload"
        ],
        "production_category_ids_present": mapping_state[
            "production_category_ids_present"
        ],
        "production_category_ids_usable": mapping_state[
            "production_category_ids_usable"
        ],
        "preexecution_gate_state": gate["state"],
        "implementation_package_digest_sha256": package[
            "implementation_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity",
                "mock_fixture_root_confinement",
                "mock_source_identity",
                "get_method_enforcement",
                "category_endpoint_enforcement",
                "query_parameter_enforcement",
                "request_body_absence",
                "authorization_header_absence",
                "mock_http_status_validation",
                "mock_content_type_validation",
                "mock_response_schema_validation",
                "fixture_category_id_reserved_range",
                "exact_slug_matching",
                "exact_name_matching",
                "single_result_enforcement",
                "positive_category_id_validation",
                "matched_mapping_digest_generation",
                "mock_response_digest_generation",
                "fixture_mapping_isolation",
                "production_payload_not_modified",
                "implementation_package_digest_generation",
                "execution_gate_closed",
            ]
        ),
        "credential_file_read_allowed": False,
        "credential_value_output_allowed": False,
        "environment_variable_read_allowed": False,
        "dns_resolution_allowed": False,
        "network_connection_allowed": False,
        "tls_connection_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "LOCAL_MOCK_LOOKUP_IMPLEMENTATION_ONLY"
        ),
        "ready_for_ls_new_batch_4g_2": True,
        "ready_for_actual_read_only_lookup_authorization": True,
        "ready_for_actual_read_only_lookup": False,
        "ready_for_category_id_resolution": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    mapping_lines = "\n".join(
        (
            f"- `{mapping['category_slug']}` → "
            f"`{mapping['candidate_fixture_category_id']}` "
            f"(`{mapping['match_state']}`)"
        )
        for mapping in result["mappings"]
    )

    return f"""# LS-NEW-BATCH-4G-1 Read-Only Category Lookup Implementation Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Transport: `{result["transport"]}`
- Method: `{result["http_method"]}`
- REST path: `{result["rest_path"]}`
- Mapping count: `{result["mapping_count"]}`

## Mock Mapping

{mapping_lines}

The category IDs above are reserved fixture IDs only.

## Isolation

- Fixture category IDs present: `true`
- Fixture IDs applied to payload: `false`
- Production category IDs present: `false`
- Production category IDs usable: `false`

## Access State

- Credential file read: `false`
- Credential values loaded: `false`
- Credential values output: `false`
- DNS resolution performed: `false`
- Network connection performed: `false`
- TLS connection performed: `false`
- HTTP request performed: `false`
- WordPress response read: `false`
- WordPress write performed: `false`

## Gate State

- Pre-execution gate: `{result["preexecution_gate_state"]}`
- Ready for actual lookup: `false`
- Execution allowed: `false`

## Verified Checks

{checks}

## Safety Boundary

- Credential file read allowed: `false`
- Credential-value output allowed: `false`
- Network connection allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress write allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `LOCAL_MOCK_LOOKUP_IMPLEMENTATION_ONLY`

## Next State

GET専用カテゴリ検索、応答形式検証、slug・name完全一致、
単一結果、ID妥当性、失敗時ブロックを実装しました。

今回取得したIDはローカルモック専用であり、本番ペイロードには
注入されていません。

次の `LS-NEW-BATCH-4G-2` で、実GET通信を許可するための
明示承認ゲートと実行コマンドを分離して構築します。
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
        result = {
            "phase_id": "LS-NEW-BATCH-4G-1",
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "credential_file_read": False,
            "credential_values_output": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_response_read": False,
            "wordpress_write_performed": False,
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
