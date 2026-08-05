#!/usr/bin/env python3

from __future__ import annotations

import base64
import copy
import hashlib
import html
import json
import os
import re
import socket
import stat
import sys
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def block_network(
    *args: Any,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "NETWORK_OPERATION_BLOCKED_BY_M24"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_"
    "layout_revision_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m24_approval.json"
)

SOURCE_ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
SOURCE_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)

M22_ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)
M22_RENDERED = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_rendered_fix2.html"
)
M22_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_rendered_update_payload_fix2.json"
)
M22_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m22_fix2_result.json"
)

M23_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m23_result.json"
)
M23_REVIEW_PACKET = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_human_review_preparation.json"
)

DECISION = ROOT / (
    "exchange/decisions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_revision.json"
)
STORE_MANIFEST = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_store_manifest.json"
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

RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m24_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m24_"
    "tawawa_reference_layout_revision_report.md"
)
CHECKLIST = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m24_"
    "tawawa_reference_layout_review_checklist.md"
)

EXPECTED_ARTICLE_SHA = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
EXPECTED_SOURCE_PAYLOAD_SHA = (
    "30a70be4110e863a85e2896f69f5b3e5"
    "1d814a6fd82d5489f899d8a244166d8f"
)
EXPECTED_SOURCE_PAYLOAD_DIGEST = (
    "2ab27b59305dbae98f997ca3a4604002"
    "98152f173ef605b534df922c187411c6"
)
EXPECTED_M22_RESULT_DIGEST = (
    "4e0f6e33cef8ad7ceaea7ce0cd453b3a"
    "8bbeb1c9ba0fade71b499b6fea794a5c"
)
EXPECTED_M22_RENDERED_SHA = (
    "86ebae8e7f0c550ed6ee4726164a6542"
    "69e9f2c6c64ac268945dac9714d31d30"
)
EXPECTED_M22_PAYLOAD_DIGEST = (
    "864e33958393fefcf1b2c10ec7e3d85b"
    "f42648393f681386a88f19048585e487"
)
EXPECTED_M22_ROLLBACK_DIGEST = (
    "60ac4fe5182e412014bcbd291ca52af1"
    "e516e7061722e608b39a34c284dbfcf5"
)
EXPECTED_M23_RESULT_DIGEST = (
    "0a5592abc57008922d9a47512f213a6a"
    "88f821d11e255d881a91e9ea557edb9e"
)
EXPECTED_M23_REVIEW_DIGEST = (
    "0cfc80e7df031b7eb1005f14c6527881"
    "da88828f246bf3669820fe0ee49f89ff"
)

EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
)
EXPECTED_DOM_EVENTS = [
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

PR_TEXT = (
    "PR：このページには"
    "アフィリエイト広告が含まれます。"
)
NOTICE_TEXT = (
    "※本ページはプロモーションを含みます。"
    "価格・配信状況は各ストアで確認してください。"
)

FORBIDDEN_SAFE_PREVIEW = [
    "http://",
    "https://",
    "af_id=",
    "lurl=",
]

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    code: str,
) -> None:
    if not condition:
        raise ValidationError(code)


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def canonical_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def bytes_sha(
    value: bytes,
) -> str:
    return hashlib.sha256(value).hexdigest()


def text_sha(
    value: str,
) -> str:
    return bytes_sha(
        value.encode("utf-8")
    )


def file_sha(
    path: Path,
) -> str:
    return bytes_sha(
        path.read_bytes()
    )


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.exists() and path.is_file(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )
    require(
        not path.is_symlink(),
        f"JSON_SYMLINK_REJECTED:{path.name}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise ValidationError(
            f"JSON_PARSE_FAILED:{path.name}"
        ) from None

    require(
        isinstance(value, dict),
        f"JSON_ROOT_NOT_OBJECT:{path.name}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    field: str,
    expected: str | None = None,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        canonical_digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"DIGEST_EXPECTED_MISMATCH:{field}",
        )

    return stored


