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
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_store_link_"
    "finalization_plan_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_store_link_"
    "finalization_plan_request.example.json"
)
PLAN_PATH = (
    ROOT
    / "exchange/plans/new_release/fresh/"
    "new-release-comic-20260703-001."
    "store_link_finalization_plan.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_store_link_"
    "finalization_plan_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m0_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_m0_"
    "store_link_finalization_plan_report.md"
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


def validate_url(
    url: str,
    expected_host: str,
    label: str,
) -> None:
    parsed = urlparse(url)

    require(
        parsed.scheme == "https",
        f"{label} must use HTTPS",
    )
    require(
        parsed.hostname == expected_host,
        f"{label} host mismatch",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        f"{label} URL userinfo forbidden",
    )


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M0",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_STORE_LINK_FINALIZATION_"
            "PLAN_FIXATION_ONLY"
        ),
        "operation mode mismatch",
    )
    require(
        policy["store_order"]
        == [
            "amazon",
            "rakuten_kobo",
            "dmm_books",
        ],
        "store order mismatch",
    )

    common = policy[
        "common_final_link_requirements"
    ]

    require(
        common["https_required"] is True,
        "HTTPS requirement missing",
    )
    require(
        common["rel_required_tokens"]
        == [
            "nofollow",
            "sponsored",
            "noopener",
        ],
        "required rel tokens mismatch",
    )

    for field in [
        "javascript_scheme_allowed",
        "data_scheme_allowed",
        "url_userinfo_allowed",
        "dummy_url_allowed",
        "placeholder_url_allowed",
        "verification_source_url_as_final_link_allowed",
    ]:
        require(
            common[field] is False,
            f"{field} must remain false",
        )

    require(
        policy["dmm_books"][
            "latest_alias_recheck_required"
        ]
        is True,
        "DMM recheck requirement missing",
    )
    require(
        policy["dmm_books"][
            "latest_alias_recheck_completed"
        ]
        is False,
        "DMM recheck must remain incomplete",
    )
    require(
        policy["dmm_books"][
            "series_latest_alias_as_final_link_allowed"
        ]
        is False,
        "DMM latest alias must not be final link",
    )

    failure = policy[
        "failure_handling"
    ]

    require(
        failure[
            "all_store_links_unavailable"
        ]
        == "BLOCK_PAYLOAD_GENERATION",
        "all-store failure handling mismatch",
    )
    require(
        failure[
            "minimum_valid_final_link_count_for_future_payload"
        ]
        == 1,
        "minimum link count mismatch",
    )
    require(
        failure[
            "unresolved_store_slot_rendering_allowed"
        ]
        is False,
        "unresolved slot rendering must be false",
    )

    boundary = policy[
        "execution_boundary"
    ]

    require(
        boundary[
            "store_link_finalization_plan_creation_allowed"
        ]
        is True,
        "plan creation must be allowed",
    )
    require(
        boundary[
            "verification_source_url_read_from_registered_input_allowed"
        ]
        is True,
        "source URL reading must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "store_link_finalization_plan_creation_allowed",
            "verification_source_url_read_from_registered_input_allowed",
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
        "store_order_verified",
        "common_link_requirements_verified",
        "dummy_and_placeholder_urls_forbidden",
        "dmm_recheck_requirement_verified",
        "dmm_latest_alias_final_use_blocked",
        "failure_handling_verified",
        "plan_only_boundary_verified",
    ]


