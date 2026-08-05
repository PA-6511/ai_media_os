#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_preflight_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_preflight_request.example.json"
)
PLAN_PATH = (
    ROOT
    / "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_preflight.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_preflight_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_k_preflight_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_k_preflight_report.md"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
CONSUMPTION_PATH = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_consumption.json"
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
    label: str,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        digest_field,
        None,
    )

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        f"{label} digest invalid",
    )

    return stored


def k0_semantic_state(
    result: dict[str, Any],
) -> dict[str, Any]:
    fields = [
        "phase_id",
        "status",
        "decision",
        "approval_label",
        "reconciliation_contract_id",
        "reconciliation_contract_digest_sha256",
        "content_item_id",
        "work_title",
        "volume_label",
        "template_contract_id",
        "template_id",
        "template_artifact_resolved",
        "reconciled_disclosure_text",
        "information_card_fields",
        "store_button_order",
        "legacy_product_data_inheritance_allowed",
        "legacy_url_inheritance_allowed",
        "final_affiliate_link_rendering_allowed",
        "dmm_url_rendering_allowed",
        "source_authorization_modified",
        "authorization_consumed",
        "consumption_evidence_created",
        "content_output_exists",
        "article_content_generated",
        "fresh_payload_created",
        "payload_binding_complete",
        "production_category_id_payload_injected",
        "network_connection_performed",
        "wordpress_write_performed",
        "execution_allowed",
        "production_status",
        "ready_for_recovery_k_preflight",
    ]

    return {
        field: result.get(field)
        for field in fields
    }


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == (
            "LS-NEW-BATCH-4G-2E-"
            "RECOVERY-K-PREFLIGHT"
        ),
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_ONE_SHOT_OFFLINE_"
            "GENERATION_PREFLIGHT_ONLY"
        ),
        "operation mode mismatch",
    )

    structure = policy[
        "planned_structure"
    ]

    require(
        structure["component_order"]
        == [
            "advertising_disclosure",
            "cover_and_information_card",
            "store_navigation_slots",
        ],
        "component order mismatch",
    )

    require(
        structure["advertising_disclosure"][
            "exact_text"
        ]
        == (
            "【PR】本記事にはアフィリエイト広告を含みます。"
            "価格・配信状況は各ストアで確認してください。"
        ),
        "disclosure text mismatch",
    )

    require(
        structure["information_card"][
            "ordered_fields"
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

    navigation = structure[
        "store_navigation"
    ]

    require(
        navigation["render_mode"]
        == "RESERVED_NON_CLICKABLE_SLOTS_ONLY",
        "store render mode mismatch",
    )
    require(
        navigation["ordered_slots"]
        == [
            "amazon",
            "rakuten_kobo",
            "dmm_books",
        ],
        "store slot order mismatch",
    )

    for field in [
        "anchor_element_allowed",
        "href_attribute_allowed",
        "verification_source_url_rendering_allowed",
        "final_affiliate_url_rendering_allowed",
        "dmm_url_rendering_allowed",
    ]:
        require(
            navigation[field] is False,
            f"{field} must remain false",
        )

    dmm = policy["dmm_boundary"]

    require(
        dmm["latest_alias_recheck_required"]
        is True,
        "DMM recheck requirement missing",
    )
    require(
        dmm["latest_alias_recheck_completed"]
        is False,
        "DMM recheck must remain incomplete",
    )
    require(
        dmm["url_copy_to_preflight_plan_allowed"]
        is False,
        "DMM URL copying must remain blocked",
    )

    boundary = policy[
        "execution_boundary"
    ]

    require(
        boundary["preflight_plan_creation_allowed"]
        is True,
        "preflight plan creation must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "preflight_plan_creation_allowed",
            "production_status",
            "safety_state",
        }:
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    require(
        boundary["production_status"]
        == "NO_GO",
        "production status must remain NO_GO",
    )

    return [
        "policy_phase_verified",
        "operation_mode_verified",
        "component_order_verified",
        "disclosure_text_verified",
        "information_card_order_verified",
        "store_slot_order_verified",
        "store_slots_non_clickable",
        "store_url_rendering_blocked",
        "dmm_url_rendering_blocked",
        "preflight_only_boundary_verified",
    ]


def validate_request_and_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    require(
        request.get("phase_id")
        == (
            "LS-NEW-BATCH-4G-2E-"
            "RECOVERY-K-PREFLIGHT"
        ),
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    for field in [
        "source_digest_validation_requested",
        "planned_structure_fixation_requested",
        "current_article_information_only_requested",
        "fixed_disclosure_requested",
        "store_navigation_slots_only_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "final_affiliate_url_output_requested",
        "dmm_url_output_requested",
        "article_content_generation_requested",
        "content_output_creation_requested",
        "authorization_consumption_requested",
        "consumption_evidence_creation_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_draft_creation_requested",
        "execution_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    bindings = request[
        "source_bindings"
    ]

    k0_result = load_json(
        resolve_path(
            bindings["k0_result_path"]
        )
    )

    require(
        digest(k0_semantic_state(k0_result))
        == bindings[
            "k0_result_semantic_digest_sha256"
        ],
        "K0 semantic digest mismatch",
    )
    require(
        k0_result.get("status")
        == (
            "PASS_FRESH_ARTICLE_TEMPLATE_RECONCILIATION_"
            "FIXED_NO_CONTENT_NO_AUTH_CONSUMPTION_NO_NETWORK"
        ),
        "K0 status mismatch",
    )
    require(
        k0_result.get("ready_for_recovery_k_preflight")
        is True,
        "K0 not ready for preflight",
    )

    artifact_specs = [
        (
            "article_input",
            "article_input_path",
            "article_input_file_sha256",
            "article_input_artifact_digest_sha256",
            "article_input_digest_sha256",
        ),
        (
            "human_review",
            "human_review_path",
            "human_review_file_sha256",
            "human_review_artifact_digest_sha256",
            "human_review_digest_sha256",
        ),
        (
            "content_generation_contract",
            "content_generation_contract_path",
            "content_generation_contract_file_sha256",
            "content_generation_contract_artifact_digest_sha256",
            "content_generation_contract_digest_sha256",
        ),
        (
            "template_reconciliation_contract",
            "template_reconciliation_contract_path",
            "template_reconciliation_contract_file_sha256",
            "template_reconciliation_contract_artifact_digest_sha256",
            "template_reconciliation_contract_digest_sha256",
        ),
        (
            "authorization",
            "authorization_path",
            "authorization_file_sha256",
            "authorization_artifact_digest_sha256",
            "authorization_digest_sha256",
        ),
    ]

    artifacts: dict[str, dict[str, Any]] = {}

    for (
        label,
        path_field,
        file_hash_field,
        artifact_digest_field,
        self_digest_field,
    ) in artifact_specs:
        path = resolve_path(
            bindings[path_field]
        )
        value = load_json(path)

        require(
            file_sha256(path)
            == bindings[file_hash_field],
            f"{label} file hash mismatch",
        )

        stored = verify_self_digest(
            value,
            self_digest_field,
            label,
        )

        require(
            stored
            == bindings[
                artifact_digest_field
            ],
            f"{label} artifact digest reference mismatch",
        )

        artifacts[label] = value

    article_input = artifacts[
        "article_input"
    ]
    human_review = artifacts[
        "human_review"
    ]
    content_contract = artifacts[
        "content_generation_contract"
    ]
    reconciliation_contract = artifacts[
        "template_reconciliation_contract"
    ]
    authorization = artifacts[
        "authorization"
    ]

    expected_identity = {
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "work_title": "ダークギャザリング",
        "volume_label": "第20巻",
        "article_title": (
            "ダークギャザリング 第20巻｜配信開始"
        ),
        "release_date": "2026-07-03",
        "author_name": "近藤憲一",
        "publisher_name": "集英社",
        "wordpress_status": "draft",
    }

    for field, expected in expected_identity.items():
        require(
            article_input.get(field) == expected,
            f"article input mismatch: {field}",
        )

        if field in human_review:
            require(
                human_review.get(field) == expected,
                f"human review mismatch: {field}",
            )

    require(
        article_input.get("input_complete")
        is True,
        "article input incomplete",
    )
    require(
        article_input.get("legacy_post185_reference")
        is False,
        "legacy post185 reference detected",
    )
    require(
        "categories" not in article_input,
        "categories field present in article input",
    )
    require(
        human_review.get("human_review_complete")
        is True,
        "human review incomplete",
    )

    require(
        content_contract.get("contract_id")
        == (
            "FRESH_NEW_RELEASE_COMIC_"
            "CONTENT_GENERATION_V1"
        ),
        "content contract ID mismatch",
    )
    require(
        reconciliation_contract.get("contract_id")
        == (
            "FRESH_NEW_RELEASE_COMIC_"
            "TEMPLATE_RECONCILIATION_V1"
        ),
        "reconciliation contract ID mismatch",
    )
    require(
        reconciliation_contract.get(
            "template_artifact_resolved"
        )
        is True,
        "template artifact not resolved",
    )
    require(
        authorization.get("authorization_id")
        == (
            "DARK_GATHERING_VOLUME_20_"
            "OFFLINE_CONTENT_GENERATION_AUTHORIZATION_V1"
        ),
        "authorization ID mismatch",
    )
    require(
        authorization.get("single_use")
        is True,
        "authorization is not single use",
    )
    require(
        authorization.get("authorization_consumed")
        is False,
        "authorization already consumed",
    )
    require(
        authorization.get("authorized_next_phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "authorization phase mismatch",
    )

    require(
        article_input["price"]["amount"] == 616,
        "price amount mismatch",
    )
    require(
        article_input["price"]["price_text"]
        == "616円（税込）",
        "price text mismatch",
    )
    require(
        article_input["price"]["verification_state"]
        == "VERIFIED",
        "price is not verified",
    )
    require(
        isinstance(
            article_input["price"]["observed_at"],
            str,
        )
        and article_input["price"]["observed_at"],
        "price observation time missing",
    )

    cover = article_input["cover"]

    require(
        cover["verification_state"] == "VERIFIED",
        "cover is not verified",
    )
    require(
        cover["source"] == "rakuten_kobo",
        "cover source mismatch",
    )
    require(
        isinstance(cover["image_url"], str)
        and cover["image_url"].startswith(
            "https://shop.r10s.jp/"
        ),
        "cover URL mismatch",
    )

    store_links = article_input[
        "store_links"
    ]

    for store_name in [
        "amazon",
        "rakuten_kobo",
        "dmm_books",
    ]:
        store = store_links[store_name]

        require(
            store["verification_state"]
            == "VERIFIED",
            f"{store_name} is not verified",
        )
        require(
            store["final_affiliate_link"]
            is False,
            f"{store_name} unexpectedly final affiliate link",
        )

    require(
        store_links["dmm_books"][
            "requires_recheck_before_payload_generation"
        ]
        is True,
        "DMM recheck requirement missing",
    )
    require(
        reconciliation_contract[
            "link_rendering"
        ]["dmm_latest_alias_recheck_completed"]
        is False,
        "DMM recheck unexpectedly complete",
    )

    approval = load_json(
        resolve_path(
            request["preflight_approval_path"]
        )
    )
    approval_digest = verify_self_digest(
        approval,
        "approval_evidence_digest_sha256",
        "preflight approval",
    )

    require(
        digest(approval)
        == request[
            "preflight_approval_digest_sha256"
        ],
        "preflight approval file digest mismatch",
    )
    require(
        approval.get("approval_label")
        == (
            "FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
            "GENERATION_PREFLIGHT_APPROVED"
        ),
        "preflight approval label mismatch",
    )
    require(
        approval.get("human_explicit_approval")
        is True,
        "explicit human approval missing",
    )
    require(
        approval.get("execution_allowed")
        is False,
        "preflight approval unexpectedly allows execution",
    )
    require(
        isinstance(approval_digest, str),
        "preflight approval digest missing",
    )

    require(
        not resolve_path(
            request["reserved_content_output_path"]
        ).exists(),
        "reserved content output already exists",
    )
    require(
        not resolve_path(
            request["consumption_evidence_path"]
        ).exists(),
        "consumption evidence already exists",
    )

    return (
        k0_result,
        article_input,
        human_review,
        content_contract,
        reconciliation_contract,
        authorization,
        [
            "request_identity_verified",
            "preflight_scope_verified",
            "k0_semantic_digest_verified",
            "k0_safe_state_verified",
            "article_input_file_verified",
            "article_input_digest_verified",
            "human_review_file_verified",
            "human_review_digest_verified",
            "content_generation_contract_verified",
            "content_generation_contract_digest_verified",
            "template_reconciliation_contract_verified",
            "template_reconciliation_contract_digest_verified",
            "authorization_file_verified",
            "authorization_digest_verified",
            "authorization_single_use_verified",
            "authorization_unconsumed",
            "article_identity_cross_checked",
            "price_and_observation_verified",
            "current_cover_verified",
            "store_identifiers_verified",
            "store_links_not_final_affiliate_links",
            "dmm_recheck_requirement_verified",
            "preflight_human_approval_verified",
            "content_output_absent",
            "consumption_evidence_absent",
            "network_not_requested",
            "wordpress_not_requested",
        ],
    )


def ensure_plan(
    stable: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if PLAN_PATH.exists():
        existing = load_json(
            PLAN_PATH
        )
        comparable = copy.deepcopy(
            existing
        )
        stored = comparable.pop(
            "preflight_plan_digest_sha256",
            None,
        )
        fixed_at = comparable.pop(
            "preflight_fixed_at_utc",
            None,
        )

        require(
            isinstance(fixed_at, str)
            and fixed_at,
            "existing preflight timestamp invalid",
        )
        require(
            comparable == stable,
            "existing preflight plan semantic mismatch",
        )

        without_digest = copy.deepcopy(
            existing
        )
        without_digest.pop(
            "preflight_plan_digest_sha256",
            None,
        )

        require(
            isinstance(stored, str)
            and digest(without_digest) == stored,
            "existing preflight plan digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(
        stable
    )
    without_digest[
        "preflight_fixed_at_utc"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    plan = copy.deepcopy(
        without_digest
    )
    plan[
        "preflight_plan_digest_sha256"
    ] = digest(without_digest)

    write_json(
        PLAN_PATH,
        plan,
    )

    return plan, True


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
            k0_result,
            article_input,
            human_review,
            content_contract,
            reconciliation_contract,
            authorization,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        authorization_path = resolve_path(
            request["source_bindings"][
                "authorization_path"
            ]
        )
        authorization_hash_before = file_sha256(
            authorization_path
        )

        cover = article_input["cover"]
        price = article_input["price"]
        identifiers = article_input[
            "identifiers"
        ]

        stable_plan = {
            "schema_version": "1.0.0",
            "document_role": (
                "ONE_SHOT_OFFLINE_ARTICLE_CONTENT_"
                "GENERATION_PREFLIGHT_PLAN"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-K-PREFLIGHT"
            ),
            "preflight_id": (
                "DARK_GATHERING_VOLUME_20_"
                "OFFLINE_GENERATION_PREFLIGHT_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "article_identity": {
                "work_title": "ダークギャザリング",
                "volume_label": "第20巻",
                "article_title": (
                    "ダークギャザリング 第20巻｜配信開始"
                ),
                "release_date": "2026-07-03",
                "author_name": "近藤憲一",
                "publisher_name": "集英社",
                "wordpress_status": "draft"
            },
            "template": {
                "template_contract_id": (
                    "POST185_STANDARD_TEMPLATE_V1_FIXED"
                ),
                "template_id": (
                    "POST185_STANDARD_TEMPLATE_V1"
                ),
                "template_artifact_resolved": True,
                "reconciliation_contract_id": (
                    "FRESH_NEW_RELEASE_COMIC_"
                    "TEMPLATE_RECONCILIATION_V1"
                )
            },
            "planned_render": {
                "html_rendered": False,
                "component_order": [
                    "advertising_disclosure",
                    "cover_and_information_card",
                    "store_navigation_slots",
                ],
                "advertising_disclosure": {
                    "element": "p",
                    "css_class": "ebook-pr-disclosure",
                    "exact_text": (
                        "【PR】本記事にはアフィリエイト広告を含みます。"
                        "価格・配信状況は各ストアで確認してください。"
                    )
                },
                "cover": {
                    "required": True,
                    "image_url": cover[
                        "image_url"
                    ],
                    "image_source": cover[
                        "source"
                    ],
                    "verification_state": cover[
                        "verification_state"
                    ],
                    "alt_text": (
                        "ダークギャザリング 第20巻 書影"
                    ),
                    "loading": "lazy",
                    "anchor_element": False,
                    "href": None
                },
                "information_card": {
                    "required": True,
                    "css_class": "ls-store-card",
                    "ordered_fields": [
                        {
                            "field_id": "work_title",
                            "label": "作品名",
                            "value": "ダークギャザリング"
                        },
                        {
                            "field_id": "price",
                            "label": "価格",
                            "value": "616円（税込）"
                        },
                        {
                            "field_id": "author",
                            "label": "作者",
                            "value": "近藤憲一"
                        },
                        {
                            "field_id": "publisher",
                            "label": "出版社",
                            "value": "集英社"
                        },
                        {
                            "field_id": "release_date",
                            "label": "発売日",
                            "value": "2026-07-03"
                        }
                    ],
                    "volume_line_included": False
                },
                "store_navigation": {
                    "css_class": "ls-store-buttons",
                    "render_mode": (
                        "RESERVED_NON_CLICKABLE_SLOTS_ONLY"
                    ),
                    "store_urls_included": False,
                    "final_affiliate_urls_included": False,
                    "slots": [
                        {
                            "order": 1,
                            "store_id": "amazon",
                            "display_name": "Amazon",
                            "identifier_type": "ASIN",
                            "identifier": identifiers[
                                "amazon_asin"
                            ],
                            "render_element": "span",
                            "reserved_css_classes": [
                                "ls-store-btn",
                                "ls-store-amazon",
                                "ls-store-disabled"
                            ],
                            "display_text": (
                                "Amazonで確認（リンク準備中）"
                            ),
                            "aria_disabled": True,
                            "href": None,
                            "url_included": False
                        },
                        {
                            "order": 2,
                            "store_id": "rakuten_kobo",
                            "display_name": "楽天Kobo",
                            "identifier_type": (
                                "RAKUTEN_KOBO_PRODUCT_NUMBER"
                            ),
                            "identifier": identifiers[
                                "rakuten_kobo_product_number"
                            ],
                            "render_element": "span",
                            "reserved_css_classes": [
                                "ls-store-btn",
                                "ls-store-kobo",
                                "ls-store-disabled"
                            ],
                            "display_text": (
                                "楽天Koboで確認（リンク準備中）"
                            ),
                            "aria_disabled": True,
                            "href": None,
                            "url_included": False
                        },
                        {
                            "order": 3,
                            "store_id": "dmm_books",
                            "display_name": "DMMブックス",
                            "identifier_type": (
                                "DMM_SERIES_ID"
                            ),
                            "identifier": identifiers[
                                "dmm_series_id"
                            ],
                            "render_element": "span",
                            "reserved_css_classes": [
                                "ls-store-btn",
                                "ls-store-dmm",
                                "ls-store-disabled"
                            ],
                            "display_text": (
                                "DMMブックスで確認（再確認待ち）"
                            ),
                            "aria_disabled": True,
                            "href": None,
                            "url_included": False,
                            "latest_alias_recheck_required": True,
                            "latest_alias_recheck_completed": False
                        }
                    ]
                }
            },
            "verified_metadata": {
                "price_amount": price["amount"],
                "price_text": price["price_text"],
                "price_currency": price["currency"],
                "price_observed_at": price[
                    "observed_at"
                ],
                "amazon_asin": identifiers[
                    "amazon_asin"
                ],
                "rakuten_kobo_product_number": (
                    identifiers[
                        "rakuten_kobo_product_number"
                    ]
                ),
                "dmm_series_id": identifiers[
                    "dmm_series_id"
                ]
            },
            "content_limits": {
                "description_mode": "minimal",
                "synopsis_included": False,
                "story_detail_included": False,
                "unsupported_claims_included": False,
                "discount_claims_included": False,
                "point_return_claims_included": False,
                "campaign_claims_included": False,
                "inventory_claims_included": False
            },
            "legacy_exclusion": {
                "legacy_product_data_included": False,
                "legacy_urls_included": False,
                "forbidden_product_tokens": [
                    "月曜日のたわわ",
                    "比村奇石",
                    "講談社",
                    "税込792円",
                    "B0H6DQLPPB",
                    "4071859"
                ]
            },
            "link_boundary": {
                "verification_source_urls_copied": False,
                "final_affiliate_urls_generated": False,
                "final_affiliate_urls_rendered": False,
                "dmm_url_copied": False,
                "dmm_url_rendered": False
            },
            "output_contract": {
                "reserved_output_path": (
                    request[
                        "reserved_content_output_path"
                    ]
                ),
                "output_document_role": (
                    "OFFLINE_FRESH_NEW_RELEASE_"
                    "ARTICLE_CONTENT_DRAFT"
                ),
                "content_output_creation_allowed_in_current_phase": False,
                "content_output_overwrite_allowed": False,
                "content_output_exists": False
            },
            "authorization_contract": {
                "authorization_id": (
                    authorization[
                        "authorization_id"
                    ]
                ),
                "authorized_phase_id": (
                    "LS-NEW-BATCH-4G-2E-RECOVERY-K"
                ),
                "single_use": True,
                "authorization_consumed": False,
                "authorization_reuse_allowed": False,
                "consumption_evidence_path": (
                    request[
                        "consumption_evidence_path"
                    ]
                ),
                "consumption_evidence_exists": False
            },
            "source_lineage": {
                "article_input_artifact_digest_sha256": (
                    request["source_bindings"][
                        "article_input_artifact_digest_sha256"
                    ]
                ),
                "human_review_artifact_digest_sha256": (
                    request["source_bindings"][
                        "human_review_artifact_digest_sha256"
                    ]
                ),
                "content_generation_contract_artifact_digest_sha256": (
                    request["source_bindings"][
                        "content_generation_contract_artifact_digest_sha256"
                    ]
                ),
                "template_reconciliation_contract_artifact_digest_sha256": (
                    request["source_bindings"][
                        "template_reconciliation_contract_artifact_digest_sha256"
                    ]
                ),
                "authorization_artifact_digest_sha256": (
                    request["source_bindings"][
                        "authorization_artifact_digest_sha256"
                    ]
                )
            },
            "category_id_injected": False,
            "fresh_payload_created": False,
            "article_content_generated": False,
            "authorization_consumed": False,
            "consumption_evidence_created": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "PREFLIGHT_PLAN_FIXED_"
                "AWAITING_EXPLICIT_RECOVERY_K_EXECUTE_NOW_CONFIRMATION"
            )
        }

        serialized_plan = json.dumps(
            stable_plan,
            ensure_ascii=False,
            sort_keys=True,
        )

        for forbidden_token in stable_plan[
            "legacy_exclusion"
        ]["forbidden_product_tokens"]:
            require(
                forbidden_token
                not in serialized_plan.replace(
                    json.dumps(
                        stable_plan[
                            "legacy_exclusion"
                        ][
                            "forbidden_product_tokens"
                        ],
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "",
                ),
                (
                    "legacy product token leaked outside "
                    f"denylist: {forbidden_token}"
                ),
            )

        for forbidden_url_token in [
            "https://www.amazon.co.jp/dp/",
            "https://books.rakuten.co.jp/rk/",
            "https://book.dmm.com/",
            "https://al.dmm.com/",
            "https://hb.afl.rakuten.co.jp/",
        ]:
            require(
                forbidden_url_token
                not in serialized_plan,
                (
                    "store URL leaked into preflight plan: "
                    + forbidden_url_token
                ),
            )

        plan, created = ensure_plan(
            stable_plan
        )

        require(
            file_sha256(authorization_path)
            == authorization_hash_before,
            "authorization modified during preflight",
        )
        require(
            not OUTPUT_PATH.exists(),
            "content output created during preflight",
        )
        require(
            not CONSUMPTION_PATH.exists(),
            "consumption evidence created during preflight",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-K-PREFLIGHT"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "preflight_plan_path": (
                display_path(PLAN_PATH)
            ),
            "preflight_plan_digest_sha256": (
                plan[
                    "preflight_plan_digest_sha256"
                ]
            ),
            "plan_created_in_this_run": (
                created
            ),
            "all_source_digests_verified": True,
            "planned_structure_fixed": True,
            "store_navigation_slots_only": True,
            "store_urls_included": False,
            "dmm_url_included": False,
            "content_output_exists": False,
            "authorization_consumed": False,
            "consumption_evidence_exists": False,
            "fresh_payload_created": False,
            "category_id_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "verified_checks": (
                policy_checks
                + source_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "preflight_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-K-PREFLIGHT"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
                "GENERATION_PREFLIGHT_NO_CONTENT_"
                "NO_AUTH_CONSUMPTION_NO_NETWORK"
            ),
            "decision": (
                "ALL_SOURCE_DIGESTS_AND_PLANNED_STRUCTURE_"
                "VERIFIED_AWAITING_RECOVERY_K_EXECUTE_NOW_CONFIRMATION"
            ),
            "approval_label": (
                "FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
                "GENERATION_PREFLIGHT_APPROVED"
            ),
            "preflight_plan_path": (
                package[
                    "preflight_plan_path"
                ]
            ),
            "preflight_plan_digest_sha256": (
                package[
                    "preflight_plan_digest_sha256"
                ]
            ),
            "preflight_package_digest_sha256": (
                package[
                    "preflight_package_digest_sha256"
                ]
            ),
            "plan_created_in_this_run": (
                created
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "all_source_digests_verified": True,
            "article_input_verified": True,
            "human_review_verified": True,
            "content_generation_contract_verified": True,
            "template_reconciliation_contract_verified": True,
            "authorization_verified": True,
            "template_artifact_resolved": True,
            "fixed_disclosure_verified": True,
            "current_cover_verified": True,
            "information_card_plan_fixed": True,
            "store_navigation_slots_only": True,
            "store_urls_included": False,
            "final_affiliate_urls_included": False,
            "dmm_url_included": False,
            "dmm_latest_alias_recheck_completed": False,
            "authorization_template_artifact_resolved_field": (
                authorization.get(
                    "template_artifact_resolved"
                )
            ),
            "authorization_consumed": False,
            "authorization_modified": False,
            "consumption_evidence_created": False,
            "content_output_exists": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "PREFLIGHT_PLAN_FIXED_"
                "AWAITING_EXPLICIT_RECOVERY_K_EXECUTE_NOW_CONFIRMATION"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_k": True,
            "ready_for_recovery_k_execute_now_confirmation": True,
            "ready_for_one_shot_offline_article_content_generation": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "preflight_plan_verified",
                    "preflight_plan_digest_verified",
                    "current_article_values_fixed",
                    "current_cover_plan_fixed",
                    "information_card_plan_fixed",
                    "store_slots_plan_fixed",
                    "store_urls_excluded",
                    "dmm_url_excluded",
                    "legacy_product_data_excluded",
                    "authorization_preserved",
                    "authorization_unconsumed",
                    "consumption_evidence_absent",
                    "content_output_absent",
                    "article_content_not_generated",
                    "payload_not_created",
                    "category_id_not_injected",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "execution_gate_closed",
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

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-K-PREFLIGHT

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Work: `{result["work_title"]}`
- Volume: `{result["volume_label"]}`

## Verified Sources

- Article input: `true`
- Human review: `true`
- Content-generation contract: `true`
- Template-reconciliation contract: `true`
- One-shot authorization: `true`

## Planned Structure

- Fixed disclosure: `true`
- Current cover: `true`
- Information card: `作品名・価格・作者・出版社・発売日`
- Store navigation: `non-clickable reserved slots only`
- Store URLs included: `false`
- Final affiliate URLs included: `false`
- DMM URL included: `false`

## Safety Boundary

- Authorization consumed: `false`
- Consumption evidence created: `false`
- Content output exists: `false`
- Article content generated: `false`
- Payload created: `false`
- Category ID injected: `false`
- Network accessed: `false`
- WordPress written: `false`
- Execution allowed: `false`
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
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-K-PREFLIGHT"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "preflight_plan_fixed": False,
            "article_content_generated": False,
            "content_output_created": False,
            "authorization_consumed": False,
            "consumption_evidence_created": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
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
