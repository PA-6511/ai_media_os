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
        "NETWORK_OPERATION_BLOCKED_BY_M23"
    )


socket.socket = block_network
socket.create_connection = block_network
socket.getaddrinfo = block_network
socket.gethostbyname = block_network
socket.gethostbyname_ex = block_network


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_rendered_layout_correction_"
    "human_review_preparation_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m23_approval.json"
)

M22_FAILURE_CHAIN = ROOT / (
    "exchange/failures/new_release/fresh/"
    "new-release-comic-20260703-001."
    "m22_m22_fix1_failure_chain.json"
)
M22_ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)
M22_CSS = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_scoped_fix2.css"
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

STORE_MANIFEST = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_safe_store_manifest.json"
)
DESKTOP_PREVIEW = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_desktop_safe_preview.html"
)
MOBILE_PREVIEW = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_mobile_safe_preview.html"
)
REVIEW_PACKET = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_human_review_preparation.json"
)
CHECKLIST = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m23_"
    "human_review_checklist.md"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m23_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m23_"
    "human_review_preparation_report.md"
)

EXPECTED_FAILURE_CHAIN_DIGEST = (
    "d2fb20c22d98edd7c685681fc8aad69c"
    "8e418c7c9536cfdaeca2a3c10196d598"
)
EXPECTED_ROLLBACK_DIGEST = (
    "60ac4fe5182e412014bcbd291ca52af1"
    "e516e7061722e608b39a34c284dbfcf5"
)
EXPECTED_PAYLOAD_DIGEST = (
    "864e33958393fefcf1b2c10ec7e3d85b"
    "f42648393f681386a88f19048585e487"
)
EXPECTED_RESULT_DIGEST = (
    "4e0f6e33cef8ad7ceaea7ce0cd453b3a"
    "8bbeb1c9ba0fade71b499b6fea794a5c"
)
EXPECTED_CURRENT_CONTENT_SHA = (
    "c5851f15e4eb477038dca512c8990068"
    "736a306cf4fb8c207036a3186119f436"
)
EXPECTED_RENDERED_CONTENT_SHA = (
    "86ebae8e7f0c550ed6ee4726164a6542"
    "69e9f2c6c64ac268945dac9714d31d30"
)
EXPECTED_SCOPED_CSS_SHA = (
    "a77f2bc010432322a754006e97fa4bf2"
    "190fccb881cc2c361edd9e2f4bddec43"
)

EXPECTED_STORES = [
    "amazon",
    "rakuten_kobo",
    "dmm",
]

