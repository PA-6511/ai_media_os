from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_published_post_human_review_changes_required.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m19_result.json"
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


def verify_digest(
    path: Path,
    field: str,
) -> dict:
    value = load(path)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field)

    assert digest(comparable) == stored
    return value


def test_review_digest_and_verdict() -> None:
    value = verify_digest(
        REVIEW,
        "human_review_evidence_digest_sha256",
    )

    assert stat.S_IMODE(
        REVIEW.stat().st_mode
    ) == 0o600
    assert value[
        "review_verdict"
    ] == "CHANGES_REQUIRED"
    assert value[
        "change_required"
    ] is True


def test_result_digest_and_status() -> None:
    value = verify_digest(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_PUBLISHED_POST_"
        "HUMAN_REVIEW_CHANGES_REQUIRED_"
        "RECORDED_LOCAL_ONLY_NO_WORDPRESS_ACCESS"
    )
    assert value[
        "wordpress_post_id"
    ] == 192


def test_desktop_layout_contract() -> None:
    value = load(REVIEW)
    layout = value[
        "approved_desktop_layout"
    ]

    assert layout["left_column"] == [
        "cover_image"
    ]
    assert layout[
        "right_column_order"
    ] == [
        "amazon_button",
        "rakuten_kobo_button",
        "dmm_button",
        "responsive_work_details",
        "pr_disclosure",
    ]
    assert layout[
        "store_buttons_vertical"
    ] is True
    assert layout[
        "work_details_format"
    ] == "LABEL_VALUE_RESPONSIVE"


def test_mobile_layout_contract() -> None:
    value = load(REVIEW)

    assert value[
        "approved_mobile_layout"
    ]["content_order"] == [
        "cover_image",
        "responsive_work_details",
        "amazon_button",
        "rakuten_kobo_button",
        "dmm_button",
        "pr_disclosure",
    ]


def test_comment_policy() -> None:
    value = load(REVIEW)
    comments = value[
        "approved_comment_policy"
    ]

    assert comments[
        "comment_status"
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


def test_no_external_operation() -> None:
    value = load(RESULT)

    assert value[
        "network_connection_performed"
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
        "wordpress_republish_performed"
    ] is False
    assert value[
        "authorization_reused"
    ] is False
    assert value[
        "automatic_retry_performed"
    ] is False


def test_next_gate_closed_for_update() -> None:
    value = load(RESULT)

    assert value[
        "ready_for_layout_correction_design_gate"
    ] is True
    assert value[
        "ready_for_wordpress_update"
    ] is False
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
