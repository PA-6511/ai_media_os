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
    "new_release_wp_production_category_preexecution_policy.json"
)
DEFAULT_SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_human_review_decision_package.example.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_resolution_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_preexecution_package.example.json"
)

RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4c_result.json"
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4c_production_category_preexecution_report.md"
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


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-4C",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_PRODUCTION_CATEGORY_PREEXECUTION_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    category_rules = policy.get(
        "production_category_request",
        {},
    )

    require(
        category_rules.get(
            "wordpress_category_id_must_begin_null"
        )
        is True,
        "category ID must begin null",
    )
    require(
        category_rules.get(
            "example_category_id_reuse_forbidden"
        )
        is True,
        "example category ID reuse must be forbidden",
    )
    checks.append("production_category_request_rules")

    gate = policy.get("preexecution_gate", {})

    require(
        gate.get("state")
        == "BLOCKED_PENDING_PRODUCTION_CATEGORY_RESOLUTION",
        "pre-execution gate state mismatch",
    )
    require(
        gate.get("execution_approval_issued") is False,
        "execution approval must remain false",
    )
    require(
        gate.get("approval_token_generation_allowed") is False,
        "approval-token generation must remain blocked",
    )
    require(
        gate.get("execution_allowed") is False,
        "execution must remain blocked",
    )
    checks.append("preexecution_gate")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "credential_read_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_database_read_allowed",
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
        == "PRODUCTION_CATEGORY_RESOLUTION_PENDING",
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source(
    source: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    requirements = policy["source_requirements"]

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
        "review_package_digest_sha256"
    )

    require(
        isinstance(expected_digest, str)
        and len(expected_digest) == 64,
        "source review package digest is invalid",
    )

    source_without_digest = copy.deepcopy(source)
    source_without_digest.pop(
        "review_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_digest,
        "source review package digest verification failed",
    )

    review = source.get("human_review", {})

    require(
        review.get("state")
        == requirements["human_review_state"],
        "source human-review state mismatch",
    )
    require(
        review.get("human_review_approval_recorded")
        == requirements["human_review_approval_recorded"],
        "source human-review approval mismatch",
    )
    require(
        review.get("effective_outcome")
        == requirements["required_effective_outcome"],
        "source effective outcome mismatch",
    )
    require(
        source.get("resolution_mode")
        == requirements["source_resolution_mode"],
        "source resolution mode mismatch",
    )
    require(
        source.get("category_ids_production_usable")
        == requirements[
            "source_category_ids_production_usable"
        ],
        "source category production usability mismatch",
    )
    require(
        review.get("execution_allowed")
        == requirements["source_execution_allowed"],
        "source execution state mismatch",
    )
    require(
        review.get("execution_approval_issued") is False,
        "source execution approval must be false",
    )
    require(
        review.get("approval_token") is None,
        "source approval token must be absent",
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
            == item.get("resolved_payload_digest_sha256"),
            f"{item_id}: resolved payload digest "
            "verification failed",
        )

        category = draft_payload.get("category")

        require(
            isinstance(category, dict),
            f"{item_id}: category must be an object",
        )
        require(
            category.get("resolution_state")
            == "RESOLVED_EXAMPLE_ONLY",
            f"{item_id}: source category must be example-only",
        )
        require(
            category.get("production_usable") is False,
            f"{item_id}: source category must not be "
            "production usable",
        )
        require(
            item.get("execution_allowed") is False,
            f"{item_id}: execution must remain blocked",
        )

    return [
        "source_phase_identity",
        "source_review_package_digest_verified",
        "source_human_review_approval_verified",
        "source_example_resolution_verified",
        "source_resolved_payload_digests_verified",
        "source_execution_gate_closed",
    ]