def add_digest(
    value: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = canonical_digest(value)
    return result


def write_bytes(
    path: Path,
    value: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(fd, "wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def write_text(
    path: Path,
    value: str,
) -> None:
    write_bytes(
        path,
        value.encode("utf-8"),
    )


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )


def extract_one(
    pattern: str,
    source: str,
    code: str,
    group: int = 0,
) -> str:
    matches = list(
        re.finditer(
            pattern,
            source,
            flags=re.DOTALL | re.IGNORECASE,
        )
    )

    require(
        len(matches) == 1,
        f"{code}_COUNT_{len(matches)}",
    )

    return matches[0].group(group)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.parts: list[str] = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        self.parts.append(data)


def text_content(
    fragment: str,
) -> str:
    parser = TextExtractor()
    parser.feed(fragment)
    parser.close()

    return " ".join(
        "".join(parser.parts).split()
    )


def class_tokens(
    attrs: dict[str, str | None],
) -> set[str]:
    value = attrs.get("class")

    if not isinstance(value, str):
        return set()

    return {
        token
        for token in value.split()
        if token
    }


class AttributeScanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.elements: list[
            tuple[str, dict[str, str | None]]
        ] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        self.elements.append(
            (
                tag.casefold(),
                {
                    key.casefold(): value
                    for key, value in attrs
                },
            )
        )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        self.handle_starttag(tag, attrs)


def scan_elements(
    fragment: str,
) -> list[
    tuple[str, dict[str, str | None]]
]:
    parser = AttributeScanner()
    parser.feed(fragment)
    parser.close()
    return parser.elements


def collect_urls(
    fragment: str,
) -> list[str]:
    values: list[str] = []

    for _, attrs in scan_elements(fragment):
        for key in ("href", "src"):
            value = attrs.get(key)

            if isinstance(value, str):
                values.append(value)

    return values


def find_store_element(
    fragment: str,
    required_class: str,
) -> tuple[
    str,
    dict[str, str | None],
]:
    matches = [
        (tag, attrs)
        for tag, attrs in scan_elements(fragment)
        if required_class in class_tokens(attrs)
    ]

    require(
        len(matches) == 1,
        (
            f"STORE_ELEMENT_{required_class}_"
            f"COUNT_{len(matches)}"
        ),
    )

    return matches[0]


def validate_https_url(
    value: str,
    *,
    required_host: str | None = None,
) -> None:
    parsed = urlsplit(value)

    require(
        parsed.scheme == "https",
        "URL_NOT_HTTPS",
    )
    require(
        parsed.hostname is not None,
        "URL_HOST_MISSING",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "URL_USERINFO_REJECTED",
    )

    if required_host is not None:
        require(
            parsed.hostname == required_host,
            "URL_HOST_MISMATCH",
        )


class LayoutEventParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.inside_root = False
        self.root_depth: int | None = None
        self.stack: list[str] = []
        self.root_count = 0
        self.events: list[str] = []

    def record(
        self,
        attrs: dict[str, str | None],
    ) -> None:
        classes = class_tokens(attrs)

        mappings = [
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

        for css_class, event in mappings:
            if css_class in classes:
                self.events.append(event)
                break

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        mapping = {
            key.casefold(): value
            for key, value in attrs
        }

        if mapping.get("id") == (
            "ebook-tawawa-reference-192"
        ):
            self.root_count += 1
            self.inside_root = True
            self.root_depth = len(self.stack)

        if self.inside_root:
            self.record(mapping)

        self.stack.append(tag.casefold())

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        mapping = {
            key.casefold(): value
            for key, value in attrs
        }

        if self.inside_root:
            self.record(mapping)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if self.stack:
            self.stack.pop()

        if (
            self.inside_root
            and self.root_depth is not None
            and len(self.stack) == self.root_depth
        ):
            self.inside_root = False


def parse_layout_events(
    value: str,
) -> tuple[int, list[str]]:
    parser = LayoutEventParser()
    parser.feed(value)
    parser.close()

    return parser.root_count, parser.events


def placeholder_data_uri() -> str:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="860" viewBox="0 0 600 860">
<rect width="600" height="860" fill="#f2f2f2"/>
<rect x="20" y="20" width="560" height="820" rx="18" fill="#ffffff" stroke="#c8c8c8" stroke-width="4"/>
<text x="300" y="400" text-anchor="middle" font-family="sans-serif" font-size="36" fill="#333333">書影プレビュー</text>
<text x="300" y="455" text-anchor="middle" font-family="sans-serif" font-size="22" fill="#666666">外部画像通信なし</text>
</svg>"""

    encoded = base64.b64encode(
        svg.encode("utf-8")
    ).decode("ascii")

    return (
        "data:image/svg+xml;base64,"
        + encoded
    )


class SafePreviewSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.parts: list[str] = []
        self.skip_tag: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        tag = tag.casefold()

        if tag in {"style", "script"}:
            self.skip_tag = tag
            return

        if self.skip_tag is not None:
            return

        safe_attrs: list[
            tuple[str, str | None]
        ] = []

        original_src = None

        for key, value in attrs:
            lowered = key.casefold()

            if lowered == "href":
                continue

            if lowered in {
                "src",
                "srcset",
                "sizes",
                "target",
            }:
                if lowered == "src":
                    original_src = value
                continue

            if (
                isinstance(value, str)
                and any(
                    forbidden in value.casefold()
                    for forbidden in [
                        "http://",
                        "https://",
                        "af_id=",
                        "lurl=",
                    ]
                )
            ):
                safe_attrs.append(
                    (lowered, "redacted")
                )
            else:
                safe_attrs.append(
                    (lowered, value)
                )

        if tag == "a":
            safe_attrs.append(
                ("href", "#preview-disabled")
            )
            safe_attrs.append(
                ("aria-disabled", "true")
            )
            safe_attrs.append(
                ("tabindex", "-1")
            )

        if tag == "img":
            safe_attrs.append(
                ("src", placeholder_data_uri())
            )
            safe_attrs.append(
                (
                    "data-preview-asset-state",
                    "embedded-placeholder",
                )
            )

            if isinstance(original_src, str):
                safe_attrs.append(
                    (
                        "data-preview-asset-fingerprint",
                        text_sha(original_src),
                    )
                )

        rendered_attrs = ""

        for key, value in safe_attrs:
            rendered_attrs += (
                " "
                + html.escape(
                    key,
                    quote=True,
                )
            )

            if value is not None:
                rendered_attrs += (
                    '="'
                    + html.escape(
                        value,
                        quote=True,
                    )
                    + '"'
                )

        self.parts.append(
            "<"
            + tag
            + rendered_attrs
            + ">"
        )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        tag = tag.casefold()

        if self.skip_tag == tag:
            self.skip_tag = None
            return

        if self.skip_tag is not None:
            return

        if tag not in VOID_TAGS:
            self.parts.append(
                "</"
                + tag
                + ">"
            )

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self.skip_tag is None:
            self.parts.append(
                html.escape(data)
            )

    def get_html(self) -> str:
        return "".join(self.parts)


def sanitize_for_preview(
    rendered_html: str,
) -> str:
    without_style = re.sub(
        (
            r"\A\s*<style\b[^>]*>"
            r".*?</style>\s*"
        ),
        "",
        rendered_html,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )

    parser = SafePreviewSanitizer()
    parser.feed(without_style)
    parser.close()

    return parser.get_html()


def assert_safe_preview(
    value: str,
) -> None:
    lowered = value.casefold()

    for forbidden in FORBIDDEN_SAFE_PREVIEW:
        require(
            forbidden.casefold()
            not in lowered,
            (
                "FORBIDDEN_SAFE_PREVIEW_TEXT:"
                + forbidden
            ),
        )

    require(
        "data:image/svg+xml;base64,"
        in value,
        "SAFE_PREVIEW_PLACEHOLDER_MISSING",
    )
    require(
        'href="#preview-disabled"'
        in value,
        "SAFE_PREVIEW_LINK_DISABLE_MARKER_MISSING",
    )


def build_css() -> str:
    return """#ebook-tawawa-reference-192,
#ebook-tawawa-reference-192 * {
  box-sizing: border-box;
}

#ebook-tawawa-reference-192 {
  display: grid;
  gap: 1.35rem;
  width: 100%;
  max-width: 860px;
  margin-inline: auto;
}

