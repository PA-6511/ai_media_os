#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import copy
import errno
import grp
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
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_one_shot_actual_category_lookup_policy.json"
)
APPROVAL_PATH = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2b_approval.json"
)
SOURCE_RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2a_result.json"
)
SOURCE_PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_actual_read_only_lookup_authorization_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2b_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2b_one_shot_actual_category_lookup_report.md"
)


class ValidationError(RuntimeError):
    pass


class ControlledBlock(RuntimeError):
    def __init__(
        self,
        *,
        status: str,
        reason: str,
        telemetry: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.telemetry = telemetry or {}


class NoRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        return None


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


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(
            f"required file missing: {path}"
        )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise ValidationError(
            f"JSON root must be object: {path}"
        )

    return value


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    os.chmod(temporary, 0o600)
    temporary.replace(path)


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        value,
        encoding="utf-8",
    )

    os.chmod(temporary, 0o600)
    temporary.replace(path)


def resolve_repo_path(value: str) -> Path:
    path = Path(value)

    if path.is_absolute():
        return path

    return ROOT / path


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2B",
        "policy phase mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == (
            "NEW_RELEASE_WP_ONE_SHOT_ACTUAL_"
            "CATEGORY_LOOKUP_POLICY_V1"
        ),
        "policy identity mismatch",
    )
    checks.append("policy_identity")

    require(
        policy.get("operation_mode")
        == (
            "APPROVED_ONE_SHOT_ACTUAL_"
            "READ_ONLY_CATEGORY_LOOKUP"
        ),
        "operation mode mismatch",
    )
    checks.append("approved_one_shot_mode")

    approval = policy["approval_contract"]

    require(
        approval["required_approval_label"]
        == (
            "APPROVED_FOR_ONE_SHOT_"
            "READ_ONLY_CATEGORY_LOOKUP_ONLY"
        ),
        "approval label mismatch",
    )
    require(
        approval["approval_consumed_on_attempt_reservation"]
        is True,
        "approval must be consumed on reservation",
    )
    require(
        approval["approval_reuse_allowed"]
        is False,
        "approval reuse must be forbidden",
    )
    checks.append("approval_contract")

    scope = policy["one_shot_http_scope"]

    require(
        scope["maximum_http_requests"] == 1,
        "maximum request count must be one",
    )
    require(
        scope["maximum_attempts"] == 1,
        "maximum attempt count must be one",
    )
    require(
        scope["retry_allowed"] is False,
        "retry must remain disabled",
    )
    require(
        scope["method"] == "GET",
        "only GET is allowed",
    )
    require(
        scope["rest_path"]
        == "/wp-json/wp/v2/categories",
        "REST path mismatch",
    )
    require(
        scope["request_body_allowed"] is False,
        "request body must remain forbidden",
    )
    require(
        scope["redirect_follow_allowed"] is False,
        "redirects must remain disabled",
    )
    require(
        scope["proxy_use_allowed"] is False,
        "proxies must remain disabled",
    )
    require(
        scope["tls_verification_required"] is True,
        "TLS verification must remain enabled",
    )
    checks.append("one_shot_http_scope")

    boundary = policy["execution_boundary"]

    for field in [
        "credential_file_read_allowed",
        "authorization_header_construction_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "tls_connection_allowed",
        "wordpress_api_call_allowed",
        "wordpress_category_lookup_allowed",
        "wordpress_response_read_allowed",
    ]:
        require(
            boundary[field] is True,
            f"{field} must be true",
        )

    for field in [
        "wordpress_post_read_allowed",
        "wordpress_media_read_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "x_api_call_allowed",
        "external_api_call_allowed",
        "production_payload_modification_allowed",
    ]:
        require(
            boundary[field] is False,
            f"{field} must remain false",
        )

    checks.append("read_only_execution_boundary")

    return checks


