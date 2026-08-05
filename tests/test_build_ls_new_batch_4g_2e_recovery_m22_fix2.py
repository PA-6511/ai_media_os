from __future__ import annotations

import copy
import hashlib
import json
import re
import stat
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
FAILURE_CHAIN = ROOT / (
    "exchange/failures/new_release/fresh/"
    "new-release-comic-20260703-001."
    "m22_m22_fix1_failure_chain.json"
)
ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)
SCOPED_CSS = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_scoped_fix2.css"
)
RENDERED_HTML = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_rendered_fix2.html"
)
UPDATE_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_rendered_update_payload_fix2.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m22_fix2_result.json"
)

EXPECTED_EVENTS = [
    "cover_image",
    "responsive_work_details",
    "pr_disclosure",
    "store_container",
    "amazon_button",
    "rakuten_kobo_button",
    "dmm_button",
]


def load(
    path: Path,
) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(
    value,
) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def text_sha(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def verify(
    path: Path,
    field: str,
) -> dict:
    value = load(path)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field)

    assert digest(comparable) == stored
    assert stat.S_IMODE(
        path.stat().st_mode
    ) == 0o600

    return value


def classes(
    attrs,
) -> set[str]:
    value = dict(attrs).get("class")

    if not isinstance(value, str):
        return set()

    return set(value.split())


class DOMOrderParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.stack: list[str] = []
        self.inside_root = False
        self.root_depth = None
        self.root_count = 0
        self.events: list[str] = []

    def record(
        self,
        attrs,
    ) -> None:
        tokens = classes(attrs)

        if "ebook-product-card__cover" in tokens:
            self.events.append("cover_image")
        elif "ebook-product-card__details" in tokens:
            self.events.append(
                "responsive_work_details"
            )
        elif "ebook-product-card__pr" in tokens:
            self.events.append("pr_disclosure")
        elif "ebook-product-card__stores" in tokens:
            self.events.append("store_container")
        elif "ls-store-amazon" in tokens:
            self.events.append("amazon_button")
        elif "ls-store-kobo" in tokens:
            self.events.append(
                "rakuten_kobo_button"
            )
        elif "ls-store-dmm" in tokens:
            self.events.append("dmm_button")

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        mapping = dict(attrs)

        if mapping.get("id") == "ebook-product-192":
            self.root_count += 1
            self.inside_root = True
            self.root_depth = len(self.stack)

        if self.inside_root:
            self.record(attrs)

        self.stack.append(tag)

    def handle_startendtag(
        self,
        tag,
        attrs,
    ):
        if self.inside_root:
            self.record(attrs)

    def handle_endtag(
        self,
        tag,
    ):
        if self.stack:
            self.stack.pop()

        if (
            self.inside_root
            and self.root_depth is not None
            and len(self.stack) == self.root_depth
        ):
            self.inside_root = False


class URLScanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.urls: list[str] = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        mapping = dict(attrs)

        for field in ("href", "src"):
            value = mapping.get(field)

            if isinstance(value, str):
                self.urls.append(value)

    def handle_startendtag(
        self,
        tag,
        attrs,
    ):
        self.handle_starttag(tag, attrs)


def urls(
    value: str,
) -> list[str]:
    parser = URLScanner()
    parser.feed(value)
    parser.close()
    return parser.urls


def require_order(
    css: str,
    selector_class: str,
    order: int,
) -> None:
    pattern = (
        rf"#ebook-product-192\s+"
        rf"\.{re.escape(selector_class)}\s*"
        rf"\{{[^}}]*\border\s*:\s*{order}\s*;"
    )

    assert re.search(
        pattern,
        css,
        flags=re.DOTALL,
    )


def test_failure_chain_recorded() -> None:
    value = verify(
        FAILURE_CHAIN,
        "failure_chain_digest_sha256",
    )

    assert len(value["failures"]) == 2

    assert value["failures"][0][
        "classification"
    ] == "STYLE_ELEMENT_TEXT_FALSE_POSITIVE"

    assert value["failures"][1][
        "classification"
    ] == "RESULT_SCHEMA_FIELD_NAME_MISMATCH"

    assert value["failures"][1][
        "generated_field_name"
    ] == "previous_m22_rerun_performed"

    assert value["failures"][1][
        "incorrect_test_field_name"
    ] == "original_m22_rerun_performed"

    assert value[
        "canonical_result_field_name"
    ] == "previous_m22_rerun_performed"

    assert value[
        "deprecated_result_field_allowed"
    ] is False


def test_result_digest_status_and_schema() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_RENDERED_LAYOUT_CORRECTION_"
        "RESULT_SCHEMA_FIXED_DOM_VALIDATED_UPDATE_"
        "PAYLOAD_GENERATED_LOCAL_ONLY_NON_EXECUTABLE_"
        "NO_WORDPRESS_ACCESS"
    )

    assert value[
        "result_schema_fixed"
    ] is True

    assert value[
        "canonical_result_field_name"
    ] == "previous_m22_rerun_performed"

    assert value[
        "previous_m22_rerun_performed"
    ] is False

    assert value[
        "previous_m22_fix1_rerun_performed"
    ] is False

    assert (
        "original_m22_rerun_performed"
        not in value
    )

    assert value[
        "deprecated_result_field_present"
    ] is False


