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
import tempfile
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_article_link_"
    "injection_one_shot_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m9_execute_now_approval.json"
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
M9_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_authorization.json"
)
M8_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_human_review.json"
)
M8_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m8_result.json"
)
M8_FIX1_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m8_fix1_result.json"
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
CREDENTIAL_FILE = Path(
    "/etc/ai-media-os/credential.env"
)

CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m9_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m9_"
    "article_dmm_link_injection_report.md"
)

EXPECTED_ARTICLE_SHA = (
    "849a37519c6af70d2212ec01d5cddef5"
    "793bfa811e97ca9f248ce099a0350bf4"
)
EXPECTED_M9_AUTH_DIGEST = (
    "d274eaf6bd14c95ac43031fbff296d0d"
    "47e6051dbb4231407327d376f93fec7f"
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


def fsync_directory(path: Path) -> None:
    fd = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_replace(
    path: Path,
    payload: bytes,
) -> None:
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.m9.",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)

    try:
        os.fchmod(fd, 0o600)

        with os.fdopen(
            fd,
            "wb",
            closefd=True,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary,
            path,
        )
        fsync_directory(path.parent)

    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass

        try:
            temporary.unlink()
        except FileNotFoundError:
            pass

        raise


def write_exclusive_json(
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


def write_exclusive_text(
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


class DmmSlotRewriter(HTMLParser):
    def __init__(
        self,
        final_url: str,
    ) -> None:
        super().__init__(
            convert_charrefs=False
        )
        self.final_url = final_url
        self.output: list[str] = []
        self.match_count = 0
        self.skip_target_data = False
        self.target_depth = 0

    @staticmethod
    def serialize_attrs(
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> str:
        rendered: list[str] = []

        for name, value in attrs:
            if value is None:
                rendered.append(name)
            else:
                rendered.append(
                    f'{name}="{html.escape(value, quote=True)}"'
                )

        return (
            ""
            if not rendered
            else " " + " ".join(rendered)
        )

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

        class_tokens = set(
            attr_map.get("class", "").split()
        )

        required = {
            "ls-store-btn",
            "ls-store-dmm",
            "ls-store-disabled",
        }

        is_target = (
            tag.casefold() == "span"
            and required.issubset(class_tokens)
            and attr_map.get("aria-disabled")
            == "true"
            and "href" not in attr_map
        )

        if is_target:
            self.match_count += 1
            self.skip_target_data = True
            self.target_depth = 1

            replacement_attrs = [
                (
                    "class",
                    "ls-store-btn ls-store-dmm",
                ),
                ("href", self.final_url),
                ("target", "_blank"),
                (
                    "rel",
                    "nofollow sponsored noopener",
                ),
            ]

            self.output.append(
                "<a"
                + self.serialize_attrs(
                    replacement_attrs
                )
                + ">"
            )
            return

        if self.skip_target_data:
            self.target_depth += 1

        self.output.append(
            "<"
            + tag
            + self.serialize_attrs(attrs)
            + ">"
        )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        self.output.append(
            "<"
            + tag
            + self.serialize_attrs(attrs)
            + " />"
        )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if self.skip_target_data:
            self.target_depth -= 1

            if self.target_depth == 0:
                self.output.append(
                    "DMMブックスで確認</a>"
                )
                self.skip_target_data = False
                return

        self.output.append(
            f"</{tag}>"
        )

    def handle_data(
        self,
        data: str,
    ) -> None:
        if not self.skip_target_data:
            self.output.append(data)

    def handle_entityref(
        self,
        name: str,
    ) -> None:
        if not self.skip_target_data:
            self.output.append(
                f"&{name};"
            )

    def handle_charref(
        self,
        name: str,
    ) -> None:
        if not self.skip_target_data:
            self.output.append(
                f"&#{name};"
            )

    def handle_comment(
        self,
        data: str,
    ) -> None:
        self.output.append(
            f"<!--{data}-->"
        )

    def handle_decl(
        self,
        decl: str,
    ) -> None:
        self.output.append(
            f"<!{decl}>"
        )

    def rewritten_html(self) -> str:
        return "".join(self.output)


def verify_postimage(
    article: dict[str, Any],
    final_url: str,
    identifier: str,
) -> None:
    content_html = article["content_html"]

    require(
        content_html.count(
            "ls-store-btn ls-store-dmm"
        ) == 1,
        "POSTIMAGE_DMM_LINK_COUNT_MISMATCH",
    )
    require(
        "ls-store-dmm ls-store-disabled"
        not in content_html,
        "POSTIMAGE_DISABLED_CLASS_REMAINS",
    )
    require(
        "DMMブックスで確認（再確認待ち）"
        not in content_html,
        "POSTIMAGE_OLD_LABEL_REMAINS",
    )
    require(
        content_html.count(
            "DMMブックスで確認"
        ) == 1,
        "POSTIMAGE_ACTIVE_LABEL_COUNT_MISMATCH",
    )
    require(
        final_url in content_html,
        "POSTIMAGE_FINAL_URL_MISSING",
    )
    require(
        'target="_blank"' in content_html,
        "POSTIMAGE_TARGET_MISSING",
    )
    require(
        'rel="nofollow sponsored noopener"'
        in content_html,
        "POSTIMAGE_REL_MISSING",
    )

    validate_final_url(
        final_url,
        identifier,
    )

    navigation = article[
        "store_navigation"
    ]

    require(
        navigation["render_mode"]
        == "PARTIAL_ACTIVE_STORE_LINKS",
        "POSTIMAGE_RENDER_MODE_MISMATCH",
    )
    require(
        navigation["anchor_elements_included"]
        is True,
        "POSTIMAGE_ANCHOR_STATE_MISMATCH",
    )
    require(
        navigation["href_attributes_included"]
        is True,
        "POSTIMAGE_HREF_STATE_MISMATCH",
    )
    require(
        navigation[
            "final_affiliate_urls_included"
        ] is True,
        "POSTIMAGE_FINAL_URL_STATE_MISMATCH",
    )
    require(
        navigation["dmm_url_included"]
        is True,
        "POSTIMAGE_DMM_URL_STATE_MISMATCH",
    )


def main() -> int:
    boundary_crossed = False
    original_article_bytes: bytes | None = None
    article_replaced = False
    consumption_digest: str | None = None

    try:
        for output in [
            CONSUMPTION,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M9_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_self_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M9",
            "POLICY_PHASE_MISMATCH",
        )

        require(
            file_sha256(ARTICLE)
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_PREIMAGE_SHA_MISMATCH",
        )
        require(
            file_sha256(SECRET_LINK)
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
            "m9_auth": M9_AUTH,
            "m8_review": M8_REVIEW,
            "m8_result": M8_RESULT,
            "m8_fix1_result": M8_FIX1_RESULT,
            "secret_link": SECRET_LINK,
            "m7_consumption": M7_CONSUMPTION,
            "m6_auth": M6_AUTH,
            "m5_review": M5_REVIEW,
            "cred1_result": CRED1_RESULT,
        }

        source_hashes_before = {
            name: file_sha256(path)
            for name, path in source_paths.items()
        }

        m9_auth = load_json(M9_AUTH)
        m8_review = load_json(M8_REVIEW)
        m8_result = load_json(M8_RESULT)
        m8_fix1_result = load_json(
            M8_FIX1_RESULT
        )
        secret_link = load_json(SECRET_LINK)
        m7_consumption = load_json(
            M7_CONSUMPTION
        )
        m6_auth = load_json(M6_AUTH)
        m5_review = load_json(M5_REVIEW)
        cred1 = load_json(CRED1_RESULT)

        verify_self_digest(
            m9_auth,
            "authorization_digest_sha256",
            EXPECTED_M9_AUTH_DIGEST,
        )
        verify_self_digest(
            m8_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M8_REVIEW_DIGEST,
        )
        verify_self_digest(
            secret_link,
            "secret_artifact_digest_sha256",
            EXPECTED_M7_LINK_DIGEST,
        )
        verify_self_digest(
            m7_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M7_CONSUMPTION_DIGEST,
        )
        verify_self_digest(
            m6_auth,
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
            EXPECTED_CRED1_DIGEST,
        )

        require(
            m9_auth["authorization_id"]
            == (
                "DMM_ARTICLE_LINK_INJECTION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "M9_AUTHORIZATION_ID_MISMATCH",
        )
        require(
            m9_auth["single_use"] is True,
            "M9_AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            m9_auth["authorization_consumed"]
            is False,
            "M9_AUTHORIZATION_ALREADY_CONSUMED",
        )
        require(
            m9_auth[
                "authorization_reuse_allowed"
            ] is False,
            "M9_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m9_auth["automatic_retry_allowed"]
            is False,
            "M9_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m8_review["review_verdict"]
            == "APPROVED_NO_CHANGE_REQUIRED",
            "M8_REVIEW_VERDICT_MISMATCH",
        )
        require(
            m8_result[
                "ready_for_ls_new_batch_4g_2e_recovery_m9"
            ] is True,
            "M8_NOT_READY_FOR_M9",
        )
        require(
            m8_fix1_result[
                "ready_for_m9_execute_now_gate"
            ] is True,
            "M8_FIX1_NOT_READY_FOR_M9",
        )
        require(
            m7_consumption[
                "authorization_consumed"
            ] is True,
            "M7_AUTHORIZATION_NOT_CONSUMED",
        )

        identifier = read_identifier()
        verify_commitment(
            identifier,
            cred1,
        )

        final_url = secret_link[
            "final_affiliate_url"
        ]

        require(
            hashlib.sha256(
                final_url.encode("utf-8")
            ).hexdigest()
            == EXPECTED_M7_FINGERPRINT,
            "SECRET_LINK_FINGERPRINT_MISMATCH",
        )

        validate_final_url(
            final_url,
            identifier,
        )

        original_article_bytes = (
            ARTICLE.read_bytes()
        )
        original_article = json.loads(
            original_article_bytes.decode(
                "utf-8"
            )
        )

        original_html = original_article.get(
            "content_html"
        )

        require(
            isinstance(original_html, str),
            "ARTICLE_CONTENT_HTML_MISSING",
        )
        require(
            original_html.count(
                "ls-store-dmm ls-store-disabled"
            ) == 1,
            "DMM_RESERVED_SLOT_COUNT_MISMATCH",
        )
        require(
            "DMMブックスで確認（再確認待ち）"
            in original_html,
            "DMM_RESERVED_SLOT_TEXT_MISSING",
        )
        require(
            "al.dmm.com"
            not in original_html.casefold(),
            "ARTICLE_ALREADY_CONTAINS_DMM_LINK",
        )
        require(
            "af_id="
            not in original_html.casefold(),
            "ARTICLE_ALREADY_CONTAINS_AF_ID",
        )

        attempt_id = str(uuid.uuid4())

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_ARTICLE_LINK_INJECTION_"
                "AUTHORIZATION_CONSUMPTION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M9"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "source_authorization_id": (
                m9_auth["authorization_id"]
            ),
            "source_authorization_digest_sha256": (
                EXPECTED_M9_AUTH_DIGEST
            ),
            "authorization_consumed": True,
            "execution_boundary_crossed": True,
            "consumed_before_article_mutation": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "article_preimage_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "secret_link_file_sha256": (
                EXPECTED_M7_LINK_FILE_SHA
            ),
            "secret_link_artifact_digest_sha256": (
                EXPECTED_M7_LINK_DIGEST
            ),
            "secret_link_fingerprint_sha256": (
                EXPECTED_M7_FINGERPRINT
            ),
            "full_final_url_present": False,
            "affiliate_identifier_present": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "consumed_at_utc": utc_now()
        }

        consumption = copy.deepcopy(
            consumption_without_digest
        )
        consumption[
            "consumption_evidence_digest_sha256"
        ] = digest(consumption_without_digest)

        write_exclusive_json(
            CONSUMPTION,
            consumption,
        )

        boundary_crossed = True
        consumption_digest = consumption[
            "consumption_evidence_digest_sha256"
        ]

        rewriter = DmmSlotRewriter(
            final_url
        )
        rewriter.feed(original_html)
        rewriter.close()

        require(
            rewriter.match_count == 1,
            "DMM_RESERVED_SLOT_REWRITE_COUNT_MISMATCH",
        )

        updated_article = copy.deepcopy(
            original_article
        )
        updated_article["content_html"] = (
            rewriter.rewritten_html()
        )

        navigation = updated_article.get(
            "store_navigation"
        )

        require(
            isinstance(navigation, dict),
            "STORE_NAVIGATION_MISSING",
        )

        navigation[
            "render_mode"
        ] = "PARTIAL_ACTIVE_STORE_LINKS"
        navigation[
            "anchor_elements_included"
        ] = True
        navigation[
            "href_attributes_included"
        ] = True
        navigation[
            "final_affiliate_urls_included"
        ] = True
        navigation[
            "dmm_url_included"
        ] = True

        verify_postimage(
            updated_article,
            final_url,
            identifier,
        )

        updated_bytes = (
            json.dumps(
                updated_article,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

        atomic_replace(
            ARTICLE,
            updated_bytes,
        )
        article_replaced = True

        persisted_article = load_json(
            ARTICLE
        )

        verify_postimage(
            persisted_article,
            final_url,
            identifier,
        )

        require(
            file_sha256(ARTICLE)
            != EXPECTED_ARTICLE_SHA,
            "ARTICLE_POSTIMAGE_SHA_UNCHANGED",
        )

        for name, path in (
            source_paths.items()
        ):
            require(
                file_sha256(path)
                == source_hashes_before[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        article_post_sha = file_sha256(
            ARTICLE
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M9"
            ),
            "status": (
                "PASS_DMM_ARTICLE_LINK_INJECTED_"
                "ONE_SHOT_AUTHORIZATION_CONSUMED_"
                "NO_NETWORK_NO_WORDPRESS"
            ),
            "decision": (
                "ARTICLE_DMM_SLOT_ACTIVATED_READY_"
                "FOR_POST_INJECTION_HUMAN_REVIEW_"
                "AND_PAYLOAD_GATE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "authorization_consumption_path": str(
                CONSUMPTION.relative_to(ROOT)
            ),
            "authorization_consumption_digest_sha256": (
                consumption_digest
            ),
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "article_path": str(
                ARTICLE.relative_to(ROOT)
            ),
            "article_preimage_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "article_postimage_sha256": (
                article_post_sha
            ),
            "article_atomic_replacement_performed": True,
            "article_rollback_performed": False,
            "dmm_reserved_slot_match_count": 1,
            "dmm_active_link_count": 1,
            "dmm_link_scheme_https_verified": True,
            "dmm_link_host_al_dmm_com_verified": True,
            "destination_exact_binding_verified": True,
            "registered_identifier_exact_binding_verified": True,
            "anchor_target_blank_verified": True,
            "anchor_rel_tokens_verified": True,
            "disabled_class_removed": True,
            "aria_disabled_removed": True,
            "store_navigation_render_mode": (
                "PARTIAL_ACTIVE_STORE_LINKS"
            ),
            "store_navigation_anchor_elements_included": True,
            "store_navigation_href_attributes_included": True,
            "store_navigation_final_affiliate_urls_included": True,
            "store_navigation_dmm_url_included": True,
            "full_final_affiliate_url_output": False,
            "full_final_affiliate_url_in_normal_evidence": False,
            "affiliate_identifier_output": False,
            "affiliate_identifier_in_normal_evidence": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "payload_created": False,
            "category_id_injected": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "x_post_performed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ARTICLE_DMM_LINK_INJECTED_"
                "AWAITING_POST_INJECTION_REVIEW"
            ),
            "ready_for_post_injection_human_review": True,
            "ready_for_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "completed_at_utc": utc_now()
        }

        result = copy.deepcopy(
            result_without_digest
        )
        result[
            "result_digest_sha256"
        ] = digest(result_without_digest)

        write_exclusive_json(
            RESULT,
            result,
        )

        write_exclusive_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M9

- Status: `{result["status"]}`
- Authorization consumed: `true`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Article preimage SHA: `{EXPECTED_ARTICLE_SHA}`
- Article postimage SHA: `{article_post_sha}`
- Atomic replacement: `true`
- DMM active link count: `1`
- HTTPS verified: `true`
- al.dmm.com verified: `true`
- Destination binding verified: `true`
- Registered identifier binding verified: `true`
- target=_blank verified: `true`
- rel tokens verified: `true`
- Store navigation updated: `true`
- Full final URL output: `false`
- Affiliate identifier output: `false`
- Network accessed: `false`
- Payload created: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for post-injection human review: `true`
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
            else "UNEXPECTED_M9_EXECUTION_FAILURE"
        )

        rollback_succeeded = False

        if (
            boundary_crossed
            and article_replaced
            and original_article_bytes
            is not None
        ):
            try:
                atomic_replace(
                    ARTICLE,
                    original_article_bytes,
                )

                rollback_succeeded = (
                    file_sha256(ARTICLE)
                    == EXPECTED_ARTICLE_SHA
                )
            except Exception:
                rollback_succeeded = False

        if boundary_crossed:
            failure_without_digest = {
                "schema_version": "1.0.0",
                "phase_id": (
                    "LS-NEW-BATCH-4G-2E-RECOVERY-M9"
                ),
                "status": (
                    "FAILED_AFTER_M9_AUTHORIZATION_"
                    "CONSUMPTION_NO_AUTOMATIC_RETRY"
                ),
                "decision": (
                    "M9_AUTHORIZATION_CONSUMED_"
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
                "article_rollback_attempted": (
                    article_replaced
                ),
                "article_rollback_succeeded": (
                    rollback_succeeded
                ),
                "article_preimage_restored": (
                    rollback_succeeded
                ),
                "full_final_affiliate_url_output": False,
                "affiliate_identifier_output": False,
                "network_connection_performed": False,
                "wordpress_access_performed": False,
                "production_status": "NO_GO",
                "manual_recovery_review_required": True,
                "failed_at_utc": utc_now()
            }

            failure = copy.deepcopy(
                failure_without_digest
            )
            failure[
                "result_digest_sha256"
            ] = digest(failure_without_digest)

            try:
                write_exclusive_json(
                    RESULT,
                    failure,
                )
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
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M9"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_M9_"
                        "AUTHORIZATION_CONSUMPTION"
                    ),
                    "error_code": error_code,
                    "authorization_consumed": False,
                    "article_modified": False,
                    "full_final_affiliate_url_output": False,
                    "affiliate_identifier_output": False,
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
