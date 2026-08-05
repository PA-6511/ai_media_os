#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "content_human_review_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "content_human_review_request.example.json"
)
REVIEW_PATH = (
    ROOT
    / "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_content_human_review.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "content_human_review_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_l_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_l_"
    "content_human_review_report.md"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"required file missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON: {path}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        value,
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def resolve_path(value: str) -> Path:
    path = Path(value)

    return (
        path
        if path.is_absolute()
        else ROOT / path
    )


def display_path(path: Path) -> str:
    return str(
        path.resolve().relative_to(
            ROOT.resolve()
        )
    )


def verify_self_digest(
    value: dict[str, Any],
    digest_field: str,
    expected: str,
    label: str,
) -> str:
    comparable = copy.deepcopy(
        value
    )
    stored = comparable.pop(
        digest_field,
        None,
    )

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        f"{label} digest invalid",
    )
    require(
        stored == expected,
        f"{label} digest mismatch",
    )

    return stored


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.spans: list[dict[str, str]] = []
        self.classes: set[str] = set()
        self.text_parts: list[str] = []
        self.href_count = 0
        self.anchor_count = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {
            key: value or ""
            for key, value in attrs
        }
        classes = values.get(
            "class",
            "",
        ).split()

        self.classes.update(
            classes
        )

        if "href" in values:
            self.href_count += 1

        if tag == "a":
            self.anchor_count += 1
            self.links.append(values)

        if tag == "img":
            self.images.append(values)

        if tag == "span":
            self.spans.append(values)

    def handle_data(
        self,
        data: str,
    ) -> None:
        compact = " ".join(
            data.split()
        )

        if compact:
            self.text_parts.append(
                compact
            )


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-L",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_GENERATED_ARTICLE_CONTENT_"
            "HUMAN_REVIEW_RECORDING_ONLY"
        ),
        "operation mode mismatch",
    )

    review = policy[
        "required_review"
    ]

    require(
        review[
            "information_card_fields_in_order"
        ]
        == [
            "作品名",
            "価格",
            "作者",
            "出版社",
            "発売日",
        ],
        "information card order mismatch",
    )
    require(
        review["store_slots_in_order"]
        == [
            "amazon",
            "rakuten_kobo",
            "dmm_books",
        ],
        "store slot order mismatch",
    )

    for field in [
        "cover_anchor_allowed",
        "store_anchor_elements_allowed",
        "store_href_attributes_allowed",
        "store_product_urls_allowed",
        "final_affiliate_urls_allowed",
        "dmm_url_allowed",
        "synopsis_allowed",
        "story_detail_allowed",
        "discount_claims_allowed",
        "point_return_claims_allowed",
        "campaign_claims_allowed",
        "inventory_claims_allowed",
        "legacy_post185_product_data_allowed",
        "legacy_post185_urls_allowed",
        "categories_field_allowed",
    ]:
        require(
            review[field] is False,
            f"{field} must remain false",
        )

    boundary = policy[
        "execution_boundary"
    ]

    require(
        boundary[
            "review_evidence_creation_allowed"
        ]
        is True,
        "review evidence creation must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "review_evidence_creation_allowed",
            "production_status",
            "safety_state",
        }:
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    return [
        "policy_phase_verified",
        "operation_mode_verified",
        "information_card_order_verified",
        "store_slot_order_verified",
        "store_link_prohibitions_verified",
        "unsupported_content_prohibitions_verified",
        "source_write_boundaries_closed",
        "production_boundary_closed",
    ]


