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
    "new_release_wp_human_review_decision_policy.json"
)
DEFAULT_SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_review_gate_package.example.json"
)
DEFAULT_REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_human_review_decision_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_human_review_decision_package.example.json"
)

RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4b_result.json"
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4b_human_review_decision_report.md"
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
        policy.get("phase_id") == "LS-NEW-BATCH-4B",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_HUMAN_REVIEW_DECISION_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    rules = policy.get("review_rules", {})

    require(
        rules.get("all_checks_true_required_for_approval")
        is True,
        "all checks must be required for approval",
    )
    require(
        rules.get("explicit_confirmation_required") is True,
        "explicit confirmation must be required",
    )
    checks.append("review_rules")

    labels = policy.get("label_rules", {})

    require(
        labels.get("review_label_generation_allowed") is True,
        "review-label generation must be allowed",
    )
    require(
        labels.get(
            "execution_approval_label_generation_allowed"
        )
        is False,
        "execution approval labels must remain blocked",
    )
    checks.append("label_boundary")

    boundary = policy.get("execution_boundary", {})

    require(
        boundary.get("human_review_recording_allowed")
        is True,
        "human review recording must be allowed",
    )

    for field in [
        "credential_read_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
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
        == "HUMAN_REVIEW_RECORD_ONLY",
        "safety state mismatch",
    )
    checks.append("execution_boundary")

    return checks


def verify_source_integrity(
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

    expected_package_digest = source.get(
        "resolved_package_digest_sha256"
    )

    require(
        isinstance(expected_package_digest, str)
        and len(expected_package_digest) == 64,
        "source resolved package digest is invalid",
    )

    source_without_digest = copy.deepcopy(source)
    source_without_digest.pop(
        "resolved_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(source_without_digest)
        == expected_package_digest,
        "source resolved package digest verification failed",
    )

    items = source.get("items")

    require(
        isinstance(items, list) and len(items) >= 1,
        "source must contain at least one item",
    )

    for item in items:
        item_id = item.get("item_id")
        draft_payload = item.get("draft_payload")
        expected_payload_digest = item.get(
            "resolved_payload_digest_sha256"
        )

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
            == expected_payload_digest,
            f"{item_id}: resolved payload digest "
            "verification failed",
        )
        require(
            item.get("human_review_status")
            == "NOT_REVIEWED",
            f"{item_id}: source must be NOT_REVIEWED",
        )
        require(
            item.get("human_review_decision") == "PENDING",
            f"{item_id}: source decision must be PENDING",
        )
        require(
            item.get("execution_allowed") is False,
            f"{item_id}: source execution must remain blocked",
        )

    gate = source.get("human_review_gate", {})

    require(
        gate.get("state") == "NOT_REVIEWED",
        "source human-review gate must be NOT_REVIEWED",
    )
    require(
        gate.get("human_approval_issued") is False,
        "source human approval must be false",
    )
    require(
        gate.get("approval_token") is None,
        "source approval token must be absent",
    )

    return [
        "source_phase_identity",
        "source_resolved_package_digest_verified",
        "source_resolved_payload_digests_verified",
        "source_review_gate_unreviewed",
        "source_execution_gate_closed",
    ]


