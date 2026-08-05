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
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_fix1_authorization.json"
)
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_fix1_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m9_fix1_result.json"
)
SECRET_LINK = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
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


def test_authorization_digest() -> None:
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


def test_consumption_digest() -> None:
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
        "automatic_retry_allowed"
    ] is False
    assert value[
        "automatic_reissue_allowed"
    ] is False


def test_result_digest_and_success() -> None:
    value = load(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["status"] == (
        "PASS_DMM_ARTICLE_LINK_INJECTED_"
        "HTML_ENTITY_VALIDATOR_FIXED_"
        "NEW_AUTHORIZATION_CONSUMED_"
        "NO_NETWORK_NO_WORDPRESS"
    )


def test_decoded_href_exact_match() -> None:
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


def test_navigation_state() -> None:
    navigation = load(ARTICLE)[
        "store_navigation"
    ]

    assert navigation["render_mode"] == (
        "PARTIAL_ACTIVE_STORE_LINKS"
    )
    assert navigation[
        "anchor_elements_included"
    ] is True
    assert navigation[
        "href_attributes_included"
    ] is True
    assert navigation[
        "final_affiliate_urls_included"
    ] is True
    assert navigation[
        "dmm_url_included"
    ] is True


def test_external_boundaries_closed() -> None:
    result = load(RESULT)

    assert result[
        "network_connection_performed"
    ] is False
    assert result[
        "payload_created"
    ] is False
    assert result[
        "wordpress_access_performed"
    ] is False
    assert result[
        "wordpress_published"
    ] is False
    assert result[
        "x_post_performed"
    ] is False
    assert result[
        "production_status"
    ] == "NO_GO"
