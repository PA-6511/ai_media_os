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
    "wordpress_draft_post_execution_human_review.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m15_result.json"
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


def test_review_digest_and_mode() -> None:
    value = verify_digest(
        REVIEW,
        "human_review_evidence_digest_sha256",
    )

    assert stat.S_IMODE(
        REVIEW.stat().st_mode
    ) == 0o600
    assert value[
        "review_verdict"
    ] == "APPROVED_NO_CHANGE_REQUIRED"


def test_result_digest_and_status() -> None:
    value = verify_digest(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_DRAFT_HUMAN_"
        "REVIEW_RECORDED_NO_CHANGE_"
        "REQUIRED_NO_WORDPRESS_ACCESS"
    )
    assert value["wordpress_post_id"] == 192


def test_human_review_assertions() -> None:
    value = load(REVIEW)

    assert value[
        "human_review_complete"
    ] is True
    assert value[
        "title_confirmed"
    ] is True
    assert value[
        "draft_status_confirmed"
    ] is True
    assert value[
        "category_confirmed"
    ] is True
    assert value[
        "body_layout_confirmed"
    ] is True
    assert value[
        "dmm_button_display_confirmed"
    ] is True
    assert value[
        "dmm_button_enabled_state_confirmed"
    ] is True
    assert value[
        "secret_information_non_exposure_confirmed"
    ] is True
    assert value[
        "publish_action_not_performed"
    ] is True
    assert value["change_required"] is False


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
        "wordpress_published"
    ] is False
    assert value[
        "authorization_consumed_in_this_phase"
    ] is False


def test_prior_phases_not_rerun() -> None:
    value = load(RESULT)

    assert value[
        "m13_rerun_performed"
    ] is False
    assert value[
        "m14_rerun_performed"
    ] is False
    assert value[
        "source_artifacts_modified"
    ] is False


def test_publication_gate_closed() -> None:
    value = load(RESULT)

    assert value[
        "ready_for_separate_wordpress_publication_authorization_gate"
    ] is True
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