FORBIDDEN_PREVIEW_TEXT = [
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


def safe_host(
    value: str,
) -> str | None:
    parsed = urlsplit(value)
    return parsed.hostname


def placeholder_data_uri() -> str:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="900" viewBox="0 0 640 900">
<rect width="640" height="900" fill="#f2f2f2"/>
<rect x="24" y="24" width="592" height="852" rx="18" fill="#ffffff" stroke="#b8b8b8" stroke-width="4"/>
<text x="320" y="420" text-anchor="middle" font-family="sans-serif" font-size="38" fill="#333333">書影プレビュー</text>
<text x="320" y="480" text-anchor="middle" font-family="sans-serif" font-size="24" fill="#666666">外部画像通信を無効化しています</text>
</svg>"""

    encoded = base64.b64encode(
        svg.encode("utf-8")
    ).decode("ascii")

    return (
        "data:image/svg+xml;base64,"
        + encoded
    )


class SourceScanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.stores: dict[
            str,
            dict[str, Any],
        ] = {}
        self.cover: dict[str, Any] | None = None

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
        classes = class_tokens(mapping)

        store_name = None

        if "ls-store-amazon" in classes:
            store_name = "amazon"
        elif "ls-store-kobo" in classes:
            store_name = "rakuten_kobo"
        elif "ls-store-dmm" in classes:
            store_name = "dmm"

        if store_name is not None:
            href = mapping.get("href")

            if (
                tag.casefold() == "a"
                and isinstance(href, str)
            ):
                state = (
                    "active_source_link_"
                    "disabled_in_safe_preview"
                )
                host = safe_host(href)
                fingerprint = text_sha(href)
            else:
                state = "disabled_no_source_link"
                host = None
                fingerprint = None

            self.stores[store_name] = {
                "store": store_name,
                "source_tag": tag.casefold(),
                "state": state,
                "host": host,
                "url_fingerprint_sha256": (
                    fingerprint
                ),
                "safe_preview_interaction": (
                    "disabled"
                )
            }

        if (
            tag.casefold() == "img"
            and self.cover is None
        ):
            src = mapping.get("src")

            self.cover = {
                "state": (
                    "embedded_placeholder_"
                    "no_external_asset_request"
                ),
                "source_host": (
                    safe_host(src)
                    if isinstance(src, str)
                    else None
                ),
                "source_asset_fingerprint_sha256": (
                    text_sha(src)
                    if isinstance(src, str)
                    else None
                )
            }

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        self.handle_starttag(tag, attrs)


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

        mapping: list[
            tuple[str, str | None]
        ] = []

        original_href = None
        original_src = None

        for key, value in attrs:
            lowered = key.casefold()

            if lowered == "href":
                original_href = value
                continue

            if lowered in {
                "src",
                "srcset",
                "sizes",
            }:
                if lowered == "src":
                    original_src = value
                continue

            if lowered == "target":
                continue

            if (
                isinstance(value, str)
                and (
                    "http://" in value
                    or "https://" in value
                    or "af_id=" in value
                    or "lurl=" in value
                )
            ):
                mapping.append(
                    (lowered, "redacted")
                )
            else:
                mapping.append(
                    (lowered, value)
                )

        if tag == "a":
            mapping.append(
                ("href", "#preview-disabled")
            )
            mapping.append(
                ("aria-disabled", "true")
            )
            mapping.append(
                ("tabindex", "-1")
            )

            if isinstance(
                original_href,
                str,
            ):
                host = safe_host(
                    original_href
                )
                fingerprint = text_sha(
                    original_href
                )

                if host is not None:
                    mapping.append(
                        (
                            "data-preview-host",
                            host,
                        )
                    )

                mapping.append(
                    (
                        "data-preview-url-fingerprint",
                        fingerprint,
                    )
                )

        if tag == "img":
            mapping.append(
                ("src", placeholder_data_uri())
            )
            mapping.append(
                (
                    "data-preview-asset-state",
                    "embedded-placeholder",
                )
            )

            if isinstance(
                original_src,
                str,
            ):
                mapping.append(
                    (
                        "data-preview-original-asset-fingerprint",
                        text_sha(original_src),
                    )
                )

        rendered_attrs = ""

        for key, value in mapping:
            if value is None:
                rendered_attrs += (
                    " "
                    + html.escape(
                        key,
                        quote=True,
                    )
                )
            else:
                rendered_attrs += (
                    " "
                    + html.escape(
                        key,
                        quote=True,
                    )
                    + '="'
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

    def handle_entityref(
        self,
        name: str,
    ) -> None:
        if self.skip_tag is None:
            self.parts.append(
                "&"
                + name
                + ";"
            )

    def handle_charref(
        self,
        name: str,
    ) -> None:
        if self.skip_tag is None:
            self.parts.append(
                "&#"
                + name
                + ";"
            )

    def get_html(self) -> str:
        return "".join(self.parts)


def sanitize_rendered_html(
    source: str,
) -> str:
    without_leading_style = re.sub(
        (
            r"\A\s*<style\b[^>]*>"
            r".*?</style>\s*"
        ),
        "",
        source,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )

    parser = SafePreviewSanitizer()
    parser.feed(without_leading_style)
    parser.close()

    return parser.get_html()


def manifest_rows(
    stores: list[dict[str, Any]],
) -> str:
    rows = []

    for store in stores:
        host = (
            store["host"]
            if store["host"] is not None
            else "なし（リンク未設定）"
        )
        fingerprint = (
            store["url_fingerprint_sha256"]
            if store[
                "url_fingerprint_sha256"
            ] is not None
            else "なし"
        )

        rows.append(
            "<tr>"
            "<td>"
            + html.escape(store["store"])
            + "</td>"
            "<td>"
            + html.escape(store["state"])
            + "</td>"
            "<td>"
            + html.escape(host)
            + "</td>"
            "<td><code>"
            + html.escape(fingerprint)
            + "</code></td>"
            "</tr>"
        )

    return "\n".join(rows)


def preview_shell(
    *,
    mode: str,
    source_css: str,
    sanitized_body: str,
    stores: list[dict[str, Any]],
) -> str:
    require(
        mode in {"desktop", "mobile"},
        "PREVIEW_MODE_INVALID",
    )

    if mode == "desktop":
        stage_width = "1180px"
        mode_label = "デスクトップ強制表示"
        override_css = """
#ebook-product-192 {
  grid-template-columns: minmax(260px, 38%) minmax(0, 1fr) !important;
}

