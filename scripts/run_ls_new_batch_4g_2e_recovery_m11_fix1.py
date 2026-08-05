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
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_payload_article_title_"
    "field_validator_fix_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m11_fix1_approval.json"
)
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
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m11_fix1_"
    "fresh_payload_generation_report.md"
)

M10_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "fresh_payload_generation_authorization.json"
)
M10_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "post_injection_article_human_review.json"
)
M10_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m10_result.json"
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
SECRET_LINK = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
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

EXPECTED_ARTICLE_SHA = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
)
EXPECTED_M10_AUTH_DIGEST = (
    "fed0e3c217c654f5e9803f750fd1d072"
    "69bff3eed4917a58638e61c9b571bc5b"
)
EXPECTED_M10_REVIEW_DIGEST = (
    "48b567388d071a89f82a63504c60fd57"
    "67ddd328db23c7a9df73f16b848ebbae"
)
EXPECTED_M10_RESULT_DIGEST = (
    "733aaac441e27498fb99aa86256b2844"
    "e2654f3b82e89d111937343599ac5f3e"
)
EXPECTED_M9_FIX1_AUTH_DIGEST = (
    "c25ddfa1023038f057ef0d403a00ffe1"
    "443f15097f8fc89c6402c7113d37b630"
)
EXPECTED_M9_FIX1_CONSUMPTION_DIGEST = (
    "d798a6b22539964f260105a41bd412d2"
    "b8959ee65f61b28eb79faae9a25885d9"
)
EXPECTED_M9_FIX1_RESULT_DIGEST = (
    "a0ea1c29b1c653139db4b6bfa51a96e"
    "f79e574f3d519ad543c6a8988bc0854d6"
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
EXPECTED_CRED1_DIGEST = (
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_text(path: Path, value: str) -> None:
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
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

    values: list[str] = []

    for raw_line in CREDENTIAL_FILE.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        key, separator, raw_value = line.partition("=")

        if (
            separator == "="
            and key.strip() == "DMM_AFFILIATE_ID"
        ):
            value = raw_value.strip()

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]

            values.append(value)

    require(
        len(values) == 1,
        "DMM_IDENTIFIER_KEY_COUNT_MUST_BE_ONE",
    )

    identifier = values[0]

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
    commitment = cred1["identifier_commitment"]

    calculated = hashlib.pbkdf2_hmac(
        "sha256",
        identifier.encode("utf-8"),
        (
            CRED1_CONTEXT
            + bytes.fromhex(commitment["salt_hex"])
        ),
        commitment["iterations"],
    ).hex()

    require(
        calculated == commitment["commitment_hex"],
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
            ("lurl", EXPECTED_PRODUCT_URL),
            ("af_id", identifier),
            ("ch", "link_tool"),
            ("ch_id", "link"),
        ],
        "FINAL_URL_QUERY_BINDING_MISMATCH",
    )


class DmmAnchorInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, Any]] = []
        self.matches: list[dict[str, Any]] = []

    def handle_starttag(self, tag, attrs) -> None:
        attr_map = {
            name.casefold(): (
                "" if value is None else value
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

    def handle_data(self, data: str) -> None:
        if self.stack:
            self.stack[-1]["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return

        node = self.stack.pop()

        if node["tag"] != tag.casefold():
            return

        classes = set(
            node["attrs"].get("class", "").split()
        )

        if (
            node["tag"] == "a"
            and "ls-store-dmm" in classes
        ):
            self.matches.append(
                {
                    "classes": classes,
                    "href": html.unescape(
                        node["attrs"].get("href", "")
                    ),
                    "target": node["attrs"].get("target"),
                    "rel": set(
                        node["attrs"].get("rel", "").split()
                    ),
                    "aria_disabled": (
                        "aria-disabled" in node["attrs"]
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


def validate_payload(
    payload: dict[str, Any],
    article: dict[str, Any],
    final_url: str,
    identifier: str,
) -> None:
    require(
        payload["title"] == article["article_title"],
        "PAYLOAD_TITLE_NOT_EXACT_ARTICLE_TITLE",
    )
    require(
        payload["title"] == EXPECTED_TITLE,
        "PAYLOAD_TITLE_MISMATCH",
    )
    require(
        payload["content_item_id"]
        == "new-release-comic-20260703-001",
        "PAYLOAD_CONTENT_ITEM_ID_MISMATCH",
    )
    require(
        payload["content_html"]
        == article["content_html"],
        "PAYLOAD_CONTENT_HTML_MISMATCH",
    )
    require(
        payload["post_status"] == "draft",
        "PAYLOAD_POST_STATUS_MISMATCH",
    )
    require(
        payload["status"] == "draft",
        "PAYLOAD_STATUS_MISMATCH",
    )
    require(
        payload["publish"] is False,
        "PAYLOAD_PUBLISH_FLAG_MISMATCH",
    )
    require(
        payload["template_id"]
        == "POST185_STANDARD_TEMPLATE_V1_FIXED",
        "PAYLOAD_TEMPLATE_ID_MISMATCH",
    )
    require(
        payload["category_mapping_id"]
        == (
            "COMIC_NEW_RELEASE_LATEST_VOLUME_"
            "TO_WP_CATEGORY_10"
        ),
        "PAYLOAD_CATEGORY_MAPPING_MISMATCH",
    )
    require(
        payload["category_id"] == 10,
        "PAYLOAD_CATEGORY_ID_MISMATCH",
    )
    require(
        payload["categories"] == [10],
        "PAYLOAD_CATEGORIES_MISMATCH",
    )
    require(
        payload["category_name"] == "最新巻",
        "PAYLOAD_CATEGORY_NAME_MISMATCH",
    )

    inspector = DmmAnchorInspector()
    inspector.feed(payload["content_html"])
    inspector.close()

    require(
        len(inspector.matches) == 1,
        "PAYLOAD_DMM_ANCHOR_COUNT_MUST_BE_ONE",
    )

    anchor = inspector.matches[0]

    require(
        anchor["classes"]
        == {"ls-store-btn", "ls-store-dmm"},
        "PAYLOAD_DMM_CLASS_MISMATCH",
    )
    require(
        anchor["text"] == "DMMブックスで確認",
        "PAYLOAD_DMM_TEXT_MISMATCH",
    )
    require(
        anchor["target"] == "_blank",
        "PAYLOAD_DMM_TARGET_MISMATCH",
    )
    require(
        anchor["rel"]
        == {"nofollow", "sponsored", "noopener"},
        "PAYLOAD_DMM_REL_MISMATCH",
    )
    require(
        anchor["aria_disabled"] is False,
        "PAYLOAD_DMM_ARIA_DISABLED_PRESENT",
    )
    require(
        anchor["href"] == final_url,
        "PAYLOAD_DMM_HREF_MISMATCH",
    )

    validate_final_url(
        anchor["href"],
        identifier,
    )


def main() -> int:
    boundary_crossed = False

    try:
        for output in [
            PAYLOAD,
            CONSUMPTION,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load(POLICY)
        approval = load(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M11-FIX1",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            file_sha(ARTICLE) == EXPECTED_ARTICLE_SHA,
            "ARTICLE_SHA_MISMATCH",
        )
        require(
            file_sha(SECRET_LINK)
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

        source_paths = {
            "article": ARTICLE,
            "m10_auth": M10_AUTH,
            "m10_review": M10_REVIEW,
            "m10_result": M10_RESULT,
            "m9_fix1_auth": M9_FIX1_AUTH,
            "m9_fix1_consumption": (
                M9_FIX1_CONSUMPTION
            ),
            "m9_fix1_result": M9_FIX1_RESULT,
            "secret_link": SECRET_LINK,
            "m7_consumption": M7_CONSUMPTION,
            "m6_auth": M6_AUTH,
            "m5_review": M5_REVIEW,
            "cred1_result": CRED1_RESULT,
            "category_mapping": CATEGORY_MAPPING,
        }

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        article = load(ARTICLE)
        m10_auth = load(M10_AUTH)
        m10_review = load(M10_REVIEW)
        m10_result = load(M10_RESULT)
        m9_fix1_auth = load(M9_FIX1_AUTH)
        m9_fix1_consumption = load(
            M9_FIX1_CONSUMPTION
        )
        m9_fix1_result = load(M9_FIX1_RESULT)
        secret_link = load(SECRET_LINK)
        m7_consumption = load(M7_CONSUMPTION)
        m6_auth = load(M6_AUTH)
        m5_review = load(M5_REVIEW)
        cred1 = load(CRED1_RESULT)
        category_mapping = load(CATEGORY_MAPPING)

        verify_digest(
            m10_auth,
            "authorization_digest_sha256",
            EXPECTED_M10_AUTH_DIGEST,
        )
        verify_digest(
            m10_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M10_REVIEW_DIGEST,
        )
        verify_digest(
            m10_result,
            "result_digest_sha256",
            EXPECTED_M10_RESULT_DIGEST,
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
            EXPECTED_CRED1_DIGEST,
        )

        require(
            "title" not in article,
            "ROOT_TITLE_KEY_MUST_BE_ABSENT",
        )
        require(
            article.get("article_title")
            == EXPECTED_TITLE,
            "ARTICLE_TITLE_FIELD_MISMATCH",
        )
        require(
            isinstance(article.get("content_html"), str),
            "ARTICLE_CONTENT_HTML_MISSING",
        )

        require(
            m10_auth["authorization_id"]
            == (
                "FRESH_PAYLOAD_GENERATION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "M10_AUTHORIZATION_ID_MISMATCH",
        )
        require(
            m10_auth["single_use"] is True,
            "M10_AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            m10_auth["authorization_consumed"]
            is False,
            "M10_AUTHORIZATION_ALREADY_CONSUMED",
        )
        require(
            m10_auth["authorization_reuse_allowed"]
            is False,
            "M10_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m10_auth["automatic_retry_allowed"]
            is False,
            "M10_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m10_auth["automatic_reissue_allowed"]
            is False,
            "M10_AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            m10_review["review_verdict"]
            == "APPROVED_NO_CHANGE_REQUIRED",
            "M10_REVIEW_VERDICT_MISMATCH",
        )
        require(
            m10_result[
                "ready_for_ls_new_batch_4g_2e_recovery_m11"
            ] is True,
            "M10_NOT_READY_FOR_M11",
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

        identifier = read_identifier()
        verify_commitment(identifier, cred1)

        final_url = secret_link["final_affiliate_url"]
        validate_final_url(final_url, identifier)

        attempt_id = str(uuid.uuid4())

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_PAYLOAD_GENERATION_"
                "AUTHORIZATION_CONSUMPTION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M11-FIX1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "source_authorization_id": (
                m10_auth["authorization_id"]
            ),
            "source_authorization_digest_sha256": (
                EXPECTED_M10_AUTH_DIGEST
            ),
            "authorization_consumed": True,
            "execution_boundary_crossed": True,
            "consumed_before_payload_generation": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "article_sha256": EXPECTED_ARTICLE_SHA,
            "formal_title_source_field": "article_title",
            "full_payload_present": False,
            "full_final_url_present": False,
            "affiliate_identifier_present": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "consumed_at_utc": now()
        }

        consumption = copy.deepcopy(
            consumption_without_digest
        )
        consumption[
            "consumption_evidence_digest_sha256"
        ] = digest(consumption_without_digest)

        write_json(CONSUMPTION, consumption)
        boundary_crossed = True

        payload_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "WORDPRESS_DRAFT_FRESH_PAYLOAD"
            ),
            "sensitivity": (
                "CONTAINS_AFFILIATE_LINK_MODE_0600"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M11-FIX1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "title": article["article_title"],
            "title_source_field": "article_title",
            "content_html": article["content_html"],
            "post_status": "draft",
            "status": "draft",
            "publish": False,
            "template_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "category_mapping_id": (
                "COMIC_NEW_RELEASE_LATEST_VOLUME_"
                "TO_WP_CATEGORY_10"
            ),
            "category_id": 10,
            "categories": [10],
            "category_name": "最新巻",
            "article_path": str(
                ARTICLE.relative_to(ROOT)
            ),
            "article_sha256": EXPECTED_ARTICLE_SHA,
            "source_authorization_digest_sha256": (
                EXPECTED_M10_AUTH_DIGEST
            ),
            "authorization_consumption_digest_sha256": (
                consumption[
                    "consumption_evidence_digest_sha256"
                ]
            ),
            "generated_offline": True,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "generated_at_utc": now()
        }

        payload = copy.deepcopy(
            payload_without_digest
        )
        payload["payload_digest_sha256"] = digest(
            payload_without_digest
        )

        write_json(PAYLOAD, payload)

        require(
            stat.S_IMODE(PAYLOAD.stat().st_mode)
            == 0o600,
            "PAYLOAD_MODE_NOT_0600",
        )

        persisted_payload = load(PAYLOAD)

        verify_digest(
            persisted_payload,
            "payload_digest_sha256",
            payload["payload_digest_sha256"],
        )

        validate_payload(
            persisted_payload,
            article,
            final_url,
            identifier,
        )

        for name, path in source_paths.items():
            require(
                file_sha(path) == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        payload_file_sha = file_sha(PAYLOAD)

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M11-FIX1"
            ),
            "status": (
                "PASS_FRESH_PAYLOAD_ARTICLE_TITLE_"
                "FIELD_VALIDATOR_FIXED_PAYLOAD_GENERATED_"
                "AUTHORIZATION_CONSUMED_NO_NETWORK_NO_WORDPRESS"
            ),
            "decision": (
                "FRESH_WORDPRESS_DRAFT_PAYLOAD_READY_"
                "FOR_HUMAN_REVIEW_AND_DRAFT_CREATION_GATE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "title": EXPECTED_TITLE,
            "title_source_field": "article_title",
            "root_title_key_absent_verified": True,
            "article_title_exact_match_verified": True,
            "post_status": "draft",
            "publish": False,
            "template_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "category_mapping_id": (
                "COMIC_NEW_RELEASE_LATEST_VOLUME_"
                "TO_WP_CATEGORY_10"
            ),
            "category_id": 10,
            "category_name": "最新巻",
            "consumption_attempt_id": attempt_id,
            "authorization_consumption_path": str(
                CONSUMPTION.relative_to(ROOT)
            ),
            "authorization_consumption_digest_sha256": (
                consumption[
                    "consumption_evidence_digest_sha256"
                ]
            ),
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "payload_path": str(
                PAYLOAD.relative_to(ROOT)
            ),
            "payload_file_sha256": payload_file_sha,
            "payload_digest_sha256": (
                payload["payload_digest_sha256"]
            ),
            "payload_file_mode": "0600",
            "article_sha256": EXPECTED_ARTICLE_SHA,
            "content_html_exact_article_match": True,
            "dmm_active_anchor_count": 1,
            "dmm_link_scheme_https_verified": True,
            "dmm_link_host_al_dmm_com_verified": True,
            "destination_exact_binding_verified": True,
            "registered_identifier_exact_binding_verified": True,
            "anchor_target_blank_verified": True,
            "anchor_rel_tokens_verified": True,
            "full_payload_output": False,
            "full_final_affiliate_url_output": False,
            "full_final_affiliate_url_in_normal_evidence": False,
            "affiliate_identifier_output": False,
            "affiliate_identifier_in_normal_evidence": False,
            "article_modified": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "FRESH_PAYLOAD_GENERATED_"
                "AWAITING_PAYLOAD_HUMAN_REVIEW"
            ),
            "ready_for_payload_human_review": True,
            "ready_for_wordpress_draft_creation": False,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        result = copy.deepcopy(result_without_digest)
        result["result_digest_sha256"] = digest(
            result_without_digest
        )

        write_json(RESULT, result)

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M11-FIX1

- Status: `{result["status"]}`
- Fixed title field: `article_title`
- Root title key absent: `true`
- Article title exact match: `true`
- Authorization consumed: `true`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- Payload file SHA-256: `{payload_file_sha}`
- Payload digest: `{payload["payload_digest_sha256"]}`
- Payload mode: `0600`
- Article SHA-256: `{EXPECTED_ARTICLE_SHA}`
- Title: `{EXPECTED_TITLE}`
- Post status: `draft`
- Publish: `false`
- Category ID: `10`
- Full payload output: `false`
- Full final URL output: `false`
- Affiliate identifier output: `false`
- Article modified: `false`
- Network accessed: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
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

    except Exception as exc:
        error_code = (
            str(exc)
            if isinstance(exc, ValidationError)
            else "UNEXPECTED_M11_FIX1_EXECUTION_FAILURE"
        )

        if boundary_crossed:
            try:
                PAYLOAD.unlink()
            except FileNotFoundError:
                pass

            failure_without_digest = {
                "schema_version": "1.0.0",
                "phase_id": (
                    "LS-NEW-BATCH-4G-2E-"
                    "RECOVERY-M11-FIX1"
                ),
                "status": (
                    "FAILED_AFTER_M11_FIX1_"
                    "AUTHORIZATION_CONSUMPTION_"
                    "NO_AUTOMATIC_RETRY"
                ),
                "decision": (
                    "M10_PAYLOAD_AUTHORIZATION_CONSUMED_"
                    "MANUAL_RECOVERY_REVIEW_REQUIRED"
                ),
                "error_code": error_code,
                "authorization_consumed": True,
                "authorization_reuse_allowed": False,
                "automatic_retry_allowed": False,
                "automatic_reissue_allowed": False,
                "consumption_evidence_preserved": (
                    CONSUMPTION.exists()
                ),
                "payload_artifact_preserved": False,
                "full_payload_output": False,
                "full_final_affiliate_url_output": False,
                "affiliate_identifier_output": False,
                "article_modified": False,
                "network_connection_performed": False,
                "wordpress_access_performed": False,
                "production_status": "NO_GO",
                "manual_recovery_review_required": True,
                "failed_at_utc": now()
            }

            failure = copy.deepcopy(
                failure_without_digest
            )
            failure["result_digest_sha256"] = digest(
                failure_without_digest
            )

            try:
                write_json(RESULT, failure)
            except Exception:
                pass

            print(
                json.dumps(
                    failure,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )

            return 1

        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M11-FIX1"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_M11_FIX1_"
                        "AUTHORIZATION_CONSUMPTION"
                    ),
                    "error_code": error_code,
                    "authorization_consumed": False,
                    "payload_created": False,
                    "full_payload_output": False,
                    "full_final_affiliate_url_output": False,
                    "affiliate_identifier_output": False,
                    "article_modified": False,
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