def validate_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Path],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M0",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    for field in [
        "store_identifier_definition_requested",
        "verification_source_url_definition_requested",
        "affiliate_conversion_requirement_definition_requested",
        "dmm_latest_alias_recheck_requirement_definition_requested",
        "store_order_definition_requested",
        "link_attribute_definition_requested",
        "failure_and_hide_condition_definition_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "actual_affiliate_link_generation_requested",
        "final_affiliate_link_validation_requested",
        "article_url_injection_requested",
        "generated_article_modification_requested",
        "content_review_modification_requested",
        "consumption_evidence_modification_requested",
        "dmm_recheck_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
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

    path_specs = {
        "l_result": (
            "recovery_l_result_path",
            "recovery_l_result_file_sha256",
        ),
        "content_review": (
            "content_human_review_path",
            "content_human_review_file_sha256",
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
    }

    paths: dict[str, Path] = {}
    values: dict[str, dict[str, Any]] = {}

    for label, (
        path_field,
        hash_field,
    ) in path_specs.items():
        path = resolve_path(
            bindings[path_field]
        )

        require(
            path.exists(),
            f"source path missing: {label}",
        )
        require(
            file_sha256(path)
            == bindings[hash_field],
            f"source hash mismatch: {label}",
        )

        paths[label] = path
        values[label] = load_json(
            path
        )

    l_result = values[
        "l_result"
    ]
    content_review = values[
        "content_review"
    ]
    article = values["article"]
    consumption = values[
        "consumption"
    ]
    article_input = values[
        "input"
    ]

    require(
        l_result.get("status")
        == (
            "PASS_FRESH_ARTICLE_CONTENT_HUMAN_REVIEW_"
            "APPROVED_NO_CHANGE_NO_PAYLOAD_NO_NETWORK"
        ),
        "Recovery L status mismatch",
    )
    require(
        l_result.get(
            "ready_for_store_link_finalization_gate"
        )
        is True,
        "Recovery L not ready for link gate",
    )
    require(
        l_result.get(
            "ready_for_dmm_recheck_gate"
        )
        is True,
        "Recovery L not ready for DMM gate",
    )

    verify_self_digest(
        content_review,
        "human_review_digest_sha256",
        bindings[
            "content_human_review_artifact_digest_sha256"
        ],
        "content human review",
    )
    verify_self_digest(
        article,
        "article_content_digest_sha256",
        bindings[
            "generated_article_artifact_digest_sha256"
        ],
        "generated article",
    )
    verify_self_digest(
        consumption,
        "consumption_evidence_digest_sha256",
        bindings[
            "consumption_evidence_artifact_digest_sha256"
        ],
        "consumption evidence",
    )
    verify_self_digest(
        article_input,
        "article_input_digest_sha256",
        bindings[
            "article_input_artifact_digest_sha256"
        ],
        "article input",
    )

    require(
        content_review[
            "human_review_complete"
        ]
        is True,
        "content review incomplete",
    )
    require(
        content_review[
            "review_decision"
        ]
        == "APPROVED_NO_CHANGE_REQUIRED",
        "content review decision mismatch",
    )
    require(
        content_review[
            "content_approved_for_store_link_finalization_gate"
        ]
        is True,
        "content not approved for link gate",
    )

    require(
        consumption[
            "authorization_consumed"
        ]
        is True,
        "generation authorization not consumed",
    )
    require(
        consumption[
            "authorization_reuse_allowed"
        ]
        is False,
        "generation authorization reuse not blocked",
    )

    content = article[
        "content_html"
    ]

    require(
        "<a " not in content.lower(),
        "generated article already contains anchor",
    )
    require(
        "href=" not in content.lower(),
        "generated article already contains href",
    )
    require(
        article[
            "store_navigation"
        ]["verification_source_urls_included"]
        is False,
        "generated article contains store URLs",
    )
    require(
        article[
            "store_navigation"
        ]["final_affiliate_urls_included"]
        is False,
        "generated article contains affiliate URLs",
    )

    stores = article_input.get(
        "store_links"
    )

    require(
        isinstance(stores, dict),
        "store links object missing",
    )

    expected = {
        "amazon": {
            "url": (
                "https://www.amazon.co.jp/dp/"
                "B0H3N7QK5K"
            ),
            "type": "ASIN",
            "identifier": "B0H3N7QK5K",
            "kind": "STABLE_PRODUCT_URL",
            "host": "www.amazon.co.jp",
            "recheck": False,
        },
        "rakuten_kobo": {
            "url": (
                "https://books.rakuten.co.jp/rk/"
                "2d876b43205136b7a0d36a78cec5bf46/"
            ),
            "type": (
                "RAKUTEN_KOBO_PRODUCT_NUMBER"
            ),
            "identifier": "4972000159519",
            "kind": "STABLE_PRODUCT_URL",
            "host": "books.rakuten.co.jp",
            "recheck": False,
        },
        "dmm_books": {
            "url": (
                "https://book.dmm.com/product/"
                "861056/latest/"
            ),
            "type": "DMM_SERIES_ID",
            "identifier": "861056",
            "kind": "SERIES_LATEST_ALIAS",
            "host": "book.dmm.com",
            "recheck": True,
        },
    }

    for store_id, expected_store in expected.items():
        store = stores.get(
            store_id
        )

        require(
            isinstance(store, dict),
            f"store missing: {store_id}",
        )
        require(
            store.get("url")
            == expected_store["url"],
            f"store URL mismatch: {store_id}",
        )
        require(
            store.get(
                "product_identifier_type"
            )
            == expected_store["type"],
            f"identifier type mismatch: {store_id}",
        )
        require(
            store.get(
                "product_identifier"
            )
            == expected_store[
                "identifier"
            ],
            f"identifier mismatch: {store_id}",
        )
        require(
            store.get("url_kind")
            == expected_store["kind"],
            f"URL kind mismatch: {store_id}",
        )
        require(
            store.get("link_role")
            == (
                "PRODUCT_VERIFICATION_SOURCE_"
                "NOT_FINAL_AFFILIATE_LINK"
            ),
            f"link role mismatch: {store_id}",
        )
        require(
            store.get(
                "verification_state"
            )
            == "VERIFIED",
            f"verification state mismatch: {store_id}",
        )
        require(
            store.get(
                "final_affiliate_link"
            )
            is False,
            f"source unexpectedly final affiliate: {store_id}",
        )
        require(
            store.get(
                "requires_recheck_before_payload_generation"
            )
            is expected_store["recheck"],
            f"recheck mismatch: {store_id}",
        )

        validate_url(
            store["url"],
            expected_store["host"],
            store_id,
        )

    approval = load_json(
        resolve_path(
            request[
                "plan_approval_path"
            ]
        )
    )
    comparable = copy.deepcopy(
        approval
    )
    stored_approval_digest = (
        comparable.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(
            stored_approval_digest,
            str,
        )
        and digest(comparable)
        == stored_approval_digest,
        "plan approval digest invalid",
    )
    require(
        digest(approval)
        == request[
            "plan_approval_digest_sha256"
        ],
        "plan approval file digest mismatch",
    )
    require(
        approval.get("approval_label")
        == (
            "FRESH_STORE_LINK_FINALIZATION_"
            "PLAN_APPROVED"
        ),
        "plan approval label mismatch",
    )
    require(
        approval.get(
            "human_explicit_approval"
        )
        is True,
        "explicit human approval missing",
    )

    return (
        content_review,
        article,
        consumption,
        article_input,
        paths,
        [
            "request_identity_verified",
            "plan_scope_verified",
            "recovery_l_result_verified",
            "content_review_verified",
            "generated_article_verified",
            "consumption_evidence_verified",
            "article_input_verified",
            "source_artifact_digests_verified",
            "generated_article_has_no_store_urls",
            "store_identifiers_verified",
            "verification_source_urls_verified",
            "verification_links_not_final_affiliate_links",
            "dmm_latest_alias_recheck_requirement_verified",
            "human_plan_approval_verified",
            "network_not_requested",
            "wordpress_not_requested",
        ],
    )


def ensure_plan(
    stable: dict[str, Any],
) -> tuple[
    dict[str, Any],
    bool,
]:
    if PLAN_PATH.exists():
        existing = load_json(
            PLAN_PATH
        )
        comparable = copy.deepcopy(
            existing
        )
        stored = comparable.pop(
            "store_link_finalization_plan_digest_sha256",
            None,
        )
        fixed_at = comparable.pop(
            "plan_fixed_at_utc",
            None,
        )

        require(
            isinstance(fixed_at, str)
            and fixed_at,
            "existing plan timestamp invalid",
        )
        require(
            comparable == stable,
            "existing plan semantic mismatch",
        )

        without_digest = copy.deepcopy(
            existing
        )
        without_digest.pop(
            "store_link_finalization_plan_digest_sha256",
            None,
        )

        require(
            isinstance(stored, str)
            and digest(without_digest)
            == stored,
            "existing plan digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(
        stable
    )
    without_digest[
        "plan_fixed_at_utc"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    plan = copy.deepcopy(
        without_digest
    )
    plan[
        "store_link_finalization_plan_digest_sha256"
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
            content_review,
            article,
            consumption,
            article_input,
            source_paths,
            source_checks,
        ) = validate_sources(
            request,
            policy,
        )

        hashes_before = {
            label: file_sha256(path)
            for label, path
            in source_paths.items()
        }

        stores = article_input[
            "store_links"
        ]

        stable_plan = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_STORE_LINK_FINALIZATION_PLAN"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M0"
            ),
            "plan_id": (
                "DARK_GATHERING_VOLUME_20_"
                "STORE_LINK_FINALIZATION_PLAN_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "article_identity": {
                "article_title": (
                    "ダークギャザリング 第20巻｜配信開始"
                ),
                "work_title": "ダークギャザリング",
                "volume_label": "第20巻"
            },
            "source_content_review": {
                "review_decision": (
                    content_review[
                        "review_decision"
                    ]
                ),
                "content_approved_for_store_link_finalization_gate": True
            },
            "store_order": [
                "amazon",
                "rakuten_kobo",
                "dmm_books",
            ],
            "common_link_contract": {
                "scheme": "https",
                "target": "_blank",
                "required_rel_tokens": [
                    "nofollow",
                    "sponsored",
                    "noopener",
                ],
                "dummy_url_allowed": False,
                "placeholder_url_allowed": False,
                "javascript_url_allowed": False,
                "data_url_allowed": False,
                "url_userinfo_allowed": False,
                "verification_source_url_may_be_used_as_final_link": False,
                "product_identity_binding_required": True,
                "human_review_required_after_finalization": True
            },
            "stores": {
                "amazon": {
                    "order": 1,
                    "display_name": "Amazon",
                    "identifier": {
                        "type": (
                            stores["amazon"][
                                "product_identifier_type"
                            ]
                        ),
                        "value": (
                            stores["amazon"][
                                "product_identifier"
                            ]
                        )
                    },
                    "verification_source": {
                        "url": stores[
                            "amazon"
                        ]["url"],
                        "url_kind": stores[
                            "amazon"
                        ]["url_kind"],
                        "role": stores[
                            "amazon"
                        ]["link_role"],
                        "verification_state": (
                            stores["amazon"][
                                "verification_state"
                            ]
                        ),
                        "is_final_affiliate_link": False
                    },
                    "finalization": {
                        "status": "PLANNED_NOT_EXECUTED",
                        "method": (
                            "APPROVED_AMAZON_AFFILIATE_"
                            "PROVIDER_OR_APPROVED_MANUAL_BUILDER"
                        ),
                        "hardcoded_affiliate_tag_allowed": False,
                        "product_binding_rule": (
                            "FINAL_DESTINATION_MUST_MATCH_ASIN_"
                            "B0H3N7QK5K"
                        ),
                        "legacy_post185_link_reuse_allowed": False,
                        "final_affiliate_url": None,
                        "ready": False
                    },
                    "failure_action": (
                        "HIDE_STORE_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                    )
                },
                "rakuten_kobo": {
                    "order": 2,
                    "display_name": "楽天Kobo",
                    "identifier": {
                        "type": (
                            stores["rakuten_kobo"][
                                "product_identifier_type"
                            ]
                        ),
                        "value": (
                            stores["rakuten_kobo"][
                                "product_identifier"
                            ]
                        )
                    },
                    "verification_source": {
                        "url": stores[
                            "rakuten_kobo"
                        ]["url"],
                        "url_kind": stores[
                            "rakuten_kobo"
                        ]["url_kind"],
                        "role": stores[
                            "rakuten_kobo"
                        ]["link_role"],
                        "verification_state": (
                            stores["rakuten_kobo"][
                                "verification_state"
                            ]
                        ),
                        "is_final_affiliate_link": False
                    },
                    "finalization": {
                        "status": "PLANNED_NOT_EXECUTED",
                        "method": (
                            "APPROVED_RAKUTEN_"
                            "AFFILIATE_DEEPLINK_BUILDER"
                        ),
                        "required_final_host": (
                            "hb.afl.rakuten.co.jp"
                        ),
                        "destination_product_binding_rule": (
                            "DESTINATION_MUST_MATCH_REGISTERED_"
                            "RAKUTEN_KOBO_PRODUCT"
                        ),
                        "legacy_post185_link_reuse_allowed": False,
                        "final_affiliate_url": None,
                        "ready": False
                    },
                    "failure_action": (
                        "HIDE_STORE_SLOT_NO_DUMMY_URL"
                    )
                },
                "dmm_books": {
                    "order": 3,
                    "display_name": "DMMブックス",
                    "identifier": {
                        "type": (
                            stores["dmm_books"][
                                "product_identifier_type"
                            ]
                        ),
                        "value": (
                            stores["dmm_books"][
                                "product_identifier"
                            ]
                        )
                    },
                    "verification_source": {
                        "url": stores[
                            "dmm_books"
                        ]["url"],
                        "url_kind": stores[
                            "dmm_books"
                        ]["url_kind"],
                        "role": stores[
                            "dmm_books"
                        ]["link_role"],
                        "verification_state": (
                            stores["dmm_books"][
                                "verification_state"
                            ]
                        ),
                        "is_final_affiliate_link": False
                    },
                    "recheck": {
                        "required": True,
                        "completed": False,
                        "mode": (
                            "ONE_SHOT_READ_ONLY_GET"
                        ),
                        "network_authorization_required": True,
                        "expected_work_title": (
                            "ダークギャザリング"
                        ),
                        "expected_volume_label": "第20巻",
                        "expected_author_name": "近藤憲一",
                        "expected_publisher_name": "集英社",
                        "canonical_product_resolution_required": True,
                        "series_latest_alias_may_be_final_link": False,
                        "recheck_result_path": None
                    },
                    "finalization": {
                        "status": (
                            "BLOCKED_AWAITING_DMM_RECHECK"
                        ),
                        "method": (
                            "APPROVED_DMM_AFFILIATE_"
                            "LINK_BUILDER_AFTER_RECHECK"
                        ),
                        "required_final_host": "al.dmm.com",
                        "affiliate_id_source": (
                            "APPROVED_NONSECRET_"
                            "CONFIGURATION_ONLY"
                        ),
                        "legacy_post185_link_reuse_allowed": False,
                        "final_affiliate_url": None,
                        "ready": False
                    },
                    "failure_action": (
                        "HIDE_DMM_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                    )
                }
            },
            "failure_contract": {
                "product_identity_mismatch": (
                    "HIDE_STORE_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                ),
                "verification_source_unreachable": (
                    "KEEP_ARTICLE_UNCHANGED_AND_RETURN_TO_REVIEW"
                ),
                "affiliate_conversion_failure": (
                    "HIDE_FAILED_STORE_SLOT_NO_DUMMY_URL"
                ),
                "invalid_final_host": (
                    "REJECT_FINAL_LINK_AND_RETURN_TO_REVIEW"
                ),
                "invalid_scheme": (
                    "REJECT_FINAL_LINK_AND_RETURN_TO_REVIEW"
                ),
                "missing_required_rel_token": (
                    "REJECT_RENDERING_AND_RETURN_TO_REVIEW"
                ),
                "dmm_latest_alias_mismatch": (
                    "HIDE_DMM_SLOT_AND_RETURN_TO_HUMAN_REVIEW"
                ),
                "dmm_canonical_product_unresolved": (
                    "HIDE_DMM_SLOT_AND_KEEP_DMM_LINK_UNAVAILABLE"
                ),
                "all_store_links_unavailable": (
                    "BLOCK_PAYLOAD_GENERATION"
                ),
                "partial_store_links_available": (
                    "REQUIRE_EXPLICIT_HUMAN_APPROVAL_BEFORE_PAYLOAD"
                ),
                "minimum_valid_final_link_count_for_future_payload": 1,
                "unresolved_store_slot_rendering_allowed": False
            },
            "current_state": {
                "verification_source_urls_recorded": True,
                "verification_source_urls_injected_into_article": False,
                "final_affiliate_links_generated": False,
                "final_affiliate_links_validated": False,
                "final_affiliate_links_injected_into_article": False,
                "dmm_latest_alias_recheck_completed": False,
                "generated_article_modified": False,
                "content_review_modified": False,
                "consumption_evidence_modified": False,
                "fresh_payload_created": False,
                "production_category_id_payload_injected": False,
                "network_access_performed": False,
                "wordpress_access_performed": False,
                "wordpress_write_performed": False,
                "execution_allowed": False,
                "production_status": "NO_GO",
                "safety_state": (
                    "STORE_LINK_FINALIZATION_PLAN_FIXED_"
                    "AWAITING_DMM_RECHECK_AUTHORIZATION"
                )
            },
            "source_lineage": {
                "content_human_review_artifact_digest_sha256": (
                    request["source_bindings"][
                        "content_human_review_artifact_digest_sha256"
                    ]
                ),
                "generated_article_artifact_digest_sha256": (
                    request["source_bindings"][
                        "generated_article_artifact_digest_sha256"
                    ]
                ),
                "consumption_evidence_artifact_digest_sha256": (
                    request["source_bindings"][
                        "consumption_evidence_artifact_digest_sha256"
                    ]
                ),
                "article_input_artifact_digest_sha256": (
                    request["source_bindings"][
                        "article_input_artifact_digest_sha256"
                    ]
                )
            },
            "next_gate": {
                "phase_id": (
                    "LS-NEW-BATCH-4G-2E-RECOVERY-M1"
                ),
                "required_action": (
                    "EXPLICIT_DMM_ONE_SHOT_READ_ONLY_"
                    "RECHECK_AUTHORIZATION"
                ),
                "network_allowed": False
            }
        }

        plan, created = ensure_plan(
            stable_plan
        )

        for label, path in source_paths.items():
            require(
                file_sha256(path)
                == hashes_before[label],
                f"source artifact modified: {label}",
            )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M0"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "plan_path": (
                display_path(PLAN_PATH)
            ),
            "plan_file_sha256": (
                file_sha256(PLAN_PATH)
            ),
            "plan_digest_sha256": (
                plan[
                    "store_link_finalization_plan_digest_sha256"
                ]
            ),
            "plan_created_in_this_run": (
                created
            ),
            "store_order_fixed": True,
            "verification_source_urls_recorded": True,
            "final_affiliate_links_generated": False,
            "dmm_recheck_completed": False,
            "source_artifacts_modified": False,
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
            "store_link_finalization_plan_package_digest_sha256"
        ] = digest(
            package_without_digest
        )

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M0"
            ),
            "status": (
                "PASS_FRESH_STORE_LINK_FINALIZATION_PLAN_"
                "FIXED_NO_LINK_GENERATION_NO_NETWORK"
            ),
            "decision": (
                "STORE_IDENTIFIERS_AND_FINALIZATION_REQUIREMENTS_"
                "FIXED_AWAITING_DMM_RECHECK_AUTHORIZATION"
            ),
            "approval_label": (
                "FRESH_STORE_LINK_FINALIZATION_PLAN_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "plan_path": package[
                "plan_path"
            ],
            "plan_file_sha256": (
                package[
                    "plan_file_sha256"
                ]
            ),
            "store_link_finalization_plan_digest_sha256": (
                package[
                    "plan_digest_sha256"
                ]
            ),
            "store_link_finalization_plan_package_digest_sha256": (
                package[
                    "store_link_finalization_plan_package_digest_sha256"
                ]
            ),
            "plan_created_in_this_run": (
                created
            ),
            "store_order": [
                "amazon",
                "rakuten_kobo",
                "dmm_books",
            ],
            "amazon_identifier_verified": True,
            "rakuten_kobo_identifier_verified": True,
            "dmm_series_identifier_verified": True,
            "verification_source_urls_recorded": True,
            "verification_source_urls_are_final_affiliate_links": False,
            "amazon_finalization_requirement_fixed": True,
            "rakuten_finalization_requirement_fixed": True,
            "dmm_finalization_requirement_fixed": True,
            "dmm_latest_alias_recheck_required": True,
            "dmm_latest_alias_recheck_completed": False,
            "common_link_attributes_fixed": True,
            "failure_and_hide_conditions_fixed": True,
            "dummy_urls_allowed": False,
            "placeholder_urls_allowed": False,
            "unresolved_store_slot_rendering_allowed": False,
            "final_affiliate_links_generated": False,
            "final_affiliate_links_validated": False,
            "article_url_injection_performed": False,
            "generated_article_modified": False,
            "content_review_modified": False,
            "consumption_evidence_modified": False,
            "source_artifacts_modified": False,
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
                "STORE_LINK_FINALIZATION_PLAN_FIXED_"
                "AWAITING_DMM_RECHECK_AUTHORIZATION"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m1": True,
            "ready_for_dmm_recheck_authorization": True,
            "ready_for_actual_dmm_recheck": False,
            "ready_for_final_affiliate_link_generation": False,
            "ready_for_article_url_injection": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "store_link_finalization_plan_verified",
                    "store_link_finalization_plan_digest_verified",
                    "verification_source_urls_recorded_as_sources_only",
                    "amazon_finalization_requirement_fixed",
                    "rakuten_finalization_requirement_fixed",
                    "dmm_recheck_plan_fixed",
                    "link_attribute_contract_fixed",
                    "failure_hide_contract_fixed",
                    "no_final_affiliate_link_generated",
                    "no_article_url_injection",
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

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M0 Store Link Finalization Plan

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Article: `{result["article_title"]}`