#ebook-tawawa-reference-192 .tawawa-reference-main-card,
#ebook-tawawa-reference-192 .tawawa-reference-description,
#ebook-tawawa-reference-192 .tawawa-reference-details,
#ebook-tawawa-reference-192 .tawawa-reference-notice {
  width: 100%;
  margin: 0;
  border: 1px solid #dedede;
  border-radius: 0.9rem;
  background: #ffffff;
}

#ebook-tawawa-reference-192 .tawawa-reference-main-card {
  display: grid;
  grid-template-columns: minmax(150px, 180px) minmax(0, 1fr);
  gap: 1.5rem;
  align-items: center;
  padding: 1.35rem;
}

#ebook-tawawa-reference-192 .tawawa-reference-cover {
  min-width: 0;
}

#ebook-tawawa-reference-192 .tawawa-reference-cover figure {
  margin: 0;
}

#ebook-tawawa-reference-192 .tawawa-reference-cover img {
  display: block;
  width: 100%;
  max-width: 180px;
  height: auto;
  margin-inline: auto;
  border-radius: 0.25rem;
}

#ebook-tawawa-reference-192 .tawawa-reference-actions {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.9rem;
}

#ebook-tawawa-reference-192 .tawawa-reference-pr {
  margin: 0;
  padding: 0.58rem 0.72rem;
  border-left: 4px solid #ff9f1a;
  background: #fff8ec;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.55;
}

#ebook-tawawa-reference-192 .tawawa-reference-stores {
  display: grid;
  gap: 0.75rem;
}

#ebook-tawawa-reference-192 .tawawa-reference-stores > * {
  display: flex;
  width: 100%;
  min-height: 3.15rem;
  margin: 0;
  padding: 0.72rem 1rem;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 999px;
  box-shadow: 0 8px 16px rgb(0 0 0 / 8%);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.4;
  text-align: center;
  text-decoration: none;
}

#ebook-tawawa-reference-192 .ls-store-amazon {
  background: linear-gradient(90deg, #ff9800, #ffb544);
  color: #111111;
}

#ebook-tawawa-reference-192 .ls-store-kobo {
  background: linear-gradient(90deg, #d90000, #e93636);
  color: #ffffff;
}

#ebook-tawawa-reference-192 .ls-store-dmm {
  background: linear-gradient(90deg, #2468e8, #4b86ef);
  color: #ffffff;
}

#ebook-tawawa-reference-192 .ls-store-disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

#ebook-tawawa-reference-192 .tawawa-reference-description {
  padding: 1.15rem 1.25rem;
  border-color: #efc88d;
  background: #fffaf1;
}

#ebook-tawawa-reference-192 .tawawa-reference-description p {
  margin: 0;
  line-height: 1.75;
}

#ebook-tawawa-reference-192 .tawawa-reference-details {
  padding: 1.15rem 1.25rem;
  background: #fbfbfb;
}

#ebook-tawawa-reference-192 .tawawa-reference-details ul {
  display: grid;
  gap: 0.65rem;
  margin: 0;
  padding-left: 1.3rem;
}

#ebook-tawawa-reference-192 .tawawa-reference-details li {
  margin: 0;
  line-height: 1.65;
  overflow-wrap: break-word;
  word-break: normal;
}

#ebook-tawawa-reference-192 .tawawa-reference-details strong {
  display: inline;
  white-space: nowrap;
}

#ebook-tawawa-reference-192 .tawawa-reference-notice {
  padding: 0.9rem 1rem;
  border: 0;
  border-left: 5px solid #c9c9c9;
  border-radius: 0.45rem;
  background: #f5f5f5;
  font-size: 0.9rem;
  line-height: 1.65;
}

