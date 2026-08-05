#!/usr/bin/env python3

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import pwd
import socket
import ssl
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_published_post_execution_"
    "evidence_verification_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m18_approval.json"
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
M15_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_post_execution_human_review.json"
)
M15_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m15_result.json"
)
M16_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_authorization.json"
)
M16_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m16_result.json"
)
M17_PRE_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m17_pre_network_result.json"
)
M17_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_consumption.json"
)
M17_SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_response.json"
)
M17_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m17_result.json"
)

WRITER_CREDENTIAL = Path(
    "/etc/ai-media-os/credential.env"
)

RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m18_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m18_"
    "wordpress_published_post_execution_evidence_report.md"
)

EXPECTED_POST_ID = 192
EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
)
EXPECTED_ATTEMPT_ID = (
    "f5f1d087-83b6-40bb-9d21-05e437d99625"
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
EXPECTED_M15_REVIEW_DIGEST = (
    "be8aafa191df793ecbe2695b662378fe"
    "f078ce42ae4169a93651a9d2b6141d4c"
)
EXPECTED_M15_RESULT_DIGEST = (
    "03d777e3e34c4d68c4b55027db87f7b"
    "20cee59f947640f3d68b125d6c79f5b06"
)
EXPECTED_M16_AUTH_FILE_SHA = (
    "0b8eb340f4551497e99d91dc64ab5d47"
    "c149efb098d50ebf6cf981d416624e58"
)
EXPECTED_M16_AUTH_DIGEST = (
    "3af20632d3fabe77f04e795318406ecd"
    "0ad9bd7b6d2eb60646e82f108556cc9e"
)
EXPECTED_M16_RESULT_DIGEST = (
    "9eda577486ceaf77be2baf0346cf7152"
    "ff3e5113bd091625715e487224c3150a"
)
EXPECTED_M17_PRE_RESULT_DIGEST = (
    "f2650043127b69ef5d6cc1b539a7f2fe"
    "523f2d53d53ea0cfdd37b0b81a6b8944"
)
EXPECTED_M17_CONSUMPTION_DIGEST = (
    "9fa836ec2fe8c49b160101351e5a913b"
    "0c606af857131b5a0550b81fb04f443e"
)
EXPECTED_M17_RESULT_DIGEST = (
    "e405bd6b44b45c8246388b0ea2fa55ac"
    "501e728563cf97d9b82be6c5dad2e93e"
)

REQUIRED_CREDENTIAL_KEYS = (
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
)

MAX_RESPONSE_BYTES = 16 * 1024 * 1024


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
        digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"DIGEST_EXPECTED_MISMATCH:{field}",
        )

    return stored


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
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


def atomic_write_text(
    path: Path,
    value: str,
) -> None:
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


def normalize_env_value(
    raw_value: str,
) -> str:
    value = raw_value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    return value


def read_writer_credentials(
    path: Path,
) -> tuple[
    dict[str, str],
    os.stat_result,
]:
    require(
        path.exists(),
        "WRITER_CREDENTIAL_MISSING",
    )

    before = path.lstat()

    require(
        not stat.S_ISLNK(before.st_mode),
        "WRITER_CREDENTIAL_SYMLINK_REJECTED",
    )
    require(
        stat.S_ISREG(before.st_mode),
        "WRITER_CREDENTIAL_NOT_REGULAR_FILE",
    )
    require(
        stat.S_IMODE(before.st_mode) == 0o600,
        "WRITER_CREDENTIAL_MODE_NOT_0600",
    )
    require(
        before.st_uid == os.geteuid(),
        "WRITER_CREDENTIAL_OWNER_UID_MISMATCH",
    )
    require(
        pwd.getpwuid(before.st_uid).pw_name
        == "deploy",
        "WRITER_CREDENTIAL_OWNER_NOT_DEPLOY",
    )

    values: dict[str, list[str]] = {
        key: []
        for key in REQUIRED_CREDENTIAL_KEYS
    }

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for raw_line in handle:
                require(
                    "\x00" not in raw_line,
                    "WRITER_CREDENTIAL_CONTAINS_NUL",
                )

                line = raw_line.strip()

                if (
                    not line
                    or line.startswith("#")
                ):
                    continue

                if line.startswith("export "):
                    line = line[7:].lstrip()

                key, separator, raw_value = (
                    line.partition("=")
                )
                key = key.strip()

                if (
                    separator == "="
                    and key in values
                ):
                    values[key].append(
                        normalize_env_value(
                            raw_value
                        )
                    )

    except UnicodeDecodeError:
        raise ValidationError(
            "WRITER_CREDENTIAL_ENCODING_INVALID"
        ) from None

    for key in REQUIRED_CREDENTIAL_KEYS:
        require(
            len(values[key]) == 1,
            "REQUIRED_WRITER_KEY_COUNT_MISMATCH",
        )
        require(
            values[key][0] != "",
            "REQUIRED_WRITER_VALUE_EMPTY",
        )

    return {
        key: values[key][0]
        for key in REQUIRED_CREDENTIAL_KEYS
    }, before


