from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def verify(
    path: Path,
    field: str,
) -> dict:
    value = load(path)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field)

    assert digest(comparable) == stored
    assert stat.S_IMODE(
        path.stat().st_mode
    ) == 0o600

    return value


def test_compliance_gate_blocks_requested_position() -> None:
    value = verify(
        COMPLIANCE,
        "compliance_assessment_digest_sha256",
    )

    assert value[
        "requested_layout_verdict"
    ] == "BLOCK_REQUESTED_PR_POSITION"
    assert value[
        "risk_findings"
    ][
        "affiliate_buttons_reachable_before_disclosure"
    ] is True
    assert value[
        "wordpress_update_allowed"
    ] is False


def test_compliant_design_order() -> None:
    value = verify(
        DESIGN,
        "design_digest_sha256",
    )

    assert value[
        "requested_layout"
    ]["status"] == (
        "BLOCKED_BY_PR_DISCLOSURE_"
        "POSITION_COMPLIANCE_GATE"
    )

    assert value[
        "compliant_alternative"
    ]["desktop"]["right_column_order"] == [
        "pr_disclosure",
        "amazon_button",
        "rakuten_kobo_button",
        "dmm_button",
        "responsive_work_details",
    ]

    assert value[
        "compliant_alternative"
    ]["mobile_order"] == [
        "cover_image",
        "responsive_work_details",
        "pr_disclosure",
        "amazon_button",
        "rakuten_kobo_button",
        "dmm_button",
    ]


def test_comment_correction_design() -> None:
    value = load(DESIGN)
    comments = value[
        "comment_correction"
    ]

    assert comments[
        "post_id_192_comment_status"
    ] == "closed"
    assert comments[
        "comment_form_visible"
    ] is False
    assert comments[
        "comment_list_visible"
    ] is False
    assert comments[
        "comment_heading_visible"
    ] is False


def test_update_draft_is_not_executable() -> None:
    value = verify(
        UPDATE_DRAFT,
        "update_draft_payload_digest_sha256",
    )

    assert value[
        "operation"
    ] == "DESIGN_DRAFT_ONLY"
    assert value[
        "rendered_content_html"
    ] is None
    assert value[
        "wordpress_request_body"
    ] is None
    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "authorization_issued"
    ] is False
    assert value[
        "authorization_consumed"
    ] is False


def test_result_status() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_LAYOUT_CORRECTION_"
        "DESIGN_GATE_REQUESTED_PR_POSITION_"
        "BLOCKED_COMPLIANT_ALTERNATIVE_"
        "DRAFTED_LOCAL_ONLY"
    )
    assert value[
        "requested_layout_execution_allowed"
    ] is False
    assert value[
        "compliant_alternative_drafted"
    ] is True
    assert value[
        "human_reapproval_required"
    ] is True


def test_no_external_operation() -> None:
    value = load(RESULT)

    assert value[
        "network_connection_performed"
    ] is False
    assert value[
        "dns_resolution_performed"
    ] is False
    assert value[
        "http_request_performed"
    ] is False
    assert value[
        "wordpress_access_performed"
    ] is False
    assert value[
        "wordpress_write_performed"
    ] is False
    assert value[
        "wordpress_update_performed"
    ] is False
    assert value[
        "authorization_issued"
    ] is False
    assert value[
        "authorization_consumed"
    ] is False


def test_next_gate_remains_closed_for_update() -> None:
    value = load(RESULT)

    assert value[
        "ready_for_compliant_layout_revision_approval"
    ] is True
    assert value[
        "ready_for_rendered_update_payload"
    ] is False
    assert value[
        "ready_for_wordpress_update"
    ] is False
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
