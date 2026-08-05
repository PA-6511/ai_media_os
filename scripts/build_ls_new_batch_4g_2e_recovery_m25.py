#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def block_network(
    *args: Any,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "NETWORK_OPERATION_BLOCKED_BY_M25"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_layout_"
    "human_review_and_backlist_future_requirement_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m25_approval.json"
)

M24_DECISION = ROOT / (
    "exchange/decisions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_revision.json"
)
M24_RENDERED = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.html"
)
M24_CSS = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.css"
)
M24_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_payload_v1.json"
)
M24_DESKTOP = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_desktop_safe_preview.html"
)
M24_MOBILE = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_mobile_safe_preview.html"
)
M24_REVIEW_PACKET = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_human_review_packet.json"
)
M24_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m24_result.json"
)
ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)

HUMAN_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_human_review_approved.json"
)
FUTURE_REQUIREMENT = ROOT / (
    "exchange/requirements/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_backlist_cover_affiliate_carousel_"
    "future_requirement.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m25_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m25_"
    "human_review_and_backlist_future_requirement_report.md"
)

EXPECTED_M24_DECISION_DIGEST = (
    "35e507d421d636afada44c2dcc89dd09"
    "de4ca75baf528ea2233fe701b971b226"
)
EXPECTED_M24_RENDERED_SHA = (
    "dc938ae164c70130a5fb27692d71c97c"
    "c367a8985c44c2c333801b337ee6caf4"
)
EXPECTED_M24_CSS_SHA = (
    "8fb60f5c3554b31de56d5a96ea111271"
    "08a12ef0bcd2f57355d3f90086dfedf0"
)
EXPECTED_M24_PAYLOAD_DIGEST = (
    "52ed18792454e5806b739059911c8117"
    "810cafcadacf35fb77429b608673cd60"
)
EXPECTED_M24_DESKTOP_SHA = (
    "454d688f6e32beb83340c27b65dfead4"
    "21c41ff19aece5910b5aae93ae424469"
)
EXPECTED_M24_MOBILE_SHA = (
    "6e3b3a3c12b171377ab9505386609dca"
    "c4c8292f60aaac9e30e13fa2fca68c0a"
)
EXPECTED_M24_REVIEW_PACKET_DIGEST = (
    "9866fa3be4b25bdfa30033c8f17f57b2"
    "cc5c5b8c0cc1710faaa6530940c61f66"
)
EXPECTED_M24_RESULT_DIGEST = (
    "010d875697f264c731913a96712aea28"
    "8ebfdeabfa7c377453e717dec724cdf0"
)
EXPECTED_ROLLBACK_DIGEST = (
    "60ac4fe5182e412014bcbd291ca52af1"
    "e516e7061722e608b39a34c284dbfcf5"
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


def canonical_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha(
    path: Path,
) -> str:
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
    expected: str,
) -> None:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        canonical_digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )
    require(
        stored == expected,
        f"DIGEST_EXPECTED_MISMATCH:{field}",
    )


def add_digest(
    value: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = canonical_digest(value)
    return result


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )


