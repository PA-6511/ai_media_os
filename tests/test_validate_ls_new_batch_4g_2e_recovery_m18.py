from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)
M16_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_authorization.json"
)
M17_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_consumption.json"
)
M17_SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_response.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m18_result.json"
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


def test_result_digest_and_status() -> None:
    value = verify_digest(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_PUBLISHED_POST_"
        "EXECUTION_EVIDENCE_VERIFIED_"
        "GET_ONLY_NO_WRITE"
    )


def test_published_post_contract() -> None:
    value = load(RESULT)

    assert value[
        "wordpress_post_id"
    ] == 192
    assert value[
        "post_id_verified"
    ] is True
    assert value[
        "wordpress_post_status"
    ] == "publish"
    assert value[
        "published_status_verified"
    ] is True
    assert value[
        "wordpress_published"
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


def test_single_get_no_write() -> None:
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
        "wordpress_republish_performed"
    ] is False
    assert value[
        "wordpress_delete_performed"
    ] is False


def test_m17_evidence_chain() -> None:
    consumption = verify_digest(
        M17_CONSUMPTION,
        "consumption_evidence_digest_sha256",
    )
    secret = verify_digest(
        M17_SECRET_RESPONSE,
        "secret_response_digest_sha256",
    )
    value = load(RESULT)

    assert stat.S_IMODE(
        M17_CONSUMPTION.stat().st_mode
    ) == 0o600
    assert stat.S_IMODE(
        M17_SECRET_RESPONSE.stat().st_mode
    ) == 0o600

    assert consumption[
        "authorization_consumed"
    ] is True
    assert consumption[
        "authorization_reuse_allowed"
    ] is False
    assert secret[
        "response_received"
    ] is True
    assert secret["http_status"] == 200

    assert value[
        "m17_result_digest_sha256"
    ] == (
        "e405bd6b44b45c8246388b0ea2fa55ac"
        "501e728563cf97d9b82be6c5dad2e93e"
    )
    assert value[
        "m17_consumption_digest_sha256"
    ] == (
        "9fa836ec2fe8c49b160101351e5a913b"
        "0c606af857131b5a0550b81fb04f443e"
    )
    assert value[
        "m17_authorization_consumed"
    ] is True
    assert value[
        "authorization_consumed_in_this_phase"
    ] is False
    assert value[
        "authorization_reused_in_this_phase"
    ] is False


def test_source_files_unchanged() -> None:
    assert hashlib.sha256(
        ARTICLE.read_bytes()
    ).hexdigest() == (
        "de2739c8ae1aa4a50973b983964b0584"
        "4086a2187b9ef337383ad6fa7123697d"
    )
    assert hashlib.sha256(
        PAYLOAD.read_bytes()
    ).hexdigest() == (
        "30a70be4110e863a85e2896f69f5b3e5"
        "1d814a6fd82d5489f899d8a244166d8f"
    )
    assert hashlib.sha256(
        M16_AUTH.read_bytes()
    ).hexdigest() == (
        "0b8eb340f4551497e99d91dc64ab5d47"
        "c149efb098d50ebf6cf981d416624e58"
    )


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
        "ready_for_post_publication_human_review"
    ] is True
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "m17_rerun_performed"
    ] is False
    assert value[
        "x_post_performed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
