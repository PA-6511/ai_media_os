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
    "new_release_wp_read_only_category_lookup_policy.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_design_package.example.json"
)

RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4g_0_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_0_read_only_category_lookup_design_report.md"
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
        policy.get("phase_id") == "LS-NEW-BATCH-4G-0",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_READ_ONLY_CATEGORY_LOOKUP_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == "READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY",
        "operation mode mismatch",
    )
    checks.append("design_only_mode")

    http = policy.get("http_contract", {})

    require(
        http.get("allowed_method") == "GET",
        "only GET may be allowed",
    )
    require(
        http.get("allowed_rest_path")
        == "/wp-json/wp/v2/categories",
        "REST path mismatch",
    )
    require(
        http.get("request_body_allowed") is False,
        "request body must remain forbidden",
    )
    require(
        http.get("redirect_follow_allowed") is False,
        "redirect following must remain forbidden",
    )
    require(
        http.get("tls_verification_required") is True,
        "TLS verification must be required",
    )
    checks.append("read_only_http_contract")

    current = policy.get("current_phase_access", {})

    for field in [
        "credential_file_metadata_read_allowed",
        "credential_file_content_read_allowed",
        "environment_variable_read_allowed",
        "dns_resolution_allowed",
        "tls_connection_allowed",
        "http_request_allowed",
        "wordpress_response_read_allowed",
    ]:
        require(
            current.get(field) is False,
            f"{field} must remain false",
        )

    checks.append("current_phase_no_access")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "credential_value_output_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_post_read_allowed",
        "wordpress_media_read_allowed",
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
        == "READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY",
        "safety state mismatch",
    )

    checks.append("execution_boundary")

    return checks


