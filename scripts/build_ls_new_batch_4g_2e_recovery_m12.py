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
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit


def _network_blocked(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("NETWORK_OPERATION_BLOCKED_BY_M12")


socket.socket = _network_blocked
socket.create_connection = _network_blocked
socket.getaddrinfo = _network_blocked


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_draft_creation_one_shot_"
    "authorization_gate_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m12_gate_approval.json"
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
SECRET_LINK = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
)

M11_FIX2_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload_human_review.json"
)
M11_FIX2_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m11_fix2_result.json"
)
M11_FIX1_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "fresh_payload_generation_consumption.json"
)
M11_FIX1_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m11_fix1_result.json"
)
M10_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "fresh_payload_generation_authorization.json"
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

AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m12_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m12_"
    "wordpress_draft_creation_authorization_report.md"
)

EXPECTED_ARTICLE_SHA = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
EXPECTED_PAYLOAD_SHA = (
    "30a70be4110e863a85e2896f69f5b3e5"
    "1d814a6fd82d5489f899d8a244166d8f"
)
EXPECTED_PAYLOAD_DIGEST = (
    "2ab27b59305dbae98f997ca3a4604002"
    "98152f173ef605b534df922c187411c6"
)
EXPECTED_M11_FIX2_REVIEW_DIGEST = (
    "52136cc8b50e8a7279e13ea4cb224033"
    "eca9790f354c7bcb18b0f6d694d71c25"
)
EXPECTED_M11_FIX2_RESULT_DIGEST = (
    "dc08a7212e812e366b05952c8e8eceba"
    "85f8f8421e2f9fcc65a54ddaa82ea404"
)
EXPECTED_M11_FIX1_CONSUMPTION_DIGEST = (
    "977e85a2de5f0b4ab07a140d39d39b6"
    "c461c87094ef636c52ab3e9a9c0338597"
)
EXPECTED_M11_FIX1_RESULT_DIGEST = (
    "56dc9fae9bd9ce621bbe98493829fd9f"
    "b751acaf0560e3c6c879dc567dc2e0d4"
)
EXPECTED_M10_AUTH_DIGEST = (
    "fed0e3c217c654f5e9803f750fd1d072"
    "69bff3eed4917a58638e61c9b571bc5b"
)
EXPECTED_SECRET_LINK_FILE_SHA = (
    "c5a70d9804a4e2dfd91049ee20bdda53"
    "79abf3e1fe3c25b0fb8cbd5fa587faa0"
)
EXPECTED_SECRET_LINK_DIGEST = (
    "4807e0a6d8a8416a936bafa978ba4f90"
    "d43ae7d304322bbd6a6ababcb2cd2db6"
)
EXPECTED_CRED1_DIGEST = (
    "7a173b74bef53781a3b2fe2e2cc2d3f3"
    "63a096b937508c241d454311d072ec7e"
)
EXPECTED_CATEGORY_MAPPING_SHA = (
    "19c2598d65d9acd817778deae8c661bc"
    "4c6ea33cc2a4d2686d33ec671764c4c0"
)
EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
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


def write_json(path: Path, value: dict[str, Any]) -> None:
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


class DmmAnchorInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current: dict[str, Any] | None = None
        self.matches: list[dict[str, Any]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() != "a":
            return

        attr_map = {
            name.casefold(): (
                "" if value is None else value
            )
            for name, value in attrs
        }

        classes = set(
            attr_map.get("class", "").split()
        )

        if "ls-store-dmm" not in classes:
            return

        self.current = {
            "classes": classes,
            "href": html.unescape(
                attr_map.get("href", "")
            ),
            "target": attr_map.get("target"),
            "rel": set(
                attr_map.get("rel", "").split()
            ),
            "aria_disabled": (
                "aria-disabled" in attr_map
            ),
            "text_parts": [],
        }

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current["text_parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if (
            tag.casefold() != "a"
            or self.current is None
        ):
            return

        current = self.current
        self.current = None

        self.matches.append(
            {
                "classes": current["classes"],
                "href": current["href"],
                "target": current["target"],
                "rel": current["rel"],
                "aria_disabled": current[
                    "aria_disabled"
                ],
                "text": re.sub(
                    r"\s+",
                    " ",
                    "".join(
                        current["text_parts"]
                    ),
                ).strip(),
            }
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


def main() -> int:
    try:
        for output in [
            AUTHORIZATION,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M12_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load(POLICY)
        approval = load(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            approval["approval_label"]
            == (
                "WORDPRESS_DRAFT_CREATION_ONE_SHOT_"
                "AUTHORIZATION_GATE_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M12",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["execution_boundary"][
                "authorization_consumption_allowed"
            ] is False,
            "AUTHORIZATION_CONSUMPTION_BOUNDARY_OPEN",
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
            "WORDPRESS_ACCESS_BOUNDARY_OPEN",
        )

        source_paths = {
            "article": ARTICLE,
            "payload": PAYLOAD,
            "secret_link": SECRET_LINK,
            "m11_fix2_review": M11_FIX2_REVIEW,
            "m11_fix2_result": M11_FIX2_RESULT,
            "m11_fix1_consumption": (
                M11_FIX1_CONSUMPTION
            ),
            "m11_fix1_result": M11_FIX1_RESULT,
            "m10_authorization": M10_AUTH,
            "cred1_result": CRED1_RESULT,
            "category_mapping": CATEGORY_MAPPING,
        }

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        require(
            source_hashes["article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_SHA_MISMATCH",
        )
        require(
            source_hashes["payload"]
            == EXPECTED_PAYLOAD_SHA,
            "PAYLOAD_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["secret_link"]
            == EXPECTED_SECRET_LINK_FILE_SHA,
            "SECRET_LINK_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["category_mapping"]
            == EXPECTED_CATEGORY_MAPPING_SHA,
            "CATEGORY_MAPPING_FILE_SHA_MISMATCH",
        )
        require(
            stat.S_IMODE(PAYLOAD.stat().st_mode)
            == 0o600,
            "PAYLOAD_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                SECRET_LINK.stat().st_mode
            ) == 0o600,
            "SECRET_LINK_MODE_NOT_0600",
        )
        require(
            not PAYLOAD.is_symlink(),
            "PAYLOAD_SYMLINK_REJECTED",
        )
        require(
            not SECRET_LINK.is_symlink(),
            "SECRET_LINK_SYMLINK_REJECTED",
        )

        article = load(ARTICLE)
        payload = load(PAYLOAD)
        secret = load(SECRET_LINK)
        review = load(M11_FIX2_REVIEW)
        m11_fix2_result = load(
            M11_FIX2_RESULT
        )
        consumption = load(
            M11_FIX1_CONSUMPTION
        )
        m11_fix1_result = load(
            M11_FIX1_RESULT
        )
        m10_auth = load(M10_AUTH)
        cred1 = load(CRED1_RESULT)
        category_mapping = load(
            CATEGORY_MAPPING
        )

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M11_FIX2_REVIEW_DIGEST,
        )
        verify_digest(
            m11_fix2_result,
            "result_digest_sha256",
            EXPECTED_M11_FIX2_RESULT_DIGEST,
        )
        verify_digest(
            consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M11_FIX1_CONSUMPTION_DIGEST,
        )
        verify_digest(
            m11_fix1_result,
            "result_digest_sha256",
            EXPECTED_M11_FIX1_RESULT_DIGEST,
        )
        verify_digest(
            m10_auth,
            "authorization_digest_sha256",
            EXPECTED_M10_AUTH_DIGEST,
        )
        verify_digest(
            secret,
            "secret_artifact_digest_sha256",
            EXPECTED_SECRET_LINK_DIGEST,
        )
        verify_digest(
            cred1,
            "result_digest_sha256",
            EXPECTED_CRED1_DIGEST,
        )

        require(
            review["review_verdict"]
            == "APPROVED_NO_CHANGE_REQUIRED",
            "M11_FIX2_REVIEW_VERDICT_MISMATCH",
        )
        require(
            m11_fix2_result["status"]
            == (
                "PASS_POST_SUCCESS_HTML_ENTITY_"
                "VALIDATOR_FIXED_EXISTING_PAYLOAD_"
                "REVIEW_APPROVED_NO_REGENERATION"
            ),
            "M11_FIX2_STATUS_MISMATCH",
        )
        require(
            m11_fix2_result[
                "ready_for_wordpress_draft_creation_authorization_gate"
            ] is True,
            "M11_FIX2_NOT_READY_FOR_M12",
        )

        require(
            consumption["authorization_consumed"]
            is True,
            "M10_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            consumption[
                "source_authorization_digest_sha256"
            ] == EXPECTED_M10_AUTH_DIGEST,
            "M10_AUTHORIZATION_CONSUMPTION_BINDING_MISMATCH",
        )
        require(
            consumption["authorization_reuse_allowed"]
            is False,
            "M10_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            consumption["automatic_retry_allowed"]
            is False,
            "M10_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            consumption["automatic_reissue_allowed"]
            is False,
            "M10_AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            m10_auth["authorization_consumed"]
            is False,
            "M10_ISSUANCE_ARTIFACT_WAS_MUTATED",
        )

        require(
            payload["title"] == EXPECTED_TITLE,
            "PAYLOAD_TITLE_MISMATCH",
        )
        require(
            payload["title"]
            == article["article_title"],
            "PAYLOAD_TITLE_ARTICLE_TITLE_MISMATCH",
        )
        require(
            payload["title_source_field"]
            == "article_title",
            "PAYLOAD_TITLE_SOURCE_FIELD_MISMATCH",
        )
        require(
            payload["content_html"]
            == article["content_html"],
            "PAYLOAD_CONTENT_HTML_MISMATCH",
        )
        require(
            payload["article_sha256"]
            == EXPECTED_ARTICLE_SHA,
            "PAYLOAD_ARTICLE_SHA_BINDING_MISMATCH",
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
            "PAYLOAD_CATEGORY_MAPPING_ID_MISMATCH",
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
        require(
            payload["content_item_id"]
            == "new-release-comic-20260703-001",
            "PAYLOAD_CONTENT_ITEM_ID_MISMATCH",
        )
        require(
            payload[
                "source_authorization_digest_sha256"
            ] == EXPECTED_M10_AUTH_DIGEST,
            "PAYLOAD_SOURCE_AUTHORIZATION_BINDING_MISMATCH",
        )
        require(
            payload[
                "authorization_consumption_digest_sha256"
            ] == EXPECTED_M11_FIX1_CONSUMPTION_DIGEST,
            "PAYLOAD_CONSUMPTION_BINDING_MISMATCH",
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

        final_url = secret["final_affiliate_url"]

        inspector = DmmAnchorInspector()
        inspector.feed(payload["content_html"])
        inspector.close()

        require(
            len(inspector.matches) == 1,
            "DMM_ANCHOR_COUNT_MUST_BE_ONE",
        )

        anchor = inspector.matches[0]

        require(
            anchor["classes"]
            == {"ls-store-btn", "ls-store-dmm"},
            "DMM_CLASS_TOKENS_MISMATCH",
        )
        require(
            "ls-store-disabled"
            not in anchor["classes"],
            "DMM_DISABLED_CLASS_PRESENT",
        )
        require(
            anchor["text"]
            == "DMMブックスで確認",
            "DMM_ANCHOR_TEXT_MISMATCH",
        )
        require(
            anchor["target"] == "_blank",
            "DMM_TARGET_MISMATCH",
        )
        require(
            anchor["rel"]
            == {"nofollow", "sponsored", "noopener"},
            "DMM_REL_TOKENS_MISMATCH",
        )
        require(
            anchor["aria_disabled"] is False,
            "DMM_ARIA_DISABLED_PRESENT",
        )
        require(
            anchor["href"] == final_url,
            "DMM_DECODED_HREF_SECRET_LINK_MISMATCH",
        )

        validate_final_url(
            anchor["href"],
            identifier,
        )

        authorization_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "WORDPRESS_DRAFT_CREATION_"
                "ONE_SHOT_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M12"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorization_id": (
                "WORDPRESS_DRAFT_CREATION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "authorized_operation": (
                "CREATE_ONE_WORDPRESS_DRAFT_"
                "FROM_BOUND_PAYLOAD"
            ),
            "payload_binding": {
                "path": str(
                    PAYLOAD.relative_to(ROOT)
                ),
                "file_sha256": EXPECTED_PAYLOAD_SHA,
                "payload_digest_sha256": (
                    EXPECTED_PAYLOAD_DIGEST
                ),
                "mode": "0600"
            },
            "article_binding": {
                "path": str(
                    ARTICLE.relative_to(ROOT)
                ),
                "file_sha256": EXPECTED_ARTICLE_SHA
            },
            "human_review_binding": {
                "path": str(
                    M11_FIX2_REVIEW.relative_to(ROOT)
                ),
                "review_verdict": (
                    "APPROVED_NO_CHANGE_REQUIRED"
                ),
                "review_digest_sha256": (
                    EXPECTED_M11_FIX2_REVIEW_DIGEST
                )
            },
            "historical_bindings": {
                "m11_fix2_result_digest_sha256": (
                    EXPECTED_M11_FIX2_RESULT_DIGEST
                ),
                "m11_fix1_consumption_digest_sha256": (
                    EXPECTED_M11_FIX1_CONSUMPTION_DIGEST
                ),
                "m11_fix1_result_digest_sha256": (
                    EXPECTED_M11_FIX1_RESULT_DIGEST
                ),
                "m10_authorization_digest_sha256": (
                    EXPECTED_M10_AUTH_DIGEST
                )
            },
            "wordpress_draft_contract": {
                "title": EXPECTED_TITLE,
                "content_source": (
                    "BOUND_PAYLOAD_CONTENT_HTML"
                ),
                "post_status": "draft",
                "publish": False,
                "category_id": 10,
                "categories": [10],
                "template_id": (
                    "POST185_STANDARD_TEMPLATE_V1_FIXED"
                ),
                "maximum_draft_count": 1,
                "create_only": True,
                "update_existing_post_allowed": False,
                "delete_post_allowed": False,
                "create_category_allowed": False,
                "update_category_allowed": False,
                "media_upload_allowed": False,
                "publish_allowed": False,
                "x_post_allowed": False
            },
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "actual_wordpress_access_allowed": False,
            "actual_wordpress_draft_creation_allowed": False,
            "actual_execution_requires_execute_now_approval": True,
            "planned_execution_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M13"
            ),
            "full_payload_present": False,
            "full_final_affiliate_url_present": False,
            "dmm_affiliate_identifier_present": False,
            "wordpress_credentials_present": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
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
        ] = digest(authorization_without_digest)

        write_json(
            AUTHORIZATION,
            authorization,
        )

        for name, path in source_paths.items():
            require(
                file_sha(path) == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M12"
            ),
            "status": (
                "PASS_WORDPRESS_DRAFT_CREATION_"
                "ONE_SHOT_AUTHORIZATION_GATE_FIXED_"
                "NO_NETWORK_NO_WORDPRESS"
            ),
            "decision": (
                "WORDPRESS_DRAFT_CREATION_"
                "AUTHORIZATION_RECORDED_AWAITING_"
                "EXPLICIT_EXECUTE_NOW_CONFIRMATION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "title": EXPECTED_TITLE,
            "post_status": "draft",
            "publish": False,
            "category_id": 10,
            "template_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "m11_fix2_review_digest_sha256": (
                EXPECTED_M11_FIX2_REVIEW_DIGEST
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
                authorization["authorization_id"]
            ),
            "authorization_single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "maximum_draft_count": 1,
            "planned_execution_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M13"
            ),
            "payload_validated": True,
            "article_binding_validated": True,
            "human_review_validated": True,
            "dmm_anchor_validated": True,
            "decoded_href_exact_binding_validated": True,
            "full_payload_output": False,
            "full_final_affiliate_url_output": False,
            "dmm_affiliate_identifier_output": False,
            "wordpress_credentials_read": False,
            "wordpress_credentials_output": False,
            "payload_modified": False,
            "article_modified": False,
            "authorization_consumed_in_this_phase": False,
            "network_connection_performed": False,
            "dns_resolution_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "WORDPRESS_DRAFT_CREATION_"
                "AUTHORIZATION_UNCONSUMED_"
                "AWAITING_EXECUTE_NOW_APPROVAL"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m13": True,
            "ready_for_wordpress_draft_creation": False,
            "ready_for_wordpress_publish": False,
            "completed_at_utc": now()
        }

        result = copy.deepcopy(result_without_digest)
        result[
            "result_digest_sha256"
        ] = digest(result_without_digest)

        write_json(RESULT, result)

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M12

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Payload file SHA-256: `{EXPECTED_PAYLOAD_SHA}`
- Payload digest: `{EXPECTED_PAYLOAD_DIGEST}`
- Payload review digest: `{EXPECTED_M11_FIX2_REVIEW_DIGEST}`
- Authorization ID: `WORDPRESS_DRAFT_CREATION_ONE_SHOT_AUTHORIZATION_V1`
- Authorization single use: `true`
- Authorization consumed: `false`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- Maximum draft count: `1`
- Planned execution phase: `LS-NEW-BATCH-4G-2E-RECOVERY-M13`
- Post status: `draft`
- Publish: `false`
- Category ID: `10`
- Payload modified: `false`
- Article modified: `false`
- Network accessed: `false`
- WordPress accessed: `false`
- WordPress draft created: `false`
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

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M12"
                    ),
                    "status": (
                        "BLOCKED_WORDPRESS_DRAFT_CREATION_"
                        "AUTHORIZATION_GATE_NO_ISSUANCE"
                    ),
                    "error_code": str(exc),
                    "authorization_created": False,
                    "authorization_consumed": False,
                    "payload_modified": False,
                    "article_modified": False,
                    "network_connection_performed": False,
                    "wordpress_access_performed": False,
                    "wordpress_draft_created": False,
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
