#!/usr/bin/env python3

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import pwd
import re
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
    "new_release_wp_writer_authenticated_"
    "network_preflight_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_network_approval.json"
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
M11_FIX2_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload_human_review.json"
)
M11_FIX2_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m11_fix2_result.json"
)
M12_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
M12_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m12_result.json"
)
M13_PRE_WRITER_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_writer_result.json"
)
M13_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)

WRITER_CREDENTIAL = Path(
    "/etc/ai-media-os/credential.env"
)

RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_network_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_network_report.md"
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
EXPECTED_M12_AUTH_SHA = (
    "7c9662a7a13502e165862e4524278992"
    "28794bce6904a0215c45a5b54ba1142b"
)
EXPECTED_M12_AUTH_DIGEST = (
    "d3ede61a71d75cbbc00a594f0a8d319a"
    "ed0e598bd9c061609a52bed7e96d07c3"
)
EXPECTED_M12_RESULT_DIGEST = (
    "51b0602ae6daf31f583693f6052bec44"
    "cc45ead92da4296075c6fc6f5cad6fc4"
)
EXPECTED_M13_PRE_WRITER_DIGEST = (
    "aee2c18d623fc54142312b8c06ee18a6"
    "553f251dcc5023db5b1ca82b4566ea69"
)
EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
)

REQUIRED_KEYS = (
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
)

MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class ValidationError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValidationError(code)


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


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.exists() and path.is_file(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
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
    expected: str,
) -> None:
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
    require(
        stored == expected,
        f"DIGEST_EXPECTED_MISMATCH:{field}",
    )


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


def normalize_env_value(raw_value: str) -> str:
    value = raw_value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    return value


def read_required_credentials(
    path: Path,
) -> tuple[dict[str, str], os.stat_result]:
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
        pwd.getpwuid(before.st_uid).pw_name == "deploy",
        "WRITER_CREDENTIAL_OWNER_NOT_DEPLOY",
    )

    values: dict[str, list[str]] = {
        key: []
        for key in REQUIRED_KEYS
    }

    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                require(
                    "\x00" not in raw_line,
                    "WRITER_CREDENTIAL_CONTAINS_NUL",
                )

                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.startswith("export "):
                    line = line[7:].lstrip()

                key, separator, raw_value = line.partition("=")
                key = key.strip()

                if separator == "=" and key in values:
                    values[key].append(
                        normalize_env_value(raw_value)
                    )
    except UnicodeDecodeError:
        raise ValidationError(
            "WRITER_CREDENTIAL_ENCODING_INVALID"
        ) from None

    for key in REQUIRED_KEYS:
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
        for key in REQUIRED_KEYS
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


def validate_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)

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


def validate_request_url(url: str) -> None:
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
        parsed.path.startswith("/wp-json/wp/v2/"),
        "REQUEST_URL_PATH_OUTSIDE_ALLOWED_REST_SCOPE",
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
        raise ValidationError("REDIRECT_BLOCKED")


