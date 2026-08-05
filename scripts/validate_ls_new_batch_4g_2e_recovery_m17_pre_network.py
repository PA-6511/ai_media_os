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
    "new_release_wp_publication_authenticated_"
    "get_only_preflight_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_"
    "m17_pre_network_approval.json"
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
M12_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
M13_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)
M13_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m13_result.json"
)
M14_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m14_result.json"
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

WRITER_CREDENTIAL = Path(
    "/etc/ai-media-os/credential.env"
)

RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m17_pre_network_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m17_pre_network_"
    "wordpress_publication_preflight_report.md"
)

EXPECTED_POST_ID = 192
EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
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
EXPECTED_M12_AUTH_SHA = (
    "7c9662a7a13502e165862e4524278992"
    "28794bce6904a0215c45a5b54ba1142b"
)
EXPECTED_M12_AUTH_DIGEST = (
    "d3ede61a71d75cbbc00a594f0a8d319a"
    "ed0e598bd9c061609a52bed7e96d07c3"
)
EXPECTED_M13_CONSUMPTION_DIGEST = (
    "a9c96f8fddc4bfebeebce2d535936a21"
    "e9214bb9ac6688e7277aa6def171aaba"
)
EXPECTED_M13_RESULT_DIGEST = (
    "34bb7a2cd15cfd829a805c1e974ca62c"
    "c453036132a25c41d7fd17b3ae681e0d"
)
EXPECTED_M14_RESULT_DIGEST = (
    "364cf76c3db0d321f9dc31251224393b"
    "403030524bb834cb147dc5f3f4e2ef61"
)
EXPECTED_M15_REVIEW_DIGEST = (
    "be8aafa191df793ecbe2695b662378fe"
    "f078ce42ae4169a93651a9d2b6141d4c"
)
EXPECTED_M15_RESULT_DIGEST = (
    "03d777e3e34c4d68c4b55027db87f7b"
    "20cee59f947640f3d68b125d6c79f5b06"
)
EXPECTED_M16_AUTH_DIGEST = (
    "3af20632d3fabe77f04e795318406ecd"
    "0ad9bd7b6d2eb60646e82f108556cc9e"
)
EXPECTED_M16_RESULT_DIGEST = (
    "9eda577486ceaf77be2baf0346cf7152"
    "ff3e5113bd091625715e487224c3150a"
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
        ) == [("context", "edit")],
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

        url = (
            self.origin
            + "/wp-json/wp/v2/posts/192"
            + "?context=edit"
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
                    "ai-media-os-m17-pre-network/1.0"
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

            if 300 <= code < 400:
                raise ValidationError(
                    "REDIRECT_BLOCKED"
                ) from None

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
    m16_authorization_file_sha256: str,
    http_status: int | None,
    get_request_count: int,
    post_id_verified: bool,
    draft_status_verified: bool,
    title_exact_match: bool,
    content_exact_match: bool,
    category_id_10_verified: bool,
    writer_credential_verified: bool,
    ready_for_execute_now_gate: bool,
) -> dict[str, Any]:
    network_performed = (
        get_request_count > 0
    )

    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-"
            "RECOVERY-M17-PRE-NETWORK"
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
            "draft"
            if draft_status_verified
            else None
        ),
        "draft_status_verified": (
            draft_status_verified
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
        "wordpress_http_status": http_status,
        "wordpress_get_request_count": (
            get_request_count
        ),
        "wordpress_non_get_request_count": 0,
        "automatic_retry_performed": False,
        "network_connection_performed": (
            network_performed
        ),
        "http_request_performed": (
            network_performed
        ),
        "wordpress_access_performed": (
            network_performed
        ),
        "connection_scheme_https": True,
        "connection_host_hoshido_jp": True,
        "proxy_used": False,
        "redirect_followed": False,
        "writer_credential_accessed": True,
        "writer_credential_structure_verified": (
            writer_credential_verified
        ),
        "writer_credential_file_modified": False,
        "m16_authorization_file_sha256": (
            m16_authorization_file_sha256
        ),
        "m16_authorization_digest_sha256": (
            EXPECTED_M16_AUTH_DIGEST
        ),
        "m16_result_digest_sha256": (
            EXPECTED_M16_RESULT_DIGEST
        ),
        "m16_authorization_single_use": True,
        "m16_authorization_consumed": False,
        "m16_authorization_reuse_allowed": False,
        "m16_automatic_retry_allowed": False,
        "m16_automatic_reissue_allowed": False,
        "m16_maximum_publish_count": 1,
        "publication_authorization_consumed_in_this_phase": False,
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
        "m14_result_digest_sha256": (
            EXPECTED_M14_RESULT_DIGEST
        ),
        "m13_result_digest_sha256": (
            EXPECTED_M13_RESULT_DIGEST
        ),
        "m13_consumption_digest_sha256": (
            EXPECTED_M13_CONSUMPTION_DIGEST
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
        "wordpress_publish_performed": False,
        "wordpress_delete_performed": False,
        "wordpress_draft_recreated": False,
        "category_operation_performed": False,
        "media_operation_performed": False,
        "authorization_issued_in_this_phase": False,
        "m13_rerun_performed": False,
        "m14_rerun_performed": False,
        "m15_rerun_performed": False,
        "m16_rerun_performed": False,
        "x_post_performed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "WORDPRESS_PUBLICATION_PREFLIGHT_"
            "VERIFIED_AWAITING_EXPLICIT_EXECUTE_NOW_GATE"
            if ready_for_execute_now_gate
            else (
                "WORDPRESS_PUBLICATION_PREFLIGHT_"
                "BLOCKED_NO_AUTH_CONSUMPTION_NO_WRITE"
            )
        ),
        "ready_for_wordpress_publication_execute_now_gate": (
            ready_for_execute_now_gate
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
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M17-PRE-NETWORK

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Error code: `{result["error_code"]}`
- WordPress post ID: `192`
- Post ID verified: `{str(result["post_id_verified"]).lower()}`
- WordPress post status: `{result["wordpress_post_status"]}`
- WordPress HTTP status: `{result["wordpress_http_status"]}`
- WordPress GET request count: `{result["wordpress_get_request_count"]}`
- WordPress non-GET request count: `0`
- Automatic retry performed: `false`
- Title exact match: `{str(result["title_exact_match"]).lower()}`
- Content exact match: `{str(result["content_exact_match"]).lower()}`
- Category ID 10 verified: `{str(result["category_id_10_verified"]).lower()}`
- M16 authorization consumed: `false`
- Authorization consumed in this phase: `false`
- WordPress write performed: `false`
- WordPress update performed: `false`
- WordPress publish performed: `false`
- Production status: `NO_GO`
- Ready for publication execute-now gate: `{str(result["ready_for_wordpress_publication_execute_now_gate"]).lower()}`
- Ready for WordPress publish: `false`
""",
    )


def main() -> int:
    source_paths = {
        "article": ARTICLE,
        "payload": PAYLOAD,
        "m12_authorization": M12_AUTH,
        "m13_consumption": M13_CONSUMPTION,
        "m13_result": M13_RESULT,
        "m14_result": M14_RESULT,
        "m15_review": M15_REVIEW,
        "m15_result": M15_RESULT,
        "m16_authorization": M16_AUTH,
        "m16_result": M16_RESULT,
    }

    source_hashes: dict[str, str] = {}
    credential_before: (
        os.stat_result | None
    ) = None
    client: (
        WordPressSingleGetClient | None
    ) = None

    m16_authorization_file_sha256 = ""
    writer_credential_verified = False

    try:
        require(
            not RESULT.exists(),
            "M17_PRE_NETWORK_RESULT_ALREADY_EXISTS",
        )
        require(
            not REPORT.exists(),
            "M17_PRE_NETWORK_REPORT_ALREADY_EXISTS",
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
                "RECOVERY-M17-PRE-NETWORK"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_PUBLICATION_AUTHENTICATED_"
                "GET_ONLY_PREFLIGHT_APPROVED"
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
                "publication_authorization_consumption_approved"
            ] is False,
            "AUTHORIZATION_CONSUMPTION_APPROVED",
        )
        require(
            approval[
                "wordpress_publish_approved"
            ] is False,
            "WORDPRESS_PUBLISH_APPROVED",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

        approval_bindings = approval[
            "source_bindings"
        ]

        for name, path in source_paths.items():
            require(
                approval_bindings[name][
                    "file_sha256"
                ] == source_hashes[name],
                f"APPROVAL_SOURCE_BINDING_MISMATCH:{name}",
            )
            require(
                approval_bindings[name]["path"]
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
                "m12_authorization"
            ] == EXPECTED_M12_AUTH_SHA,
            "M12_AUTHORIZATION_FILE_SHA_MISMATCH",
        )

        m16_authorization_file_sha256 = (
            source_hashes[
                "m16_authorization"
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
                M16_RESULT.stat().st_mode
            ) == 0o600,
            "M16_RESULT_MODE_NOT_0600",
        )
        require(
            stat.S_IMODE(
                M15_REVIEW.stat().st_mode
            ) == 0o600,
            "M15_REVIEW_MODE_NOT_0600",
        )

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        m12_auth = load_json(M12_AUTH)
        m13_consumption = load_json(
            M13_CONSUMPTION
        )
        m13_result = load_json(M13_RESULT)
        m14_result = load_json(M14_RESULT)
        m15_review = load_json(M15_REVIEW)
        m15_result = load_json(M15_RESULT)
        m16_auth = load_json(M16_AUTH)
        m16_result = load_json(M16_RESULT)

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            m12_auth,
            "authorization_digest_sha256",
            EXPECTED_M12_AUTH_DIGEST,
        )
        verify_digest(
            m13_consumption,
            "consumption_evidence_digest_sha256",
            EXPECTED_M13_CONSUMPTION_DIGEST,
        )
        verify_digest(
            m13_result,
            "result_digest_sha256",
            EXPECTED_M13_RESULT_DIGEST,
        )
        verify_digest(
            m14_result,
            "result_digest_sha256",
            EXPECTED_M14_RESULT_DIGEST,
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

        require(
            m16_result["status"]
            == (
                "PASS_WORDPRESS_PUBLICATION_ONE_SHOT_"
                "AUTHORIZATION_GATE_FIXED_NO_NETWORK_NO_WORDPRESS"
            ),
            "M16_RESULT_STATUS_MISMATCH",
        )
        require(
            m16_result[
                "authorization_digest_sha256"
            ] == EXPECTED_M16_AUTH_DIGEST,
            "M16_RESULT_AUTHORIZATION_DIGEST_MISMATCH",
        )
        require(
            m16_result[
                "ready_for_wordpress_publication_preflight"
            ] is True,
            "M16_PUBLICATION_PREFLIGHT_NOT_READY",
        )
        require(
            m16_result[
                "ready_for_wordpress_publication_execute_now_gate"
            ] is False,
            "M16_EXECUTE_NOW_GATE_ALREADY_OPEN",
        )
        require(
            m16_result[
                "ready_for_wordpress_publish"
            ] is False,
            "M16_WORDPRESS_PUBLISH_READY_TRUE",
        )
        require(
            m16_result[
                "wordpress_publish_performed"
            ] is False,
            "M16_WORDPRESS_PUBLISH_PERFORMED",
        )

        require(
            m16_auth["authorization_id"]
            == (
                "WORDPRESS_PUBLICATION_ONE_SHOT_"
                "AUTHORIZATION_V1"
            ),
            "M16_AUTHORIZATION_ID_MISMATCH",
        )
        require(
            m16_auth["wordpress_post_id"]
            == EXPECTED_POST_ID,
            "M16_AUTHORIZATION_POST_ID_MISMATCH",
        )
        require(
            m16_auth["single_use"] is True,
            "M16_AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            m16_auth[
                "authorization_consumed"
            ] is False,
            "M16_AUTHORIZATION_ALREADY_CONSUMED",
        )
        require(
            m16_auth[
                "authorization_reuse_allowed"
            ] is False,
            "M16_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m16_auth[
                "automatic_retry_allowed"
            ] is False,
            "M16_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m16_auth[
                "automatic_reissue_allowed"
            ] is False,
            "M16_AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            m16_auth[
                "maximum_publish_count"
            ] == 1,
            "M16_MAXIMUM_PUBLISH_COUNT_MISMATCH",
        )
        require(
            m16_auth[
                "required_current_post_status"
            ] == "draft",
            "M16_REQUIRED_CURRENT_STATUS_MISMATCH",
        )
        require(
            m16_auth[
                "allowed_target_post_status"
            ] == "publish",
            "M16_ALLOWED_TARGET_STATUS_MISMATCH",
        )
        require(
            m16_auth[
                "planned_preflight_phase_id"
            ] == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M17-PRE-NETWORK"
            ),
            "M16_PLANNED_PREFLIGHT_PHASE_MISMATCH",
        )
        require(
            m16_auth[
                "planned_execution_phase_id"
            ] == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M17"
            ),
            "M16_PLANNED_EXECUTION_PHASE_MISMATCH",
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
            m15_review[
                "change_required"
            ] is False,
            "M15_CHANGE_REQUIRED_TRUE",
        )
        require(
            m15_review[
                "publish_action_not_performed"
            ] is True,
            "M15_PUBLISH_ACTION_PERFORMED",
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
            payload["status"] == "draft",
            "PAYLOAD_STATUS_NOT_DRAFT",
        )
        require(
            payload["post_status"] == "draft",
            "PAYLOAD_POST_STATUS_NOT_DRAFT",
        )
        require(
            payload["publish"] is False,
            "PAYLOAD_PUBLISH_TRUE",
        )
        require(
            payload["category_id"] == 10,
            "PAYLOAD_CATEGORY_ID_MISMATCH",
        )
        require(
            payload["categories"] == [10],
            "PAYLOAD_CATEGORIES_MISMATCH",
        )

        credentials, credential_before = (
            read_writer_credentials(
                WRITER_CREDENTIAL
            )
        )
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
            response_status == "draft",
            "POST_STATUS_NOT_DRAFT",
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
                "PASS_WORDPRESS_PUBLICATION_"
                "AUTHENTICATED_GET_ONLY_PREFLIGHT_"
                "VERIFIED_NO_AUTH_CONSUMPTION_NO_WRITE"
            ),
            decision=(
                "WORDPRESS_DRAFT_192_VERIFIED_"
                "READY_FOR_EXPLICIT_PUBLICATION_"
                "EXECUTE_NOW_GATE"
            ),
            error_code=None,
            m16_authorization_file_sha256=(
                m16_authorization_file_sha256
            ),
            http_status=http_status,
            get_request_count=1,
            post_id_verified=True,
            draft_status_verified=True,
            title_exact_match=True,
            content_exact_match=True,
            category_id_10_verified=True,
            writer_credential_verified=True,
            ready_for_execute_now_gate=True,
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
                "BLOCKED_WORDPRESS_PUBLICATION_"
                "AUTHENTICATED_GET_ONLY_PREFLIGHT_"
                "NO_AUTH_CONSUMPTION_NO_WRITE"
            ),
            decision=(
                "FAIL_CLOSED_PUBLICATION_"
                "EXECUTE_NOW_GATE_NOT_READY"
            ),
            error_code=str(exc),
            m16_authorization_file_sha256=(
                m16_authorization_file_sha256
            ),
            http_status=http_status,
            get_request_count=get_count,
            post_id_verified=False,
            draft_status_verified=False,
            title_exact_match=False,
            content_exact_match=False,
            category_id_10_verified=False,
            writer_credential_verified=(
                writer_credential_verified
            ),
            ready_for_execute_now_gate=False,
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
                "BLOCKED_WORDPRESS_PUBLICATION_"
                "AUTHENTICATED_GET_ONLY_PREFLIGHT_"
                "UNEXPECTED_NO_AUTH_CONSUMPTION_NO_WRITE"
            ),
            decision=(
                "UNEXPECTED_FAILURE_FAIL_CLOSED_"
                "PUBLICATION_EXECUTE_NOW_GATE_NOT_READY"
            ),
            error_code=(
                "UNEXPECTED_M17_PRE_NETWORK_FAILURE"
            ),
            m16_authorization_file_sha256=(
                m16_authorization_file_sha256
            ),
            http_status=http_status,
            get_request_count=get_count,
            post_id_verified=False,
            draft_status_verified=False,
            title_exact_match=False,
            content_exact_match=False,
            category_id_10_verified=False,
            writer_credential_verified=(
                writer_credential_verified
            ),
            ready_for_execute_now_gate=False,
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
