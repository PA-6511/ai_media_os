#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import html
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_post_injection_article_"
    "review_and_payload_authorization_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m10_gate_approval.json"
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
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m10_"
    "post_injection_review_and_payload_"
    "authorization_report.md"
)

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
SECRET_LINK = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
)
M9_FIX1_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_fix1_authorization.json"
)
M9_FIX1_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_fix1_consumption.json"
)
M9_FIX1_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m9_fix1_result.json"
)
OLD_M9_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_authorization.json"
)
OLD_M9_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_consumption.json"
)
OLD_M9_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m9_result.json"
)
M8_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_human_review.json"
)
M7_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_consumption.json"
)
M6_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_authorization.json"
)
M5_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_historical_m4_evidence_human_review.json"
)
CRED1_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m6_cred1_result.json"
)
CATEGORY_MAPPING = ROOT / (
    "config/"
    "new_release_wp_production_category_mapping.json"
)
CREDENTIAL_FILE = Path(
    "/etc/ai-media-os/credential.env"
)

EXPECTED_ARTICLE_POST_SHA = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
EXPECTED_ARTICLE_PRE_SHA = (
    "849a37519c6af70d2212ec01d5cddef5"
    "793bfa811e97ca9f248ce099a0350bf4"
)
EXPECTED_M9_FIX1_RESULT_DIGEST = (
    "a0ea1c29b1c653139db4b6bfa51a96ef"
    "79e574f3d519ad543c6a8988bc0854d6"
)
EXPECTED_M9_FIX1_CONSUMPTION_DIGEST = (
    "d798a6b22539964f260105a41bd412d2b"
    "8959ee65f61b28eb79faae9a25885d9"
)
EXPECTED_M9_FIX1_AUTH_DIGEST = (
    "c25ddfa1023038f057ef0d403a00ffe14"
    "43f15097f8fc89c6402c7113d37b630"
)
EXPECTED_M8_REVIEW_DIGEST = (
    "764fa0e5b3eea9cd09369995c78b6b05"
    "98c66aca17f66f80e3391d4654d932a4"
)
EXPECTED_M7_LINK_FILE_SHA = (
    "c5a70d9804a4e2dfd91049ee20bdda53"
    "79abf3e1fe3c25b0fb8cbd5fa587faa0"
)
EXPECTED_M7_LINK_DIGEST = (
    "4807e0a6d8a8416a936bafa978ba4f90"
    "d43ae7d304322bbd6a6ababcb2cd2db6"
)
EXPECTED_M7_CONSUMPTION_DIGEST = (
    "9d6a8ba944747d1df2d039075a2f511f"
    "df88215a81cc4b867c9d184313b0efcc"
)
EXPECTED_M6_AUTH_DIGEST = (
    "0607dd3774aa592369a1a22ac2692372"
    "ad57d70fe3a70d5eee387d47a27ec3f5"
)
EXPECTED_M5_REVIEW_DIGEST = (
    "92c59e79b7f8ff9b3dae934d1912f524"
    "9ccd4ce0c754cb5a5070e0b8264be892"
)
EXPECTED_CRED1_RESULT_DIGEST = (
    "7a173b74bef53781a3b2fe2e2cc2d3f3"
    "63a096b937508c241d454311d072ec7e"
)
EXPECTED_PRODUCT_URL = (
    "https://book.dmm.com/product/"
    "861056/b950yshes32617/"
)

CRED1_CONTEXT = (
    b"LS-NEW-BATCH-4G-2E-RECOVERY-M6-CRED1"
    b"\x00DMM_AFFILIATE_ID\x00"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

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
        digest(comparable) == stored,
        f"DIGEST_VERIFICATION_FAILED:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"EXPECTED_DIGEST_MISMATCH:{field}",
        )

    return stored