def test_dom_order_ignores_style_text() -> None:
    rendered = RENDERED_HTML.read_text(
        encoding="utf-8"
    )

    parser = DOMOrderParser()
    parser.feed(rendered)
    parser.close()

    assert parser.root_count == 1
    assert parser.events == EXPECTED_EVENTS

    result = load(RESULT)

    assert result[
        "dom_event_order_verified"
    ] == EXPECTED_EVENTS

    assert result[
        "validator_type"
    ] == "HTMLPARSER_DOM_ONLY"

    assert result[
        "style_element_text_ignored"
    ] is True

    assert result[
        "plain_string_index_order_validation_used"
    ] is False


def test_mobile_and_desktop_css_orders() -> None:
    css = SCOPED_CSS.read_text(
        encoding="utf-8"
    )

    marker = "@media (min-width: 768px)"
    assert marker in css

    mobile_css, desktop_css = css.split(
        marker,
        1,
    )

    require_order(
        mobile_css,
        "ebook-product-card__details",
        1,
    )
    require_order(
        mobile_css,
        "ebook-product-card__pr",
        2,
    )
    require_order(
        mobile_css,
        "ebook-product-card__stores",
        3,
    )

    require_order(
        desktop_css,
        "ebook-product-card__pr",
        1,
    )
    require_order(
        desktop_css,
        "ebook-product-card__stores",
        2,
    )
    require_order(
        desktop_css,
        "ebook-product-card__details",
        3,
    )


def test_rollback_evidence() -> None:
    value = verify(
        ROLLBACK,
        "rollback_evidence_digest_sha256",
    )

    article = load(ARTICLE)

    assert value[
        "current_content_html"
    ] == article["content_html"]

    assert value[
        "current_content_html_sha256"
    ] == text_sha(
        article["content_html"]
    )

    assert value[
        "live_comment_status_verified_in_this_phase"
    ] is False


def test_update_payload_fields_and_boundary() -> None:
    value = verify(
        UPDATE_PAYLOAD,
        "update_payload_digest_sha256",
    )

    body = value[
        "wordpress_request_body"
    ]

    assert set(body.keys()) == {
        "content",
        "comment_status",
    }

    assert body[
        "comment_status"
    ] == "closed"

    assert body[
        "content"
    ] == RENDERED_HTML.read_text(
        encoding="utf-8"
    )

    assert "title" not in body
    assert "status" not in body
    assert "categories" not in body
    assert "slug" not in body
    assert "excerpt" not in body

    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "authorization_issued"
    ] is False
    assert value[
        "authorization_consumed"
    ] is False
    assert value[
        "deprecated_result_field_present"
    ] is False


def test_store_urls_preserved() -> None:
    article = load(ARTICLE)
    rendered = RENDERED_HTML.read_text(
        encoding="utf-8"
    )

    assert Counter(
        urls(article["content_html"])
    ) == Counter(
        urls(rendered)
    )

    result = load(RESULT)

    assert result[
        "store_url_multiset_preserved"
    ] is True
    assert result[
        "store_button_html_preserved"
    ] is True
    assert result[
        "amazon_state_preserved"
    ] is True
    assert result[
        "rakuten_kobo_state_preserved"
    ] is True
    assert result[
        "dmm_active_anchor_preserved"
    ] is True
    assert result[
        "new_external_url_added"
    ] is False


def test_output_modes_and_secret_boundary() -> None:
    for path in [
        FAILURE_CHAIN,
        ROLLBACK,
        SCOPED_CSS,
        RENDERED_HTML,
        UPDATE_PAYLOAD,
        RESULT,
    ]:
        assert stat.S_IMODE(
            path.stat().st_mode
        ) == 0o600

    result = load(RESULT)

    assert result[
        "full_rendered_content_output"
    ] is False
    assert result[
        "full_update_payload_output"
    ] is False
    assert result[
        "full_store_url_output"
    ] is False
    assert result[
        "affiliate_identifier_output"
    ] is False


def test_no_external_or_authorization_operation() -> None:
    result = load(RESULT)

    assert result[
        "network_connection_performed"
    ] is False
    assert result[
        "dns_resolution_performed"
    ] is False
    assert result[
        "http_request_performed"
    ] is False
    assert result[
        "wordpress_access_performed"
    ] is False
    assert result[
        "wordpress_write_performed"
    ] is False
    assert result[
        "wordpress_update_performed"
    ] is False
    assert result[
        "wordpress_republish_performed"
    ] is False
    assert result[
        "wordpress_delete_performed"
    ] is False
    assert result[
        "authorization_issued"
    ] is False
    assert result[
        "authorization_consumed"
    ] is False
    assert result[
        "authorization_reused"
    ] is False
    assert result[
        "automatic_retry_performed"
    ] is False
    assert result[
        "automatic_reissue_performed"
    ] is False

    assert result[
        "previous_m22_rerun_performed"
    ] is False

    assert result[
        "previous_m22_fix1_rerun_performed"
    ] is False

    assert (
        "original_m22_rerun_performed"
        not in result
    )

    assert result[
        "execution_allowed"
    ] is False

    assert result[
        "ready_for_rendered_update_payload_human_review"
    ] is True
    assert result[
        "ready_for_wordpress_update_authorization_gate"
    ] is False
    assert result[
        "ready_for_wordpress_update"
    ] is False
    assert result[
        "production_status"
    ] == "NO_GO"
