from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]

BUILDER = ROOT / (
    "scripts/"
    "build_ls_new_batch_4g_2e_"
    "recovery_m8_fix1.py"
)
ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_human_review.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_authorization.json"
)
M8_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m8_result.json"
)
FIX_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m8_fix1_result.json"
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


def load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "m8_fix1_builder",
        BUILDER,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


def test_html_slot_parser_exact_match() -> None:
    builder = load_builder()
    article = load(ARTICLE)

    parser = builder.ReservedSlotParser()
    parser.feed(article["content_html"])
    parser.close()

    assert len(parser.matches) == 1

    slot = parser.matches[0]

    assert slot["tag"] == "span"
    assert slot["aria_disabled"] == "true"
    assert slot["href_present"] is False
    assert (
        slot["descendant_anchor_count"]
        == 0
    )
    assert slot["normalized_text"] == (
        "DMMブックスで確認（再確認待ち）"
    )

    required = {
        "ls-store-btn",
        "ls-store-dmm",
        "ls-store-disabled",
    }

    assert required.issubset(
        set(slot["class_tokens"])
    )


def test_article_preimage_unchanged() -> None:
    assert hashlib.sha256(
        ARTICLE.read_bytes()
    ).hexdigest() == (
        "849a37519c6af70d2212ec01d5cddef5"
        "793bfa811e97ca9f248ce099a0350bf4"
    )


def test_review_digest() -> None:
    value = load(REVIEW)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "human_review_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["review_verdict"] == (
        "APPROVED_NO_CHANGE_REQUIRED"
    )


def test_authorization_digest_and_state() -> None:
    value = load(AUTHORIZATION)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "authorization_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["single_use"] is True
    assert (
        value["authorization_consumed"]
        is False
    )
    assert (
        value[
            "authorization_reuse_allowed"
        ]
        is False
    )
    assert (
        value["automatic_retry_allowed"]
        is False
    )
    assert (
        value["actual_injection_allowed"]
        is False
    )


def test_m8_result_digest_and_state() -> None:
    value = load(M8_RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value[
        "ready_for_ls_new_batch_4g_2e_recovery_m9"
    ] is True
    assert (
        value["article_modified"]
        is False
    )
    assert (
        value[
            "network_connection_performed"
        ]
        is False
    )


def test_fix_result_digest_and_state() -> None:
    value = load(FIX_RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "fix_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value[
        "html_slot_match_count"
    ] == 1
    assert value[
        "m8_review_rebuilt"
    ] is True
    assert value[
        "m9_authorization_created"
    ] is True
    assert value[
        "m9_authorization_consumed"
    ] is False


def test_builder_contains_no_network_code() -> None:
    source = BUILDER.read_text(
        encoding="utf-8"
    )

    for forbidden in [
        "urllib.request",
        "requests.get(",
        "requests.post(",
        "urlopen(",
        "opener.open(",
        "http.client",
        "import socket",
        "socket.create_connection",
    ]:
        assert forbidden not in source
