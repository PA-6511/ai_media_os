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
    "new_release_wp_category_review_gate_policy.json"
)
DEFAULT_PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_draft_preparation.example.json"
)
DEFAULT_CATEGORY_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_resolution_request.example.json"
)
DEFAULT_REVIEW_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_human_review_gate_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_review_gate_package.example.json"
)

RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4a_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4a_category_review_gate_report.md"
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
    required: bool,
) -> str | None:
    normalized = normalize_text(
        value,
        field_name=field_name,
        required=required,
    )

    if normalized is None:
        return None

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
        policy.get("phase_id") == "LS-NEW-BATCH-4A",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_CATEGORY_REVIEW_GATE_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    category_policy = policy.get(
        "category_resolution",
        {}
    )

    require(
        category_policy.get("required") is True,
        "category resolution must be required",
    )
    require(
        category_policy.get(
            "one_resolution_per_category_slug"
        )
        is True,
        "one resolution per category slug must be required",
    )
    checks.append("category_resolution_policy")

    review_policy = policy.get("human_review_gate", {})

    require(
        review_policy.get("initial_review_status")
        == "NOT_REVIEWED",
        "review gate must begin as NOT_REVIEWED",
    )
    require(
        review_policy.get("initial_item_decision")
        == "PENDING",
        "item review must begin as PENDING",
    )
    require(
        review_policy.get(
            "approval_label_generation_allowed"
        )
        is False,
        "approval-label generation must remain blocked",
    )
    require(
        review_policy.get(
            "approval_token_generation_allowed"
        )
        is False,
        "approval-token generation must remain blocked",
    )
    checks.append("human_review_gate_policy")

    boundary = policy.get("execution_boundary", {})

    for field in [
        "credential_read_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "x_api_call_allowed",
        "x_post_allowed",
        "external_api_call_allowed",
        "human_approval_issued",
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
        == "CATEGORY_RESOLUTION_AND_REVIEW_PREP_ONLY",
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source_integrity(
    package: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    require(
        package.get("phase_id")
        == policy.get("source_phase_id"),
        "source package phase mismatch",
    )
    require(
        package.get("template_contract_id")
        == policy.get("template_contract_id"),
        "template contract mismatch",
    )

    expected_batch_digest = package.get(
        "batch_digest_sha256"
    )

    require(
        isinstance(expected_batch_digest, str)
        and len(expected_batch_digest) == 64,
        "source batch digest is invalid",
    )

    package_without_digest = copy.deepcopy(package)
    package_without_digest.pop(
        "batch_digest_sha256",
        None,
    )

    actual_batch_digest = canonical_digest(
        package_without_digest
    )

    require(
        actual_batch_digest == expected_batch_digest,
        "source batch digest verification failed",
    )

    items = package.get("items")

    require(
        isinstance(items, list) and len(items) >= 1,
        "source package must contain at least one item",
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

        expected_payload_digest = item.get(
            "payload_digest_sha256"
        )

        require(
            canonical_digest(draft_payload)
            == expected_payload_digest,
            f"{item_id}: payload digest verification failed",
        )

        category = draft_payload.get("category")

        require(
            isinstance(category, dict),
            f"{item_id}: category must be an object",
        )
        require(
            category.get("wordpress_category_id") is None,
            f"{item_id}: source category ID must remain unresolved",
        )
        require(
            category.get("resolution_state")
            == "PENDING_ID_LOOKUP",
            f"{item_id}: source category state mismatch",
        )

    return [
        "source_phase_identity",
        "source_batch_digest_verified",
        "source_item_payload_digests_verified",
        "source_category_ids_unresolved",
    ]


def validate_category_request(
    request: dict[str, Any],
    package: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], bool]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4A",
        "category request phase mismatch",
    )
    require(
        request.get("package_id") == package.get("package_id"),
        "category request package_id mismatch",
    )
    require(
        request.get("batch_id") == package.get("batch_id"),
        "category request batch_id mismatch",
    )

    request_version = request.get("request_version")

    require(
        isinstance(request_version, int)
        and not isinstance(request_version, bool)
        and request_version >= 1,
        "category request_version must be positive",
    )

    category_policy = policy["category_resolution"]
    mode = request.get("resolution_mode")

    require(
        mode in category_policy[
            "allowed_resolution_modes"
        ],
        f"unsupported resolution_mode: {mode}",
    )

    resolutions = request.get("resolutions")

    require(
        isinstance(resolutions, list)
        and len(resolutions) >= 1,
        "category resolutions must be a non-empty list",
    )

    resolution_map: dict[str, dict[str, Any]] = {}

    for index, resolution in enumerate(
        resolutions,
        start=1,
    ):
        require(
            isinstance(resolution, dict),
            f"resolution[{index}] must be an object",
        )

        slug = normalize_text(
            resolution.get("category_slug"),
            field_name=(
                f"resolution[{index}].category_slug"
            ),
            required=True,
        )
        name = normalize_text(
            resolution.get("category_name"),
            field_name=(
                f"resolution[{index}].category_name"
            ),
            required=True,
        )
        source = normalize_text(
            resolution.get("resolution_source"),
            field_name=(
                f"resolution[{index}].resolution_source"
            ),
            required=True,
        )

        assert slug is not None
        assert name is not None
        assert source is not None

        require(
            slug not in resolution_map,
            f"duplicate category resolution: {slug}",
        )

        category_id = resolution.get(
            "wordpress_category_id"
        )

        require(
            isinstance(category_id, int)
            and not isinstance(category_id, bool)
            and category_id > 0,
            f"{slug}: category ID must be a positive integer",
        )

        verified_at = parse_datetime(
            resolution.get("verified_at"),
            field_name=f"{slug}.verified_at",
            required=True,
        )
        evidence_note = normalize_text(
            resolution.get("evidence_note"),
            field_name=f"{slug}.evidence_note",
            required=True,
        )

        if mode == "EXAMPLE_ONLY":
            example_policy = category_policy[
                "example_mode"
            ]

            require(
                source
                == example_policy["required_source"],
                "EXAMPLE_ONLY requires EXAMPLE_FIXTURE source",
            )
            require(
                example_policy["minimum_category_id"]
                <= category_id
                <= example_policy["maximum_category_id"],
                "example category ID is outside reserved range",
            )

            production_usable = False
            resolution_state = "RESOLVED_EXAMPLE_ONLY"

        else:
            production_policy = category_policy[
                "production_manual_mode"
            ]

            require(
                source
                == production_policy["required_source"],
                "production manual resolution requires "
                "MANUAL_VERIFIED source",
            )

            production_usable = True
            resolution_state = (
                "RESOLVED_MANUAL_VERIFIED_REVIEW_PENDING"
            )

        resolution_map[slug] = {
            "category_slug": slug,
            "category_name": name,
            "wordpress_category_id": category_id,
            "resolution_source": source,
            "verified_at": verified_at,
            "evidence_note": evidence_note,
            "resolution_state": resolution_state,
            "production_usable": production_usable,
        }

    required_categories = {
        item["draft_payload"]["category"]["slug"]:
        item["draft_payload"]["category"]["name"]
        for item in package["items"]
    }

    require(
        set(resolution_map) == set(required_categories),
        "category request must resolve exactly every "
        "category used by the package",
    )

    for slug, expected_name in required_categories.items():
        require(
            resolution_map[slug]["category_name"]
            == expected_name,
            f"{slug}: category name mismatch",
        )

    return resolution_map, mode != "EXAMPLE_ONLY"


def validate_review_request(
    review: dict[str, Any],
    package: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    require(
        review.get("phase_id") == "LS-NEW-BATCH-4A",
        "review request phase mismatch",
    )
    require(
        review.get("package_id") == package.get("package_id"),
        "review request package_id mismatch",
    )
    require(
        review.get("batch_id") == package.get("batch_id"),
        "review request batch_id mismatch",
    )
    require(
        review.get("source_batch_digest_sha256")
        == package.get("batch_digest_sha256"),
        "review source batch digest mismatch",
    )
    require(
        review.get("review_status") == "NOT_REVIEWED",
        "review_status must remain NOT_REVIEWED",
    )
    require(
        review.get("human_approval_issued") is False,
        "human approval must remain false",
    )
    require(
        review.get("approval_label") is None,
        "approval_label must remain null",
    )
    require(
        review.get("approval_token") is None,
        "approval_token must remain null",
    )
    require(
        review.get("reviewed_at") is None,
        "reviewed_at must remain null",
    )
    require(
        review.get("reviewer") is None,
        "reviewer must remain null",
    )

    item_reviews = review.get("item_reviews")

    require(
        isinstance(item_reviews, list),
        "item_reviews must be a list",
    )

    review_by_item: dict[str, dict[str, Any]] = {}

    for item_review in item_reviews:
        require(
            isinstance(item_review, dict),
            "each item review must be an object",
        )

        item_id = item_review.get("item_id")

        require(
            isinstance(item_id, str),
            "item review requires string item_id",
        )
        require(
            item_id not in review_by_item,
            f"duplicate item review: {item_id}",
        )

        review_by_item[item_id] = item_review

    source_items = {
        item["item_id"]: item
        for item in package["items"]
    }

    require(
        set(review_by_item) == set(source_items),
        "review request must contain exactly one review "
        "for every source item",
    )

    required_checks = set(
        policy["human_review_gate"][
            "required_item_checks"
        ]
    )

    for item_id, source_item in source_items.items():
        item_review = review_by_item[item_id]

        require(
            item_review.get(
                "source_preview_digest_sha256"
            )
            == source_item[
                "source_preview_digest_sha256"
            ],
            f"{item_id}: source preview digest mismatch",
        )
        require(
            item_review.get(
                "source_payload_digest_sha256"
            )
            == source_item["payload_digest_sha256"],
            f"{item_id}: source payload digest mismatch",
        )

        checks = item_review.get("checks")

        require(
            isinstance(checks, dict),
            f"{item_id}: checks must be an object",
        )
        require(
            set(checks) == required_checks,
            f"{item_id}: review check set mismatch",
        )
        require(
            all(value is False for value in checks.values()),
            f"{item_id}: all initial checks must be false",
        )
        require(
            item_review.get("decision") == "PENDING",
            f"{item_id}: initial decision must be PENDING",
        )
        require(
            item_review.get("reviewer_note") is None,
            f"{item_id}: reviewer_note must remain null",
        )

    return [
        "review_request_identity",
        "review_source_digests_verified",
        "review_checklist_complete",
        "review_status_not_reviewed",
        "human_approval_not_issued",
        "approval_label_absent",
        "approval_token_absent",
    ]


def build_gate_package(
    package: dict[str, Any],
    category_request: dict[str, Any],
    review_request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source_integrity(
        package,
        policy,
    )

    resolution_map, category_ids_production_usable = (
        validate_category_request(
            category_request,
            package,
            policy,
        )
    )

    review_checks = validate_review_request(
        review_request,
        package,
        policy,
    )

    resolved_items: list[dict[str, Any]] = []

    for source_item in package["items"]:
        resolved_item = copy.deepcopy(source_item)
        category = resolved_item[
            "draft_payload"
        ]["category"]
        resolution = resolution_map[category["slug"]]

        category[
            "wordpress_category_id"
        ] = resolution["wordpress_category_id"]
        category[
            "resolution_state"
        ] = resolution["resolution_state"]
        category[
            "resolution_source"
        ] = resolution["resolution_source"]
        category[
            "resolution_verified_at"
        ] = resolution["verified_at"]
        category[
            "resolution_evidence_note"
        ] = resolution["evidence_note"]
        category[
            "production_usable"
        ] = resolution["production_usable"]

        resolved_item["source_payload_digest_sha256"] = (
            source_item["payload_digest_sha256"]
        )
        resolved_item[
            "resolved_payload_digest_sha256"
        ] = canonical_digest(
            resolved_item["draft_payload"]
        )
        resolved_item[
            "category_resolution_completed"
        ] = True
        resolved_item["human_review_status"] = "NOT_REVIEWED"
        resolved_item["human_review_decision"] = "PENDING"
        resolved_item["approval_label"] = None
        resolved_item["approval_token"] = None
        resolved_item["credential_read_allowed"] = False
        resolved_item["wordpress_api_call_allowed"] = False
        resolved_item["wordpress_write_allowed"] = False
        resolved_item["execution_allowed"] = False

        resolved_items.append(resolved_item)

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4A",
        "policy_id": policy["policy_id"],
        "gate_package_id": (
            f"wp-category-review-gate-{package['batch_id']}"
        ),
        "source_package_id": package["package_id"],
        "batch_id": package["batch_id"],
        "template_contract_id": package[
            "template_contract_id"
        ],
        "source_batch_digest_sha256": package[
            "batch_digest_sha256"
        ],
        "resolution_mode": category_request[
            "resolution_mode"
        ],
        "category_resolution": {
            "completed": True,
            "category_count": len(resolution_map),
            "category_ids_production_usable": (
                category_ids_production_usable
            ),
            "wordpress_category_lookup_allowed": False
        },
        "item_count": len(resolved_items),
        "items": resolved_items,
        "human_review_gate": {
            "state": "NOT_REVIEWED",
            "required": True,
            "checklist_created": True,
            "human_approval_issued": False,
            "approval_label": None,
            "approval_token": None,
            "execution_allowed": False
        },
        "execution_boundary": {
            "credential_read_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_category_lookup_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_post_allowed": False,
            "external_api_call_allowed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "CATEGORY_RESOLUTION_AND_REVIEW_PREP_ONLY"
            )
        },
        "verified_checks": source_checks + review_checks
    }

    output = copy.deepcopy(package_without_digest)
    output["resolved_package_digest_sha256"] = (
        canonical_digest(package_without_digest)
    )

    return output


def build_result(
    gate_package: dict[str, Any],
    *,
    package_path: Path,
    category_request_path: Path,
    review_request_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    category_resolution = gate_package[
        "category_resolution"
    ]

    return {
        "phase_id": "LS-NEW-BATCH-4A",
        "status": (
            "PASS_CATEGORY_RESOLUTION_AND_"
            "REVIEW_GATE_NO_WORDPRESS_ACCESS"
        ),
        "decision": (
            "CATEGORY_RESOLUTION_INPUT_AND_"
            "HUMAN_REVIEW_GATE_READY"
        ),
        "policy_id": gate_package["policy_id"],
        "gate_package_id": gate_package[
            "gate_package_id"
        ],
        "source_package_id": gate_package[
            "source_package_id"
        ],
        "batch_id": gate_package["batch_id"],
        "source_package_path": display_path(package_path),
        "category_request_path": display_path(
            category_request_path
        ),
        "review_request_path": display_path(
            review_request_path
        ),
        "output_path": display_path(output_path),
        "item_count": gate_package["item_count"],
        "resolution_mode": gate_package[
            "resolution_mode"
        ],
        "category_resolution_completed": (
            category_resolution["completed"]
        ),
        "category_ids_production_usable": (
            category_resolution[
                "category_ids_production_usable"
            ]
        ),
        "human_review_state": gate_package[
            "human_review_gate"
        ]["state"],
        "human_approval_issued": False,
        "resolved_package_digest_sha256": gate_package[
            "resolved_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + gate_package["verified_checks"]
            + [
                "category_slug_exact_match",
                "category_name_exact_match",
                "category_id_type_and_range_validation",
                "resolved_payload_digest_generation",
                "resolved_package_digest_generation",
                "source_package_not_mutated",
                "human_review_gate_closed",
                "execution_gate_closed"
            ]
        ),
        "credential_read_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "x_post_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "CATEGORY_RESOLUTION_AND_REVIEW_PREP_ONLY"
        ),
        "ready_for_real_category_resolution_input": True,
        "ready_for_human_review": True,
        "ready_for_ls_new_batch_4b": True,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4A Category Resolution and Review Gate Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Gate package: `{result["gate_package_id"]}`
- Source package: `{result["source_package_id"]}`
- Batch: `{result["batch_id"]}`
- Items: `{result["item_count"]}`
- Resolution mode: `{result["resolution_mode"]}`
- Category resolution completed: `{str(result["category_resolution_completed"]).lower()}`
- Category IDs production usable: `{str(result["category_ids_production_usable"]).lower()}`
- Human review state: `{result["human_review_state"]}`
- Human approval issued: `false`

## Integrity

- Resolved package digest: `{result["resolved_package_digest_sha256"]}`

## Verified Checks

{checks}

## Safety Boundary

- Credential read allowed: `false`
- WordPress API call allowed: `false`
- WordPress category lookup allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X posting allowed: `false`
- External API call allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `CATEGORY_RESOLUTION_AND_REVIEW_PREP_ONLY`

## Next State

カテゴリID解決入力と人間レビュー用チェックリストの形式を固定しました。

現在のサンプルは `EXAMPLE_ONLY` であり、カテゴリIDは実WordPressでは
利用できません。次の `LS-NEW-BATCH-4B` で人間レビュー結果を記録できますが、
認証情報読み込み、WordPress通信、下書き作成、公開は引き続き禁止です。
"""


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--package",
        type=Path,
        default=DEFAULT_PACKAGE_PATH,
    )
    parser.add_argument(
        "--category-request",
        type=Path,
        default=DEFAULT_CATEGORY_REQUEST_PATH,
    )
    parser.add_argument(
        "--review-request",
        type=Path,
        default=DEFAULT_REVIEW_REQUEST_PATH,
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

    package_path = resolve_path(args.package)
    category_request_path = resolve_path(
        args.category_request
    )
    review_request_path = resolve_path(
        args.review_request
    )
    output_path = resolve_path(args.output)

    try:
        policy = load_json(POLICY_PATH)
        package = load_json(package_path)
        category_request = load_json(
            category_request_path
        )
        review_request = load_json(review_request_path)

        policy_checks = validate_policy(policy)

        original_package = copy.deepcopy(package)

        gate_package = build_gate_package(
            package=package,
            category_request=category_request,
            review_request=review_request,
            policy=policy,
        )

        require(
            package == original_package,
            "source package was mutated",
        )

        result = build_result(
            gate_package,
            package_path=package_path,
            category_request_path=category_request_path,
            review_request_path=review_request_path,
            output_path=output_path,
            policy_checks=policy_checks,
        )

        if not args.check_only:
            write_json(output_path, gate_package)
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
                    "phase_id": "LS-NEW-BATCH-4A",
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
