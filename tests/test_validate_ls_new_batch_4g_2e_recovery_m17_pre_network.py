from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

M16_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m17_pre_network_result.json"
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
        "PASS_WORDPRESS_PUBLICATION_"
        "AUTHENTICATED_GET_ONLY_PREFLIGHT_"
        "VERIFIED_NO_AUTH_CONSUMPTION_NO_WRITE"
    )


def test_wordpress_post_contract() -> None:
    value = load(RESULT)

    assert value["wordpress_post_id"] == 192
    assert value[
        "post_id_verified"
    ] is True
    assert value[
        "wordpress_post_status"
    ] == "draft"
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


def test_single_get_no_retry_no_write() -> None:
    value = load(RESULT)

    assert value[
        "wordpress_http_status"
    ] == 200
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
        "wordpress_update_performed"
    ] is False
    assert value[
        "wordpress_publish_performed"
    ] is False
    assert value[
        "wordpress_delete_performed"
    ] is False


def test_m16_authorization_remains_unconsumed() -> None:
    authorization = load(M16_AUTH)
    value = load(RESULT)

    assert stat.S_IMODE(
        M16_AUTH.stat().st_mode
    ) == 0o600
    assert authorization[
        "authorization_digest_sha256"
    ] == (
        "3af20632d3fabe77f04e795318406ecd"
        "0ad9bd7b6d2eb60646e82f108556cc9e"
    )
    assert authorization[
        "authorization_consumed"
    ] is False
    assert value[
        "m16_authorization_consumed"
    ] is False
    assert value[
        "publication_authorization_consumed_in_this_phase"
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


def test_next_gate_and_production_closed() -> None:
    value = load(RESULT)

    assert value[
        "ready_for_wordpress_publication_execute_now_gate"
    ] is True
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
    assert value[
        "authorization_issued_in_this_phase"
    ] is False
    assert value[
        "m16_rerun_performed"
    ] is False
    assert value[
        "x_post_performed"
    ] is False
