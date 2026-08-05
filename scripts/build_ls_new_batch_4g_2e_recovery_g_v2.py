#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "input_registration_v2_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "input_registration_request_v2.example.json"
)
INPUT_PATH = (
    ROOT
    / "exchange/inputs/new_release/fresh/"
    "new-release-comic-20260703-001.input.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "input_registration_package_v2.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_g_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_g_"
    "article_input_registration_report.md"
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


def validate_url(
    value: str,
    allowed_hosts: set[str],
    label: str,
) -> None:
    parsed = urlparse(value)

    require(
        parsed.scheme == "https",
        f"{label} must use https",
    )
    require(
        parsed.hostname in allowed_hosts,
        f"{label} host mismatch",
    )


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-G",
        "policy phase mismatch",
    )
    require(
        policy.get("policy_revision") == 2,
        "policy revision mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_FRESH_ARTICLE_INPUT_"
            "REGISTRATION_REISSUE_V2_ONLY"
        ),
        "operation mode mismatch",
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
        "categories_initial_state": "ABSENT",
        "legacy_post185_reference": False,
    }

    for field, value in expected.items():
        require(
            fixed.get(field) == value,
            f"fixed article mismatch: {field}",
        )

    approval = policy[
        "approval_contract"
    ]

    require(
        approval[
            "superseded_approval_must_be_preserved"
        ]
        is True,
        "old approval preservation missing",
    )
    require(
        approval[
            "superseded_approval_modification_allowed"
        ]
        is False,
        "old approval modification must be false",
    )
    require(
        approval[
            "human_explicit_reissue_approval_required"
        ]
        is True,
        "reissue approval must be required",
    )

    boundary = policy[
        "execution_boundary"
    ]

    require(
        boundary["approval_reissue_allowed"]
        is True,
        "approval reissue must be allowed",
    )
    require(
        boundary[
            "article_input_registration_allowed"
        ]
        is True,
        "article registration must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "approval_reissue_allowed",
            "article_input_registration_allowed",
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
        "policy_revision_2_verified",
        "operation_mode_verified",
        "fixed_article_verified",
        "old_approval_preservation_required",
        "reissue_approval_required",
        "registration_only_boundary_verified",
        "execution_boundary_closed",
    ]


