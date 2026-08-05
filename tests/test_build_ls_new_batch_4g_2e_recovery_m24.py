from __future__ import annotations

import copy
import hashlib
import json
import stat
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DECISION = ROOT / (
    "exchange/decisions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_revision.json"
)
SCOPED_CSS = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.css"
)
RENDERED_HTML = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.html"
)
UPDATE_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_payload_v1.json"
)
DESKTOP_PREVIEW = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_desktop_safe_preview.html"
)
MOBILE_PREVIEW = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_mobile_safe_preview.html"
)
REVIEW_PACKET = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_human_review_packet.json"
)
STORE_MANIFEST = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_store_manifest.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m24_result.json"
)

FORBIDDEN = [
    "http://",
    "https://",
    "af_id=",
    "lurl=",
]

EXPECTED_EVENTS = [
    "main_card",
    "cover_image",
    "action_column",
    "pr_disclosure",
    "store_container",
    "amazon_button",
    "rakuten_kobo_button",
    "dmm_button",
    "short_description",
    "work_details",
    "promotion_notice",
]


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


def classes(attrs) -> set[str]:
    value = dict(attrs).get("class")

    if not isinstance(value, str):
        return set()

    return set(value.split())


class EventParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.inside = False
        self.depth = None
        self.stack = []
        self.root_count = 0
        self.events = []

    def record(self, attrs) -> None:
        tokens = classes(attrs)

        mapping = [
            (
                "tawawa-reference-main-card",
                "main_card",
            ),
            (
                "tawawa-reference-cover",
                "cover_image",
            ),
            (
                "tawawa-reference-actions",
                "action_column",
            ),
            (
                "tawawa-reference-pr",
                "pr_disclosure",
            ),
            (
                "tawawa-reference-stores",
                "store_container",
            ),
            (
                "ls-store-amazon",
                "amazon_button",
            ),
            (
                "ls-store-kobo",
                "rakuten_kobo_button",
            ),
            (
                "ls-store-dmm",
                "dmm_button",
            ),
            (
                "tawawa-reference-description",
                "short_description",
            ),
            (
                "tawawa-reference-details",
                "work_details",
            ),
            (
                "tawawa-reference-notice",
                "promotion_notice",
            ),
        ]

        for css_class, event in mapping:
            if css_class in tokens:
                self.events.append(event)
                break

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        mapping = dict(attrs)

        if mapping.get("id") == (
            "ebook-tawawa-reference-192"
        ):
            self.root_count += 1
            self.inside = True
            self.depth = len(self.stack)

        if self.inside:
            self.record(attrs)

        self.stack.append(tag)

    def handle_startendtag(
        self,
        tag,
        attrs,
    ):
        if self.inside:
            self.record(attrs)

    def handle_endtag(
        self,
        tag,
    ):
        if self.stack:
            self.stack.pop()

        if (
            self.inside
            and self.depth is not None
            and len(self.stack) == self.depth
        ):
            self.inside = False


def test_result_digest_and_status() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
        "REVISION_GENERATED_LOCAL_ONLY_NON_EXECUTABLE_"
        "SAFE_PREVIEWS_READY_NO_WORDPRESS_ACCESS"
    )
    assert value[
        "ready_for_tawawa_reference_layout_human_review"
    ] is True


def test_decision_digest() -> None:
    value = verify(
        DECISION,
        "decision_digest_sha256",
    )

    assert value["decision"] == (
        "ADOPT_TAWAWA_SCREENSHOT_AS_LAYOUT_REFERENCE"
    )
    assert value[
        "generated_layout_human_review_completed"
    ] is False


def test_rendered_dom_order() -> None:
    rendered = RENDERED_HTML.read_text(
        encoding="utf-8"
    )

    parser = EventParser()
    parser.feed(rendered)
    parser.close()

    assert parser.root_count == 1
    assert parser.events == EXPECTED_EVENTS

    assert (
        "PR：このページには"
        "アフィリエイト広告が含まれます。"
        in rendered
    )
    assert (
        "※本ページはプロモーションを含みます。"
        in rendered
    )


def test_tawawa_reference_css() -> None:
    css = SCOPED_CSS.read_text(
        encoding="utf-8"
    )

    assert (
        "grid-template-columns: "
        "minmax(150px, 180px) "
        "minmax(0, 1fr)"
        in css
    )
    assert (
        ".ls-store-amazon"
        in css
    )
    assert (
        ".ls-store-kobo"
        in css
    )
    assert (
        ".ls-store-dmm"
        in css
    )
    assert (
        "@media (max-width: 699px)"
        in css
    )


def test_update_payload_boundary() -> None:
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

    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "authorization_issued"
    ] is False


def test_safe_previews() -> None:
    for path, mode in [
        (
            DESKTOP_PREVIEW,
            "desktop",
        ),
        (
            MOBILE_PREVIEW,
            "mobile",
        ),
    ]:
        value = path.read_text(
            encoding="utf-8"
        )
        lowered = value.lower()

        assert (
            f'data-preview-mode="{mode}"'
            in value
        )
        assert (
            'href="#preview-disabled"'
            in value
        )
        assert (
            "data:image/svg+xml;base64,"
            in value
        )

        for forbidden in FORBIDDEN:
            assert forbidden not in lowered


def test_review_packet_and_manifest() -> None:
    review = verify(
        REVIEW_PACKET,
        "review_packet_digest_sha256",
    )
    manifest = verify(
        STORE_MANIFEST,
        "store_manifest_digest_sha256",
    )

    assert review[
        "human_review_completed"
    ] is False
    assert review[
        "human_review_verdict"
    ] == "NOT_RECORDED"
    assert review[
        "comment_status_target"
    ] == "closed"

    assert manifest[
        "full_store_url_present"
    ] is False
    assert manifest[
        "affiliate_identifier_present"
    ] is False


def test_no_wordpress_or_authorization() -> None:
    value = load(RESULT)

    assert value[
        "network_connection_performed"
    ] is False
    assert value[
        "wordpress_access_performed"
    ] is False
    assert value[
        "wordpress_write_performed"
    ] is False
    assert value[
        "wordpress_update_performed"
    ] is False
    assert value[
        "authorization_issued"
    ] is False
    assert value[
        "authorization_consumed"
    ] is False
    assert value[
        "authorization_reused"
    ] is False
    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"


def test_output_modes() -> None:
    for path in [
        DECISION,
        STORE_MANIFEST,
        SCOPED_CSS,
        RENDERED_HTML,
        UPDATE_PAYLOAD,
        DESKTOP_PREVIEW,
        MOBILE_PREVIEW,
        REVIEW_PACKET,
        RESULT,
    ]:
        assert stat.S_IMODE(
            path.stat().st_mode
        ) == 0o600