## Store Plan

1. Amazon
   - Identifier: `ASIN B0H3N7QK5K`
   - Finalization: approved provider or approved manual builder
   - Final link generated: `false`

2. 楽天Kobo
   - Identifier: `4972000159519`
   - Required affiliate host: `hb.afl.rakuten.co.jp`
   - Final link generated: `false`

3. DMMブックス
   - Series ID: `861056`
   - Latest-alias recheck required: `true`
   - Latest-alias recheck completed: `false`
   - Final link generated: `false`

## Common Link Contract

- HTTPS: required
- target: `_blank`
- rel: `nofollow sponsored noopener`
- Dummy URL: forbidden
- Placeholder URL: forbidden
- Verification source URL as final affiliate URL: forbidden

## Failure Boundary

- Failed store: hide the store slot
- DMM mismatch/unresolved: hide DMM and return to review
- All stores unavailable: block payload generation
- Partial links: require explicit human approval

## Current Phase Boundary

- Generated article modified: `false`
- Final affiliate links generated: `false`
- Article URL injection: `false`
- DMM network recheck: `false`
- Payload created: `false`
- Category ID injected: `false`
- Network accessed: `false`
- WordPress written: `false`
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-M0"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "store_link_finalization_plan_fixed": False,
            "final_affiliate_links_generated": False,
            "dmm_latest_alias_recheck_completed": False,
            "article_url_injection_performed": False,
            "generated_article_modified": False,
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