def validate_source(
    policy: dict[str, Any],
    source_result: dict[str, Any],
    source_package: dict[str, Any],
) -> list[str]:
    source_contract = policy["source_contract"]

    require(
        source_result.get("phase_id")
        == policy["source_phase_id"],
        "source result phase mismatch",
    )
    require(
        source_result.get("status")
        == source_contract[
            "required_source_status"
        ],
        "source status mismatch",
    )
    require(
        source_result.get("decision")
        == source_contract[
            "required_source_decision"
        ],
        "source decision mismatch",
    )
    require(
        source_result.get(
            "http_request_performed"
        )
        is False,
        "source must not have performed HTTP",
    )
    require(
        source_result.get(
            "wordpress_write_performed"
        )
        is False,
        "source must not have written to WordPress",
    )

    expected_package_digest = (
        source_result[
            "authorization_package_digest_sha256"
        ]
    )

    require(
        source_package.get(
            "authorization_package_digest_sha256"
        )
        == expected_package_digest,
        "source package digest reference mismatch",
    )

    package_without_digest = copy.deepcopy(
        source_package
    )
    package_without_digest.pop(
        "authorization_package_digest_sha256",
        None,
    )

    require(
        canonical_digest(package_without_digest)
        == expected_package_digest,
        "source package digest verification failed",
    )

    return [
        "source_phase_identity",
        "source_status_verified",
        "source_decision_verified",
        "source_http_unperformed",
        "source_wordpress_write_unperformed",
        "source_package_digest_verified",
    ]


def validate_approval(
    policy: dict[str, Any],
    approval: dict[str, Any],
    source_result: dict[str, Any],
) -> list[str]:
    required_label = policy[
        "approval_contract"
    ]["required_approval_label"]

    require(
        approval.get("phase_id")
        == "LS-NEW-BATCH-4G-2B",
        "approval phase mismatch",
    )
    require(
        approval.get("approval_label")
        == required_label,
        "approval label mismatch",
    )
    require(
        approval.get("human_explicit_approval")
        is True,
        "human explicit approval missing",
    )
    require(
        approval.get("approved_by")
        == "HUMAN_OPERATOR",
        "approval actor mismatch",
    )
    require(
        approval.get("approval_label_consumed")
        is False,
        "approval evidence must be initially unconsumed",
    )
    require(
        approval.get("approval_reuse_allowed")
        is False,
        "approval reuse must be forbidden",
    )
    require(
        approval.get("execution_allowed")
        is True,
        "approval evidence does not permit execution",
    )

    require(
        approval.get(
            "source_authorization_scope_digest_sha256"
        )
        == source_result[
            "authorization_scope_digest_sha256"
        ],
        "approval scope digest mismatch",
    )
    require(
        approval.get(
            "source_authorization_package_digest_sha256"
        )
        == source_result[
            "authorization_package_digest_sha256"
        ],
        "approval package digest mismatch",
    )

    evidence_digest = approval.get(
        "approval_evidence_digest_sha256"
    )

    require(
        isinstance(evidence_digest, str)
        and len(evidence_digest) == 64,
        "approval evidence digest invalid",
    )

    approval_without_digest = copy.deepcopy(
        approval
    )
    approval_without_digest.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        canonical_digest(approval_without_digest)
        == evidence_digest,
        "approval evidence digest verification failed",
    )

    scope = approval["approval_scope"]

    require(
        scope["maximum_http_requests"] == 1,
        "approval request count mismatch",
    )
    require(
        scope["maximum_attempts"] == 1,
        "approval attempt count mismatch",
    )
    require(
        scope["retry_allowed"] is False,
        "approval retry must be false",
    )
    require(
        scope["method"] == "GET",
        "approval method must be GET",
    )
    require(
        scope["target_hostname"]
        == "hoshido.jp",
        "approval hostname mismatch",
    )
    require(
        scope["wordpress_write_allowed"]
        is False,
        "approval must not permit writes",
    )
    require(
        scope["payload_modification_allowed"]
        is False,
        "approval must not permit payload modification",
    )

    return [
        "human_explicit_approval_verified",
        "approval_label_verified",
        "approval_scope_verified",
        "approval_digest_verified",
        "approval_unconsumed_before_reservation",
        "approval_reuse_forbidden",
    ]


