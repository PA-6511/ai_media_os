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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_publication_final_"
    "one_shot_execution_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_"
    "m17_final_execute_approval.json"
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

WRITER_CREDENTIAL = Path(
    "/etc/ai-media-os/credential.env"
)

CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_consumption.json"
)
SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_response.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m17_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m17_"
    "wordpress_publication_report.md"
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

REQUIRED_CREDENTIAL_KEYS = (
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
)

MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class ValidationError(RuntimeError):
    pass


class PostExecutionUncertain(RuntimeError):
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


def atomic_create_bytes(
    path: Path,
    data: bytes,
    mode: int = 0o600,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    require(
        not path.exists(),
        f"OUTPUT_ALREADY_EXISTS:{path.name}",
    )

    temporary = path.with_name(
        path.name
        + ".tmp."
        + uuid.uuid4().hex
    )

    fd = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )

    linked = False

    try:
        with os.fdopen(
            fd,
            "wb",
        ) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

        os.link(temporary, path)
        linked = True

        directory_fd = os.open(
            path.parent,
            os.O_RDONLY,
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        try:
            temporary.unlink(missing_ok=True)
        except Exception:
            pass

        if not linked:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    atomic_create_bytes(
        path,
        (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8"),
        0o600,
    )


def atomic_create_text(
    path: Path,
    value: str,
) -> None:
    atomic_create_bytes(
        path,
        value.encode("utf-8"),
        0o600,
    )


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


def build_post_url(origin: str) -> str:
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


class WordPressPublicationClient:
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
        self.publication_post_count = 0
        self.last_http_status: int | None = None

        context = ssl.create_default_context()

        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            NoRedirectHandler(),
            urllib.request.HTTPSHandler(
                context=context
            ),
        )

    def get_post_before_publication(
        self,
    ) -> tuple[dict[str, Any], int]:
        require(
            self.get_request_count == 0,
            "PRE_PUBLICATION_GET_ALREADY_USED",
        )
        require(
            self.publication_post_count == 0,
            "PUBLICATION_POST_ALREADY_STARTED",
        )

        url = build_post_url(self.origin)
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
                    "ai-media-os-m17/1.0"
                ),
                "Cache-Control": "no-store",
            },
        )

        require(
            request.get_method() == "GET",
            "PRE_PUBLICATION_METHOD_NOT_GET",
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
                self.last_http_status = status_code

                require(
                    status_code == 200,
                    (
                        "PRE_PUBLICATION_GET_"
                        f"HTTP_STATUS_{status_code}"
                    ),
                )
                require(
                    response.geturl() == url,
                    "PRE_PUBLICATION_FINAL_URL_CHANGED",
                )

                body = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

                require(
                    len(body)
                    <= MAX_RESPONSE_BYTES,
                    "PRE_PUBLICATION_RESPONSE_TOO_LARGE",
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
                        "PRE_PUBLICATION_JSON_PARSE_FAILED"
                    ) from None

                require(
                    isinstance(parsed, dict),
                    "PRE_PUBLICATION_RESPONSE_NOT_OBJECT",
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
                    "PRE_PUBLICATION_GET_"
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
                "PRE_PUBLICATION_GET_NETWORK_FAILED"
            ) from None

    def publish_post(
        self,
        request_body: bytes,
    ) -> tuple[
        int,
        str,
        str,
        bytes,
    ]:
        require(
            self.get_request_count == 1,
            "PRE_PUBLICATION_GET_COUNT_NOT_ONE",
        )
        require(
            self.publication_post_count == 0,
            "PUBLICATION_POST_ALREADY_USED",
        )

        url = build_post_url(self.origin)
        validate_request_url(url)

        request = urllib.request.Request(
            url=url,
            method="POST",
            data=request_body,
            headers={
                "Accept": "application/json",
                "Content-Type": (
                    "application/json; charset=utf-8"
                ),
                "Authorization": (
                    self.authorization_header
                ),
                "User-Agent": (
                    "ai-media-os-m17/1.0"
                ),
                "Cache-Control": "no-store",
            },
        )

        require(
            request.get_method() == "POST",
            "PUBLICATION_METHOD_NOT_POST",
        )

        self.publication_post_count += 1

        try:
            with self.opener.open(
                request,
                timeout=30,
            ) as response:
                status_code = int(
                    response.getcode()
                )
                self.last_http_status = status_code
                final_url = response.geturl()
                content_type = (
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                )

                raw_body = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

                if len(raw_body) > MAX_RESPONSE_BYTES:
                    raise PostExecutionUncertain(
                        "PUBLICATION_RESPONSE_TOO_LARGE"
                    )

                return (
                    status_code,
                    final_url,
                    content_type,
                    raw_body,
                )

        except ValidationError as exc:
            raise PostExecutionUncertain(
                str(exc)
            ) from None

        except urllib.error.HTTPError as exc:
            code = int(exc.code)
            self.last_http_status = code
            final_url = exc.geturl()
            content_type = (
                exc.headers.get(
                    "Content-Type",
                    "",
                )
                if exc.headers is not None
                else ""
            )

            try:
                raw_body = exc.read(
                    MAX_RESPONSE_BYTES + 1
                )
            except Exception:
                raw_body = b""

            try:
                exc.close()
            except Exception:
                pass

            if len(raw_body) > MAX_RESPONSE_BYTES:
                raw_body = raw_body[
                    :MAX_RESPONSE_BYTES
                ]

            return (
                code,
                final_url,
                content_type,
                raw_body,
            )

        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ssl.SSLError,
        ):
            raise PostExecutionUncertain(
                "PUBLICATION_NETWORK_RESULT_UNKNOWN"
            ) from None


