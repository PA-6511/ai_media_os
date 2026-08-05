from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)
M12_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
M13_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_network_result.json"
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
        "PASS_WORDPRESS_WRITER_AUTHENTICATED_"
        "NETWORK_PREFLIGHT_GET_ONLY_"
        "NO_DUPLICATE_NO_AUTH_CONSUMPTION"
    )


def test_authentication_and_permission() -> None:
    value = load(RESULT)

    assert value["authenticated"] is True
    assert value["edit_posts"] is True
    assert value[
        "users_me_http_status"
    ] == 200


def test_category_and_duplicate_check() -> None:
    value = load(RESULT)

    assert value[
        "category_id_10_verified"
    ] is True
    assert value[
        "category_name_verified"
    ] is True
    assert value[
        "duplicate_raw_fields_verified"
    ] is True
    assert value[
        "duplicate_exact_match_count"
    ] == 0
    assert value[
        "duplicate_detected"
    ] is False


def test_get_only_and_no_consumption() -> None:
    value = load(RESULT)

    assert value[
        "http_get_request_count"
    ] == 3
    assert value[
        "http_non_get_request_count"
    ] == 0
    assert value[
        "automatic_retry_performed"
    ] is False
    assert value[
        "m12_authorization_consumed"
    ] is False
    assert not M13_CONSUMPTION.exists()


def test_payload_and_authorization_binding() -> None:
    value = load(RESULT)

    assert hashlib.sha256(
        PAYLOAD.read_bytes()
    ).hexdigest() == (
        "30a70be4110e863a85e2896f69f5b3e5"
        "1d814a6fd82d5489f899d8a244166d8f"
    )
    assert stat.S_IMODE(
        PAYLOAD.stat().st_mode
    ) == 0o600
    assert hashlib.sha256(
        M12_AUTH.read_bytes()
    ).hexdigest() == (
        "7c9662a7a13502e165862e4524278992"
        "28794bce6904a0215c45a5b54ba1142b"
    )
    assert value["payload_unchanged"] is True
    assert value["article_unchanged"] is True


def test_external_write_boundaries_closed() -> None:
    value = load(RESULT)

    assert value[
        "wordpress_write_performed"
    ] is False
    assert value[
        "wordpress_draft_created"
    ] is False
    assert value[
        "wordpress_published"
    ] is False
    assert value["category_created"] is False
    assert value["category_updated"] is False
    assert value["media_uploaded"] is False
    assert value["x_post_performed"] is False
    assert value[
        "production_status"
    ] == "NO_GO"
    assert value[
        "ready_for_final_wordpress_draft_creation_execute_now_gate"
    ] is True
