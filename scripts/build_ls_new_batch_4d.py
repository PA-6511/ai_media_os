#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_read_only_category_discovery_policy.json"
)
DEFAULT_SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_preexecution_package.example.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_discovery_request.example.json"
)
DEFAULT_CATALOG_PATH = (
    ROOT
    / "exchange/examples/"
    "wordpress_category_catalog.fixture.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_discovery_result.example.json"
)

RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4d_result.json"
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4d_read_only_category_discovery_report.md"
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


def parse_datetime(
    value: Any,
    *,
    field_name: str,
) -> str:
    normalized = normalize_text(
        value,
        field_name=field_name,
        required=True,
    )
    assert normalized is not None

    candidate = (
        normalized[:-1] + "+00:00"
        if normalized.endswith("Z")
        else normalized
    )

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO 8601 datetime"
        ) from exc

    require(
        parsed.tzinfo is not None,
        f"{field_name} must include a timezone offset",
    )

    return normalized


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-4D",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_READ_ONLY_CATEGORY_DISCOVERY_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    discovery = policy.get("discovery", {})

    require(
        discovery.get("current_allowed_mode")
        == "LOCAL_FIXTURE_ONLY",
        "current discovery mode must be LOCAL_FIXTURE_ONLY",
    )
    require(
        discovery.get("exact_slug_match_required") is True,
        "exact slug matching must be required",
    )
    require(
        discovery.get("exact_name_match_required") is True,
        "exact name matching must be required",
    )
    checks.append("discovery_rules")

    fixture_rules = policy.get("fixture_rules", {})

    require(
        fixture_rules.get("production_usable") is False,
        "fixture results must not be production usable",
    )
    require(
        fixture_rules.get("payload_injection_allowed") is False,
        "fixture IDs must not be injected into payloads",
    )
    checks.append("fixture_isolation_rules")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "credential_read_allowed",
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
        == "READ_ONLY_DISCOVERY_DESIGN_ONLY",
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
        "preexecution_package_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source pre-execution digest is invalid",
    )

    source_without_digest = copy.deepcopy(source)
    source_without_digest.pop(
        "preexecution_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_digest,
        "source pre-execution digest verification failed",
    )

    resolution = source.get(
        "production_category_resolution",
        {},
    )
    gate = source.get("preexecution_gate", {})

    require(
        resolution.get("state")
        == "PENDING_MANUAL_VERIFICATION",
        "source category resolution state mismatch",
    )
    require(
        resolution.get("example_category_ids_removed") is True,
        "example category IDs must already be removed",
    )
    require(
        resolution.get("production_category_ids_present")
        is False,
        "production category IDs must remain absent",
    )
    require(
        gate.get("state")
        == "BLOCKED_PENDING_PRODUCTION_CATEGORY_RESOLUTION",
        "source pre-execution gate mismatch",
    )
    require(
        gate.get("execution_allowed") is False,
        "source execution must remain blocked",
    )

    items = source.get("items")

    require(
        isinstance(items, list) and len(items) >= 1,
        "source must contain at least one item",
    )

    for item in items:
        item_id = item.get("item_id")
        draft_payload = item.get("draft_payload")

        require(
            isinstance(item_id, str),
            "source item_id must be a string",
        )
        require(
            isinstance(draft_payload, dict),
            f"{item_id}: draft_payload must be an object",
        )
        require(
            canonical_digest(draft_payload)
            == item.get(
                "production_pending_payload_digest_sha256"
            ),
            f"{item_id}: pending payload digest "
            "verification failed",
        )

        category = draft_payload.get("category")

        require(
            isinstance(category, dict),
            f"{item_id}: category must be an object",
        )
        require(
            category.get("wordpress_category_id") is None,
            f"{item_id}: production category ID must be null",
        )
        require(
            category.get("resolution_state")
            == "PENDING_PRODUCTION_MANUAL_VERIFICATION",
            f"{item_id}: category state mismatch",
        )
        require(
            category.get("production_usable") is False,
            f"{item_id}: category must not be production usable",
        )
        require(
            item.get("execution_allowed") is False,
            f"{item_id}: execution must remain blocked",
        )

    return [
        "source_phase_identity",
        "source_preexecution_digest_verified",
        "source_pending_payload_digests_verified",
        "source_category_ids_absent",
        "source_preexecution_gate_closed",
    ]