def validate_post_contract(
    post_data: dict[str, Any],
    payload: dict[str, Any],
    required_status: str,
) -> tuple[
    bool,
    bool,
    bool,
    bool,
    bool,
]:
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

    id_valid = (
        isinstance(response_id, int)
        and response_id == EXPECTED_POST_ID
    )
    status_valid = (
        response_status == required_status
    )
    title_match = (
        isinstance(response_title, dict)
        and isinstance(
            response_title.get("raw"),
            str,
        )
        and response_title["raw"]
        == payload["title"]
    )
    content_match = (
        isinstance(response_content, dict)
        and isinstance(
            response_content.get("raw"),
            str,
        )
        and response_content["raw"]
        == payload["content_html"]
    )
    category_match = (
        isinstance(response_categories, list)
        and response_categories == [10]
    )

    return (
        id_valid,
        status_valid,
        title_match,
        content_match,
        category_match,
    )


def write_secret_response(
    *,
    attempt_id: str,
    response_received: bool,
    http_status: int | None,
    final_url_verified: bool,
    content_type: str | None,
    raw_body: bytes | None,
    parsed_json: Any | None,
    error_code: str | None,
) -> None:
    artifact_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
        ),
        "document_role": (
            "SECRET_WORDPRESS_PUBLICATION_RESPONSE"
        ),
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": 192,
        "execution_attempt_id": attempt_id,
        "response_received": response_received,
        "http_status": http_status,
        "final_response_url_verified": (
            final_url_verified
        ),
        "content_type": content_type,
        "body_json": parsed_json,
        "body_base64": (
            base64.b64encode(
                raw_body
            ).decode("ascii")
            if (
                raw_body is not None
                and parsed_json is None
            )
            else None
        ),
        "error_code": error_code,
        "contains_potential_affiliate_content": (
            raw_body is not None
        ),
        "mode_required": "0600",
        "created_at_utc": now()
    }

    artifact = copy.deepcopy(
        artifact_without_digest
    )
    artifact[
        "secret_response_digest_sha256"
    ] = digest(artifact_without_digest)

    atomic_create_json(
        SECRET_RESPONSE,
        artifact,
    )


