#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/new_release_wp_draft_preparation_policy.json"
)
DEFAULT_SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_article_ready_preview_result.example.json"
)
DEFAULT_REVIEW_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_draft_review_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_draft_preparation.example.json"
)

RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4_result.json"
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4_wp_draft_preparation_report.md"
)

SAFE_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ValidationError(RuntimeError):
    pass


class ArticleHTMLInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.elements: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized_tag = tag.lower()
        attributes = {
            key.lower(): value or ""
            for key, value in attrs
        }

        self.elements.append(normalized_tag)

        if normalized_tag == "a":
            self.links.append(attributes)

        if normalized_tag == "img":
            self.images.append(attributes)


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


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def validate_https_url(
    value: str,
    *,
    field_name: str,
) -> None:
    parsed = urlparse(value)

    require(
        parsed.scheme == "https" and bool(parsed.hostname),
        f"{field_name} must use a valid HTTPS URL",
    )


def validate_policy(policy: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-4",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_WP_DRAFT_PREPARATION_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    payload_rules = policy.get("payload_rules", {})

    require(
        payload_rules.get("wordpress_status") == "draft",
        "WordPress status must remain draft",
    )
    require(
        payload_rules.get("uncategorized_allowed") is False,
        "uncategorized must remain forbidden",
    )
    require(
        payload_rules.get(
            "category_id_must_remain_null_in_this_phase"
        )
        is True,
        "category ID must remain unresolved in this phase",
    )
    checks.append("payload_rules")

    approval_gate = policy.get("approval_gate", {})

    require(
        approval_gate.get("initial_state") == "NOT_APPROVED",
        "approval gate must start closed",
    )
    require(
        approval_gate.get("human_approval_required") is True,
        "human approval must be required",
    )
    require(
        approval_gate.get(
            "approval_token_generation_allowed"
        )
        is False,
        "approval-token generation must remain blocked",
    )
    checks.append("approval_gate")

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
        boundary.get("safety_state") == "PREPARATION_ONLY",
        "safety state must remain PREPARATION_ONLY",
    )
    checks.append("execution_boundary")

    return checks


def validate_review_request(
    review: dict[str, Any],
    *,
    batch_id: str,
) -> list[str]:
    require(
        review.get("phase_id") == "LS-NEW-BATCH-4",
        "review phase_id mismatch",
    )
    require(
        review.get("batch_id") == batch_id,
        "review batch_id mismatch",
    )
    require(
        review.get("review_status") == "NOT_REVIEWED",
        "review_status must remain NOT_REVIEWED",
    )
    require(
        review.get("approved_item_ids") == [],
        "approved_item_ids must remain empty",
    )
    require(
        review.get("human_approval_issued") is False,
        "human approval must remain false",
    )
    require(
        review.get("approval_token") is None,
        "approval_token must remain null",
    )
    require(
        review.get("reviewed_at") is None,
        "reviewed_at must remain null",
    )

    return [
        "review_request_identity",
        "human_approval_not_issued",
        "approval_token_absent",
    ]


def validate_html(
    content_html: str,
    *,
    item_id: str,
    policy: dict[str, Any],
) -> dict[str, int]:
    html_rules = policy["html_rules"]

    for marker in html_rules["required_markers"]:
        require(
            marker in content_html,
            f"{item_id}: required HTML marker missing: {marker}",
        )

    inspector = ArticleHTMLInspector()
    inspector.feed(content_html)
    inspector.close()

    prohibited = set(html_rules["prohibited_elements"])
    detected_prohibited = sorted(
        prohibited.intersection(inspector.elements)
    )

    require(
        not detected_prohibited,
        f"{item_id}: prohibited HTML elements detected: "
        f"{detected_prohibited}",
    )

    require(
        len(inspector.links) >= 1,
        f"{item_id}: at least one store link is required",
    )
    require(
        len(inspector.images) >= 1,
        f"{item_id}: at least one cover image is required",
    )

    required_rel_tokens = set(
        html_rules["affiliate_rel_tokens_required"]
    )

    for index, link in enumerate(inspector.links, start=1):
        href = link.get("href", "")
        validate_https_url(
            href,
            field_name=f"{item_id}.link[{index}].href",
        )

        rel_tokens = {
            token.strip().lower()
            for token in link.get("rel", "").split()
            if token.strip()
        }

        require(
            required_rel_tokens.issubset(rel_tokens),
            f"{item_id}.link[{index}] missing affiliate rel tokens",
        )

    for index, image in enumerate(inspector.images, start=1):
        src = image.get("src", "")
        validate_https_url(
            src,
            field_name=f"{item_id}.image[{index}].src",
        )

        require(
            bool(image.get("alt", "").strip()),
            f"{item_id}.image[{index}] requires alt text",
        )

    return {
        "link_count": len(inspector.links),
        "image_count": len(inspector.images),
    }


