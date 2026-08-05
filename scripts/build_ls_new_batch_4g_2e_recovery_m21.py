#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def block_network(
    *args: Any,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "NETWORK_OPERATION_BLOCKED_BY_M21"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_compliant_layout_revision_"
    "human_approval_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m21_approval.json"
)

M19_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_published_post_human_review_changes_required.json"
)
M19_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m19_result.json"
)
M20_COMPLIANCE = ROOT / (
    "exchange/compliance/new_release/fresh/"
    "new-release-comic-20260703-001."
    "pr_disclosure_position_compliance_assessment.json"
)
M20_DESIGN = ROOT / (
    "exchange/designs/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_design.json"
)
M20_UPDATE_DRAFT = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_update_draft_payload.json"
)
M20_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m20_result.json"
)

ADOPTION = ROOT / (
    "exchange/decisions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_compliant_layout_revision_adoption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m21_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m21_"
    "wordpress_compliant_layout_revision_"
    "human_approval_report.md"
)

EXPECTED_M19_REVIEW_DIGEST = (
    "ee9cc3be321c2c592afc0c784c002d95"
    "06a598cf9a2072e3c1e205d662417db1"
)
EXPECTED_M19_RESULT_DIGEST = (
    "e02748eead2f2d578fbb86c5e53140f5"
    "26d0d8ac6fa4ec95774c266ffeaa9aaa"
)
EXPECTED_M20_COMPLIANCE_DIGEST = (
    "957874620811effbae144f86a5b4b7a0"
    "6e5fa12001aaee0608307db71654dc01"
)
EXPECTED_M20_DESIGN_DIGEST = (
    "e49bbaf98e529986f0c04956b909029f"
    "2055e2eb0f9e19e100a002e265caf495"
)
EXPECTED_M20_UPDATE_DRAFT_DIGEST = (
    "489ca68a4b9e923df7c87035a7d47436"
    "4403d719bdd52fd484091cf9d6d654d8"
)
EXPECTED_M20_RESULT_DIGEST = (
    "564f734dd840a5be3653eeffd4ecf816"
    "13cada7b74b125645e53428637ccb301"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    code: str,
) -> None:
    if not condition:
        raise ValidationError(code)


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.exists() and path.is_file(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )
    require(
        not path.is_symlink(),
        f"JSON_SYMLINK_REJECTED:{path.name}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise ValidationError(
            f"JSON_PARSE_FAILED:{path.name}"
        ) from None

    require(
        isinstance(value, dict),
        f"JSON_ROOT_NOT_OBJECT:{path.name}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    field: str,
    expected: str | None = None,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"DIGEST_EXPECTED_MISMATCH:{field}",
        )

    return stored


