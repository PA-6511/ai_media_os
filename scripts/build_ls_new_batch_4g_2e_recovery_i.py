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
    "content_generation_gate_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "content_generation_gate_request.example.json"
)
CONTRACT_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "content_generation_contract.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "content_generation_gate_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_i_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_i_"
    "content_generation_gate_report.md"
)
RESERVED_OUTPUT_PATH = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
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
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(
            f"required file missing: {path}"
        )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise ValidationError(
            f"JSON root must be object: {path}"
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


def resolve_repo_path(value: str) -> Path:
    path = Path(value)

    return (
        path
        if path.is_absolute()
        else ROOT / path
    )


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(
            resolved.relative_to(
                ROOT.resolve()
            )
        )
    except ValueError:
        return str(resolved)


def source_semantic_state(
    source: dict[str, Any],
) -> dict[str, Any]:
    fields = [
        "phase_id",
        "status",
        "decision",
        "approval_label",
        "content_item_id",
        "work_title",
        "volume_label",
        "article_title",
        "release_date",
        "author_name",
        "publisher_name",
        "wordpress_status",
        "price_amount",
        "price_text",
        "amazon_asin",
        "rakuten_kobo_product_number",
        "dmm_series_id",
        "human_review_recorded",
        "human_review_complete",
        "source_registration_modified",
        "dmm_latest_alias_recheck_requirement_acknowledged",
        "dmm_latest_alias_recheck_completed",
        "article_content_generated",
        "fresh_payload_created",
        "fresh_payload_read",
        "fresh_payload_copied",
        "payload_binding_complete",
        "payload_modified",
        "production_category_id_payload_injected",
        "credential_file_read",
        "network_connection_performed",
        "http_request_performed",
        "wordpress_access_performed",
        "wordpress_write_performed",
        "wordpress_draft_created",
        "execution_allowed",
        "production_status",
        "ready_for_ls_new_batch_4g_2e_recovery_i",
        "ready_for_article_content_generation_gate"
    ]

    return {
        field: source.get(field)
        for field in fields
    }


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-I",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_CONTENT_GENERATION_"
            "CONTRACT_FIXATION_ONLY"
        ),
        "operation mode mismatch",
    )
    require(
        policy.get("template_contract_id")
        == "POST185_STANDARD_TEMPLATE_V1_FIXED",
        "template contract mismatch",
    )

    fixed = policy["fixed_article"]

    expected = {
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
        "price_amount": 616,
        "price_text": "616円（税込）",
        "price_currency": "JPY",
        "amazon_asin": "B0H3N7QK5K",
        "rakuten_kobo_product_number": (
            "4972000159519"
        ),
        "dmm_series_id": "861056",
        "categories_initial_state": "ABSENT",
        "legacy_post185_reference": False,
    }

    for field, expected_value in expected.items():
        require(
            fixed.get(field) == expected_value,
            f"fixed article mismatch: {field}",
        )

    disclosure = policy[
        "disclosure_contract"
    ]

    require(
        disclosure[
            "clear_advertising_disclosure_required"
        ]
        is True,
        "advertising disclosure must be required",
    )
    require(
        set(disclosure["allowed_disclosure_labels"])
        == {"PR", "広告"},
        "allowed disclosure labels mismatch",
    )
    require(
        disclosure[
            "affiliate_disclosure_omission_allowed"
        ]
        is False,
        "disclosure omission must be forbidden",
    )

    factuality = policy[
        "factuality_contract"
    ]

    require(
        factuality["verified_source_only"]
        is True,
        "verified-source-only rule missing",
    )

    for field, value in factuality.items():
        if field == "verified_source_only":
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    dmm = policy[
        "dmm_recheck_contract"
    ]

    require(
        dmm[
            "latest_alias_recheck_requirement_inherited"
        ]
        is True,
        "DMM recheck inheritance missing",
    )
    require(
        dmm["latest_alias_recheck_completed"]
        is False,
        "DMM recheck must remain incomplete",
    )
    require(
        dmm[
            "recheck_required_before_payload_generation"
        ]
        is True,
        "DMM pre-payload recheck missing",
    )
    require(
        dmm["network_recheck_allowed_in_current_phase"]
        is False,
        "DMM network recheck must remain blocked",
    )

    boundary = policy[
        "execution_boundary"
    ]

    require(
        boundary[
            "content_generation_contract_fixation_allowed"
        ]
        is True,
        "contract fixation must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "content_generation_contract_fixation_allowed",
            "production_status",
            "safety_state",
        }:
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    require(
        boundary["production_status"] == "NO_GO",
        "production status must remain NO_GO",
    )

    return [
        "policy_phase_verified",
        "operation_mode_verified",
        "template_contract_verified",
        "fixed_article_verified",
        "advertising_disclosure_required",
        "fabrication_prohibitions_verified",
        "source_retention_required",
        "dmm_recheck_requirement_inherited",
        "dmm_recheck_not_completed",
        "execution_boundary_closed",
    ]