def validate_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Path],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-L",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    for field in [
        "title_review_requested",
        "advertising_disclosure_review_requested",
        "cover_review_requested",
        "information_card_review_requested",
        "non_clickable_store_slot_review_requested",
        "store_url_absence_review_requested",
        "unnecessary_content_absence_review_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "generated_article_modification_requested",
        "consumption_evidence_modification_requested",
        "source_input_modification_requested",
        "content_generation_contract_modification_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_draft_creation_requested",
        "wordpress_publish_requested",
        "execution_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    bindings = request[
        "source_bindings"
    ]

    path_fields = {
        "k_result": (
            "recovery_k_result_path",
            "recovery_k_result_file_sha256",
        ),
        "article": (
            "generated_article_path",
            "generated_article_file_sha256",
        ),
        "consumption": (
            "consumption_evidence_path",
            "consumption_evidence_file_sha256",
        ),
        "input": (
            "article_input_path",
            "article_input_file_sha256",
        ),
        "content_contract": (
            "content_generation_contract_path",
            "content_generation_contract_file_sha256",
        ),
        "reconciliation_contract": (
            "template_reconciliation_contract_path",
            "template_reconciliation_contract_file_sha256",
        ),
        "preflight": (
            "preflight_plan_path",
            "preflight_plan_file_sha256",
        ),
    }

    paths: dict[str, Path] = {}
    values: dict[str, dict[str, Any]] = {}

    for label, (
        path_field,
        hash_field,
    ) in path_fields.items():
        path = resolve_path(
            bindings[path_field]
        )

        require(
            file_sha256(path)
            == bindings[hash_field],
            f"{label} file hash mismatch",
        )

        paths[label] = path
        values[label] = load_json(
            path
        )

    k_result = values["k_result"]
    article = values["article"]
    consumption = values[
        "consumption"
    ]

    require(
        k_result.get("status")
        == (
            "PASS_FRESH_ARTICLE_CONTENT_GENERATED_"
            "OFFLINE_ONE_SHOT_AUTHORIZATION_CONSUMED_"
            "NO_PAYLOAD_NO_NETWORK"
        ),
        "Recovery K status mismatch",
    )
    require(
        k_result.get(
            "ready_for_article_content_human_review"
        )
        is True,
        "Recovery K not ready for human review",
    )

    article_digest = verify_self_digest(
        article,
        "article_content_digest_sha256",
        bindings[
            "generated_article_artifact_digest_sha256"
        ],
        "generated article",
    )

    consumption_digest = verify_self_digest(
        consumption,
        "consumption_evidence_digest_sha256",
        bindings[
            "consumption_evidence_artifact_digest_sha256"
        ],
        "consumption evidence",
    )

    verify_self_digest(
        values["input"],
        "article_input_digest_sha256",
        bindings[
            "article_input_artifact_digest_sha256"
        ],
        "article input",
    )
    verify_self_digest(
        values["content_contract"],
        "content_generation_contract_digest_sha256",
        bindings[
            "content_generation_contract_artifact_digest_sha256"
        ],
        "content generation contract",
    )
    verify_self_digest(
        values["reconciliation_contract"],
        "template_reconciliation_contract_digest_sha256",
        bindings[
            "template_reconciliation_contract_artifact_digest_sha256"
        ],
        "template reconciliation contract",
    )
    verify_self_digest(
        values["preflight"],
        "preflight_plan_digest_sha256",
        bindings[
            "preflight_plan_artifact_digest_sha256"
        ],
        "preflight plan",
    )

    require(
        consumption[
            "generated_content_file_sha256"
        ]
        == file_sha256(
            paths["article"]
        ),
        "consumption-to-article file binding mismatch",
    )
    require(
        consumption[
            "generated_content_artifact_digest_sha256"
        ]
        == article_digest,
        "consumption-to-article digest binding mismatch",
    )
    require(
        consumption_digest
        == bindings[
            "consumption_evidence_artifact_digest_sha256"
        ],
        "consumption digest mismatch",
    )
    require(
        consumption["authorization_consumed"]
        is True,
        "authorization consumption not confirmed",
    )
    require(
        consumption[
            "authorization_reuse_allowed"
        ]
        is False,
        "authorization reuse not blocked",
    )

    approval = load_json(
        resolve_path(
            request[
                "human_review_approval_path"
            ]
        )
    )
    comparable = copy.deepcopy(
        approval
    )
    stored_approval_digest = comparable.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        isinstance(
            stored_approval_digest,
            str,
        )
        and digest(comparable)
        == stored_approval_digest,
        "human review approval digest invalid",
    )
    require(
        digest(approval)
        == request[
            "human_review_approval_digest_sha256"
        ],
        "human review approval file digest mismatch",
    )
    require(
        approval.get("approval_label")
        == "FRESH_ARTICLE_CONTENT_HUMAN_REVIEW_APPROVED",
        "human review approval label mismatch",
    )
    require(
        approval.get("human_explicit_approval")
        is True,
        "explicit human approval missing",
    )

    return (
        article,
        consumption,
        approval,
        paths,
        [
            "request_identity_verified",
            "review_scope_verified",
            "recovery_k_result_verified",
            "generated_article_file_verified",
            "generated_article_digest_verified",
            "consumption_evidence_file_verified",
            "consumption_evidence_digest_verified",
            "consumption_to_article_binding_verified",
            "source_input_verified",
            "content_generation_contract_verified",
            "template_reconciliation_contract_verified",
            "preflight_plan_verified",
            "authorization_consumption_verified",
            "authorization_reuse_blocked",
            "human_review_approval_verified",
        ],
    )