def same_metadata(
    before: os.stat_result,
    after: os.stat_result,
) -> bool:
    return (
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_size,
        before.st_mtime_ns,
    ) == (
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_gid,
        after.st_size,
        after.st_mtime_ns,
    )


def validate_base_url(
    base_url: str,
) -> str:
    parsed = urllib.parse.urlsplit(
        base_url
    )

    require(
        parsed.scheme.casefold() == "https",
        "WORDPRESS_BASE_URL_SCHEME_INVALID",
    )
    require(
        parsed.hostname == "hoshido.jp",
        "WORDPRESS_BASE_URL_HOST_INVALID",
    )
    require(
        parsed.port is None,
        "WORDPRESS_BASE_URL_EXPLICIT_PORT_REJECTED",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "WORDPRESS_BASE_URL_USERINFO_REJECTED",
    )
    require(
        parsed.path in {"", "/"},
        "WORDPRESS_BASE_URL_PATH_REJECTED",
    )
    require(
        parsed.query == "",
        "WORDPRESS_BASE_URL_QUERY_REJECTED",
    )
    require(
        parsed.fragment == "",
        "WORDPRESS_BASE_URL_FRAGMENT_REJECTED",
    )

    return "https://hoshido.jp"


def build_request_url(
    origin: str,
) -> str:
    query = urllib.parse.urlencode(
        [
            ("context", "edit"),
            (
                "_fields",
                "id,status,title,content,categories",
            ),
        ]
    )

    return (
        origin
        + "/wp-json/wp/v2/posts/192?"
        + query
    )


def validate_request_url(
    url: str,
) -> None:
    parsed = urllib.parse.urlsplit(url)

    require(
        parsed.scheme == "https",
        "REQUEST_URL_SCHEME_INVALID",
    )
    require(
        parsed.hostname == "hoshido.jp",
        "REQUEST_URL_HOST_INVALID",
    )
    require(
        parsed.port is None,
        "REQUEST_URL_EXPLICIT_PORT_REJECTED",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "REQUEST_URL_USERINFO_REJECTED",
    )
    require(
        parsed.fragment == "",
        "REQUEST_URL_FRAGMENT_REJECTED",
    )
    require(
        parsed.path
        == "/wp-json/wp/v2/posts/192",
        "REQUEST_URL_PATH_MISMATCH",
    )
    require(
        urllib.parse.parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        ) == [
            ("context", "edit"),
            (
                "_fields",
                "id,status,title,content,categories",
            ),
        ],
        "REQUEST_URL_QUERY_MISMATCH",
    )


class NoRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise ValidationError(
            "REDIRECT_BLOCKED"
        )


class WordPressSingleGetClient:
    def __init__(
        self,
        origin: str,
        authorization_header: str,
    ) -> None:
        self.origin = origin
        self.authorization_header = (
            authorization_header
        )
        self.get_request_count = 0
        self.non_get_request_count = 0
        self.last_http_status: int | None = None

        context = ssl.create_default_context()

        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            NoRedirectHandler(),
            urllib.request.HTTPSHandler(
                context=context
            ),
        )

    def get_post(
        self,
    ) -> tuple[
        dict[str, Any],
        int,
    ]:
        require(
            self.get_request_count == 0,
            "WORDPRESS_GET_ALREADY_USED",
        )
        require(
            self.non_get_request_count == 0,
            "NON_GET_REQUEST_ALREADY_RECORDED",
        )

        url = build_request_url(
            self.origin
        )
        validate_request_url(url)

        request = urllib.request.Request(
            url=url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": (
                    self.authorization_header
                ),
                "User-Agent": (
                    "ai-media-os-m18/1.0"
                ),
                "Cache-Control": "no-store",
            },
        )

        require(
            request.get_method() == "GET",
            "NON_GET_REQUEST_BLOCKED",
        )

        self.get_request_count += 1

        try:
            with self.opener.open(
                request,
                timeout=20,
            ) as response:
                status_code = int(
                    response.getcode()
                )
                self.last_http_status = (
                    status_code
                )

                require(
                    status_code == 200,
                    (
                        "WORDPRESS_POST_GET_"
                        f"HTTP_STATUS_{status_code}"
                    ),
                )
                require(
                    response.geturl() == url,
                    "FINAL_RESPONSE_URL_CHANGED",
                )

                validate_request_url(
                    response.geturl()
                )

                content_type = (
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                    .split(";", 1)[0]
                    .strip()
                    .casefold()
                )

                require(
                    content_type
                    in {
                        "application/json",
                        "application/hal+json",
                    },
                    "UNEXPECTED_RESPONSE_CONTENT_TYPE",
                )

                body = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

                require(
                    len(body)
                    <= MAX_RESPONSE_BYTES,
                    "WORDPRESS_RESPONSE_TOO_LARGE",
                )

                try:
                    parsed = json.loads(
                        body.decode("utf-8")
                    )
                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ):
                    raise ValidationError(
                        "WORDPRESS_RESPONSE_JSON_PARSE_FAILED"
                    ) from None

                require(
                    isinstance(parsed, dict),
                    "WORDPRESS_POST_RESPONSE_NOT_OBJECT",
                )

                return parsed, status_code

        except ValidationError:
            raise

        except urllib.error.HTTPError as exc:
            code = int(exc.code)
            self.last_http_status = code

            try:
                exc.close()
            except Exception:
                pass

            raise ValidationError(
                (
                    "WORDPRESS_POST_GET_"
                    f"HTTP_STATUS_{code}"
                )
            ) from None

        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ssl.SSLError,
        ):
            raise ValidationError(
                "WORDPRESS_POST_GET_NETWORK_FAILED"
            ) from None