def reserve_one_shot(
    lock_path: Path,
    *,
    approval: dict[str, Any],
) -> dict[str, Any]:
    lock_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    reservation = {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-4G-2B",
        "lock_id": "ls-new-batch-4g-2b-one-shot",
        "state": "ATTEMPT_RESERVED_APPROVAL_CONSUMED",
        "reserved_at_utc": utc_now(),
        "approval_label": approval[
            "approval_label"
        ],
        "approval_evidence_digest_sha256": approval[
            "approval_evidence_digest_sha256"
        ],
        "approval_label_consumed": True,
        "http_request_limit": 1,
        "http_attempt_limit": 1,
        "retry_allowed": False,
        "execution_complete": False,
    }

    encoded = (
        json.dumps(
            reservation,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    try:
        fd = os.open(
            lock_path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise ControlledBlock(
            status=(
                "BLOCKED_ONE_SHOT_APPROVAL_"
                "ALREADY_CONSUMED"
            ),
            reason=(
                "The one-shot execution lock already "
                "exists. No credential or network access "
                "was performed."
            ),
            telemetry={
                "one_shot_lock_existed": True,
                "approval_label_consumed": True,
            },
        ) from exc

    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)

    return reservation


def finalize_lock(
    lock_path: Path,
    reservation: dict[str, Any],
    *,
    final_state: str,
    result_status: str,
    http_request_attempt_count: int,
) -> None:
    final = copy.deepcopy(reservation)

    final.update(
        {
            "state": final_state,
            "completed_at_utc": utc_now(),
            "result_status": result_status,
            "http_request_attempt_count": (
                http_request_attempt_count
            ),
            "approval_label_consumed": True,
            "execution_complete": True,
        }
    )

    write_json(lock_path, final)


def read_credentials(
    policy: dict[str, Any],
) -> dict[str, str]:
    contract = policy["credential_contract"]
    path = Path(
        contract["credential_file_path"]
    )

    try:
        metadata = os.lstat(path)
    except FileNotFoundError as exc:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "FILE_MISSING"
            ),
            reason=(
                "Production credential file is missing."
            ),
        ) from exc

    if stat.S_ISLNK(metadata.st_mode):
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_SYMLINK"
            ),
            reason=(
                "Production credential path is a symbolic link."
            ),
        )

    if not stat.S_ISREG(metadata.st_mode):
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "NOT_REGULAR_FILE"
            ),
            reason=(
                "Production credential path is not "
                "a regular file."
            ),
        )

    owner_name = pwd.getpwuid(
        metadata.st_uid
    ).pw_name
    group_name = grp.getgrgid(
        metadata.st_gid
    ).gr_name
    mode_octal = (
        f"{stat.S_IMODE(metadata.st_mode):04o}"
    )

    if owner_name != contract["expected_owner"]:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "OWNER_MISMATCH"
            ),
            reason="Credential owner mismatch.",
        )

    if group_name != contract["expected_group"]:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "GROUP_MISMATCH"
            ),
            reason="Credential group mismatch.",
        )

    if mode_octal != contract["required_mode_octal"]:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "MODE_MISMATCH"
            ),
            reason="Credential mode mismatch.",
        )

    flags = os.O_RDONLY

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC

    try:
        fd = os.open(path, flags)
    except OSError as exc:
        status_code = (
            "BLOCKED_PRODUCTION_CREDENTIAL_SYMLINK"
            if exc.errno == errno.ELOOP
            else (
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "OPEN_FAILED"
            )
        )

        raise ControlledBlock(
            status=status_code,
            reason=(
                "Credential file could not be opened safely."
            ),
        ) from exc

    values: dict[str, str] = {}
    duplicate_keys: set[str] = set()
    invalid_format = False

    try:
        with os.fdopen(
            fd,
            mode="r",
            encoding="utf-8",
            errors="strict",
            closefd=True,
        ) as handle:
            for raw_line in handle:
                stripped = raw_line.strip()

                if (
                    stripped == ""
                    or stripped.startswith("#")
                ):
                    continue

                if (
                    stripped.startswith("export ")
                    or "=" not in raw_line
                ):
                    invalid_format = True
                    continue

                key_part, value_part = (
                    raw_line.split("=", 1)
                )
                key = key_part.strip()
                value = value_part.strip()

                if key in values:
                    duplicate_keys.add(key)
                    continue

                values[key] = value

    except UnicodeDecodeError as exc:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "INVALID_ENCODING"
            ),
            reason=(
                "Credential file encoding is invalid."
            ),
        ) from exc

    required_keys = set(
        contract["required_keys"]
    )
    present_keys = set(values)

    if invalid_format:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "INVALID_FORMAT"
            ),
            reason=(
                "Credential file has invalid line structure."
            ),
        )

    if duplicate_keys:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "DUPLICATE_KEYS"
            ),
            reason=(
                "Credential file has duplicate keys."
            ),
        )

    if present_keys != required_keys:
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "KEY_SET_MISMATCH"
            ),
            reason=(
                "Credential key set does not match "
                "the approved contract."
            ),
        )

    if any(
        value == ""
        for value in values.values()
    ):
        raise ControlledBlock(
            status=(
                "BLOCKED_PRODUCTION_CREDENTIAL_"
                "EMPTY_VALUE"
            ),
            reason=(
                "Credential file contains an empty value."
            ),
        )

    return values