class SafeWordPressGetClient:
    def __init__(
        self,
        origin: str,
        authorization_header: str,
    ) -> None:
        self.origin = origin
        self.authorization_header = authorization_header
        self.get_request_count = 0

        context = ssl.create_default_context()

        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            NoRedirectHandler(),
            urllib.request.HTTPSHandler(
                context=context
            ),
        )

    def get_json(
        self,
        path: str,
        query: dict[str, Any],
    ) -> tuple[Any, dict[str, str], int]:
        require(
            self.get_request_count < 3,
            "GET_REQUEST_COUNT_LIMIT_EXCEEDED",
        )

        query_string = urllib.parse.urlencode(
            query,
            doseq=True,
            encoding="utf-8",
        )

        url = self.origin + path

        if query_string:
            url += "?" + query_string

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
                    "ai-media-os-m13-pre-network/1.0"
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

                require(
                    status_code == 200,
                    f"UNEXPECTED_HTTP_STATUS_{status_code}",
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

                content_length = (
                    response.headers.get(
                        "Content-Length"
                    )
                )

                if content_length is not None:
                    try:
                        parsed_length = int(
                            content_length
                        )
                    except ValueError:
                        raise ValidationError(
                            "INVALID_RESPONSE_CONTENT_LENGTH"
                        ) from None

                    require(
                        parsed_length
                        <= MAX_RESPONSE_BYTES,
                        "RESPONSE_BODY_TOO_LARGE",
                    )

                body = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

                require(
                    len(body)
                    <= MAX_RESPONSE_BYTES,
                    "RESPONSE_BODY_TOO_LARGE",
                )

                try:
                    parsed_body = json.loads(
                        body.decode("utf-8")
                    )
                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ):
                    raise ValidationError(
                        "WORDPRESS_RESPONSE_JSON_PARSE_FAILED"
                    ) from None

                safe_headers = {
                    "x-wp-total": response.headers.get(
                        "X-WP-Total",
                        "",
                    ),
                    "x-wp-totalpages": response.headers.get(
                        "X-WP-TotalPages",
                        "",
                    ),
                }

                return (
                    parsed_body,
                    safe_headers,
                    status_code,
                )

        except ValidationError:
            raise
        except urllib.error.HTTPError as exc:
            code = int(exc.code)

            try:
                exc.close()
            except Exception:
                pass

            if 300 <= code < 400:
                raise ValidationError(
                    "REDIRECT_BLOCKED"
                ) from None

            raise ValidationError(
                f"WORDPRESS_HTTP_STATUS_{code}"
            ) from None
        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ssl.SSLError,
        ):
            raise ValidationError(
                "WORDPRESS_NETWORK_REQUEST_FAILED"
            ) from None


def build_result(
    *,
    status: str,
    decision: str,
    error_code: str | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-"
            "RECOVERY-M13-PRE-NETWORK"
        ),
        "status": status,
        "decision": decision,
        "error_code": error_code,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "connection_scheme_https": (
            state["connection_scheme_https"]
        ),
        "connection_host_hoshido_jp": (
            state["connection_host_hoshido_jp"]
        ),
        "cross_host_redirect_followed": False,
        "proxy_used": False,
        "authenticated": state["authenticated"],
        "edit_posts": state["edit_posts"],
        "category_id_10_verified": (
            state["category_id_10_verified"]
        ),
        "category_name_verified": (
            state["category_name_verified"]
        ),
        "duplicate_candidate_count": (
            state["duplicate_candidate_count"]
        ),
        "duplicate_exact_match_count": (
            state["duplicate_exact_match_count"]
        ),
        "duplicate_detected": (
            state["duplicate_detected"]
        ),
        "duplicate_raw_fields_verified": (
            state["duplicate_raw_fields_verified"]
        ),
        "users_me_http_status": (
            state["users_me_http_status"]
        ),
        "category_http_status": (
            state["category_http_status"]
        ),
        "duplicate_search_http_status": (
            state["duplicate_search_http_status"]
        ),
        "http_get_request_count": (
            state["http_get_request_count"]
        ),
        "http_non_get_request_count": 0,
        "automatic_retry_performed": False,
        "credential_file_regular": (
            state["credential_file_regular"]
        ),
        "credential_file_symlink": False,
        "credential_file_mode_0600": (
            state["credential_file_mode_0600"]
        ),
        "credential_file_owner_deploy": (
            state["credential_file_owner_deploy"]
        ),
        "credential_required_keys_exactly_once": (
            state[
                "credential_required_keys_exactly_once"
            ]
        ),
        "credential_required_values_nonempty": (
            state[
                "credential_required_values_nonempty"
            ]
        ),
        "credential_file_modified": False,
        "credential_values_output": False,
        "username_output": False,
        "application_password_output": False,
        "authorization_header_output": False,
        "credential_length_output": False,
        "credential_mask_output": False,
        "credential_hash_output": False,
        "credential_file_content_output": False,
        "full_wordpress_response_output": False,
        "existing_post_id_output": False,
        "existing_post_content_output": False,
        "payload_file_sha256": EXPECTED_PAYLOAD_SHA,
        "payload_digest_sha256": (
            EXPECTED_PAYLOAD_DIGEST
        ),
        "payload_unchanged": (
            state["payload_unchanged"]
        ),
        "article_unchanged": (
            state["article_unchanged"]
        ),
        "m13_pre_writer_result_digest_sha256": (
            EXPECTED_M13_PRE_WRITER_DIGEST
        ),
        "m12_authorization_file_sha256": (
            EXPECTED_M12_AUTH_SHA
        ),
        "m12_authorization_digest_sha256": (
            EXPECTED_M12_AUTH_DIGEST
        ),
        "m12_authorization_consumed": False,
        "m12_authorization_reuse_allowed": False,
        "m12_automatic_retry_allowed": False,
        "m12_automatic_reissue_allowed": False,
        "m13_consumption_artifact_exists": False,
        "network_connection_performed": (
            state["http_get_request_count"] > 0
        ),
        "wordpress_access_performed": (
            state["http_get_request_count"] > 0
        ),
        "wordpress_permission_check_performed": (
            state["users_me_http_status"] == 200
        ),
        "wordpress_category_check_performed": (
            state["category_http_status"] == 200
        ),
        "wordpress_duplicate_check_performed": (
            state["duplicate_search_http_status"]
            == 200
        ),
        "wordpress_write_performed": False,
        "wordpress_draft_created": False,
        "wordpress_published": False,
        "category_created": False,
        "category_updated": False,
        "media_uploaded": False,
        "x_post_performed": False,
        "production_status": "NO_GO",
        "safety_state": state["safety_state"],
        "ready_for_final_wordpress_draft_creation_execute_now_gate": (
            state[
                "ready_for_final_wordpress_draft_creation_execute_now_gate"
            ]
        ),
        "ready_for_wordpress_draft_creation": False,
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


