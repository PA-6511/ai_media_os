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
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)
SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_response.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m13_result.json"
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


def verify_internal_digest(
    path: Path,
    field: str,
) -> dict:
    value = load(path)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field)

    assert digest(comparable) == stored

    return value


def test_result_success_and_digest() -> None:
    value = verify_internal_digest(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_DRAFT_CREATED_"
        "ONE_SHOT_AUTHORIZATION_CONSUMED_"
        "NO_PUBLISH_NO_RETRY"
    )
    assert value[
        "wordpress_http_status"
    ] == 201
    assert value[
        "wordpress_draft_created"
    ] is True
    assert value[
        "created_draft_count"
    ] == 1


def test_authorization_consumption() -> None:
    value = verify_internal_digest(
        CONSUMPTION,
        "consumption_evidence_digest_sha256",
    )

    assert value[
        "authorization_consumed"
    ] is True
    assert value[
        "authorization_reuse_allowed"
    ] is False
    assert value[
        "automatic_retry_allowed"
    ] is False
    assert value[
        "automatic_reissue_allowed"
    ] is False


def test_secret_response_protected() -> None:
    value = verify_internal_digest(
        SECRET_RESPONSE,
        "secret_response_digest_sha256",
    )

    assert stat.S_IMODE(
        SECRET_RESPONSE.stat().st_mode
    ) == 0o600
    assert value[
        "response_received"
    ] is True
    assert value["http_status"] == 201


def test_payload_and_authorization_unchanged() -> None:
    assert hashlib.sha256(
        PAYLOAD.read_bytes()
    ).hexdigest() == (
        "30a70be4110e863a85e2896f69f5b3e5"
        "1d814a6fd82d5489f899d8a244166d8f"
    )
    assert hashlib.sha256(
        M12_AUTH.read_bytes()
    ).hexdigest() == (
        "7c9662a7a13502e165862e4524278992"
        "28794bce6904a0215c45a5b54ba1142b"
    )


def test_response_contract() -> None:
    value = load(RESULT)

    assert value[
        "wordpress_post_id"
    ] > 0
    assert value[
        "wordpress_post_status"
    ] == "draft"
    assert value[
        "title_exact_match"
    ] is True
    assert value[
        "content_exact_match"
    ] is True
    assert value[
        "category_id_10_verified"
    ] is True
    assert value[
        "request_fields_exactly_limited"
    ] is True
    assert value[
        "template_field_sent"
    ] is False


def test_publish_and_other_writes_blocked() -> None:
    value = load(RESULT)

    assert value[
        "wordpress_published"
    ] is False
    assert value[
        "existing_post_updated"
    ] is False
    assert value["post_deleted"] is False
    assert value[
        "category_created"
    ] is False
    assert value[
        "category_updated"
    ] is False
    assert value[
        "media_uploaded"
    ] is False
    assert value[
        "x_post_performed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
    assert value[
        "ready_for_wordpress_publish"
    ] is False