def validate_request_and_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-I",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    required_true_fields = [
        "content_generation_contract_fixation_requested",
        "template_contract_inheritance_requested",
        "advertising_disclosure_requirement_requested",
        "source_retention_requirement_requested",
        "fabrication_prohibition_requested",
        "dmm_recheck_requirement_inheritance_requested",
    ]

    for field in required_true_fields:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    required_false_fields = [
        "dmm_recheck_execution_requested",
        "article_content_generation_requested",
        "content_output_creation_requested",
        "fresh_payload_creation_requested",
        "fresh_payload_read_requested",
        "fresh_payload_copy_requested",
        "payload_binding_requested",
        "payload_modification_requested",
        "production_category_id_payload_injection_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_draft_creation_requested",
        "execution_requested",
    ]

    for field in required_false_fields:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    source_result = load_json(
        resolve_repo_path(
            request["source_result_path"]
        )
    )
    source_review_path = resolve_repo_path(
        request["source_review_path"]
    )
    source_review = load_json(
        source_review_path
    )
    source_input_path = resolve_repo_path(
        request["source_input_path"]
    )
    source_input = load_json(
        source_input_path
    )
    gate_approval = load_json(
        resolve_repo_path(
            request[
                "content_generation_gate_approval_path"
            ]
        )
    )

    require(
        digest(source_semantic_state(source_result))
        == request[
            "source_result_semantic_digest_sha256"
        ],
        "source result semantic digest mismatch",
    )
    require(
        source_result.get("status")
        == (
            "PASS_FRESH_ARTICLE_INPUT_HUMAN_"
            "REVIEW_RECORDED_NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
        ),
        "source status mismatch",
    )
    require(
        source_result.get("human_review_complete")
        is True,
        "source review not complete",
    )
    require(
        source_result.get("article_content_generated")
        is False,
        "source content already generated",
    )
    require(
        source_result.get("fresh_payload_created")
        is False,
        "source payload already generated",
    )
    require(
        source_result.get(
            "production_category_id_payload_injected"
        )
        is False,
        "source category already injected",
    )
    require(
        source_result.get("wordpress_write_performed")
        is False,
        "source WordPress write detected",
    )
    require(
        source_result.get("execution_allowed")
        is False,
        "source execution unexpectedly allowed",
    )

    require(
        file_sha256(source_review_path)
        == request["source_review_file_sha256"],
        "source review file changed",
    )

    review_without_digest = copy.deepcopy(
        source_review
    )
    stored_review_digest = review_without_digest.pop(
        "human_review_digest_sha256",
        None,
    )

    require(
        isinstance(stored_review_digest, str)
        and digest(review_without_digest)
        == stored_review_digest,
        "source review digest invalid",
    )
    require(
        stored_review_digest
        == request[
            "source_review_artifact_digest_sha256"
        ],
        "source review digest reference mismatch",
    )
    require(
        source_review.get("human_review_complete")
        is True,
        "human review artifact incomplete",
    )
    require(
        source_review.get("dmm_recheck_completed")
        is False,
        "DMM recheck unexpectedly complete",
    )

    require(
        file_sha256(source_input_path)
        == request["source_input_file_sha256"],
        "source input file changed",
    )

    input_without_digest = copy.deepcopy(
        source_input
    )
    stored_input_digest = input_without_digest.pop(
        "article_input_digest_sha256",
        None,
    )

    require(
        isinstance(stored_input_digest, str)
        and digest(input_without_digest)
        == stored_input_digest,
        "source input digest invalid",
    )
    require(
        stored_input_digest
        == request[
            "source_input_artifact_digest_sha256"
        ],
        "source input digest reference mismatch",
    )
    require(
        "categories" not in source_input,
        "source input categories field present",
    )

    gate_approval_without_digest = copy.deepcopy(
        gate_approval
    )
    stored_gate_approval_digest = (
        gate_approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_gate_approval_digest, str)
        and digest(gate_approval_without_digest)
        == stored_gate_approval_digest,
        "gate approval digest invalid",
    )
    require(
        digest(gate_approval)
        == request[
            "content_generation_gate_approval_digest_sha256"
        ],
        "gate approval file digest mismatch",
    )
    require(
        gate_approval.get("approval_label")
        == (
            "FRESH_ARTICLE_CONTENT_"
            "GENERATION_GATE_APPROVED"
        ),
        "gate approval label mismatch",
    )
    require(
        gate_approval.get("human_explicit_approval")
        is True,
        "explicit gate approval missing",
    )
    require(
        gate_approval.get(
            "article_content_generation_allowed"
        )
        is False,
        "approval must not allow content generation",
    )
    require(
        gate_approval.get("execution_allowed")
        is False,
        "approval must not allow execution",
    )

    return (
        source_result,
        source_review,
        gate_approval,
        [
            "request_identity_verified",
            "contract_fixation_requested",
            "template_inheritance_requested",
            "disclosure_requirement_requested",
            "source_retention_requested",
            "fabrication_prohibition_requested",
            "dmm_recheck_inheritance_requested",
            "source_result_semantic_digest_verified",
            "source_result_safe_state_verified",
            "source_review_file_verified",
            "source_review_digest_verified",
            "source_input_file_verified",
            "source_input_digest_verified",
            "gate_approval_verified",
            "dmm_recheck_not_requested",
            "content_generation_not_requested",
            "content_output_not_requested",
            "payload_generation_not_requested",
            "category_injection_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
            "execution_not_requested",
        ],
    )