def build_result(
    *,
    status: str,
    decision: str,
    error_code: str | None,
    get_request_count: int,
    http_status: int | None,
    writer_credential_accessed: bool,
    writer_credential_verified: bool,
    post_id_verified: bool,
    published_status_verified: bool,
    title_exact_match: bool,
    content_exact_match: bool,
    category_id_10_verified: bool,
    m17_secret_response_digest: str | None,
    m17_secret_response_file_sha: str | None,
    ready_for_human_review: bool,
) -> dict[str, Any]:
    access_performed = (
        get_request_count > 0
    )

    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M18"
        ),
        "status": status,
        "decision": decision,
        "error_code": error_code,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "post_id_verified": post_id_verified,
        "wordpress_post_status": (
            "publish"
            if published_status_verified
            else None
        ),
        "published_status_verified": (
            published_status_verified
        ),
        "title_exact_match": (
            title_exact_match
        ),
        "content_exact_match": (
            content_exact_match
        ),
        "category_id_10_verified": (
            category_id_10_verified
        ),
        "wordpress_published": (
            published_status_verified
        ),
        "wordpress_http_status": http_status,
        "wordpress_get_request_count": (
            get_request_count
        ),
        "wordpress_non_get_request_count": 0,
        "automatic_retry_performed": False,
        "network_connection_performed": (
            access_performed
        ),
        "http_request_performed": (
            access_performed
        ),
        "wordpress_access_performed": (
            access_performed
        ),
        "connection_scheme_https": True,
        "connection_host_hoshido_jp": True,
        "proxy_used": False,
        "redirect_followed": False,
        "writer_credential_accessed": (
            writer_credential_accessed
        ),
        "writer_credential_structure_verified": (
            writer_credential_verified
        ),
        "writer_credential_file_modified": False,
        "m17_execution_attempt_id": (
            EXPECTED_ATTEMPT_ID
        ),
        "m17_result_digest_sha256": (
            EXPECTED_M17_RESULT_DIGEST
        ),
        "m17_consumption_digest_sha256": (
            EXPECTED_M17_CONSUMPTION_DIGEST
        ),
        "m17_pre_network_result_digest_sha256": (
            EXPECTED_M17_PRE_RESULT_DIGEST
        ),
        "m17_secret_response_digest_sha256": (
            m17_secret_response_digest
        ),
        "m17_secret_response_file_sha256": (
            m17_secret_response_file_sha
        ),
        "m17_authorization_consumed": True,
        "m17_authorization_reuse_allowed": False,
        "m17_automatic_retry_allowed": False,
        "m17_automatic_reissue_allowed": False,
        "m16_authorization_issuance_file_sha256": (
            EXPECTED_M16_AUTH_FILE_SHA
        ),
        "m16_authorization_digest_sha256": (
            EXPECTED_M16_AUTH_DIGEST
        ),
        "m16_authorization_issuance_artifact_consumed_state": False,
        "authorization_consumed_in_this_phase": False,
        "authorization_reused_in_this_phase": False,
        "authorization_reissued_in_this_phase": False,
        "payload_file_sha256": (
            EXPECTED_PAYLOAD_SHA
        ),
        "payload_digest_sha256": (
            EXPECTED_PAYLOAD_DIGEST
        ),
        "article_file_sha256": (
            EXPECTED_ARTICLE_SHA
        ),
        "m15_result_digest_sha256": (
            EXPECTED_M15_RESULT_DIGEST
        ),
        "m15_human_review_digest_sha256": (
            EXPECTED_M15_REVIEW_DIGEST
        ),
        "source_artifacts_modified": False,
        "credential_values_output": False,
        "username_output": False,
        "application_password_output": False,
        "authorization_header_output": False,
        "credential_file_content_output": False,
        "full_wordpress_response_output": False,
        "full_post_content_output": False,
        "full_payload_output": False,
        "full_affiliate_url_output": False,
        "dmm_identifier_output": False,
        "wordpress_write_performed": False,
        "wordpress_update_performed": False,
        "wordpress_republish_performed": False,
        "wordpress_delete_performed": False,
        "wordpress_post_recreated": False,
        "category_operation_performed": False,
        "media_operation_performed": False,
        "m17_rerun_performed": False,
        "x_post_performed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "WORDPRESS_PUBLISHED_POST_192_"
            "EVIDENCE_VERIFIED_AWAITING_HUMAN_REVIEW"
            if ready_for_human_review
            else (
                "WORDPRESS_PUBLISHED_POST_"
                "EVIDENCE_VERIFICATION_BLOCKED_NO_WRITE"
            )
        ),
        "ready_for_post_publication_human_review": (
            ready_for_human_review
        ),
        "ready_for_wordpress_publish": False,
        "completed_at_utc": now()
    }

    result = copy.deepcopy(
        result_without_digest
    )
    result[
        "result_digest_sha256"
    ] = digest(result_without_digest)

    return result


