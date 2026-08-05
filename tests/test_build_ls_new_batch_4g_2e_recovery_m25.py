from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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


def test_human_review_evidence() -> None:
    value = verify(
        HUMAN_REVIEW,
        "human_review_evidence_digest_sha256",
    )

    assert value[
        "human_review_completed"
    ] is True
    assert value[
        "human_review_verdict"
    ] == "APPROVED_NO_CHANGE_REQUIRED"
    assert value[
        "desktop_review"
    ]["verdict"] == "APPROVED_NO_CHANGE_REQUIRED"
    assert value[
        "mobile_review"
    ]["verdict"] == "APPROVED_NO_CHANGE_REQUIRED"
    assert value[
        "layout_change_required"
    ] is False


def test_mobile_review_boundary() -> None:
    value = load(HUMAN_REVIEW)

    assert value[
        "mobile_review"
    ]["horizontal_scroll_detected"] is False
    assert value[
        "mobile_review"
    ]["pr_before_buttons"] is True
    assert value[
        "mobile_review"
    ]["store_order_approved"] is True


def test_future_requirement_recorded() -> None:
    value = verify(
        FUTURE_REQUIREMENT,
        "future_requirement_digest_sha256",
    )

    assert value[
        "requirement_id"
    ] == "SERIES_BACKLIST_COVER_AFFILIATE_CAROUSEL_V1"
    assert value[
        "recommended_implementation_phase_id"
    ] == "LS-NEW-SERIES-BACKLIST-1"
    assert value[
        "status"
    ] == "FUTURE_REQUIREMENT_RECORDED_NOT_IMPLEMENTED"
    assert value[
        "implementation_authorized"
    ] is False


def test_future_requirement_fields() -> None:
    value = load(FUTURE_REQUIREMENT)

    required = set(
        value["required_volume_fields"]
    )

    assert {
        "volume_number",
        "cover_image",
        "product_title",
        "release_date",
        "amazon_affiliate_route",
        "rakuten_kobo_affiliate_route",
        "dmm_affiliate_route",
        "link_state",
        "cover_source",
    } == required

    assert value[
        "required_rendering_controls"
    ]["image_lazy_loading"] is True
    assert value[
        "required_rendering_controls"
    ]["duplicate_volume_prevention"] is True
    assert value[
        "required_rendering_controls"
    ]["broken_link_click_prevention"] is True


def test_future_requirement_not_in_current_payload() -> None:
    value = load(FUTURE_REQUIREMENT)

    assert value[
        "current_m24_rendered_html_modified"
    ] is False
    assert value[
        "current_m24_css_modified"
    ] is False
    assert value[
        "current_m24_update_payload_modified"
    ] is False
    assert value[
        "included_in_current_wordpress_update"
    ] is False


def test_result_status_and_gate() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
        "HUMAN_REVIEW_APPROVED_NO_CHANGE_REQUIRED_"
        "BACKLIST_FUTURE_REQUIREMENT_RECORDED_"
        "LOCAL_ONLY_NO_WORDPRESS_ACCESS"
    )
    assert value[
        "human_review_completed"
    ] is True
    assert value[
        "human_review_verdict"
    ] == "APPROVED_NO_CHANGE_REQUIRED"
    assert value[
        "ready_for_wordpress_update_authorization_gate"
    ] is True
    assert value[
        "ready_for_wordpress_update"
    ] is False


def test_current_update_boundary_unchanged() -> None:
    value = load(RESULT)

    assert value[
        "comment_status_target"
    ] == "closed"
    assert value[
        "allowed_update_fields"
    ] == [
        "content",
        "comment_status",
    ]
    assert value[
        "m24_rendered_html_modified"
    ] is False
    assert value[
        "m24_css_modified"
    ] is False
    assert value[
        "m24_update_payload_modified"
    ] is False


def test_no_external_or_wordpress_operation() -> None:
    value = load(RESULT)

    assert value[
        "network_connection_performed"
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
    assert value[
        "authorization_reused"
    ] is False
    assert value[
        "automatic_retry_performed"
    ] is False
    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"


def test_output_modes() -> None:
    for path in [
        HUMAN_REVIEW,
        FUTURE_REQUIREMENT,
        RESULT,
    ]:
        assert stat.S_IMODE(
            path.stat().st_mode
        ) == 0o600