def build_result(
    *,
    status: str,
    decision: str,
    error_code: str | None,
    attempt_id: str | None,
    authorization_consumed: bool,
    consumption_digest: str | None,
    get_request_count: int,
    publication_post_count: int,
    response_received: bool,
    http_status: int | None,
    returned_status: str | None,
    post_id_verified: bool,
    title_match: bool,
    content_match: bool,
    category_match: bool,
    publication_verified: bool,
    publication_result_unknown: bool,
    manual_review_required: bool,
) -> dict[str, Any]:
    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
        ),
        "status": status,
        "decision": decision,
        "error_code": error_code,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": 192,
        "execution_attempt_id": attempt_id,
        "m16_authorization_file_sha256": (
            EXPECTED_M16_AUTH_FILE_SHA
        ),
        "m16_authorization_digest_sha256": (
            EXPECTED_M16_AUTH_DIGEST
        ),
        "m16_result_digest_sha256": (
            EXPECTED_M16_RESULT_DIGEST
        ),
        "m17_pre_network_result_digest_sha256": (
            EXPECTED_M17_PRE_RESULT_DIGEST
        ),
        "payload_file_sha256": (
            EXPECTED_PAYLOAD_SHA
        ),
        "payload_digest_sha256": (
            EXPECTED_PAYLOAD_DIGEST
        ),
        "authorization_consumed": (
            authorization_consumed
        ),
        "authorization_reuse_allowed": False,
        "automatic_retry_allowed": False,
        "automatic_reissue_allowed": False,
        "consumption_evidence_digest_sha256": (
            consumption_digest
        ),
        "pre_publication_get_request_count": (
            get_request_count
        ),
        "publication_post_request_count": (
            publication_post_count
        ),
        "wordpress_response_received": (
            response_received
        ),
        "wordpress_http_status": http_status,
        "returned_wordpress_status": (
            returned_status
        ),
        "post_id_verified": post_id_verified,
        "title_exact_match": title_match,
        "content_exact_match": content_match,
        "category_id_10_verified": (
            category_match
        ),
        "publication_verified": (
            publication_verified
        ),
        "publication_result_unknown": (
            publication_result_unknown
        ),
        "wordpress_published": (
            publication_verified
        ),
        "publication_count": (
            1 if publication_verified else 0
        ),
        "request_fields_exactly_limited": True,
        "publication_request_status_only": True,
        "title_field_sent": False,
        "content_field_sent": False,
        "categories_field_sent": False,
        "source_artifacts_modified": False,
        "writer_credential_file_modified": False,
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
        "title_change_performed": False,
        "content_change_performed": False,
        "category_change_performed": False,
        "post_delete_performed": False,
        "post_recreation_performed": False,
        "media_operation_performed": False,
        "x_post_performed": False,
        "manual_wordpress_review_required": (
            manual_review_required
        ),
        "secret_response_artifact_path": (
            str(
                SECRET_RESPONSE.relative_to(ROOT)
            )
            if SECRET_RESPONSE.exists()
            else None
        ),
        "secret_response_artifact_mode_0600": (
            SECRET_RESPONSE.exists()
            and stat.S_IMODE(
                SECRET_RESPONSE.stat().st_mode
            ) == 0o600
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "WORDPRESS_POST_192_PUBLISHED_"
            "AWAITING_POST_PUBLICATION_EVIDENCE_REVIEW"
            if publication_verified
            else (
                "PUBLICATION_AUTHORIZATION_CONSUMED_"
                "RESULT_UNKNOWN_OR_REQUIRES_MANUAL_REVIEW_"
                "NO_RETRY"
                if authorization_consumed
                else (
                    "PUBLICATION_BLOCKED_BEFORE_"
                    "AUTHORIZATION_CONSUMPTION"
                )
            )
        ),
        "ready_for_post_publication_evidence_review": (
            publication_verified
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
    atomic_create_json(
        RESULT,
        result,
    )

    atomic_create_text(
        REPORT,
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M17

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Error code: `{result["error_code"]}`
- WordPress post ID: `192`
- Authorization consumed: `{str(result["authorization_consumed"]).lower()}`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- Pre-publication GET count: `{result["pre_publication_get_request_count"]}`
- Publication POST count: `{result["publication_post_request_count"]}`
- HTTP status: `{result["wordpress_http_status"]}`
- Returned status: `{result["returned_wordpress_status"]}`
- Post ID verified: `{str(result["post_id_verified"]).lower()}`
- Title exact match: `{str(result["title_exact_match"]).lower()}`
- Content exact match: `{str(result["content_exact_match"]).lower()}`
- Category ID 10 verified: `{str(result["category_id_10_verified"]).lower()}`
- Publication verified: `{str(result["publication_verified"]).lower()}`
- Publication result unknown: `{str(result["publication_result_unknown"]).lower()}`
- Title field sent: `false`
- Content field sent: `false`
- Categories field sent: `false`
- WordPress published: `{str(result["wordpress_published"]).lower()}`
- Production status: `NO_GO`
- Ready for post-publication evidence review: `{str(result["ready_for_post_publication_evidence_review"]).lower()}`
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
    }

    source_hashes: dict[str, str] = {}
    credential_before: (
        os.stat_result | None
    ) = None
    client: (
        WordPressPublicationClient | None
    ) = None

    authorization_consumed = False
    consumption_digest: str | None = None
    attempt_id: str | None = None
    response_received = False
    http_status: int | None = None
    returned_status: str | None = None
    post_id_verified = False
    title_match = False
    content_match = False
    category_match = False
    publication_verified = False

    try:
        for output in [
            CONSUMPTION,
            SECRET_RESPONSE,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M17_OUTPUT_ALREADY_EXISTS:{output.name}",
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
                "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_PUBLICATION_FINAL_"
                "ONE_SHOT_EXECUTE_NOW_APPROVED"
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
                "publication_authorization_consumption_approved"
            ] is True,
            "AUTHORIZATION_CONSUMPTION_NOT_APPROVED",
        )
        require(
            approval[
                "wordpress_publication_approved"
            ] is True,
            "WORDPRESS_PUBLICATION_NOT_APPROVED",
        )
        require(
            approval[
                "maximum_get_request_count"
            ] == 1,
            "APPROVAL_GET_LIMIT_MISMATCH",
        )
        require(
            approval[
                "maximum_publication_post_count"
            ] == 1,
            "APPROVAL_POST_LIMIT_MISMATCH",
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

        require(
            m17_pre_result["status"]
            == (
                "PASS_WORDPRESS_PUBLICATION_"
                "AUTHENTICATED_GET_ONLY_PREFLIGHT_"
                "VERIFIED_NO_AUTH_CONSUMPTION_NO_WRITE"
            ),
            "M17_PRE_RESULT_STATUS_MISMATCH",
        )
        require(
            m17_pre_result[
                "ready_for_wordpress_publication_execute_now_gate"
            ] is True,
            "M17_PRE_EXECUTE_GATE_NOT_READY",
        )
        require(
            m17_pre_result[
                "m16_authorization_consumed"
            ] is False,
            "M17_PRE_AUTHORIZATION_CONSUMED",
        )
        require(
            m17_pre_result[
                "wordpress_post_status"
            ] == "draft",
            "M17_PRE_POST_NOT_DRAFT",
        )
        require(
            m17_pre_result[
                "title_exact_match"
            ] is True,
            "M17_PRE_TITLE_MISMATCH",
        )
        require(
            m17_pre_result[
                "content_exact_match"
            ] is True,
            "M17_PRE_CONTENT_MISMATCH",
        )
        require(
            m17_pre_result[
                "category_id_10_verified"
            ] is True,
            "M17_PRE_CATEGORY_MISMATCH",
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
            "M16_REQUIRED_STATUS_MISMATCH",
        )
        require(
            m16_auth[
                "allowed_target_post_status"
            ] == "publish",
            "M16_TARGET_STATUS_MISMATCH",
        )
        require(
            m16_auth[
                "planned_execution_phase_id"
            ] == (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
            ),
            "M16_PLANNED_PHASE_MISMATCH",
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
            "M15_CHANGE_REQUIRED",
        )
        require(
            m15_review[
                "publish_action_not_performed"
            ] is True,
            "M15_PUBLISH_ACTION_ALREADY_PERFORMED",
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
            payload["post_status"]
            == "draft",
            "PAYLOAD_POST_STATUS_NOT_DRAFT",
        )
        require(
            payload["publish"] is False,
            "PAYLOAD_PUBLISH_TRUE",
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

        client = WordPressPublicationClient(
            origin=origin,
            authorization_header=(
                authorization_header
            ),
        )

        pre_data, pre_http_status = (
            client.get_post_before_publication()
        )

        require(
            pre_http_status == 200,
            "PRE_PUBLICATION_HTTP_NOT_200",
        )

        (
            pre_id_valid,
            pre_status_valid,
            pre_title_match,
            pre_content_match,
            pre_category_match,
        ) = validate_post_contract(
            pre_data,
            payload,
            "draft",
        )

        require(
            pre_id_valid,
            "PRE_PUBLICATION_POST_ID_MISMATCH",
        )
        require(
            pre_status_valid,
            "PRE_PUBLICATION_STATUS_NOT_DRAFT",
        )
        require(
            pre_title_match,
            "PRE_PUBLICATION_TITLE_MISMATCH",
        )
        require(
            pre_content_match,
            "PRE_PUBLICATION_CONTENT_MISMATCH",
        )
        require(
            pre_category_match,
            "PRE_PUBLICATION_CATEGORY_MISMATCH",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        require(
            credential_before is not None
            and same_metadata(
                credential_before,
                WRITER_CREDENTIAL.lstat(),
            ),
            "WRITER_CREDENTIAL_METADATA_CHANGED",
        )

        attempt_id = str(uuid.uuid4())

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
            ),
            "document_role": (
                "WORDPRESS_PUBLICATION_"
                "AUTHORIZATION_CONSUMPTION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "wordpress_post_id": 192,
            "execution_attempt_id": attempt_id,
            "source_authorization_path": str(
                M16_AUTH.relative_to(ROOT)
            ),
            "source_authorization_file_sha256": (
                EXPECTED_M16_AUTH_FILE_SHA
            ),
            "source_authorization_digest_sha256": (
                EXPECTED_M16_AUTH_DIGEST
            ),
            "m16_result_digest_sha256": (
                EXPECTED_M16_RESULT_DIGEST
            ),
            "m17_pre_network_result_digest_sha256": (
                EXPECTED_M17_PRE_RESULT_DIGEST
            ),
            "payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "pre_publication_get_completed": True,
            "pre_publication_post_id_verified": True,
            "pre_publication_status_draft_verified": True,
            "pre_publication_title_exact_match": True,
            "pre_publication_content_exact_match": True,
            "pre_publication_category_id_10_verified": True,
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "maximum_publish_count": 1,
            "publication_post_not_yet_started_at_consumption": True,
            "consumed_at_utc": now(),
            "production_status": "NO_GO"
        }

        consumption = copy.deepcopy(
            consumption_without_digest
        )
        consumption[
            "consumption_evidence_digest_sha256"
        ] = digest(
            consumption_without_digest
        )

        atomic_create_json(
            CONSUMPTION,
            consumption,
        )

        authorization_consumed = True
        consumption_digest = consumption[
            "consumption_evidence_digest_sha256"
        ]

        request_object = {
            "status": "publish"
        }

        require(
            set(request_object.keys())
            == {"status"},
            "PUBLICATION_REQUEST_FIELD_SET_INVALID",
        )

        request_body = json.dumps(
            request_object,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        try:
            (
                http_status,
                final_response_url,
                content_type,
                raw_response,
            ) = client.publish_post(
                request_body
            )
            response_received = True

        except PostExecutionUncertain as exc:
            write_secret_response(
                attempt_id=attempt_id,
                response_received=False,
                http_status=None,
                final_url_verified=False,
                content_type=None,
                raw_body=None,
                parsed_json=None,
                error_code=str(exc),
            )

            result = build_result(
                status=(
                    "BLOCKED_WORDPRESS_PUBLICATION_"
                    "RESULT_UNKNOWN_AUTHORIZATION_"
                    "CONSUMED_NO_RETRY"
                ),
                decision=(
                    "MANUAL_WORDPRESS_PUBLICATION_"
                    "STATE_CONFIRMATION_REQUIRED"
                ),
                error_code=str(exc),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                get_request_count=1,
                publication_post_count=1,
                response_received=False,
                http_status=None,
                returned_status=None,
                post_id_verified=False,
                title_match=False,
                content_match=False,
                category_match=False,
                publication_verified=False,
                publication_result_unknown=True,
                manual_review_required=True,
            )

            write_outputs(result)

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )

            return 2

        expected_response_url = (
            build_post_url(origin)
        )
        final_url_verified = (
            final_response_url
            == expected_response_url
        )

        parsed_response: Any | None = None

        try:
            parsed_response = json.loads(
                raw_response.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            parsed_response = None

        write_secret_response(
            attempt_id=attempt_id,
            response_received=True,
            http_status=http_status,
            final_url_verified=(
                final_url_verified
            ),
            content_type=content_type,
            raw_body=raw_response,
            parsed_json=parsed_response,
            error_code=None,
        )

        if not isinstance(
            parsed_response,
            dict,
        ):
            result = build_result(
                status=(
                    "BLOCKED_WORDPRESS_PUBLICATION_"
                    "RESPONSE_PARSE_AUTHORIZATION_"
                    "CONSUMED_NO_RETRY"
                ),
                decision=(
                    "MANUAL_WORDPRESS_PUBLICATION_"
                    "STATE_CONFIRMATION_REQUIRED"
                ),
                error_code=(
                    "PUBLICATION_RESPONSE_JSON_PARSE_FAILED"
                ),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                get_request_count=1,
                publication_post_count=1,
                response_received=True,
                http_status=http_status,
                returned_status=None,
                post_id_verified=False,
                title_match=False,
                content_match=False,
                category_match=False,
                publication_verified=False,
                publication_result_unknown=True,
                manual_review_required=True,
            )

            write_outputs(result)

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )

            return 2

        returned_status_value = (
            parsed_response.get("status")
        )
        returned_status = (
            returned_status_value
            if isinstance(
                returned_status_value,
                str,
            )
            else None
        )

        (
            post_id_verified,
            status_verified,
            title_match,
            content_match,
            category_match,
        ) = validate_post_contract(
            parsed_response,
            payload,
            "publish",
        )

        publication_verified = (
            http_status == 200
            and final_url_verified
            and post_id_verified
            and status_verified
            and title_match
            and content_match
            and category_match
        )

        if not publication_verified:
            result = build_result(
                status=(
                    "BLOCKED_WORDPRESS_PUBLICATION_"
                    "RESPONSE_CONTRACT_AUTHORIZATION_"
                    "CONSUMED_NO_RETRY"
                ),
                decision=(
                    "PUBLICATION_MAY_HAVE_OCCURRED_"
                    "MANUAL_REVIEW_REQUIRED"
                ),
                error_code=(
                    "PUBLICATION_RESPONSE_CONTRACT_MISMATCH"
                ),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                get_request_count=1,
                publication_post_count=1,
                response_received=True,
                http_status=http_status,
                returned_status=returned_status,
                post_id_verified=(
                    post_id_verified
                ),
                title_match=title_match,
                content_match=content_match,
                category_match=category_match,
                publication_verified=False,
                publication_result_unknown=True,
                manual_review_required=True,
            )

            write_outputs(result)

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )

            return 2

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        require(
            credential_before is not None
            and same_metadata(
                credential_before,
                WRITER_CREDENTIAL.lstat(),
            ),
            "WRITER_CREDENTIAL_METADATA_CHANGED",
        )

        result = build_result(
            status=(
                "PASS_WORDPRESS_PUBLICATION_"
                "ONE_SHOT_AUTHORIZATION_CONSUMED_"
                "POST_192_PUBLISHED_NO_RETRY"
            ),
            decision=(
                "WORDPRESS_POST_192_PUBLISHED_"
                "READY_FOR_POST_PUBLICATION_"
                "EVIDENCE_VERIFICATION"
            ),
            error_code=None,
            attempt_id=attempt_id,
            authorization_consumed=True,
            consumption_digest=(
                consumption_digest
            ),
            get_request_count=1,
            publication_post_count=1,
            response_received=True,
            http_status=http_status,
            returned_status="publish",
            post_id_verified=True,
            title_match=True,
            content_match=True,
            category_match=True,
            publication_verified=True,
            publication_result_unknown=False,
            manual_review_required=False,
        )

        write_outputs(result)

        del credentials
        del credential_pair
        del authorization_header
        del pre_data
        del parsed_response
        del raw_response
        del request_body
        del request_object

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
        post_count = (
            client.publication_post_count
            if client is not None
            else 0
        )

        if authorization_consumed:
            if (
                attempt_id is not None
                and not SECRET_RESPONSE.exists()
            ):
                try:
                    write_secret_response(
                        attempt_id=attempt_id,
                        response_received=(
                            response_received
                        ),
                        http_status=http_status,
                        final_url_verified=False,
                        content_type=None,
                        raw_body=None,
                        parsed_json=None,
                        error_code=str(exc),
                    )
                except Exception:
                    pass

            result = build_result(
                status=(
                    "BLOCKED_WORDPRESS_PUBLICATION_"
                    "POST_CONSUMPTION_AUTHORIZATION_"
                    "CONSUMED_NO_RETRY"
                ),
                decision=(
                    "MANUAL_WORDPRESS_PUBLICATION_"
                    "STATE_CONFIRMATION_REQUIRED"
                ),
                error_code=str(exc),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                get_request_count=get_count,
                publication_post_count=post_count,
                response_received=(
                    response_received
                ),
                http_status=http_status,
                returned_status=returned_status,
                post_id_verified=(
                    post_id_verified
                ),
                title_match=title_match,
                content_match=content_match,
                category_match=category_match,
                publication_verified=(
                    publication_verified
                ),
                publication_result_unknown=True,
                manual_review_required=True,
            )

            try:
                write_outputs(result)
            except Exception:
                pass

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )

            return 2

        result = build_result(
            status=(
                "BLOCKED_WORDPRESS_PUBLICATION_"
                "BEFORE_AUTHORIZATION_CONSUMPTION"
            ),
            decision=(
                "FAIL_CLOSED_M16_AUTHORIZATION_"
                "REMAINS_UNCONSUMED"
            ),
            error_code=str(exc),
            attempt_id=None,
            authorization_consumed=False,
            consumption_digest=None,
            get_request_count=get_count,
            publication_post_count=0,
            response_received=False,
            http_status=(
                client.last_http_status
                if client is not None
                else None
            ),
            returned_status=None,
            post_id_verified=False,
            title_match=False,
            content_match=False,
            category_match=False,
            publication_verified=False,
            publication_result_unknown=False,
            manual_review_required=False,
        )

        write_outputs(result)

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
        post_count = (
            client.publication_post_count
            if client is not None
            else 0
        )

        if authorization_consumed:
            error_code = (
                "UNEXPECTED_POST_CONSUMPTION_FAILURE"
            )

            if (
                attempt_id is not None
                and not SECRET_RESPONSE.exists()
            ):
                try:
                    write_secret_response(
                        attempt_id=attempt_id,
                        response_received=(
                            response_received
                        ),
                        http_status=http_status,
                        final_url_verified=False,
                        content_type=None,
                        raw_body=None,
                        parsed_json=None,
                        error_code=error_code,
                    )
                except Exception:
                    pass

            result = build_result(
                status=(
                    "BLOCKED_WORDPRESS_PUBLICATION_"
                    "UNEXPECTED_AUTHORIZATION_"
                    "CONSUMED_NO_RETRY"
                ),
                decision=(
                    "MANUAL_WORDPRESS_PUBLICATION_"
                    "STATE_CONFIRMATION_REQUIRED"
                ),
                error_code=error_code,
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                get_request_count=get_count,
                publication_post_count=post_count,
                response_received=(
                    response_received
                ),
                http_status=http_status,
                returned_status=returned_status,
                post_id_verified=(
                    post_id_verified
                ),
                title_match=title_match,
                content_match=content_match,
                category_match=category_match,
                publication_verified=(
                    publication_verified
                ),
                publication_result_unknown=True,
                manual_review_required=True,
            )

            try:
                write_outputs(result)
            except Exception:
                pass

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )

            return 2

        result = build_result(
            status=(
                "BLOCKED_WORDPRESS_PUBLICATION_"
                "UNEXPECTED_BEFORE_AUTHORIZATION_"
                "CONSUMPTION"
            ),
            decision=(
                "FAIL_CLOSED_M16_AUTHORIZATION_"
                "REMAINS_UNCONSUMED"
            ),
            error_code=(
                "UNEXPECTED_PRE_CONSUMPTION_FAILURE"
            ),
            attempt_id=None,
            authorization_consumed=False,
            consumption_digest=None,
            get_request_count=get_count,
            publication_post_count=0,
            response_received=False,
            http_status=None,
            returned_status=None,
            post_id_verified=False,
            title_match=False,
            content_match=False,
            category_match=False,
            publication_verified=False,
            publication_result_unknown=False,
            manual_review_required=False,
        )

        write_outputs(result)

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
