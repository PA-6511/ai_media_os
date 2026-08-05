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
    "input_human_review_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "input_human_review_request.example.json"
)
REVIEW_PATH = (
    ROOT
    / "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001.human_review.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "input_human_review_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_h_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_h_"
    "human_review_report.md"
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
        "policy_revision",
        "approval_revision",
        "approval_reissued",
        "current_f_result_rebound",
        "superseded_approval_preserved",
        "superseded_approval_modified",
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
        "price_currency",
        "amazon_asin",
        "rakuten_kobo_product_number",
        "dmm_series_id",
        "dmm_latest_alias_recheck_required",
        "categories_initial_state",
        "categories_field_present",
        "legacy_post185_reference",
        "article_input_registered",
        "input_complete",
        "human_review_complete",
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
        "ready_for_ls_new_batch_4g_2e_recovery_h",
        "ready_for_fresh_article_input_human_review"
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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-H",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_FRESH_ARTICLE_INPUT_"
            "HUMAN_REVIEW_RECORDING_ONLY"
        ),
        "operation mode mismatch",
    )

    reviewed = policy["reviewed_article"]

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

    for field, value in expected.items():
        require(
            reviewed.get(field) == value,
            f"reviewed article mismatch: {field}",
        )

    contract = policy[
        "human_review_contract"
    ]

    require(
        contract["human_review_complete"]
        is True,
        "human review must be complete",
    )
    require(
        contract[
            "dmm_latest_alias_recheck_requirement_acknowledged"
        ]
        is True,
        "DMM requirement acknowledgement missing",
    )
    require(
        contract[
            "dmm_latest_alias_recheck_completed"
        ]
        is False,
        "DMM recheck must remain incomplete",
    )
    require(
        contract[
            "source_registration_must_remain_immutable"
        ]
        is True,
        "source registration immutability missing",
    )

    boundary = policy[
        "execution_boundary"
    ]

    require(
        boundary["human_review_recording_allowed"]
        is True,
        "human review recording must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "human_review_recording_allowed",
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
        "reviewed_article_verified",
        "human_review_contract_verified",
        "dmm_requirement_acknowledged",
        "dmm_recheck_not_completed",
        "source_registration_immutability_required",
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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-H",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )
    require(
        request.get(
            "human_review_recording_requested"
        )
        is True,
        "human review recording must be requested",
    )
    require(
        request.get(
            "source_registration_preservation_requested"
        )
        is True,
        "source registration preservation missing",
    )
    require(
        request.get(
            "dmm_recheck_requirement_acknowledgement_requested"
        )
        is True,
        "DMM requirement acknowledgement missing",
    )

    false_fields = [
        "dmm_recheck_execution_requested",
        "source_registration_modification_requested",
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
    source_input_path = resolve_repo_path(
        request["source_input_path"]
    )
    source_input = load_json(
        source_input_path
    )
    source_approval_v2 = load_json(
        resolve_repo_path(
            request["source_approval_v2_path"]
        )
    )
    review_approval = load_json(
        resolve_repo_path(
            request["human_review_approval_path"]
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
            "PASS_FRESH_ARTICLE_INPUT_REGISTERED_"
            "NO_PAYLOAD_NO_NETWORK"
        ),
        "source status mismatch",
    )
    require(
        source_result.get("decision")
        == (
            "DARK_GATHERING_VOLUME_20_INPUT_"
            "REGISTERED_AWAITING_HUMAN_REVIEW"
        ),
        "source decision mismatch",
    )

    required_result_values = {
        "policy_revision": 2,
        "approval_revision": 2,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
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
        "network_connection_performed": False,
        "wordpress_write_performed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
    }

    for field, expected in required_result_values.items():
        require(
            source_result.get(field) == expected,
            f"source result mismatch: {field}",
        )

    require(
        file_sha256(source_input_path)
        == request["source_input_file_sha256"],
        "source input file changed",
    )

    source_input_without_digest = copy.deepcopy(
        source_input
    )
    stored_input_digest = (
        source_input_without_digest.pop(
            "article_input_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_input_digest, str)
        and digest(source_input_without_digest)
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
        source_input.get("human_review_complete")
        is False,
        "source input must remain unmodified",
    )
    require(
        source_input.get("article_content_generated")
        is False,
        "source input content state mismatch",
    )
    require(
        "categories" not in source_input,
        "source input categories field present",
    )

    source_approval_without_digest = copy.deepcopy(
        source_approval_v2
    )
    stored_source_approval_digest = (
        source_approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_source_approval_digest, str)
        and digest(source_approval_without_digest)
        == stored_source_approval_digest,
        "source approval v2 digest invalid",
    )
    require(
        stored_source_approval_digest
        == request[
            "source_approval_v2_digest_sha256"
        ],
        "source approval v2 reference mismatch",
    )

    review_approval_without_digest = copy.deepcopy(
        review_approval
    )
    stored_review_approval_digest = (
        review_approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_review_approval_digest, str)
        and digest(review_approval_without_digest)
        == stored_review_approval_digest,
        "human review approval digest invalid",
    )
    require(
        digest(review_approval)
        == request[
            "human_review_approval_digest_sha256"
        ],
        "human review approval file digest mismatch",
    )
    require(
        review_approval.get("approval_label")
        == "FRESH_ARTICLE_INPUT_HUMAN_REVIEW_APPROVED",
        "human review approval label mismatch",
    )
    require(
        review_approval.get("human_explicit_approval")
        is True,
        "human review approval missing",
    )
    require(
        review_approval[
            "review_confirmation"
        ][
            "dmm_latest_alias_recheck_requirement_acknowledged"
        ]
        is True,
        "DMM acknowledgement missing",
    )
    require(
        review_approval[
            "review_confirmation"
        ][
            "dmm_latest_alias_recheck_completed"
        ]
        is False,
        "DMM recheck must remain incomplete",
    )
    require(
        review_approval.get("execution_allowed")
        is False,
        "review approval must not authorize execution",
    )

    return (
        source_result,
        source_input,
        review_approval,
        [
            "request_identity_verified",
            "human_review_recording_requested",
            "source_registration_preservation_requested",
            "source_result_semantic_digest_verified",
            "source_result_safe_state_verified",
            "source_input_file_hash_verified",
            "source_input_artifact_digest_verified",
            "source_input_unchanged",
            "source_approval_v2_verified",
            "human_review_approval_verified",
            "dmm_requirement_acknowledged",
            "dmm_recheck_not_requested",
            "source_modification_not_requested",
            "content_generation_not_requested",
            "payload_generation_not_requested",
            "category_injection_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
            "execution_not_requested",
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
        stored_digest = comparable.pop(
            "human_review_digest_sha256",
            None,
        )
        reviewed_at = comparable.pop(
            "reviewed_at_utc",
            None,
        )

        require(
            isinstance(reviewed_at, str)
            and reviewed_at != "",
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
            isinstance(stored_digest, str)
            and digest(without_digest)
            == stored_digest,
            "existing review digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(
        stable
    )
    without_digest[
        "reviewed_at_utc"
    ] = utc_now()

    artifact = copy.deepcopy(
        without_digest
    )
    artifact[
        "human_review_digest_sha256"
    ] = digest(without_digest)

    write_json(
        REVIEW_PATH,
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
            source_input,
            review_approval,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        stable_review = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_NEW_RELEASE_ARTICLE_INPUT_"
                "HUMAN_REVIEW"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-H"
            ),
            "review_id": (
                "dark-gathering-volume-20-"
                "fresh-article-input-human-review-v1"
            ),
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
            "review_checklist": {
                "identity_confirmed": True,
                "article_title_confirmed": True,
                "release_date_confirmed": True,
                "author_confirmed": True,
                "publisher_confirmed": True,
                "price_confirmed": True,
                "store_identifiers_confirmed": True,
                "wordpress_draft_status_confirmed": True,
                "categories_absence_confirmed": True,
                "legacy_post185_absence_confirmed": True,
                "dmm_latest_alias_recheck_requirement_acknowledged": True,
                "dmm_latest_alias_recheck_completed": False
            },
            "review_outcome": (
                "APPROVED_FOR_NEXT_CONTENT_"
                "GENERATION_GATE_ONLY"
            ),
            "source_registration": {
                "path": request[
                    "source_input_path"
                ],
                "file_sha256": request[
                    "source_input_file_sha256"
                ],
                "article_input_digest_sha256": (
                    request[
                        "source_input_artifact_digest_sha256"
                    ]
                ),
                "modified": False,
                "human_review_complete_field_in_source": False
            },
            "human_review_approval": {
                "approval_label": review_approval[
                    "approval_label"
                ],
                "approval_evidence_digest_sha256": (
                    review_approval[
                        "approval_evidence_digest_sha256"
                    ]
                ),
                "human_explicit_approval": True,
                "execution_allowed": False
            },
            "human_review_recorded": True,
            "human_review_complete": True,
            "source_registration_modified": False,
            "dmm_recheck_requirement_acknowledged": True,
            "dmm_recheck_completed": False,
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
                "FRESH_ARTICLE_INPUT_HUMAN_REVIEW_"
                "RECORDED_AWAITING_CONTENT_GENERATION_GATE"
            )
        }

        review, created = ensure_review(
            stable_review
        )

        require(
            file_sha256(
                resolve_repo_path(
                    request["source_input_path"]
                )
            )
            == request["source_input_file_sha256"],
            "source input modified during review",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-H"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "review_package_id": (
                "dark-gathering-volume-20-"
                "fresh-article-input-human-review"
            ),
            "review_artifact_path": (
                display_path(REVIEW_PATH)
            ),
            "human_review_digest_sha256": (
                review[
                    "human_review_digest_sha256"
                ]
            ),
            "review_created_in_this_run": (
                created
            ),
            "source_registration_path": (
                request["source_input_path"]
            ),
            "source_registration_file_sha256": (
                request[
                    "source_input_file_sha256"
                ]
            ),
            "source_registration_modified": False,
            "human_review_recorded": True,
            "human_review_complete": True,
            "dmm_recheck_requirement_acknowledged": True,
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
            "human_review_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-H"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_INPUT_HUMAN_"
                "REVIEW_RECORDED_NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "DARK_GATHERING_VOLUME_20_INPUT_"
                "HUMAN_REVIEW_APPROVED_AWAITING_"
                "CONTENT_GENERATION_GATE"
            ),
            "approval_label": (
                "FRESH_ARTICLE_INPUT_"
                "HUMAN_REVIEW_APPROVED"
            ),
            "review_artifact_path": (
                package[
                    "review_artifact_path"
                ]
            ),
            "human_review_digest_sha256": (
                package[
                    "human_review_digest_sha256"
                ]
            ),
            "human_review_package_digest_sha256": (
                package[
                    "human_review_package_digest_sha256"
                ]
            ),
            "review_created_in_this_run": (
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
            "release_date": "2026-07-03",
            "author_name": "近藤憲一",
            "publisher_name": "集英社",
            "wordpress_status": "draft",
            "price_amount": 616,
            "price_text": "616円（税込）",
            "amazon_asin": "B0H3N7QK5K",
            "rakuten_kobo_product_number": (
                "4972000159519"
            ),
            "dmm_series_id": "861056",
            "human_review_recorded": True,
            "human_review_complete": True,
            "source_registration_modified": False,
            "source_registration_human_review_complete": False,
            "dmm_latest_alias_recheck_requirement_acknowledged": True,
            "dmm_latest_alias_recheck_completed": False,
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
                "FRESH_ARTICLE_INPUT_HUMAN_REVIEW_"
                "RECORDED_AWAITING_CONTENT_GENERATION_GATE"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_i": True,
            "ready_for_article_content_generation_gate": True,
            "ready_for_article_content_generation": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_offline_payload_binding": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "human_review_artifact_verified",
                    "human_review_digest_verified",
                    "source_registration_preserved",
                    "human_review_complete_in_review_record",
                    "source_registration_remains_immutable",
                    "dmm_requirement_acknowledged",
                    "dmm_recheck_still_pending",
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

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-H Human Review

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Work: `{result["work_title"]}`
- Volume: `{result["volume_label"]}`

## Human Review

- Human review recorded: `true`
- Human review complete: `true`
- Source registration modified: `false`
- Source registration review field changed: `false`
- DMM recheck requirement acknowledged: `true`
- DMM recheck completed: `false`

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
                "LS-NEW-BATCH-4G-2E-RECOVERY-H"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "human_review_recorded": False,
            "human_review_complete": False,
            "source_registration_modified": False,
            "article_content_generated": False,
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
