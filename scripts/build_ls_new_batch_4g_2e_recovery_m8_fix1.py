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

FIX_POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_article_reserved_slot_"
    "html_validator_fix_policy.json"
)
FIX_APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m8_fix1_"
    "html_validator_fix_approval.json"
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
M8_REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m8_"
    "dmm_final_link_review_and_injection_"
    "authorization_report.md"
)
FIX_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m8_fix1_result.json"
)
FIX_REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m8_fix1_"
    "html_validator_fix_report.md"
)

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
M7_LINK = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
)
M7_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_consumption.json"
)
M7_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m7_result.json"
)
M6_AUTHORIZATION = ROOT / (
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

CREDENTIAL_FILE = Path(
    "/etc/ai-media-os/credential.env"
)
CREDENTIAL_KEY = "DMM_AFFILIATE_ID"

EXPECTED_ARTICLE_SHA = (
    "849a37519c6af70d2212ec01d5cddef5"
    "793bfa811e97ca9f248ce099a0350bf4"
)
EXPECTED_M7_LINK_FILE_SHA = (
    "c5a70d9804a4e2dfd91049ee20bdda53"
    "79abf3e1fe3c25b0fb8cbd5fa587faa0"
)
EXPECTED_M7_LINK_DIGEST = (
    "4807e0a6d8a8416a936bafa978ba4f90"
    "d43ae7d304322bbd6a6ababcb2cd2db6"
)
EXPECTED_M7_FINGERPRINT = (
    "f01572020caf88cd0a017e0e739bc492"
    "394fa275eeac0e346328adba0fd99141"
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


def utc_now() -> str:
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


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
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


def verify_self_digest(
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


class ReservedSlotParser(HTMLParser):
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
        attributes = {
            name.casefold(): (
                ""
                if value is None
                else value
            )
            for name, value in attrs
        }

        node = {
            "tag": tag.casefold(),
            "attrs": attributes,
            "text_parts": [],
            "descendant_anchor_count": 0,
        }

        for ancestor in self.stack:
            if tag.casefold() == "a":
                ancestor[
                    "descendant_anchor_count"
                ] += 1

        self.stack.append(node)

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self.stack:
            self.stack[-1][
                "text_parts"
            ].append(data)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if not self.stack:
            return

        node = self.stack.pop()

        if node["tag"] != tag.casefold():
            return

        class_tokens = set(
            node["attrs"].get(
                "class",
                "",
            ).split()
        )

        required = {
            "ls-store-btn",
            "ls-store-dmm",
            "ls-store-disabled",
        }

        if (
            node["tag"] == "span"
            and required.issubset(
                class_tokens
            )
        ):
            normalized_text = re.sub(
                r"\s+",
                " ",
                html.unescape(
                    "".join(
                        node["text_parts"]
                    )
                ),
            ).strip()

            self.matches.append(
                {
                    "tag": node["tag"],
                    "class_tokens": sorted(
                        class_tokens
                    ),
                    "aria_disabled": (
                        node["attrs"].get(
                            "aria-disabled"
                        )
                    ),
                    "href_present": (
                        "href"
                        in node["attrs"]
                    ),
                    "descendant_anchor_count": (
                        node[
                            "descendant_anchor_count"
                        ]
                    ),
                    "normalized_text": (
                        normalized_text
                    ),
                }
            )

        if self.stack:
            self.stack[-1][
                "text_parts"
            ].extend(
                node["text_parts"]
            )


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
        )
        == 0o600,
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

        key, separator, value = (
            line.partition("=")
        )

        if (
            separator == "="
            and key.strip()
            == CREDENTIAL_KEY
        ):
            value = value.strip()

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
        )
        is not None,
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
        pairs
        == [
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


def main() -> int:
    try:
        for output in [
            REVIEW,
            AUTHORIZATION,
            M8_RESULT,
            M8_REPORT,
            FIX_RESULT,
            FIX_REPORT,
        ]:
            require(
                not output.exists(),
                f"OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(FIX_POLICY)
        approval = load_json(
            FIX_APPROVAL
        )

        approval_digest = (
            verify_self_digest(
                approval,
                "approval_evidence_digest_sha256",
            )
        )

        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M8-FIX1"
            ),
            "POLICY_PHASE_MISMATCH",
        )

        source_paths = {
            "article": ARTICLE,
            "m7_link": M7_LINK,
            "m7_consumption": M7_CONSUMPTION,
            "m7_result": M7_RESULT,
            "m6_authorization": M6_AUTHORIZATION,
            "m5_review": M5_REVIEW,
            "cred1_result": CRED1_RESULT,
        }

        source_hashes = {
            name: file_sha256(path)
            for name, path
            in source_paths.items()
        }

        require(
            source_hashes["article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_SHA_MISMATCH",
        )
        require(
            source_hashes["m7_link"]
            == EXPECTED_M7_LINK_FILE_SHA,
            "M7_LINK_FILE_SHA_MISMATCH",
        )
        require(
            stat.S_IMODE(
                M7_LINK.stat().st_mode
            )
            == 0o600,
            "M7_LINK_MODE_NOT_0600",
        )
        require(
            not M7_LINK.is_symlink(),
            "M7_LINK_SYMLINK_REJECTED",
        )

        article = load_json(ARTICLE)
        m7_link = load_json(M7_LINK)
        m7_consumption = load_json(
            M7_CONSUMPTION
        )
        m7_result = load_json(
            M7_RESULT
        )
        m6_authorization = load_json(
            M6_AUTHORIZATION
        )
        m5_review = load_json(
            M5_REVIEW
        )
        cred1 = load_json(
            CRED1_RESULT
        )

        verify_self_digest(
            m7_link,
            "secret_artifact_digest_sha256",
            EXPECTED_M7_LINK_DIGEST,
        )
        verify_self_digest(
            m7_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M7_CONSUMPTION_DIGEST,
        )
        verify_self_digest(
            m6_authorization,
            "authorization_digest_sha256",
            EXPECTED_M6_AUTH_DIGEST,
        )
        verify_self_digest(
            m5_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M5_REVIEW_DIGEST,
        )
        verify_self_digest(
            cred1,
            "result_digest_sha256",
            EXPECTED_CRED1_RESULT_DIGEST,
        )

        require(
            m7_result["status"]
            == (
                "PASS_DMM_FINAL_AFFILIATE_LINK_"
                "GENERATED_OFFLINE_AUTHORIZATION_"
                "CONSUMED_NO_NETWORK"
            ),
            "M7_RESULT_STATUS_MISMATCH",
        )
        require(
            m7_consumption[
                "authorization_consumed"
            ]
            is True,
            "M7_AUTHORIZATION_NOT_CONSUMED",
        )

        identifier = read_identifier()
        verify_commitment(
            identifier,
            cred1,
        )

        final_url = m7_link[
            "final_affiliate_url"
        ]

        require(
            hashlib.sha256(
                final_url.encode("utf-8")
            ).hexdigest()
            == EXPECTED_M7_FINGERPRINT,
            "M7_FINGERPRINT_MISMATCH",
        )

        validate_final_url(
            final_url,
            identifier,
        )

        content_html = article.get(
            "content_html"
        )

        require(
            isinstance(
                content_html,
                str,
            ),
            "CONTENT_HTML_MISSING",
        )
        require(
            "al.dmm.com"
            not in content_html.casefold(),
            "ARTICLE_ALREADY_CONTAINS_AL_DMM",
        )
        require(
            "af_id="
            not in content_html.casefold(),
            "ARTICLE_ALREADY_CONTAINS_AF_ID",
        )

        parser = ReservedSlotParser()
        parser.feed(content_html)
        parser.close()

        require(
            len(parser.matches) == 1,
            (
                "DMM_RESERVED_SLOT_MATCH_COUNT_"
                "MUST_BE_ONE"
            ),
        )

        slot = parser.matches[0]

        require(
            slot["tag"] == "span",
            "DMM_SLOT_TAG_MISMATCH",
        )
        require(
            slot["aria_disabled"]
            == "true",
            "DMM_SLOT_ARIA_DISABLED_MISMATCH",
        )
        require(
            slot["href_present"]
            is False,
            "DMM_SLOT_HREF_PRESENT",
        )
        require(
            slot[
                "descendant_anchor_count"
            ]
            == 0,
            "DMM_SLOT_DESCENDANT_ANCHOR_PRESENT",
        )
        require(
            slot["normalized_text"]
            == (
                "DMMブックスで確認"
                "（再確認待ち）"
            ),
            "DMM_SLOT_TEXT_MISMATCH",
        )

        navigation = article.get(
            "store_navigation"
        )

        require(
            isinstance(
                navigation,
                dict,
            ),
            "STORE_NAVIGATION_MISSING",
        )
        require(
            navigation["render_mode"]
            == (
                "RESERVED_NON_CLICKABLE_"
                "SLOTS_ONLY"
            ),
            "RENDER_MODE_MISMATCH",
        )
        require(
            navigation[
                "anchor_elements_included"
            ]
            is False,
            "ANCHOR_STATE_MISMATCH",
        )
        require(
            navigation[
                "href_attributes_included"
            ]
            is False,
            "HREF_STATE_MISMATCH",
        )
        require(
            navigation[
                "final_affiliate_urls_included"
            ]
            is False,
            "FINAL_URL_STATE_MISMATCH",
        )
        require(
            navigation[
                "dmm_url_included"
            ]
            is False,
            "DMM_URL_STATE_MISMATCH",
        )

        source_bindings = {
            name: {
                "path": str(
                    path.relative_to(ROOT)
                ),
                "file_sha256": (
                    source_hashes[name]
                ),
            }
            for name, path
            in source_paths.items()
        }

        review_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M8-FIX1"
            ),
            "document_role": (
                "DMM_FINAL_AFFILIATE_LINK_"
                "HUMAN_REVIEW_EVIDENCE"
            ),
            "review_id": (
                "DMM_FINAL_AFFILIATE_LINK_"
                "HUMAN_REVIEW_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "approval_label": (
                "DMM_ARTICLE_RESERVED_SLOT_"
                "HTML_VALIDATOR_FIX_APPROVED"
            ),
            "reviewed_by": "HUMAN_OPERATOR",
            "human_explicit_approval": True,
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "validator_fix": {
                "previous_false_negative": (
                    "ARTICLE_DMM_RESERVED_SLOT_"
                    "LABEL_MISSING"
                ),
                "fixed_validation_mode": (
                    "HTML_STRUCTURE_BASED"
                ),
                "matching_slot_count": 1,
                "required_tag_verified": True,
                "required_class_tokens_verified": True,
                "aria_disabled_verified": True,
                "normalized_text_verified": True,
                "href_absent_verified": True,
                "descendant_anchor_absent_verified": True
            },
            "secret_link_validation": {
                "file_sha256": (
                    EXPECTED_M7_LINK_FILE_SHA
                ),
                "artifact_digest_sha256": (
                    EXPECTED_M7_LINK_DIGEST
                ),
                "final_url_fingerprint_sha256": (
                    EXPECTED_M7_FINGERPRINT
                ),
                "file_mode": "0600",
                "scheme_https_verified": True,
                "host_al_dmm_com_verified": True,
                "destination_exact_binding_verified": True,
                "registered_identifier_exact_binding_verified": True,
                "full_final_url_present": False,
                "affiliate_identifier_present": False
            },
            "article_preimage": {
                "path": str(
                    ARTICLE.relative_to(ROOT)
                ),
                "file_sha256": (
                    EXPECTED_ARTICLE_SHA
                ),
                "article_modified": False
            },
            "source_bindings": (
                source_bindings
            ),
            "full_final_url_output": False,
            "affiliate_identifier_output": False,
            "network_connection_performed": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "article_dmm_slot_activated": False,
            "wordpress_access_performed": False,
            "production_status": "NO_GO",
            "reviewed_at_utc": utc_now()
        }

        review = copy.deepcopy(
            review_without_digest
        )
        review[
            "human_review_evidence_digest_sha256"
        ] = digest(
            review_without_digest
        )

        write_json(
            REVIEW,
            review,
        )

        authorization_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_ARTICLE_LINK_INJECTION_"
                "ONE_SHOT_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M8-FIX1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorization_id": (
                "DMM_ARTICLE_LINK_INJECTION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "approval_label": (
                "DMM_ARTICLE_RESERVED_SLOT_"
                "HTML_VALIDATOR_FIX_APPROVED"
            ),
            "authorized_operation": (
                "ONE_SHOT_ARTICLE_DMM_LINK_"
                "INJECTION_AND_SLOT_ACTIVATION"
            ),
            "human_review_binding": {
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
            "article_preimage_binding": {
                "path": str(
                    ARTICLE.relative_to(ROOT)
                ),
                "file_sha256": (
                    EXPECTED_ARTICLE_SHA
                ),
                "required_slot_tag": "span",
                "required_class_tokens": [
                    "ls-store-btn",
                    "ls-store-dmm",
                    "ls-store-disabled"
                ],
                "required_aria_disabled": "true",
                "required_text": (
                    "DMMブックスで確認"
                    "（再確認待ち）"
                )
            },
            "secret_link_binding": {
                "path": str(
                    M7_LINK.relative_to(ROOT)
                ),
                "file_sha256": (
                    EXPECTED_M7_LINK_FILE_SHA
                ),
                "artifact_digest_sha256": (
                    EXPECTED_M7_LINK_DIGEST
                ),
                "final_url_fingerprint_sha256": (
                    EXPECTED_M7_FINGERPRINT
                ),
                "required_mode": "0600",
                "full_final_url_present": False,
                "affiliate_identifier_present": False
            },
            "historical_bindings": {
                "m7_consumption_digest_sha256": (
                    EXPECTED_M7_CONSUMPTION_DIGEST
                ),
                "m6_authorization_digest_sha256": (
                    EXPECTED_M6_AUTH_DIGEST
                ),
                "m5_human_review_digest_sha256": (
                    EXPECTED_M5_REVIEW_DIGEST
                ),
                "cred1_result_digest_sha256": (
                    EXPECTED_CRED1_RESULT_DIGEST
                )
            },
            "required_mutation_contract": {
                "only_dmm_slot_may_change": True,
                "replace_span_with_anchor": True,
                "activated_label": (
                    "DMMブックスで確認"
                ),
                "anchor_target": "_blank",
                "anchor_rel": (
                    "nofollow sponsored noopener"
                ),
                "remove_disabled_class": True,
                "remove_aria_disabled": True,
                "amazon_slot_modification_allowed": False,
                "rakuten_kobo_slot_modification_allowed": False,
                "title_modification_allowed": False,
                "body_copy_modification_allowed": False,
                "image_modification_allowed": False,
                "price_metadata_modification_allowed": False
            },
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "actual_injection_requires_execute_now_approval": True,
            "actual_injection_allowed": False,
            "planned_execution_phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M9"
            ),
            "planned_consumption_path": (
                "exchange/authorizations/"
                "new_release/fresh/"
                "new-release-comic-20260703-001."
                "article_dmm_link_injection_"
                "consumption.json"
            ),
            "network_connection_performed": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "article_dmm_slot_activated": False,
            "payload_created": False,
            "wordpress_access_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "authorized_at_utc": utc_now()
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
                file_sha256(path)
                == source_hashes[name],
                f"SOURCE_CHANGED:{name}",
            )

        m8_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M8"
            ),
            "status": (
                "PASS_DMM_FINAL_AFFILIATE_LINK_"
                "HUMAN_REVIEW_APPROVED_ARTICLE_"
                "INJECTION_AUTHORIZATION_FIXED_"
                "NO_ARTICLE_CHANGE_NO_NETWORK"
            ),
            "decision": (
                "DMM_FINAL_LINK_REVIEW_APPROVED_"
                "ARTICLE_INJECTION_AUTHORIZATION_"
                "RECORDED_AWAITING_EXPLICIT_"
                "EXECUTE_NOW_CONFIRMATION"
            ),
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "review_path": str(
                REVIEW.relative_to(ROOT)
            ),
            "review_file_sha256": (
                file_sha256(REVIEW)
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
                file_sha256(AUTHORIZATION)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "authorization_single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "html_reserved_slot_verified": True,
            "secret_link_verified": True,
            "cred1_commitment_revalidated": True,
            "full_final_affiliate_url_output": False,
            "affiliate_identifier_output": False,
            "network_connection_performed": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "article_dmm_slot_activated": False,
            "payload_created": False,
            "wordpress_access_performed": False,
            "production_status": "NO_GO",
            "ready_for_ls_new_batch_4g_2e_recovery_m9": True,
            "ready_for_article_url_injection": False,
            "ready_for_execution": False,
            "completed_at_utc": utc_now()
        }

        m8_result = copy.deepcopy(
            m8_without_digest
        )
        m8_result[
            "result_digest_sha256"
        ] = digest(m8_without_digest)

        write_json(
            M8_RESULT,
            m8_result,
        )

        fix_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M8-FIX1"
            ),
            "status": (
                "PASS_DMM_ARTICLE_RESERVED_SLOT_"
                "HTML_VALIDATOR_FIXED_M8_REBUILT_"
                "NO_ARTICLE_CHANGE_NO_NETWORK"
            ),
            "decision": (
                "HTML_VALIDATOR_FALSE_NEGATIVE_"
                "REMOVED_M8_REVIEW_AND_M9_"
                "AUTHORIZATION_READY"
            ),
            "approval_digest_sha256": (
                approval_digest
            ),
            "article_file_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "html_slot_match_count": 1,
            "html_slot_tag_verified": True,
            "html_slot_class_tokens_verified": True,
            "html_slot_aria_disabled_verified": True,
            "html_slot_text_verified": True,
            "html_slot_href_absent": True,
            "html_slot_descendant_anchor_absent": True,
            "m8_review_rebuilt": True,
            "m9_authorization_created": True,
            "m9_authorization_consumed": False,
            "full_final_affiliate_url_output": False,
            "affiliate_identifier_output": False,
            "secret_link_modified": False,
            "article_modified": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "production_status": "NO_GO",
            "ready_for_m9_execute_now_gate": True,
            "completed_at_utc": utc_now()
        }

        fix_result = copy.deepcopy(
            fix_without_digest
        )
        fix_result[
            "fix_evidence_digest_sha256"
        ] = digest(fix_without_digest)

        write_json(
            FIX_RESULT,
            fix_result,
        )

        write_text(
            M8_REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M8

- Status: `{m8_result["status"]}`
- Review verdict: `APPROVED_NO_CHANGE_REQUIRED`
- HTML reserved slot verified: `true`
- Injection authorization consumed: `false`
- Full final URL output: `false`
- Affiliate identifier output: `false`
- Article modified: `false`
- Network accessed: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for M9: `true`
""",
        )

        write_text(
            FIX_REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M8-FIX1

- Status: `{fix_result["status"]}`
- Cause: `content_html whole-string exact-match false negative`
- Replacement: `HTML structure-based validator`
- DMM reserved slot matches: `1`
- Article modified: `false`
- Secret link modified: `false`
- Network accessed: `false`
- Full final URL output: `false`
- Affiliate identifier output: `false`
- M8 review rebuilt: `true`
- M9 authorization created: `true`
- M9 authorization consumed: `false`
- Production status: `NO_GO`
""",
        )

        del identifier
        del final_url

        print(
            json.dumps(
                fix_result,
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
                        "RECOVERY-M8-FIX1"
                    ),
                    "status": (
                        "BLOCKED_DMM_ARTICLE_"
                        "RESERVED_SLOT_HTML_"
                        "VALIDATOR_FIX"
                    ),
                    "error_code": str(exc),
                    "m8_review_rebuilt": False,
                    "m9_authorization_created": False,
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