def validate_request(
    request: dict[str, Any],
    source: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4C",
        "request phase_id mismatch",
    )
    require(
        request.get("review_package_id")
        == source.get("review_package_id"),
        "request review_package_id mismatch",
    )
    require(
        request.get("batch_id") == source.get("batch_id"),
        "request batch_id mismatch",
    )
    require(
        request.get(
            "source_review_package_digest_sha256"
        )
        == source.get("review_package_digest_sha256"),
        "request source package digest mismatch",
    )

    version = request.get("request_version")

    require(
        isinstance(version, int)
        and not isinstance(version, bool)
        and version >= 1,
        "request_version must be positive",
    )

    rules = policy["production_category_request"]

    require(
        request.get("resolution_status")
        == rules["required_status"],
        "resolution_status mismatch",
    )
    require(
        request.get("execution_approval_issued") is False,
        "execution approval must remain false",
    )
    require(
        request.get("approval_token") is None,
        "approval token must remain null",
    )

    categories = request.get("categories")

    require(
        isinstance(categories, list)
        and len(categories) >= 1,
        "categories must be a non-empty list",
    )

    category_map: dict[str, dict[str, Any]] = {}

    for index, category in enumerate(categories, start=1):
        require(
            isinstance(category, dict),
            f"categories[{index}] must be an object",
        )

        slug = normalize_text(
            category.get("category_slug"),
            field_name=f"categories[{index}].category_slug",
            required=True,
        )
        name = normalize_text(
            category.get("category_name"),
            field_name=f"categories[{index}].category_name",
            required=True,
        )

        assert slug is not None
        assert name is not None

        require(
            slug not in category_map,
            f"duplicate category request: {slug}",
        )
        require(
            category.get("wordpress_category_id") is None,
            f"{slug}: WordPress category ID must begin null",
        )
        require(
            category.get("resolution_source") is None,
            f"{slug}: resolution_source must begin null",
        )
        require(
            category.get("verified_at") is None,
            f"{slug}: verified_at must begin null",
        )
        require(
            category.get("evidence_note") is None,
            f"{slug}: evidence_note must begin null",
        )
        require(
            category.get("human_verification_confirmed")
            is False,
            f"{slug}: human verification must begin false",
        )

        category_map[slug] = {
            "category_slug": slug,
            "category_name": name,
        }

    source_categories = {
        item["draft_payload"]["category"]["slug"]:
        item["draft_payload"]["category"]["name"]
        for item in source["items"]
    }

    require(
        set(category_map) == set(source_categories),
        "request must contain exactly every source category",
    )

    for slug, expected_name in source_categories.items():
        require(
            category_map[slug]["category_name"]
            == expected_name,
            f"{slug}: category name mismatch",
        )

    return category_map