def validate_base_url(
    raw_url: str,
    policy: dict[str, Any],
) -> tuple[str, str]:
    contract = policy["credential_contract"]

    try:
        parsed = urllib.parse.urlsplit(
            raw_url.strip()
        )
    except ValueError as exc:
        raise ControlledBlock(
            status=(
                "BLOCKED_INVALID_WORDPRESS_BASE_URL"
            ),
            reason="WordPress base URL is invalid.",
        ) from exc

    if parsed.scheme.lower() != "https":
        raise ControlledBlock(
            status=(
                "BLOCKED_NON_HTTPS_WORDPRESS_BASE_URL"
            ),
            reason="WordPress base URL is not HTTPS.",
        )

    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_BASE_URL_USERINFO"
            ),
            reason=(
                "WordPress base URL contains forbidden userinfo."
            ),
        )

    hostname = (
        parsed.hostname.lower()
        if parsed.hostname
        else None
    )

    if hostname != contract["expected_hostname"]:
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_HOSTNAME_MISMATCH"
            ),
            reason=(
                "WordPress hostname does not match "
                "the approved hostname."
            ),
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_PORT_INVALID"
            ),
            reason="WordPress URL port is invalid.",
        ) from exc

    if port not in contract["allowed_ports"]:
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_PORT_NOT_ALLOWED"
            ),
            reason="WordPress URL port is not allowed.",
        )

    if (
        parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_BASE_URL_SHAPE"
            ),
            reason=(
                "WordPress base URL must contain only "
                "the approved HTTPS origin."
            ),
        )

    netloc = hostname

    if port == 443:
        netloc = f"{hostname}:443"

    origin = urllib.parse.urlunsplit(
        ("https", netloc, "", "", "")
    )

    return origin, hostname


def construct_request_url(
    origin: str,
    policy: dict[str, Any],
) -> str:
    scope = policy["one_shot_http_scope"]

    query = urllib.parse.urlencode(
        scope["query_parameters"]
    )

    return (
        f"{origin}"
        f"{scope['rest_path']}"
        f"?{query}"
    )