def validate_request(
    request: dict[str, Any],
    source: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], str, str, str]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-4B",
        "request phase_id mismatch",
    )
    require(
        request.get("gate_package_id")
        == source.get("gate_package_id"),
        "request gate_package_id mismatch",
    )
    require(
        request.get("batch_id") == source.get("batch_id"),
        "request batch_id mismatch",
    )
    require(
        request.get(
            "source_resolved_package_digest_sha256"
        )
        == source.get("resolved_package_digest_sha256"),
        "request source package digest mismatch",
    )

    request_version = request.get("request_version")

    require(
        isinstance(request_version, int)
        and not isinstance(request_version, bool)
        and request_version >= 1,
        "request_version must be positive",
    )

    require(
        request.get("review_status") == "COMPLETED",
        "review_status must be COMPLETED",
    )

    reviewer = normalize_text(
        request.get("reviewer"),
        field_name="reviewer",
        required=True,
    )
    reviewed_at = parse_datetime(
        request.get("reviewed_at"),
        field_name="reviewed_at",
    )
    confirmation = normalize_text(
        request.get("human_review_confirmation"),
        field_name="human_review_confirmation",
        required=True,
    )

    assert reviewer is not None
    assert confirmation is not None

    require(
        confirmation
        == policy["review_rules"]["required_confirmation"],
        "human review confirmation mismatch",
    )
    require(
        request.get("execution_approval_issued") is False,
        "execution approval must remain false",
    )
    require(
        request.get("approval_token") is None,
        "approval token must remain null",
    )

    overall_decision = request.get("overall_decision")

    require(
        overall_decision
        in policy["allowed_overall_decisions"],
        f"unsupported overall_decision: {overall_decision}",
    )

    item_reviews = request.get("item_reviews")

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

    source_by_item = {
        item["item_id"]: item
        for item in source["items"]
    }

    require(
        set(review_by_item) == set(source_by_item),
        "request must contain exactly one review "
        "for every source item",
    )

    required_checks = set(policy["required_item_checks"])
    item_decisions: list[str] = []

    for item_id, source_item in source_by_item.items():
        review = review_by_item[item_id]

        require(
            review.get(
                "source_resolved_payload_digest_sha256"
            )
            == source_item[
                "resolved_payload_digest_sha256"
            ],
            f"{item_id}: source resolved payload "
            "digest mismatch",
        )

        checks = review.get("checks")

        require(
            isinstance(checks, dict),
            f"{item_id}: checks must be an object",
        )
        require(
            set(checks) == required_checks,
            f"{item_id}: review check set mismatch",
        )
        require(
            all(isinstance(value, bool) for value in checks.values()),
            f"{item_id}: review checks must be boolean",
        )

        decision = review.get("decision")

        require(
            decision in policy["allowed_item_decisions"],
            f"{item_id}: unsupported decision: {decision}",
        )

        note = normalize_text(
            review.get("reviewer_note"),
            field_name=f"{item_id}.reviewer_note",
            required=False,
        )

        if decision == "APPROVE_FOR_DRAFT_PRE_EXECUTION":
            require(
                all(checks.values()),
                f"{item_id}: all checks must be true "
                "for approval",
            )
        else:
            require(
                note is not None,
                f"{item_id}: rejection requires reviewer_note",
            )

        item_decisions.append(decision)

    calculated_overall = (
        "REJECT"
        if "REJECT" in item_decisions
        else "APPROVE_FOR_DRAFT_PRE_EXECUTION"
    )

    require(
        overall_decision == calculated_overall,
        "overall_decision does not match item decisions",
    )

    return (
        review_by_item,
        reviewer,
        reviewed_at,
        overall_decision,
    )