def main() -> int:
    sources = {
        "m24_decision": M24_DECISION,
        "m24_rendered": M24_RENDERED,
        "m24_css": M24_CSS,
        "m24_payload": M24_PAYLOAD,
        "m24_desktop": M24_DESKTOP,
        "m24_mobile": M24_MOBILE,
        "m24_review_packet": M24_REVIEW_PACKET,
        "m24_result": M24_RESULT,
        "rollback": ROLLBACK,
    }

    try:
        for output in [
            HUMAN_REVIEW,
            FUTURE_REQUIREMENT,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M25_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        approval_copy = copy.deepcopy(approval)
        approval_digest = approval_copy.pop(
            "approval_evidence_digest_sha256",
            None,
        )

        require(
            canonical_digest(approval_copy)
            == approval_digest,
            "APPROVAL_DIGEST_MISMATCH",
        )
        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M25",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_HUMAN_REVIEW_"
                "APPROVED_NO_CHANGE_REQUIRED_WITH_BACKLIST_"
                "CAROUSEL_FUTURE_REQUIREMENT"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_review_verdict"]
            == "APPROVED_NO_CHANGE_REQUIRED",
            "HUMAN_REVIEW_VERDICT_MISMATCH",
        )
        require(
            approval[
                "backlist_carousel_implementation_approved"
            ] is False,
            "BACKLIST_IMPLEMENTATION_APPROVED",
        )
        require(
            approval["wordpress_update_approved"]
            is False,
            "WORDPRESS_UPDATE_APPROVED",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in sources.items()
        }

        for name, path in sources.items():
            binding = approval[
                "source_bindings"
            ][name]

            require(
                binding["path"]
                == str(path.relative_to(ROOT)),
                f"SOURCE_PATH_MISMATCH:{name}",
            )
            require(
                binding["file_sha256"]
                == source_hashes[name],
                f"SOURCE_SHA_MISMATCH:{name}",
            )

        m24_decision = load_json(
            M24_DECISION
        )
        m24_payload = load_json(
            M24_PAYLOAD
        )
        m24_review = load_json(
            M24_REVIEW_PACKET
        )
        m24_result = load_json(
            M24_RESULT
        )
        rollback = load_json(
            ROLLBACK
        )

        verify_digest(
            m24_decision,
            "decision_digest_sha256",
            EXPECTED_M24_DECISION_DIGEST,
        )
        verify_digest(
            m24_payload,
            "update_payload_digest_sha256",
            EXPECTED_M24_PAYLOAD_DIGEST,
        )
        verify_digest(
            m24_review,
            "review_packet_digest_sha256",
            EXPECTED_M24_REVIEW_PACKET_DIGEST,
        )
        verify_digest(
            m24_result,
            "result_digest_sha256",
            EXPECTED_M24_RESULT_DIGEST,
        )
        verify_digest(
            rollback,
            "rollback_evidence_digest_sha256",
            EXPECTED_ROLLBACK_DIGEST,
        )

        require(
            file_sha(M24_RENDERED)
            == EXPECTED_M24_RENDERED_SHA,
            "M24_RENDERED_SHA_MISMATCH",
        )
        require(
            file_sha(M24_CSS)
            == EXPECTED_M24_CSS_SHA,
            "M24_CSS_SHA_MISMATCH",
        )
        require(
            file_sha(M24_DESKTOP)
            == EXPECTED_M24_DESKTOP_SHA,
            "M24_DESKTOP_SHA_MISMATCH",
        )
        require(
            file_sha(M24_MOBILE)
            == EXPECTED_M24_MOBILE_SHA,
            "M24_MOBILE_SHA_MISMATCH",
        )

        require(
            m24_result["status"]
            == (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "REVISION_GENERATED_LOCAL_ONLY_NON_EXECUTABLE_"
                "SAFE_PREVIEWS_READY_NO_WORDPRESS_ACCESS"
            ),
            "M24_STATUS_MISMATCH",
        )
        require(
            m24_review[
                "human_review_completed"
            ] is False,
            "M24_REVIEW_ALREADY_COMPLETED",
        )
        require(
            m24_review[
                "human_review_verdict"
            ] == "NOT_RECORDED",
            "M24_REVIEW_VERDICT_ALREADY_RECORDED",
        )

        request_body = m24_payload[
            "wordpress_request_body"
        ]

        require(
            set(request_body.keys())
            == {
                "content",
                "comment_status",
            },
            "CURRENT_UPDATE_FIELD_SET_MISMATCH",
        )
        require(
            request_body["comment_status"]
            == "closed",
            "COMMENT_STATUS_NOT_CLOSED",
        )
        require(
            m24_payload[
                "execution_allowed"
            ] is False,
            "M24_PAYLOAD_EXECUTION_ALLOWED",
        )

        human_review_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M25"
            ),
            "document_role": (
                "TAWAWA_REFERENCE_LAYOUT_HUMAN_REVIEW_RESULT"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "human_review_completed": True,
            "human_review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "desktop_review": {
                "completed": True,
                "verdict": (
                    "APPROVED_NO_CHANGE_REQUIRED"
                ),
                "cover_left_buttons_right": True,
                "pr_before_buttons": True,
                "store_order_approved": True,
                "button_width_and_spacing_approved": True,
                "lower_sections_separated": True,
                "text_wrapping_approved": True,
                "overall_balance_approved": True
            },
            "mobile_review": {
                "completed": True,
                "verdict": (
                    "APPROVED_NO_CHANGE_REQUIRED"
                ),
                "single_column_order_approved": True,
                "pr_before_buttons": True,
                "store_order_approved": True,
                "button_width_and_spacing_approved": True,
                "horizontal_scroll_detected": False,
                "text_wrapping_approved": True,
                "overall_balance_approved": True
            },
            "review_source": (
                "HUMAN_OPERATOR_VISUAL_REVIEW_OF_"
                "DESKTOP_AND_MOBILE_SAFE_PREVIEWS"
            ),
            "m24_result_digest_sha256": (
                EXPECTED_M24_RESULT_DIGEST
            ),
            "m24_decision_digest_sha256": (
                EXPECTED_M24_DECISION_DIGEST
            ),
            "m24_rendered_content_sha256": (
                EXPECTED_M24_RENDERED_SHA
            ),
            "m24_scoped_css_sha256": (
                EXPECTED_M24_CSS_SHA
            ),
            "m24_update_payload_digest_sha256": (
                EXPECTED_M24_PAYLOAD_DIGEST
            ),
            "desktop_preview_sha256": (
                EXPECTED_M24_DESKTOP_SHA
            ),
            "mobile_preview_sha256": (
                EXPECTED_M24_MOBILE_SHA
            ),
            "comment_status_target": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status"
            ],
            "layout_change_required": False,
            "m24_artifacts_modified": False,
            "wordpress_access_performed": False,
            "wordpress_update_performed": False,
            "authorization_issued": False,
            "production_status": "NO_GO",
            "recorded_at_utc": now()
        }

        human_review = add_digest(
            human_review_without_digest,
            "human_review_evidence_digest_sha256",
        )
        write_json(
            HUMAN_REVIEW,
            human_review,
        )

        future_requirement_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M25"
            ),
            "document_role": (
                "SERIES_BACKLIST_COVER_AFFILIATE_"
                "CAROUSEL_FUTURE_REQUIREMENT"
            ),
            "requirement_id": (
                "SERIES_BACKLIST_COVER_AFFILIATE_"
                "CAROUSEL_V1"
            ),
            "recommended_implementation_phase_id": (
                "LS-NEW-SERIES-BACKLIST-1"
            ),
            "status": (
                "FUTURE_REQUIREMENT_RECORDED_NOT_IMPLEMENTED"
            ),
            "scope": {
                "series_backlist_volume_display": True,
                "cover_image_per_volume": True,
                "affiliate_route_per_volume": True,
                "desktop_display": (
                    "HORIZONTAL_MULTI_VOLUME_CAROUSEL_OR_LIST"
                ),
                "mobile_display": (
                    "HORIZONTAL_SWIPE_OR_LIMITED_VISIBLE_CARDS"
                )
            },
            "required_volume_fields": [
                "volume_number",
                "cover_image",
                "product_title",
                "release_date",
                "amazon_affiliate_route",
                "rakuten_kobo_affiliate_route",
                "dmm_affiliate_route",
                "link_state",
                "cover_source"
            ],
            "required_rendering_controls": {
                "image_lazy_loading": True,
                "descriptive_alt_text": True,
                "volume_number_visible": True,
                "duplicate_volume_prevention": True,
                "broken_link_click_prevention": True,
                "responsive_card_sizing": True,
                "horizontal_overflow_control": True
            },
            "required_governance_controls": {
                "pr_before_first_affiliate_interaction": True,
                "cover_and_destination_product_match_validation": True,
                "volume_and_destination_product_match_validation": True,
                "full_affiliate_url_normal_output_allowed": False,
                "affiliate_identifier_normal_output_allowed": False,
                "credential_output_allowed": False,
                "automatic_permanent_rule_from_single_edit_allowed": False
            },
            "store_interaction_policy": {
                "preferred_default": (
                    "SELECT_VOLUME_THEN_SELECT_AVAILABLE_STORE"
                ),
                "single_verified_store_direct_link_allowed": True,
                "unverified_or_broken_route_clickable": False
            },
            "current_m24_rendered_html_modified": False,
            "current_m24_css_modified": False,
            "current_m24_update_payload_modified": False,
            "included_in_current_wordpress_update": False,
            "implementation_authorized": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "authorization_issued": False,
            "production_status": "NO_GO",
            "recorded_at_utc": now()
        }

        future_requirement = add_digest(
            future_requirement_without_digest,
            "future_requirement_digest_sha256",
        )
        write_json(
            FUTURE_REQUIREMENT,
            future_requirement,
        )

        for name, path in sources.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M25"
            ),
            "status": (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "HUMAN_REVIEW_APPROVED_NO_CHANGE_REQUIRED_"
                "BACKLIST_FUTURE_REQUIREMENT_RECORDED_"
                "LOCAL_ONLY_NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "HUMAN_REVIEW_APPROVED_READY_FOR_SEPARATE_"
                "WORDPRESS_UPDATE_AUTHORIZATION_GATE_"
                "BACKLIST_REQUIREMENT_DEFERRED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "human_review_path": str(
                HUMAN_REVIEW.relative_to(ROOT)
            ),
            "human_review_evidence_digest_sha256": (
                human_review[
                    "human_review_evidence_digest_sha256"
                ]
            ),
            "human_review_completed": True,
            "human_review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "desktop_review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "mobile_review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "layout_change_required": False,
            "future_requirement_path": str(
                FUTURE_REQUIREMENT.relative_to(ROOT)
            ),
            "future_requirement_digest_sha256": (
                future_requirement[
                    "future_requirement_digest_sha256"
                ]
            ),
            "backlist_carousel_future_requirement_recorded": True,
            "backlist_carousel_implemented": False,
            "backlist_carousel_included_in_current_payload": False,
            "recommended_backlist_phase_id": (
                "LS-NEW-SERIES-BACKLIST-1"
            ),
            "m24_rendered_html_modified": False,
            "m24_css_modified": False,
            "m24_update_payload_modified": False,
            "comment_status_target": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status"
            ],
            "rollback_evidence_digest_sha256": (
                EXPECTED_ROLLBACK_DIGEST
            ),
            "source_artifacts_modified": False,
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
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "HUMAN_REVIEW_APPROVED_BACKLIST_REQUIREMENT_"
                "DEFERRED_AWAITING_SEPARATE_UPDATE_AUTHORIZATION"
            ),
            "ready_for_wordpress_update_authorization_gate": True,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "ready_for_backlist_carousel_implementation": False,
            "completed_at_utc": now()
        }

        result = add_digest(
            result_without_digest,
            "result_digest_sha256",
        )
        write_json(
            RESULT,
            result,
        )

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M25

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Human review completed: `true`
- Human review verdict: `APPROVED_NO_CHANGE_REQUIRED`
- Desktop verdict: `APPROVED_NO_CHANGE_REQUIRED`
- Mobile verdict: `APPROVED_NO_CHANGE_REQUIRED`
- M24 layout change required: `false`
- Backlist carousel future requirement recorded: `true`
- Backlist carousel implemented: `false`
- Included in current update payload: `false`
- Recommended future phase: `LS-NEW-SERIES-BACKLIST-1`
- Comment status target: `closed`
- Allowed update fields: `content, comment_status`
- M24 rendered HTML modified: `false`
- M24 CSS modified: `false`
- M24 update payload modified: `false`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Authorization issued: `false`
- Production status: `NO_GO`
- Ready for WordPress update authorization gate: `true`
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M25"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                        "HUMAN_REVIEW_AND_BACKLIST_REQUIREMENT_"
                        "NO_WORDPRESS_ACCESS"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_issued": False,
                    "execution_allowed": False,
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