def real_transport(
    *,
    request_url: str,
    username: str,
    password: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    scope = policy["one_shot_http_scope"]

    authorization_raw = (
        f"{username}:{password}"
    ).encode("utf-8")

    authorization_value = (
        "Basic "
        + base64.b64encode(
            authorization_raw
        ).decode("ascii")
    )

    request = urllib.request.Request(
        request_url,
        data=None,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": authorization_value,
            "User-Agent": (
                "ai-media-os-readonly-category-lookup/1.0"
            ),
        },
    )

    context = ssl.create_default_context()

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
        urllib.request.HTTPSHandler(
            context=context
        ),
    )

    try:
        with opener.open(
            request,
            timeout=scope["timeout_seconds"],
        ) as response:
            status_code = response.getcode()
            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            body = response.read(
                scope["maximum_response_bytes"]
                + 1
            )

    except urllib.error.HTTPError as exc:
        if exc.code in {
            301,
            302,
            303,
            307,
            308,
        }:
            raise ControlledBlock(
                status=(
                    "BLOCKED_WORDPRESS_REDIRECT"
                ),
                reason=(
                    "WordPress returned a redirect. "
                    "Redirect following is disabled."
                ),
                telemetry={
                    "http_status": exc.code,
                    "http_response_received": True,
                },
            ) from exc

        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_HTTP_ERROR"
            ),
            reason=(
                "WordPress returned an unexpected "
                "HTTP status."
            ),
            telemetry={
                "http_status": exc.code,
                "http_response_received": True,
            },
        ) from exc

    except urllib.error.URLError as exc:
        reason = exc.reason

        if isinstance(reason, ssl.SSLError):
            status = "BLOCKED_WORDPRESS_TLS_FAILURE"
        elif isinstance(reason, socket.timeout):
            status = "BLOCKED_WORDPRESS_READ_TIMEOUT"
        elif isinstance(reason, socket.gaierror):
            status = "BLOCKED_WORDPRESS_DNS_FAILURE"
        else:
            status = (
                "BLOCKED_WORDPRESS_NETWORK_FAILURE"
            )

        raise ControlledBlock(
            status=status,
            reason=(
                "WordPress network request failed "
                "without retry."
            ),
        ) from exc

    except TimeoutError as exc:
        raise ControlledBlock(
            status="BLOCKED_WORDPRESS_READ_TIMEOUT",
            reason=(
                "WordPress request timed out "
                "without retry."
            ),
        ) from exc

    finally:
        authorization_raw = b""
        authorization_value = ""

    if (
        len(body)
        > scope["maximum_response_bytes"]
    ):
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_RESPONSE_TOO_LARGE"
            ),
            reason=(
                "WordPress response exceeded "
                "the approved byte limit."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
            },
        )

    return {
        "http_status": status_code,
        "content_type": content_type,
        "body": body,
        "response_bytes": len(body),
    }


def validate_response(
    response: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    scope = policy["one_shot_http_scope"]
    target = policy["target_category"]

    status_code = response["http_status"]

    if status_code not in scope[
        "allowed_http_statuses"
    ]:
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_HTTP_STATUS"
            ),
            reason=(
                "WordPress returned a non-approved "
                "HTTP status."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
            },
        )

    content_type = response[
        "content_type"
    ].lower()

    if not content_type.startswith(
        scope["required_content_type_prefix"]
    ):
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_INVALID_CONTENT_TYPE"
            ),
            reason=(
                "WordPress response content type "
                "is not JSON."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
            },
        )

    try:
        decoded = response["body"].decode(
            "utf-8"
        )
        payload = json.loads(decoded)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ControlledBlock(
            status="BLOCKED_WORDPRESS_INVALID_JSON",
            reason=(
                "WordPress response is not valid "
                "UTF-8 JSON."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
            },
        ) from exc

    if not isinstance(payload, list):
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_INVALID_RESPONSE"
            ),
            reason=(
                "WordPress category response root "
                "is not an array."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
            },
        )

    normalized: list[dict[str, Any]] = []

    for item in payload:
        if not isinstance(item, dict):
            raise ControlledBlock(
                status=(
                    "BLOCKED_WORDPRESS_INVALID_RESPONSE"
                ),
                reason=(
                    "WordPress category item is "
                    "not an object."
                ),
                telemetry={
                    "http_status": status_code,
                    "http_response_received": True,
                },
            )

        category_id = item.get("id")
        slug = item.get("slug")
        name = item.get("name")
        count = item.get("count")

        if not (
            isinstance(category_id, int)
            and not isinstance(category_id, bool)
            and category_id > 0
        ):
            raise ControlledBlock(
                status=(
                    "BLOCKED_WORDPRESS_CATEGORY_ID_INVALID"
                ),
                reason=(
                    "WordPress category ID is invalid."
                ),
                telemetry={
                    "http_status": status_code,
                    "http_response_received": True,
                },
            )

        if not (
            isinstance(slug, str)
            and isinstance(name, str)
            and isinstance(count, int)
            and not isinstance(count, bool)
            and count >= 0
        ):
            raise ControlledBlock(
                status=(
                    "BLOCKED_WORDPRESS_INVALID_RESPONSE"
                ),
                reason=(
                    "WordPress category fields "
                    "are invalid."
                ),
                telemetry={
                    "http_status": status_code,
                    "http_response_received": True,
                },
            )

        normalized.append(
            {
                "id": category_id,
                "slug": slug,
                "name": name,
                "count": count,
            }
        )

    matches = [
        item
        for item in normalized
        if item["slug"]
        == target["category_slug"]
    ]

    if len(matches) == 0:
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_CATEGORY_NOT_FOUND"
            ),
            reason=(
                "Approved WordPress category slug "
                "was not found."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
                "matched_category_count": 0,
            },
        )

    if len(matches) != 1:
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_CATEGORY_DUPLICATE"
            ),
            reason=(
                "WordPress returned multiple exact "
                "slug matches."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
                "matched_category_count": len(matches),
            },
        )

    matched = matches[0]

    if (
        matched["name"]
        != target["category_name"]
    ):
        raise ControlledBlock(
            status=(
                "BLOCKED_WORDPRESS_CATEGORY_NAME_MISMATCH"
            ),
            reason=(
                "WordPress category name does not "
                "match the approved name."
            ),
            telemetry={
                "http_status": status_code,
                "http_response_received": True,
                "matched_category_count": 1,
            },
        )

    mapping_without_digest = {
        "source_type": "REAL_WORDPRESS_REST",
        "category_slug": matched["slug"],
        "category_name": matched["name"],
        "production_category_id_candidate": (
            matched["id"]
        ),
        "wordpress_post_count": matched["count"],
        "match_state": (
            "MATCHED_REAL_WORDPRESS_READ_ONLY"
        ),
        "human_verification_required": True,
        "production_usable": False,
        "payload_injection_allowed": False,
        "automatic_use_allowed": False,
    }

    mapping = copy.deepcopy(
        mapping_without_digest
    )
    mapping[
        "production_mapping_candidate_digest_sha256"
    ] = canonical_digest(
        mapping_without_digest
    )

    return mapping


