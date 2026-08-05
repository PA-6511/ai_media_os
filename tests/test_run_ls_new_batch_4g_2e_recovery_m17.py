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
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_consumption.json"
)
SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_response.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m17_result.json"
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


def test_result_success() -> None:
    value = verify_digest(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_PUBLICATION_"
        "ONE_SHOT_AUTHORIZATION_CONSUMED_"
        "POST_192_PUBLISHED_NO_RETRY"
    )
    assert value[
        "publication_verified"
    ] is True


def test_authorization_consumption() -> None:
    value = verify_digest(
        CONSUMPTION,
        "consumption_evidence_digest_sha256",
    )

    assert stat.S_IMODE(
        CONSUMPTION.stat().st_mode
    ) == 0o600
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


def test_secret_response() -> None:
    value = verify_digest(
        SECRET_RESPONSE,
        "secret_response_digest_sha256",
    )

    assert stat.S_IMODE(
        SECRET_RESPONSE.stat().st_mode
    ) == 0o600
    assert value[
        "response_received"
    ] is True
    assert value["http_status"] == 200
    assert value[
        "final_response_url_verified"
    ] is True


def test_publication_contract() -> None:
    value = load(RESULT)

    assert value[
        "pre_publication_get_request_count"
    ] == 1
    assert value[
        "publication_post_request_count"
    ] == 1
    assert value[
        "wordpress_http_status"
    ] == 200
    assert value[
        "returned_wordpress_status"
    ] == "publish"
    assert value[
        "post_id_verified"
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
    assert value[
        "wordpress_published"
    ] is True
    assert value["publication_count"] == 1


def test_no_unapproved_changes() -> None:
    value = load(RESULT)

    assert value[
        "publication_request_status_only"
    ] is True
    assert value[
        "title_field_sent"
    ] is False
    assert value[
        "content_field_sent"
    ] is False
    assert value[
        "categories_field_sent"
    ] is False
    assert value[
        "title_change_performed"
    ] is False
    assert value[
        "content_change_performed"
    ] is False
    assert value[
        "category_change_performed"
    ] is False
    assert value[
        "post_delete_performed"
    ] is False
    assert value[
        "post_recreation_performed"
    ] is False
    assert value[
        "media_operation_performed"
    ] is False
    assert value[
        "x_post_performed"
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


def test_post_publication_gate() -> None:
    value = load(RESULT)

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
    assert value[
        "publication_result_unknown"
    ] is False
    assert value[
        "ready_for_post_publication_evidence_review"
    ] is True
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