@media (max-width: 699px) {
  #ebook-tawawa-reference-192 {
    gap: 1rem;
  }

  #ebook-tawawa-reference-192 .tawawa-reference-main-card {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.1rem;
    padding: 1rem;
  }

  #ebook-tawawa-reference-192 .tawawa-reference-cover img {
    width: min(68vw, 240px);
    max-width: 100%;
  }

  #ebook-tawawa-reference-192 .tawawa-reference-actions {
    gap: 0.75rem;
  }

  #ebook-tawawa-reference-192 .tawawa-reference-stores > * {
    min-height: 3rem;
    font-size: 0.98rem;
  }

  #ebook-tawawa-reference-192 .tawawa-reference-description,
  #ebook-tawawa-reference-192 .tawawa-reference-details {
    padding: 1rem;
  }
}
"""


def preview_shell(
    *,
    mode: str,
    title: str,
    css: str,
    safe_body: str,
) -> str:
    require(
        mode in {"desktop", "mobile"},
        "PREVIEW_MODE_INVALID",
    )

    if mode == "desktop":
        width = "1180px"
        forced_css = """
.preview-content {
  width: min(100%, 900px);
}

#ebook-tawawa-reference-192 .tawawa-reference-main-card {
  grid-template-columns: minmax(150px, 180px) minmax(0, 1fr) !important;
}
"""
        label = "デスクトップ"
    else:
        width = "430px"
        forced_css = """
.preview-content {
  width: min(100%, 390px);
}

#ebook-tawawa-reference-192 .tawawa-reference-main-card {
  grid-template-columns: minmax(0, 1fr) !important;
}

#ebook-tawawa-reference-192 .tawawa-reference-cover img {
  width: min(68vw, 240px) !important;
}
"""
        label = "スマートフォン"

    shell_css = f"""
body {{
  margin: 0;
  padding: 1.25rem;
  background: #f2f3f5;
  color: #202124;
  font-family:
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}}

.preview-page {{
  width: min(100%, {width});
  margin-inline: auto;
  padding: 2.4rem;
  border-radius: 0.8rem;
  background: #ffffff;
}}

.preview-theme-title {{
  width: min(100%, 900px);
  margin: 0 auto 1.4rem;
  padding: 0.9rem 1rem;
  border-left: 6px solid #ff9f1a;
  border-radius: 0.4rem;
  background: #fffaf3;
  font-size: 1.5rem;
}}

.preview-theme-note {{
  width: min(100%, 900px);
  margin: -0.65rem auto 1.3rem;
  color: #666666;
  font-size: 0.82rem;
  text-align: right;
}}

.preview-safety {{
  width: min(100%, 900px);
  margin: 0 auto 1.25rem;
  padding: 0.7rem 0.85rem;
  border-radius: 0.4rem;
  background: #eef5ff;
  font-size: 0.82rem;
}}

.preview-content {{
  margin-inline: auto;
}}

#ebook-tawawa-reference-192 a {{
  pointer-events: none !important;
  cursor: not-allowed !important;
}}

{forced_css}
"""

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M24 {html.escape(label)}安全プレビュー</title>
<style>
{css}
{shell_css}
</style>
</head>
<body data-preview-mode="{html.escape(mode)}">
<div class="preview-page">
  <h1 class="preview-theme-title">{html.escape(title)}</h1>
  <p class="preview-theme-note">タイトル領域はWordPressテーマ側・更新対象外</p>
  <p class="preview-safety">
    安全プレビュー：外部リンクは無効、外部画像はプレースホルダーです。
  </p>
  <main class="preview-content">
    {safe_body}
  </main>
</div>
</body>
</html>
"""