def validate_request(
    request: dict[str, Any],
    source: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, str]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4D",
        "request phase_id mismatch",
    )
    require(
        request.get("preexecution_package_id")
        == source.get("preexecution_package_id"),
        "request preexecution_package_id mismatch",
    )
    require(
        request.get("batch_id") == source.get("batch_id"),
        "request batch_id mismatch",
    )
    require(
        request.get(
            "source_preexecution_package_digest_sha256"
        )
        == source.get("preexecution_package_digest_sha256"),
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
        request.get("discovery_mode")
        == policy["discovery"]["current_allowed_mode"],
        "discovery_mode must be LOCAL_FIXTURE_ONLY",
    )
    require(
        request.get("production_lookup_requested") is False,
        "production lookup must remain false",
    )
    require(
        request.get("credential_access_requested") is False,
        "credential access must remain false",
    )
    require(
        request.get("wordpress_access_requested") is False,
        "WordPress access must remain false",
    )

    expected_categories = request.get("expected_categories")

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
        item["draft_payload"]["category"]["slug"]:
        item["draft_payload"]["category"]["name"]
        for item in source["items"]
    }

    require(
        requested == source_categories,
        "requested categories must exactly match "
        "source categories",
    )

    return requested


def validate_catalog(
    catalog: dict[str, Any],
    expected_categories: dict[str, str],
    policy: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    require(
        catalog.get("phase_id") == "LS-NEW-BATCH-4D",
        "catalog phase_id mismatch",
    )

    fixture_rules = policy["fixture_rules"]

    require(
        catalog.get("source_type")
        == fixture_rules["source_type"],
        "catalog source_type mismatch",
    )
    require(
        catalog.get("site_identity")
        == fixture_rules["site_identity"],
        "catalog site identity mismatch",
    )
    require(
        catalog.get("production_usable") is False,
        "catalog must not be production usable",
    )

    parse_datetime(
        catalog.get("fetched_at"),
        field_name="catalog.fetched_at",
    )

    categories = catalog.get("categories")

    require(
        isinstance(categories, list)
        and len(categories) >= 1,
        "catalog categories must be non-empty",
    )

    catalog_by_slug: dict[str, list[dict[str, Any]]] = {}

    for index, category in enumerate(categories, start=1):
        require(
            isinstance(category, dict),
            f"catalog.categories[{index}] must be an object",
        )

        category_id = category.get(
            "wordpress_category_id"
        )

        require(
            isinstance(category_id, int)
            and not isinstance(category_id, bool),
            "fixture category ID must be an integer",
        )
        require(
            fixture_rules["minimum_reserved_category_id"]
            <= category_id
            <= fixture_rules["maximum_reserved_category_id"],
            "fixture category ID is outside reserved range",
        )

        slug = normalize_text(
            category.get("category_slug"),
            field_name=(
                f"catalog.categories[{index}].category_slug"
            ),
            required=True,
        )
        name = normalize_text(
            category.get("category_name"),
            field_name=(
                f"catalog.categories[{index}].category_name"
            ),
            required=True,
        )

        assert slug is not None
        assert name is not None

        post_count = category.get("post_count")

        require(
            isinstance(post_count, int)
            and not isinstance(post_count, bool)
            and post_count >= 0,
            f"{slug}: post_count must be non-negative",
        )

        catalog_by_slug.setdefault(slug, []).append(
            {
                "wordpress_category_id": category_id,
                "category_slug": slug,
                "category_name": name,
                "post_count": post_count,
            }
        )

    matches: dict[str, dict[str, Any]] = {}

    for slug, expected_name in expected_categories.items():
        candidates = catalog_by_slug.get(slug, [])

        require(
            len(candidates) >= 1,
            f"category fixture match not found: {slug}",
        )
        require(
            len(candidates) == 1,
            f"duplicate category fixture matches: {slug}",
        )

        candidate = candidates[0]

        require(
            candidate["category_name"] == expected_name,
            f"{slug}: fixture category name mismatch",
        )

        matches[slug] = candidate

    return matches


def build_package(
    source: dict[str, Any],
    request: dict[str, Any],
    catalog: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source(source, policy)
    expected_categories = validate_request(
        request,
        source,
        policy,
    )
    matches = validate_catalog(
        catalog,
        expected_categories,
        policy,
    )

    discovery_results = []

    for slug, expected_name in sorted(
        expected_categories.items()
    ):
        match = matches[slug]

        discovery_results.append(
            {
                "category_slug": slug,
                "category_name": expected_name,
                "match_state": "MATCHED_FIXTURE_ONLY",
                "candidate_fixture_category_id": match[
                    "wordpress_category_id"
                ],
                "fixture_post_count": match["post_count"],
                "discovery_source": "LOCAL_FIXTURE",
                "production_usable": False,
                "payload_injection_allowed": False,
                "human_verification_required": True
            }
        )

    item_links = []

    for item in source["items"]:
        category = item["draft_payload"]["category"]
        match = matches[category["slug"]]

        item_links.append(
            {
                "item_id": item["item_id"],
                "category_slug": category["slug"],
                "category_name": category["name"],
                "source_wordpress_category_id": None,
                "candidate_fixture_category_id": match[
                    "wordpress_category_id"
                ],
                "candidate_state": "FIXTURE_ONLY_NOT_APPLIED",
                "source_pending_payload_digest_sha256": item[
                    "production_pending_payload_digest_sha256"
                ],
                "production_payload_modified": False,
                "production_usable": False,
                "execution_allowed": False
            }
        )

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4D",
        "policy_id": policy["policy_id"],
        "discovery_package_id": (
            f"wp-category-discovery-{source['batch_id']}"
        ),
        "source_preexecution_package_id": source[
            "preexecution_package_id"
        ],
        "batch_id": source["batch_id"],
        "template_contract_id": source[
            "template_contract_id"
        ],
        "source_preexecution_package_digest_sha256": source[
            "preexecution_package_digest_sha256"
        ],
        "discovery_mode": "LOCAL_FIXTURE_ONLY",
        "catalog_identity": {
            "source_type": catalog["source_type"],
            "site_identity": catalog["site_identity"],
            "fetched_at": catalog["fetched_at"],
            "production_usable": False
        },
        "discovery_summary": {
            "expected_category_count": len(
                expected_categories
            ),
            "matched_category_count": len(matches),
            "all_categories_matched": (
                len(expected_categories) == len(matches)
            ),
            "production_category_ids_present": False,
            "production_category_ids_usable": False,
            "fixture_candidates_present": True,
            "fixture_candidates_applied_to_payload": False
        },
        "discovery_results": discovery_results,
        "item_discovery_links": item_links,
        "preexecution_gate": {
            "state": (
                "BLOCKED_FIXTURE_DISCOVERY_NOT_PRODUCTION"
            ),
            "read_only_design_verified": True,
            "production_read_only_lookup_completed": False,
            "production_category_resolution_completed": False,
            "execution_approval_issued": False,
            "approval_token": None,
            "execution_allowed": False
        },
        "execution_boundary": {
            "credential_read_allowed": False,
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
            "safety_state": "READ_ONLY_DISCOVERY_DESIGN_ONLY"
        },
        "verified_checks": source_checks
    }

    output = copy.deepcopy(package_without_digest)
    output["discovery_package_digest_sha256"] = (
        canonical_digest(package_without_digest)
    )

    return output


def build_result(
    package: dict[str, Any],
    *,
    source_path: Path,
    request_path: Path,
    catalog_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    summary = package["discovery_summary"]
    gate = package["preexecution_gate"]

    return {
        "phase_id": "LS-NEW-BATCH-4D",
        "status": (
            "PASS_READ_ONLY_CATEGORY_DISCOVERY_DESIGN_"
            "NO_WORDPRESS_ACCESS"
        ),
        "decision": (
            "LOCAL_FIXTURE_DISCOVERY_VERIFIED_"
            "PRODUCTION_LOOKUP_PENDING"
        ),
        "policy_id": package["policy_id"],
        "discovery_package_id": package[
            "discovery_package_id"
        ],
        "source_preexecution_package_id": package[
            "source_preexecution_package_id"
        ],
        "batch_id": package["batch_id"],
        "source_path": display_path(source_path),
        "request_path": display_path(request_path),
        "catalog_path": display_path(catalog_path),
        "output_path": display_path(output_path),
        "discovery_mode": package["discovery_mode"],
        "expected_category_count": summary[
            "expected_category_count"
        ],
        "matched_category_count": summary[
            "matched_category_count"
        ],
        "all_categories_matched": summary[
            "all_categories_matched"
        ],
        "fixture_candidates_present": summary[
            "fixture_candidates_present"
        ],
        "fixture_candidates_applied_to_payload": summary[
            "fixture_candidates_applied_to_payload"
        ],
        "production_category_ids_present": False,
        "production_category_ids_usable": False,
        "preexecution_gate_state": gate["state"],
        "execution_approval_issued": False,
        "approval_token_present": False,
        "discovery_package_digest_sha256": package[
            "discovery_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "discovery_request_identity",
                "requested_categories_exact_match",
                "fixture_source_identity",
                "fixture_timestamp_validation",
                "fixture_category_id_reserved_range",
                "category_slug_exact_match",
                "category_name_exact_match",
                "one_match_per_category",
                "fixture_candidate_isolation",
                "production_payload_not_modified",
                "discovery_package_digest_generation",
                "source_package_not_mutated",
                "execution_gate_closed"
            ]
        ),
        "credential_read_allowed": False,
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
        "safety_state": "READ_ONLY_DISCOVERY_DESIGN_ONLY",
        "ready_for_credential_isolated_read_only_preflight": True,
        "ready_for_ls_new_batch_4e": True,
        "ready_for_production_category_resolution": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4D Read-Only Category Discovery Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Package: `{result["discovery_package_id"]}`
- Batch: `{result["batch_id"]}`
- Discovery mode: `{result["discovery_mode"]}`

## Discovery Summary

- Expected categories: `{result["expected_category_count"]}`
- Matched categories: `{result["matched_category_count"]}`
- All categories matched: `{str(result["all_categories_matched"]).lower()}`
- Fixture candidates present: `{str(result["fixture_candidates_present"]).lower()}`
- Fixture candidates applied to payload: `false`
- Production category IDs present: `false`
- Production category IDs usable: `false`

## Execution State

- Pre-execution gate: `{result["preexecution_gate_state"]}`
- Execution approval issued: `false`
- Approval token present: `false`
- Ready for execution: `false`

## Integrity

- Discovery package digest: `{result["discovery_package_digest_sha256"]}`

## Verified Checks

{checks}

## Safety Boundary

- Credential read allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress database read allowed: `false`
- WordPress database write allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X posting allowed: `false`
- External API call allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `READ_ONLY_DISCOVERY_DESIGN_ONLY`

## Next State

ローカルフィクスチャを使用したカテゴリ探索・完全一致照合・
重複防止・候補隔離の設計検証が完了しました。

フィクスチャカテゴリIDは候補情報としてのみ保存され、
WordPress下書きペイロードには注入されていません。

次の `LS-NEW-BATCH-4E` では、認証情報を分離した読み取り専用
カテゴリ検索の事前条件を設計できます。実WordPress通信は
まだ許可されていません。
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
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
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
    catalog_path = resolve_path(args.catalog)
    output_path = resolve_path(args.output)

    try:
        policy = load_json(POLICY_PATH)
        source = load_json(source_path)
        request = load_json(request_path)
        catalog = load_json(catalog_path)

        policy_checks = validate_policy(policy)
        original_source = copy.deepcopy(source)

        package = build_package(
            source=source,
            request=request,
            catalog=catalog,
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
            catalog_path=catalog_path,
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
                    "phase_id": "LS-NEW-BATCH-4D",
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