def verify_source_result(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    source_path_value = request.get("source_result_path")

    require(
        isinstance(source_path_value, str),
        "source_result_path must be a string",
    )

    source_path = resolve_repo_path(source_path_value)
    source = load_json(source_path)

    require(
        source.get("phase_id")
        == policy.get("source_phase_id"),
        "source phase mismatch",
    )
    require(
        source.get("status")
        == "PASS_PRODUCTION_CREDENTIAL_NONSECRET_CHECK",
        "source credential check is not PASS",
    )

    expected_digest = source.get(
        "sanitized_check_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source sanitized digest is invalid",
    )
    require(
        request.get(
            "source_sanitized_check_digest_sha256"
        )
        == expected_digest,
        "request source digest mismatch",
    )

    require(
        source.get("production_credential_presence_verified")
        is True,
        "credential presence is not verified",
    )
    require(
        source.get("production_credential_metadata_verified")
        is True,
        "credential metadata is not verified",
    )
    require(
        source.get("production_credential_structure_verified")
        is True,
        "credential structure is not verified",
    )
    require(
        source.get("credential_values_output") is False,
        "source must not output credential values",
    )
    require(
        source.get("wordpress_access_performed") is False,
        "source must not have accessed WordPress",
    )
    require(
        source.get("ready_for_ls_new_batch_4g") is True,
        "source is not ready for 4G",
    )
    require(
        source.get("execution_allowed") is False,
        "source execution must remain blocked",
    )

    return [
        "source_phase_identity",
        "source_credential_check_passed",
        "source_sanitized_digest_referenced",
        "source_credential_presence_verified",
        "source_credential_metadata_verified",
        "source_credential_structure_verified",
        "source_secret_output_absent",
        "source_wordpress_access_absent",
        "source_execution_gate_closed",
    ]


def validate_request(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, str]]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4G-0",
        "request phase_id mismatch",
    )
    require(
        request.get("operation_mode")
        == "READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY",
        "request operation mode mismatch",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    credential_path = policy[
        "credential_contract"
    ]["credential_file_path"]

    require(
        request.get("credential_file_path")
        == credential_path,
        "credential file path mismatch",
    )

    http_plan = request.get("http_plan")

    require(
        isinstance(http_plan, dict),
        "http_plan must be an object",
    )
    require(
        http_plan.get("method") == "GET",
        "HTTP method must be GET",
    )
    require(
        http_plan.get("rest_path")
        == "/wp-json/wp/v2/categories",
        "REST path mismatch",
    )
    require(
        http_plan.get("request_body") is None,
        "request body must remain null",
    )
    require(
        http_plan.get("follow_redirects") is False,
        "redirect following must remain false",
    )
    require(
        http_plan.get("tls_verification_required")
        is True,
        "TLS verification must remain enabled",
    )

    expected_query = {
        "slug": "{category_slug}",
        "per_page": 100,
        "_fields": "id,slug,name,count",
    }

    require(
        http_plan.get("query_parameters")
        == expected_query,
        "query-parameter contract mismatch",
    )

    for field in [
        "credential_file_read_requested",
        "environment_variable_read_requested",
        "dns_resolution_requested",
        "tls_connection_requested",
        "http_request_requested",
        "wordpress_response_read_requested",
        "wordpress_write_requested",
        "credential_value_output_requested",
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
            f"target_categories[{index}] must be an object",
        )

        slug = target.get("category_slug")
        name = target.get("category_name")

        require(
            isinstance(slug, str) and slug.strip(),
            f"target_categories[{index}].category_slug "
            "must be non-empty",
        )
        require(
            isinstance(name, str) and name.strip(),
            f"target_categories[{index}].category_name "
            "must be non-empty",
        )

        slug = slug.strip()
        name = name.strip()

        require(
            slug not in seen_slugs,
            f"duplicate target category slug: {slug}",
        )

        seen_slugs.add(slug)

        normalized_targets.append(
            {
                "category_slug": slug,
                "category_name": name,
            }
        )

    require(
        normalized_targets == policy["target_categories"],
        "target categories mismatch policy",
    )

    return normalized_targets


def build_lookup_plan(
    target: dict[str, str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    http = policy["http_contract"]

    plan_without_digest = {
        "category_slug": target["category_slug"],
        "category_name": target["category_name"],
        "method": "GET",
        "base_url": None,
        "rest_path": http["allowed_rest_path"],
        "query_parameters": {
            "slug": target["category_slug"],
            "per_page": http["fixed_per_page"],
            "_fields": http["fixed_fields"],
        },
        "request_body": None,
        "authorization_header_constructed": False,
        "credential_values_loaded": False,
        "request_url_constructed": False,
        "dns_resolution_performed": False,
        "tls_connection_performed": False,
        "http_request_performed": False,
        "response_read": False,
        "future_matching_requirements": {
            "exact_slug_match": True,
            "exact_name_match": True,
            "single_result": True,
            "positive_integer_category_id": True,
            "human_verification_required": True,
            "automatic_payload_injection_allowed": False,
        },
    }

    plan = copy.deepcopy(plan_without_digest)
    plan["lookup_plan_digest_sha256"] = (
        canonical_digest(plan_without_digest)
    )

    return plan


def build_package(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source_result(
        request,
        policy,
    )
    targets = validate_request(
        request,
        policy,
    )

    plans = [
        build_lookup_plan(target, policy)
        for target in targets
    ]

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4G-0",
        "policy_id": policy["policy_id"],
        "design_package_id": (
            "wp-read-only-category-lookup-design"
        ),
        "operation_mode": (
            "READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY"
        ),
        "credential_preflight_state": {
            "presence_verified": True,
            "metadata_verified": True,
            "structure_verified": True,
            "credential_values_loaded": False,
            "credential_values_output": False,
        },
        "http_contract": {
            "allowed_method": "GET",
            "allowed_rest_path": (
                "/wp-json/wp/v2/categories"
            ),
            "request_body_allowed": False,
            "redirect_follow_allowed": False,
            "tls_verification_required": True,
            "write_methods_allowed": False,
        },
        "lookup_plan_count": len(plans),
        "lookup_plans": plans,
        "current_phase_activity": {
            "credential_file_read": False,
            "environment_variable_read": False,
            "dns_resolution": False,
            "tls_connection": False,
            "http_request": False,
            "wordpress_response_read": False,
            "wordpress_write": False,
        },
        "preexecution_gate": {
            "state": "BLOCKED_LOOKUP_DESIGN_ONLY",
            "implementation_required": True,
            "explicit_lookup_authorization_required": True,
            "network_authority_granted": False,
            "wordpress_read_authority_granted": False,
            "wordpress_write_authority_granted": False,
            "execution_approval_issued": False,
            "approval_token": None,
            "execution_allowed": False,
        },
        "execution_boundary": {
            "credential_value_output_allowed": False,
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
                "READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY"
            ),
        },
        "verified_checks": source_checks,
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
    activity = package["current_phase_activity"]
    gate = package["preexecution_gate"]

    return {
        "phase_id": "LS-NEW-BATCH-4G-0",
        "status": (
            "PASS_READ_ONLY_CATEGORY_LOOKUP_"
            "DESIGN_NO_NETWORK"
        ),
        "decision": (
            "GET_ONLY_CATEGORY_LOOKUP_CONTRACT_READY"
        ),
        "policy_id": package["policy_id"],
        "design_package_id": package[
            "design_package_id"
        ],
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "operation_mode": package["operation_mode"],
        "lookup_plan_count": package[
            "lookup_plan_count"
        ],
        "http_method": "GET",
        "rest_path": "/wp-json/wp/v2/categories",
        "credential_preflight_passed": True,
        "credential_values_loaded": False,
        "credential_values_output": False,
        "credential_file_read": activity[
            "credential_file_read"
        ],
        "dns_resolution_performed": activity[
            "dns_resolution"
        ],
        "tls_connection_performed": activity[
            "tls_connection"
        ],
        "http_request_performed": activity[
            "http_request"
        ],
        "wordpress_response_read": activity[
            "wordpress_response_read"
        ],
        "wordpress_write_performed": activity[
            "wordpress_write"
        ],
        "preexecution_gate_state": gate["state"],
        "network_authority_granted": gate[
            "network_authority_granted"
        ],
        "wordpress_read_authority_granted": gate[
            "wordpress_read_authority_granted"
        ],
        "wordpress_write_authority_granted": gate[
            "wordpress_write_authority_granted"
        ],
        "design_package_digest_sha256": package[
            "design_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "request_identity",
                "credential_path_contract",
                "get_method_lock",
                "category_rest_path_lock",
                "query_parameter_lock",
                "request_body_absence",
                "redirect_follow_disabled",
                "tls_verification_required",
                "target_category_exact_match",
                "lookup_plan_generation",
                "lookup_plan_digest_generation",
                "credential_file_unread",
                "network_unaccessed",
                "wordpress_unaccessed",
                "wordpress_write_forbidden",
                "design_package_digest_generation",
                "execution_gate_closed",
            ]
        ),
        "credential_value_output_allowed": False,
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
            "READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY"
        ),
        "ready_for_ls_new_batch_4g_1": True,
        "ready_for_lookup_implementation": True,
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

    return f"""# LS-NEW-BATCH-4G-0 Read-Only Category Lookup Design Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Design package: `{result["design_package_id"]}`
- Lookup plans: `{result["lookup_plan_count"]}`

## HTTP Contract

- Method: `GET`
- REST path: `/wp-json/wp/v2/categories`
- Request body allowed: `false`
- Redirect following allowed: `false`
- TLS verification required: `true`

## Credential State

- Credential preflight passed: `true`
- Credential values loaded: `false`
- Credential values output: `false`
- Credential file read in this phase: `false`

## Network and WordPress State

- DNS resolution performed: `false`
- TLS connection performed: `false`
- HTTP request performed: `false`
- WordPress response read: `false`
- WordPress write performed: `false`

## Gate State

- Pre-execution gate: `{result["preexecution_gate_state"]}`
- Network authority granted: `false`
- WordPress read authority granted: `false`
- WordPress write authority granted: `false`
- Execution allowed: `false`

## Verified Checks

{checks}

## Safety Boundary

- Credential-value output allowed: `false`
- DNS resolution allowed: `false`
- Network connection allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `READ_ONLY_CATEGORY_LOOKUP_DESIGN_ONLY`

## Next State

WordPressカテゴリ取得のGET専用HTTP契約、対象カテゴリ、
一致条件、失敗時ブロック条件を固定しました。

認証ファイル読み込み、DNS、TLS、HTTP通信、WordPress応答取得は
まだ行っていません。

次の `LS-NEW-BATCH-4G-1` で、実通信を行わない実装本体と
モック応答による照合テストを構築します。
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
            "phase_id": "LS-NEW-BATCH-4G-0",
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "credential_values_loaded": False,
            "credential_values_output": False,
            "dns_resolution_performed": False,
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
