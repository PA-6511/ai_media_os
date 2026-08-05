#!/usr/bin/env python3

from __future__ import annotations

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
        "NETWORK_OPERATION_BLOCKED_BY_M22_FIX2"
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
    "result_schema_fix_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m22_fix2_approval.json"
)

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
SOURCE_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)
M20_DESIGN = ROOT / (
    "exchange/designs/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_design.json"
)
M20_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m20_result.json"
)
M21_ADOPTION = ROOT / (
    "exchange/decisions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_compliant_layout_revision_adoption.json"
)
M21_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m21_result.json"
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
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m22_fix2_"
    "rendered_layout_correction_result_schema_fix_report.md"
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
EXPECTED_M20_DESIGN_DIGEST = (
    "e49bbaf98e529986f0c04956b909029f"
    "2055e2eb0f9e19e100a002e265caf495"
)
EXPECTED_M20_RESULT_DIGEST = (
    "564f734dd840a5be3653eeffd4ecf816"
    "13cada7b74b125645e53428637ccb301"
)
EXPECTED_M21_ADOPTION_DIGEST = (
    "fdb707f5ad8bb0536f5f8b98f79a0ff2"
    "3e4a727b1717de7b1a459e9fc7645d9e"
)
EXPECTED_M21_RESULT_DIGEST = (
    "9628e73b193d327e3020a266313293a6"
    "3dc57f953ecac53139f62bfd50821cdf"
)

EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
)
EXPECTED_DETAILS = {
    "作品名": "ダークギャザリング",
    "価格": "616円（税込）",
    "作者": "近藤憲一",
    "出版社": "集英社",
    "発売日": "2026-07-03",
}
DETAIL_ORDER = [
    "作品名",
    "価格",
    "作者",
    "出版社",
    "発売日",
]
PR_TEXT = (
    "PR：このページには"
    "アフィリエイト広告が含まれます。"
)
EXPECTED_DOM_EVENTS = [
    "cover_image",
    "responsive_work_details",
    "pr_disclosure",
    "store_container",
    "amazon_button",
    "rakuten_kobo_button",
    "dmm_button",
]


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
            flags=re.DOTALL,
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
    scanner = AttributeScanner()
    scanner.feed(fragment)
    scanner.close()
    return scanner.elements


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


def collect_urls(
    fragment: str,
) -> list[str]:
    values: list[str] = []

    for _, attrs in scan_elements(fragment):
        for field in ("href", "src"):
            value = attrs.get(field)

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
    found = [
        (tag, attrs)
        for tag, attrs in scan_elements(fragment)
        if required_class in class_tokens(attrs)
    ]

    require(
        len(found) == 1,
        (
            f"STORE_ELEMENT_{required_class}_"
            f"COUNT_{len(found)}"
        ),
    )

    return found[0]


def validate_url(
    value: str,
    *,
    required_host: str | None = None,
) -> None:
    parsed = urlsplit(value)

    require(
        parsed.scheme == "https",
        "STORE_URL_NOT_HTTPS",
    )
    require(
        parsed.hostname is not None,
        "STORE_URL_HOST_MISSING",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "STORE_URL_USERINFO_REJECTED",
    )
    require(
        parsed.fragment == "",
        "STORE_URL_FRAGMENT_REJECTED",
    )

    if required_host is not None:
        require(
            parsed.hostname == required_host,
            "STORE_URL_HOST_MISMATCH",
        )


class LayoutDOMParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.stack: list[str] = []
        self.inside_root = False
        self.root_depth: int | None = None
        self.root_count = 0
        self.events: list[str] = []

    def record(
        self,
        attrs: dict[str, str | None],
    ) -> None:
        classes = class_tokens(attrs)

        if "ebook-product-card__cover" in classes:
            self.events.append("cover_image")
        elif "ebook-product-card__details" in classes:
            self.events.append(
                "responsive_work_details"
            )
        elif "ebook-product-card__pr" in classes:
            self.events.append("pr_disclosure")
        elif "ebook-product-card__stores" in classes:
            self.events.append("store_container")
        elif "ls-store-amazon" in classes:
            self.events.append("amazon_button")
        elif "ls-store-kobo" in classes:
            self.events.append(
                "rakuten_kobo_button"
            )
        elif "ls-store-dmm" in classes:
            self.events.append("dmm_button")

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

        if mapping.get("id") == "ebook-product-192":
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