def base_result() -> dict[str, Any]:
    return {
        "phase_id": "LS-NEW-BATCH-4G-2B",
        "approval_label": (
            "APPROVED_FOR_ONE_SHOT_"
            "READ_ONLY_CATEGORY_LOOKUP_ONLY"
        ),
        "approval_label_consumed": True,
        "approval_reuse_allowed": False,
        "one_shot_lock_created": True,
        "maximum_http_requests": 1,
        "maximum_attempts": 1,
        "retry_allowed": False,
        "http_method": "GET",
        "rest_path": "/wp-json/wp/v2/categories",
        "target_hostname": "hoshido.jp",
        "target_category_slug": "comic-new-release",
        "target_category_name": "コミック新刊",
        "credential_file_read": False,
        "credential_values_loaded": False,
        "credential_values_output": False,
        "credential_value_lengths_output": False,
        "credential_value_hashes_output": False,
        "authorization_header_constructed": False,
        "authorization_header_output": False,
        "environment_variables_exported": False,
        "dns_resolution_attempted": False,
        "network_connection_attempted": False,
        "tls_connection_attempted": False,
        "tls_verification_required": True,
        "http_request_attempt_count": 0,
        "http_response_received": False,
        "wordpress_response_read": False,
        "wordpress_write_performed": False,
        "production_payload_modified": False,
        "production_category_id_payload_injected": False,
        "fixture_category_id_used": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_SHOT_READ_ONLY_CATEGORY_LOOKUP_ONLY"
        ),
    }


def build_report(
    result: dict[str, Any],
) -> str:
    mapping = result.get(
        "production_category_mapping_candidate"
    )

    mapping_section = (
        "- Production category candidate: `not recorded`\n"
    )

    if isinstance(mapping, dict):
        mapping_section = (
            f"- Slug: `{mapping['category_slug']}`\n"
            f"- Name: `{mapping['category_name']}`\n"
            f"- Candidate category ID: "
            f"`{mapping['production_category_id_candidate']}`\n"
            f"- Match state: `{mapping['match_state']}`\n"
            "- Human verification required: `true`\n"
            "- Payload injection allowed: `false`\n"
        )

    return f"""# LS-NEW-BATCH-4G-2B One-Shot Actual Category Lookup Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Approval label consumed: `true`
- Approval reuse allowed: `false`
- One-shot lock created: `true`

## Approved HTTP Scope

- Hostname: `hoshido.jp`
- Method: `GET`
- REST path: `/wp-json/wp/v2/categories`
- Maximum requests: `1`
- Maximum attempts: `1`
- Retry allowed: `false`
- Redirect following: `false`
- Proxy use: `false`
- TLS verification required: `true`

## Actual Activity

- Credential file read: `{str(result["credential_file_read"]).lower()}`
- Credential values loaded: `{str(result["credential_values_loaded"]).lower()}`
- Credential values output: `false`
- Authorization header output: `false`
- HTTP request attempts: `{result["http_request_attempt_count"]}`
- HTTP response received: `{str(result["http_response_received"]).lower()}`
- WordPress response read: `{str(result["wordpress_response_read"]).lower()}`
- WordPress write performed: `false`
- Production payload modified: `false`

## Production Category Mapping Candidate

{mapping_section}

## Safety State

- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- Payload modification allowed: `false`
- Execution allowed after this run: `false`
- Production status: `NO_GO`
- Safety state: `ONE_SHOT_READ_ONLY_CATEGORY_LOOKUP_ONLY`
"""