def build_package(
    source: dict[str, Any],
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source(source, policy)
    category_map = validate_request(
        request,
        source,
        policy,
    )

    pending_items: list[dict[str, Any]] = []

    for source_item in source["items"]:
        item = copy.deepcopy(source_item)
        category = item["draft_payload"]["category"]
        slug = category["slug"]

        require(
            slug in category_map,
            f"{item['item_id']}: category request missing",
        )

        category.pop("resolution_source", None)
        category.pop("resolution_verified_at", None)
        category.pop("resolution_evidence_note", None)

        category["wordpress_category_id"] = None
        category["resolution_state"] = (
            "PENDING_PRODUCTION_MANUAL_VERIFICATION"
        )
        category["resolution_source"] = None
        category["production_resolution_verified_at"] = None
        category["production_resolution_evidence_note"] = None
        category["human_verification_confirmed"] = False
        category["production_usable"] = False
        category["source_example_category_id_removed"] = True

        item["production_pending_payload_digest_sha256"] = (
            canonical_digest(item["draft_payload"])
        )
        item["production_category_resolution_status"] = (
            "PENDING_MANUAL_VERIFICATION"
        )
        item["production_category_review_required"] = True
        item["execution_approval_issued"] = False
        item["approval_token"] = None
        item["credential_read_allowed"] = False
        item["wordpress_api_call_allowed"] = False
        item["wordpress_write_allowed"] = False
        item["execution_allowed"] = False

        pending_items.append(item)

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4C",
        "policy_id": policy["policy_id"],
        "preexecution_package_id": (
            f"wp-production-category-pending-"
            f"{source['batch_id']}"
        ),
        "source_review_package_id": source[
            "review_package_id"
        ],
        "batch_id": source["batch_id"],
        "template_contract_id": source[
            "template_contract_id"
        ],
        "source_review_package_digest_sha256": source[
            "review_package_digest_sha256"
        ],
        "content_human_review": {
            "state": "COMPLETED",
            "approval_recorded": True,
            "source_review_label": source[
                "human_review"
            ]["review_label"]
        },
        "production_category_resolution": {
            "state": "PENDING_MANUAL_VERIFICATION",
            "category_count": len(category_map),
            "example_category_ids_removed": True,
            "production_category_ids_present": False,
            "human_verification_completed": False,
            "production_usable": False
        },
        "item_count": len(pending_items),
        "items": pending_items,
        "preexecution_gate": {
            "state": (
                "BLOCKED_PENDING_PRODUCTION_CATEGORY_RESOLUTION"
            ),
            "content_review_recorded": True,
            "production_category_resolution_required": True,
            "production_category_review_required": True,
            "execution_approval_issued": False,
            "approval_token": None,
            "execution_allowed": False
        },
        "execution_boundary": {
            "credential_read_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_category_lookup_allowed": False,
            "wordpress_database_read_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_post_allowed": False,
            "external_api_call_allowed": False,
            "execution_approval_issued": False,
            "approval_token_present": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "PRODUCTION_CATEGORY_RESOLUTION_PENDING"
            )
        },
        "verified_checks": source_checks
    }

    output = copy.deepcopy(package_without_digest)
    output["preexecution_package_digest_sha256"] = (
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
    resolution = package[
        "production_category_resolution"
    ]

    return {
        "phase_id": "LS-NEW-BATCH-4C",
        "status": (
            "PASS_PRODUCTION_CATEGORY_REQUEST_"
            "PREPARED_NO_WORDPRESS_ACCESS"
        ),
        "decision": (
            "EXAMPLE_CATEGORY_REMOVED_"
            "PRODUCTION_RESOLUTION_PENDING"
        ),
        "policy_id": package["policy_id"],
        "preexecution_package_id": package[
            "preexecution_package_id"
        ],
        "source_review_package_id": package[
            "source_review_package_id"
        ],
        "batch_id": package["batch_id"],
        "source_path": display_path(source_path),
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "item_count": package["item_count"],
        "content_human_review_recorded": True,
        "example_category_ids_removed": resolution[
            "example_category_ids_removed"
        ],
        "production_category_ids_present": resolution[
            "production_category_ids_present"
        ],
        "production_category_resolution_state": resolution[
            "state"
        ],
        "production_category_ids_usable": False,
        "execution_approval_issued": False,
        "approval_token_present": False,
        "preexecution_gate_state": package[
            "preexecution_gate"
        ]["state"],
        "preexecution_package_digest_sha256": package[
            "preexecution_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "production_category_request_identity",
                "category_slug_exact_match",
                "category_name_exact_match",
                "pending_null_category_id_enforced",
                "example_category_id_removed",
                "production_pending_payload_digest_generation",
                "preexecution_package_digest_generation",
                "source_package_not_mutated",
                "approval_token_absence",
                "execution_gate_closed"
            ]
        ),
        "credential_read_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_database_read_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "x_post_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CATEGORY_RESOLUTION_PENDING"
        ),
        "ready_for_read_only_category_discovery_design": True,
        "ready_for_ls_new_batch_4d": True,
        "ready_for_production_pre_execution": False,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4C Production Category Pre-Execution Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Package: `{result["preexecution_package_id"]}`
- Batch: `{result["batch_id"]}`
- Items: `{result["item_count"]}`

## Category State

- Content human review recorded: `true`
- Example category IDs removed: `{str(result["example_category_ids_removed"]).lower()}`
- Production category IDs present: `{str(result["production_category_ids_present"]).lower()}`
- Production category resolution: `{result["production_category_resolution_state"]}`
- Production category IDs usable: `false`

## Execution State

- Pre-execution gate: `{result["preexecution_gate_state"]}`
- Execution approval issued: `false`
- Approval token present: `false`
- Ready for execution: `false`

## Integrity

- Package digest: `{result["preexecution_package_digest_sha256"]}`

## Verified Checks

{checks}

## Safety Boundary

- Credential read allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress database read allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X posting allowed: `false`
- External API call allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `PRODUCTION_CATEGORY_RESOLUTION_PENDING`

## Next State

試験用カテゴリIDを本番候補ペイロードから除去し、
実WordPressカテゴリIDの手動確認要求を準備しました。

次の `LS-NEW-BATCH-4D` では、WordPressカテゴリを読み取り専用で
確認する仕組みを設計できます。現段階ではWordPressへの接続、
データベース読み取り、認証情報読み込み、下書き作成は行いません。
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
                    "phase_id": "LS-NEW-BATCH-4C",
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