def main() -> int:
    source_paths = {
        "source_article": SOURCE_ARTICLE,
        "source_payload": SOURCE_PAYLOAD,
        "m22_rollback": M22_ROLLBACK,
        "m22_rendered": M22_RENDERED,
        "m22_payload": M22_PAYLOAD,
        "m22_result": M22_RESULT,
        "m23_result": M23_RESULT,
        "m23_review_packet": M23_REVIEW_PACKET,
    }

    try:
        for output in [
            DECISION,
            STORE_MANIFEST,
            SCOPED_CSS,
            RENDERED_HTML,
            UPDATE_PAYLOAD,
            DESKTOP_PREVIEW,
            MOBILE_PREVIEW,
            REVIEW_PACKET,
            RESULT,
            REPORT,
            CHECKLIST,
        ]:
            require(
                not output.exists(),
                f"M24_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M24",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_TAWAWA_REFERENCE_"
                "LAYOUT_REVISION_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_APPROVAL_FALSE",
        )
        require(
            approval["wordpress_update_approved"]
            is False,
            "WORDPRESS_UPDATE_APPROVED",
        )
        require(
            approval[
                "authorization_issue_approved"
            ] is False,
            "AUTHORIZATION_ISSUE_APPROVED",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        for name, path in source_paths.items():
            binding = approval[
                "source_bindings"
            ][name]

            require(
                binding["path"]
                == str(path.relative_to(ROOT)),
                f"APPROVAL_SOURCE_PATH_MISMATCH:{name}",
            )
            require(
                binding["file_sha256"]
                == source_hashes[name],
                f"APPROVAL_SOURCE_SHA_MISMATCH:{name}",
            )

        require(
            source_hashes["source_article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["source_payload"]
            == EXPECTED_SOURCE_PAYLOAD_SHA,
            "SOURCE_PAYLOAD_FILE_SHA_MISMATCH",
        )

        source_article = load_json(
            SOURCE_ARTICLE
        )
        source_payload = load_json(
            SOURCE_PAYLOAD
        )
        rollback = load_json(
            M22_ROLLBACK
        )
        m22_payload = load_json(
            M22_PAYLOAD
        )
        m22_result = load_json(
            M22_RESULT
        )
        m23_result = load_json(
            M23_RESULT
        )
        m23_review = load_json(
            M23_REVIEW_PACKET
        )

        verify_digest(
            source_payload,
            "payload_digest_sha256",
            EXPECTED_SOURCE_PAYLOAD_DIGEST,
        )
        verify_digest(
            rollback,
            "rollback_evidence_digest_sha256",
            EXPECTED_M22_ROLLBACK_DIGEST,
        )
        verify_digest(
            m22_payload,
            "update_payload_digest_sha256",
            EXPECTED_M22_PAYLOAD_DIGEST,
        )
        verify_digest(
            m22_result,
            "result_digest_sha256",
            EXPECTED_M22_RESULT_DIGEST,
        )
        verify_digest(
            m23_result,
            "result_digest_sha256",
            EXPECTED_M23_RESULT_DIGEST,
        )
        verify_digest(
            m23_review,
            "review_preparation_digest_sha256",
            EXPECTED_M23_REVIEW_DIGEST,
        )

        source_rendered = M22_RENDERED.read_text(
            encoding="utf-8"
        )

        require(
            text_sha(source_rendered)
            == EXPECTED_M22_RENDERED_SHA,
            "M22_RENDERED_SHA_MISMATCH",
        )
        require(
            source_payload["title"]
            == EXPECTED_TITLE,
            "SOURCE_TITLE_MISMATCH",
        )
        require(
            source_article["article_title"]
            == EXPECTED_TITLE,
            "ARTICLE_TITLE_MISMATCH",
        )
        require(
            m23_result[
                "ready_for_human_visual_review"
            ] is True,
            "M23_VISUAL_REVIEW_NOT_READY",
        )
        require(
            m23_result[
                "wordpress_access_performed"
            ] is False,
            "M23_WORDPRESS_ACCESS_TRUE",
        )

        cover_html = extract_one(
            (
                r'<figure class="ls-book-cover">'
                r'.*?</figure>'
            ),
            source_rendered,
            "COVER_HTML",
        )

        store_inner = extract_one(
            (
                r'<div class="ebook-product-card__stores '
                r'ls-store-buttons"[^>]*>(.*?)</div>'
            ),
            source_rendered,
            "STORE_CONTAINER",
            1,
        )

        detail_matches = list(
            re.finditer(
                (
                    r'<div class="ebook-product-card__detail-row">'
                    r'\s*<dt>(.*?)</dt>'
                    r'\s*<dd>(.*?)</dd>'
                    r'\s*</div>'
                ),
                source_rendered,
                flags=re.DOTALL | re.IGNORECASE,
            )
        )

        require(
            len(detail_matches) == 5,
            (
                "DETAIL_ROW_COUNT_"
                + str(len(detail_matches))
            ),
        )

        details: list[
            tuple[str, str]
        ] = []

        for match in detail_matches:
            label = text_content(
                match.group(1)
            ).strip()
            value = text_content(
                match.group(2)
            ).strip()

            require(
                label != "" and value != "",
                "DETAIL_ROW_EMPTY",
            )

            details.append(
                (label, value)
            )

        amazon_tag, amazon_attrs = (
            find_store_element(
                store_inner,
                "ls-store-amazon",
            )
        )
        kobo_tag, kobo_attrs = (
            find_store_element(
                store_inner,
                "ls-store-kobo",
            )
        )
        dmm_tag, dmm_attrs = (
            find_store_element(
                store_inner,
                "ls-store-dmm",
            )
        )

        require(
            amazon_tag == "span",
            "AMAZON_STATE_CHANGED",
        )
        require(
            "ls-store-disabled"
            in class_tokens(amazon_attrs),
            "AMAZON_DISABLED_CLASS_MISSING",
        )
        require(
            kobo_tag == "span",
            "KOBO_STATE_CHANGED",
        )
        require(
            "ls-store-disabled"
            in class_tokens(kobo_attrs),
            "KOBO_DISABLED_CLASS_MISSING",
        )
        require(
            dmm_tag == "a",
            "DMM_ACTIVE_ANCHOR_MISSING",
        )

        dmm_href = dmm_attrs.get("href")

        require(
            isinstance(dmm_href, str),
            "DMM_HREF_MISSING",
        )

        validate_https_url(
            dmm_href,
            required_host="al.dmm.com",
        )

        source_urls = collect_urls(
            source_rendered
        )

        for value in source_urls:
            validate_https_url(value)

        display_title = (
            source_payload["title"]
            .replace("｜配信開始", "")
            .strip()
        )

        require(
            display_title != "",
            "DISPLAY_TITLE_EMPTY",
        )

        description_html = (
            "<p><strong>"
            + html.escape(display_title)
            + "</strong>が配信開始です。</p>"
        )

        detail_items = "\n".join(
            (
                "    <li><strong>"
                + html.escape(label)
                + "：</strong>"
                + html.escape(value)
                + "</li>"
            )
            for label, value in details
        )

        css = build_css()

        rendered_html = (
            '<style id="ebook-tawawa-reference-192-css">\n'
            + css
            + "</style>\n"
            + (
                '<section id="ebook-tawawa-reference-192" '
                'class="tawawa-reference-layout" '
                'data-layout-version="TAWAWA-REFERENCE-V1" '
                'data-wordpress-post-id="192">\n'
            )
            + (
                '  <div class="tawawa-reference-main-card">\n'
            )
            + (
                '    <div class="tawawa-reference-cover">\n'
            )
            + cover_html
            + "\n    </div>\n"
            + (
                '    <div class="tawawa-reference-actions">\n'
            )
            + (
                '      <p class="tawawa-reference-pr" role="note">'
            )
            + html.escape(PR_TEXT)
            + "</p>\n"
            + (
                '      <div class="tawawa-reference-stores '
                'ls-store-buttons" aria-label="電子書籍ストア">'
            )
            + store_inner
            + "</div>\n"
            + "    </div>\n"
            + "  </div>\n"
            + (
                '  <div class="tawawa-reference-description">\n'
            )
            + "    "
            + description_html
            + "\n"
            + "  </div>\n"
            + (
                '  <div class="tawawa-reference-details">\n'
            )
            + "  <ul>\n"
            + detail_items
            + "\n  </ul>\n"
            + "  </div>\n"
            + (
                '  <div class="tawawa-reference-notice" '
                'role="note">'
            )
            + html.escape(NOTICE_TEXT)
            + "</div>\n"
            + "</section>\n"
        )

        root_count, events = (
            parse_layout_events(
                rendered_html
            )
        )

        require(
            root_count == 1,
            f"ROOT_COUNT_{root_count}",
        )
        require(
            events == EXPECTED_DOM_EVENTS,
            (
                "DOM_EVENT_ORDER_MISMATCH:"
                + ",".join(events)
            ),
        )
        require(
            rendered_html.count(PR_TEXT)
            == 1,
            "PR_TEXT_COUNT_MISMATCH",
        )
        require(
            rendered_html.count(NOTICE_TEXT)
            == 1,
            "NOTICE_TEXT_COUNT_MISMATCH",
        )
        require(
            Counter(
                collect_urls(rendered_html)
            )
            == Counter(source_urls),
            "SOURCE_URL_MULTISET_CHANGED",
        )
        require(
            cover_html in rendered_html,
            "COVER_HTML_NOT_PRESERVED",
        )
        require(
            store_inner in rendered_html,
            "STORE_HTML_NOT_PRESERVED",
        )

        rendered_sha = text_sha(
            rendered_html
        )
        css_sha = text_sha(css)

        write_text(
            SCOPED_CSS,
            css,
        )
        write_text(
            RENDERED_HTML,
            rendered_html,
        )

        request_body = {
            "content": rendered_html,
            "comment_status": "closed",
        }

        require(
            set(request_body.keys())
            == {
                "content",
                "comment_status",
            },
            "REQUEST_FIELD_SET_MISMATCH",
        )

        update_payload_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M24"
            ),
            "document_role": (
                "NON_EXECUTABLE_WORDPRESS_TAWAWA_"
                "REFERENCE_LAYOUT_UPDATE_PAYLOAD"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "expected_current_status": "publish",
            "operation": (
                "NON_EXECUTABLE_WORDPRESS_POST_UPDATE_DRAFT"
            ),
            "allowed_request_fields": [
                "content",
                "comment_status",
            ],
            "wordpress_request_body": request_body,
            "rendered_content_html_sha256": (
                rendered_sha
            ),
            "scoped_css_sha256": css_sha,
            "rollback_evidence_path": str(
                M22_ROLLBACK.relative_to(ROOT)
            ),
            "rollback_evidence_digest_sha256": (
                EXPECTED_M22_ROLLBACK_DIGEST
            ),
            "reference_layout": (
                "TAWAWA_SCREENSHOT_REFERENCE_V1"
            ),
            "title_field_in_request": False,
            "status_field_in_request": False,
            "categories_field_in_request": False,
            "slug_field_in_request": False,
            "excerpt_field_in_request": False,
            "execution_allowed": False,
            "authorization_issued": False,
            "authorization_consumed": False,
            "authorization_reused": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_update_performed": False,
            "production_status": "NO_GO",
            "created_at_utc": now()
        }

        update_payload = add_digest(
            update_payload_without_digest,
            "update_payload_digest_sha256",
        )

        write_json(
            UPDATE_PAYLOAD,
            update_payload,
        )

        store_manifest_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M24"
            ),
            "document_role": (
                "TAWAWA_REFERENCE_LAYOUT_SAFE_STORE_MANIFEST"
            ),
            "wordpress_post_id": 192,
            "stores": [
                {
                    "store": "amazon",
                    "source_state": (
                        "disabled_no_source_link"
                    ),
                    "safe_preview_state": "disabled",
                    "host": None,
                    "url_fingerprint_sha256": None
                },
                {
                    "store": "rakuten_kobo",
                    "source_state": (
                        "disabled_no_source_link"
                    ),
                    "safe_preview_state": "disabled",
                    "host": None,
                    "url_fingerprint_sha256": None
                },
                {
                    "store": "dmm",
                    "source_state": "active_source_link",
                    "safe_preview_state": "disabled",
                    "host": "al.dmm.com",
                    "url_fingerprint_sha256": (
                        text_sha(dmm_href)
                    )
                }
            ],
            "full_store_url_present": False,
            "affiliate_identifier_present": False,
            "created_at_utc": now()
        }

        store_manifest = add_digest(
            store_manifest_without_digest,
            "store_manifest_digest_sha256",
        )

        write_json(
            STORE_MANIFEST,
            store_manifest,
        )

        safe_body = sanitize_for_preview(
            rendered_html
        )

        desktop_preview = preview_shell(
            mode="desktop",
            title=source_payload["title"],
            css=css,
            safe_body=safe_body,
        )
        mobile_preview = preview_shell(
            mode="mobile",
            title=source_payload["title"],
            css=css,
            safe_body=safe_body,
        )

        assert_safe_preview(
            desktop_preview
        )
        assert_safe_preview(
            mobile_preview
        )

        write_text(
            DESKTOP_PREVIEW,
            desktop_preview,
        )
        write_text(
            MOBILE_PREVIEW,
            mobile_preview,
        )

        desktop_sha = text_sha(
            desktop_preview
        )
        mobile_sha = text_sha(
            mobile_preview
        )

        decision_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M24"
            ),
            "document_role": (
                "TAWAWA_REFERENCE_LAYOUT_REVISION_DECISION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "decision": (
                "ADOPT_TAWAWA_SCREENSHOT_AS_LAYOUT_REFERENCE"
            ),
            "previous_m23_visual_review_verdict": (
                "TARGET_LAYOUT_MISMATCH_CHANGES_REQUIRED"
            ),
            "desktop_main_card": {
                "left": "cover_image",
                "right_order": [
                    "pr_disclosure",
                    "amazon_button",
                    "rakuten_kobo_button",
                    "dmm_button"
                ]
            },
            "lower_section_order": [
                "short_distribution_description",
                "work_detail_list",
                "promotion_notice"
            ],
            "mobile_order": [
                "cover_image",
                "pr_disclosure",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
                "short_distribution_description",
                "work_detail_list",
                "promotion_notice"
            ],
            "comment_status_target": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status"
            ],
            "rendered_content_sha256": (
                rendered_sha
            ),
            "scoped_css_sha256": css_sha,
            "generated_layout_human_review_completed": False,
            "generated_layout_human_review_verdict": (
                "NOT_RECORDED"
            ),
            "wordpress_access_performed": False,
            "wordpress_update_performed": False,
            "authorization_issued": False,
            "production_status": "NO_GO",
            "created_at_utc": now()
        }

        decision = add_digest(
            decision_without_digest,
            "decision_digest_sha256",
        )

        write_json(
            DECISION,
            decision,
        )

        review_packet_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M24"
            ),
            "document_role": (
                "TAWAWA_REFERENCE_LAYOUT_HUMAN_REVIEW_PACKET"
            ),
            "wordpress_post_id": 192,
            "human_review_status": (
                "AWAITING_VISUAL_REVIEW"
            ),
            "human_review_completed": False,
            "human_review_verdict": (
                "NOT_RECORDED"
            ),
            "desktop_preview_path": str(
                DESKTOP_PREVIEW.relative_to(ROOT)
            ),
            "desktop_preview_sha256": (
                desktop_sha
            ),
            "mobile_preview_path": str(
                MOBILE_PREVIEW.relative_to(ROOT)
            ),
            "mobile_preview_sha256": (
                mobile_sha
            ),
            "review_targets": [
                "DESKTOP_COVER_LEFT_BUTTONS_RIGHT",
                "PR_BEFORE_FIRST_STORE_BUTTON",
                "BUTTONS_VERTICAL_EQUAL_WIDTH",
                "DESCRIPTION_SEPARATE_LOWER_BOX",
                "DETAILS_SEPARATE_LOWER_BOX",
                "NOTICE_SEPARATE_LOWER_BOX",
                "MOBILE_SINGLE_COLUMN_NO_HORIZONTAL_SCROLL",
                "EXCESS_WHITESPACE_NOT_PRESENT",
                "TEXT_WRAPPING_NATURAL",
                "COMMENT_STATUS_CLOSED",
                "UPDATE_FIELDS_CONTENT_AND_COMMENT_STATUS_ONLY"
            ],
            "comment_status_target": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status"
            ],
            "safe_preview_external_links_active": False,
            "safe_preview_external_assets_requested": False,
            "ready_for_tawawa_reference_layout_human_review": True,
            "ready_for_wordpress_update_authorization_gate": False,
            "production_status": "NO_GO",
            "created_at_utc": now()
        }

        review_packet = add_digest(
            review_packet_without_digest,
            "review_packet_digest_sha256",
        )

        write_json(
            REVIEW_PACKET,
            review_packet,
        )

        write_text(
            CHECKLIST,
            """# M24 たわわ参照レイアウト確認

## デスクトップ

- [ ] 書影がメインカード左側
- [ ] PR表記が右側の先頭
- [ ] Amazon、楽天Kobo、DMMが同じ幅で縦並び
- [ ] メインカード内に作品詳細が入り込んでいない
- [ ] 説明文がメインカード下の独立ボックス
- [ ] 作品詳細がその下の独立ボックス
- [ ] 注意書きが最下段の独立ボックス
- [ ] 余白が過剰でない
- [ ] 文字が細切れに改行されない

## スマートフォン

- [ ] 書影が先頭
- [ ] PR表記がストアボタンより前
- [ ] Amazon、楽天Kobo、DMMの順
- [ ] 説明文、作品詳細、注意書きが下段
- [ ] 横スクロールが発生しない
- [ ] ボタン幅と余白が自然

## 機械確認済み

- [x] `comment_status=closed`
- [x] 更新対象は `content` と `comment_status` のみ
- [x] WordPressアクセスなし
- [x] WordPress更新なし
- [x] 認可発行なし
- [x] 安全プレビュー内の外部リンク無効
- [x] 安全プレビュー内の外部画像通信なし
""",
        )

        for path in [
            DECISION,
            STORE_MANIFEST,
            SCOPED_CSS,
            RENDERED_HTML,
            UPDATE_PAYLOAD,
            DESKTOP_PREVIEW,
            MOBILE_PREVIEW,
            REVIEW_PACKET,
            CHECKLIST,
        ]:
            require(
                stat.S_IMODE(
                    path.stat().st_mode
                ) == 0o600,
                f"OUTPUT_MODE_NOT_0600:{path.name}",
            )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M24"
            ),
            "status": (
                "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
                "REVISION_GENERATED_LOCAL_ONLY_NON_EXECUTABLE_"
                "SAFE_PREVIEWS_READY_NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "TAWAWA_REFERENCE_LAYOUT_GENERATED_"
                "AWAITING_HUMAN_VISUAL_REVIEW"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "reference_layout": (
                "HUMAN_PROVIDED_TAWAWA_SCREENSHOT"
            ),
            "decision_path": str(
                DECISION.relative_to(ROOT)
            ),
            "decision_digest_sha256": (
                decision["decision_digest_sha256"]
            ),
            "rendered_html_path": str(
                RENDERED_HTML.relative_to(ROOT)
            ),
            "rendered_content_sha256": (
                rendered_sha
            ),
            "scoped_css_path": str(
                SCOPED_CSS.relative_to(ROOT)
            ),
            "scoped_css_sha256": css_sha,
            "update_payload_path": str(
                UPDATE_PAYLOAD.relative_to(ROOT)
            ),
            "update_payload_digest_sha256": (
                update_payload[
                    "update_payload_digest_sha256"
                ]
            ),
            "desktop_preview_path": str(
                DESKTOP_PREVIEW.relative_to(ROOT)
            ),
            "desktop_preview_sha256": (
                desktop_sha
            ),
            "mobile_preview_path": str(
                MOBILE_PREVIEW.relative_to(ROOT)
            ),
            "mobile_preview_sha256": (
                mobile_sha
            ),
            "store_manifest_digest_sha256": (
                store_manifest[
                    "store_manifest_digest_sha256"
                ]
            ),
            "review_packet_digest_sha256": (
                review_packet[
                    "review_packet_digest_sha256"
                ]
            ),
            "desktop_cover_left_buttons_right": True,
            "desktop_buttons_vertical_equal_width": True,
            "lower_description_separated": True,
            "lower_details_separated": True,
            "lower_notice_separated": True,
            "mobile_single_column_layout_generated": True,
            "pr_before_first_affiliate_interaction": True,
            "store_url_multiset_preserved": True,
            "store_element_html_preserved": True,
            "amazon_state_preserved": True,
            "rakuten_kobo_state_preserved": True,
            "dmm_active_anchor_preserved": True,
            "new_external_url_added": False,
            "comment_status_target": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status"
            ],
            "human_review_completed": False,
            "human_review_verdict": (
                "NOT_RECORDED"
            ),
            "safe_preview_external_links_active": False,
            "safe_preview_external_assets_requested": False,
            "full_store_url_present_in_safe_previews": False,
            "affiliate_identifier_present_in_safe_previews": False,
            "source_artifacts_modified": False,
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_update_performed": False,
            "wordpress_republish_performed": False,
            "wordpress_delete_performed": False,
            "authorization_issued": False,
            "authorization_consumed": False,
            "authorization_reused": False,
            "automatic_retry_performed": False,
            "automatic_reissue_performed": False,
            "x_post_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "TAWAWA_REFERENCE_LAYOUT_SAFE_PREVIEWS_"
                "AWAITING_HUMAN_REVIEW_NO_WORDPRESS_UPDATE"
            ),
            "ready_for_tawawa_reference_layout_human_review": True,
            "ready_for_wordpress_update_authorization_gate": False,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        result = add_digest(
            result_without_digest,
            "result_digest_sha256",
        )

        write_json(
            RESULT,
            result,
        )

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M24

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Reference layout: `HUMAN_PROVIDED_TAWAWA_SCREENSHOT`
- WordPress post ID: `192`
- Desktop cover left / buttons right: `true`
- Buttons vertical and equal width: `true`
- Description separated below card: `true`
- Details separated below description: `true`
- Notice separated at bottom: `true`
- Mobile single-column layout: `true`
- PR before first affiliate interaction: `true`
- Comment status target: `closed`
- Allowed update fields: `content, comment_status`
- Store URL multiset preserved: `true`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Authorization issued: `false`
- Production status: `NO_GO`
- Ready for human review: `true`
""",
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M24"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_"
                        "LAYOUT_REVISION_NO_WORDPRESS_ACCESS"
                    ),
                    "error_code": str(exc),
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_issued": False,
                    "execution_allowed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