def parse_dom_events(
    rendered: str,
) -> tuple[int, list[str]]:
    parser = LayoutDOMParser()
    parser.feed(rendered)
    parser.close()

    return parser.root_count, parser.events


def require_css_order(
    css_segment: str,
    class_name: str,
    expected_order: int,
    code: str,
) -> None:
    pattern = (
        rf"#ebook-product-192\s+"
        rf"\.{re.escape(class_name)}\s*"
        rf"\{{[^}}]*\border\s*:\s*"
        rf"{expected_order}\s*;"
    )

    require(
        re.search(
            pattern,
            css_segment,
            flags=re.DOTALL,
        ) is not None,
        code,
    )


def validate_css_orders(
    css: str,
) -> None:
    marker = "@media (min-width: 768px)"

    require(
        marker in css,
        "DESKTOP_MEDIA_QUERY_MISSING",
    )

    mobile_css, desktop_css = css.split(
        marker,
        1,
    )

    require_css_order(
        mobile_css,
        "ebook-product-card__details",
        1,
        "MOBILE_DETAILS_ORDER_MISMATCH",
    )
    require_css_order(
        mobile_css,
        "ebook-product-card__pr",
        2,
        "MOBILE_PR_ORDER_MISMATCH",
    )
    require_css_order(
        mobile_css,
        "ebook-product-card__stores",
        3,
        "MOBILE_STORES_ORDER_MISMATCH",
    )

    require_css_order(
        desktop_css,
        "ebook-product-card__pr",
        1,
        "DESKTOP_PR_ORDER_MISMATCH",
    )
    require_css_order(
        desktop_css,
        "ebook-product-card__stores",
        2,
        "DESKTOP_STORES_ORDER_MISMATCH",
    )
    require_css_order(
        desktop_css,
        "ebook-product-card__details",
        3,
        "DESKTOP_DETAILS_ORDER_MISMATCH",
    )

    require(
        re.search(
            (
                r"#ebook-product-192\s*\{[^}]*"
                r"grid-template-columns\s*:\s*"
                r"minmax\(260px,\s*38%\)\s+"
                r"minmax\(0,\s*1fr\)\s*;"
            ),
            desktop_css,
            flags=re.DOTALL,
        ) is not None,
        "DESKTOP_TWO_COLUMN_GRID_MISSING",
    )


