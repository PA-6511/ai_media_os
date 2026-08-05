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
        "NETWORK_OPERATION_BLOCKED_BY_M20"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_layout_correction_"
    "design_gate_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m20_approval.json"
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
M16_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_authorization.json"
)
M17_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_consumption.json"
)
M17_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m17_result.json"
)
M18_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m18_result.json"
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

COMPLIANCE = ROOT / (
    "exchange/compliance/new_release/fresh/"
    "new-release-comic-20260703-001."
    "pr_disclosure_position_compliance_assessment.json"
)
DESIGN = ROOT / (
    "exchange/designs/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_design.json"
)
UPDATE_DRAFT = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_update_draft_payload.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m20_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m20_"
    "wordpress_layout_correction_design_gate_report.md"
)

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
EXPECTED_M16_AUTH_FILE_SHA = (
    "0b8eb340f4551497e99d91dc64ab5d47"
    "c149efb098d50ebf6cf981d416624e58"
)
EXPECTED_M16_AUTH_DIGEST = (
    "3af20632d3fabe77f04e795318406ecd"
    "0ad9bd7b6d2eb60646e82f108556cc9e"
)
EXPECTED_M17_CONSUMPTION_DIGEST = (
    "9fa836ec2fe8c49b160101351e5a913b"
    "0c606af857131b5a0550b81fb04f443e"
)
EXPECTED_M17_RESULT_DIGEST = (
    "e405bd6b44b45c8246388b0ea2fa55ac"
    "501e728563cf97d9b82be6c5dad2e93e"
)
EXPECTED_M18_RESULT_DIGEST = (
    "a278655efbd252455d95b063cf2cc8ed"
    "4ec4de78f009d9991156cb1a10b02c95"
)
EXPECTED_M19_REVIEW_DIGEST = (
    "ee9cc3be321c2c592afc0c784c002d95"
    "06a598cf9a2072e3c1e205d662417db1"
)
EXPECTED_M19_RESULT_DIGEST = (
    "e02748eead2f2d578fbb86c5e53140f5"
    "26d0d8ac6fa4ec95774c266ffeaa9aaa"
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


def canonical_digest(value: Any) -> str:
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
        canonical_digest(comparable) == stored,
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


def add_digest(
    value: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = canonical_digest(value)
    return result


def main() -> int:
    source_paths = {
        "article": ARTICLE,
        "payload": PAYLOAD,
        "m16_authorization": M16_AUTH,
        "m17_consumption": M17_CONSUMPTION,
        "m17_result": M17_RESULT,
        "m18_result": M18_RESULT,
        "m19_review": M19_REVIEW,
        "m19_result": M19_RESULT,
    }

    try:
        for output in [
            COMPLIANCE,
            DESIGN,
            UPDATE_DRAFT,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M20_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M20",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["operation_mode"]
            == (
                "LOCAL_LAYOUT_CORRECTION_DESIGN_"
                "AND_NON_EXECUTABLE_DRAFT_ONLY"
            ),
            "POLICY_OPERATION_MODE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_LAYOUT_CORRECTION_"
                "DESIGN_GATE_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )
        require(
            approval["compliance_block_approved"]
            is True,
            "COMPLIANCE_BLOCK_NOT_APPROVED",
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

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        m16_auth = load_json(M16_AUTH)
        m17_consumption = load_json(
            M17_CONSUMPTION
        )
        m17_result = load_json(M17_RESULT)
        m18_result = load_json(M18_RESULT)
        m19_review = load_json(M19_REVIEW)
        m19_result = load_json(M19_RESULT)

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            m16_auth,
            "authorization_digest_sha256",
            EXPECTED_M16_AUTH_DIGEST,
        )
        verify_digest(
            m17_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M17_CONSUMPTION_DIGEST,
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

        require(
            m19_result["status"]
            == (
                "PASS_WORDPRESS_PUBLISHED_POST_"
                "HUMAN_REVIEW_CHANGES_REQUIRED_"
                "RECORDED_LOCAL_ONLY_NO_WORDPRESS_ACCESS"
            ),
            "M19_STATUS_MISMATCH",
        )
        require(
            m19_result["review_verdict"]
            == "CHANGES_REQUIRED",
            "M19_REVIEW_VERDICT_MISMATCH",
        )
        require(
            m19_result["change_required"]
            is True,
            "M19_CHANGE_REQUIRED_FALSE",
        )
        require(
            m19_result[
                "ready_for_layout_correction_design_gate"
            ] is True,
            "M19_DESIGN_GATE_NOT_READY",
        )
        require(
            m19_result["ready_for_wordpress_update"]
            is False,
            "M19_UPDATE_GATE_ALREADY_OPEN",
        )

        requested_desktop = (
            m19_review[
                "approved_desktop_layout"
            ]["right_column_order"]
        )
        requested_mobile = (
            m19_review[
                "approved_mobile_layout"
            ]["content_order"]
        )

        require(
            requested_desktop == [
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
                "responsive_work_details",
                "pr_disclosure",
            ],
            "M19_DESKTOP_ORDER_MISMATCH",
        )
        require(
            requested_mobile == [
                "cover_image",
                "responsive_work_details",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
                "pr_disclosure",
            ],
            "M19_MOBILE_ORDER_MISMATCH",
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

        compliance_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M20"
            ),
            "document_role": (
                "PR_DISCLOSURE_POSITION_"
                "COMPLIANCE_ASSESSMENT"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "assessment_scope": (
                "AFFILIATE_DISCLOSURE_VISIBILITY_"
                "BEFORE_LINK_INTERACTION"
            ),
            "source_basis": [
                {
                    "authority": (
                        "Consumer Affairs Agency"
                    ),
                    "document": (
                        "Stealth Marketing Q&A"
                    ),
                    "question": "Q13",
                    "principle": (
                        "Affiliate advertising disclosure "
                        "must be clear from the overall display, "
                        "including visibility such as size and color."
                    )
                },
                {
                    "authority": (
                        "Consumer Affairs Agency"
                    ),
                    "document": (
                        "Stealth Marketing Q&A"
                    ),
                    "question": "Q11",
                    "principle": (
                        "Terms such as advertising, promotion, "
                        "and PR may be used when the commercial "
                        "nature is clear to consumers."
                    )
                }
            ],
            "requested_desktop_pr_position": (
                "AFTER_ALL_AFFILIATE_BUTTONS_AND_DETAILS"
            ),
            "requested_mobile_pr_position": (
                "AFTER_ALL_AFFILIATE_BUTTONS"
            ),
            "risk_findings": {
                "affiliate_buttons_reachable_before_disclosure": True,
                "consumer_may_interact_before_disclosure": True,
                "clear_pre_interaction_disclosure_not_guaranteed": True
            },
            "assessment_type": (
                "CONSERVATIVE_OPERATIONAL_COMPLIANCE_GATE"
            ),
            "formal_legal_opinion": False,
            "requested_layout_verdict": (
                "BLOCK_REQUESTED_PR_POSITION"
            ),
            "compliant_alternative_required": True,
            "required_alternative_pr_position": (
                "IMMEDIATELY_BEFORE_FIRST_AFFILIATE_BUTTON"
            ),
            "human_reapproval_required": True,
            "wordpress_update_allowed": False,
            "assessed_at_utc": now()
        }

        compliance = add_digest(
            compliance_without_digest,
            "compliance_assessment_digest_sha256",
        )
        write_json(COMPLIANCE, compliance)

        template_html = """<section class="ebook-product-card" data-layout-version="M20-COMPLIANT-DRAFT">
  <div class="ebook-product-card__cover">
    {{COVER_HTML}}
  </div>
  <div class="ebook-product-card__content">
    <p class="ebook-product-card__pr" role="note">
      PR：このページにはアフィリエイト広告が含まれます。
    </p>
    <div class="ebook-product-card__stores">
      {{AMAZON_BUTTON_HTML}}
      {{RAKUTEN_KOBO_BUTTON_HTML}}
      {{DMM_BUTTON_HTML}}
    </div>
    <dl class="ebook-product-card__details">
      <div class="ebook-product-card__detail-row">
        <dt>作品名</dt>
        <dd>{{WORK_TITLE_TEXT}}</dd>
      </div>
      <div class="ebook-product-card__detail-row">
        <dt>価格</dt>
        <dd>{{PRICE_TEXT}}</dd>
      </div>
      <div class="ebook-product-card__detail-row">
        <dt>作者</dt>
        <dd>{{AUTHOR_TEXT}}</dd>
      </div>
      <div class="ebook-product-card__detail-row">
        <dt>出版社</dt>
        <dd>{{PUBLISHER_TEXT}}</dd>
      </div>
      <div class="ebook-product-card__detail-row">
        <dt>発売日</dt>
        <dd>{{RELEASE_DATE_TEXT}}</dd>
      </div>
    </dl>
  </div>
</section>"""

        template_css = """.ebook-product-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}

.ebook-product-card__cover {
  min-width: 0;
}

.ebook-product-card__cover img {
  display: block;
  width: min(100%, 360px);
  height: auto;
  margin-inline: auto;
}

.ebook-product-card__content {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1rem;
}

.ebook-product-card__details {
  order: 1;
  display: grid;
  gap: 0;
  width: 100%;
  margin: 0;
  overflow: hidden;
  border: 1px solid currentColor;
  border-radius: 0.5rem;
}

.ebook-product-card__pr {
  order: 2;
  margin: 0;
  padding: 0.65rem 0.8rem;
  border: 1px solid currentColor;
  border-radius: 0.4rem;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.5;
}

.ebook-product-card__stores {
  order: 3;
  display: grid;
  gap: 0.75rem;
}

.ebook-product-card__detail-row {
  display: grid;
  grid-template-columns: minmax(5.5rem, 32%) minmax(0, 1fr);
  margin: 0;
  border-bottom: 1px solid currentColor;
}

.ebook-product-card__detail-row:last-child {
  border-bottom: 0;
}

.ebook-product-card__detail-row dt,
.ebook-product-card__detail-row dd {
  min-width: 0;
  margin: 0;
  padding: 0.7rem 0.8rem;
  overflow-wrap: anywhere;
}

.ebook-product-card__detail-row dt {
  font-weight: 700;
}

@media (min-width: 768px) {
  .ebook-product-card {
    grid-template-columns: minmax(260px, 38%) minmax(0, 1fr);
    gap: 2rem;
  }

  .ebook-product-card__cover img {
    width: 100%;
    max-width: 360px;
  }

  .ebook-product-card__pr {
    order: 1;
  }

  .ebook-product-card__stores {
    order: 2;
  }

  .ebook-product-card__details {
    order: 3;
  }

  .ebook-product-card__detail-row {
    grid-template-columns: minmax(7rem, 28%) minmax(0, 1fr);
  }
}"""

        design_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M20"
            ),
            "document_role": (
                "WORDPRESS_LAYOUT_CORRECTION_DESIGN"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "requested_layout": {
                "status": (
                    "BLOCKED_BY_PR_DISCLOSURE_"
                    "POSITION_COMPLIANCE_GATE"
                ),
                "desktop_right_column_order": (
                    requested_desktop
                ),
                "mobile_order": requested_mobile
            },
            "compliant_alternative": {
                "status": (
                    "DRAFTED_AWAITING_HUMAN_APPROVAL"
                ),
                "desktop": {
                    "left_column": [
                        "cover_image"
                    ],
                    "right_column_order": [
                        "pr_disclosure",
                        "amazon_button",
                        "rakuten_kobo_button",
                        "dmm_button",
                        "responsive_work_details"
                    ]
                },
                "mobile_order": [
                    "cover_image",
                    "responsive_work_details",
                    "pr_disclosure",
                    "amazon_button",
                    "rakuten_kobo_button",
                    "dmm_button"
                ],
                "template_html": template_html,
                "template_css": template_css
            },
            "comment_correction": {
                "post_id_192_comment_status": "closed",
                "comment_form_visible": False,
                "comment_list_visible": False,
                "comment_heading_visible": False,
                "future_template_scope": (
                    "EBOOK_AFFILIATE_ARTICLES"
                ),
                "future_template_update_executable": False
            },
            "source_content_file_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "source_payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "source_payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "compliance_assessment_digest_sha256": (
                compliance[
                    "compliance_assessment_digest_sha256"
                ]
            ),
            "wordpress_access_performed": False,
            "wordpress_update_performed": False,
            "execution_allowed": False,
            "created_at_utc": now()
        }

        design = add_digest(
            design_without_digest,
            "design_digest_sha256",
        )
        write_json(DESIGN, design)

        draft_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M20"
            ),
            "document_role": (
                "NON_EXECUTABLE_WORDPRESS_"
                "LAYOUT_CORRECTION_UPDATE_DRAFT"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "expected_current_status": "publish",
            "target_status": "publish",
            "operation": "DESIGN_DRAFT_ONLY",
            "render_mode": (
                "TOKENIZED_TEMPLATE_NOT_READY_FOR_WORDPRESS"
            ),
            "content_template_html": (
                template_html
            ),
            "content_template_css": (
                template_css
            ),
            "required_token_bindings": [
                "COVER_HTML",
                "AMAZON_BUTTON_HTML",
                "RAKUTEN_KOBO_BUTTON_HTML",
                "DMM_BUTTON_HTML",
                "WORK_TITLE_TEXT",
                "PRICE_TEXT",
                "AUTHOR_TEXT",
                "PUBLISHER_TEXT",
                "RELEASE_DATE_TEXT"
            ],
            "comment_status_target": "closed",
            "wordpress_request_body": None,
            "rendered_content_html": None,
            "live_affiliate_links_embedded": False,
            "requested_pr_after_buttons_accepted": False,
            "compliance_adjusted_pr_position": (
                "BEFORE_FIRST_AFFILIATE_BUTTON"
            ),
            "human_approval_of_adjustment_required": True,
            "execution_allowed": False,
            "authorization_issued": False,
            "authorization_consumed": False,
            "ready_for_wordpress_update": False,
            "production_status": "NO_GO",
            "design_digest_sha256": (
                design["design_digest_sha256"]
            ),
            "compliance_assessment_digest_sha256": (
                compliance[
                    "compliance_assessment_digest_sha256"
                ]
            ),
            "created_at_utc": now()
        }

        update_draft = add_digest(
            draft_without_digest,
            "update_draft_payload_digest_sha256",
        )
        write_json(
            UPDATE_DRAFT,
            update_draft,
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M20"
            ),
            "status": (
                "PASS_WORDPRESS_LAYOUT_CORRECTION_"
                "DESIGN_GATE_REQUESTED_PR_POSITION_"
                "BLOCKED_COMPLIANT_ALTERNATIVE_"
                "DRAFTED_LOCAL_ONLY"
            ),
            "decision": (
                "REQUESTED_PR_AFTER_AFFILIATE_LINKS_"
                "REJECTED_COMPLIANT_PR_BEFORE_LINKS_"
                "REQUIRES_HUMAN_APPROVAL"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "requested_layout_compliance_verdict": (
                "BLOCK_REQUESTED_PR_POSITION"
            ),
            "requested_layout_execution_allowed": False,
            "compliant_alternative_drafted": True,
            "compliant_alternative_execution_allowed": False,
            "human_reapproval_required": True,
            "compliance_path": str(
                COMPLIANCE.relative_to(ROOT)
            ),
            "compliance_assessment_digest_sha256": (
                compliance[
                    "compliance_assessment_digest_sha256"
                ]
            ),
            "design_path": str(
                DESIGN.relative_to(ROOT)
            ),
            "design_digest_sha256": (
                design["design_digest_sha256"]
            ),
            "update_draft_path": str(
                UPDATE_DRAFT.relative_to(ROOT)
            ),
            "update_draft_payload_digest_sha256": (
                update_draft[
                    "update_draft_payload_digest_sha256"
                ]
            ),
            "update_draft_rendered_content_present": False,
            "update_draft_wordpress_request_body_present": False,
            "comment_status_target": "closed",
            "future_template_comment_change_executed": False,
            "m19_result_digest_sha256": (
                EXPECTED_M19_RESULT_DIGEST
            ),
            "m19_human_review_digest_sha256": (
                EXPECTED_M19_REVIEW_DIGEST
            ),
            "m18_result_digest_sha256": (
                EXPECTED_M18_RESULT_DIGEST
            ),
            "m17_result_digest_sha256": (
                EXPECTED_M17_RESULT_DIGEST
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
            "authorization_issued": False,
            "authorization_consumed": False,
            "authorization_reused": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "m17_rerun_performed": False,
            "m18_rerun_performed": False,
            "m19_rerun_performed": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "REQUESTED_LAYOUT_BLOCKED_"
                "COMPLIANT_ALTERNATIVE_AWAITING_APPROVAL_"
                "NO_WORDPRESS_UPDATE"
            ),
            "ready_for_compliant_layout_revision_approval": True,
            "ready_for_rendered_update_payload": False,
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M20

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Requested PR position: `after affiliate buttons`
- Requested layout compliance verdict: `BLOCK_REQUESTED_PR_POSITION`
- Compliance assessment type: `conservative operational gate`
- Formal legal opinion: `false`
- Compliant desktop order: `cover left / PR / Amazon / Rakuten Kobo / DMM / details`
- Compliant mobile order: `cover / details / PR / Amazon / Rakuten Kobo / DMM`
- Comment status target for post 192: `closed`
- Rendered update content present: `false`
- WordPress request body present: `false`
- Compliant alternative drafted: `true`
- Human reapproval required: `true`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Authorization issued: `false`
- Production status: `NO_GO`
- Ready for compliant layout revision approval: `true`
- Ready for rendered update payload: `false`
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M20"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_LAYOUT_CORRECTION_"
                        "DESIGN_GATE_NO_WORDPRESS_ACCESS"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
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