#ebook-product-192 .ebook-product-card__pr {
  order: 1 !important;
}

#ebook-product-192 .ebook-product-card__stores {
  order: 2 !important;
}

#ebook-product-192 .ebook-product-card__details {
  order: 3 !important;
}
"""
    else:
        stage_width = "390px"
        mode_label = "スマートフォン強制表示"
        override_css = """
#ebook-product-192 {
  grid-template-columns: minmax(0, 1fr) !important;
}

#ebook-product-192 .ebook-product-card__details {
  order: 1 !important;
}

#ebook-product-192 .ebook-product-card__pr {
  order: 2 !important;
}

#ebook-product-192 .ebook-product-card__stores {
  order: 3 !important;
}

#ebook-product-192 .ebook-product-card__detail-row {
  grid-template-columns: minmax(0, 1fr) !important;
}
"""

    review_css = f"""
body {{
  margin: 0;
  padding: 2rem;
  background: #ececec;
  color: #222;
  font-family:
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}}

.preview-header,
.preview-safety,
.preview-manifest,
.preview-stage {{
  width: min(100%, {stage_width});
  margin-inline: auto;
}}

.preview-header,
.preview-safety,
.preview-manifest {{
  margin-bottom: 1.25rem;
  padding: 1rem;
  border: 1px solid #cfcfcf;
  border-radius: 0.6rem;
  background: #fff;
}}

.preview-stage {{
  padding: 1.25rem;
  border: 1px solid #bdbdbd;
  border-radius: 0.7rem;
  background: #fff;
}}

.preview-safety {{
  font-weight: 700;
}}

.preview-manifest {{
  overflow-x: auto;
}}

.preview-manifest table {{
  width: 100%;
  border-collapse: collapse;
}}

.preview-manifest th,
.preview-manifest td {{
  padding: 0.55rem;
  border: 1px solid #d7d7d7;
  text-align: left;
  vertical-align: top;
}}

.preview-manifest code {{
  overflow-wrap: anywhere;
}}

#ebook-product-192 a,
#ebook-product-192 [aria-disabled="true"] {{
  pointer-events: none !important;
  cursor: not-allowed !important;
}}

#ebook-product-192 .ebook-product-card__stores > * {{
  display: block;
  padding: 0.9rem;
  border: 1px solid #bdbdbd;
  border-radius: 0.5rem;
  text-align: center;
  font-weight: 700;
  text-decoration: none;
}}

#ebook-product-192 .ls-store-disabled {{
  opacity: 0.55;
}}

{override_css}
"""

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M23 {html.escape(mode_label)}</title>
<style>
{source_css}
{review_css}
</style>
</head>
<body data-preview-mode="{html.escape(mode)}">
<section class="preview-header">
  <h1>M23 {html.escape(mode_label)}</h1>
  <p>WordPress投稿ID192・人間レビュー専用ローカルプレビュー</p>
</section>

<section class="preview-safety">
  外部リンクは無効化済みです。外部画像は埋込みプレースホルダーへ置換されています。
  このファイルには完全なストアURLやアフィリエイト識別子を含めていません。
</section>

<section class="preview-manifest">
  <h2>安全なストア導線確認</h2>
  <table>
    <thead>
      <tr>
        <th>ストア</th>
        <th>状態</th>
        <th>ホスト</th>
        <th>URLフィンガープリント</th>
      </tr>
    </thead>
    <tbody>
      {manifest_rows(stores)}
    </tbody>
  </table>
</section>

<main class="preview-stage">
{sanitized_body}
</main>
</body>
</html>
"""


