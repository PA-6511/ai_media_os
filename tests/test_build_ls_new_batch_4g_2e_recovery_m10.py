from __future__ import annotations

import copy
import hashlib
import html
import json
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
SECRET_LINK = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
)
REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "post_injection_article_human_review.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "fresh_payload_generation_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m10_result.json"
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


class Finder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.hrefs: list[str] = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        attrs = dict(attrs)

        if (
            tag == "a"
            and "ls-store-dmm"
            in attrs.get(
                "class",
                "",
            ).split()
        ):
            self.hrefs.append(
                html.unescape(
                    attrs.get(
                        "href",
                        "",
                    )
                )
            )


def test_article_postimage_sha() -> None:
    assert hashlib.sha256(
        ARTICLE.read_bytes()
    ).hexdigest() == (
        "de2739c8ae1aa4a50973b983964b0584"
        "4086a2187b9ef337383ad6fa7123697d"
    )


def test_review_digest_and_verdict() -> None:
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
        value["automatic_reissue_allowed"]
        is False
    )
    assert (
        value[
            "actual_payload_generation_allowed"
        ]
        is False
    )


def test_dmm_href_matches_secret() -> None:
    article = load(ARTICLE)
    secret = load(SECRET_LINK)

    finder = Finder()
    finder.feed(
        article["content_html"]
    )
    finder.close()

    assert len(finder.hrefs) == 1
    assert finder.hrefs[0] == (
        secret["final_affiliate_url"]
    )


def test_payload_contract_fixed() -> None:
    value = load(AUTHORIZATION)[
        "payload_contract"
    ]

    assert value["template_id"] == (
        "POST185_STANDARD_TEMPLATE_V1_FIXED"
    )
    assert value[
        "category_mapping_id"
    ] == (
        "COMIC_NEW_RELEASE_LATEST_VOLUME_"
        "TO_WP_CATEGORY_10"
    )
    assert value["category_id"] == 10
    assert value["category_name"] == "最新巻"
    assert value["post_status"] == "draft"
    assert value["publish_allowed"] is False


def test_result_digest_and_boundaries() -> None:
    value = load(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["status"] == (
        "PASS_POST_INJECTION_ARTICLE_"
        "HUMAN_REVIEW_APPROVED_FRESH_"
        "PAYLOAD_AUTHORIZATION_FIXED_"
        "NO_PAYLOAD_NO_NETWORK"
    )
    assert value["article_modified"] is False
    assert value["payload_created"] is False
    assert (
        value[
            "network_connection_performed"
        ]
        is False
    )
    assert (
        value[
            "wordpress_access_performed"
        ]
        is False
    )
    assert value["production_status"] == "NO_GO"