def write_json(
    path: Path,
    value: dict[str, Any],
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

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_text(
    path: Path,
    value: str,
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

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def read_identifier() -> str:
    require(
        CREDENTIAL_FILE.exists(),
        "CREDENTIAL_FILE_MISSING",
    )
    require(
        not CREDENTIAL_FILE.is_symlink(),
        "CREDENTIAL_FILE_SYMLINK_REJECTED",
    )
    require(
        stat.S_IMODE(
            CREDENTIAL_FILE.stat().st_mode
        ) == 0o600,
        "CREDENTIAL_FILE_MODE_NOT_0600",
    )
    require(
        CREDENTIAL_FILE.stat().st_uid
        == os.geteuid(),
        "CREDENTIAL_FILE_OWNER_MISMATCH",
    )

    matches: list[str] = []

    for raw_line in CREDENTIAL_FILE.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        key, separator, raw_value = (
            line.partition("=")
        )

        if (
            separator == "="
            and key.strip()
            == "DMM_AFFILIATE_ID"
        ):
            value = raw_value.strip()

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]

            matches.append(value)

    require(
        len(matches) == 1,
        "DMM_IDENTIFIER_KEY_COUNT_MUST_BE_ONE",
    )

    identifier = matches[0]

    require(
        re.fullmatch(
            r"[A-Za-z0-9]+-[0-9]{3}",
            identifier,
        ) is not None,
        "DMM_IDENTIFIER_FORMAT_INVALID",
    )

    return identifier


def verify_commitment(
    identifier: str,
    cred1: dict[str, Any],
) -> None:
    commitment = cred1[
        "identifier_commitment"
    ]

    calculated = hashlib.pbkdf2_hmac(
        "sha256",
        identifier.encode("utf-8"),
        (
            CRED1_CONTEXT
            + bytes.fromhex(
                commitment["salt_hex"]
            )
        ),
        commitment["iterations"],
    ).hex()

    require(
        calculated
        == commitment["commitment_hex"],
        "CRED1_COMMITMENT_MISMATCH",
    )


def validate_final_url(
    final_url: str,
    identifier: str,
) -> None:
    parsed = urlsplit(final_url)

    require(
        parsed.scheme == "https",
        "FINAL_URL_SCHEME_INVALID",
    )
    require(
        parsed.hostname == "al.dmm.com",
        "FINAL_URL_HOST_INVALID",
    )
    require(
        parsed.port is None,
        "FINAL_URL_PORT_REJECTED",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "FINAL_URL_USERINFO_REJECTED",
    )
    require(
        parsed.path == "/",
        "FINAL_URL_PATH_INVALID",
    )
    require(
        parsed.fragment == "",
        "FINAL_URL_FRAGMENT_REJECTED",
    )

    pairs = parse_qsl(
        parsed.query,
        keep_blank_values=True,
        strict_parsing=True,
    )

    require(
        pairs == [
            (
                "lurl",
                EXPECTED_PRODUCT_URL,
            ),
            ("af_id", identifier),
            ("ch", "link_tool"),
            ("ch_id", "link"),
        ],
        "FINAL_URL_QUERY_BINDING_MISMATCH",
    )


class DmmAnchorInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.stack: list[dict[str, Any]] = []
        self.matches: list[dict[str, Any]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        attr_map = {
            name.casefold(): (
                ""
                if value is None
                else value
            )
            for name, value in attrs
        }

        self.stack.append(
            {
                "tag": tag.casefold(),
                "attrs": attr_map,
                "text": [],
            }
        )

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self.stack:
            self.stack[-1]["text"].append(
                data
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if not self.stack:
            return

        node = self.stack.pop()

        if node["tag"] != tag.casefold():
            return

        classes = set(
            node["attrs"].get(
                "class",
                "",
            ).split()
        )

        if (
            node["tag"] == "a"
            and "ls-store-dmm" in classes
        ):
            self.matches.append(
                {
                    "class_tokens": classes,
                    "href": html.unescape(
                        node["attrs"].get(
                            "href",
                            "",
                        )
                    ),
                    "target": node[
                        "attrs"
                    ].get("target"),
                    "rel_tokens": set(
                        node["attrs"].get(
                            "rel",
                            "",
                        ).split()
                    ),
                    "aria_disabled_present": (
                        "aria-disabled"
                        in node["attrs"]
                    ),
                    "text": re.sub(
                        r"\s+",
                        " ",
                        "".join(node["text"]),
                    ).strip(),
                }
            )

        if self.stack:
            self.stack[-1]["text"].extend(
                node["text"]
            )


def reconstruct_preimage(
    article: dict[str, Any],
    final_url: str,
) -> dict[str, Any]:
    reconstructed = copy.deepcopy(
        article
    )

    current_html = reconstructed[
        "content_html"
    ]

    encoded_url = html.escape(
        final_url,
        quote=True,
    )

    active_anchor = (
        '<a class="ls-store-btn ls-store-dmm" '
        f'href="{encoded_url}" '
        'target="_blank" '
        'rel="nofollow sponsored noopener">'
        'DMMブックスで確認</a>'
    )

    reserved_span = (
        '<span class="ls-store-btn '
        'ls-store-dmm ls-store-disabled" '
        'aria-disabled="true">'
        'DMMブックスで確認（再確認待ち）'
        '</span>'
    )

    require(
        current_html.count(
            active_anchor
        ) == 1,
        "ACTIVE_DMM_ANCHOR_SERIALIZATION_MISMATCH",
    )

    reconstructed["content_html"] = (
        current_html.replace(
            active_anchor,
            reserved_span,
            1,
        )
    )

    navigation = reconstructed[
        "store_navigation"
    ]

    navigation[
        "render_mode"
    ] = "RESERVED_NON_CLICKABLE_SLOTS_ONLY"
    navigation[
        "anchor_elements_included"
    ] = False
    navigation[
        "href_attributes_included"
    ] = False
    navigation[
        "final_affiliate_urls_included"
    ] = False
    navigation[
        "dmm_url_included"
    ] = False

    return reconstructed


def main() -> int:
    try:
        for output in [
            REVIEW,
            AUTHORIZATION,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M10_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load(POLICY)
        approval = load(APPROVAL)

        approval_digest = verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M10"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["execution_boundary"][
                "fresh_payload_generation_allowed"
            ] is False,
            "PAYLOAD_GENERATION_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "article_modification_allowed"
            ] is False,
            "ARTICLE_MODIFICATION_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "network_connection_allowed"
            ] is False,
            "NETWORK_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "wordpress_access_allowed"
            ] is False,
            "WORDPRESS_BOUNDARY_OPEN",
        )

        source_paths = {
            "article": ARTICLE,
            "secret_link": SECRET_LINK,
            "m9_fix1_authorization": (
                M9_FIX1_AUTH
            ),
            "m9_fix1_consumption": (
                M9_FIX1_CONSUMPTION
            ),
            "m9_fix1_result": (
                M9_FIX1_RESULT
            ),
            "old_m9_authorization": (
                OLD_M9_AUTH
            ),
            "old_m9_consumption": (
                OLD_M9_CONSUMPTION
            ),
            "old_m9_result": (
                OLD_M9_RESULT
            ),
            "m8_review": M8_REVIEW,
            "m7_consumption": (
                M7_CONSUMPTION
            ),
            "m6_authorization": M6_AUTH,
            "m5_review": M5_REVIEW,
            "cred1_result": CRED1_RESULT,
            "category_mapping": (
                CATEGORY_MAPPING
            ),
        }

        source_hashes_before = {
            name: file_sha(path)
            for name, path
            in source_paths.items()
        }

        require(
            source_hashes_before["article"]
            == EXPECTED_ARTICLE_POST_SHA,
            "ARTICLE_POSTIMAGE_SHA_MISMATCH",
        )
        require(
            source_hashes_before["secret_link"]
            == EXPECTED_M7_LINK_FILE_SHA,
            "SECRET_LINK_FILE_SHA_MISMATCH",
        )
        require(
            stat.S_IMODE(
                SECRET_LINK.stat().st_mode
            ) == 0o600,
            "SECRET_LINK_MODE_NOT_0600",
        )
        require(
            not SECRET_LINK.is_symlink(),
            "SECRET_LINK_SYMLINK_REJECTED",
        )

        article = load(ARTICLE)
        secret_link = load(SECRET_LINK)
        m9_fix1_auth = load(
            M9_FIX1_AUTH
        )
        m9_fix1_consumption = load(
            M9_FIX1_CONSUMPTION
        )
        m9_fix1_result = load(
            M9_FIX1_RESULT
        )
        old_m9_consumption = load(
            OLD_M9_CONSUMPTION
        )
        old_m9_result = load(
            OLD_M9_RESULT
        )
        m8_review = load(M8_REVIEW)
        m7_consumption = load(
            M7_CONSUMPTION
        )
        m6_auth = load(M6_AUTH)
        m5_review = load(M5_REVIEW)
        cred1 = load(CRED1_RESULT)
        category_mapping = load(
            CATEGORY_MAPPING
        )

        verify_digest(
            m9_fix1_auth,
            "authorization_digest_sha256",
            EXPECTED_M9_FIX1_AUTH_DIGEST,
        )
        verify_digest(
            m9_fix1_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M9_FIX1_CONSUMPTION_DIGEST,
        )
        verify_digest(
            m9_fix1_result,
            "result_digest_sha256",
            EXPECTED_M9_FIX1_RESULT_DIGEST,
        )
        verify_digest(
            old_m9_consumption,
            "consumption_evidence_digest_sha256",
        )
        verify_digest(
            old_m9_result,
            "result_digest_sha256",
        )
        verify_digest(
            m8_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M8_REVIEW_DIGEST,
        )
        verify_digest(
            secret_link,
            "secret_artifact_digest_sha256",
            EXPECTED_M7_LINK_DIGEST,
        )
        verify_digest(
            m7_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M7_CONSUMPTION_DIGEST,
        )
        verify_digest(
            m6_auth,
            "authorization_digest_sha256",
            EXPECTED_M6_AUTH_DIGEST,
        )
        verify_digest(
            m5_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M5_REVIEW_DIGEST,
        )
        verify_digest(
            cred1,
            "result_digest_sha256",
            EXPECTED_CRED1_RESULT_DIGEST,
        )

        require(
            m9_fix1_result["status"]
            == (
                "PASS_DMM_ARTICLE_LINK_INJECTED_"
                "HTML_ENTITY_VALIDATOR_FIXED_"
                "NEW_AUTHORIZATION_CONSUMED_"
                "NO_NETWORK_NO_WORDPRESS"
            ),
            "M9_FIX1_STATUS_MISMATCH",
        )
        require(
            m9_fix1_result[
                "article_postimage_sha256"
            ]
            == EXPECTED_ARTICLE_POST_SHA,
            "M9_FIX1_ARTICLE_POSTIMAGE_BINDING_MISMATCH",
        )
        require(
            m9_fix1_consumption[
                "authorization_consumed"
            ] is True,
            "M9_FIX1_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            old_m9_consumption[
                "authorization_consumed"
            ] is True,
            "OLD_M9_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            old_m9_result["status"]
            == (
                "FAILED_AFTER_M9_AUTHORIZATION_"
                "CONSUMPTION_NO_AUTOMATIC_RETRY"
            ),
            "OLD_M9_FAILURE_STATUS_CHANGED",
        )

        identifier = read_identifier()
        verify_commitment(
            identifier,
            cred1,
        )

        final_url = secret_link[
            "final_affiliate_url"
        ]

        validate_final_url(
            final_url,
            identifier,
        )

        content_html = article.get(
            "content_html"
        )

        require(
            isinstance(content_html, str),
            "CONTENT_HTML_MISSING",
        )

        inspector = DmmAnchorInspector()
        inspector.feed(content_html)
        inspector.close()

        require(
            len(inspector.matches) == 1,
            "DMM_ACTIVE_ANCHOR_COUNT_MUST_BE_ONE",
        )

        anchor = inspector.matches[0]

        require(
            anchor["class_tokens"]
            == {
                "ls-store-btn",
                "ls-store-dmm",
            },
            "DMM_ANCHOR_CLASS_TOKENS_MISMATCH",
        )
        require(
            anchor["text"]
            == "DMMブックスで確認",
            "DMM_ANCHOR_TEXT_MISMATCH",
        )
        require(
            anchor["target"] == "_blank",
            "DMM_ANCHOR_TARGET_MISMATCH",
        )
        require(
            anchor["rel_tokens"]
            == {
                "nofollow",
                "sponsored",
                "noopener",
            },
            "DMM_ANCHOR_REL_TOKENS_MISMATCH",
        )
        require(
            anchor[
                "aria_disabled_present"
            ] is False,
            "DMM_ANCHOR_ARIA_DISABLED_PRESENT",
        )
        require(
            anchor["href"] == final_url,
            "DMM_ANCHOR_DECODED_HREF_MISMATCH",
        )

        navigation = article.get(
            "store_navigation"
        )

        require(
            isinstance(navigation, dict),
            "STORE_NAVIGATION_MISSING",
        )
        require(
            navigation.get("render_mode")
            == "PARTIAL_ACTIVE_STORE_LINKS",
            "STORE_NAVIGATION_RENDER_MODE_MISMATCH",
        )
        require(
            navigation.get(
                "anchor_elements_included"
            ) is True,
            "STORE_NAVIGATION_ANCHORS_MISMATCH",
        )
        require(
            navigation.get(
                "href_attributes_included"
            ) is True,
            "STORE_NAVIGATION_HREFS_MISMATCH",
        )
        require(
            navigation.get(
                "final_affiliate_urls_included"
            ) is True,
            "STORE_NAVIGATION_FINAL_URLS_MISMATCH",
        )
        require(
            navigation.get(
                "dmm_url_included"
            ) is True,
            "STORE_NAVIGATION_DMM_URL_MISMATCH",
        )

        reconstructed = reconstruct_preimage(
            article,
            final_url,
        )

        reconstructed_bytes = (
            json.dumps(
                reconstructed,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

        reconstructed_sha = hashlib.sha256(
            reconstructed_bytes
        ).hexdigest()

        require(
            reconstructed_sha
            == EXPECTED_ARTICLE_PRE_SHA,
            "ARTICLE_PREIMAGE_INVERSE_RECONSTRUCTION_MISMATCH",
        )

        require(
            "Amazonで確認（リンク準備中）"
            in reconstructed["content_html"],
            "AMAZON_SLOT_CHANGED",
        )
        require(
            "楽天Koboで確認（リンク準備中）"
            in reconstructed["content_html"],
            "RAKUTEN_KOBO_SLOT_CHANGED",
        )
        require(
            "【PR】本記事にはアフィリエイト広告を含みます。"
            in reconstructed["content_html"],
            "PR_DISCLOSURE_CHANGED",
        )

        mapping_text = json.dumps(
            category_mapping,
            ensure_ascii=False,
        )

        require(
            "COMIC_NEW_RELEASE_LATEST_VOLUME_TO_WP_CATEGORY_10"
            in mapping_text,
            "CATEGORY_MAPPING_ID_MISSING",
        )
        require(
            "最新巻" in mapping_text,
            "CATEGORY_NAME_MISSING",
        )

        source_bindings = {
            name: {
                "path": str(
                    path.relative_to(ROOT)
                ),
                "file_sha256": (
                    source_hashes_before[name]
                ),
            }
            for name, path
            in source_paths.items()
        }

        review_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M10"
            ),
            "document_role": (
                "POST_INJECTION_ARTICLE_"
                "HUMAN_REVIEW_EVIDENCE"
            ),
            "review_id": (
                "POST_INJECTION_ARTICLE_"
                "HUMAN_REVIEW_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "approval_label": (
                "DMM_POST_INJECTION_ARTICLE_"
                "HUMAN_REVIEW_AND_FRESH_PAYLOAD_"
                "AUTHORIZATION_GATE_APPROVED"
            ),
            "reviewed_by": "HUMAN_OPERATOR",
            "human_explicit_approval": True,
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "article_binding": {
                "path": str(
                    ARTICLE.relative_to(ROOT)
                ),
                "postimage_sha256": (
                    EXPECTED_ARTICLE_POST_SHA
                ),
                "preimage_sha256": (
                    EXPECTED_ARTICLE_PRE_SHA
                ),
                "inverse_reconstructed_preimage_sha256": (
                    reconstructed_sha
                )
            },
            "validation_results": {
                "dmm_active_anchor_count_one": True,
                "dmm_anchor_class_tokens_exact": True,
                "dmm_anchor_text_verified": True,
                "dmm_anchor_target_blank_verified": True,
                "dmm_anchor_rel_tokens_verified": True,
                "dmm_disabled_class_absent": True,
                "dmm_aria_disabled_absent": True,
                "decoded_href_exact_secret_link_match": True,
                "dmm_link_scheme_https_verified": True,
                "dmm_link_host_al_dmm_com_verified": True,
                "destination_exact_binding_verified": True,
                "registered_identifier_exact_binding_verified": True,
                "store_navigation_matches_html": True,
                "article_preimage_inverse_reconstruction_verified": True,
                "amazon_slot_unchanged": True,
                "rakuten_kobo_slot_unchanged": True,
                "pr_disclosure_unchanged": True,
                "non_dmm_structure_unchanged": True,
                "m9_fix1_result_verified": True,
                "m9_fix1_consumption_verified": True,
                "old_m9_failure_evidence_preserved": True,
                "m8_review_verified": True,
                "m7_secret_link_verified": True,
                "m7_consumption_verified": True,
                "m6_authorization_verified": True,
                "m5_review_verified": True,
                "cred1_commitment_revalidated": True
            },
            "secret_link_binding": {
                "path": str(
                    SECRET_LINK.relative_to(ROOT)
                ),
                "file_sha256": (
                    EXPECTED_M7_LINK_FILE_SHA
                ),
                "artifact_digest_sha256": (
                    EXPECTED_M7_LINK_DIGEST
                ),
                "full_final_url_present": False,
                "affiliate_identifier_present": False
            },
            "source_bindings": source_bindings,
            "full_final_affiliate_url_output": False,
            "affiliate_identifier_output": False,
            "article_modified": False,
            "payload_created": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "production_status": "NO_GO",
            "reviewed_at_utc": now()
        }

        review = copy.deepcopy(
            review_without_digest
        )
        review[
            "human_review_evidence_digest_sha256"
        ] = digest(review_without_digest)

        write_json(
            REVIEW,
            review,
        )

        authorization_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_PAYLOAD_GENERATION_"
                "ONE_SHOT_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M10"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorization_id": (
                "FRESH_PAYLOAD_GENERATION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "authorized_operation": (
                "ONE_SHOT_FRESH_WORDPRESS_"
                "DRAFT_PAYLOAD_GENERATION"
            ),
            "article_binding": {
                "path": str(
                    ARTICLE.relative_to(ROOT)
                ),
                "article_postimage_sha256": (
                    EXPECTED_ARTICLE_POST_SHA
                )
            },
            "post_injection_review_binding": {
                "path": str(
                    REVIEW.relative_to(ROOT)
                ),
                "review_verdict": (
                    "APPROVED_NO_CHANGE_REQUIRED"
                ),
                "review_digest_sha256": (
                    review[
                        "human_review_evidence_digest_sha256"
                    ]
                )
            },
            "secret_link_binding": {
                "path": str(
                    SECRET_LINK.relative_to(ROOT)
                ),
                "file_sha256": (
                    EXPECTED_M7_LINK_FILE_SHA
                ),
                "artifact_digest_sha256": (
                    EXPECTED_M7_LINK_DIGEST
                ),
                "full_final_url_present": False,
                "affiliate_identifier_present": False
            },
            "historical_bindings": {
                "m9_fix1_authorization_digest_sha256": (
                    EXPECTED_M9_FIX1_AUTH_DIGEST
                ),
                "m9_fix1_consumption_digest_sha256": (
                    EXPECTED_M9_FIX1_CONSUMPTION_DIGEST
                ),
                "m9_fix1_result_digest_sha256": (
                    EXPECTED_M9_FIX1_RESULT_DIGEST
                ),
                "m7_consumption_digest_sha256": (
                    EXPECTED_M7_CONSUMPTION_DIGEST
                ),
                "m6_authorization_digest_sha256": (
                    EXPECTED_M6_AUTH_DIGEST
                ),
                "m5_review_digest_sha256": (
                    EXPECTED_M5_REVIEW_DIGEST
                ),
                "cred1_result_digest_sha256": (
                    EXPECTED_CRED1_RESULT_DIGEST
                )
            },
            "payload_contract": {
                "template_id": (
                    "POST185_STANDARD_TEMPLATE_V1_FIXED"
                ),
                "category_mapping_id": (
                    "COMIC_NEW_RELEASE_LATEST_VOLUME_"
                    "TO_WP_CATEGORY_10"
                ),
                "category_id": 10,
                "category_name": "最新巻",
                "post_status": "draft",
                "publish_allowed": False,
                "article_content_must_match_bound_article": True,
                "payload_generation_offline_only": True
            },
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "actual_payload_generation_requires_execute_now_approval": True,
            "actual_payload_generation_allowed": False,
            "planned_execution_phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M11"
            ),
            "full_final_url_present": False,
            "affiliate_identifier_present": False,
            "article_modified": False,
            "payload_created": False,
            "category_id_injected": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "authorized_at_utc": now()
        }

        authorization = copy.deepcopy(
            authorization_without_digest
        )
        authorization[
            "authorization_digest_sha256"
        ] = digest(
            authorization_without_digest
        )

        write_json(
            AUTHORIZATION,
            authorization,
        )

        for name, path in (
            source_paths.items()
        ):
            require(
                file_sha(path)
                == source_hashes_before[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M10"
            ),
            "status": (
                "PASS_POST_INJECTION_ARTICLE_"
                "HUMAN_REVIEW_APPROVED_FRESH_"
                "PAYLOAD_AUTHORIZATION_FIXED_"
                "NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "POST_INJECTION_ARTICLE_APPROVED_"
                "FRESH_PAYLOAD_AUTHORIZATION_"
                "RECORDED_AWAITING_EXPLICIT_"
                "EXECUTE_NOW_CONFIRMATION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "review_path": str(
                REVIEW.relative_to(ROOT)
            ),
            "review_file_sha256": (
                file_sha(REVIEW)
            ),
            "review_digest_sha256": (
                review[
                    "human_review_evidence_digest_sha256"
                ]
            ),
            "authorization_path": str(
                AUTHORIZATION.relative_to(ROOT)
            ),
            "authorization_file_sha256": (
                file_sha(AUTHORIZATION)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "authorization_id": (
                authorization[
                    "authorization_id"
                ]
            ),
            "authorization_single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "article_postimage_sha256_verified": True,
            "article_preimage_inverse_reconstruction_verified": True,
            "non_dmm_structure_unchanged": True,
            "dmm_anchor_verified": True,
            "decoded_href_exact_binding_verified": True,
            "store_navigation_verified": True,
            "category_mapping_verified": True,
            "template_id_fixed": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "category_mapping_id_fixed": (
                "COMIC_NEW_RELEASE_LATEST_VOLUME_"
                "TO_WP_CATEGORY_10"
            ),
            "category_id_fixed": 10,
            "category_name_fixed": "最新巻",
            "full_final_affiliate_url_output": False,
            "affiliate_identifier_output": False,
            "article_modified": False,
            "payload_created": False,
            "category_id_injected": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "POST_INJECTION_REVIEW_APPROVED_"
                "PAYLOAD_AUTHORIZATION_UNCONSUMED_"
                "AWAITING_EXECUTE_NOW_APPROVAL"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m11": True,
            "ready_for_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "completed_at_utc": now()
        }

        result = copy.deepcopy(
            result_without_digest
        )
        result[
            "result_digest_sha256"
        ] = digest(result_without_digest)

        write_json(
            RESULT,
            result,
        )

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M10

- Status: `{result["status"]}`
- Review verdict: `APPROVED_NO_CHANGE_REQUIRED`
- Article postimage SHA verified: `true`
- Article preimage inverse reconstruction verified: `true`
- Non-DMM structure unchanged: `true`
- DMM active anchor verified: `true`
- Decoded href exact binding verified: `true`
- Store navigation verified: `true`
- Category mapping ID: `COMIC_NEW_RELEASE_LATEST_VOLUME_TO_WP_CATEGORY_10`
- Category ID: `10`
- Category name: `最新巻`
- Template ID: `POST185_STANDARD_TEMPLATE_V1_FIXED`
- Payload authorization single use: `true`
- Payload authorization consumed: `false`
- Payload authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- Full final URL output: `false`
- Affiliate identifier output: `false`
- Article modified: `false`
- Payload created: `false`
- Network accessed: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for M11 execute-now gate: `true`
""",
        )

        del identifier
        del final_url

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
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M10"
                    ),
                    "status": (
                        "BLOCKED_POST_INJECTION_"
                        "ARTICLE_HUMAN_REVIEW_AND_"
                        "FRESH_PAYLOAD_AUTHORIZATION_GATE"
                    ),
                    "error_code": str(exc),
                    "review_approved": False,
                    "authorization_created": False,
                    "full_final_affiliate_url_output": False,
                    "affiliate_identifier_output": False,
                    "article_modified": False,
                    "payload_created": False,
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
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
