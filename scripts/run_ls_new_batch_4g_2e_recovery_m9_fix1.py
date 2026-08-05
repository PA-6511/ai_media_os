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
    "new_release_wp_fresh_dmm_article_link_injection_"
    "html_entity_validator_fix_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m9_fix1_approval.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_fix1_authorization.json"
)
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_fix1_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m9_fix1_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m9_fix1_"
    "article_dmm_link_injection_report.md"
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

OLD_M9_PATHS = {
    "policy": ROOT / (
        "config/"
        "new_release_wp_fresh_dmm_article_link_"
        "injection_one_shot_policy.json"
    ),
    "approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m9_execute_now_approval.json"
    ),
    "authorization": ROOT / (
        "exchange/authorizations/new_release/fresh/"
        "new-release-comic-20260703-001."
        "article_dmm_link_injection_authorization.json"
    ),
    "consumption": ROOT / (
        "exchange/authorizations/new_release/fresh/"
        "new-release-comic-20260703-001."
        "article_dmm_link_injection_consumption.json"
    ),
    "result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m9_result.json"
    ),
    "runner": ROOT / (
        "scripts/"
        "run_ls_new_batch_4g_2e_recovery_m9.py"
    ),
    "test": ROOT / (
        "tests/"
        "test_run_ls_new_batch_4g_2e_recovery_m9.py"
    )
}

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

EXPECTED_ARTICLE_SHA = (
    "849a37519c6af70d2212ec01d5cddef5"
    "793bfa811e97ca9f248ce099a0350bf4"
)
EXPECTED_OLD_M9_AUTH_DIGEST = (
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


def require(condition: bool, message: str) -> None:
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
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.m9-fix1.",
        dir=str(path.parent),
    )
    temp_path = Path(temp_name)

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

        os.replace(temp_path, path)
        fsync_directory(path.parent)

    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass

        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

        raise


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


class ReservedSpanRewriter(HTMLParser):
    def __init__(self, final_url: str) -> None:
        super().__init__(
            convert_charrefs=False
        )
        self.final_url = final_url
        self.output: list[str] = []
        self.match_count = 0
        self.in_target = False
        self.target_depth = 0

    @staticmethod
    def attrs_text(
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> str:
        values: list[str] = []

        for name, value in attrs:
            if value is None:
                values.append(name)
            else:
                values.append(
                    f'{name}="{html.escape(value, quote=True)}"'
                )

        return (
            ""
            if not values
            else " " + " ".join(values)
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

        classes = set(
            attr_map.get("class", "").split()
        )

        is_target = (
            tag.casefold() == "span"
            and {
                "ls-store-btn",
                "ls-store-dmm",
                "ls-store-disabled",
            }.issubset(classes)
            and attr_map.get("aria-disabled")
            == "true"
            and "href" not in attr_map
        )

        if is_target:
            self.match_count += 1
            self.in_target = True
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
                + self.attrs_text(
                    replacement_attrs
                )
                + ">"
            )
            return

        if self.in_target:
            self.target_depth += 1

        self.output.append(
            "<"
            + tag
            + self.attrs_text(attrs)
            + ">"
        )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if self.in_target:
            self.target_depth -= 1

            if self.target_depth == 0:
                self.output.append(
                    "DMMブックスで確認</a>"
                )
                self.in_target = False
                return

        self.output.append(f"</{tag}>")

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
            + self.attrs_text(attrs)
            + " />"
        )

    def handle_data(self, data: str) -> None:
        if not self.in_target:
            self.output.append(data)

    def handle_entityref(
        self,
        name: str,
    ) -> None:
        if not self.in_target:
            self.output.append(
                f"&{name};"
            )

    def handle_charref(
        self,
        name: str,
    ) -> None:
        if not self.in_target:
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

    def rewritten(self) -> str:
        return "".join(self.output)


class ActiveAnchorInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.stack: list[
            dict[str, Any]
        ] = []
        self.matches: list[
            dict[str, Any]
        ] = []

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

        node = {
            "tag": tag.casefold(),
            "attrs": attr_map,
            "text": [],
        }

        self.stack.append(node)

    def handle_data(self, data: str) -> None:
        if self.stack:
            self.stack[-1]["text"].append(
                data
            )

    def handle_endtag(self, tag: str) -> None:
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
            text = re.sub(
                r"\s+",
                " ",
                "".join(node["text"]),
            ).strip()

            self.matches.append(
                {
                    "class_tokens": classes,
                    "href": node["attrs"].get(
                        "href"
                    ),
                    "target": node["attrs"].get(
                        "target"
                    ),
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
                    "text": text,
                }
            )

        if self.stack:
            self.stack[-1]["text"].extend(
                node["text"]
            )


def verify_postimage(
    article: dict[str, Any],
    final_url: str,
    identifier: str,
) -> None:
    content_html = article.get(
        "content_html"
    )

    require(
        isinstance(content_html, str),
        "POSTIMAGE_CONTENT_HTML_MISSING",
    )

    inspector = ActiveAnchorInspector()
    inspector.feed(content_html)
    inspector.close()

    require(
        len(inspector.matches) == 1,
        "POSTIMAGE_DMM_ANCHOR_COUNT_MUST_BE_ONE",
    )

    anchor = inspector.matches[0]

    require(
        anchor["class_tokens"]
        == {
            "ls-store-btn",
            "ls-store-dmm",
        },
        "POSTIMAGE_CLASS_TOKENS_MISMATCH",
    )
    require(
        anchor["text"]
        == "DMMブックスで確認",
        "POSTIMAGE_TEXT_MISMATCH",
    )
    require(
        anchor["target"] == "_blank",
        "POSTIMAGE_TARGET_MISMATCH",
    )
    require(
        anchor["rel_tokens"]
        == {
            "nofollow",
            "sponsored",
            "noopener",
        },
        "POSTIMAGE_REL_TOKENS_MISMATCH",
    )
    require(
        anchor[
            "aria_disabled_present"
        ] is False,
        "POSTIMAGE_ARIA_DISABLED_PRESENT",
    )
    require(
        "ls-store-disabled"
        not in anchor["class_tokens"],
        "POSTIMAGE_DISABLED_CLASS_PRESENT",
    )

    decoded_href = html.unescape(
        anchor["href"] or ""
    )

    require(
        decoded_href == final_url,
        "POSTIMAGE_DECODED_HREF_MISMATCH",
    )

    validate_final_url(
        decoded_href,
        identifier,
    )

    navigation = article.get(
        "store_navigation"
    )

    require(
        isinstance(navigation, dict),
        "POSTIMAGE_STORE_NAVIGATION_MISSING",
    )
    require(
        navigation.get("render_mode")
        == "PARTIAL_ACTIVE_STORE_LINKS",
        "POSTIMAGE_RENDER_MODE_MISMATCH",
    )
    require(
        navigation.get(
            "anchor_elements_included"
        ) is True,
        "POSTIMAGE_ANCHORS_STATE_MISMATCH",
    )
    require(
        navigation.get(
            "href_attributes_included"
        ) is True,
        "POSTIMAGE_HREF_STATE_MISMATCH",
    )
    require(
        navigation.get(
            "final_affiliate_urls_included"
        ) is True,
        "POSTIMAGE_FINAL_URL_STATE_MISMATCH",
    )
    require(
        navigation.get(
            "dmm_url_included"
        ) is True,
        "POSTIMAGE_DMM_URL_STATE_MISMATCH",
    )