def add_digest(
    value: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = digest(value)
    return result


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_text(
    path: Path,
    value: str,
) -> None:
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    source_paths = {
        "m19_review": M19_REVIEW,
        "m19_result": M19_RESULT,
        "m20_compliance": M20_COMPLIANCE,
        "m20_design": M20_DESIGN,
        "m20_update_draft": M20_UPDATE_DRAFT,
        "m20_result": M20_RESULT,
    }

    try:
        for output in [
            ADOPTION,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M21_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M21",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["operation_mode"]
            == (
                "LOCAL_COMPLIANT_LAYOUT_REVISION_"
                "ADOPTION_RECORDING_ONLY"
            ),
            "POLICY_OPERATION_MODE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_COMPLIANT_LAYOUT_"
                "REVISION_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )
        require(
            approval[
                "rendered_update_payload_generation_approved"
            ] is False,
            "RENDERED_UPDATE_PAYLOAD_GENERATION_APPROVED",
        )
        require(
            approval["wordpress_update_approved"]
            is False,
            "WORDPRESS_UPDATE_APPROVED",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        bindings = approval["source_bindings"]

        for name, path in source_paths.items():
            require(
                bindings[name]["file_sha256"]
                == source_hashes[name],
                f"APPROVAL_SOURCE_SHA_MISMATCH:{name}",
            )
            require(
                bindings[name]["path"]
                == str(path.relative_to(ROOT)),
                f"APPROVAL_SOURCE_PATH_MISMATCH:{name}",
            )

        m19_review = load_json(M19_REVIEW)
        m19_result = load_json(M19_RESULT)
        m20_compliance = load_json(
            M20_COMPLIANCE
        )
        m20_design = load_json(M20_DESIGN)
        m20_update_draft = load_json(
            M20_UPDATE_DRAFT
        )
        m20_result = load_json(M20_RESULT)

        verify_digest(
            m19_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M19_REVIEW_DIGEST,
        )
        verify_digest(
            m19_result,
            "result_digest_sha256",
            EXPECTED_M19_RESULT_DIGEST,
        )
        verify_digest(
            m20_compliance,
            "compliance_assessment_digest_sha256",
            EXPECTED_M20_COMPLIANCE_DIGEST,
        )
        verify_digest(
            m20_design,
            "design_digest_sha256",
            EXPECTED_M20_DESIGN_DIGEST,
        )
        verify_digest(
            m20_update_draft,
            "update_draft_payload_digest_sha256",
            EXPECTED_M20_UPDATE_DRAFT_DIGEST,
        )
        verify_digest(
            m20_result,
            "result_digest_sha256",
            EXPECTED_M20_RESULT_DIGEST,
        )

        require(
            m20_result["status"]
            == (
                "PASS_WORDPRESS_LAYOUT_CORRECTION_"
                "DESIGN_GATE_REQUESTED_PR_POSITION_"
                "BLOCKED_COMPLIANT_ALTERNATIVE_"
                "DRAFTED_LOCAL_ONLY"
            ),
            "M20_STATUS_MISMATCH",
        )
        require(
            m20_result[
                "requested_layout_compliance_verdict"
            ] == "BLOCK_REQUESTED_PR_POSITION",
            "M20_COMPLIANCE_VERDICT_MISMATCH",
        )
        require(
            m20_result[
                "compliant_alternative_drafted"
            ] is True,
            "M20_ALTERNATIVE_NOT_DRAFTED",
        )
        require(
            m20_result[
                "compliant_alternative_execution_allowed"
            ] is False,
            "M20_ALTERNATIVE_EXECUTION_ALLOWED",
        )
        require(
            m20_result[
                "human_reapproval_required"
            ] is True,
            "M20_HUMAN_REAPPROVAL_NOT_REQUIRED",
        )
        require(
            m20_result[
                "ready_for_compliant_layout_revision_approval"
            ] is True,
            "M20_REVISION_APPROVAL_GATE_NOT_READY",
        )
        require(
            m20_result[
                "ready_for_wordpress_update"
            ] is False,
            "M20_WORDPRESS_UPDATE_GATE_OPEN",
        )

        require(
            m20_compliance[
                "requested_layout_verdict"
            ] == "BLOCK_REQUESTED_PR_POSITION",
            "COMPLIANCE_REQUESTED_POSITION_NOT_BLOCKED",
        )
        require(
            m20_compliance[
                "required_alternative_pr_position"
            ] == (
                "IMMEDIATELY_BEFORE_FIRST_"
                "AFFILIATE_BUTTON"
            ),
            "COMPLIANCE_PR_POSITION_MISMATCH",
        )
        require(
            m20_compliance[
                "wordpress_update_allowed"
            ] is False,
            "COMPLIANCE_WORDPRESS_UPDATE_ALLOWED",
        )

        alternative = m20_design[
            "compliant_alternative"
        ]

        require(
            alternative["status"]
            == "DRAFTED_AWAITING_HUMAN_APPROVAL",
            "M20_ALTERNATIVE_STATUS_MISMATCH",
        )
        require(
            alternative["desktop"]["left_column"]
            == ["cover_image"],
            "DESKTOP_LEFT_COLUMN_MISMATCH",
        )
        require(
            alternative["desktop"][
                "right_column_order"
            ] == [
                "pr_disclosure",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
                "responsive_work_details",
            ],
            "DESKTOP_RIGHT_ORDER_MISMATCH",
        )
        require(
            alternative["mobile_order"] == [
                "cover_image",
                "responsive_work_details",
                "pr_disclosure",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
            ],
            "MOBILE_ORDER_MISMATCH",
        )

        comments = m20_design[
            "comment_correction"
        ]

        require(
            comments[
                "post_id_192_comment_status"
            ] == "closed",
            "COMMENT_STATUS_TARGET_MISMATCH",
        )
        require(
            comments["comment_form_visible"]
            is False,
            "COMMENT_FORM_VISIBLE",
        )
        require(
            comments["comment_list_visible"]
            is False,
            "COMMENT_LIST_VISIBLE",
        )
        require(
            comments["comment_heading_visible"]
            is False,
            "COMMENT_HEADING_VISIBLE",
        )

        require(
            m20_update_draft[
                "rendered_content_html"
            ] is None,
            "M20_RENDERED_CONTENT_PRESENT",
        )
        require(
            m20_update_draft[
                "wordpress_request_body"
            ] is None,
            "M20_WORDPRESS_REQUEST_BODY_PRESENT",
        )
        require(
            m20_update_draft[
                "execution_allowed"
            ] is False,
            "M20_UPDATE_DRAFT_EXECUTION_ALLOWED",
        )
        require(
            m20_update_draft[
                "authorization_issued"
            ] is False,
            "M20_AUTHORIZATION_ISSUED",
        )
        require(
            m20_update_draft[
                "authorization_consumed"
            ] is False,
            "M20_AUTHORIZATION_CONSUMED",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        adoption_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M21"
            ),
            "document_role": (
                "WORDPRESS_COMPLIANT_LAYOUT_"
                "REVISION_HUMAN_ADOPTION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "approval_label": (
                "WORDPRESS_COMPLIANT_LAYOUT_"
                "REVISION_APPROVED"
            ),
            "approved_by": "HUMAN_OPERATOR",
            "human_approval_complete": True,
            "adoption_decision": (
                "ADOPT_M20_COMPLIANT_LAYOUT_REVISION"
            ),
            "adopted_desktop_layout": {
                "left_column": [
                    "cover_image"
                ],
                "right_column_order": [
                    "pr_disclosure",
                    "amazon_button",
                    "rakuten_kobo_button",
                    "dmm_button",
                    "responsive_work_details"
                ],
                "store_buttons_vertical": True,
                "work_details_format": (
                    "RESPONSIVE_DESCRIPTION_LIST"
                )
            },
            "adopted_mobile_order": [
                "cover_image",
                "responsive_work_details",
                "pr_disclosure",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button"
            ],
            "adopted_pr_contract": {
                "text": (
                    "PR：このページには"
                    "アフィリエイト広告が含まれます。"
                ),
                "position": (
                    "IMMEDIATELY_BEFORE_FIRST_"
                    "AFFILIATE_BUTTON"
                ),
                "hidden_or_collapsed": False,
                "minimum_font_size_px": 14
            },
            "adopted_comment_contract": {
                "wordpress_post_id": 192,
                "comment_status": "closed",
                "comment_form_visible": False,
                "comment_list_visible": False,
                "comment_heading_visible": False,
                "future_template_scope": (
                    "EBOOK_AFFILIATE_ARTICLES"
                ),
                "future_template_update_requires_separate_approval": True
            },
            "m19_human_review_digest_sha256": (
                EXPECTED_M19_REVIEW_DIGEST
            ),
            "m19_result_digest_sha256": (
                EXPECTED_M19_RESULT_DIGEST
            ),
            "m20_compliance_assessment_digest_sha256": (
                EXPECTED_M20_COMPLIANCE_DIGEST
            ),
            "m20_design_digest_sha256": (
                EXPECTED_M20_DESIGN_DIGEST
            ),
            "m20_update_draft_payload_digest_sha256": (
                EXPECTED_M20_UPDATE_DRAFT_DIGEST
            ),
            "m20_result_digest_sha256": (
                EXPECTED_M20_RESULT_DIGEST
            ),
            "rendered_update_payload_generated": False,
            "wordpress_request_body_generated": False,
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_issued": False,
            "authorization_consumed": False,
            "authorization_reused": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "m17_rerun_performed": False,
            "m18_rerun_performed": False,
            "m19_rerun_performed": False,
            "m20_rerun_performed": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "ready_for_rendered_update_payload_generation_gate": True,
            "ready_for_wordpress_update_authorization_gate": False,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "adopted_at_utc": now()
        }

        adoption = add_digest(
            adoption_without_digest,
            "adoption_evidence_digest_sha256",
        )
        write_json(ADOPTION, adoption)

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M21"
            ),
            "status": (
                "PASS_WORDPRESS_COMPLIANT_LAYOUT_"
                "REVISION_HUMAN_APPROVAL_RECORDED_"
                "LOCAL_ONLY_NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "COMPLIANT_LAYOUT_REVISION_ADOPTED_"
                "READY_FOR_SEPARATE_RENDERED_UPDATE_"
                "PAYLOAD_GENERATION_GATE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "human_approval_complete": True,
            "compliant_layout_revision_adopted": True,
            "adoption_path": str(
                ADOPTION.relative_to(ROOT)
            ),
            "adoption_evidence_digest_sha256": (
                adoption[
                    "adoption_evidence_digest_sha256"
                ]
            ),
            "adopted_desktop_order": [
                "cover_image_left",
                "pr_disclosure_right",
                "amazon_button_right",
                "rakuten_kobo_button_right",
                "dmm_button_right",
                "responsive_work_details_right"
            ],
            "adopted_mobile_order": [
                "cover_image",
                "responsive_work_details",
                "pr_disclosure",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button"
            ],
            "comment_status_target": "closed",
            "m20_result_digest_sha256": (
                EXPECTED_M20_RESULT_DIGEST
            ),
            "m20_design_digest_sha256": (
                EXPECTED_M20_DESIGN_DIGEST
            ),
            "m20_compliance_assessment_digest_sha256": (
                EXPECTED_M20_COMPLIANCE_DIGEST
            ),
            "m20_update_draft_payload_digest_sha256": (
                EXPECTED_M20_UPDATE_DRAFT_DIGEST
            ),
            "source_artifacts_modified": False,
            "rendered_update_payload_generated": False,
            "wordpress_request_body_generated": False,
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_issued": False,
            "authorization_consumed": False,
            "authorization_reused": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "COMPLIANT_LAYOUT_REVISION_ADOPTED_"
                "AWAITING_RENDERED_PAYLOAD_GENERATION_"
                "NO_WORDPRESS_UPDATE"
            ),
            "ready_for_rendered_update_payload_generation_gate": True,
            "ready_for_wordpress_update_authorization_gate": False,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        result = add_digest(
            result_without_digest,
            "result_digest_sha256",
        )
        write_json(RESULT, result)

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M21

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Human approval complete: `true`
- Compliant layout revision adopted: `true`
- Desktop layout: `cover left / PR / Amazon / Rakuten Kobo / DMM / responsive details`
- Mobile layout: `cover / responsive details / PR / Amazon / Rakuten Kobo / DMM`
- Comment status target: `closed`
- Rendered update payload generated: `false`
- WordPress request body generated: `false`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Authorization issued: `false`
- Authorization consumed: `false`
- Production status: `NO_GO`
- Ready for rendered update payload generation gate: `true`
- Ready for WordPress update authorization gate: `false`
- Ready for WordPress update: `false`
""",
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
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M21"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_COMPLIANT_"
                        "LAYOUT_REVISION_HUMAN_APPROVAL_"
                        "NO_WORDPRESS_ACCESS"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_update_performed": False,
                    "rendered_update_payload_generated": False,
                    "authorization_issued": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
