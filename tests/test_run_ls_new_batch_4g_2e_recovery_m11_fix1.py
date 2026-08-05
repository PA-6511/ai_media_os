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
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "fresh_payload_generation_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m11_fix1_result.json"
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


def test_article_schema_title_field() -> None:
    article = load(ARTICLE)

    assert "title" not in article
    assert article["article_title"] == (
        "ダークギャザリング 第20巻｜配信開始"
    )


def test_payload_digest_and_mode() -> None:
    value = load(PAYLOAD)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "payload_digest_sha256"
    )

    assert digest(comparable) == stored
    assert stat.S_IMODE(
        PAYLOAD.stat().st_mode
    ) == 0o600


def test_payload_title_from_article_title() -> None:
    article = load(ARTICLE)
    payload = load(PAYLOAD)

    assert payload["title_source_field"] == (
        "article_title"
    )
    assert payload["title"] == (
        article["article_title"]
    )
    assert payload["content_html"] == (
        article["content_html"]
    )


def test_payload_contract() -> None:
    payload = load(PAYLOAD)

    assert payload["post_status"] == "draft"
    assert payload["status"] == "draft"
    assert payload["publish"] is False
    assert payload["template_id"] == (
        "POST185_STANDARD_TEMPLATE_V1_FIXED"
    )
    assert payload[
        "category_mapping_id"
    ] == (
        "COMIC_NEW_RELEASE_LATEST_VOLUME_"
        "TO_WP_CATEGORY_10"
    )
    assert payload["category_id"] == 10
    assert payload["categories"] == [10]
    assert payload["category_name"] == "最新巻"


def test_consumption_digest_and_state() -> None:
    value = load(CONSUMPTION)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "consumption_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
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


def test_result_digest_and_boundaries() -> None:
    value = load(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["status"] == (
        "PASS_FRESH_PAYLOAD_ARTICLE_TITLE_"
        "FIELD_VALIDATOR_FIXED_PAYLOAD_GENERATED_"
        "AUTHORIZATION_CONSUMED_NO_NETWORK_NO_WORDPRESS"
    )
    assert value[
        "article_title_exact_match_verified"
    ] is True
    assert value[
        "content_html_exact_article_match"
    ] is True
    assert value["article_modified"] is False
    assert value[
        "network_connection_performed"
    ] is False
    assert value[
        "wordpress_access_performed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