def review_article(
    article: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, bool],
    list[str],
]:
    content = article[
        "content_html"
    ]
    review = policy[
        "required_review"
    ]

    parser = ArticleParser()
    parser.feed(content)

    checks: dict[str, bool] = {}

    checks["article_title_matches"] = (
        article.get("article_title")
        == review["article_title"]
    )

    expected_start = (
        '<div class="ebook-new-release-article" '
        'data-template-id="POST185_STANDARD_TEMPLATE_V1">\n'
        '  <p class="ebook-pr-disclosure">'
    )

    checks[
        "disclosure_is_first_visible_component"
    ] = content.startswith(
        expected_start
    )
    checks["disclosure_text_exact"] = (
        review["fixed_disclosure_text"]
        in content
    )

    checks["single_cover_image"] = (
        len(parser.images) == 1
    )

    cover = (
        parser.images[0]
        if parser.images
        else {}
    )

    checks["cover_alt_matches"] = (
        cover.get("alt")
        == "ダークギャザリング 第20巻 書影"
    )
    checks["cover_loading_lazy"] = (
        cover.get("loading") == "lazy"
    )
    checks["cover_asset_url_present"] = (
        cover.get("src", "").startswith(
            "https://shop.r10s.jp/"
        )
    )

    expected_fields = [
        ("作品名", "ダークギャザリング"),
        ("価格", "616円（税込）"),
        ("作者", "近藤憲一"),
        ("出版社", "集英社"),
        ("発売日", "2026-07-03"),
    ]

    positions: list[int] = []

    for label, value in expected_fields:
        token = (
            f"<strong>{label}：</strong>{value}"
        )
        position = content.find(token)
        checks[
            f"information_field_{label}_matches"
        ] = position >= 0
        positions.append(position)

    checks[
        "information_card_order_matches"
    ] = (
        all(
            position >= 0
            for position in positions
        )
        and positions == sorted(
            positions
        )
    )

    checks["store_slot_count_is_three"] = (
        len(parser.spans) == 3
    )

    slot_classes = [
        set(
            span.get(
                "class",
                "",
            ).split()
        )
        for span in parser.spans
    ]

    expected_slot_classes = [
        "ls-store-amazon",
        "ls-store-kobo",
        "ls-store-dmm",
    ]

    checks["store_slot_order_matches"] = (
        len(slot_classes) == 3
        and all(
            expected
            in slot_classes[index]
            for index, expected in enumerate(
                expected_slot_classes
            )
        )
    )

    checks[
        "all_store_slots_aria_disabled"
    ] = (
        len(parser.spans) == 3
        and all(
            span.get("aria-disabled")
            == "true"
            for span in parser.spans
        )
    )

    checks["anchor_elements_absent"] = (
        parser.anchor_count == 0
    )
    checks["href_attributes_absent"] = (
        parser.href_count == 0
    )

    serialized_article = json.dumps(
        article,
        ensure_ascii=False,
        sort_keys=True,
    )

    store_url_tokens = [
        "https://www.amazon.co.jp/dp/",
        "https://books.rakuten.co.jp/rk/",
        "https://book.dmm.com/",
        "https://al.dmm.com/",
        "https://hb.afl.rakuten.co.jp/",
    ]

    checks["store_product_urls_absent"] = all(
        token not in serialized_article
        for token in store_url_tokens
    )

    checks["final_affiliate_urls_absent"] = (
        article[
            "store_navigation"
        ]["final_affiliate_urls_included"]
        is False
    )
    checks["dmm_url_absent"] = (
        article[
            "store_navigation"
        ]["dmm_url_included"]
        is False
    )

    forbidden_text = [
        "あらすじ",
        "ポイント還元",
        "割引",
        "キャンペーン",
        "在庫",
        "月曜日のたわわ",
        "比村奇石",
        "税込792円",
        "B0H6DQLPPB",
        "4071859",
    ]

    checks[
        "unnecessary_and_legacy_content_absent"
    ] = all(
        token not in content
        for token in forbidden_text
    )

    checks["categories_field_absent"] = (
        "categories" not in article
        and article[
            "categories_field_present"
        ]
        is False
    )
    checks["payload_absent"] = (
        article["fresh_payload_created"]
        is False
        and article[
            "payload_binding_complete"
        ]
        is False
    )
    checks["production_boundary_closed"] = (
        article[
            "production_category_id_payload_injected"
        ]
        is False
        and article[
            "network_access_performed"
        ]
        is False
        and article[
            "wordpress_write_performed"
        ]
        is False
        and article[
            "wordpress_published"
        ]
        is False
        and article["production_status"]
        == "NO_GO"
    )

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    require(
        not failed,
        "human review checks failed: "
        + ",".join(failed),
    )

    return (
        checks,
        [
            "article_title_review_passed",
            "fixed_disclosure_review_passed",
            "cover_review_passed",
            "information_card_review_passed",
            "store_slot_review_passed",
            "store_urls_absence_review_passed",
            "unnecessary_content_absence_review_passed",
            "legacy_content_absence_review_passed",
            "categories_absence_review_passed",
            "production_boundary_review_passed",
        ],
    )