def ensure_contract(
    stable: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if CONTRACT_PATH.exists():
        existing = load_json(
            CONTRACT_PATH
        )
        comparable = copy.deepcopy(
            existing
        )
        stored_digest = comparable.pop(
            "content_generation_contract_digest_sha256",
            None,
        )
        fixed_at = comparable.pop(
            "contract_fixed_at_utc",
            None,
        )

        require(
            isinstance(fixed_at, str)
            and fixed_at != "",
            "existing contract timestamp invalid",
        )
        require(
            comparable == stable,
            "existing contract semantic mismatch",
        )

        without_digest = copy.deepcopy(
            existing
        )
        without_digest.pop(
            "content_generation_contract_digest_sha256",
            None,
        )

        require(
            isinstance(stored_digest, str)
            and digest(without_digest)
            == stored_digest,
            "existing contract digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(
        stable
    )
    without_digest[
        "contract_fixed_at_utc"
    ] = utc_now()

    contract = copy.deepcopy(
        without_digest
    )
    contract[
        "content_generation_contract_digest_sha256"
    ] = digest(without_digest)

    write_json(
        CONTRACT_PATH,
        contract,
    )

    return contract, True


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
            source_result,
            source_review,
            gate_approval,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        require(
            not RESERVED_OUTPUT_PATH.exists(),
            "reserved content output already exists",
        )

        stable_contract = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_NEW_RELEASE_ARTICLE_"
                "CONTENT_GENERATION_CONTRACT"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-I"
            ),
            "contract_id": (
                "FRESH_NEW_RELEASE_COMIC_"
                "CONTENT_GENERATION_V1"
            ),
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "output_language": "ja-JP",
            "wordpress_status": "draft",
            "reserved_output_path": (
                "exchange/content/new_release/fresh/"
                "new-release-comic-20260703-001.article.json"
            ),
            "output_document_role": (
                "OFFLINE_FRESH_NEW_RELEASE_"
                "ARTICLE_CONTENT_DRAFT"
            ),
            "template_contract": {
                "template_contract_id": (
                    "POST185_STANDARD_TEMPLATE_V1_FIXED"
                ),
                "existing_template_structure_must_be_used": True,
                "template_structure_redefinition_allowed": False
            },
            "advertising_disclosure": {
                "required": True,
                "allowed_labels": [
                    "PR",
                    "広告"
                ],
                "must_appear_before_store_navigation": True,
                "omission_allowed": False
            },
            "factuality_rules": {
                "verified_source_only": True,
                "fabricated_information_allowed": False,
                "fabricated_synopsis_allowed": False,
                "fabricated_story_detail_allowed": False,
                "fabricated_discount_allowed": False,
                "fabricated_point_return_allowed": False,
                "fabricated_campaign_allowed": False,
                "fabricated_inventory_allowed": False,
                "fabricated_release_date_allowed": False,
                "fabricated_price_allowed": False,
                "copy_paste_explanation_allowed": False,
                "unsupported_superlative_claim_allowed": False
            },
            "verified_metadata": {
                "release_date": "2026-07-03",
                "author_name": "近藤憲一",
                "publisher_name": "集英社",
                "price_amount": 616,
                "price_text": "616円（税込）",
                "price_currency": "JPY",
                "amazon_asin": "B0H3N7QK5K",
                "rakuten_kobo_product_number": (
                    "4972000159519"
                ),
                "dmm_series_id": "861056"
            },
            "source_retention": {
                "publisher_source_required": True,
                "store_source_references_required": True,
                "store_identifiers_required": True,
                "price_observation_time_required": True,
                "cover_source_required": True,
                "source_evidence_removal_allowed": False
            },
            "store_link_rules": {
                "registered_links_are_verification_sources_only": True,
                "registered_links_are_final_affiliate_links": False,
                "final_affiliate_link_generation_allowed": False
            },
            "dmm_recheck_rules": {
                "latest_alias_recheck_requirement_inherited": True,
                "latest_alias_recheck_completed": False,
                "network_recheck_allowed_in_current_phase": False,
                "dmm_url_rendering_before_recheck_allowed": False,
                "dmm_final_link_use_before_recheck_allowed": False,
                "recheck_required_before_payload_generation": True
            },
            "source_lineage": {
                "article_input_path": request[
                    "source_input_path"
                ],
                "article_input_digest_sha256": request[
                    "source_input_artifact_digest_sha256"
                ],
                "human_review_path": request[
                    "source_review_path"
                ],
                "human_review_digest_sha256": request[
                    "source_review_artifact_digest_sha256"
                ],
                "content_generation_gate_approval_digest_sha256": (
                    gate_approval[
                        "approval_evidence_digest_sha256"
                    ]
                )
            },
            "source_registration_overwrite_allowed": False,
            "human_review_artifact_overwrite_allowed": False,
            "content_output_overwrite_allowed": False,
            "categories_field_allowed": False,
            "article_content_generated": False,
            "content_output_created": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "CONTENT_GENERATION_CONTRACT_FIXED_"
                "AWAITING_OFFLINE_GENERATION_APPROVAL"
            )
        }

        contract, created = ensure_contract(
            stable_contract
        )

        require(
            not RESERVED_OUTPUT_PATH.exists(),
            "content output created during gate phase",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-I"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "content_generation_contract_id": (
                contract["contract_id"]
            ),
            "content_generation_contract_path": (
                display_path(CONTRACT_PATH)
            ),
            "content_generation_contract_digest_sha256": (
                contract[
                    "content_generation_contract_digest_sha256"
                ]
            ),
            "contract_created_in_this_run": (
                created
            ),
            "reserved_output_path": (
                display_path(RESERVED_OUTPUT_PATH)
            ),
            "content_output_exists": False,
            "template_contract_inherited": True,
            "advertising_disclosure_required": True,
            "fabrication_prohibited": True,
            "source_retention_required": True,
            "dmm_recheck_requirement_inherited": True,
            "dmm_recheck_completed": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "verified_checks": (
                policy_checks
                + source_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "content_generation_gate_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-I"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_CONTENT_GENERATION_"
                "CONTRACT_FIXED_NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "CONTENT_GENERATION_CONTRACT_READY_"
                "AWAITING_OFFLINE_GENERATION_APPROVAL"
            ),
            "approval_label": (
                "FRESH_ARTICLE_CONTENT_"
                "GENERATION_GATE_APPROVED"
            ),
            "content_generation_contract_id": (
                contract["contract_id"]
            ),
            "content_generation_contract_path": (
                package[
                    "content_generation_contract_path"
                ]
            ),
            "content_generation_contract_digest_sha256": (
                package[
                    "content_generation_contract_digest_sha256"
                ]
            ),
            "content_generation_gate_package_digest_sha256": (
                package[
                    "content_generation_gate_package_digest_sha256"
                ]
            ),
            "contract_created_in_this_run": (
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
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "wordpress_status": "draft",
            "advertising_disclosure_required": True,
            "allowed_disclosure_labels": [
                "PR",
                "広告"
            ],
            "fabricated_information_allowed": False,
            "fabricated_synopsis_allowed": False,
            "fabricated_discount_allowed": False,
            "fabricated_point_return_allowed": False,
            "source_retention_required": True,
            "dmm_latest_alias_recheck_requirement_inherited": True,
            "dmm_latest_alias_recheck_completed": False,
            "dmm_url_rendering_before_recheck_allowed": False,
            "reserved_content_output_path": (
                package["reserved_output_path"]
            ),
            "content_output_exists": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "fresh_payload_read": False,
            "fresh_payload_copied": False,
            "payload_binding_complete": False,
            "payload_modified": False,
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
                "CONTENT_GENERATION_CONTRACT_FIXED_"
                "AWAITING_OFFLINE_GENERATION_APPROVAL"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_j": True,
            "ready_for_offline_article_content_generation_approval": True,
            "ready_for_article_content_generation": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_offline_payload_binding": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "content_generation_contract_verified",
                    "content_generation_contract_digest_verified",
                    "template_contract_inherited",
                    "advertising_disclosure_fixed",
                    "fabrication_prohibitions_fixed",
                    "source_retention_fixed",
                    "dmm_recheck_requirement_carried_forward",
                    "dmm_recheck_still_pending",
                    "reserved_content_output_absent",
                    "article_content_not_generated",
                    "fresh_payload_not_created",
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

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-I Content Generation Gate

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Work: `{result["work_title"]}`
- Volume: `{result["volume_label"]}`
- Template: `{result["template_contract_id"]}`

## Fixed Contract

- Advertising disclosure required: `true`
- Allowed labels: `PR`, `広告`
- Fabricated information allowed: `false`
- Fabricated synopsis allowed: `false`
- Fabricated discount allowed: `false`
- Fabricated point return allowed: `false`
- Source retention required: `true`
- DMM latest-alias recheck inherited: `true`
- DMM recheck completed: `false`

## Execution Boundary

- Content output exists: `false`
- Article content generated: `false`
- Fresh payload created: `false`
- Payload binding complete: `false`
- Category ID injected: `false`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress write performed: `false`
- WordPress draft created: `false`
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-I"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "content_generation_contract_fixed": False,
            "article_content_generated": False,
            "content_output_created": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
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
