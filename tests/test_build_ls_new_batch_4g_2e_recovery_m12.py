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
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m12_result.json"
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


def test_payload_binding_unchanged() -> None:
    assert hashlib.sha256(
        PAYLOAD.read_bytes()
    ).hexdigest() == (
        "30a70be4110e863a85e2896f69f5b3e5"
        "1d814a6fd82d5489f899d8a244166d8f"
    )

    assert stat.S_IMODE(
        PAYLOAD.stat().st_mode
    ) == 0o600


def test_authorization_digest() -> None:
    value = load(AUTHORIZATION)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "authorization_digest_sha256"
    )

    assert digest(comparable) == stored


def test_authorization_state() -> None:
    value = load(AUTHORIZATION)

    assert value["authorization_id"] == (
        "WORDPRESS_DRAFT_CREATION_"
        "ONE_SHOT_AUTHORIZATION_V1"
    )
    assert value["single_use"] is True
    assert value[
        "authorization_consumed"
    ] is False
    assert value[
        "authorization_reuse_allowed"
    ] is False
    assert value[
        "automatic_retry_allowed"
    ] is False
    assert value[
        "automatic_reissue_allowed"
    ] is False
    assert value[
        "actual_wordpress_draft_creation_allowed"
    ] is False


def test_authorization_scope() -> None:
    contract = load(AUTHORIZATION)[
        "wordpress_draft_contract"
    ]

    assert contract[
        "maximum_draft_count"
    ] == 1
    assert contract["post_status"] == "draft"
    assert contract["publish"] is False
    assert contract["category_id"] == 10
    assert contract["categories"] == [10]
    assert contract[
        "update_existing_post_allowed"
    ] is False
    assert contract[
        "delete_post_allowed"
    ] is False
    assert contract[
        "media_upload_allowed"
    ] is False


def test_result_digest_and_readiness() -> None:
    value = load(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["status"] == (
        "PASS_WORDPRESS_DRAFT_CREATION_"
        "ONE_SHOT_AUTHORIZATION_GATE_FIXED_"
        "NO_NETWORK_NO_WORDPRESS"
    )
    assert value[
        "ready_for_ls_new_batch_4g_2e_recovery_m13"
    ] is True
    assert value[
        "ready_for_wordpress_draft_creation"
    ] is False


def test_external_boundaries_closed() -> None:
    value = load(RESULT)

    assert value[
        "authorization_consumed_in_this_phase"
    ] is False
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
        "wordpress_draft_created"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