def validate_request_and_lineage(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-G",
        "request phase mismatch",
    )
    require(
        request.get("request_version") == 2,
        "request version mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )
    require(
        request.get("approval_reissue_requested")
        is True,
        "approval reissue must be requested",
    )
    require(
        request.get(
            "superseded_approval_preservation_requested"
        )
        is True,
        "old approval preservation must be requested",
    )
    require(
        request.get(
            "article_input_registration_requested"
        )
        is True,
        "registration must be requested",
    )

    false_fields = [
        "human_review_completion_requested",
        "article_content_generation_requested",
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

    for field in false_fields:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    source_result = load_json(
        resolve_repo_path(
            request["source_result_path"]
        )
    )
    source_contract_path = resolve_repo_path(
        request["source_contract_path"]
    )
    source_contract = load_json(
        source_contract_path
    )
    source_template_path = resolve_repo_path(
        request["source_template_path"]
    )
    source_template = load_json(
        source_template_path
    )
    old_approval_path = resolve_repo_path(
        request["superseded_approval_path"]
    )
    old_approval = load_json(
        old_approval_path
    )
    approval_v2 = load_json(
        resolve_repo_path(
            request["approval_v2_path"]
        )
    )

    require(
        digest(source_result)
        == request["source_result_digest_sha256"],
        "current F result digest mismatch",
    )

    stable_source_fields = {
        "phase_id": source_result["phase_id"],
        "status": source_result["status"],
        "decision": source_result["decision"],
        "approval_label": source_result[
            "approval_label"
        ],
        "input_contract_id": source_result[
            "input_contract_id"
        ],
        "input_contract_digest_sha256": source_result[
            "input_contract_digest_sha256"
        ],
        "input_template_digest_sha256": source_result[
            "input_template_digest_sha256"
        ],
        "fixed_wordpress_status": source_result[
            "fixed_wordpress_status"
        ],
        "production_category_id": source_result[
            "production_category_id"
        ],
        "production_category_name": source_result[
            "production_category_name"
        ],
        "legacy_post185_reference_allowed": source_result[
            "legacy_post185_reference_allowed"
        ],
        "article_input_registered": source_result[
            "article_input_registered"
        ],
        "fresh_payload_created": source_result[
            "fresh_payload_created"
        ],
        "payload_binding_complete": source_result[
            "payload_binding_complete"
        ],
        "production_category_id_payload_injected": (
            source_result[
                "production_category_id_payload_injected"
            ]
        ),
        "wordpress_write_performed": source_result[
            "wordpress_write_performed"
        ],
        "execution_allowed": source_result[
            "execution_allowed"
        ],
        "production_status": source_result[
            "production_status"
        ],
    }

    require(
        digest(stable_source_fields)
        == request["source_semantic_digest_sha256"],
        "current F semantic digest mismatch",
    )

    required_status = (
        "PASS_FRESH_PAYLOAD_GENERATION_"
        "INPUT_CONTRACT_FIXED_NO_PAYLOAD_NO_NETWORK"
    )
    required_decision = (
        "INPUT_CONTRACT_READY_AWAITING_"
        "FRESH_ARTICLE_INPUT_REGISTRATION"
    )

    require(
        source_result.get("status")
        == required_status,
        "source status mismatch",
    )
    require(
        source_result.get("decision")
        == required_decision,
        "source decision mismatch",
    )

    for field in [
        "article_input_registered",
        "fresh_payload_created",
        "fresh_payload_read",
        "fresh_payload_copied",
        "payload_binding_complete",
        "payload_modified",
        "production_category_id_payload_injected",
        "network_connection_performed",
        "http_request_performed",
        "wordpress_access_performed",
        "wordpress_write_performed",
        "wordpress_draft_created",
        "execution_allowed",
    ]:
        require(
            source_result.get(field) is False,
            f"source unsafe field: {field}",
        )

    require(
        source_result.get("production_status")
        == "NO_GO",
        "source must remain NO_GO",
    )

    require(
        file_sha256(source_contract_path)
        == request[
            "source_contract_file_sha256"
        ],
        "source contract file hash mismatch",
    )

    contract_without_digest = copy.deepcopy(
        source_contract
    )
    stored_contract_digest = (
        contract_without_digest.pop(
            "input_contract_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_contract_digest, str)
        and digest(contract_without_digest)
        == stored_contract_digest,
        "source contract digest invalid",
    )
    require(
        stored_contract_digest
        == request[
            "source_contract_artifact_digest_sha256"
        ],
        "source contract digest reference mismatch",
    )

    require(
        file_sha256(source_template_path)
        == request[
            "source_template_file_sha256"
        ],
        "source template file hash mismatch",
    )

    template_without_digest = copy.deepcopy(
        source_template
    )
    stored_template_digest = (
        template_without_digest.pop(
            "input_template_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_template_digest, str)
        and digest(template_without_digest)
        == stored_template_digest,
        "source template digest invalid",
    )
    require(
        stored_template_digest
        == request[
            "source_template_artifact_digest_sha256"
        ],
        "source template digest reference mismatch",
    )

    old_without_digest = copy.deepcopy(
        old_approval
    )
    stored_old_digest = old_without_digest.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        isinstance(stored_old_digest, str)
        and digest(old_without_digest)
        == stored_old_digest,
        "superseded approval digest invalid",
    )
    require(
        stored_old_digest
        == request[
            "superseded_approval_evidence_digest_sha256"
        ],
        "superseded approval digest reference mismatch",
    )
    require(
        file_sha256(old_approval_path)
        == request[
            "superseded_approval_file_sha256"
        ],
        "superseded approval was modified",
    )

    approval_v2_without_digest = copy.deepcopy(
        approval_v2
    )
    stored_v2_digest = (
        approval_v2_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_v2_digest, str)
        and digest(approval_v2_without_digest)
        == stored_v2_digest,
        "approval v2 digest invalid",
    )
    require(
        digest(approval_v2)
        == request[
            "approval_v2_file_digest_sha256"
        ],
        "approval v2 file digest mismatch",
    )
    require(
        approval_v2.get("approval_revision") == 2,
        "approval v2 revision mismatch",
    )
    require(
        approval_v2.get("approval_label")
        == "FRESH_ARTICLE_INPUT_REGISTRATION_APPROVED",
        "approval v2 label mismatch",
    )
    require(
        approval_v2.get("reissue_approval_label")
        == (
            "FRESH_ARTICLE_INPUT_REGISTRATION_"
            "APPROVAL_REISSUE_APPROVED"
        ),
        "reissue approval label mismatch",
    )
    require(
        approval_v2.get(
            "human_explicit_reissue_approval"
        )
        is True,
        "human reissue approval missing",
    )
    require(
        approval_v2.get(
            "current_source_result_digest_sha256"
        )
        == digest(source_result),
        "approval v2 source binding mismatch",
    )
    require(
        approval_v2["superseded_approval"][
            "preserved"
        ]
        is True,
        "superseded approval preservation missing",
    )
    require(
        approval_v2.get("execution_allowed")
        is False,
        "approval v2 must not authorize execution",
    )

    return (
        source_result,
        source_contract,
        old_approval,
        approval_v2,
        [
            "request_identity_verified",
            "approval_reissue_requested",
            "old_approval_preservation_requested",
            "registration_requested",
            "current_f_result_digest_verified",
            "current_f_semantic_digest_verified",
            "current_f_safe_state_verified",
            "source_contract_verified",
            "source_template_verified",
            "superseded_approval_digest_verified",
            "superseded_approval_file_preserved",
            "approval_v2_digest_verified",
            "approval_v2_source_binding_verified",
            "human_reissue_approval_verified",
            "human_review_not_requested",
            "content_generation_not_requested",
            "payload_generation_not_requested",
            "category_injection_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
            "execution_not_requested",
        ],
    )


def validate_article(
    article: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    fixed = policy["fixed_article"]

    for field, expected in fixed.items():
        require(
            article.get(field) == expected,
            f"article mismatch: {field}",
        )

    require(
        re.fullmatch(
            r"new-release-comic-[0-9]{8}-[0-9]{3}",
            article["content_item_id"],
        )
        is not None,
        "content item ID format mismatch",
    )

    try:
        parsed_date = date.fromisoformat(
            article["release_date"]
        )
    except ValueError as exc:
        raise ValidationError(
            "release date format invalid"
        ) from exc

    require(
        parsed_date.isoformat()
        == "2026-07-03",
        "release date mismatch",
    )
    require(
        article["article_title"].endswith(
            "｜配信開始"
        ),
        "article title suffix mismatch",
    )
    require(
        "Kindle版" not in article[
            "article_title"
        ],
        "Kindle label forbidden",
    )
    require(
        "categories" not in article,
        "categories field forbidden before binding",
    )

    content_source = article.get(
        "content_source"
    )

    require(
        isinstance(content_source, dict),
        "content source missing",
    )
    require(
        content_source.get("human_verified")
        is True,
        "content source must be verified",
    )
    require(
        content_source.get(
            "runtime_network_verification_performed"
        )
        is False,
        "runtime network verification must be false",
    )

    references = content_source.get(
        "source_references"
    )

    require(
        isinstance(references, list)
        and len(references) == 4,
        "source reference count mismatch",
    )

    refs = {
        item["source_id"]: item
        for item in references
        if isinstance(item, dict)
        and isinstance(item.get("source_id"), str)
    }

    require(
        set(refs) == {
            "shueisha_official",
            "amazon_kindle",
            "rakuten_kobo",
            "dmm_books",
        },
        "source reference identity mismatch",
    )

    validate_url(
        refs["shueisha_official"]["url"],
        {"www.shueisha.co.jp"},
        "Shueisha source",
    )
    validate_url(
        refs["amazon_kindle"]["url"],
        {"www.amazon.co.jp"},
        "Amazon source",
    )
    validate_url(
        refs["rakuten_kobo"]["url"],
        {"books.rakuten.co.jp"},
        "Rakuten source",
    )
    validate_url(
        refs["dmm_books"]["url"],
        {"book.dmm.com"},
        "DMM source",
    )

    for source in refs.values():
        require(
            source.get("verification_state")
            == "VERIFIED",
            "source verification state mismatch",
        )

    require(
        refs["dmm_books"].get("url_kind")
        == "SERIES_LATEST_ALIAS",
        "DMM URL kind mismatch",
    )
    require(
        refs["dmm_books"].get(
            "requires_recheck_before_payload_generation"
        )
        is True,
        "DMM recheck flag missing",
    )

    stores = article.get("store_links")

    require(
        isinstance(stores, dict),
        "store links missing",
    )
    require(
        set(stores) == {
            "amazon",
            "rakuten_kobo",
            "dmm_books",
        },
        "store identities mismatch",
    )

    require(
        stores["amazon"][
            "product_identifier"
        ]
        == "B0H3N7QK5K",
        "Amazon ASIN mismatch",
    )
    require(
        stores["rakuten_kobo"][
            "product_identifier"
        ]
        == "4972000159519",
        "Rakuten product number mismatch",
    )
    require(
        stores["dmm_books"][
            "product_identifier"
        ]
        == "861056",
        "DMM series ID mismatch",
    )

    for store_id, store in stores.items():
        require(
            store["verification_state"]
            == "VERIFIED",
            f"{store_id} verification mismatch",
        )
        require(
            store["final_affiliate_link"]
            is False,
            f"{store_id} final affiliate flag must be false",
        )

    require(
        stores["dmm_books"][
            "requires_recheck_before_payload_generation"
        ]
        is True,
        "DMM generation recheck missing",
    )

    cover = article.get("cover")

    require(
        isinstance(cover, dict),
        "cover data missing",
    )
    validate_url(
        cover["image_url"],
        {"shop.r10s.jp"},
        "cover image",
    )
    validate_url(
        cover["source_page_url"],
        {"books.rakuten.co.jp"},
        "cover source page",
    )
    require(
        cover["source"] == "rakuten_kobo",
        "cover source mismatch",
    )
    require(
        cover["verification_state"]
        == "VERIFIED",
        "cover verification mismatch",
    )
    require(
        cover["local_copy_created"] is False,
        "cover local copy must remain false",
    )

    price = article.get("price")

    require(
        isinstance(price, dict),
        "price data missing",
    )
    require(
        price["amount"] == 616,
        "price amount mismatch",
    )
    require(
        price["price_text"]
        == "616円（税込）",
        "price text mismatch",
    )
    require(
        price["currency"] == "JPY",
        "price currency mismatch",
    )
    require(
        price["verification_state"]
        == "VERIFIED",
        "price verification mismatch",
    )
    require(
        set(price["verification_sources"])
        == {
            "rakuten_kobo",
            "dmm_books",
        },
        "price verification source mismatch",
    )
    require(
        price["automatic_refresh_performed"]
        is False,
        "automatic price refresh must be false",
    )

    identifiers = article.get(
        "identifiers"
    )

    require(
        isinstance(identifiers, dict),
        "identifier data missing",
    )
    require(
        identifiers["isbn_13"]
        == "9784088851204",
        "ISBN mismatch",
    )
    require(
        identifiers["amazon_asin"]
        == "B0H3N7QK5K",
        "ASIN mismatch",
    )
    require(
        identifiers[
            "rakuten_kobo_product_number"
        ]
        == "4972000159519",
        "Rakuten identifier mismatch",
    )
    require(
        identifiers["dmm_series_id"]
        == "861056",
        "DMM identifier mismatch",
    )

    return [
        "content_item_id_verified",
        "article_identity_verified",
        "release_date_verified",
        "author_verified",
        "publisher_verified",
        "draft_status_verified",
        "categories_field_absent",
        "legacy_post185_reference_false",
        "four_sources_verified",
        "store_identifiers_verified",
        "cover_source_verified",
        "price_616_verified",
        "price_two_source_verification_verified",
        "dmm_latest_alias_recheck_required",
        "affiliate_disclosure_required",
    ]


def ensure_registration(
    stable: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if INPUT_PATH.exists():
        existing = load_json(INPUT_PATH)
        comparable = copy.deepcopy(
            existing
        )
        stored_digest = comparable.pop(
            "article_input_digest_sha256",
            None,
        )
        registered_at = comparable.pop(
            "registered_at_utc",
            None,
        )

        require(
            isinstance(registered_at, str)
            and registered_at != "",
            "existing registration timestamp invalid",
        )
        require(
            comparable == stable,
            "existing registration semantic mismatch",
        )

        without_digest = copy.deepcopy(
            existing
        )
        without_digest.pop(
            "article_input_digest_sha256",
            None,
        )

        require(
            isinstance(stored_digest, str)
            and digest(without_digest)
            == stored_digest,
            "existing registration digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(
        stable
    )
    without_digest[
        "registered_at_utc"
    ] = utc_now()

    artifact = copy.deepcopy(
        without_digest
    )
    artifact[
        "article_input_digest_sha256"
    ] = digest(without_digest)

    write_json(
        INPUT_PATH,
        artifact,
    )

    return artifact, True


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
            source_contract,
            old_approval,
            approval_v2,
            lineage_checks,
        ) = validate_request_and_lineage(
            request,
            policy,
        )

        article = request.get(
            "article_input"
        )

        require(
            isinstance(article, dict),
            "article input missing",
        )

        article_checks = validate_article(
            article,
            policy,
        )

        stable_registration = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_NEW_RELEASE_ARTICLE_"
                "INPUT_REGISTRATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-G"
            ),
            "registration_revision": 2,
            "contract_id": (
                "FRESH_NEW_RELEASE_COMIC_DRAFT_INPUT_V1"
            ),
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "input_complete": True,
            "human_registration_approval_recorded": True,
            "human_review_complete": False,
            **copy.deepcopy(article),
            "approval_lineage": {
                "approval_revision": 2,
                "approval_label": approval_v2[
                    "approval_label"
                ],
                "reissue_approval_label": (
                    approval_v2[
                        "reissue_approval_label"
                    ]
                ),
                "approval_evidence_digest_sha256": (
                    approval_v2[
                        "approval_evidence_digest_sha256"
                    ]
                ),
                "superseded_approval_path": (
                    request[
                        "superseded_approval_path"
                    ]
                ),
                "superseded_approval_evidence_digest_sha256": (
                    request[
                        "superseded_approval_evidence_digest_sha256"
                    ]
                ),
                "superseded_approval_preserved": True,
                "current_source_result_digest_sha256": (
                    digest(source_result)
                ),
                "human_explicit_reissue_approval": True,
                "execution_allowed": False,
            },
            "source_input_contract": {
                "path": request[
                    "source_contract_path"
                ],
                "input_contract_digest_sha256": (
                    source_contract[
                        "input_contract_digest_sha256"
                    ]
                ),
            },
            "article_input_registered": True,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "fresh_payload_read": False,
            "fresh_payload_copied": False,
            "payload_binding_complete": False,
            "payload_modified": False,
            "production_category_id_payload_injected": False,
            "credential_file_read": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "FRESH_ARTICLE_INPUT_REGISTERED_"
                "VIA_APPROVAL_V2_AWAITING_HUMAN_REVIEW"
            ),
        }

        require(
            "categories"
            not in stable_registration,
            "registration must not contain categories",
        )

        registration, created = (
            ensure_registration(
                stable_registration
            )
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-G"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "policy_revision": 2,
            "approval_revision": 2,
            "registration_package_id": (
                "dark-gathering-volume-20-"
                "fresh-article-input-registration-v2"
            ),
            "registration_artifact_path": (
                display_path(INPUT_PATH)
            ),
            "article_input_digest_sha256": (
                registration[
                    "article_input_digest_sha256"
                ]
            ),
            "registration_created_in_this_run": (
                created
            ),
            "superseded_approval_preserved": True,
            "superseded_approval_digest_sha256": (
                request[
                    "superseded_approval_evidence_digest_sha256"
                ]
            ),
            "approval_v2_digest_sha256": (
                approval_v2[
                    "approval_evidence_digest_sha256"
                ]
            ),
            "current_source_result_digest_sha256": (
                digest(source_result)
            ),
            "article_input_registered": True,
            "input_complete": True,
            "human_review_complete": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "verified_checks": (
                policy_checks
                + lineage_checks
                + article_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "registration_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-G"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_INPUT_REGISTERED_"
                "NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "DARK_GATHERING_VOLUME_20_INPUT_"
                "REGISTERED_AWAITING_HUMAN_REVIEW"
            ),
            "policy_revision": 2,
            "approval_revision": 2,
            "approval_label": (
                "FRESH_ARTICLE_INPUT_"
                "REGISTRATION_APPROVED"
            ),
            "reissue_approval_label": (
                "FRESH_ARTICLE_INPUT_REGISTRATION_"
                "APPROVAL_REISSUE_APPROVED"
            ),
            "approval_reissued": True,
            "current_f_result_rebound": True,
            "superseded_approval_preserved": True,
            "superseded_approval_modified": False,
            "registration_artifact_path": (
                package[
                    "registration_artifact_path"
                ]
            ),
            "article_input_digest_sha256": (
                package[
                    "article_input_digest_sha256"
                ]
            ),
            "registration_package_digest_sha256": (
                package[
                    "registration_package_digest_sha256"
                ]
            ),
            "registration_created_in_this_run": (
                created
            ),
            "content_item_id": registration[
                "content_item_id"
            ],
            "work_title": registration[
                "work_title"
            ],
            "volume_label": registration[
                "volume_label"
            ],
            "article_title": registration[
                "article_title"
            ],
            "release_date": registration[
                "release_date"
            ],
            "author_name": registration[
                "author_name"
            ],
            "publisher_name": registration[
                "publisher_name"
            ],
            "wordpress_status": "draft",
            "price_amount": 616,
            "price_text": "616円（税込）",
            "price_currency": "JPY",
            "amazon_asin": "B0H3N7QK5K",
            "rakuten_kobo_product_number": (
                "4972000159519"
            ),
            "dmm_series_id": "861056",
            "dmm_latest_alias_recheck_required": True,
            "categories_initial_state": "ABSENT",
            "categories_field_present": False,
            "legacy_post185_reference": False,
            "article_input_registered": True,
            "input_complete": True,
            "human_review_complete": False,
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
                "FRESH_ARTICLE_INPUT_REGISTERED_"
                "VIA_APPROVAL_V2_AWAITING_HUMAN_REVIEW"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_h": True,
            "ready_for_fresh_article_input_human_review": True,
            "ready_for_article_content_generation": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_offline_payload_binding": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "registration_artifact_verified",
                    "registration_digest_verified",
                    "approval_v2_recorded",
                    "superseded_approval_preserved",
                    "input_complete",
                    "human_review_pending",
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

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-G Article Input Registration

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Approval revision: `2`
- Approval reissued: `true`
- Superseded approval preserved: `true`

## Registered Article

- Work: `{result["work_title"]}`
- Volume: `{result["volume_label"]}`
- Article title: `{result["article_title"]}`
- Release date: `{result["release_date"]}`
- Author: `{result["author_name"]}`
- Publisher: `{result["publisher_name"]}`
- Price: `{result["price_text"]}`

## Registration Boundary

- Article input registered: `true`
- Input complete: `true`
- Human review complete: `false`
- Categories field present: `false`
- Legacy post185 reference: `false`
- DMM latest alias recheck required: `true`

## Execution Boundary

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
                "LS-NEW-BATCH-4G-2E-RECOVERY-G"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "approval_revision": 2,
            "article_input_registered": False,
            "human_review_complete": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
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
