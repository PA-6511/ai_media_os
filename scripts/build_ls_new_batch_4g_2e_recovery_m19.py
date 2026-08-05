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
        "NETWORK_OPERATION_BLOCKED_BY_M19"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_published_post_human_review_"
    "changes_required_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m19_approval.json"
)

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)
M15_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_post_execution_human_review.json"
)
M15_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m15_result.json"
)
M16_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_authorization.json"
)
M16_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m16_result.json"
)
M17_PRE_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m17_pre_network_result.json"
)
M17_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_consumption.json"
)
M17_SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_response.json"
)
M17_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m17_result.json"
)
M18_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m18_result.json"
)

REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_published_post_human_review_changes_required.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m19_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m19_"
    "wordpress_published_post_human_review_"
    "changes_required_report.md"
)

EXPECTED_POST_ID = 192

EXPECTED_ARTICLE_SHA = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
EXPECTED_PAYLOAD_SHA = (
    "30a70be4110e863a85e2896f69f5b3e5"
    "1d814a6fd82d5489f899d8a244166d8f"
)
EXPECTED_PAYLOAD_DIGEST = (
    "2ab27b59305dbae98f997ca3a4604002"
    "98152f173ef605b534df922c187411c6"
)
EXPECTED_M15_REVIEW_DIGEST = (
    "be8aafa191df793ecbe2695b662378fe"
    "f078ce42ae4169a93651a9d2b6141d4c"
)
EXPECTED_M15_RESULT_DIGEST = (
    "03d777e3e34c4d68c4b55027db87f7b"
    "20cee59f947640f3d68b125d6c79f5b06"
)
EXPECTED_M16_AUTH_FILE_SHA = (
    "0b8eb340f4551497e99d91dc64ab5d47"
    "c149efb098d50ebf6cf981d416624e58"
)
EXPECTED_M16_AUTH_DIGEST = (
    "3af20632d3fabe77f04e795318406ecd"
    "0ad9bd7b6d2eb60646e82f108556cc9e"
)
EXPECTED_M16_RESULT_DIGEST = (
    "9eda577486ceaf77be2baf0346cf7152"
    "ff3e5113bd091625715e487224c3150a"
)
EXPECTED_M17_PRE_RESULT_DIGEST = (
    "f2650043127b69ef5d6cc1b539a7f2fe"
    "523f2d53d53ea0cfdd37b0b81a6b8944"
)
EXPECTED_M17_CONSUMPTION_DIGEST = (
    "9fa836ec2fe8c49b160101351e5a913b"
    "0c606af857131b5a0550b81fb04f443e"
)
EXPECTED_M17_SECRET_DIGEST = (
    "edc92fb39dafda7948d6d7e539181473"
    "43507b50239d0ae2608311ed306de741"
)
EXPECTED_M17_SECRET_FILE_SHA = (
    "cab1e674bbac70daae4cbc017f8e01c6"
    "dea7fcd79353c887581fbbf1239d2660"
)
EXPECTED_M17_RESULT_DIGEST = (
    "e405bd6b44b45c8246388b0ea2fa55ac"
    "501e728563cf97d9b82be6c5dad2e93e"
)
EXPECTED_M18_RESULT_DIGEST = (
    "a278655efbd252455d95b063cf2cc8ed"
    "4ec4de78f009d9991156cb1a10b02c95"
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
        "article": ARTICLE,
        "payload": PAYLOAD,
        "m15_review": M15_REVIEW,
        "m15_result": M15_RESULT,
        "m16_authorization": M16_AUTH,
        "m16_result": M16_RESULT,
        "m17_pre_network_result": M17_PRE_RESULT,
        "m17_consumption": M17_CONSUMPTION,
        "m17_secret_response": M17_SECRET_RESPONSE,
        "m17_result": M17_RESULT,
        "m18_result": M18_RESULT,
    }

    try:
        for output in [
            REVIEW,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M19_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M19",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["operation_mode"]
            == (
                "LOCAL_HUMAN_REVIEW_"
                "CHANGE_REQUIREMENTS_RECORDING_ONLY"
            ),
            "POLICY_OPERATION_MODE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_PUBLISHED_POST_HUMAN_"
                "REVIEW_CHANGES_REQUIRED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )
        require(
            approval["review_verdict"]
            == "CHANGES_REQUIRED",
            "REVIEW_VERDICT_MISMATCH",
        )
        require(
            approval["wordpress_access_approved"]
            is False,
            "WORDPRESS_ACCESS_APPROVED",
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

        require(
            source_hashes["article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["payload"]
            == EXPECTED_PAYLOAD_SHA,
            "PAYLOAD_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["m16_authorization"]
            == EXPECTED_M16_AUTH_FILE_SHA,
            "M16_AUTHORIZATION_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["m17_secret_response"]
            == EXPECTED_M17_SECRET_FILE_SHA,
            "M17_SECRET_RESPONSE_FILE_SHA_MISMATCH",
        )

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        m15_review = load_json(M15_REVIEW)
        m15_result = load_json(M15_RESULT)
        m16_auth = load_json(M16_AUTH)
        m16_result = load_json(M16_RESULT)
        m17_pre_result = load_json(
            M17_PRE_RESULT
        )
        m17_consumption = load_json(
            M17_CONSUMPTION
        )
        m17_secret = load_json(
            M17_SECRET_RESPONSE
        )
        m17_result = load_json(M17_RESULT)
        m18_result = load_json(M18_RESULT)

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            m15_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M15_REVIEW_DIGEST,
        )
        verify_digest(
            m15_result,
            "result_digest_sha256",
            EXPECTED_M15_RESULT_DIGEST,
        )
        verify_digest(
            m16_auth,
            "authorization_digest_sha256",
            EXPECTED_M16_AUTH_DIGEST,
        )
        verify_digest(
            m16_result,
            "result_digest_sha256",
            EXPECTED_M16_RESULT_DIGEST,
        )
        verify_digest(
            m17_pre_result,
            "result_digest_sha256",
            EXPECTED_M17_PRE_RESULT_DIGEST,
        )
        verify_digest(
            m17_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M17_CONSUMPTION_DIGEST,
        )
        verify_digest(
            m17_secret,
            "secret_response_digest_sha256",
            EXPECTED_M17_SECRET_DIGEST,
        )
        verify_digest(
            m17_result,
            "result_digest_sha256",
            EXPECTED_M17_RESULT_DIGEST,
        )
        verify_digest(
            m18_result,
            "result_digest_sha256",
            EXPECTED_M18_RESULT_DIGEST,
        )

        require(
            m18_result["status"]
            == (
                "PASS_WORDPRESS_PUBLISHED_POST_"
                "EXECUTION_EVIDENCE_VERIFIED_"
                "GET_ONLY_NO_WRITE"
            ),
            "M18_STATUS_MISMATCH",
        )
        require(
            m18_result["wordpress_post_id"]
            == EXPECTED_POST_ID,
            "M18_POST_ID_MISMATCH",
        )
        require(
            m18_result["wordpress_post_status"]
            == "publish",
            "M18_STATUS_NOT_PUBLISH",
        )
        require(
            m18_result["published_status_verified"]
            is True,
            "M18_PUBLISHED_NOT_VERIFIED",
        )
        require(
            m18_result["title_exact_match"]
            is True,
            "M18_TITLE_MISMATCH",
        )
        require(
            m18_result["content_exact_match"]
            is True,
            "M18_CONTENT_MISMATCH",
        )
        require(
            m18_result["category_id_10_verified"]
            is True,
            "M18_CATEGORY_MISMATCH",
        )
        require(
            m18_result[
                "ready_for_post_publication_human_review"
            ] is True,
            "M18_HUMAN_REVIEW_NOT_READY",
        )

        require(
            m17_result["authorization_consumed"]
            is True,
            "M17_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            m17_result["authorization_reuse_allowed"]
            is False,
            "M17_REUSE_ALLOWED",
        )
        require(
            m17_result["automatic_retry_allowed"]
            is False,
            "M17_RETRY_ALLOWED",
        )
        require(
            m17_result["automatic_reissue_allowed"]
            is False,
            "M17_REISSUE_ALLOWED",
        )
        require(
            m17_result["wordpress_published"]
            is True,
            "M17_NOT_PUBLISHED",
        )

        require(
            payload["title"]
            == article["article_title"],
            "ARTICLE_TITLE_MISMATCH",
        )
        require(
            payload["content_html"]
            == article["content_html"],
            "ARTICLE_CONTENT_MISMATCH",
        )
        require(
            payload["categories"] == [10],
            "PAYLOAD_CATEGORY_MISMATCH",
        )

        requested = approval[
            "approved_change_requirements"
        ]

        require(
            requested["desktop_cover_left"]
            is True,
            "DESKTOP_COVER_LEFT_NOT_APPROVED",
        )
        require(
            requested[
                "desktop_store_button_order"
            ] == [
                "amazon",
                "rakuten_kobo",
                "dmm",
            ],
            "DESKTOP_BUTTON_ORDER_MISMATCH",
        )
        require(
            requested[
                "desktop_details_right_below_buttons"
            ] is True,
            "DESKTOP_DETAILS_POSITION_MISMATCH",
        )
        require(
            requested[
                "desktop_pr_below_details"
            ] is True,
            "DESKTOP_PR_POSITION_MISMATCH",
        )
        require(
            requested["mobile_order"]
            == [
                "cover_image",
                "work_details",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
                "pr_disclosure",
            ],
            "MOBILE_ORDER_MISMATCH",
        )
        require(
            requested[
                "ebook_affiliate_comments_disabled"
            ] is True,
            "COMMENTS_DISABLE_NOT_APPROVED",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        review_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M19"
            ),
            "document_role": (
                "WORDPRESS_PUBLISHED_POST_"
                "HUMAN_REVIEW_CHANGE_REQUIREMENTS"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "reviewed_by": "HUMAN_OPERATOR",
            "review_method": (
                "PUBLIC_PAGE_VISUAL_REVIEW"
            ),
            "review_verdict": (
                "CHANGES_REQUIRED"
            ),
            "human_review_complete": True,
            "published_page_display_confirmed": True,
            "change_required": True,
            "approved_no_change_required": False,
            "issues": [
                {
                    "issue_id": (
                        "DETAIL_CARD_LAYOUT_BALANCE"
                    ),
                    "severity": "REQUIRES_CORRECTION",
                    "finding": (
                        "Work detail card width, wrapping, "
                        "and whitespace balance are unsuitable."
                    )
                },
                {
                    "issue_id": (
                        "DESKTOP_STORE_BUTTON_POSITION"
                    ),
                    "severity": "REQUIRES_CORRECTION",
                    "finding": (
                        "Desktop store buttons must be "
                        "positioned beside the cover image."
                    )
                },
                {
                    "issue_id": (
                        "PR_DISCLOSURE_POSITION"
                    ),
                    "severity": "REQUIRES_CORRECTION",
                    "finding": (
                        "PR disclosure position must follow "
                        "the approved responsive layout."
                    )
                },
                {
                    "issue_id": (
                        "COMMENTS_NOT_REQUIRED"
                    ),
                    "severity": "REQUIRES_CORRECTION",
                    "finding": (
                        "Comment form and comment display "
                        "are unnecessary for ebook affiliate articles."
                    )
                }
            ],
            "approved_desktop_layout": {
                "left_column": [
                    "cover_image"
                ],
                "right_column_order": [
                    "amazon_button",
                    "rakuten_kobo_button",
                    "dmm_button",
                    "responsive_work_details",
                    "pr_disclosure"
                ],
                "store_buttons_vertical": True,
                "work_details_format": (
                    "LABEL_VALUE_RESPONSIVE"
                ),
                "remove_excess_whitespace": True,
                "prevent_fragmented_wrapping": True
            },
            "approved_mobile_layout": {
                "content_order": [
                    "cover_image",
                    "responsive_work_details",
                    "amazon_button",
                    "rakuten_kobo_button",
                    "dmm_button",
                    "pr_disclosure"
                ]
            },
            "approved_comment_policy": {
                "scope": (
                    "EBOOK_AFFILIATE_ARTICLES"
                ),
                "comment_status": "closed",
                "comment_form_visible": False,
                "comment_list_visible": False,
                "comment_heading_visible": False
            },
            "pr_position_pre_implementation_compliance_check_required": True,
            "m18_result_digest_sha256": (
                EXPECTED_M18_RESULT_DIGEST
            ),
            "m17_result_digest_sha256": (
                EXPECTED_M17_RESULT_DIGEST
            ),
            "m17_consumption_digest_sha256": (
                EXPECTED_M17_CONSUMPTION_DIGEST
            ),
            "m17_secret_response_digest_sha256": (
                EXPECTED_M17_SECRET_DIGEST
            ),
            "payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "article_file_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_reused": False,
            "authorization_reissued": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "m17_rerun_performed": False,
            "m18_rerun_performed": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "ready_for_layout_correction_design_gate": True,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "reviewed_at_utc": now()
        }

        review = copy.deepcopy(
            review_without_digest
        )
        review[
            "human_review_evidence_digest_sha256"
        ] = digest(review_without_digest)

        write_json(REVIEW, review)

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M19"
            ),
            "status": (
                "PASS_WORDPRESS_PUBLISHED_POST_"
                "HUMAN_REVIEW_CHANGES_REQUIRED_"
                "RECORDED_LOCAL_ONLY_NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "CORRECTIONS_REQUIRED_READY_FOR_"
                "SEPARATE_LAYOUT_CORRECTION_DESIGN_GATE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "last_verified_wordpress_status": (
                "publish"
            ),
            "review_verdict": (
                "CHANGES_REQUIRED"
            ),
            "human_review_complete": True,
            "change_required": True,
            "human_review_path": str(
                REVIEW.relative_to(ROOT)
            ),
            "human_review_evidence_digest_sha256": (
                review[
                    "human_review_evidence_digest_sha256"
                ]
            ),
            "approved_desktop_order": [
                "cover_image_left",
                "amazon_button_right",
                "rakuten_kobo_button_right",
                "dmm_button_right",
                "responsive_work_details_right",
                "pr_disclosure_right"
            ],
            "approved_mobile_order": [
                "cover_image",
                "responsive_work_details",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
                "pr_disclosure"
            ],
            "ebook_affiliate_comments_disabled_required": True,
            "pr_position_pre_implementation_compliance_check_required": True,
            "m18_result_digest_sha256": (
                EXPECTED_M18_RESULT_DIGEST
            ),
            "m17_result_digest_sha256": (
                EXPECTED_M17_RESULT_DIGEST
            ),
            "m17_consumption_digest_sha256": (
                EXPECTED_M17_CONSUMPTION_DIGEST
            ),
            "payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
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
            "authorization_reused": False,
            "authorization_reissued": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "m17_rerun_performed": False,
            "m18_rerun_performed": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "PUBLISHED_POST_REVIEW_CHANGES_REQUIRED_"
                "AWAITING_CORRECTION_DESIGN_NO_WRITE"
            ),
            "ready_for_layout_correction_design_gate": True,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        result = copy.deepcopy(
            result_without_digest
        )
        result[
            "result_digest_sha256"
        ] = digest(result_without_digest)

        write_json(RESULT, result)

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M19

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Last verified WordPress status: `publish`
- Review verdict: `CHANGES_REQUIRED`
- Human review complete: `true`
- Change required: `true`
- Desktop cover position: `left`
- Desktop right upper order: `Amazon / Rakuten Kobo / DMM`
- Desktop right lower section: `responsive label-value work details`
- Desktop PR position: `below work details`
- Mobile order: `cover / details / Amazon / Rakuten Kobo / DMM / PR`
- Ebook affiliate comments disabled required: `true`
- PR-position compliance check before implementation: `true`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress write performed: `false`
- WordPress update performed: `false`
- WordPress republish performed: `false`
- Production status: `NO_GO`
- Ready for layout correction design gate: `true`
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
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M19"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_PUBLISHED_POST_"
                        "HUMAN_REVIEW_CHANGES_REQUIRED_"
                        "RECORDING_NO_WORDPRESS_ACCESS"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_write_performed": False,
                    "wordpress_update_performed": False,
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
