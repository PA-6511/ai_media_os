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
    "new_release_wp_fresh_payload_generation_"
    "input_gate_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_payload_generation_"
    "input_gate_request.example.json"
)
CONTRACT_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_payload_generation_"
    "input_contract.json"
)
TEMPLATE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_payload_generation_"
    "input.template.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_payload_generation_"
    "input_gate_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_f_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_f_"
    "input_gate_report.md"
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-F",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_FRESH_PAYLOAD_GENERATION_"
            "INPUT_CONTRACT_FIXATION_ONLY"
        ),
        "operation mode mismatch",
    )

    contract = policy["input_contract"]

    require(
        contract["contract_id"]
        == "FRESH_NEW_RELEASE_COMIC_DRAFT_INPUT_V1",
        "input contract identity mismatch",
    )
    require(
        contract["fixed_wordpress_status"]
        == "draft",
        "WordPress status must be draft",
    )
    require(
        contract["categories_initial_states_allowed"]
        == ["ABSENT", "EMPTY_LIST"],
        "initial category states mismatch",
    )
    require(
        contract[
            "categories_value_before_binding_allowed"
        ]
        is False,
        "category values must be forbidden before binding",
    )
    require(
        contract[
            "legacy_wordpress_post_id_185_reference_allowed"
        ]
        is False,
        "post185 reference must remain forbidden",
    )

    execution = policy["execution_boundary"]

    for field, value in execution.items():
        if field in {
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
        "policy_operation_mode_verified",
        "input_contract_identity_verified",
        "draft_status_fixed",
        "initial_category_state_fixed",
        "post185_reference_forbidden",
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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-F",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )
    require(
        request.get(
            "input_contract_fixation_requested"
        )
        is True,
        "contract fixation must be requested",
    )
    require(
        request.get(
            "incomplete_input_template_creation_requested"
        )
        is True,
        "incomplete template creation must be requested",
    )

    false_fields = [
        "article_input_registration_requested",
        "fresh_payload_creation_requested",
        "fresh_payload_read_requested",
        "fresh_payload_copy_requested",
        "payload_binding_requested",
        "payload_modification_requested",
        "production_category_id_payload_injection_requested",
        "legacy_post185_reference_requested",
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
        ROOT / request["source_result_path"]
    )
    source_plan_path = (
        ROOT / request["source_plan_path"]
    )
    source_plan = load_json(
        source_plan_path
    )
    source_approval = load_json(
        ROOT / request["source_plan_approval_path"]
    )
    approval = load_json(
        ROOT / request["input_gate_approval_path"]
    )

    require(
        digest(source_result)
        == request["source_result_digest_sha256"],
        "source result digest mismatch",
    )
    require(
        file_sha256(source_plan_path)
        == request["source_plan_file_sha256"],
        "source plan file SHA-256 mismatch",
    )
    require(
        digest(source_approval)
        == request[
            "source_plan_approval_digest_sha256"
        ],
        "source approval digest mismatch",
    )
    require(
        digest(approval)
        == request[
            "input_gate_approval_digest_sha256"
        ],
        "input-gate approval digest mismatch",
    )

    source_contract = policy[
        "source_contract"
    ]

    require(
        source_result.get("status")
        == source_contract["required_status"],
        "source status mismatch",
    )
    require(
        source_result.get("decision")
        == source_contract["required_decision"],
        "source decision mismatch",
    )
    require(
        source_result.get(
            "legacy_post185_lineage_excluded"
        )
        is True,
        "source legacy exclusion missing",
    )
    require(
        source_result.get("fresh_payload_created")
        is False,
        "source fresh payload already exists",
    )
    require(
        source_result.get("payload_binding_complete")
        is False,
        "source payload binding already complete",
    )

    plan_without_digest = copy.deepcopy(
        source_plan
    )
    stored_plan_digest = plan_without_digest.pop(
        "plan_artifact_digest_sha256",
        None,
    )

    require(
        isinstance(stored_plan_digest, str)
        and digest(plan_without_digest)
        == stored_plan_digest,
        "source plan artifact digest invalid",
    )
    require(
        stored_plan_digest
        == request[
            "source_plan_artifact_digest_sha256"
        ],
        "source plan digest reference mismatch",
    )
    require(
        source_plan.get("plan_id")
        == source_contract["required_plan_id"],
        "source plan identity mismatch",
    )
    require(
        source_plan["mapping"][
            "production_category_id"
        ]
        == 10,
        "source category ID mismatch",
    )
    require(
        source_plan["legacy_exclusion"][
            "legacy_post185_lineage_excluded"
        ]
        is True,
        "source-plan legacy exclusion missing",
    )
    require(
        source_plan["current_state"][
            "fresh_payload_exists"
        ]
        is False,
        "source plan indicates an existing payload",
    )

    approval_without_digest = copy.deepcopy(
        approval
    )
    stored_approval_digest = (
        approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_approval_digest, str)
        and digest(approval_without_digest)
        == stored_approval_digest,
        "input-gate approval evidence invalid",
    )
    require(
        approval.get("approval_label")
        == (
            "FRESH_PAYLOAD_GENERATION_"
            "INPUT_GATE_APPROVED"
        ),
        "input-gate approval label mismatch",
    )
    require(
        approval.get("human_explicit_approval")
        is True,
        "human approval missing",
    )
    require(
        approval.get("execution_allowed")
        is False,
        "input-gate approval must not authorize execution",
    )

    return (
        source_result,
        source_plan,
        approval,
        [
            "request_identity_verified",
            "contract_fixation_requested",
            "incomplete_template_requested",
            "source_result_digest_verified",
            "source_plan_file_sha256_verified",
            "source_plan_artifact_digest_verified",
            "source_plan_approval_verified",
            "input_gate_human_approval_verified",
            "legacy_post185_exclusion_verified",
            "fresh_payload_absence_verified",
            "payload_binding_absence_verified",
            "article_input_registration_not_requested",
            "payload_generation_not_requested",
            "category_injection_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
            "execution_not_requested",
        ],
    )


