from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

M13_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m13_result.json"
)
M13_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m14_result.json"
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


def test_result_digest_and_status() -> None:
    value = load(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["status"] == (
        "PASS_WORDPRESS_DRAFT_POST_EXECUTION_"
        "EVIDENCE_VERIFIED_GET_ONLY_NO_WRITE"
    )


def test_post_contract_verified() -> None:
    value = load(RESULT)

    assert value["post_id"] == 192
    assert value[
        "post_id_verified"
    ] is True
    assert value["post_status"] == "draft"
    assert value[
        "draft_status_verified"
    ] is True
    assert value[
        "title_exact_match"
    ] is True
    assert value[
        "content_exact_match"
    ] is True
    assert value[
        "category_id_10_verified"
    ] is True


def test_single_get_and_no_write() -> None:
    value = load(RESULT)

    assert value[
        "wordpress_get_request_count"
    ] == 1
    assert value[
        "wordpress_non_get_request_count"
    ] == 0
    assert value[
        "automatic_retry_performed"
    ] is False
    assert value[
        "wordpress_write_performed"
    ] is False
    assert value[
        "wordpress_draft_updated"
    ] is False
    assert value[
        "wordpress_draft_recreated"
    ] is False
    assert value[
        "wordpress_published"
    ] is False


def test_m13_consumption_remains_fixed() -> None:
    m13 = load(M13_RESULT)
    consumption = load(
        M13_CONSUMPTION
    )
    value = load(RESULT)

    assert m13[
        "result_digest_sha256"
    ] == (
        "34bb7a2cd15cfd829a805c1e974ca62c"
        "c453036132a25c41d7fd17b3ae681e0d"
    )
    assert consumption[
        "consumption_evidence_digest_sha256"
    ] == (
        "a9c96f8fddc4bfebeebce2d535936a21"
        "e9214bb9ac6688e7277aa6def171aaba"
    )
    assert value[
        "m13_authorization_consumed"
    ] is True
    assert value[
        "m13_authorization_reuse_allowed"
    ] is False
    assert value[
        "authorization_consumed_in_this_phase"
    ] is False


def test_secret_output_boundaries() -> None:
    value = load(RESULT)

    assert value[
        "credential_values_output"
    ] is False
    assert value[
        "username_output"
    ] is False
    assert value[
        "application_password_output"
    ] is False
    assert value[
        "authorization_header_output"
    ] is False
    assert value[
        "full_wordpress_response_output"
    ] is False
    assert value[
        "full_post_content_output"
    ] is False
    assert value[
        "full_affiliate_url_output"
    ] is False
    assert value[
        "dmm_identifier_output"
    ] is False


def test_review_gate_and_production_closed() -> None:
    value = load(RESULT)

    assert value[
        "ready_for_human_wordpress_draft_review"
    ] is True
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
    assert value[
        "m13_rerun_performed"
    ] is False
    assert value[
        "x_post_performed"
    ] is False
