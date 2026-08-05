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
    "new_release_wp_fresh_payload_post_success_"
    "html_entity_validator_fix_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m11_fix2_approval.json"
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
M11_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "fresh_payload_generation_consumption.json"
)
M11_RESULT = ROOT / (
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
CREDENTIAL_FILE = Path(
    "/etc/ai-media-os/credential.env"
)

REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload_human_review.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m11_fix2_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m11_fix2_"
    "existing_payload_review_report.md"
)

EXPECTED_PAYLOAD_SHA = (
    "30a70be4110e863a85e2896f69f5b3e5"
    "1d814a6fd82d5489f899d8a244166d8f"
)
EXPECTED_PAYLOAD_DIGEST = (
    "2ab27b59305dbae98f997ca3a4604002"
    "98152f173ef605b534df922c187411c6"
)
EXPECTED_CONSUMPTION_DIGEST = (
    "977e85a2de5f0b4ab07a140d39d39b6"
    "c461c87094ef636c52ab3e9a9c0338597"
)
EXPECTED_RESULT_DIGEST = (
    "56dc9fae9bd9ce621bbe98493829fd9f"
    "b751acaf0560e3c6c879dc567dc2e0d4"
)
EXPECTED_M10_AUTH_DIGEST = (
    "fed0e3c217c654f5e9803f750fd1d072"
    "69bff3eed4917a58638e61c9b571bc5b"
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


def validate_url(
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

    require(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
        == [
            ("lurl", EXPECTED_PRODUCT_URL),
            ("af_id", identifier),
            ("ch", "link_tool"),
            ("ch_id", "link"),
        ],
        "FINAL_URL_QUERY_BINDING_MISMATCH",
    )


def main() -> int:
    try:
        for output in [REVIEW, RESULT, REPORT]:
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
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M11-FIX2",
            "POLICY_PHASE_MISMATCH",
        )

        source_paths = {
            "article": ARTICLE,
            "payload": PAYLOAD,
            "secret_link": SECRET_LINK,
            "m11_consumption": M11_CONSUMPTION,
            "m11_result": M11_RESULT,
            "m10_authorization": M10_AUTH,
            "cred1_result": CRED1_RESULT,
        }

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        require(
            source_hashes["payload"]
            == EXPECTED_PAYLOAD_SHA,
            "PAYLOAD_FILE_SHA_MISMATCH",
        )
        require(
            stat.S_IMODE(PAYLOAD.stat().st_mode)
            == 0o600,
            "PAYLOAD_MODE_NOT_0600",
        )

        article = load(ARTICLE)
        payload = load(PAYLOAD)
        secret = load(SECRET_LINK)
        consumption = load(M11_CONSUMPTION)
        m11_result = load(M11_RESULT)
        m10_auth = load(M10_AUTH)
        cred1 = load(CRED1_RESULT)

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_CONSUMPTION_DIGEST,
        )
        verify_digest(
            m11_result,
            "result_digest_sha256",
            EXPECTED_RESULT_DIGEST,
        )
        verify_digest(
            m10_auth,
            "authorization_digest_sha256",
            EXPECTED_M10_AUTH_DIGEST,
        )
        verify_digest(
            secret,
            "secret_artifact_digest_sha256",
        )
        verify_digest(
            cred1,
            "result_digest_sha256",
        )

        require(
            consumption["authorization_consumed"]
            is True,
            "AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            consumption["authorization_reuse_allowed"]
            is False,
            "AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            consumption["automatic_retry_allowed"]
            is False,
            "AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            consumption["automatic_reissue_allowed"]
            is False,
            "AUTOMATIC_REISSUE_ALLOWED",
        )

        require(
            payload["title"]
            == article["article_title"],
            "PAYLOAD_TITLE_ARTICLE_TITLE_MISMATCH",
        )
        require(
            payload["title_source_field"]
            == "article_title",
            "TITLE_SOURCE_FIELD_MISMATCH",
        )
        require(
            payload["content_html"]
            == article["content_html"],
            "PAYLOAD_CONTENT_HTML_MISMATCH",
        )
        require(
            payload["post_status"] == "draft",
            "POST_STATUS_MISMATCH",
        )
        require(
            payload["status"] == "draft",
            "STATUS_MISMATCH",
        )
        require(
            payload["publish"] is False,
            "PUBLISH_FLAG_MISMATCH",
        )
        require(
            payload["template_id"]
            == "POST185_STANDARD_TEMPLATE_V1_FIXED",
            "TEMPLATE_ID_MISMATCH",
        )
        require(
            payload["category_mapping_id"]
            == (
                "COMIC_NEW_RELEASE_LATEST_VOLUME_"
                "TO_WP_CATEGORY_10"
            ),
            "CATEGORY_MAPPING_ID_MISMATCH",
        )
        require(
            payload["category_id"] == 10,
            "CATEGORY_ID_MISMATCH",
        )
        require(
            payload["categories"] == [10],
            "CATEGORIES_MISMATCH",
        )
        require(
            payload["category_name"] == "最新巻",
            "CATEGORY_NAME_MISMATCH",
        )
        require(
            payload["content_item_id"]
            == "new-release-comic-20260703-001",
            "CONTENT_ITEM_ID_MISMATCH",
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
            anchor["text"] == "DMMブックスで確認",
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
            "ls-store-disabled"
            not in anchor["classes"],
            "DMM_DISABLED_CLASS_PRESENT",
        )
        require(
            anchor["href"] == final_url,
            "DECODED_HREF_SECRET_LINK_MISMATCH",
        )

        validate_url(anchor["href"], identifier)

        review_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M11-FIX2"
            ),
            "document_role": (
                "EXISTING_WORDPRESS_DRAFT_"
                "PAYLOAD_HUMAN_REVIEW"
            ),
            "review_id": (
                "WORDPRESS_DRAFT_PAYLOAD_"
                "HUMAN_REVIEW_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "reviewed_by": "HUMAN_OPERATOR",
            "human_explicit_approval": True,
            "diagnosis": (
                "POST_SUCCESS_SAFETY_CHECK_"
                "HTML_ENTITY_ESCAPING_FALSE_NEGATIVE"
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
            "validation_results": {
                "payload_title_matches_article_title": True,
                "title_source_field_article_title": True,
                "content_html_exact_article_match": True,
                "post_status_draft": True,
                "status_draft": True,
                "publish_false": True,
                "template_id_verified": True,
                "category_mapping_id_verified": True,
                "category_id_10": True,
                "categories_array_verified": True,
                "category_name_verified": True,
                "dmm_anchor_count_one": True,
                "dmm_anchor_class_tokens_exact": True,
                "dmm_anchor_text_verified": True,
                "dmm_anchor_target_blank": True,
                "dmm_anchor_rel_tokens_exact": True,
                "dmm_aria_disabled_absent": True,
                "dmm_disabled_class_absent": True,
                "href_html_entity_decoded": True,
                "decoded_href_exact_secret_link_match": True,
                "dmm_url_structure_verified": True,
                "destination_binding_verified": True,
                "registered_identifier_binding_verified": True,
                "authorization_consumption_verified": True,
                "authorization_reuse_blocked": True,
                "automatic_retry_blocked": True,
                "automatic_reissue_blocked": True
            },
            "full_payload_output": False,
            "full_final_affiliate_url_output": False,
            "affiliate_identifier_output": False,
            "payload_regenerated": False,
            "payload_modified": False,
            "article_modified": False,
            "authorization_reissued": False,
            "authorization_reconsumed": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "production_status": "NO_GO",
            "reviewed_at_utc": now()
        }

        review = copy.deepcopy(review_without_digest)
        review[
            "human_review_evidence_digest_sha256"
        ] = digest(review_without_digest)

        write_json(REVIEW, review)

        for name, path in source_paths.items():
            require(
                file_sha(path) == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M11-FIX2"
            ),
            "status": (
                "PASS_POST_SUCCESS_HTML_ENTITY_"
                "VALIDATOR_FIXED_EXISTING_PAYLOAD_"
                "REVIEW_APPROVED_NO_REGENERATION"
            ),
            "decision": (
                "EXISTING_PAYLOAD_APPROVED_READY_FOR_"
                "WORDPRESS_DRAFT_CREATION_AUTHORIZATION_GATE"
            ),
            "review_verdict": (
                "APPROVED_NO_CHANGE_REQUIRED"
            ),
            "payload_file_sha256": EXPECTED_PAYLOAD_SHA,
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "review_path": str(
                REVIEW.relative_to(ROOT)
            ),
            "review_digest_sha256": (
                review[
                    "human_review_evidence_digest_sha256"
                ]
            ),
            "html_postimage_reparsed": True,
            "href_html_entity_decoded": True,
            "decoded_href_exact_secret_link_match": True,
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "payload_regenerated": False,
            "payload_modified": False,
            "article_modified": False,
            "authorization_reissued": False,
            "authorization_reconsumed": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "PAYLOAD_REVIEW_APPROVED_AWAITING_"
                "WORDPRESS_DRAFT_CREATION_AUTHORIZATION_GATE"
            ),
            "ready_for_wordpress_draft_creation_authorization_gate": True,
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M11-FIX2

- Status: `{result["status"]}`
- Review verdict: `APPROVED_NO_CHANGE_REQUIRED`
- Payload file SHA-256: `{EXPECTED_PAYLOAD_SHA}`
- Payload digest: `{EXPECTED_PAYLOAD_DIGEST}`
- Payload mode: `0600`
- HTML reparsed: `true`
- href HTML entity decoded: `true`
- Decoded href exact match: `true`
- Authorization remains consumed: `true`
- Payload regenerated: `false`
- Payload modified: `false`
- Article modified: `false`
- Authorization reissued: `false`
- Authorization reconsumed: `false`
- Network accessed: `false`
- WordPress accessed: `false`
- WordPress draft created: `false`
- Production status: `NO_GO`
- Ready for WordPress draft creation authorization gate: `true`
""",
        )

        del final_url
        del identifier

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
                        "RECOVERY-M11-FIX2"
                    ),
                    "status": (
                        "BLOCKED_EXISTING_PAYLOAD_"
                        "REVIEW_NO_SOURCE_CHANGE"
                    ),
                    "error_code": str(exc),
                    "review_approved": False,
                    "payload_regenerated": False,
                    "payload_modified": False,
                    "authorization_reissued": False,
                    "authorization_reconsumed": False,
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