def ensure_digest_artifact(
    *,
    path: Path,
    stable: dict[str, Any],
    timestamp_field: str,
    digest_field: str,
) -> tuple[dict[str, Any], bool]:
    if path.exists():
        existing = load_json(path)
        comparison = copy.deepcopy(existing)
        stored_digest = comparison.pop(
            digest_field,
            None,
        )
        timestamp = comparison.pop(
            timestamp_field,
            None,
        )

        require(
            isinstance(timestamp, str)
            and timestamp != "",
            f"{path.name} timestamp invalid",
        )
        require(
            comparison == stable,
            f"{path.name} semantic mismatch",
        )

        without_digest = copy.deepcopy(
            existing
        )
        without_digest.pop(
            digest_field,
            None,
        )

        require(
            isinstance(stored_digest, str)
            and digest(without_digest)
            == stored_digest,
            f"{path.name} digest mismatch",
        )

        return existing, False

    without_digest = copy.deepcopy(stable)
    without_digest[timestamp_field] = utc_now()

    artifact = copy.deepcopy(
        without_digest
    )
    artifact[digest_field] = digest(
        without_digest
    )

    write_json(path, artifact)

    return artifact, True


def main() -> int:
    try:
        policy = load_json(POLICY_PATH)
        request = load_json(REQUEST_PATH)

        policy_checks = validate_policy(
            policy
        )
        (
            _source_result,
            source_plan,
            approval,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        input_contract = policy[
            "input_contract"
        ]

        stable_contract = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-F"
            ),
            "contract_id": input_contract[
                "contract_id"
            ],
            "template_contract_id": policy[
                "template_contract_id"
            ],
            "article_scope_id": input_contract[
                "article_scope_id"
            ],
            "article_scope_label": input_contract[
                "article_scope_label"
            ],
            "required_top_level_fields": input_contract[
                "required_top_level_fields"
            ],
            "content_item_id_pattern": input_contract[
                "content_item_id_pattern"
            ],
            "fixed_article_type": input_contract[
                "fixed_article_type"
            ],
            "fixed_wordpress_status": "draft",
            "release_date_format": "YYYY-MM-DD",
            "article_title_rules": input_contract[
                "article_title_rules"
            ],
            "content_source_contract": input_contract[
                "content_source_contract"
            ],
            "store_link_contract": input_contract[
                "store_link_contract"
            ],
            "cover_contract": input_contract[
                "cover_contract"
            ],
            "price_contract": input_contract[
                "price_contract"
            ],
            "affiliate_disclosure_required": True,
            "categories_initial_states_allowed": [
                "ABSENT",
                "EMPTY_LIST"
            ],
            "categories_value_before_binding_allowed": False,
            "legacy_post185_reference_allowed": False,
            "human_review_required_before_payload_generation": True,
            "source_root": (
                "exchange/payloads/new_release/fresh"
            ),
            "existing_file_overwrite_allowed": False,
            "category_id_10_injection_allowed_during_generation": False,
            "source_plan_id": source_plan[
                "plan_id"
            ],
            "source_plan_artifact_digest_sha256": source_plan[
                "plan_artifact_digest_sha256"
            ],
            "approval_label": approval[
                "approval_label"
            ],
            "approval_evidence_digest_sha256": approval[
                "approval_evidence_digest_sha256"
            ],
            "article_input_registered": False,
            "fresh_payload_created": False,
            "execution_allowed": False,
            "production_status": "NO_GO"
        }

        contract, contract_created = (
            ensure_digest_artifact(
                path=CONTRACT_PATH,
                stable=stable_contract,
                timestamp_field=(
                    "input_contract_fixed_at_utc"
                ),
                digest_field=(
                    "input_contract_digest_sha256"
                ),
            )
        )

        stable_template = {
            "schema_version": "1.0.0",
            "document_role": (
                "NON_EXECUTABLE_INCOMPLETE_INPUT_TEMPLATE"
            ),
            "contract_id": contract[
                "contract_id"
            ],
            "input_complete": False,
            "human_review_complete": False,
            "content_item_id": None,
            "work_title": None,
            "volume_label": None,
            "article_title": None,
            "release_date": None,
            "author_name": None,
            "publisher_name": None,
            "article_type": (
                "COMIC_NEW_RELEASE_LATEST_VOLUME_"
                "DISTRIBUTION_START"
            ),
            "wordpress_status": "draft",
            "content_source": {
                "source_type": None,
                "source_reference": None,
                "human_verified": False
            },
            "store_links": {
                "amazon": {
                    "url": None,
                    "verification_state": "PENDING"
                },
                "rakuten_kobo": {
                    "url": None,
                    "verification_state": "PENDING"
                },
                "dmm_books": {
                    "url": None,
                    "verification_state": "PENDING"
                }
            },
            "cover": {
                "image_url": None,
                "source": None,
                "verification_state": "PENDING"
            },
            "price": {
                "price_text": None,
                "currency": "JPY",
                "observed_at": None,
                "verification_state": "PENDING"
            },
            "affiliate_disclosure_required": True,
            "categories_initial_state": "ABSENT",
            "legacy_post185_reference": False,
            "article_input_registration_requested": False,
            "payload_generation_requested": False,
            "category_id_injection_requested": False,
            "wordpress_execution_requested": False,
            "execution_allowed": False
        }

        template, template_created = (
            ensure_digest_artifact(
                path=TEMPLATE_PATH,
                stable=stable_template,
                timestamp_field=(
                    "input_template_fixed_at_utc"
                ),
                digest_field=(
                    "input_template_digest_sha256"
                ),
            )
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-F"
            ),
            "policy_id": policy["policy_id"],
            "input_contract_path": str(
                CONTRACT_PATH.relative_to(ROOT)
            ),
            "input_contract_digest_sha256": contract[
                "input_contract_digest_sha256"
            ],
            "input_template_path": str(
                TEMPLATE_PATH.relative_to(ROOT)
            ),
            "input_template_digest_sha256": template[
                "input_template_digest_sha256"
            ],
            "contract_created_in_this_run": (
                contract_created
            ),
            "template_created_in_this_run": (
                template_created
            ),
            "article_input_registered": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "category_id_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "verified_checks": (
                policy_checks
                + source_checks
            )
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "input_gate_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-F"
            ),
            "status": (
                "PASS_FRESH_PAYLOAD_GENERATION_"
                "INPUT_CONTRACT_FIXED_NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "INPUT_CONTRACT_READY_AWAITING_"
                "FRESH_ARTICLE_INPUT_REGISTRATION"
            ),
            "approval_label": (
                "FRESH_PAYLOAD_GENERATION_"
                "INPUT_GATE_APPROVED"
            ),
            "input_contract_id": contract[
                "contract_id"
            ],
            "input_contract_path": package[
                "input_contract_path"
            ],
            "input_contract_digest_sha256": package[
                "input_contract_digest_sha256"
            ],
            "input_template_path": package[
                "input_template_path"
            ],
            "input_template_digest_sha256": package[
                "input_template_digest_sha256"
            ],
            "input_gate_package_digest_sha256": package[
                "input_gate_package_digest_sha256"
            ],
            "contract_created_in_this_run": (
                contract_created
            ),
            "template_created_in_this_run": (
                template_created
            ),
            "fixed_wordpress_status": "draft",
            "production_category_id": 10,
            "production_category_name": "最新巻",
            "categories_initial_states_allowed": [
                "ABSENT",
                "EMPTY_LIST"
            ],
            "legacy_post185_reference_allowed": False,
            "article_input_registered": False,
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
                "FRESH_PAYLOAD_INPUT_CONTRACT_"
                "FIXED_NO_ARTICLE_INPUT"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_g": True,
            "ready_for_fresh_article_input_registration": True,
            "ready_for_fresh_payload_generation": False,
            "ready_for_offline_payload_binding": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "input_contract_artifact_verified",
                    "input_contract_digest_verified",
                    "incomplete_input_template_verified",
                    "input_template_digest_verified",
                    "article_input_not_registered",
                    "fresh_payload_not_created",
                    "category_id_not_injected",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "execution_gate_closed",
                ]
            )
        }

        write_json(PACKAGE_PATH, package)
        write_json(RESULT_PATH, result)

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-F Input Gate

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Input contract: `{result["input_contract_id"]}`
- WordPress status: `draft`

## Fixed Boundaries

- Legacy post185 reference allowed: `false`
- Article input registered: `false`
- Fresh payload created: `false`
- Categories before binding: `ABSENT` or `EMPTY_LIST`
- Category ID 10 injected: `false`
- WordPress access performed: `false`
- WordPress write performed: `false`

## Next State

A separate human-reviewed phase must register one concrete fresh
new-release article input. This phase does not generate a payload.
"""

        REPORT_PATH.write_text(
            report,
            encoding="utf-8",
        )
        os.chmod(REPORT_PATH, 0o600)

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
                "LS-NEW-BATCH-4G-2E-RECOVERY-F"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "article_input_registered": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO"
        }
        write_json(RESULT_PATH, failure)
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