def ensure_review(
    stable: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if REVIEW_PATH.exists():
        existing = load_json(
            REVIEW_PATH
        )
        comparable = copy.deepcopy(
            existing
        )
        stored = comparable.pop(
            "human_review_digest_sha256",
            None,
        )
        reviewed_at = comparable.pop(
            "reviewed_at_utc",
            None,
        )

        require(
            isinstance(reviewed_at, str)
            and reviewed_at,
            "existing review timestamp invalid",
        )
        require(
            comparable == stable,
            "existing review semantic mismatch",
        )

        without_digest = copy.deepcopy(
            existing
        )
        without_digest.pop(
            "human_review_digest_sha256",
            None,
        )

        require(
            isinstance(stored, str)
            and digest(without_digest)
            == stored,
            "existing review digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(
        stable
    )
    without_digest[
        "reviewed_at_utc"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    evidence = copy.deepcopy(
        without_digest
    )
    evidence[
        "human_review_digest_sha256"
    ] = digest(without_digest)

    write_json(
        REVIEW_PATH,
        evidence,
    )

    return evidence, True


def main() -> int:
    try:
        policy = load_json(
            POLICY_PATH
        )
        request = load_json(
            REQUEST_PATH
        )

        policy_checks = validate_policy(
            policy
        )

        (
            article,
            consumption,
            approval,
            source_paths,
            source_checks,
        ) = validate_sources(
            request,
            policy,
        )

        source_hashes_before = {
            label: file_sha256(path)
            for label, path in source_paths.items()
        }

        checks, review_checks = review_article(
            article,
            policy,
        )

        stable_review = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_ARTICLE_CONTENT_HUMAN_REVIEW_EVIDENCE"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-L"
            ),
            "review_id": (
                "DARK_GATHERING_VOLUME_20_"
                "ARTICLE_CONTENT_HUMAN_REVIEW_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "human_explicit_approval": True,
            "human_review_complete": True,
            "review_decision": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "no_change_required": True,
            "reviewed_article_path": (
                request["source_bindings"][
                    "generated_article_path"
                ]
            ),
            "reviewed_article_file_sha256": (
                request["source_bindings"][
                    "generated_article_file_sha256"
                ]
            ),
            "reviewed_article_artifact_digest_sha256": (
                request["source_bindings"][
                    "generated_article_artifact_digest_sha256"
                ]
            ),
            "consumption_evidence_path": (
                request["source_bindings"][
                    "consumption_evidence_path"
                ]
            ),
            "consumption_evidence_artifact_digest_sha256": (
                request["source_bindings"][
                    "consumption_evidence_artifact_digest_sha256"
                ]
            ),
            "review_approval_path": (
                request[
                    "human_review_approval_path"
                ]
            ),
            "review_approval_digest_sha256": (
                approval[
                    "approval_evidence_digest_sha256"
                ]
            ),
            "review_checks": checks,
            "review_summary": {
                "article_title_verified": True,
                "fixed_disclosure_verified": True,
                "current_cover_verified": True,
                "cover_asset_url_allowed": True,
                "cover_anchor_absent": True,
                "information_card_verified": True,
                "information_card_order_verified": True,
                "non_clickable_store_slots_verified": True,
                "store_product_urls_absent": True,
                "final_affiliate_urls_absent": True,
                "dmm_url_absent": True,
                "unnecessary_content_absent": True,
                "legacy_post185_content_absent": True,
                "categories_field_absent": True
            },
            "source_artifacts_modified": False,
            "generated_article_modified": False,
            "consumption_evidence_modified": False,
            "article_input_modified": False,
            "content_generation_contract_modified": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "content_approved_for_store_link_finalization_gate": True,
            "content_approved_for_payload_generation": False,
            "content_approved_for_wordpress": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ARTICLE_CONTENT_HUMAN_REVIEW_COMPLETE_"
                "AWAITING_STORE_LINK_FINALIZATION_GATE"
            )
        }

        review_evidence, created = ensure_review(
            stable_review
        )

        for label, path in source_paths.items():
            require(
                file_sha256(path)
                == source_hashes_before[label],
                f"source artifact modified: {label}",
            )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-L"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "review_evidence_path": (
                display_path(REVIEW_PATH)
            ),
            "review_evidence_file_sha256": (
                file_sha256(REVIEW_PATH)
            ),
            "human_review_digest_sha256": (
                review_evidence[
                    "human_review_digest_sha256"
                ]
            ),
            "review_evidence_created_in_this_run": (
                created
            ),
            "human_review_complete": True,
            "review_decision": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "all_review_checks_passed": True,
            "source_artifacts_modified": False,
            "fresh_payload_created": False,
            "category_id_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "verified_checks": (
                policy_checks
                + source_checks
                + review_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "content_human_review_package_digest_sha256"
        ] = digest(
            package_without_digest
        )

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-L"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_CONTENT_HUMAN_REVIEW_"
                "APPROVED_NO_CHANGE_NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "OFFLINE_ARTICLE_CONTENT_REVIEW_COMPLETE_"
                "READY_FOR_STORE_LINK_FINALIZATION_GATE"
            ),
            "approval_label": (
                "FRESH_ARTICLE_CONTENT_HUMAN_REVIEW_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "review_evidence_path": (
                package[
                    "review_evidence_path"
                ]
            ),
            "review_evidence_file_sha256": (
                package[
                    "review_evidence_file_sha256"
                ]
            ),
            "human_review_digest_sha256": (
                package[
                    "human_review_digest_sha256"
                ]
            ),
            "content_human_review_package_digest_sha256": (
                package[
                    "content_human_review_package_digest_sha256"
                ]
            ),
            "review_evidence_created_in_this_run": (
                created
            ),
            "human_review_complete": True,
            "review_decision": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "no_change_required": True,
            "all_review_checks_passed": True,
            "article_title_verified": True,
            "fixed_disclosure_verified": True,
            "current_cover_verified": True,
            "cover_asset_url_allowed": True,
            "cover_anchor_absent": True,
            "information_card_verified": True,
            "information_card_order_verified": True,
            "non_clickable_store_slots_verified": True,
            "store_anchor_elements_absent": True,
            "store_href_attributes_absent": True,
            "store_product_urls_absent": True,
            "final_affiliate_urls_absent": True,
            "dmm_url_absent": True,
            "unnecessary_content_absent": True,
            "legacy_post185_content_absent": True,
            "categories_field_absent": True,
            "source_artifacts_modified": False,
            "generated_article_modified": False,
            "consumption_evidence_modified": False,
            "article_input_modified": False,
            "content_generation_contract_modified": False,
            "authorization_consumed": (
                consumption[
                    "authorization_consumed"
                ]
            ),
            "authorization_reuse_allowed": (
                consumption[
                    "authorization_reuse_allowed"
                ]
            ),
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ARTICLE_CONTENT_HUMAN_REVIEW_COMPLETE_"
                "AWAITING_STORE_LINK_FINALIZATION_GATE"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m": True,
            "ready_for_store_link_finalization_gate": True,
            "ready_for_dmm_recheck_gate": True,
            "ready_for_fresh_payload_generation": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package[
                    "verified_checks"
                ]
                + [
                    "human_review_evidence_verified",
                    "human_review_digest_verified",
                    "review_decision_approved_no_change",
                    "source_artifacts_preserved",
                    "payload_not_created",
                    "category_id_not_injected",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "production_gate_closed",
                ]
            ),
        }

        write_json(
            PACKAGE_PATH,
            package,
        )
        write_json(
            RESULT_PATH,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-L Content Human Review

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Article: `{result["article_title"]}`
- Human review complete: `true`
- Review decision: `{result["review_decision"]}`
- Change required: `false`

## Review Checks

- Article title: `PASS`
- Fixed PR disclosure: `PASS`
- Current cover: `PASS`
- Information card and order: `PASS`
- Non-clickable store slots: `PASS`
- Store product URLs absent: `PASS`
- Final affiliate URLs absent: `PASS`
- DMM URL absent: `PASS`
- Unnecessary content absent: `PASS`
- Legacy post185 content absent: `PASS`
- Categories field absent: `PASS`

## Source Preservation

- Generated article modified: `false`
- Consumption evidence modified: `false`
- Article input modified: `false`
- Content-generation contract modified: `false`

## Production Boundary

- Payload created: `false`
- Category ID injected: `false`
- Network accessed: `false`
- WordPress written: `false`
- Published: `false`
- Production status: `NO_GO`
"""

        write_text(
            REPORT_PATH,
            report,
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
        failure = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-L"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "human_review_complete": False,
            "review_decision": "REJECTED_FAIL_CLOSED",
            "generated_article_modified": False,
            "consumption_evidence_modified": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO"
        }

        write_json(
            RESULT_PATH,
            failure,
        )

        print(
            json.dumps(
                failure,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