def build_scoped_css() -> str:
    return """#ebook-product-192 {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
  width: 100%;
}

#ebook-product-192,
#ebook-product-192 * {
  box-sizing: border-box;
}

#ebook-product-192 .ebook-product-card__cover {
  min-width: 0;
}

#ebook-product-192 .ebook-product-card__cover .ls-book-cover {
  margin: 0;
}

#ebook-product-192 .ebook-product-card__cover img {
  display: block;
  width: min(100%, 360px);
  height: auto;
  margin-inline: auto;
}

#ebook-product-192 .ebook-product-card__content {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1rem;
}

#ebook-product-192 .ebook-product-card__details {
  order: 1;
  display: grid;
  width: 100%;
  margin: 0;
  overflow: hidden;
  border: 1px solid #d8d8d8;
  border-radius: 0.5rem;
  background: #fff;
}

#ebook-product-192 .ebook-product-card__detail-row {
  display: grid;
  grid-template-columns: minmax(6.5rem, 32%) minmax(0, 1fr);
  margin: 0;
  border-bottom: 1px solid #e3e3e3;
}

#ebook-product-192 .ebook-product-card__detail-row:last-child {
  border-bottom: 0;
}

#ebook-product-192 .ebook-product-card__detail-row dt,
#ebook-product-192 .ebook-product-card__detail-row dd {
  min-width: 0;
  margin: 0;
  padding: 0.72rem 0.85rem;
  line-height: 1.6;
  overflow-wrap: break-word;
  word-break: normal;
}

#ebook-product-192 .ebook-product-card__detail-row dt {
  font-weight: 700;
  background: #f6f6f6;
}

#ebook-product-192 .ebook-product-card__pr {
  order: 2;
  margin: 0;
  padding: 0.62rem 0.78rem;
  border: 1px solid #d8d8d8;
  border-radius: 0.4rem;
  background: #fafafa;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.55;
}

#ebook-product-192 .ebook-product-card__stores {
  order: 3;
  display: grid;
  gap: 0.75rem;
  margin: 0;
}

#ebook-product-192 .ebook-product-card__stores > * {
  width: 100%;
  margin: 0;
}

@media (max-width: 479px) {
  #ebook-product-192 .ebook-product-card__detail-row {
    grid-template-columns: minmax(0, 1fr);
  }

  #ebook-product-192 .ebook-product-card__detail-row dt {
    padding-bottom: 0.35rem;
  }

  #ebook-product-192 .ebook-product-card__detail-row dd {
    padding-top: 0.35rem;
  }
}

@media (min-width: 768px) {
  #ebook-product-192 {
    grid-template-columns: minmax(260px, 38%) minmax(0, 1fr);
    gap: 2rem;
  }

  #ebook-product-192 .ebook-product-card__cover img {
    width: 100%;
    max-width: 360px;
  }

  #ebook-product-192 .ebook-product-card__pr {
    order: 1;
  }

  #ebook-product-192 .ebook-product-card__stores {
    order: 2;
  }

  #ebook-product-192 .ebook-product-card__details {
    order: 3;
  }

  #ebook-product-192 .ebook-product-card__detail-row {
    grid-template-columns: minmax(7rem, 28%) minmax(0, 1fr);
  }
}
"""