def main() -> int:
    state: dict[str, Any] = {
        "connection_scheme_https": False,
        "connection_host_hoshido_jp": False,
        "authenticated": False,
        "edit_posts": False,
        "category_id_10_verified": False,
        "category_name_verified": False,
        "duplicate_candidate_count": 0,
        "duplicate_exact_match_count": 0,
        "duplicate_detected": False,
        "duplicate_raw_fields_verified": False,
        "users_me_http_status": None,
        "category_http_status": None,
        "duplicate_search_http_status": None,
        "http_get_request_count": 0,
        "credential_file_regular": False,
        "credential_file_mode_0600": False,
        "credential_file_owner_deploy": False,
        "credential_required_keys_exactly_once": False,
        "credential_required_values_nonempty": False,
        "payload_unchanged": False,
        "article_unchanged": False,
        "safety_state": (
            "WORDPRESS_WRITER_NETWORK_PREFLIGHT_BLOCKED"
        ),
        "ready_for_final_wordpress_draft_creation_execute_now_gate": (
            False
        ),
    }

    source_paths = {
        "article": ARTICLE,
        "payload": PAYLOAD,
        "m11_fix2_review": M11_FIX2_REVIEW,
        "m11_fix2_result": M11_FIX2_RESULT,
        "m12_authorization": M12_AUTH,
        "m12_result": M12_RESULT,
        "m13_pre_writer_result": (
            M13_PRE_WRITER_RESULT
        ),
    }

    source_hashes: dict[str, str] = {}
    credential_before: os.stat_result | None = None
    client: SafeWordPressGetClient | None = None

    try:
        require(
            not RESULT.exists(),
            "RESULT_ALREADY_EXISTS",
        )
        require(
            not REPORT.exists(),
            "REPORT_ALREADY_EXISTS",
        )
        require(
            not M13_CONSUMPTION.exists(),
            "M13_CONSUMPTION_ALREADY_EXISTS",
        )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_digest(
            approval,
            "approval_evidence_digest_sha256",
            approval[
                "approval_evidence_digest_sha256"
            ],
        )

        require(
            approval["approval_label"]
            == (
                "WORDPRESS_WRITER_AUTHENTICATED_"
                "NETWORK_PREFLIGHT_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M13-PRE-NETWORK"
            ),
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["execution_boundary"][
                "post_requests_allowed"
            ] is False,
            "POST_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "m12_authorization_consumption_allowed"
            ] is False,
            "M12_CONSUMPTION_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "wordpress_write_allowed"
            ] is False,
            "WORDPRESS_WRITE_BOUNDARY_OPEN",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in source_paths.items()
        }

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
            source_hashes["m12_authorization"]
            == EXPECTED_M12_AUTH_SHA,
            "M12_AUTHORIZATION_FILE_SHA_MISMATCH",
        )
        require(
            stat.S_IMODE(PAYLOAD.stat().st_mode)
            == 0o600,
            "PAYLOAD_MODE_NOT_0600",
        )
        require(
            not PAYLOAD.is_symlink(),
            "PAYLOAD_SYMLINK_REJECTED",
        )

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        review = load_json(M11_FIX2_REVIEW)
        m11_result = load_json(
            M11_FIX2_RESULT
        )
        m12_auth = load_json(M12_AUTH)
        m12_result = load_json(M12_RESULT)
        pre_writer_result = load_json(
            M13_PRE_WRITER_RESULT
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
            m11_result,
            "result_digest_sha256",
            EXPECTED_M11_FIX2_RESULT_DIGEST,
        )
        verify_digest(
            m12_auth,
            "authorization_digest_sha256",
            EXPECTED_M12_AUTH_DIGEST,
        )
        verify_digest(
            m12_result,
            "result_digest_sha256",
            EXPECTED_M12_RESULT_DIGEST,
        )
        verify_digest(
            pre_writer_result,
            "result_digest_sha256",
            EXPECTED_M13_PRE_WRITER_DIGEST,
        )

        require(
            pre_writer_result["status"]
            == (
                "PASS_WORDPRESS_WRITER_CREDENTIAL_"
                "NONSECRET_PREFLIGHT_NO_NETWORK_"
                "NO_WORDPRESS_NO_AUTH_CONSUMPTION"
            ),
            "M13_PRE_WRITER_STATUS_MISMATCH",
        )
        require(
            pre_writer_result[
                "ready_for_writer_network_preflight_gate"
            ] is True,
            "M13_PRE_WRITER_NOT_READY",
        )

        require(
            m12_auth["single_use"] is True,
            "M12_AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            m12_auth["authorization_consumed"]
            is False,
            "M12_AUTHORIZATION_ALREADY_CONSUMED",
        )
        require(
            m12_auth[
                "authorization_reuse_allowed"
            ] is False,
            "M12_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m12_auth["automatic_retry_allowed"]
            is False,
            "M12_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m12_auth["automatic_reissue_allowed"]
            is False,
            "M12_AUTOMATIC_REISSUE_ALLOWED",
        )

        require(
            payload["title"] == EXPECTED_TITLE,
            "PAYLOAD_TITLE_MISMATCH",
        )
        require(
            payload["title"]
            == article["article_title"],
            "PAYLOAD_ARTICLE_TITLE_MISMATCH",
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
            payload["categories"] == [10],
            "PAYLOAD_CATEGORIES_MISMATCH",
        )
        require(
            payload["category_id"] == 10,
            "PAYLOAD_CATEGORY_ID_MISMATCH",
        )
        require(
            payload["content_item_id"]
            == "new-release-comic-20260703-001",
            "PAYLOAD_CONTENT_ITEM_ID_MISMATCH",
        )

        state["payload_unchanged"] = True
        state["article_unchanged"] = True

        credentials, credential_before = (
            read_required_credentials(
                WRITER_CREDENTIAL
            )
        )

        state["credential_file_regular"] = True
        state["credential_file_mode_0600"] = True
        state["credential_file_owner_deploy"] = True
        state[
            "credential_required_keys_exactly_once"
        ] = True
        state[
            "credential_required_values_nonempty"
        ] = True

        origin = validate_base_url(
            credentials["WORDPRESS_BASE_URL"]
        )

        state["connection_scheme_https"] = True
        state["connection_host_hoshido_jp"] = True

        credential_pair = (
            credentials["WORDPRESS_USERNAME"]
            + ":"
            + credentials[
                "WORDPRESS_APP_PASSWORD"
            ]
        )

        authorization_header = (
            "Basic "
            + base64.b64encode(
                credential_pair.encode("utf-8")
            ).decode("ascii")
        )

        client = SafeWordPressGetClient(
            origin=origin,
            authorization_header=(
                authorization_header
            ),
        )

        user_data, _, user_status = (
            client.get_json(
                "/wp-json/wp/v2/users/me",
                {
                    "context": "edit",
                },
            )
        )

        state["http_get_request_count"] = (
            client.get_request_count
        )
        state["users_me_http_status"] = (
            user_status
        )

        require(
            isinstance(user_data, dict),
            "USERS_ME_RESPONSE_NOT_OBJECT",
        )
        require(
            isinstance(user_data.get("id"), int)
            and user_data["id"] > 0,
            "AUTHENTICATED_USER_INVALID",
        )

        capabilities = user_data.get(
            "capabilities"
        )

        require(
            isinstance(capabilities, dict),
            "USER_CAPABILITIES_MISSING",
        )
        require(
            capabilities.get("edit_posts")
            is True,
            "EDIT_POSTS_CAPABILITY_MISSING",
        )

        state["authenticated"] = True
        state["edit_posts"] = True

        category_data, _, category_status = (
            client.get_json(
                "/wp-json/wp/v2/categories/10",
                {
                    "context": "view",
                },
            )
        )

        state["http_get_request_count"] = (
            client.get_request_count
        )
        state["category_http_status"] = (
            category_status
        )

        require(
            isinstance(category_data, dict),
            "CATEGORY_RESPONSE_NOT_OBJECT",
        )
        require(
            category_data.get("id") == 10,
            "CATEGORY_ID_10_MISMATCH",
        )
        require(
            category_data.get("name") == "最新巻",
            "CATEGORY_NAME_MISMATCH",
        )
        require(
            category_data.get("taxonomy")
            == "category",
            "CATEGORY_TAXONOMY_MISMATCH",
        )

        state["category_id_10_verified"] = True
        state["category_name_verified"] = True

        posts_data, posts_headers, posts_status = (
            client.get_json(
                "/wp-json/wp/v2/posts",
                {
                    "context": "edit",
                    "status": "draft",
                    "search": EXPECTED_TITLE,
                    "per_page": 100,
                    "page": 1,
                    "_fields": (
                        "title,content,status,categories"
                    ),
                },
            )
        )

        state["http_get_request_count"] = (
            client.get_request_count
        )
        state[
            "duplicate_search_http_status"
        ] = posts_status

        require(
            client.get_request_count == 3,
            "GET_REQUEST_COUNT_MISMATCH",
        )
        require(
            isinstance(posts_data, list),
            "POSTS_RESPONSE_NOT_ARRAY",
        )

        total_raw = posts_headers[
            "x-wp-total"
        ]
        total_pages_raw = posts_headers[
            "x-wp-totalpages"
        ]

        require(
            re.fullmatch(r"[0-9]+", total_raw)
            is not None,
            "X_WP_TOTAL_HEADER_INVALID",
        )
        require(
            re.fullmatch(
                r"[0-9]+",
                total_pages_raw,
            )
            is not None,
            "X_WP_TOTALPAGES_HEADER_INVALID",
        )

        total = int(total_raw)
        total_pages = int(total_pages_raw)

        require(
            total_pages <= 1,
            "DUPLICATE_SEARCH_RESULT_SET_INCOMPLETE",
        )
        require(
            total == len(posts_data),
            "DUPLICATE_SEARCH_TOTAL_MISMATCH",
        )

        state["duplicate_candidate_count"] = (
            len(posts_data)
        )

        exact_match_count = 0

        for candidate in posts_data:
            require(
                isinstance(candidate, dict),
                "DUPLICATE_CANDIDATE_NOT_OBJECT",
            )
            require(
                candidate.get("status")
                == "draft",
                "DUPLICATE_CANDIDATE_STATUS_MISMATCH",
            )

            title_object = candidate.get(
                "title"
            )
            content_object = candidate.get(
                "content"
            )

            require(
                isinstance(title_object, dict),
                "DUPLICATE_TITLE_OBJECT_MISSING",
            )
            require(
                isinstance(content_object, dict),
                "DUPLICATE_CONTENT_OBJECT_MISSING",
            )
            require(
                isinstance(
                    title_object.get("raw"),
                    str,
                ),
                "DUPLICATE_TITLE_RAW_UNAVAILABLE",
            )
            require(
                isinstance(
                    content_object.get("raw"),
                    str,
                ),
                "DUPLICATE_CONTENT_RAW_UNAVAILABLE",
            )

            if (
                title_object["raw"]
                == payload["title"]
                and content_object["raw"]
                == payload["content_html"]
            ):
                exact_match_count += 1

        state[
            "duplicate_raw_fields_verified"
        ] = True
        state[
            "duplicate_exact_match_count"
        ] = exact_match_count
        state["duplicate_detected"] = (
            exact_match_count > 0
        )

        require(
            exact_match_count == 0,
            "DUPLICATE_DRAFT_DETECTED",
        )

        credential_after = (
            WRITER_CREDENTIAL.lstat()
        )

        require(
            credential_before is not None
            and same_metadata(
                credential_before,
                credential_after,
            ),
            "WRITER_CREDENTIAL_METADATA_CHANGED",
        )

        for name, path in source_paths.items():
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        require(
            not M13_CONSUMPTION.exists(),
            "M13_CONSUMPTION_CREATED_UNEXPECTEDLY",
        )

        state["safety_state"] = (
            "WRITER_AUTHENTICATED_NETWORK_"
            "PREFLIGHT_PASS_M12_AUTHORIZATION_UNCONSUMED"
        )
        state[
            "ready_for_final_wordpress_draft_creation_execute_now_gate"
        ] = True

        result = build_result(
            status=(
                "PASS_WORDPRESS_WRITER_AUTHENTICATED_"
                "NETWORK_PREFLIGHT_GET_ONLY_"
                "NO_DUPLICATE_NO_AUTH_CONSUMPTION"
            ),
            decision=(
                "WRITER_AUTHENTICATION_PERMISSION_CATEGORY_"
                "AND_DUPLICATE_CHECKS_PASS_READY_FOR_FINAL_"
                "WORDPRESS_DRAFT_EXECUTE_NOW_GATE"
            ),
            error_code=None,
            state=state,
        )

        write_json(RESULT, result)

        write_text(
            REPORT,
            f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M13-PRE-NETWORK

- Status: `{result["status"]}`
- Authenticated: `true`
- edit_posts: `true`
- Category ID 10 verified: `true`
- Category name verified: `true`
- Duplicate candidate count: `{result["duplicate_candidate_count"]}`
- Duplicate exact match count: `0`
- Duplicate detected: `false`
- GET request count: `3`
- Non-GET request count: `0`
- Automatic retry performed: `false`
- Credential values output: `false`
- Full WordPress response output: `false`
- M12 authorization consumed: `false`
- WordPress write performed: `false`
- WordPress draft created: `false`
- Production status: `NO_GO`
- Ready for final WordPress draft execute-now gate: `true`
""",
        )

        del credential_pair
        del authorization_header
        del credentials
        del user_data
        del category_data
        del posts_data

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        if client is not None:
            state["http_get_request_count"] = (
                client.get_request_count
            )

        if credential_before is not None:
            try:
                require(
                    same_metadata(
                        credential_before,
                        WRITER_CREDENTIAL.lstat(),
                    ),
                    "WRITER_CREDENTIAL_METADATA_CHANGED",
                )
            except (
                ValidationError,
                FileNotFoundError,
            ):
                exc = ValidationError(
                    "WRITER_CREDENTIAL_METADATA_CHANGED"
                )

        if source_hashes:
            try:
                for name, path in (
                    source_paths.items()
                ):
                    require(
                        file_sha(path)
                        == source_hashes[name],
                        f"SOURCE_ARTIFACT_CHANGED:{name}",
                    )
            except (
                ValidationError,
                FileNotFoundError,
            ) as source_exc:
                exc = ValidationError(
                    str(source_exc)
                )

        state["duplicate_detected"] = (
            str(exc)
            == "DUPLICATE_DRAFT_DETECTED"
        )
        state["safety_state"] = (
            "WRITER_AUTHENTICATED_NETWORK_"
            "PREFLIGHT_BLOCKED_M12_AUTHORIZATION_UNCONSUMED"
        )

        result = build_result(
            status=(
                "BLOCKED_WORDPRESS_WRITER_AUTHENTICATED_"
                "NETWORK_PREFLIGHT_NO_AUTH_CONSUMPTION"
            ),
            decision=(
                "FAIL_CLOSED_NO_WORDPRESS_WRITE_"
                "M12_AUTHORIZATION_REMAINS_UNCONSUMED"
            ),
            error_code=str(exc),
            state=state,
        )

        try:
            write_json(RESULT, result)

            write_text(
                REPORT,
                f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M13-PRE-NETWORK

- Status: `{result["status"]}`
- Error code: `{result["error_code"]}`
- Authenticated: `{str(result["authenticated"]).lower()}`
- edit_posts: `{str(result["edit_posts"]).lower()}`
- Category ID 10 verified: `{str(result["category_id_10_verified"]).lower()}`
- Duplicate exact match count: `{result["duplicate_exact_match_count"]}`
- Duplicate detected: `{str(result["duplicate_detected"]).lower()}`
- GET request count: `{result["http_get_request_count"]}`
- Non-GET request count: `0`
- M12 authorization consumed: `false`
- WordPress write performed: `false`
- WordPress draft created: `false`
- Production status: `NO_GO`
""",
            )
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
        state["safety_state"] = (
            "UNEXPECTED_NETWORK_PREFLIGHT_FAILURE_"
            "M12_AUTHORIZATION_UNCONSUMED"
        )

        result = build_result(
            status=(
                "BLOCKED_WORDPRESS_WRITER_AUTHENTICATED_"
                "NETWORK_PREFLIGHT_NO_AUTH_CONSUMPTION"
            ),
            decision=(
                "UNEXPECTED_FAILURE_FAIL_CLOSED_"
                "NO_WORDPRESS_WRITE"
            ),
            error_code=(
                "UNEXPECTED_NETWORK_PREFLIGHT_FAILURE"
            ),
            state=state,
        )

        try:
            write_json(RESULT, result)
            write_text(
                REPORT,
                """# LS-NEW-BATCH-4G-2E-RECOVERY-M13-PRE-NETWORK

- Status: `BLOCKED_WORDPRESS_WRITER_AUTHENTICATED_NETWORK_PREFLIGHT_NO_AUTH_CONSUMPTION`
- Error code: `UNEXPECTED_NETWORK_PREFLIGHT_FAILURE`
- M12 authorization consumed: `false`
- WordPress write performed: `false`
- WordPress draft created: `false`
- Production status: `NO_GO`
""",
            )
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