def build_review_package(
    source: dict[str, Any],
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_checks = verify_source_integrity(
        source,
        policy,
    )

    (
        review_by_item,
        reviewer,
        reviewed_at,
        overall_decision,
    ) = validate_request(
        request,
        source,
        policy,
    )

    source_production_usable = bool(
        source["category_resolution"][
            "category_ids_production_usable"
        ]
    )
    resolution_mode = source["resolution_mode"]

    labels = policy["label_rules"]

    if overall_decision == "REJECT":
        effective_outcome = "REVIEW_REJECTED"
        review_label = labels["rejection_label"]
        human_review_approval_recorded = False
    elif (
        resolution_mode == "EXAMPLE_ONLY"
        or not source_production_usable
    ):
        effective_outcome = (
            "REVIEW_APPROVED_EXAMPLE_ONLY_NOT_EXECUTABLE"
        )
        review_label = labels["example_approval_label"]
        human_review_approval_recorded = True
    else:
        effective_outcome = (
            "REVIEW_APPROVED_PRE_EXECUTION_NO_TOKEN"
        )
        review_label = labels["production_review_label"]
        human_review_approval_recorded = True

    reviewed_items: list[dict[str, Any]] = []

    for source_item in source["items"]:
        item = copy.deepcopy(source_item)
        review = review_by_item[item["item_id"]]

        item["human_review_status"] = "COMPLETED"
        item["human_review_decision"] = review["decision"]
        item["human_review_checks"] = copy.deepcopy(
            review["checks"]
        )
        item["human_reviewer"] = reviewer
        item["human_reviewed_at"] = reviewed_at
        item["human_reviewer_note"] = review.get(
            "reviewer_note"
        )
        item["review_label"] = review_label
        item["approval_token"] = None
        item["execution_approval_issued"] = False
        item["credential_read_allowed"] = False
        item["wordpress_api_call_allowed"] = False
        item["wordpress_write_allowed"] = False
        item["execution_allowed"] = False

        reviewed_items.append(item)

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4B",
        "policy_id": policy["policy_id"],
        "review_package_id": (
            f"wp-human-review-{source['batch_id']}"
        ),
        "source_gate_package_id": source[
            "gate_package_id"
        ],
        "batch_id": source["batch_id"],
        "template_contract_id": source[
            "template_contract_id"
        ],
        "source_resolved_package_digest_sha256": source[
            "resolved_package_digest_sha256"
        ],
        "resolution_mode": resolution_mode,
        "category_ids_production_usable": (
            source_production_usable
        ),
        "item_count": len(reviewed_items),
        "items": reviewed_items,
        "human_review": {
            "state": "COMPLETED",
            "overall_decision": overall_decision,
            "effective_outcome": effective_outcome,
            "review_label": review_label,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "overall_note": request.get("overall_note"),
            "human_review_approval_recorded": (
                human_review_approval_recorded
            ),
            "execution_approval_issued": False,
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
            "execution_approval_issued": False,
            "approval_token_present": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": "HUMAN_REVIEW_RECORD_ONLY"
        },
        "verified_checks": source_checks
    }

    output = copy.deepcopy(package_without_digest)
    output["review_package_digest_sha256"] = (
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
    review = package["human_review"]

    return {
        "phase_id": "LS-NEW-BATCH-4B",
        "status": (
            "PASS_HUMAN_REVIEW_RECORDED_"
            "NO_WORDPRESS_ACCESS"
        ),
        "decision": (
            "HUMAN_REVIEW_DECISION_RECORDED_"
            "EXECUTION_GATE_REMAINS_CLOSED"
        ),
        "policy_id": package["policy_id"],
        "review_package_id": package[
            "review_package_id"
        ],
        "source_gate_package_id": package[
            "source_gate_package_id"
        ],
        "batch_id": package["batch_id"],
        "source_path": display_path(source_path),
        "request_path": display_path(request_path),
        "output_path": display_path(output_path),
        "item_count": package["item_count"],
        "resolution_mode": package["resolution_mode"],
        "category_ids_production_usable": package[
            "category_ids_production_usable"
        ],
        "human_review_state": review["state"],
        "overall_decision": review["overall_decision"],
        "effective_outcome": review["effective_outcome"],
        "review_label": review["review_label"],
        "human_review_approval_recorded": review[
            "human_review_approval_recorded"
        ],
        "execution_approval_issued": False,
        "approval_token_present": False,
        "review_package_digest_sha256": package[
            "review_package_digest_sha256"
        ],
        "verified_checks": (
            policy_checks
            + package["verified_checks"]
            + [
                "review_request_identity",
                "explicit_human_confirmation",
                "reviewer_and_timestamp_validation",
                "review_checklist_exact_match",
                "all_checks_true_for_approval",
                "item_decision_consistency",
                "overall_decision_consistency",
                "example_only_execution_block",
                "review_label_generation",
                "approval_token_absence",
                "review_package_digest_generation",
                "source_package_not_mutated",
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
        "safety_state": "HUMAN_REVIEW_RECORD_ONLY",
        "ready_for_real_human_review_input": True,
        "ready_for_ls_new_batch_4c": True,
        "ready_for_production_pre_execution": (
            review["human_review_approval_recorded"]
            and package["category_ids_production_usable"]
        ),
        "ready_for_execution": False,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4B Human Review Decision Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Review package: `{result["review_package_id"]}`
- Batch: `{result["batch_id"]}`
- Items: `{result["item_count"]}`
- Resolution mode: `{result["resolution_mode"]}`
- Category IDs production usable: `{str(result["category_ids_production_usable"]).lower()}`

## Human Review

- State: `{result["human_review_state"]}`
- Overall decision: `{result["overall_decision"]}`
- Effective outcome: `{result["effective_outcome"]}`
- Review label: `{result["review_label"]}`
- Human review approval recorded: `{str(result["human_review_approval_recorded"]).lower()}`
- Execution approval issued: `false`
- Approval token present: `false`

## Integrity

- Review package digest: `{result["review_package_digest_sha256"]}`

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
- Safety state: `HUMAN_REVIEW_RECORD_ONLY`

## Next State

人間レビュー結果を記録しました。

現在のカテゴリ解決は `EXAMPLE_ONLY` のため、レビュー上は承認でも
WordPress実行承認には昇格しません。承認トークンは生成されず、
認証情報読み込み、WordPress通信、下書き作成、公開は引き続き禁止です。
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

        package = build_review_package(
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
                    "phase_id": "LS-NEW-BATCH-4B",
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