def assert_safe_preview(
    value: str,
) -> None:
    lowered = value.casefold()

    for forbidden in FORBIDDEN_PREVIEW_TEXT:
        require(
            forbidden.casefold()
            not in lowered,
            (
                "FORBIDDEN_PREVIEW_TEXT:"
                + forbidden
            ),
        )

    require(
        'href="#preview-disabled"'
        in value,
        "SANITIZED_LINK_MARKER_MISSING",
    )
    require(
        "data:image/svg+xml;base64,"
        in value,
        "EMBEDDED_IMAGE_PLACEHOLDER_MISSING",
    )


def main() -> int:
    source_paths = {
        "m22_failure_chain": M22_FAILURE_CHAIN,
        "m22_rollback": M22_ROLLBACK,
        "m22_css": M22_CSS,
        "m22_rendered": M22_RENDERED,
        "m22_payload": M22_PAYLOAD,
        "m22_result": M22_RESULT,
    }

    try:
        for output in [
            STORE_MANIFEST,
            DESKTOP_PREVIEW,
            MOBILE_PREVIEW,
            REVIEW_PACKET,
            CHECKLIST,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M23_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M23",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["operation_mode"]
            == (
                "LOCAL_SAFE_VISUAL_REVIEW_"
                "PREPARATION_ONLY"
            ),
            "POLICY_OPERATION_MODE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_RENDERED_LAYOUT_CORRECTION_"
                "HUMAN_REVIEW_PREPARATION_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval["human_explicit_approval"]
            is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )
        require(
            approval[
                "safe_preview_generation_approved"
            ] is True,
            "SAFE_PREVIEW_NOT_APPROVED",
        )
        require(
            approval[
                "external_links_in_preview_approved"
            ] is False,
            "EXTERNAL_LINKS_APPROVED",
        )
        require(
            approval[
                "human_review_result_recording_approved"
            ] is False,
            "REVIEW_RESULT_RECORDING_APPROVED",
        )
        require(
            approval["wordpress_update_approved"]
            is False,
            "WORDPRESS_UPDATE_APPROVED",
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

        failure_chain = load_json(
            M22_FAILURE_CHAIN
        )
        rollback = load_json(
            M22_ROLLBACK
        )
        update_payload = load_json(
            M22_PAYLOAD
        )
        m22_result = load_json(
            M22_RESULT
        )

        verify_digest(
            failure_chain,
            "failure_chain_digest_sha256",
            EXPECTED_FAILURE_CHAIN_DIGEST,
        )
        verify_digest(
            rollback,
            "rollback_evidence_digest_sha256",
            EXPECTED_ROLLBACK_DIGEST,
        )
        verify_digest(
            update_payload,
            "update_payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            m22_result,
            "result_digest_sha256",
            EXPECTED_RESULT_DIGEST,
        )

        source_css = M22_CSS.read_text(
            encoding="utf-8"
        )
        source_rendered = (
            M22_RENDERED.read_text(
                encoding="utf-8"
            )
        )

        require(
            text_sha(source_css)
            == EXPECTED_SCOPED_CSS_SHA,
            "SCOPED_CSS_SHA_MISMATCH",
        )
        require(
            text_sha(source_rendered)
            == EXPECTED_RENDERED_CONTENT_SHA,
            "RENDERED_HTML_SHA_MISMATCH",
        )
        require(
            rollback[
                "current_content_html_sha256"
            ] == EXPECTED_CURRENT_CONTENT_SHA,
            "CURRENT_CONTENT_SHA_MISMATCH",
        )

        require(
            m22_result["status"]
            == (
                "PASS_WORDPRESS_RENDERED_LAYOUT_"
                "CORRECTION_RESULT_SCHEMA_FIXED_"
                "DOM_VALIDATED_UPDATE_PAYLOAD_"
                "GENERATED_LOCAL_ONLY_NON_EXECUTABLE_"
                "NO_WORDPRESS_ACCESS"
            ),
            "M22_FIX2_STATUS_MISMATCH",
        )
        require(
            m22_result[
                "ready_for_rendered_update_payload_human_review"
            ] is True,
            "M22_FIX2_REVIEW_NOT_READY",
        )
        require(
            m22_result[
                "ready_for_wordpress_update_authorization_gate"
            ] is False,
            "M22_FIX2_AUTH_GATE_OPEN",
        )
        require(
            m22_result[
                "ready_for_wordpress_update"
            ] is False,
            "M22_FIX2_UPDATE_GATE_OPEN",
        )
        require(
            m22_result[
                "wordpress_access_performed"
            ] is False,
            "M22_FIX2_WORDPRESS_ACCESS_TRUE",
        )

        request_body = update_payload[
            "wordpress_request_body"
        ]

        require(
            set(request_body.keys())
            == {
                "content",
                "comment_status",
            },
            "REQUEST_BODY_FIELD_SET_MISMATCH",
        )
        require(
            request_body["content"]
            == source_rendered,
            "REQUEST_BODY_CONTENT_MISMATCH",
        )
        require(
            request_body[
                "comment_status"
            ] == "closed",
            "COMMENT_STATUS_NOT_CLOSED",
        )
        require(
            update_payload[
                "execution_allowed"
            ] is False,
            "UPDATE_PAYLOAD_EXECUTION_ALLOWED",
        )
        require(
            update_payload[
                "authorization_issued"
            ] is False,
            "UPDATE_PAYLOAD_AUTHORIZATION_ISSUED",
        )

        scanner = SourceScanner()
        scanner.feed(source_rendered)
        scanner.close()

        require(
            set(scanner.stores.keys())
            == set(EXPECTED_STORES),
            "STORE_SET_MISMATCH",
        )

        stores = [
            scanner.stores[name]
            for name in EXPECTED_STORES
        ]

        require(
            scanner.stores["amazon"][
                "state"
            ] == "disabled_no_source_link",
            "AMAZON_STATE_MISMATCH",
        )
        require(
            scanner.stores["rakuten_kobo"][
                "state"
            ] == "disabled_no_source_link",
            "KOBO_STATE_MISMATCH",
        )
        require(
            scanner.stores["dmm"][
                "state"
            ] == (
                "active_source_link_"
                "disabled_in_safe_preview"
            ),
            "DMM_STATE_MISMATCH",
        )
        require(
            scanner.stores["dmm"][
                "host"
            ] == "al.dmm.com",
            "DMM_HOST_MISMATCH",
        )
        require(
            scanner.stores["dmm"][
                "url_fingerprint_sha256"
            ] == m22_result[
                "dmm_url_fingerprint_sha256"
            ],
            "DMM_FINGERPRINT_MISMATCH",
        )

        store_manifest_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M23"
            ),
            "document_role": (
                "SAFE_STORE_STATE_HOST_AND_"
                "FINGERPRINT_MANIFEST"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "stores": stores,
            "cover_asset": (
                scanner.cover
                if scanner.cover is not None
                else {
                    "state": (
                        "no_cover_asset_detected"
                    )
                }
            ),
            "full_store_url_present": False,
            "affiliate_identifier_present": False,
            "preview_external_link_count": 0,
            "preview_external_asset_request_count": 0,
            "created_at_utc": now()
        }

        store_manifest = add_digest(
            store_manifest_without_digest,
            "store_manifest_digest_sha256",
        )

        manifest_text = json.dumps(
            store_manifest,
            ensure_ascii=False,
            indent=2,
        )

        for forbidden in FORBIDDEN_PREVIEW_TEXT:
            require(
                forbidden.casefold()
                not in manifest_text.casefold(),
                (
                    "FORBIDDEN_MANIFEST_TEXT:"
                    + forbidden
                ),
            )

        write_json(
            STORE_MANIFEST,
            store_manifest,
        )

        sanitized_body = (
            sanitize_rendered_html(
                source_rendered
            )
        )

        desktop_preview = preview_shell(
            mode="desktop",
            source_css=source_css,
            sanitized_body=sanitized_body,
            stores=stores,
        )
        mobile_preview = preview_shell(
            mode="mobile",
            source_css=source_css,
            sanitized_body=sanitized_body,
            stores=stores,
        )

        assert_safe_preview(
            desktop_preview
        )
        assert_safe_preview(
            mobile_preview
        )

        require(
            'data-preview-mode="desktop"'
            in desktop_preview,
            "DESKTOP_MODE_MARKER_MISSING",
        )
        require(
            'data-preview-mode="mobile"'
            in mobile_preview,
            "MOBILE_MODE_MARKER_MISSING",
        )

        write_text(
            DESKTOP_PREVIEW,
            desktop_preview,
        )
        write_text(
            MOBILE_PREVIEW,
            mobile_preview,
        )

        desktop_preview_sha = text_sha(
            desktop_preview
        )
        mobile_preview_sha = text_sha(
            mobile_preview
        )

        review_packet_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M23"
            ),
            "document_role": (
                "WORDPRESS_RENDERED_LAYOUT_"
                "HUMAN_REVIEW_PREPARATION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "human_review_status": (
                "AWAITING_VISUAL_REVIEW"
            ),
            "human_review_completed": False,
            "human_review_verdict": (
                "NOT_RECORDED"
            ),
            "review_targets": [
                {
                    "review_id": (
                        "DESKTOP_TWO_COLUMN_LAYOUT"
                    ),
                    "required": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                },
                {
                    "review_id": (
                        "MOBILE_SINGLE_COLUMN_ORDER"
                    ),
                    "required": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                },
                {
                    "review_id": (
                        "COVER_SIZE_AND_SPACING"
                    ),
                    "required": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                },
                {
                    "review_id": (
                        "STORE_BUTTON_ORDER_AND_BALANCE"
                    ),
                    "required": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                },
                {
                    "review_id": (
                        "PR_DISCLOSURE_VISIBILITY"
                    ),
                    "required": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                },
                {
                    "review_id": (
                        "DETAIL_WIDTH_WRAPPING_WHITESPACE"
                    ),
                    "required": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                },
                {
                    "review_id": (
                        "COMMENT_STATUS_CLOSED"
                    ),
                    "required": True,
                    "machine_verified": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                },
                {
                    "review_id": (
                        "UPDATE_FIELDS_CONTENT_AND_"
                        "COMMENT_STATUS_ONLY"
                    ),
                    "required": True,
                    "machine_verified": True,
                    "review_result": (
                        "NOT_RECORDED"
                    )
                }
            ],
            "desktop_preview_path": str(
                DESKTOP_PREVIEW.relative_to(ROOT)
            ),
            "desktop_preview_sha256": (
                desktop_preview_sha
            ),
            "mobile_preview_path": str(
                MOBILE_PREVIEW.relative_to(ROOT)
            ),
            "mobile_preview_sha256": (
                mobile_preview_sha
            ),
            "safe_store_manifest_path": str(
                STORE_MANIFEST.relative_to(ROOT)
            ),
            "safe_store_manifest_digest_sha256": (
                store_manifest[
                    "store_manifest_digest_sha256"
                ]
            ),
            "source_rendered_content_sha256": (
                EXPECTED_RENDERED_CONTENT_SHA
            ),
            "source_scoped_css_sha256": (
                EXPECTED_SCOPED_CSS_SHA
            ),
            "source_update_payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "comment_status_target": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status",
            ],
            "safe_preview_external_links_active": False,
            "safe_preview_external_assets_requested": False,
            "full_store_url_present": False,
            "affiliate_identifier_present": False,
            "wordpress_access_performed": False,
            "wordpress_update_performed": False,
            "authorization_issued": False,
            "ready_for_human_visual_review": True,
            "ready_for_wordpress_update_authorization_gate": False,
            "production_status": "NO_GO",
            "created_at_utc": now()
        }

        review_packet = add_digest(
            review_packet_without_digest,
            "review_preparation_digest_sha256",
        )

        write_json(
            REVIEW_PACKET,
            review_packet,
        )

        write_text(
            CHECKLIST,
            """# M23 人間目視レビュー・チェックリスト

確認対象は、次の安全プレビュー2ファイルだけです。

- デスクトップ:
  `exchange/previews/new_release/fresh/new-release-comic-20260703-001.wordpress_layout_desktop_safe_preview.html`
- スマートフォン:
  `exchange/previews/new_release/fresh/new-release-comic-20260703-001.wordpress_layout_mobile_safe_preview.html`

元のレンダリング済みHTMLや更新Payloadには完全なストア導線情報が含まれるため、通常の目視確認には使用しないでください。

## デスクトップ

- [ ] 書影が左側に配置されている
- [ ] 右側の先頭にPR表記がある
- [ ] Amazon、楽天Kobo、DMMの順で縦並びになっている
- [ ] 作品詳細がストアボタン群の下にある
- [ ] 書影と右側領域の比率が不自然ではない
- [ ] 右側に過剰な空白がない
- [ ] 作品詳細のラベルと値が読みやすい
- [ ] 文字が不自然に細切れ改行されていない

## スマートフォン

- [ ] 書影が先頭にある
- [ ] 作品詳細が書影の次にある
- [ ] PR表記が各ストアボタンより前にある
- [ ] Amazon、楽天Kobo、DMMの順になっている
- [ ] 横スクロールが発生していない
- [ ] 詳細欄のラベルと値が読みやすい
- [ ] 余白が広すぎず狭すぎない

## 機械検証済み境界

- [x] 更新フィールドは `content` と `comment_status` のみ
- [x] `comment_status=closed`
- [x] 外部リンクは安全プレビュー内で無効
- [x] 外部画像通信は埋込みプレースホルダーに置換
- [x] 完全なストアURLを安全プレビューへ出力していない
- [x] アフィリエイト識別子を安全プレビューへ出力していない
- [x] WordPress更新認可は未発行
- [x] WordPressアクセス・更新は未実行
""",
        )

        for path in [
            STORE_MANIFEST,
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-M23"
            ),
            "status": (
                "PASS_WORDPRESS_RENDERED_LAYOUT_"
                "CORRECTION_HUMAN_REVIEW_PREPARATION_"
                "SAFE_PREVIEWS_READY_LOCAL_ONLY_"
                "NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "SAFE_DESKTOP_AND_MOBILE_PREVIEWS_"
                "READY_AWAITING_HUMAN_VISUAL_REVIEW"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "source_m22_fix2_result_digest_sha256": (
                EXPECTED_RESULT_DIGEST
            ),
            "source_rendered_content_sha256": (
                EXPECTED_RENDERED_CONTENT_SHA
            ),
            "source_scoped_css_sha256": (
                EXPECTED_SCOPED_CSS_SHA
            ),
            "source_update_payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "store_manifest_path": str(
                STORE_MANIFEST.relative_to(ROOT)
            ),
            "store_manifest_digest_sha256": (
                store_manifest[
                    "store_manifest_digest_sha256"
                ]
            ),
            "desktop_preview_path": str(
                DESKTOP_PREVIEW.relative_to(ROOT)
            ),
            "desktop_preview_sha256": (
                desktop_preview_sha
            ),
            "mobile_preview_path": str(
                MOBILE_PREVIEW.relative_to(ROOT)
            ),
            "mobile_preview_sha256": (
                mobile_preview_sha
            ),
            "review_packet_path": str(
                REVIEW_PACKET.relative_to(ROOT)
            ),
            "review_preparation_digest_sha256": (
                review_packet[
                    "review_preparation_digest_sha256"
                ]
            ),
            "checklist_path": str(
                CHECKLIST.relative_to(ROOT)
            ),
            "safe_desktop_preview_generated": True,
            "safe_mobile_preview_generated": True,
            "external_links_active_in_previews": False,
            "external_asset_requests_in_previews": False,
            "full_store_url_present_in_previews": False,
            "affiliate_identifier_present_in_previews": False,
            "store_confirmation_uses_host_state_and_fingerprint_only": True,
            "comment_status_target": "closed",
            "allowed_update_fields": [
                "content",
                "comment_status",
            ],
            "human_review_completed": False,
            "human_review_verdict": (
                "NOT_RECORDED"
            ),
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
                "SAFE_VISUAL_REVIEW_PREVIEWS_READY_"
                "AWAITING_HUMAN_REVIEW_NO_WORDPRESS_UPDATE"
            ),
            "ready_for_human_visual_review": True,
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M23

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- Safe desktop preview generated: `true`
- Safe mobile preview generated: `true`
- Desktop preview SHA-256: `{desktop_preview_sha}`
- Mobile preview SHA-256: `{mobile_preview_sha}`
- Store confirmation method: `host / state / fingerprint only`
- Active external links in preview: `false`
- External asset requests in preview: `false`
- Full store URL in preview: `false`
- Affiliate identifier in preview: `false`
- Comment status target: `closed`
- Allowed update fields: `content, comment_status`
- Human review completed: `false`
- Human review verdict: `NOT_RECORDED`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Authorization issued: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Ready for human visual review: `true`
- Ready for WordPress update authorization gate: `false`
- Ready for WordPress update: `false`
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M23"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_RENDERED_LAYOUT_"
                        "CORRECTION_HUMAN_REVIEW_PREPARATION_"
                        "NO_WORDPRESS_ACCESS"
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
