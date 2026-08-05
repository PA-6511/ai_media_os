from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ADOPTION = ROOT / (
    "exchange/decisions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_compliant_layout_revision_adoption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m21_result.json"
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


def test_adoption_digest_and_decision() -> None:
    value = verify(
        ADOPTION,
        "adoption_evidence_digest_sha256",
    )

    assert value[
        "human_approval_complete"
    ] is True
    assert value[
        "adoption_decision"
    ] == (
        "ADOPT_M20_COMPLIANT_LAYOUT_REVISION"
    )


def test_desktop_layout_adopted() -> None:
    value = load(ADOPTION)

    assert value[
        "adopted_desktop_layout"
    ]["left_column"] == [
        "cover_image"
    ]
    assert value[
        "adopted_desktop_layout"
    ]["right_column_order"] == [
        "pr_disclosure",
        "amazon_button",
        "rakuten_kobo_button",
        "dmm_button",
        "responsive_work_details",
    ]


def test_mobile_layout_adopted() -> None:
    value = load(ADOPTION)

    assert value[
        "adopted_mobile_order"
    ] == [
        "cover_image",
        "responsive_work_details",
        "pr_disclosure",
        "amazon_button",
        "rakuten_kobo_button",
        "dmm_button",
    ]


def test_pr_and_comment_contracts() -> None:
    value = load(ADOPTION)

    assert value[
        "adopted_pr_contract"
    ]["position"] == (
        "IMMEDIATELY_BEFORE_FIRST_"
        "AFFILIATE_BUTTON"
    )
    assert value[
        "adopted_pr_contract"
    ]["hidden_or_collapsed"] is False

    assert value[
        "adopted_comment_contract"
    ]["comment_status"] == "closed"
    assert value[
        "adopted_comment_contract"
    ]["comment_form_visible"] is False
    assert value[
        "adopted_comment_contract"
    ]["comment_list_visible"] is False


def test_no_payload_or_wordpress_operation() -> None:
    value = load(ADOPTION)

    assert value[
        "rendered_update_payload_generated"
    ] is False
    assert value[
        "wordpress_request_body_generated"
    ] is False
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


def test_result_status() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_COMPLIANT_LAYOUT_"
        "REVISION_HUMAN_APPROVAL_RECORDED_"
        "LOCAL_ONLY_NO_WORDPRESS_ACCESS"
    )
    assert value[
        "compliant_layout_revision_adopted"
    ] is True
    assert value[
        "comment_status_target"
    ] == "closed"


def test_next_gate_remains_closed_for_update() -> None:
    value = load(RESULT)

    assert value[
        "ready_for_rendered_update_payload_generation_gate"
    ] is True
    assert value[
        "ready_for_wordpress_update_authorization_gate"
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