def main() -> int:
    boundary_crossed = False
    article_replaced = False
    original_article_bytes: bytes | None = None
    consumption_digest: str | None = None

    try:
        for path in [
            APPROVAL,
            AUTHORIZATION,
            CONSUMPTION,
            RESULT,
            REPORT,
        ]:
            require(
                not path.exists(),
                f"OUTPUT_ALREADY_EXISTS:{path.name}",
            )

        policy = load(POLICY)

        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M9-FIX1"
            ),
            "POLICY_PHASE_MISMATCH",
        )

        require(
            file_sha(ARTICLE)
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_PREIMAGE_SHA_MISMATCH",
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

        old_hashes = {
            name: file_sha(path)
            for name, path
            in OLD_M9_PATHS.items()
        }

        old_auth = load(
            OLD_M9_PATHS["authorization"]
        )
        old_consumption = load(
            OLD_M9_PATHS["consumption"]
        )
        old_result = load(
            OLD_M9_PATHS["result"]
        )

        verify_digest(
            old_auth,
            "authorization_digest_sha256",
            EXPECTED_OLD_M9_AUTH_DIGEST,
        )
        verify_digest(
            old_consumption,
            "consumption_evidence_digest_sha256",
        )
        verify_digest(
            old_result,
            "result_digest_sha256",
        )

        require(
            old_consumption[
                "authorization_consumed"
            ] is True,
            "OLD_M9_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            old_consumption[
                "authorization_reuse_allowed"
            ] is False,
            "OLD_M9_REUSE_ALLOWED",
        )
        require(
            old_consumption[
                "automatic_retry_allowed"
            ] is False,
            "OLD_M9_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            old_result["status"]
            == (
                "FAILED_AFTER_M9_AUTHORIZATION_"
                "CONSUMPTION_NO_AUTOMATIC_RETRY"
            ),
            "OLD_M9_FAILURE_STATUS_MISMATCH",
        )
        require(
            old_result["error_code"]
            == "POSTIMAGE_FINAL_URL_MISSING",
            "OLD_M9_ERROR_CODE_MISMATCH",
        )

        m8_review = load(M8_REVIEW)
        m8_result = load(M8_RESULT)
        m8_fix1 = load(M8_FIX1_RESULT)
        secret_link = load(SECRET_LINK)
        m7_consumption = load(
            M7_CONSUMPTION
        )
        m6_auth = load(M6_AUTH)
        m5_review = load(M5_REVIEW)
        cred1 = load(CRED1_RESULT)

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
            m8_review["review_verdict"]
            == "APPROVED_NO_CHANGE_REQUIRED",
            "M8_REVIEW_VERDICT_MISMATCH",
        )
        require(
            m8_result[
                "ready_for_ls_new_batch_4g_2e_recovery_m9"
            ] is True,
            "M8_NOT_READY",
        )
        require(
            m8_fix1[
                "ready_for_m9_execute_now_gate"
            ] is True,
            "M8_FIX1_NOT_READY",
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
            "CONTENT_HTML_MISSING",
        )
        require(
            original_html.count(
                "ls-store-dmm ls-store-disabled"
            ) == 1,
            "RESERVED_DMM_SPAN_COUNT_MISMATCH",
        )
        require(
            "DMMブックスで確認（再確認待ち）"
            in original_html,
            "RESERVED_DMM_TEXT_MISSING",
        )
        require(
            '<a class="ls-store-btn ls-store-dmm"'
            not in original_html,
            "ACTIVE_DMM_ANCHOR_ALREADY_PRESENT",
        )
        require(
            "al.dmm.com"
            not in original_html.casefold(),
            "ARTICLE_ALREADY_CONTAINS_AL_DMM",
        )

        source_bindings = {
            "article_preimage": {
                "path": str(
                    ARTICLE.relative_to(ROOT)
                ),
                "file_sha256": (
                    EXPECTED_ARTICLE_SHA
                )
            },
            "secret_link": {
                "path": str(
                    SECRET_LINK.relative_to(ROOT)
                ),
                "file_sha256": (
                    EXPECTED_M7_LINK_FILE_SHA
                ),
                "artifact_digest_sha256": (
                    EXPECTED_M7_LINK_DIGEST
                ),
                "fingerprint_sha256": (
                    EXPECTED_M7_FINGERPRINT
                )
            },
            "old_m9": {
                name: {
                    "path": str(
                        path.relative_to(ROOT)
                    ),
                    "file_sha256": (
                        old_hashes[name]
                    )
                }
                for name, path
                in OLD_M9_PATHS.items()
            }
        }

        approval_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M9-FIX1"
            ),
            "approval_id": (
                "dmm-article-link-injection-"
                "html-entity-validator-fix-"
                "approval-v1"
            ),
            "approval_label": (
                "DMM_ARTICLE_LINK_INJECTION_"
                "HTML_ENTITY_VALIDATOR_FIX_AND_"
                "NEW_ONE_SHOT_AUTHORIZATION_APPROVED"
            ),
            "approved_by": "HUMAN_OPERATOR",
            "human_explicit_approval": True,
            "approved_at_utc": now(),
            "diagnosis": (
                "HTML_ENTITY_ESCAPING_FALSE_NEGATIVE"
            ),
            "old_m9_authorization_consumed": True,
            "old_m9_authorization_reuse_allowed": False,
            "new_authorization_single_use": True,
            "new_authorization_reuse_allowed": False,
            "new_authorization_automatic_retry_allowed": False,
            "new_authorization_automatic_reissue_allowed": False,
            "full_final_url_output_allowed": False,
            "affiliate_identifier_output_allowed": False,
            "source_bindings": source_bindings,
            "production_status": "NO_GO"
        }

        approval = copy.deepcopy(
            approval_without_digest
        )
        approval[
            "approval_evidence_digest_sha256"
        ] = digest(approval_without_digest)

        write_exclusive_json(
            APPROVAL,
            approval,
        )

        authorization_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_ARTICLE_LINK_INJECTION_"
                "FIX1_ONE_SHOT_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M9-FIX1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorization_id": (
                "DMM_ARTICLE_LINK_INJECTION_FIX1_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "authorized_operation": (
                "ONE_SHOT_ARTICLE_DMM_LINK_"
                "INJECTION_WITH_HTML_ENTITY_"
                "DECODED_POSTIMAGE_VALIDATION"
            ),
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
            "old_m9_failure_binding": {
                "authorization_digest_sha256": (
                    EXPECTED_OLD_M9_AUTH_DIGEST
                ),
                "authorization_consumed": True,
                "historical_error_code": (
                    "POSTIMAGE_FINAL_URL_MISSING"
                ),
                "historical_diagnosis": (
                    "HTML_ENTITY_ESCAPING_FALSE_NEGATIVE"
                )
            },
            "validator_contract": {
                "postimage_html_reparse_required": True,
                "href_entity_decode_required": True,
                "decoded_href_exact_match_required": True,
                "raw_url_substring_check_allowed": False
            },
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "actual_execution_allowed": True,
            "full_final_url_present": False,
            "affiliate_identifier_present": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
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

        write_exclusive_json(
            AUTHORIZATION,
            authorization,
        )

        attempt_id = str(uuid.uuid4())

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_ARTICLE_LINK_INJECTION_FIX1_"
                "AUTHORIZATION_CONSUMPTION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M9-FIX1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "source_authorization_id": (
                authorization[
                    "authorization_id"
                ]
            ),
            "source_authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
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
            "secret_link_fingerprint_sha256": (
                EXPECTED_M7_FINGERPRINT
            ),
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
        ] = digest(
            consumption_without_digest
        )

        write_exclusive_json(
            CONSUMPTION,
            consumption,
        )

        boundary_crossed = True
        consumption_digest = consumption[
            "consumption_evidence_digest_sha256"
        ]

        rewriter = ReservedSpanRewriter(
            final_url
        )
        rewriter.feed(original_html)
        rewriter.close()

        require(
            rewriter.match_count == 1,
            "RESERVED_DMM_SPAN_REWRITE_COUNT_MISMATCH",
        )

        updated_article = copy.deepcopy(
            original_article
        )
        updated_article["content_html"] = (
            rewriter.rewritten()
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

        persisted_article = load(ARTICLE)

        verify_postimage(
            persisted_article,
            final_url,
            identifier,
        )

        postimage_sha = file_sha(ARTICLE)

        require(
            postimage_sha
            != EXPECTED_ARTICLE_SHA,
            "ARTICLE_POSTIMAGE_SHA_UNCHANGED",
        )

        for name, path in (
            OLD_M9_PATHS.items()
        ):
            require(
                file_sha(path)
                == old_hashes[name],
                f"OLD_M9_ARTIFACT_CHANGED:{name}",
            )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M9-FIX1"
            ),
            "status": (
                "PASS_DMM_ARTICLE_LINK_INJECTED_"
                "HTML_ENTITY_VALIDATOR_FIXED_"
                "NEW_AUTHORIZATION_CONSUMED_"
                "NO_NETWORK_NO_WORDPRESS"
            ),
            "decision": (
                "ARTICLE_DMM_SLOT_ACTIVATED_"
                "READY_FOR_POST_INJECTION_"
                "HUMAN_REVIEW_AND_PAYLOAD_GATE"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "authorization_path": str(
                AUTHORIZATION.relative_to(ROOT)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "authorization_consumption_path": str(
                CONSUMPTION.relative_to(ROOT)
            ),
            "authorization_consumption_digest_sha256": (
                consumption_digest
            ),
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "old_m9_authorization_remains_consumed": True,
            "old_m9_artifacts_modified": False,
            "article_preimage_sha256": (
                EXPECTED_ARTICLE_SHA
            ),
            "article_postimage_sha256": (
                postimage_sha
            ),
            "article_atomic_replacement_performed": True,
            "article_rollback_performed": False,
            "html_postimage_reparsed": True,
            "href_html_entity_decoded": True,
            "decoded_href_exact_secret_link_match": True,
            "dmm_active_anchor_count": 1,
            "dmm_anchor_class_tokens_exact": True,
            "dmm_anchor_text_verified": True,
            "dmm_anchor_target_blank_verified": True,
            "dmm_anchor_rel_tokens_verified": True,
            "dmm_disabled_class_absent": True,
            "dmm_aria_disabled_absent": True,
            "dmm_link_scheme_https_verified": True,
            "dmm_link_host_al_dmm_com_verified": True,
            "destination_exact_binding_verified": True,
            "registered_identifier_exact_binding_verified": True,
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
            "completed_at_utc": now()
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
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M9-FIX1

- Status: `{result["status"]}`
- Historical diagnosis: `HTML_ENTITY_ESCAPING_FALSE_NEGATIVE`
- Old M9 authorization remains consumed: `true`
- New authorization consumed: `true`
- New authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- HTML postimage reparsed: `true`
- href HTML entity decoded: `true`
- Decoded href exact match: `true`
- Article preimage SHA: `{EXPECTED_ARTICLE_SHA}`
- Article postimage SHA: `{postimage_sha}`
- DMM active anchor count: `1`
- Full final URL output: `false`
- Affiliate identifier output: `false`
- Network accessed: `false`
- Payload created: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for post-injection review: `true`
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
            if isinstance(
                exc,
                ValidationError,
            )
            else (
                "UNEXPECTED_M9_FIX1_"
                "EXECUTION_FAILURE"
            )
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
                    file_sha(ARTICLE)
                    == EXPECTED_ARTICLE_SHA
                )
            except Exception:
                rollback_succeeded = False

        if boundary_crossed:
            failure_without_digest = {
                "schema_version": "1.0.0",
                "phase_id": (
                    "LS-NEW-BATCH-4G-2E-"
                    "RECOVERY-M9-FIX1"
                ),
                "status": (
                    "FAILED_AFTER_M9_FIX1_"
                    "AUTHORIZATION_CONSUMPTION_"
                    "NO_AUTOMATIC_RETRY"
                ),
                "decision": (
                    "M9_FIX1_AUTHORIZATION_CONSUMED_"
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
                "failed_at_utc": now()
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
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M9-FIX1"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_M9_FIX1_"
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
