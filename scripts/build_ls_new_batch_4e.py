#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_credential_isolated_read_only_preflight_policy.json"
)
DEFAULT_SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_discovery_result.example.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_lookup_preflight_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_lookup_preflight_package.example.json"
)

RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4e_result.json"
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4e_credential_isolated_read_only_preflight_report.md"
)

FORBIDDEN_REQUEST_KEYS = {
    "authorization",
    "password",
    "app_password",
    "application_password",
    "secret",
    "token",
    "cookie",
    "username_value",
    "credential_value"
}


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


def normalize_text(
    value: Any,
    *,
    field_name: str,
    required: bool,
) -> str | None:
    if value is None:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} must be a string or null"
        )

    normalized = unicodedata.normalize("NFKC", value).strip()

    if normalized == "":
        if required:
            raise ValidationError(
                f"{field_name} must not be blank"
            )
        return None

    return normalized


def scan_forbidden_request_keys(
    value: Any,
    *,
    path: str = "request",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).strip().lower()

            require(
                normalized_key not in FORBIDDEN_REQUEST_KEYS,
                f"forbidden credential-like key detected: "
                f"{path}.{key}",
            )

            scan_forbidden_request_keys(
                child,
                path=f"{path}.{key}",
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_forbidden_request_keys(
                child,
                path=f"{path}[{index}]",
            )


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-4E",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_CREDENTIAL_ISOLATED_READ_ONLY_PREFLIGHT_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("current_mode")
        == "DESIGN_ONLY_NO_CREDENTIAL_ACCESS",
        "current mode mismatch",
    )
    checks.append("design_only_mode")

    request_contract = policy.get(
        "read_only_request_contract",
        {},
    )

    require(
        request_contract.get("allowed_http_methods")
        == ["GET"],
        "only GET may be planned",
    )
    require(
        request_contract.get("request_body_allowed") is False,
        "request body must be forbidden",
    )
    require(
        request_contract.get(
            "custom_authorization_header_in_request_allowed"
        )
        is False,
        "custom authorization header must be forbidden",
    )
    checks.append("read_only_http_contract")

    isolation = policy.get("credential_isolation", {})

    for field in [
        "credential_values_in_policy_allowed",
        "credential_values_in_request_allowed",
        "credential_file_exists_check_allowed",
        "credential_file_metadata_read_allowed",
        "credential_file_content_read_allowed",
        "environment_variable_read_allowed",
        "secret_output_allowed",
        "production_writer_credentials_reuse_allowed",
    ]:
        require(
            isolation.get(field) is False,
            f"{field} must remain false",
        )

    require(
        isolation.get(
            "separate_read_only_wordpress_account_required"
        )
        is True,
        "separate read-only account must be required",
    )
    checks.append("credential_isolation_contract")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "credential_read_allowed",
        "environment_variable_read_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_database_read_allowed",
        "wordpress_database_write_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "x_api_call_allowed",
        "x_post_allowed",
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
        == "CREDENTIAL_ISOLATED_READ_ONLY_PREFLIGHT_DESIGN",
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source(
    source: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    require(
        source.get("phase_id")
        == policy.get("source_phase_id"),
        "source phase mismatch",
    )
    require(
        source.get("template_contract_id")
        == policy.get("template_contract_id"),
        "template contract mismatch",
    )

    expected_digest = source.get(
        "discovery_package_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source discovery digest is invalid",
    )

    source_without_digest = copy.deepcopy(source)
    source_without_digest.pop(
        "discovery_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_digest,
        "source discovery package digest "
        "verification failed",
    )

    require(
        source.get("discovery_mode")
        == "LOCAL_FIXTURE_ONLY",
        "source discovery mode mismatch",
    )

    summary = source.get("discovery_summary", {})
    gate = source.get("preexecution_gate", {})

    require(
        summary.get("all_categories_matched") is True,
        "source categories must all be matched",
    )
    require(
        summary.get(
            "fixture_candidates_applied_to_payload"
        )
        is False,
        "fixture candidates must not be applied",
    )
    require(
        summary.get("production_category_ids_present")
        is False,
        "production category IDs must remain absent",
    )
    require(
        gate.get("state")
        == "BLOCKED_FIXTURE_DISCOVERY_NOT_PRODUCTION",
        "source gate state mismatch",
    )
    require(
        gate.get("execution_allowed") is False,
        "source execution must remain blocked",
    )

    return [
        "source_phase_identity",
        "source_discovery_digest_verified",
        "source_fixture_candidates_isolated",
        "source_production_category_ids_absent",
        "source_execution_gate_closed",
    ]


def validate_request(
    request: dict[str, Any],
    source: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, str]:
    scan_forbidden_request_keys(request)

    require(
        request.get("phase_id") == "LS-NEW-BATCH-4E",
        "request phase_id mismatch",
    )
    require(
        request.get("discovery_package_id")
        == source.get("discovery_package_id"),
        "request discovery_package_id mismatch",
    )
    require(
        request.get("batch_id") == source.get("batch_id"),
        "request batch_id mismatch",
    )
    require(
        request.get(
            "source_discovery_package_digest_sha256"
        )
        == source.get("discovery_package_digest_sha256"),
        "request source digest mismatch",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    require(
        request.get("preflight_mode")
        == "DESIGN_ONLY_NO_CREDENTIAL_ACCESS",
        "preflight mode mismatch",
    )
    require(
        request.get("execution_approval_issued") is False,
        "execution approval must remain false",
    )
    require(
        request.get("approval_token") is None,
        "approval token must remain null",
    )

    endpoint = request.get("endpoint_plan")

    require(
        isinstance(endpoint, dict),
        "endpoint_plan must be an object",
    )
    require(
        endpoint.get("base_url") is None,
        "base_url must remain null",
    )
    require(
        endpoint.get("rest_path")
        == policy["read_only_request_contract"][
            "required_rest_path"
        ],
        "REST path mismatch",
    )
    require(
        endpoint.get("http_method") == "GET",
        "HTTP method must be GET",
    )
    require(
        endpoint.get("request_body") is None,
        "request body must remain null",
    )
    require(
        endpoint.get("custom_headers") is None,
        "custom headers must remain null",
    )

    expected_query = {
        "slug": "{category_slug}",
        "per_page": 100,
        "_fields": "id,slug,name,count",
    }

    require(
        endpoint.get("query_template") == expected_query,
        "query template mismatch",
    )

    credential = request.get("credential_plan")

    require(
        isinstance(credential, dict),
        "credential_plan must be an object",
    )

    isolation = policy["credential_isolation"]

    require(
        credential.get("credential_file_path")
        == isolation["future_credential_file_path"],
        "credential file path mismatch",
    )
    require(
        credential.get(
            "required_environment_variable_names"
        )
        == isolation[
            "required_environment_variable_names"
        ],
        "environment-variable contract mismatch",
    )

    for field in [
        "credential_values_present",
        "credential_file_exists_check_requested",
        "credential_file_metadata_read_requested",
        "credential_file_content_read_requested",
        "environment_variable_read_requested",
    ]:
        require(
            credential.get(field) is False,
            f"{field} must remain false",
        )

    network = request.get("network_plan")

    require(
        isinstance(network, dict),
        "network_plan must be an object",
    )

    for field in [
        "dns_resolution_requested",
        "tcp_connection_requested",
        "tls_connection_requested",
        "http_request_requested",
        "wordpress_response_read_requested",
    ]:
        require(
            network.get(field) is False,
            f"{field} must remain false",
        )

    expected_categories = request.get(
        "expected_categories"
    )

    require(
        isinstance(expected_categories, list)
        and len(expected_categories) >= 1,
        "expected_categories must be a non-empty list",
    )

    requested: dict[str, str] = {}

    for index, category in enumerate(
        expected_categories,
        start=1,
    ):
        require(
            isinstance(category, dict),
            f"expected_categories[{index}] must be an object",
        )

        slug = normalize_text(
            category.get("category_slug"),
            field_name=(
                f"expected_categories[{index}].category_slug"
            ),
            required=True,
        )
        name = normalize_text(
            category.get("category_name"),
            field_name=(
                f"expected_categories[{index}].category_name"
            ),
            required=True,
        )

        assert slug is not None
        assert name is not None

        require(
            slug not in requested,
            f"duplicate expected category: {slug}",
        )

        requested[slug] = name

    source_categories = {
        item["category_slug"]: item["category_name"]
        for item in source["discovery_results"]
    }

    require(
        requested == source_categories,
        "requested categories must exactly match source",
    )

    return requested


def build_package(
    source: dict[str, Any],
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source(source, policy)
    categories = validate_request(
        request,
        source,
        policy,
    )

    query_plans = []

    for slug, name in sorted(categories.items()):
        plan_without_digest = {
            "category_slug": slug,
            "category_name": name,
            "http_method": "GET",
            "base_url": None,
            "rest_path": "/wp-json/wp/v2/categories",
            "query_parameters": {
                "slug": slug,
                "per_page": 100,
                "_fields": "id,slug,name,count"
            },
            "request_body": None,
            "authorization_header": None,
            "request_url_constructed": False,
            "credential_values_loaded": False,
            "dns_resolution_performed": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_response_read": False,
            "future_result_requires_exact_slug_match": True,
            "future_result_requires_exact_name_match": True,
            "future_result_requires_single_match": True,
            "future_result_requires_human_verification": True,
            "automatic_payload_injection_allowed": False
        }

        plan = copy.deepcopy(plan_without_digest)
        plan["query_plan_digest_sha256"] = (
            canonical_digest(plan_without_digest)
        )
        query_plans.append(plan)

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4E",
        "policy_id": policy["policy_id"],
        "preflight_package_id": (
            f"wp-readonly-category-preflight-"
            f"{source['batch_id']}"
        ),
        "source_discovery_package_id": source[
            "discovery_package_id"
        ],
        "batch_id": source["batch_id"],
        "template_contract_id": source[
            "template_contract_id"
        ],
        "source_discovery_package_digest_sha256": source[
            "discovery_package_digest_sha256"
        ],
        "preflight_mode": (
            "DESIGN_ONLY_NO_CREDENTIAL_ACCESS"
        ),
        "credential_contract": {
            "credential_file_path": policy[
                "credential_isolation"
            ]["future_credential_file_path"],
            "required_environment_variable_names": policy[
                "credential_isolation"
            ]["required_environment_variable_names"],
            "separate_read_only_wordpress_account_required": True,
            "production_writer_credentials_reuse_allowed": False,
            "credential_file_touched": False,
            "credential_values_loaded": False,
            "environment_variables_read": False,
            "secret_output_generated": False
        },
        "network_preflight": {
            "base_url_present": False,
            "dns_resolution_performed": False,
            "tcp_connection_performed": False,
            "tls_connection_performed": False,
            "http_request_performed": False,
            "wordpress_response_read": False
        },
        "query_plan_count": len(query_plans),
        "query_plans": query_plans,
        "preexecution_gate": {
            "state": (
                "BLOCKED_NO_SITE_URL_NO_CREDENTIAL_"
                "PREFLIGHT_NO_NETWORK_AUTHORITY"
            ),
            "read_only_request_contract_ready": True,
            "credential_contract_ready": True,
            "credential_presence_verified": False,
            "base_url_resolved": False,
            "network_preflight_completed": False,
            "production_category_lookup_completed": False,
            "execution_approval_issued": False,
            "approval_token": None,
            "execution_allowed": False
        },
        "execution_boundary": {
            "credential_read_allowed": False,
            "environment_variable_read_allowed": False,
            "dns_resolution_allowed": False,
            "network_connection_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_category_lookup_allowed": False,
            "wordpress_database_read_allowed": False,
            "wordpress_database_write_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_post_allowed": False,
            "external_api_call_allowed": False,
            "execution_approval_issued": False,
            "approval_token_present": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "CREDENTIAL_ISOLATED_READ_ONLY_"
                "PREFLIGHT_DESIGN"
            )
        },
        "verified_checks": source_checks
    }

    output = copy.deepcopy(package_without_digest)
    output["preflight_package_digest_sha256"] = (
        canonical_digest(package_without_digest)
    )

    return output


def build_result(
    package: dict[str, Any],
    *,
    source_path: Path,
    request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    gate = package["preexecution_gate"]
    credential = package["credential_contract"]
    network = package["network_preflight"]

    return {
        "phase_id": "LS-NEW-BATCH-4E",
        "status": (
            "PASS_CREDENTIAL_ISOLATED_READ_ONLY_"
            "PREFLIGHT_DESIGN_NO_ACCESS"
        ),
        "decision": (
            "READ_ONLY_QUERY_CONTRACT_READY_"
            "CREDENTIALS_AND_NETWORK_UNTOUCHED"
        ),
        "policy_id": package["policy_id"],
        "preflight_package_id": package[
            "preflight_package_id"
        ],
        "source_discovery_package_id": package[
            "source_discovery_package_id"
        ],
        "batch_id": package["batch_id"],
        "source_path": display_path(source_path),
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "preflight_mode": package["preflight_mode"],
        "query_plan_count": package["query_plan_count"],
        "http_method": "GET",
        "rest_path": "/wp-json/wp/v2/categories",
        "base_url_present": network["base_url_present"],
        "credential_file_touched": credential[
            "credential_file_touched"
        ],
        "credential_values_loaded": credential[
            "credential_values_loaded"
        ],
        "environment_variables_read": credential[
            "environment_variables_read"
        ],
        "dns_resolution_performed": network[
            "dns_resolution_performed"
        ],
        "network_connection_performed": network[
            "tcp_connection_performed"
        ],
        "http_request_performed": network[
            "http_request_performed"
        ],
        "preexecution_gate_state": gate["state"],
        "execution_approval_issued": False,
        "approval_token_present": False,
        "preflight_package_digest_sha256": package[
            "preflight_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "preflight_request_identity",
                "forbidden_secret_key_scan",
                "base_url_null_lock",
                "get_method_lock",
                "rest_path_lock",
                "query_template_lock",
                "request_body_absence",
                "custom_header_absence",
                "credential_file_untouched",
                "environment_variables_unread",
                "network_operations_unperformed",
                "category_query_plan_generation",
                "query_plan_digest_generation",
                "preflight_package_digest_generation",
                "source_package_not_mutated",
                "execution_gate_closed"
            ]
        ),
        "credential_read_allowed": False,
        "environment_variable_read_allowed": False,
        "dns_resolution_allowed": False,
        "network_connection_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_database_read_allowed": False,
        "wordpress_database_write_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "x_post_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "CREDENTIAL_ISOLATED_READ_ONLY_PREFLIGHT_DESIGN"
        ),
        "ready_for_non_secret_credential_presence_preflight": True,
        "ready_for_ls_new_batch_4f": True,
        "ready_for_production_read_only_lookup": False,
        "ready_for_production_category_resolution": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4E Credential-Isolated Read-Only Preflight Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Package: `{result["preflight_package_id"]}`
- Batch: `{result["batch_id"]}`
- Mode: `{result["preflight_mode"]}`
- Query plans: `{result["query_plan_count"]}`

## Read-Only Contract

- HTTP method: `{result["http_method"]}`
- REST path: `{result["rest_path"]}`
- Base URL present: `false`
- Request body: `null`
- Custom authorization header: `null`

## Credential Isolation

- Credential file touched: `false`
- Credential values loaded: `false`
- Environment variables read: `false`
- Production writer credential reuse allowed: `false`

## Network State

- DNS resolution performed: `false`
- Network connection performed: `false`
- HTTP request performed: `false`

## Gate State

- Pre-execution gate: `{result["preexecution_gate_state"]}`
- Execution approval issued: `false`
- Approval token present: `false`
- Ready for execution: `false`

## Integrity

- Package digest: `{result["preflight_package_digest_sha256"]}`

## Verified Checks

{checks}

## Safety Boundary

- Credential read allowed: `false`
- Environment variable read allowed: `false`
- DNS resolution allowed: `false`
- Network connection allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress database read allowed: `false`
- WordPress database write allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- External API call allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `CREDENTIAL_ISOLATED_READ_ONLY_PREFLIGHT_DESIGN`

## Next State

読み取り専用カテゴリ取得のHTTP契約、クエリ形式、
認証情報分離方針を固定しました。

認証ファイルの存在確認、メタデータ取得、内容読み込み、
環境変数読み込み、DNS、TLS、HTTP通信は実施していません。

次の `LS-NEW-BATCH-4F` では秘密値を出力せず、
専用認証ファイルの存在・権限・必須変数名の有無だけを
確認する事前ゲートを設計できます。
"""


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_PATH,
    )
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

    source_path = resolve_path(args.source)
    request_path = resolve_path(args.request)
    output_path = resolve_path(args.output)

    try:
        policy = load_json(POLICY_PATH)
        source = load_json(source_path)
        request = load_json(request_path)

        policy_checks = validate_policy(policy)
        original_source = copy.deepcopy(source)

        package = build_package(
            source=source,
            request=request,
            policy=policy,
        )

        require(
            source == original_source,
            "source package was mutated",
        )

        result = build_result(
            package,
            source_path=source_path,
            request_path=request_path,
            output_path=output_path,
            policy_checks=policy_checks,
        )

        if not args.check_only:
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

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": "LS-NEW-BATCH-4E",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "credential_read_allowed": False,
                    "wordpress_api_call_allowed": False,
                    "wordpress_write_allowed": False,
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