def validate_store_order(
    store_order: Any,
    *,
    item_id: str,
    policy: dict[str, Any],
) -> list[str]:
    require(
        isinstance(store_order, list),
        f"{item_id}: store_button_order must be a list",
    )
    require(
        len(store_order) >= 1,
        f"{item_id}: at least one store is required",
    )
    require(
        len(store_order) == len(set(store_order)),
        f"{item_id}: duplicate store names detected",
    )

    global_order = policy["store_button_order"]

    for store_name in store_order:
        require(
            store_name in global_order,
            f"{item_id}: unsupported store: {store_name}",
        )

    expected_order = [
        store_name
        for store_name in global_order
        if store_name in store_order
    ]

    require(
        store_order == expected_order,
        f"{item_id}: store button order mismatch",
    )

    return list(store_order)


def build_prepared_item(
    generated: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> dict[str, Any]:
    item_id = normalize_text(
        generated.get("item_id"),
        field_name="generated.item_id",
        required=True,
    )
    assert item_id is not None

    require(
        generated.get("source_classification")
        == "READY_FOR_DRAFT",
        f"{item_id}: source classification must be READY_FOR_DRAFT",
    )
    require(
        generated.get("wordpress_write_allowed") is False,
        f"{item_id}: source must not allow WordPress write",
    )

    payload = generated.get("article_payload")

    require(
        isinstance(payload, dict),
        f"{item_id}: article_payload must be an object",
    )

    required_fields = policy["required_article_fields"]
    missing_fields = [
        field
        for field in required_fields
        if field not in payload
    ]

    require(
        not missing_fields,
        f"{item_id}: article payload fields missing: "
        f"{missing_fields}",
    )

    title = normalize_text(
        payload.get("post_title"),
        field_name=f"{item_id}.post_title",
        required=True,
    )
    slug = normalize_text(
        payload.get("post_name"),
        field_name=f"{item_id}.post_name",
        required=True,
    )
    excerpt = normalize_text(
        payload.get("post_excerpt"),
        field_name=f"{item_id}.post_excerpt",
        required=True,
    )
    content_html = normalize_text(
        payload.get("content_html"),
        field_name=f"{item_id}.content_html",
        required=True,
    )
    category_slug = normalize_text(
        payload.get("category_slug"),
        field_name=f"{item_id}.category_slug",
        required=True,
    )
    category_name = normalize_text(
        payload.get("category_name"),
        field_name=f"{item_id}.category_name",
        required=True,
    )

    assert title is not None
    assert slug is not None
    assert excerpt is not None
    assert content_html is not None
    assert category_slug is not None
    assert category_name is not None

    require(
        payload.get("post_status") == "draft",
        f"{item_id}: post_status must remain draft",
    )
    require(
        payload.get("template_id")
        == policy["payload_rules"]["template_id"],
        f"{item_id}: template_id mismatch",
    )
    require(
        payload.get("description_mode") == "minimal",
        f"{item_id}: description_mode must remain minimal",
    )
    require(
        payload.get("uncategorized_assigned") is False,
        f"{item_id}: uncategorized must not be assigned",
    )
    require(
        category_slug != "uncategorized",
        f"{item_id}: uncategorized slug is forbidden",
    )
    require(
        bool(SAFE_SLUG_PATTERN.fullmatch(slug)),
        f"{item_id}: invalid post slug",
    )

    metadata = payload.get("metadata")

    require(
        isinstance(metadata, dict),
        f"{item_id}: metadata must be an object",
    )

    store_order = validate_store_order(
        metadata.get("store_button_order"),
        item_id=item_id,
        policy=policy,
    )

    html_summary = validate_html(
        content_html,
        item_id=item_id,
        policy=policy,
    )

    source_preview_digest = normalize_text(
        generated.get("preview_digest_sha256"),
        field_name=f"{item_id}.preview_digest_sha256",
        required=True,
    )
    assert source_preview_digest is not None

    require(
        len(source_preview_digest) == 64,
        f"{item_id}: invalid preview digest",
    )

    idempotency_key = hashlib.sha256(
        (
            "LS-NEW-BATCH-4"
            + "\x1f"
            + item_id
            + "\x1f"
            + slug
            + "\x1f"
            + source_preview_digest
        ).encode("utf-8")
    ).hexdigest()

    draft_payload = {
        "title": title,
        "slug": slug,
        "status": "draft",
        "excerpt": excerpt,
        "content_html": content_html,
        "category": {
            "slug": category_slug,
            "name": category_name,
            "wordpress_category_id": None,
            "resolution_state": "PENDING_ID_LOOKUP"
        },
        "template_id": payload["template_id"],
        "metadata": metadata
    }

    payload_digest = canonical_digest(draft_payload)

    return {
        "item_id": item_id,
        "preparation_state": "PREPARED_NOT_APPROVED",
        "source_preview_digest_sha256": source_preview_digest,
        "idempotency_key": idempotency_key,
        "payload_digest_sha256": payload_digest,
        "html_validation": html_summary,
        "store_button_order": store_order,
        "draft_payload": draft_payload,
        "approval_state": "NOT_APPROVED",
        "approval_token": None,
        "future_wordpress_post_id": None,
        "rollback_plan": {
            "required": True,
            "action_if_future_creation_fails": (
                "DO_NOT_RETRY_AUTOMATICALLY"
            ),
            "action_if_future_draft_is_created_then_rejected": (
                "DELETE_OR_TRASH_CREATED_DRAFT_AFTER_HUMAN_REVIEW"
            )
        },
        "credential_read_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "execution_allowed": False
    }


def build_package(
    source: dict[str, Any],
    review: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    require(
        source.get("phase_id") == policy["source_phase_id"],
        "source phase mismatch",
    )
    require(
        source.get("template_contract_id")
        == policy["template_contract_id"],
        "template contract mismatch",
    )
    require(
        source.get("generation_mode") == "PREVIEW_ONLY",
        "source generation_mode must be PREVIEW_ONLY",
    )

    generated_items = source.get("generated_items")

    require(
        isinstance(generated_items, list),
        "generated_items must be a list",
    )

    limits = policy["batch_limits"]

    require(
        limits["minimum_items"]
        <= len(generated_items)
        <= limits["maximum_items"],
        "generated item count is outside preparation limits",
    )

    batch_id = normalize_text(
        source.get("batch_id"),
        field_name="batch_id",
        required=True,
    )
    assert batch_id is not None

    review_checks = validate_review_request(
        review,
        batch_id=batch_id,
    )

    prepared_items = [
        build_prepared_item(item, policy=policy)
        for item in generated_items
    ]

    item_ids = [
        item["item_id"]
        for item in prepared_items
    ]

    require(
        len(item_ids) == len(set(item_ids)),
        "duplicate item_id detected in prepared batch",
    )

    idempotency_keys = [
        item["idempotency_key"]
        for item in prepared_items
    ]

    require(
        len(idempotency_keys) == len(set(idempotency_keys)),
        "duplicate idempotency key detected",
    )

    package_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4",
        "policy_id": policy["policy_id"],
        "package_id": f"wp-draft-prep-{batch_id}",
        "batch_id": batch_id,
        "template_contract_id": policy[
            "template_contract_id"
        ],
        "source_phase_id": source["phase_id"],
        "source_generation_mode": source[
            "generation_mode"
        ],
        "item_count": len(prepared_items),
        "items": prepared_items,
        "review": {
            "review_status": review["review_status"],
            "approved_item_ids": [],
            "human_approval_issued": False,
            "approval_token": None,
            "reviewed_at": None
        },
        "approval_gate": {
            "state": "NOT_APPROVED",
            "human_approval_required": True,
            "approval_token_required": True,
            "execution_allowed": False
        },
        "category_resolution": {
            "required": True,
            "completed": False,
            "wordpress_api_lookup_allowed": False
        },
        "execution_boundary": {
            "credential_read_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_post_allowed": False,
            "external_api_call_allowed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": "PREPARATION_ONLY"
        }
    }

    package = dict(package_without_digest)
    package["batch_digest_sha256"] = canonical_digest(
        package_without_digest
    )
    package["_review_validation_checks"] = review_checks

    return package


def build_result(
    package: dict[str, Any],
    *,
    source_path: Path,
    review_path: Path,
    output_path: Path,
    policy_checks: list[str],
) -> dict[str, Any]:
    review_checks = package.pop(
        "_review_validation_checks"
    )

    return {
        "phase_id": "LS-NEW-BATCH-4",
        "status": (
            "PASS_DRAFT_PREPARATION_NO_WORDPRESS_ACCESS"
        ),
        "decision": (
            "CONTROLLED_DRAFT_PAYLOAD_PACKAGE_PREPARED"
        ),
        "policy_id": package["policy_id"],
        "package_id": package["package_id"],
        "batch_id": package["batch_id"],
        "source_path": display_path(source_path),
        "review_path": display_path(review_path),
        "output_path": display_path(output_path),
        "item_count": package["item_count"],
        "batch_digest_sha256": package[
            "batch_digest_sha256"
        ],
        "approval_state": package[
            "approval_gate"
        ]["state"],
        "human_approval_issued": False,
        "category_resolution_completed": False,
        "verified_checks": (
            policy_checks
            + review_checks
            + [
                "source_preview_identity",
                "batch_size_limit",
                "article_payload_required_fields",
                "draft_status_lock",
                "post185_template_lock",
                "uncategorized_exclusion",
                "html_safety_validation",
                "affiliate_link_validation",
                "cover_image_validation",
                "fixed_store_order",
                "idempotency_key_generation",
                "item_payload_digest_generation",
                "batch_digest_generation",
                "category_id_unresolved_lock",
                "execution_gate_closed"
            ]
        ),
        "credential_read_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "x_post_allowed": False,
        "external_api_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "PREPARATION_ONLY",
        "ready_for_human_review": True,
        "ready_for_category_resolution_design": True,
        "ready_for_ls_new_batch_4a": True,
        "ready_for_execution": False,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-4 WordPress Draft Preparation Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Package: `{result["package_id"]}`
- Batch: `{result["batch_id"]}`
- Items: `{result["item_count"]}`
- Batch digest: `{result["batch_digest_sha256"]}`

## Approval State

- Approval state: `{result["approval_state"]}`
- Human approval issued: `false`
- Category resolution completed: `false`
- Ready for execution: `false`

## Verified Checks

{checks}

## Safety Boundary

- Credential read allowed: `false`
- WordPress API call allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X posting allowed: `false`
- External API call allowed: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Safety state: `PREPARATION_ONLY`

## Next State

WordPress下書き作成候補を、版固定されたペイロードとして準備しました。

次の `LS-NEW-BATCH-4A` ではカテゴリID解決方法と人間レビューゲートを
設計できますが、現段階では認証情報の読み込み、WordPress API通信、
下書き作成および公開はすべて禁止されています。
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
        "--review",
        type=Path,
        default=DEFAULT_REVIEW_PATH,
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
    review_path = resolve_path(args.review)
    output_path = resolve_path(args.output)

    try:
        policy = load_json(POLICY_PATH)
        source = load_json(source_path)
        review = load_json(review_path)

        policy_checks = validate_policy(policy)

        package = build_package(
            source=source,
            review=review,
            policy=policy,
        )

        result = build_result(
            package,
            source_path=source_path,
            review_path=review_path,
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
                    "phase_id": "LS-NEW-BATCH-4",
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