def main() -> int:
    source_paths = {
        "article": ARTICLE,
        "source_payload": SOURCE_PAYLOAD,
        "m20_design": M20_DESIGN,
        "m20_result": M20_RESULT,
        "m21_adoption": M21_ADOPTION,
        "m21_result": M21_RESULT,
    }

    try:
        for output in [
            FAILURE_CHAIN,
            ROLLBACK,
            SCOPED_CSS,
            RENDERED_HTML,
            UPDATE_PAYLOAD,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M22_FIX2_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["operation_mode"]
            == (
                "LOCAL_RESULT_SCHEMA_FIX_AND_"
                "NON_EXECUTABLE_PAYLOAD_REGENERATION"
            ),
            "POLICY_OPERATION_MODE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_RENDERED_LAYOUT_CORRECTION_"
                "RESULT_SCHEMA_FIX_APPROVED"
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
                "canonical_result_field_name"
            ] == "previous_m22_rerun_performed",
            "CANONICAL_FIELD_NAME_MISMATCH",
        )
        require(
            approval[
                "deprecated_result_field_name"
            ] == "original_m22_rerun_performed",
            "DEPRECATED_FIELD_NAME_MISMATCH",
        )
        require(
            approval[
                "result_and_test_schema_unification_approved"
            ] is True,
            "SCHEMA_UNIFICATION_NOT_APPROVED",
        )
        require(
            approval["m22_rerun_approved"]
            is False,
            "M22_RERUN_APPROVED",
        )
        require(
            approval["m22_fix1_rerun_approved"]
            is False,
            "M22_FIX1_RERUN_APPROVED",
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

        require(
            source_hashes["article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["source_payload"]
            == EXPECTED_SOURCE_PAYLOAD_SHA,
            "SOURCE_PAYLOAD_FILE_SHA_MISMATCH",
        )

        article = load_json(ARTICLE)
        source_payload = load_json(
            SOURCE_PAYLOAD
        )
        m20_design = load_json(
            M20_DESIGN
        )
        m20_result = load_json(
            M20_RESULT
        )
        m21_adoption = load_json(
            M21_ADOPTION
        )
        m21_result = load_json(
            M21_RESULT
        )

        verify_digest(
            source_payload,
            "payload_digest_sha256",
            EXPECTED_SOURCE_PAYLOAD_DIGEST,
        )
        verify_digest(
            m20_design,
            "design_digest_sha256",
            EXPECTED_M20_DESIGN_DIGEST,
        )
        verify_digest(
            m20_result,
            "result_digest_sha256",
            EXPECTED_M20_RESULT_DIGEST,
        )
        verify_digest(
            m21_adoption,
            "adoption_evidence_digest_sha256",
            EXPECTED_M21_ADOPTION_DIGEST,
        )
        verify_digest(
            m21_result,
            "result_digest_sha256",
            EXPECTED_M21_RESULT_DIGEST,
        )

        require(
            m21_result[
                "compliant_layout_revision_adopted"
            ] is True,
            "M21_LAYOUT_NOT_ADOPTED",
        )
        require(
            m21_result[
                "ready_for_rendered_update_payload_generation_gate"
            ] is True,
            "M21_RENDER_GATE_NOT_READY",
        )
        require(
            m21_result[
                "ready_for_wordpress_update"
            ] is False,
            "M21_WORDPRESS_UPDATE_GATE_OPEN",
        )

        require(
            m21_adoption[
                "adopted_desktop_layout"
            ]["right_column_order"] == [
                "pr_disclosure",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
                "responsive_work_details",
            ],
            "M21_DESKTOP_ORDER_MISMATCH",
        )
        require(
            m21_adoption[
                "adopted_mobile_order"
            ] == [
                "cover_image",
                "responsive_work_details",
                "pr_disclosure",
                "amazon_button",
                "rakuten_kobo_button",
                "dmm_button",
            ],
            "M21_MOBILE_ORDER_MISMATCH",
        )
        require(
            m21_adoption[
                "adopted_comment_contract"
            ]["comment_status"] == "closed",
            "M21_COMMENT_STATUS_MISMATCH",
        )

        require(
            article["article_title"]
            == EXPECTED_TITLE,
            "ARTICLE_TITLE_MISMATCH",
        )
        require(
            source_payload["title"]
            == EXPECTED_TITLE,
            "SOURCE_PAYLOAD_TITLE_MISMATCH",
        )
        require(
            source_payload["content_html"]
            == article["content_html"],
            "ARTICLE_PAYLOAD_CONTENT_MISMATCH",
        )
        require(
            source_payload["categories"]
            == [10],
            "SOURCE_PAYLOAD_CATEGORY_MISMATCH",
        )

        failure_chain_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2"
            ),
            "document_role": (
                "M22_AND_M22_FIX1_FAILURE_CHAIN"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "failures": [
                {
                    "failed_phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M22"
                    ),
                    "classification": (
                        "STYLE_ELEMENT_TEXT_FALSE_POSITIVE"
                    ),
                    "pytest_passed_count": 7,
                    "pytest_failed_count": 1,
                    "temporary_result_digest_sha256": (
                        "613db1031948407ec473821eb39b4455"
                        "a27e9e070ebc90f690b40b0e09584f3b"
                    ),
                    "temporary_result_is_final": False,
                    "temporary_result_adopted": False,
                    "rerun_performed": False
                },
                {
                    "failed_phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX1"
                    ),
                    "classification": (
                        "RESULT_SCHEMA_FIELD_NAME_MISMATCH"
                    ),
                    "pytest_passed_count": 8,
                    "pytest_failed_count": 1,
                    "failed_test": (
                        "test_no_external_or_authorization_operation"
                    ),
                    "generated_field_name": (
                        "previous_m22_rerun_performed"
                    ),
                    "incorrect_test_field_name": (
                        "original_m22_rerun_performed"
                    ),
                    "exception_type": "KeyError",
                    "temporary_result_digest_sha256": (
                        "d4f6bb83ba112644d27b0e422537d3c3"
                        "a328788b66b33dd747c94588840e35ef"
                    ),
                    "temporary_result_is_final": False,
                    "temporary_result_adopted": False,
                    "rerun_performed": False
                }
            ],
            "canonical_result_field_name": (
                "previous_m22_rerun_performed"
            ),
            "deprecated_result_field_name": (
                "original_m22_rerun_performed"
            ),
            "deprecated_result_field_allowed": False,
            "fix_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2"
            ),
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_update_performed": False,
            "recorded_at_utc": now()
        }

        failure_chain = add_digest(
            failure_chain_without_digest,
            "failure_chain_digest_sha256",
        )
        write_json(
            FAILURE_CHAIN,
            failure_chain,
        )

        current_content = article[
            "content_html"
        ]

        require(
            isinstance(current_content, str)
            and current_content != "",
            "CURRENT_CONTENT_MISSING",
        )

        cover_html = extract_one(
            (
                r'<figure class="ls-book-cover">'
                r'.*?</figure>'
            ),
            current_content,
            "COVER_HTML",
        )

        detail_card_html = extract_one(
            (
                r'<div class="ls-store-card">'
                r'.*?</div>'
            ),
            current_content,
            "DETAIL_CARD_HTML",
        )

        store_inner = extract_one(
            (
                r'<div class="ls-store-buttons"'
                r'[^>]*>(.*?)</div>'
            ),
            current_content,
            "STORE_BUTTON_CONTAINER",
            1,
        )

        extract_one(
            (
                r'<p class="ebook-pr-disclosure">'
                r'.*?</p>'
            ),
            current_content,
            "CURRENT_PR_DISCLOSURE",
        )

        detail_matches = list(
            re.finditer(
                (
                    r"<li>\s*<strong>(.*?)</strong>"
                    r"(.*?)</li>"
                ),
                detail_card_html,
                flags=re.DOTALL,
            )
        )

        require(
            len(detail_matches)
            == len(DETAIL_ORDER),
            "DETAIL_FIELD_COUNT_MISMATCH",
        )

        detail_values: dict[str, str] = {}

        for match in detail_matches:
            label = text_content(
                match.group(1)
            ).rstrip("：:").strip()

            value = text_content(
                match.group(2)
            ).strip()

            require(
                label not in detail_values,
                f"DUPLICATE_DETAIL_LABEL:{label}",
            )

            detail_values[label] = value

        require(
            list(detail_values.keys())
            == DETAIL_ORDER,
            "DETAIL_LABEL_ORDER_MISMATCH",
        )
        require(
            detail_values == EXPECTED_DETAILS,
            "DETAIL_VALUES_MISMATCH",
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
            "AMAZON_ELEMENT_NOT_SPAN",
        )
        require(
            "ls-store-disabled"
            in class_tokens(amazon_attrs),
            "AMAZON_STATE_CHANGED",
        )
        require(
            amazon_attrs.get("href") is None,
            "AMAZON_UNEXPECTED_HREF",
        )

        require(
            kobo_tag == "span",
            "KOBO_ELEMENT_NOT_SPAN",
        )
        require(
            "ls-store-disabled"
            in class_tokens(kobo_attrs),
            "KOBO_STATE_CHANGED",
        )
        require(
            kobo_attrs.get("href") is None,
            "KOBO_UNEXPECTED_HREF",
        )

        require(
            dmm_tag == "a",
            "DMM_ELEMENT_NOT_ANCHOR",
        )

        dmm_href = dmm_attrs.get("href")

        require(
            isinstance(dmm_href, str),
            "DMM_HREF_MISSING",
        )

        validate_url(
            dmm_href,
            required_host="al.dmm.com",
        )

        require(
            dmm_attrs.get("target")
            == "_blank",
            "DMM_TARGET_MISMATCH",
        )

        dmm_rel = dmm_attrs.get("rel")

        require(
            isinstance(dmm_rel, str),
            "DMM_REL_MISSING",
        )
        require(
            set(dmm_rel.split())
            == {
                "nofollow",
                "sponsored",
                "noopener",
            },
            "DMM_REL_MISMATCH",
        )

        current_urls = collect_urls(
            current_content
        )

        require(
            len(current_urls) >= 2,
            "CURRENT_URL_COUNT_TOO_LOW",
        )

        for value in current_urls:
            validate_url(value)

        css = build_scoped_css()

        require(
            "url(" not in css.casefold(),
            "CSS_EXTERNAL_URL_REJECTED",
        )

        validate_css_orders(css)

        detail_rows = "\n".join(
            (
                '      <div class="ebook-product-card__detail-row">\n'
                f"        <dt>{html.escape(label)}</dt>\n"
                f"        <dd>{html.escape(detail_values[label])}</dd>\n"
                "      </div>"
            )
            for label in DETAIL_ORDER
        )

        rendered_html = (
            '<style id="ebook-product-192-scoped-css">\n'
            + css
            + "</style>\n"
            + (
                '<div id="ebook-product-192" '
                'class="ebook-new-release-article ebook-product-card" '
                'data-template-id="POST185_STANDARD_TEMPLATE_V1" '
                'data-layout-version="M22-FIX2-SCHEMA-CONSISTENT-V1">\n'
            )
            + '  <div class="ebook-product-card__cover">\n'
            + cover_html
            + "\n  </div>\n"
            + '  <div class="ebook-product-card__content">\n'
            + '    <dl class="ebook-product-card__details">\n'
            + detail_rows
            + "\n    </dl>\n"
            + (
                '    <p class="ebook-product-card__pr" '
                'role="note">'
            )
            + html.escape(PR_TEXT)
            + "</p>\n"
            + (
                '    <div class="ebook-product-card__stores '
                'ls-store-buttons" aria-label="電子書籍ストア">'
            )
            + store_inner
            + "</div>\n"
            + "  </div>\n"
            + "</div>\n"
        )

        root_count, dom_events = (
            parse_dom_events(rendered_html)
        )

        require(
            root_count == 1,
            f"LAYOUT_ROOT_COUNT_{root_count}",
        )
        require(
            dom_events == EXPECTED_DOM_EVENTS,
            (
                "DOM_EVENT_ORDER_MISMATCH:"
                + ",".join(dom_events)
            ),
        )

        rendered_urls = collect_urls(
            rendered_html
        )

        require(
            Counter(rendered_urls)
            == Counter(current_urls),
            "URL_MULTISET_CHANGED",
        )
        require(
            cover_html in rendered_html,
            "COVER_HTML_NOT_PRESERVED",
        )
        require(
            store_inner in rendered_html,
            "STORE_HTML_NOT_PRESERVED",
        )
        require(
            rendered_html.count(PR_TEXT) == 1,
            "PR_TEXT_COUNT_MISMATCH",
        )
        require(
            current_content != rendered_html,
            "RENDERED_CONTENT_UNCHANGED",
        )

        current_content_sha = text_sha(
            current_content
        )
        rendered_content_sha = text_sha(
            rendered_html
        )
        css_sha = text_sha(css)

        rollback_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2"
            ),
            "document_role": (
                "WORDPRESS_LAYOUT_CORRECTION_"
                "CURRENT_CONTENT_ROLLBACK_EVIDENCE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "last_verified_wordpress_status": "publish",
            "current_content_html": current_content,
            "current_content_html_sha256": (
                current_content_sha
            ),
            "source_article_file_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "source_payload_file_sha256": (
                EXPECTED_SOURCE_PAYLOAD_SHA
            ),
            "source_payload_digest_sha256": (
                EXPECTED_SOURCE_PAYLOAD_DIGEST
            ),
            "live_content_last_verified_equal_to_source": True,
            "live_verification_source_phase": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M18"
            ),
            "live_comment_status_verified_in_this_phase": False,
            "live_comment_status": (
                "UNKNOWN_NOT_NETWORK_CHECKED"
            ),
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "created_at_utc": now()
        }

        rollback = add_digest(
            rollback_without_digest,
            "rollback_evidence_digest_sha256",
        )

        write_json(
            ROLLBACK,
            rollback,
        )
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2"
            ),
            "document_role": (
                "NON_EXECUTABLE_WORDPRESS_RENDERED_"
                "LAYOUT_CORRECTION_UPDATE_PAYLOAD"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "expected_current_status": "publish",
            "operation": (
                "NON_EXECUTABLE_WORDPRESS_POST_UPDATE_DRAFT"
            ),
            "request_method_if_later_authorized": "POST",
            "rest_path_if_later_authorized": (
                "/wp-json/wp/v2/posts/192"
            ),
            "allowed_request_fields": [
                "content",
                "comment_status",
            ],
            "wordpress_request_body": request_body,
            "current_content_html_sha256": (
                current_content_sha
            ),
            "rendered_content_html_sha256": (
                rendered_content_sha
            ),
            "scoped_css_sha256": css_sha,
            "rollback_evidence_path": str(
                ROLLBACK.relative_to(ROOT)
            ),
            "rollback_evidence_digest_sha256": (
                rollback[
                    "rollback_evidence_digest_sha256"
                ]
            ),
            "validator_type": (
                "HTMLPARSER_DOM_ONLY"
            ),
            "style_element_text_ignored_for_dom_order": True,
            "dom_event_order_verified": dom_events,
            "desktop_css_order_verified": True,
            "canonical_result_field_name": (
                "previous_m22_rerun_performed"
            ),
            "deprecated_result_field_present": False,
            "store_url_multiset_preserved": True,
            "store_button_html_preserved": True,
            "cover_html_preserved": True,
            "pr_disclosure_before_first_store_interaction": True,
            "target_comment_status": "closed",
            "title_field_in_request": False,
            "status_field_in_request": False,
            "categories_field_in_request": False,
            "slug_field_in_request": False,
            "excerpt_field_in_request": False,
            "execution_allowed": False,
            "authorization_issued": False,
            "authorization_consumed": False,
            "authorization_reused": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_update_performed": False,
            "production_status": "NO_GO",
            "m21_adoption_digest_sha256": (
                EXPECTED_M21_ADOPTION_DIGEST
            ),
            "m21_result_digest_sha256": (
                EXPECTED_M21_RESULT_DIGEST
            ),
            "failure_chain_digest_sha256": (
                failure_chain[
                    "failure_chain_digest_sha256"
                ]
            ),
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

        for path in [
            FAILURE_CHAIN,
            ROLLBACK,
            SCOPED_CSS,
            RENDERED_HTML,
            UPDATE_PAYLOAD,
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2"
            ),
            "status": (
                "PASS_WORDPRESS_RENDERED_LAYOUT_CORRECTION_"
                "RESULT_SCHEMA_FIXED_DOM_VALIDATED_UPDATE_"
                "PAYLOAD_GENERATED_LOCAL_ONLY_NON_EXECUTABLE_"
                "NO_WORDPRESS_ACCESS"
            ),
            "decision": (
                "M22_FIX1_SCHEMA_MISMATCH_RECORDED_"
                "CANONICAL_RESULT_FIELD_FIXED_RENDERED_"
                "UPDATE_PAYLOAD_READY_FOR_HUMAN_REVIEW"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "previous_m22_failure_recorded": True,
            "previous_m22_fix1_failure_recorded": True,
            "previous_m22_failure_classification": (
                "STYLE_ELEMENT_TEXT_FALSE_POSITIVE"
            ),
            "previous_m22_fix1_failure_classification": (
                "RESULT_SCHEMA_FIELD_NAME_MISMATCH"
            ),
            "previous_m22_temporary_result_adopted": False,
            "previous_m22_fix1_temporary_result_adopted": False,
            "previous_m22_rerun_performed": False,
            "previous_m22_fix1_rerun_performed": False,
            "canonical_result_field_name": (
                "previous_m22_rerun_performed"
            ),
            "deprecated_result_field_name": (
                "original_m22_rerun_performed"
            ),
            "deprecated_result_field_present": False,
            "result_schema_fixed": True,
            "validator_type": "HTMLPARSER_DOM_ONLY",
            "style_element_text_ignored": True,
            "plain_string_index_order_validation_used": False,
            "dom_root_count": root_count,
            "dom_event_order_verified": dom_events,
            "desktop_css_order_verified": True,
            "failure_chain_path": str(
                FAILURE_CHAIN.relative_to(ROOT)
            ),
            "failure_chain_digest_sha256": (
                failure_chain[
                    "failure_chain_digest_sha256"
                ]
            ),
            "current_content_html_sha256": (
                current_content_sha
            ),
            "rendered_content_html_sha256": (
                rendered_content_sha
            ),
            "scoped_css_sha256": css_sha,
            "rollback_path": str(
                ROLLBACK.relative_to(ROOT)
            ),
            "rollback_evidence_digest_sha256": (
                rollback[
                    "rollback_evidence_digest_sha256"
                ]
            ),
            "scoped_css_path": str(
                SCOPED_CSS.relative_to(ROOT)
            ),
            "rendered_html_path": str(
                RENDERED_HTML.relative_to(ROOT)
            ),
            "update_payload_path": str(
                UPDATE_PAYLOAD.relative_to(ROOT)
            ),
            "update_payload_digest_sha256": (
                update_payload[
                    "update_payload_digest_sha256"
                ]
            ),
            "rendered_content_generated": True,
            "scoped_css_generated": True,
            "rollback_content_evidence_generated": True,
            "non_executable_update_payload_generated": True,
            "allowed_update_fields": [
                "content",
                "comment_status",
            ],
            "comment_status_target": "closed",
            "title_field_in_request": False,
            "status_field_in_request": False,
            "categories_field_in_request": False,
            "store_url_multiset_preserved": True,
            "store_button_html_preserved": True,
            "amazon_state_preserved": True,
            "rakuten_kobo_state_preserved": True,
            "dmm_active_anchor_preserved": True,
            "dmm_url_fingerprint_sha256": (
                text_sha(dmm_href)
            ),
            "new_external_url_added": False,
            "pr_disclosure_before_first_store_interaction": True,
            "responsive_detail_card_generated": True,
            "source_artifacts_modified": False,
            "full_rendered_content_output": False,
            "full_update_payload_output": False,
            "full_store_url_output": False,
            "affiliate_identifier_output": False,
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
                "RESULT_SCHEMA_FIXED_DOM_VALIDATED_"
                "RENDERED_UPDATE_PAYLOAD_AWAITING_HUMAN_"
                "REVIEW_NO_WORDPRESS_UPDATE"
            ),
            "ready_for_rendered_update_payload_human_review": True,
            "ready_for_wordpress_update_authorization_gate": False,
            "ready_for_wordpress_update": False,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        require(
            "original_m22_rerun_performed"
            not in result_without_digest,
            "DEPRECATED_RESULT_FIELD_PRESENT",
        )
        require(
            result_without_digest[
                "previous_m22_rerun_performed"
            ] is False,
            "CANONICAL_RERUN_FIELD_NOT_FALSE",
        )

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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- WordPress post ID: `192`
- M22 failure recorded: `true`
- M22-FIX1 failure recorded: `true`
- M22-FIX1 failure classification: `RESULT_SCHEMA_FIELD_NAME_MISMATCH`
- Canonical result field: `previous_m22_rerun_performed`
- Deprecated result field present: `false`
- Previous M22 rerun performed: `false`
- Previous M22-FIX1 rerun performed: `false`
- Validator type: `HTMLPARSER_DOM_ONLY`
- Style text ignored: `true`
- DOM event order verified: `{", ".join(dom_events)}`
- Desktop CSS order verified: `true`
- Current content SHA-256: `{current_content_sha}`
- Rendered content SHA-256: `{rendered_content_sha}`
- Scoped CSS SHA-256: `{css_sha}`
- Allowed update fields: `content, comment_status`
- Comment status target: `closed`
- Store URL multiset preserved: `true`
- PR disclosure before store interaction: `true`
- Network connection performed: `false`
- WordPress access performed: `false`
- WordPress update performed: `false`
- Authorization issued: `false`
- Execution allowed: `false`
- Production status: `NO_GO`
- Ready for rendered update payload human review: `true`
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M22-FIX2"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_RENDERED_LAYOUT_"
                        "CORRECTION_RESULT_SCHEMA_FIX_"
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