def execute(
    *,
    transport: Callable[..., dict[str, Any]] = real_transport,
    policy_path: Path = POLICY_PATH,
    approval_path: Path = APPROVAL_PATH,
    source_result_path: Path = SOURCE_RESULT_PATH,
    source_package_path: Path = SOURCE_PACKAGE_PATH,
    result_path: Path = RESULT_PATH,
    report_path: Path = REPORT_PATH,
    lock_path_override: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    policy = load_json(policy_path)
    approval = load_json(approval_path)
    source_result = load_json(
        source_result_path
    )
    source_package = load_json(
        source_package_path
    )

    policy_checks = validate_policy(policy)
    source_checks = validate_source(
        policy,
        source_result,
        source_package,
    )
    approval_checks = validate_approval(
        policy,
        approval,
        source_result,
    )

    lock_path = (
        lock_path_override
        if lock_path_override is not None
        else resolve_repo_path(
            policy["one_shot_lock"]["lock_path"]
        )
    )

    reservation = reserve_one_shot(
        lock_path,
        approval=approval,
    )

    result = base_result()
    result.update(
        {
            "status": (
                "BLOCKED_ONE_SHOT_LOOKUP_"
                "NOT_COMPLETED"
            ),
            "decision": (
                "ONE_SHOT_APPROVAL_CONSUMED_"
                "NO_RETRY"
            ),
            "started_at_utc": utc_now(),
            "verified_checks": (
                policy_checks
                + source_checks
                + approval_checks
                + [
                    "one_shot_lock_reserved",
                    "approval_consumed_before_access",
                ]
            ),
        }
    )

    try:
        credentials = read_credentials(
            policy
        )

        result["credential_file_read"] = True
        result["credential_values_loaded"] = True

        origin, hostname = validate_base_url(
            credentials[
                "WORDPRESS_BASE_URL"
            ],
            policy,
        )

        require(
            hostname
            == result["target_hostname"],
            "validated hostname mismatch",
        )

        request_url = construct_request_url(
            origin,
            policy,
        )

        result[
            "authorization_header_constructed"
        ] = True
        result["dns_resolution_attempted"] = True
        result[
            "network_connection_attempted"
        ] = True
        result[
            "tls_connection_attempted"
        ] = True
        result[
            "http_request_attempt_count"
        ] = 1

        response = transport(
            request_url=request_url,
            username=credentials[
                "WORDPRESS_READONLY_USERNAME"
            ],
            password=credentials[
                "WORDPRESS_READONLY_APP_PASSWORD"
            ],
            policy=policy,
        )

        result["http_response_received"] = True
        result["wordpress_response_read"] = True
        result["http_status"] = response[
            "http_status"
        ]
        result["response_bytes"] = response[
            "response_bytes"
        ]
        result["response_content_type"] = (
            response["content_type"].split(
                ";",
                1,
            )[0]
        )

        mapping = validate_response(
            response,
            policy,
        )

        result.update(
            {
                "status": (
                    "PASS_ONE_SHOT_ACTUAL_"
                    "READ_ONLY_CATEGORY_LOOKUP"
                ),
                "decision": (
                    "PRODUCTION_CATEGORY_ID_CANDIDATE_"
                    "RECORDED_HUMAN_VERIFICATION_REQUIRED"
                ),
                "production_category_mapping_candidate": (
                    mapping
                ),
                "production_category_id_received": True,
                "production_category_id_candidate": (
                    mapping[
                        "production_category_id_candidate"
                    ]
                ),
                "human_result_verification_required": True,
                "ready_for_ls_new_batch_4h": True,
                "ready_for_category_mapping_human_verification": True,
                "ready_for_category_mapping_fixation": False,
                "ready_for_payload_injection": False,
                "ready_for_wordpress_draft": False,
                "ready_for_execution": False,
                "next_phase_execution_allowed": False,
                "completed_at_utc": utc_now(),
            }
        )

        result["verified_checks"].extend(
            [
                "credential_file_safely_read",
                "credential_metadata_revalidated",
                "credential_key_set_verified",
                "credential_values_not_output",
                "approved_hostname_verified",
                "https_origin_verified",
                "authorization_header_not_output",
                "proxy_use_disabled",
                "redirect_follow_disabled",
                "single_http_attempt_enforced",
                "tls_verification_enabled",
                "http_status_verified",
                "content_type_verified",
                "response_size_verified",
                "response_json_verified",
                "exact_slug_match_verified",
                "exact_name_match_verified",
                "single_result_verified",
                "positive_category_id_verified",
                "production_mapping_candidate_digest_generated",
                "payload_unmodified",
                "wordpress_write_absent",
                "execution_gate_closed_after_consumption",
            ]
        )

        write_json(
            result_path,
            result,
        )
        write_text(
            report_path,
            build_report(result),
        )

        finalize_lock(
            lock_path,
            reservation,
            final_state=(
                "CONSUMED_COMPLETED_PASS"
            ),
            result_status=result["status"],
            http_request_attempt_count=1,
        )

        credentials.clear()

        return 0, result

    except ControlledBlock as blocked:
        result.update(
            {
                "status": blocked.status,
                "decision": (
                    "ONE_SHOT_ATTEMPT_BLOCKED_"
                    "APPROVAL_CONSUMED_NO_RETRY"
                ),
                "reason": blocked.reason,
                "ready_for_ls_new_batch_4h": False,
                "ready_for_category_mapping_human_verification": False,
                "ready_for_category_mapping_fixation": False,
                "ready_for_payload_injection": False,
                "ready_for_wordpress_draft": False,
                "ready_for_execution": False,
                "next_phase_execution_allowed": False,
                "completed_at_utc": utc_now(),
            }
        )

        for key, value in blocked.telemetry.items():
            result[key] = value

        write_json(
            result_path,
            result,
        )
        write_text(
            report_path,
            build_report(result),
        )

        finalize_lock(
            lock_path,
            reservation,
            final_state=(
                "CONSUMED_COMPLETED_BLOCKED"
            ),
            result_status=result["status"],
            http_request_attempt_count=result[
                "http_request_attempt_count"
            ],
        )

        return 3, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execute-approved-one-shot",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.execute_approved_one_shot:
        result = {
            "phase_id": "LS-NEW-BATCH-4G-2B",
            "status": (
                "BLOCKED_EXECUTION_FLAG_REQUIRED"
            ),
            "execution_allowed": False,
            "production_status": "NO_GO",
        }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 3

    try:
        return_code, result = execute()

        stream = (
            sys.stdout
            if return_code == 0
            else sys.stderr
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=stream,
        )

        return return_code

    except ControlledBlock as blocked:
        result = {
            "phase_id": "LS-NEW-BATCH-4G-2B",
            "status": blocked.status,
            "decision": (
                "EXECUTION_BLOCKED_BEFORE_ACCESS"
            ),
            "reason": blocked.reason,
            "credential_file_read": False,
            "credential_values_output": False,
            "http_request_attempt_count": 0,
            "wordpress_write_performed": False,
            "production_payload_modified": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
        }

        result.update(
            blocked.telemetry
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 3

    except ValidationError as exc:
        result = {
            "phase_id": "LS-NEW-BATCH-4G-2B",
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "credential_file_read": False,
            "credential_values_output": False,
            "http_request_attempt_count": 0,
            "wordpress_write_performed": False,
            "production_payload_modified": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
        }

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