def write_outputs(
    result: dict[str, Any],
) -> None:
    atomic_write_json(
        RESULT,
        result,
    )

    atomic_write_text(
        REPORT,
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M18

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Error code: `{result["error_code"]}`
- WordPress post ID: `192`
- Post ID verified: `{str(result["post_id_verified"]).lower()}`
- WordPress post status: `{result["wordpress_post_status"]}`
- Published status verified: `{str(result["published_status_verified"]).lower()}`
- Title exact match: `{str(result["title_exact_match"]).lower()}`
- Content exact match: `{str(result["content_exact_match"]).lower()}`
- Category ID 10 verified: `{str(result["category_id_10_verified"]).lower()}`
- WordPress HTTP status: `{result["wordpress_http_status"]}`
- WordPress GET request count: `{result["wordpress_get_request_count"]}`
- WordPress non-GET request count: `0`
- Automatic retry performed: `false`
- M17 authorization consumed: `true`
- Authorization consumed in M18: `false`
- Authorization reused in M18: `false`
- WordPress write performed: `false`
- WordPress update performed: `false`
- WordPress republish performed: `false`
- WordPress delete performed: `false`
- Production status: `NO_GO`
- Ready for post-publication human review: `{str(result["ready_for_post_publication_human_review"]).lower()}`
""",
    )


def main() -> int:
    source_paths = {
        "article": ARTICLE,
        "payload": PAYLOAD,
        "m15_review": M15_REVIEW,
        "m15_result": M15_RESULT,
        "m16_authorization": M16_AUTH,
        "m16_result": M16_RESULT,
        "m17_pre_network_result": (
            M17_PRE_RESULT
        ),
        "m17_consumption": (
            M17_CONSUMPTION
        ),
        "m17_secret_response": (
            M17_SECRET_RESPONSE
        ),
        "m17_result": M17_RESULT,
    }

    source_hashes: dict[str, str] = {}
    credential_before: (
        os.stat_result | None
    ) = None
    client: (
        WordPressSingleGetClient | None
    ) = None

    writer_credential_accessed = False
    writer_credential_verified = False
    m17_secret_response_digest: (
        str | None
    ) = None
    m17_secret_response_file_sha: (
        str | None
    ) = None

    try:
        require(
            not RESULT.exists(),
            "M18_RESULT_ALREADY_EXISTS",
        )
        require(
            not REPORT.exists(),
            "M18_REPORT_ALREADY_EXISTS",
        )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M18"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_PUBLISHED_POST_EXECUTION_"
                "EVIDENCE_VERIFICATION_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            approval[
                "human_explicit_approval"
            ] is True,
            "HUMAN_EXPLICIT_APPROVAL_FALSE",
        )
        require(
            approval[
                "maximum_get_request_count"
            ] == 1,
            "APPROVAL_GET_LIMIT_MISMATCH",
        )
        require(
            approval[
                "non_get_request_allowed"
            ] is False,
            "APPROVAL_NON_GET_ALLOWED",
        )
        require(
            approval[
                "wordpress_write_approved"
            ] is False,
            "WORDPRESS_WRITE_APPROVED",
        )
        require(
            approval[
                "wordpress_republish_approved"
            ] is False,
            "WORDPRESS_REPUBLISH_APPROVED",
        )
        require(
            approval[
                "authorization_reuse_approved"
            ] is False,
            "AUTHORIZATION_REUSE_APPROVED",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        bindings = approval[
            "source_bindings"
        ]

        for name, path in source_paths.items():
            require(
                bindings[name]["file_sha256"]
                == source_hashes[name],
                f"APPROVAL_SOURCE_SHA_MISMATCH:{name}",
            )
            require(
                bindings[name]["path"]
                == str(path.relative_to(ROOT)),
                f"APPROVAL_SOURCE_PATH_MISMATCH:{name}",
            )

        require(
            source_hashes["article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["payload"]
            == EXPECTED_PAYLOAD_SHA,
            "PAYLOAD_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes[
                "m16_authorization"
            ] == EXPECTED_M16_AUTH_FILE_SHA,
            "M16_AUTHORIZATION_FILE_SHA_MISMATCH",
        )

        m17_secret_response_file_sha = (
            source_hashes[
                "m17_secret_response"
            ]
        )

        require(
            stat.S_IMODE(
                PAYLOAD.stat().st_mode
            ) == 0o600,
            "PAYLOAD_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M16_AUTH.stat().st_mode
            ) == 0o600,
            "M16_AUTHORIZATION_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M17_CONSUMPTION.stat().st_mode
            ) == 0o600,
            "M17_CONSUMPTION_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M17_SECRET_RESPONSE.stat().st_mode
            ) == 0o600,
            "M17_SECRET_RESPONSE_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M17_RESULT.stat().st_mode
            ) == 0o600,
            "M17_RESULT_MODE_NOT_0600",
        )

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        m15_review = load_json(
            M15_REVIEW
        )
        m15_result = load_json(
            M15_RESULT
        )
        m16_auth = load_json(M16_AUTH)
        m16_result = load_json(
            M16_RESULT
        )
        m17_pre_result = load_json(
            M17_PRE_RESULT
        )
        m17_consumption = load_json(
            M17_CONSUMPTION
        )
        m17_secret_response = load_json(
            M17_SECRET_RESPONSE
        )
        m17_result = load_json(
            M17_RESULT
        )

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            m15_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M15_REVIEW_DIGEST,
        )
        verify_digest(
            m15_result,
            "result_digest_sha256",
            EXPECTED_M15_RESULT_DIGEST,
        )
        verify_digest(
            m16_auth,
            "authorization_digest_sha256",
            EXPECTED_M16_AUTH_DIGEST,
        )
        verify_digest(
            m16_result,
            "result_digest_sha256",
            EXPECTED_M16_RESULT_DIGEST,
        )
        verify_digest(
            m17_pre_result,
            "result_digest_sha256",
            EXPECTED_M17_PRE_RESULT_DIGEST,
        )
        verify_digest(
            m17_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M17_CONSUMPTION_DIGEST,
        )
        m17_secret_response_digest = (
            verify_digest(
                m17_secret_response,
                "secret_response_digest_sha256",
            )
        )
        verify_digest(
            m17_result,
            "result_digest_sha256",
            EXPECTED_M17_RESULT_DIGEST,
        )

        require(
            m17_result["status"]
            == (
                "PASS_WORDPRESS_PUBLICATION_"
                "ONE_SHOT_AUTHORIZATION_CONSUMED_"
                "POST_192_PUBLISHED_NO_RETRY"
            ),
            "M17_RESULT_STATUS_MISMATCH",
        )
        require(
            m17_result[
                "execution_attempt_id"
            ] == EXPECTED_ATTEMPT_ID,
            "M17_ATTEMPT_ID_MISMATCH",
        )
        require(
            m17_result[
                "wordpress_post_id"
            ] == EXPECTED_POST_ID,
            "M17_POST_ID_MISMATCH",
        )
        require(
            m17_result[
                "authorization_consumed"
            ] is True,
            "M17_AUTHORIZATION_NOT_CONSUMED",
        )
        require(
            m17_result[
                "authorization_reuse_allowed"
            ] is False,
            "M17_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m17_result[
                "automatic_retry_allowed"
            ] is False,
            "M17_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m17_result[
                "automatic_reissue_allowed"
            ] is False,
            "M17_AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            m17_result[
                "pre_publication_get_request_count"
            ] == 1,
            "M17_PRE_GET_COUNT_MISMATCH",
        )
        require(
            m17_result[
                "publication_post_request_count"
            ] == 1,
            "M17_PUBLICATION_POST_COUNT_MISMATCH",
        )
        require(
            m17_result[
                "wordpress_http_status"
            ] == 200,
            "M17_HTTP_STATUS_MISMATCH",
        )
        require(
            m17_result[
                "returned_wordpress_status"
            ] == "publish",
            "M17_RETURNED_STATUS_MISMATCH",
        )
        require(
            m17_result[
                "post_id_verified"
            ] is True,
            "M17_POST_ID_NOT_VERIFIED",
        )
        require(
            m17_result[
                "title_exact_match"
            ] is True,
            "M17_TITLE_MISMATCH",
        )
        require(
            m17_result[
                "content_exact_match"
            ] is True,
            "M17_CONTENT_MISMATCH",
        )
        require(
            m17_result[
                "category_id_10_verified"
            ] is True,
            "M17_CATEGORY_MISMATCH",
        )
        require(
            m17_result[
                "publication_verified"
            ] is True,
            "M17_PUBLICATION_NOT_VERIFIED",
        )
        require(
            m17_result[
                "publication_result_unknown"
            ] is False,
            "M17_PUBLICATION_RESULT_UNKNOWN",
        )
        require(
            m17_result[
                "wordpress_published"
            ] is True,
            "M17_WORDPRESS_PUBLISHED_FALSE",
        )
        require(
            m17_result[
                "publication_count"
            ] == 1,
            "M17_PUBLICATION_COUNT_MISMATCH",
        )
        require(
            m17_result[
                "publication_request_status_only"
            ] is True,
            "M17_REQUEST_NOT_STATUS_ONLY",
        )
        require(
            m17_result[
                "title_field_sent"
            ] is False,
            "M17_TITLE_FIELD_SENT",
        )
        require(
            m17_result[
                "content_field_sent"
            ] is False,
            "M17_CONTENT_FIELD_SENT",
        )
        require(
            m17_result[
                "categories_field_sent"
            ] is False,
            "M17_CATEGORIES_FIELD_SENT",
        )
        require(
            m17_result[
                "ready_for_post_publication_evidence_review"
            ] is True,
            "M17_POST_PUBLICATION_REVIEW_NOT_READY",
        )

        require(
            m17_consumption[
                "execution_attempt_id"
            ] == EXPECTED_ATTEMPT_ID,
            "M17_CONSUMPTION_ATTEMPT_ID_MISMATCH",
        )
        require(
            m17_consumption[
                "source_authorization_file_sha256"
            ] == EXPECTED_M16_AUTH_FILE_SHA,
            "M17_CONSUMPTION_AUTH_FILE_SHA_MISMATCH",
        )
        require(
            m17_consumption[
                "source_authorization_digest_sha256"
            ] == EXPECTED_M16_AUTH_DIGEST,
            "M17_CONSUMPTION_AUTH_DIGEST_MISMATCH",
        )
        require(
            m17_consumption[
                "pre_publication_get_completed"
            ] is True,
            "M17_PRE_PUBLICATION_GET_INCOMPLETE",
        )
        require(
            m17_consumption[
                "pre_publication_post_id_verified"
            ] is True,
            "M17_PRE_POST_ID_NOT_VERIFIED",
        )
        require(
            m17_consumption[
                "pre_publication_status_draft_verified"
            ] is True,
            "M17_PRE_DRAFT_NOT_VERIFIED",
        )
        require(
            m17_consumption[
                "pre_publication_title_exact_match"
            ] is True,
            "M17_PRE_TITLE_MISMATCH",
        )
        require(
            m17_consumption[
                "pre_publication_content_exact_match"
            ] is True,
            "M17_PRE_CONTENT_MISMATCH",
        )
        require(
            m17_consumption[
                "pre_publication_category_id_10_verified"
            ] is True,
            "M17_PRE_CATEGORY_MISMATCH",
        )
        require(
            m17_consumption[
                "authorization_consumed"
            ] is True,
            "M17_CONSUMPTION_STATE_FALSE",
        )
        require(
            m17_consumption[
                "authorization_reuse_allowed"
            ] is False,
            "M17_CONSUMPTION_REUSE_ALLOWED",
        )
        require(
            m17_consumption[
                "automatic_retry_allowed"
            ] is False,
            "M17_CONSUMPTION_RETRY_ALLOWED",
        )
        require(
            m17_consumption[
                "automatic_reissue_allowed"
            ] is False,
            "M17_CONSUMPTION_REISSUE_ALLOWED",
        )
        require(
            m17_consumption[
                "maximum_publish_count"
            ] == 1,
            "M17_CONSUMPTION_MAX_COUNT_MISMATCH",
        )

        require(
            m17_secret_response[
                "phase_id"
            ] == (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
            ),
            "M17_SECRET_PHASE_MISMATCH",
        )
        require(
            m17_secret_response[
                "document_role"
            ] == (
                "SECRET_WORDPRESS_PUBLICATION_RESPONSE"
            ),
            "M17_SECRET_ROLE_MISMATCH",
        )
        require(
            m17_secret_response[
                "execution_attempt_id"
            ] == EXPECTED_ATTEMPT_ID,
            "M17_SECRET_ATTEMPT_ID_MISMATCH",
        )
        require(
            m17_secret_response[
                "wordpress_post_id"
            ] == EXPECTED_POST_ID,
            "M17_SECRET_POST_ID_MISMATCH",
        )
        require(
            m17_secret_response[
                "response_received"
            ] is True,
            "M17_SECRET_RESPONSE_NOT_RECEIVED",
        )
        require(
            m17_secret_response[
                "http_status"
            ] == 200,
            "M17_SECRET_HTTP_STATUS_MISMATCH",
        )
        require(
            m17_secret_response[
                "final_response_url_verified"
            ] is True,
            "M17_SECRET_URL_NOT_VERIFIED",
        )
        require(
            m17_secret_response[
                "error_code"
            ] is None,
            "M17_SECRET_ERROR_PRESENT",
        )

        require(
            m16_auth[
                "authorization_id"
            ] == (
                "WORDPRESS_PUBLICATION_ONE_SHOT_"
                "AUTHORIZATION_V1"
            ),
            "M16_AUTHORIZATION_ID_MISMATCH",
        )
        require(
            m16_auth[
                "authorization_consumed"
            ] is False,
            "M16_ISSUANCE_ARTIFACT_CHANGED",
        )
        require(
            m16_auth[
                "authorization_reuse_allowed"
            ] is False,
            "M16_AUTHORIZATION_REUSE_ALLOWED",
        )

        require(
            m15_review[
                "review_verdict"
            ] == "APPROVED_NO_CHANGE_REQUIRED",
            "M15_REVIEW_VERDICT_MISMATCH",
        )
        require(
            m15_review[
                "human_review_complete"
            ] is True,
            "M15_HUMAN_REVIEW_INCOMPLETE",
        )

        require(
            payload["title"]
            == EXPECTED_TITLE,
            "PAYLOAD_TITLE_MISMATCH",
        )
        require(
            payload["title"]
            == article["article_title"],
            "ARTICLE_TITLE_MISMATCH",
        )
        require(
            payload["content_html"]
            == article["content_html"],
            "ARTICLE_CONTENT_MISMATCH",
        )
        require(
            payload["categories"] == [10],
            "PAYLOAD_CATEGORIES_MISMATCH",
        )
        require(
            payload["category_id"] == 10,
            "PAYLOAD_CATEGORY_ID_MISMATCH",
        )

        credentials, credential_before = (
            read_writer_credentials(
                WRITER_CREDENTIAL
            )
        )
        writer_credential_accessed = True
        writer_credential_verified = True

        origin = validate_base_url(
            credentials[
                "WORDPRESS_BASE_URL"
            ]
        )

        credential_pair = (
            credentials[
                "WORDPRESS_USERNAME"
            ]
            + ":"
            + credentials[
                "WORDPRESS_APP_PASSWORD"
            ]
        )

        authorization_header = (
            "Basic "
            + base64.b64encode(
                credential_pair.encode(
                    "utf-8"
                )
            ).decode("ascii")
        )

        client = WordPressSingleGetClient(
            origin=origin,
            authorization_header=(
                authorization_header
            ),
        )

        post_data, http_status = (
            client.get_post()
        )

        require(
            client.get_request_count == 1,
            "WORDPRESS_GET_COUNT_NOT_ONE",
        )
        require(
            client.non_get_request_count
            == 0,
            "WORDPRESS_NON_GET_COUNT_NOT_ZERO",
        )

        response_id = post_data.get("id")
        response_status = post_data.get(
            "status"
        )
        response_title = post_data.get(
            "title"
        )
        response_content = post_data.get(
            "content"
        )
        response_categories = post_data.get(
            "categories"
        )

        require(
            response_id == EXPECTED_POST_ID,
            "POST_ID_192_MISMATCH",
        )
        require(
            response_status == "publish",
            "POST_STATUS_NOT_PUBLISH",
        )
        require(
            isinstance(
                response_title,
                dict,
            ),
            "POST_TITLE_OBJECT_MISSING",
        )
        require(
            isinstance(
                response_title.get("raw"),
                str,
            ),
            "POST_TITLE_RAW_UNAVAILABLE",
        )
        require(
            response_title["raw"]
            == payload["title"],
            "POST_TITLE_EXACT_MISMATCH",
        )
        require(
            isinstance(
                response_content,
                dict,
            ),
            "POST_CONTENT_OBJECT_MISSING",
        )
        require(
            isinstance(
                response_content.get("raw"),
                str,
            ),
            "POST_CONTENT_RAW_UNAVAILABLE",
        )
        require(
            response_content["raw"]
            == payload["content_html"],
            "POST_CONTENT_EXACT_MISMATCH",
        )
        require(
            isinstance(
                response_categories,
                list,
            ),
            "POST_CATEGORIES_NOT_ARRAY",
        )
        require(
            response_categories == [10],
            "POST_CATEGORIES_EXACT_MISMATCH",
        )

        require(
            credential_before is not None
            and same_metadata(
                credential_before,
                WRITER_CREDENTIAL.lstat(),
            ),
            "WRITER_CREDENTIAL_METADATA_CHANGED",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        result = build_result(
            status=(
                "PASS_WORDPRESS_PUBLISHED_POST_"
                "EXECUTION_EVIDENCE_VERIFIED_"
                "GET_ONLY_NO_WRITE"
            ),
            decision=(
                "WORDPRESS_POST_192_PUBLISHED_STATE_"
                "VERIFIED_READY_FOR_POST_PUBLICATION_"
                "HUMAN_REVIEW"
            ),
            error_code=None,
            get_request_count=1,
            http_status=http_status,
            writer_credential_accessed=True,
            writer_credential_verified=True,
            post_id_verified=True,
            published_status_verified=True,
            title_exact_match=True,
            content_exact_match=True,
            category_id_10_verified=True,
            m17_secret_response_digest=(
                m17_secret_response_digest
            ),
            m17_secret_response_file_sha=(
                m17_secret_response_file_sha
            ),
            ready_for_human_review=True,
        )

        write_outputs(result)

        del credentials
        del credential_pair
        del authorization_header
        del post_data
        del response_content

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        get_count = (
            client.get_request_count
            if client is not None
            else 0
        )
        http_status = (
            client.last_http_status
            if client is not None
            else None
        )

        result = build_result(
            status=(
                "BLOCKED_WORDPRESS_PUBLISHED_POST_"
                "EXECUTION_EVIDENCE_VERIFICATION_"
                "NO_WRITE"
            ),
            decision=(
                "FAIL_CLOSED_POST_PUBLICATION_"
                "HUMAN_REVIEW_NOT_READY"
            ),
            error_code=str(exc),
            get_request_count=get_count,
            http_status=http_status,
            writer_credential_accessed=(
                writer_credential_accessed
            ),
            writer_credential_verified=(
                writer_credential_verified
            ),
            post_id_verified=False,
            published_status_verified=False,
            title_exact_match=False,
            content_exact_match=False,
            category_id_10_verified=False,
            m17_secret_response_digest=(
                m17_secret_response_digest
            ),
            m17_secret_response_file_sha=(
                m17_secret_response_file_sha
            ),
            ready_for_human_review=False,
        )

        try:
            write_outputs(result)
        except FileExistsError:
            pass

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    except Exception:
        get_count = (
            client.get_request_count
            if client is not None
            else 0
        )
        http_status = (
            client.last_http_status
            if client is not None
            else None
        )

        result = build_result(
            status=(
                "BLOCKED_WORDPRESS_PUBLISHED_POST_"
                "EXECUTION_EVIDENCE_VERIFICATION_"
                "UNEXPECTED_NO_WRITE"
            ),
            decision=(
                "UNEXPECTED_FAILURE_FAIL_CLOSED_"
                "POST_PUBLICATION_HUMAN_REVIEW_NOT_READY"
            ),
            error_code=(
                "UNEXPECTED_M18_VERIFICATION_FAILURE"
            ),
            get_request_count=get_count,
            http_status=http_status,
            writer_credential_accessed=(
                writer_credential_accessed
            ),
            writer_credential_verified=(
                writer_credential_verified
            ),
            post_id_verified=False,
            published_status_verified=False,
            title_exact_match=False,
            content_exact_match=False,
            category_id_10_verified=False,
            m17_secret_response_digest=(
                m17_secret_response_digest
            ),
            m17_secret_response_file_sha=(
                m17_secret_response_file_sha
            ),
            ready_for_human_review=False,
        )

        try:
            write_outputs(result)
        except FileExistsError:
            pass

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
