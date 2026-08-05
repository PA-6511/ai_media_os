#!/usr/bin/env python3

from __future__ import annotations

import base64
import copy
import hashlib
import html
import json
import os
import ssl
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_layout_"
    "post_update_get_verification_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m28_post_update_verify_approval.json"
)

M27_CONSUMPTION = ROOT / (
    "exchange/consumptions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_consumption.json"
)
M27_EXECUTION_SNAPSHOT = ROOT / (
    "exchange/executions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_execution_snapshot.json"
)
M27_EXECUTION_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_execute_result.json"
)
M26_AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_authorization.json"
)
M27_CONFIRMATION = ROOT / (
    "exchange/confirmations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "execute_now_confirmation.json"
)
M24_RENDERED = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.html"
)
M24_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_payload_v1.json"
)
M25_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_human_review_approved.json"
)
M25_REQUIREMENT = ROOT / (
    "exchange/requirements/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_backlist_cover_affiliate_carousel_"
    "future_requirement.json"
)
ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)

CREDENTIAL_ENV = Path(
    "/etc/ai-media-os/credential.env"
)

VERIFICATION = ROOT / (
    "exchange/verifications/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "post_update_get_verification.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m28_post_update_verify_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m28_"
    "post_update_get_verification_report.md"
)

EXPECTED_POST_ID = 192
EXPECTED_STATUS = "publish"
EXPECTED_TITLE = "ダークギャザリング 第20巻｜配信開始"
EXPECTED_CATEGORIES = [10]
EXPECTED_COMMENT_STATUS = "closed"

EXPECTED_CONTENT_SHA = (
    "dc938ae164c70130a5fb27692d71c97c"
    "c367a8985c44c2c333801b337ee6caf4"
)
EXPECTED_CONSUMPTION_DIGEST = (
    "ade807888265e7b1fa1fdc49abb65bf2"
    "deda2d7607530c1a0ad99195f71eac4a"
)
EXPECTED_EXECUTION_SNAPSHOT_DIGEST = (
    "bd08a01aa548cb1da45bbc891e08ef69"
    "26216b28ed43019dd8f5c06dd9367366"
)
EXPECTED_EXECUTION_RESULT_DIGEST = (
    "1d1f123851bd3e1bd8754c896d0cbd4d"
    "a7f0fc71874203e5f6558b67167a1651"
)
EXPECTED_AUTHORIZATION_DIGEST = (
    "d7f53a0eb02a037cde4b6ab71b4b026b"
    "79eb8c2d2c08a95a8bec5f1ad0b6e615"
)
EXPECTED_CONFIRMATION_DIGEST = (
    "74cc04d1d01a5ae81a2367ed098ce17b"
    "a4896db8e1ac713a8014fd2c01cc1c64"
)
EXPECTED_PAYLOAD_DIGEST = (
    "52ed18792454e5806b739059911c8117"
    "810cafcadacf35fb77429b608673cd60"
)
EXPECTED_REVIEW_DIGEST = (
    "7fd7a9f0f5317435160010fac811b77d"
    "876f77919ad2b5905c6cdea82f8f1806"
)
EXPECTED_REQUIREMENT_DIGEST = (
    "bfa2e1b69c1d5cfe3999ac0048539d1d"
    "4b01d60e9ba9d452a8e65176a5d028a4"
)
EXPECTED_ROLLBACK_DIGEST = (
    "60ac4fe5182e412014bcbd291ca52af1"
    "e516e7061722e608b39a34c284dbfcf5"
)
EXPECTED_REQUEST_BODY_DIGEST = (
    "02f5f89d916e328f0b020ebfefafcb39"
    "1e1c4b0a511d4b2277e37fa225fc81e7"
)

MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class ValidationError(RuntimeError):
    pass


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


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


def canonical_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def text_sha(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
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
    expected: str,
) -> None:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        canonical_digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )
    require(
        stored == expected,
        f"DIGEST_EXPECTED_MISMATCH:{field}",
    )


def add_digest(
    value: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = canonical_digest(value)
    return result


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


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )


def load_credential_env(
    path: Path,
) -> dict[str, str]:
    require(
        path.exists() and path.is_file(),
        "CREDENTIAL_ENV_MISSING",
    )
    require(
        not path.is_symlink(),
        "CREDENTIAL_ENV_SYMLINK_REJECTED",
    )

    file_stat = path.stat()

    require(
        stat.S_IMODE(file_stat.st_mode) == 0o600,
        "CREDENTIAL_ENV_MODE_NOT_0600",
    )
    require(
        file_stat.st_uid == os.geteuid(),
        "CREDENTIAL_ENV_OWNER_MISMATCH",
    )

    values: dict[str, str] = {}

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        key, raw_value = line.split(
            "=",
            1,
        )

        key = key.strip()
        value = raw_value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {
                "'",
                '"',
            }
        ):
            value = value[1:-1]

        values[key] = value

    for required_key in [
        "WORDPRESS_BASE_URL",
        "WORDPRESS_USERNAME",
        "WORDPRESS_APP_PASSWORD",
    ]:
        require(
            bool(values.get(required_key)),
            f"CREDENTIAL_KEY_MISSING:{required_key}",
        )

    return values


def safe_exception_type(
    exc: BaseException,
) -> str:
    if isinstance(exc, URLError):
        reason = getattr(
            exc,
            "reason",
            None,
        )

        if reason is not None:
            return type(reason).__name__

    return type(exc).__name__


def build_get_request(
    values: dict[str, str],
) -> Request:
    parsed = urlsplit(
        values["WORDPRESS_BASE_URL"]
    )

    require(
        parsed.scheme == "https",
        "WORDPRESS_BASE_URL_NOT_HTTPS",
    )
    require(
        parsed.hostname == "hoshido.jp",
        "WORDPRESS_HOST_MISMATCH",
    )
    require(
        parsed.port in {
            None,
            443,
        },
        "WORDPRESS_PORT_NOT_443",
    )
    require(
        not parsed.query
        and not parsed.fragment,
        "WORDPRESS_BASE_URL_HAS_QUERY_OR_FRAGMENT",
    )

    base_path = parsed.path.rstrip("/")

    target_url = (
        f"https://hoshido.jp"
        f"{base_path}/wp-json/wp/v2/posts/"
        f"{EXPECTED_POST_ID}"
        "?context=edit"
        "&_fields=id,status,title,categories,"
        "comment_status,content"
    )

    token = base64.b64encode(
        (
            values["WORDPRESS_USERNAME"]
            + ":"
            + values["WORDPRESS_APP_PASSWORD"]
        ).encode("utf-8")
    ).decode("ascii")

    return Request(
        target_url,
        method="GET",
        headers={
            "Authorization": (
                "Basic " + token
            ),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": (
                "ai-media-os-m28-post-update-verify/1.0"
            ),
            "Connection": "close",
        },
    )


def perform_single_get(
    request: Request,
) -> tuple[int, bytes]:
    opener = build_opener(
        ProxyHandler({}),
        NoRedirectHandler(),
        HTTPSHandler(
            context=ssl.create_default_context()
        ),
    )

    try:
        with opener.open(
            request,
            timeout=30,
        ) as response:
            status = int(
                response.getcode()
            )
            body = response.read(
                MAX_RESPONSE_BYTES + 1
            )
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read(
            MAX_RESPONSE_BYTES + 1
        )

    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError(
            "RESPONSE_SIZE_LIMIT_EXCEEDED"
        )

    return status, body


def main() -> int:
    source_paths = {
        "m27_consumption": M27_CONSUMPTION,
        "m27_execution_snapshot": M27_EXECUTION_SNAPSHOT,
        "m27_execution_result": M27_EXECUTION_RESULT,
        "m26_authorization": M26_AUTHORIZATION,
        "execute_now_confirmation": M27_CONFIRMATION,
        "m24_rendered": M24_RENDERED,
        "m24_payload": M24_PAYLOAD,
        "m25_review": M25_REVIEW,
        "m25_requirement": M25_REQUIREMENT,
        "rollback": ROLLBACK,
    }

    for output in [
        VERIFICATION,
        RESULT,
        REPORT,
    ]:
        require(
            not output.exists(),
            f"OUTPUT_ALREADY_EXISTS:{output.name}",
        )

    policy = load_json(POLICY)
    approval = load_json(APPROVAL)

    approval_copy = copy.deepcopy(
        approval
    )
    approval_digest = approval_copy.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        canonical_digest(approval_copy)
        == approval_digest,
        "APPROVAL_DIGEST_MISMATCH",
    )
    require(
        policy["phase_id"]
        == (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M28-POST-UPDATE-VERIFY"
        ),
        "POLICY_PHASE_MISMATCH",
    )
    require(
        approval["approval_label"]
        == (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "POST_UPDATE_GET_VERIFICATION_APPROVED"
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
        "MAXIMUM_GET_COUNT_NOT_ONE",
    )
    require(
        approval[
            "non_get_request_approved"
        ] is False,
        "NON_GET_REQUEST_APPROVED",
    )
    require(
        approval[
            "automatic_retry_approved"
        ] is False,
        "AUTOMATIC_RETRY_APPROVED",
    )
    require(
        approval[
            "second_post_approved"
        ] is False,
        "SECOND_POST_APPROVED",
    )

    source_hashes_before = {
        name: file_sha(path)
        for name, path
        in source_paths.items()
    }

    for name, path in source_paths.items():
        binding = approval[
            "source_bindings"
        ][name]

        require(
            binding["path"]
            == str(path.relative_to(ROOT)),
            f"SOURCE_PATH_MISMATCH:{name}",
        )
        require(
            binding["file_sha256"]
            == source_hashes_before[name],
            f"SOURCE_SHA_MISMATCH:{name}",
        )

    consumption = load_json(
        M27_CONSUMPTION
    )
    execution_snapshot = load_json(
        M27_EXECUTION_SNAPSHOT
    )
    execution_result = load_json(
        M27_EXECUTION_RESULT
    )
    authorization = load_json(
        M26_AUTHORIZATION
    )
    confirmation = load_json(
        M27_CONFIRMATION
    )
    payload = load_json(
        M24_PAYLOAD
    )
    review = load_json(
        M25_REVIEW
    )
    requirement = load_json(
        M25_REQUIREMENT
    )
    rollback = load_json(
        ROLLBACK
    )

    verify_digest(
        consumption,
        "consumption_digest_sha256",
        EXPECTED_CONSUMPTION_DIGEST,
    )
    verify_digest(
        execution_snapshot,
        "snapshot_digest_sha256",
        EXPECTED_EXECUTION_SNAPSHOT_DIGEST,
    )
    verify_digest(
        execution_result,
        "result_digest_sha256",
        EXPECTED_EXECUTION_RESULT_DIGEST,
    )
    verify_digest(
        authorization,
        "authorization_digest_sha256",
        EXPECTED_AUTHORIZATION_DIGEST,
    )
    verify_digest(
        confirmation,
        "confirmation_digest_sha256",
        EXPECTED_CONFIRMATION_DIGEST,
    )
    verify_digest(
        payload,
        "update_payload_digest_sha256",
        EXPECTED_PAYLOAD_DIGEST,
    )
    verify_digest(
        review,
        "human_review_evidence_digest_sha256",
        EXPECTED_REVIEW_DIGEST,
    )
    verify_digest(
        requirement,
        "future_requirement_digest_sha256",
        EXPECTED_REQUIREMENT_DIGEST,
    )
    verify_digest(
        rollback,
        "rollback_evidence_digest_sha256",
        EXPECTED_ROLLBACK_DIGEST,
    )

    require(
        file_sha(M24_RENDERED)
        == EXPECTED_CONTENT_SHA,
        "M24_RENDERED_SHA_MISMATCH",
    )

    require(
        consumption[
            "authorization_consumed"
        ] is True,
        "AUTHORIZATION_NOT_CONSUMED",
    )
    require(
        consumption[
            "confirmation_consumed"
        ] is True,
        "CONFIRMATION_NOT_CONSUMED",
    )
    require(
        consumption[
            "authorization_consumption_count"
        ] == 1,
        "AUTHORIZATION_CONSUMPTION_COUNT_NOT_ONE",
    )
    require(
        consumption[
            "confirmation_consumption_count"
        ] == 1,
        "CONFIRMATION_CONSUMPTION_COUNT_NOT_ONE",
    )
    require(
        consumption[
            "authorization_reuse_allowed"
        ] is False,
        "AUTHORIZATION_REUSE_ALLOWED",
    )
    require(
        consumption[
            "automatic_retry_allowed"
        ] is False,
        "AUTOMATIC_RETRY_ALLOWED",
    )
    require(
        consumption[
            "second_post_allowed"
        ] is False,
        "SECOND_POST_ALLOWED",
    )

    require(
        execution_result[
            "outcome"
        ] == (
            "VALIDATED_HTTP_200_UPDATE_RESPONSE"
        ),
        "M27_EXECUTION_OUTCOME_NOT_VALIDATED",
    )
    require(
        execution_result[
            "response_validated"
        ] is True,
        "M27_RESPONSE_NOT_VALIDATED",
    )
    require(
        execution_result[
            "http_status_code"
        ] == 200,
        "M27_HTTP_STATUS_NOT_200",
    )
    require(
        execution_result[
            "post_request_count"
        ] == 1,
        "M27_POST_COUNT_NOT_ONE",
    )
    require(
        execution_result[
            "automatic_retry_count"
        ] == 0,
        "M27_AUTOMATIC_RETRY_OCCURRED",
    )
    require(
        execution_result[
            "second_post_performed"
        ] is False,
        "M27_SECOND_POST_PERFORMED",
    )
    require(
        execution_result[
            "wordpress_update_performed"
        ] is True,
        "M27_UPDATE_NOT_PERFORMED",
    )
    require(
        execution_result[
            "authorization_consumed"
        ] is True,
        "M27_AUTHORIZATION_NOT_CONSUMED",
    )
    require(
        execution_result[
            "confirmation_consumed"
        ] is True,
        "M27_CONFIRMATION_NOT_CONSUMED",
    )
    require(
        execution_result[
            "ready_for_retry"
        ] is False,
        "M27_RETRY_GATE_OPEN",
    )
    require(
        execution_result[
            "ready_for_second_post"
        ] is False,
        "M27_SECOND_POST_GATE_OPEN",
    )

    for field in [
        "response_post_id_matches",
        "response_status_is_publish",
        "response_title_matches",
        "response_categories_match",
        "response_comment_status_is_closed",
        "response_content_matches_m24",
    ]:
        require(
            execution_result[field]
            is True,
            f"M27_RESPONSE_CHECK_FALSE:{field}",
        )

    require(
        execution_snapshot[
            "response_content_sha256"
        ] == EXPECTED_CONTENT_SHA,
        "M27_SNAPSHOT_CONTENT_SHA_MISMATCH",
    )
    require(
        execution_snapshot[
            "response_comment_status"
        ] == EXPECTED_COMMENT_STATUS,
        "M27_SNAPSHOT_COMMENT_STATUS_MISMATCH",
    )

    require(
        authorization[
            "wordpress_post_id"
        ] == EXPECTED_POST_ID,
        "AUTHORIZATION_POST_ID_MISMATCH",
    )
    require(
        authorization[
            "single_use"
        ] is True,
        "AUTHORIZATION_NOT_SINGLE_USE",
    )
    require(
        authorization[
            "maximum_update_count"
        ] == 1,
        "AUTHORIZATION_MAXIMUM_UPDATE_NOT_ONE",
    )
    require(
        authorization[
            "reuse_allowed"
        ] is False,
        "AUTHORIZATION_REUSE_ALLOWED_ORIGINAL",
    )
    require(
        authorization[
            "automatic_retry_allowed"
        ] is False,
        "AUTHORIZATION_RETRY_ALLOWED_ORIGINAL",
    )

    require(
        confirmation[
            "execute_now_confirmation_recorded"
        ] is True,
        "EXECUTE_NOW_CONFIRMATION_NOT_RECORDED",
    )
    require(
        confirmation[
            "single_use"
        ] is True,
        "CONFIRMATION_NOT_SINGLE_USE",
    )
    require(
        confirmation[
            "maximum_update_count"
        ] == 1,
        "CONFIRMATION_MAXIMUM_UPDATE_NOT_ONE",
    )

    rendered_html = M24_RENDERED.read_text(
        encoding="utf-8"
    )
    request_body = payload.get(
        "wordpress_request_body"
    )

    require(
        isinstance(request_body, dict),
        "REQUEST_BODY_NOT_OBJECT",
    )
    require(
        set(request_body.keys())
        == {
            "content",
            "comment_status",
        },
        "REQUEST_FIELD_SET_MISMATCH",
    )
    require(
        request_body["content"]
        == rendered_html,
        "REQUEST_CONTENT_MISMATCH",
    )
    require(
        request_body[
            "comment_status"
        ] == EXPECTED_COMMENT_STATUS,
        "REQUEST_COMMENT_STATUS_NOT_CLOSED",
    )
    require(
        canonical_digest(request_body)
        == EXPECTED_REQUEST_BODY_DIGEST,
        "REQUEST_BODY_DIGEST_MISMATCH",
    )

    require(
        review[
            "human_review_verdict"
        ] == "APPROVED_NO_CHANGE_REQUIRED",
        "HUMAN_REVIEW_NOT_APPROVED",
    )
    require(
        requirement[
            "implementation_authorized"
        ] is False,
        "BACKLIST_IMPLEMENTATION_AUTHORIZED",
    )
    require(
        requirement[
            "included_in_current_wordpress_update"
        ] is False,
        "BACKLIST_INCLUDED_IN_CURRENT_UPDATE",
    )

    credentials = load_credential_env(
        CREDENTIAL_ENV
    )
    request = build_get_request(
        credentials
    )

    get_request_count = 1
    non_get_request_count = 0
    automatic_retry_count = 0
    redirect_followed = False

    get_transport_attempted = True
    http_response_received = False
    wordpress_access_performed = False

    http_status_code: int | None = None
    response_size_bytes: int | None = None
    safe_error_type: str | None = None

    observed_post_id: int | None = None
    observed_status: str | None = None
    observed_title: str | None = None
    observed_title_source: str | None = None
    observed_categories: list[int] | None = None
    observed_comment_status: str | None = None
    observed_content_sha256: str | None = None
    observed_content_length: int | None = None

    verification_checks = {
        "http_status_200": False,
        "response_json_object": False,
        "post_id_matches": False,
        "status_is_publish": False,
        "title_matches": False,
        "categories_match": False,
        "comment_status_is_closed": False,
        "content_raw_observed": False,
        "content_matches_m24": False,
    }

    failure_codes: list[str] = []

    try:
        (
            http_status_code,
            response_bytes,
        ) = perform_single_get(
            request
        )

        http_response_received = True
        wordpress_access_performed = True
        response_size_bytes = len(
            response_bytes
        )

        verification_checks[
            "http_status_200"
        ] = http_status_code == 200

        if not verification_checks[
            "http_status_200"
        ]:
            failure_codes.append(
                "HTTP_STATUS_NOT_200"
            )
        else:
            try:
                response_json = json.loads(
                    response_bytes.decode(
                        "utf-8"
                    )
                )
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                response_json = None
                failure_codes.append(
                    "RESPONSE_JSON_PARSE_FAILED"
                )

            verification_checks[
                "response_json_object"
            ] = isinstance(
                response_json,
                dict,
            )

            if isinstance(
                response_json,
                dict,
            ):
                observed_post_id = (
                    response_json.get("id")
                )
                observed_status = (
                    response_json.get(
                        "status"
                    )
                )

                title_object = (
                    response_json.get(
                        "title"
                    )
                )
                categories_object = (
                    response_json.get(
                        "categories"
                    )
                )
                content_object = (
                    response_json.get(
                        "content"
                    )
                )

                if isinstance(
                    title_object,
                    dict,
                ):
                    raw_title = title_object.get(
                        "raw"
                    )
                    rendered_title = (
                        title_object.get(
                            "rendered"
                        )
                    )

                    if isinstance(
                        raw_title,
                        str,
                    ):
                        observed_title = raw_title
                        observed_title_source = (
                            "raw"
                        )
                    elif isinstance(
                        rendered_title,
                        str,
                    ):
                        observed_title = (
                            html.unescape(
                                rendered_title
                            )
                        )
                        observed_title_source = (
                            "rendered"
                        )

                if isinstance(
                    categories_object,
                    list,
                ) and all(
                    isinstance(item, int)
                    for item
                    in categories_object
                ):
                    observed_categories = (
                        categories_object
                    )

                comment_status = (
                    response_json.get(
                        "comment_status"
                    )
                )

                if isinstance(
                    comment_status,
                    str,
                ):
                    observed_comment_status = (
                        comment_status
                    )

                if isinstance(
                    content_object,
                    dict,
                ):
                    raw_content = (
                        content_object.get(
                            "raw"
                        )
                    )

                    if isinstance(
                        raw_content,
                        str,
                    ):
                        observed_content_sha256 = (
                            text_sha(
                                raw_content
                            )
                        )
                        observed_content_length = (
                            len(raw_content)
                        )
                        verification_checks[
                            "content_raw_observed"
                        ] = True

                verification_checks[
                    "post_id_matches"
                ] = (
                    observed_post_id
                    == EXPECTED_POST_ID
                )
                verification_checks[
                    "status_is_publish"
                ] = (
                    observed_status
                    == EXPECTED_STATUS
                )
                verification_checks[
                    "title_matches"
                ] = (
                    observed_title
                    == EXPECTED_TITLE
                )
                verification_checks[
                    "categories_match"
                ] = (
                    observed_categories
                    is not None
                    and sorted(
                        observed_categories
                    )
                    == EXPECTED_CATEGORIES
                )
                verification_checks[
                    "comment_status_is_closed"
                ] = (
                    observed_comment_status
                    == EXPECTED_COMMENT_STATUS
                )
                verification_checks[
                    "content_matches_m24"
                ] = (
                    observed_content_sha256
                    == EXPECTED_CONTENT_SHA
                )

                for check_name, code in [
                    (
                        "post_id_matches",
                        "FINAL_POST_ID_MISMATCH",
                    ),
                    (
                        "status_is_publish",
                        "FINAL_STATUS_NOT_PUBLISH",
                    ),
                    (
                        "title_matches",
                        "FINAL_TITLE_MISMATCH",
                    ),
                    (
                        "categories_match",
                        "FINAL_CATEGORIES_MISMATCH",
                    ),
                    (
                        "comment_status_is_closed",
                        "FINAL_COMMENT_STATUS_NOT_CLOSED",
                    ),
                    (
                        "content_raw_observed",
                        "FINAL_CONTENT_RAW_MISSING",
                    ),
                    (
                        "content_matches_m24",
                        "FINAL_CONTENT_M24_MISMATCH",
                    ),
                ]:
                    if not verification_checks[
                        check_name
                    ]:
                        failure_codes.append(
                            code
                        )
            else:
                failure_codes.append(
                    "RESPONSE_ROOT_NOT_OBJECT"
                )

    except Exception as exc:
        safe_error_type = (
            safe_exception_type(exc)
        )
        failure_codes.append(
            "POST_UPDATE_GET_RESPONSE_UNKNOWN"
        )

    source_hashes_after = {
        name: file_sha(path)
        for name, path
        in source_paths.items()
    }

    source_artifacts_modified = (
        source_hashes_before
        != source_hashes_after
    )

    if source_artifacts_modified:
        failure_codes.append(
            "SOURCE_ARTIFACT_MODIFIED"
        )

    final_state_verified = (
        http_response_received
        and http_status_code == 200
        and all(
            verification_checks.values()
        )
        and not failure_codes
        and get_request_count == 1
        and non_get_request_count == 0
        and automatic_retry_count == 0
        and redirect_followed is False
        and not source_artifacts_modified
    )

    verification_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M28-POST-UPDATE-VERIFY"
        ),
        "document_role": (
            "WORDPRESS_POST_UPDATE_AUTHENTICATED_GET_"
            "FINAL_STATE_VERIFICATION"
        ),
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "request_method": "GET",
        "get_request_count": (
            get_request_count
        ),
        "non_get_request_count": (
            non_get_request_count
        ),
        "automatic_retry_count": (
            automatic_retry_count
        ),
        "redirect_followed": (
            redirect_followed
        ),
        "get_transport_attempted": (
            get_transport_attempted
        ),
        "http_response_received": (
            http_response_received
        ),
        "wordpress_access_performed": (
            wordpress_access_performed
        ),
        "http_status_code": (
            http_status_code
        ),
        "response_size_bytes": (
            response_size_bytes
        ),
        "safe_error_type": (
            safe_error_type
        ),
        "observed_post_id": (
            observed_post_id
        ),
        "observed_status": (
            observed_status
        ),
        "observed_title": (
            observed_title
        ),
        "observed_title_source": (
            observed_title_source
        ),
        "observed_category_ids": (
            observed_categories
        ),
        "observed_comment_status": (
            observed_comment_status
        ),
        "observed_content_sha256": (
            observed_content_sha256
        ),
        "observed_content_length": (
            observed_content_length
        ),
        "expected_content_sha256": (
            EXPECTED_CONTENT_SHA
        ),
        "verification_checks": (
            verification_checks
        ),
        "failure_codes": sorted(
            set(failure_codes)
        ),
        "authorization_consumed": True,
        "confirmation_consumed": True,
        "authorization_consumption_count": 1,
        "confirmation_consumption_count": 1,
        "authorization_reused": False,
        "automatic_reissue_performed": False,
        "second_post_performed": False,
        "backlist_carousel_included": False,
        "source_artifacts_modified": (
            source_artifacts_modified
        ),
        "credential_value_stored": False,
        "username_stored": False,
        "full_url_stored": False,
        "authorization_header_stored": False,
        "wordpress_content_stored": False,
        "affiliate_identifier_stored": False,
        "wordpress_write_performed": False,
        "wordpress_update_performed": False,
        "wordpress_republish_performed": False,
        "wordpress_delete_performed": False,
        "x_post_performed": False,
        "final_state_verified": (
            final_state_verified
        ),
        "verified_at_utc": now()
    }

    verification = add_digest(
        verification_without_digest,
        "verification_digest_sha256",
    )
    write_json(
        VERIFICATION,
        verification,
    )

    if final_state_verified:
        status = (
            "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "POST_UPDATE_GET_VERIFICATION_FINAL_STATE_MATCHED_"
            "NO_WRITE"
        )
        decision = (
            "FINAL_WORDPRESS_STATE_MATCHED_ONE_SHOT_UPDATE_"
            "COMPLETE_AUTHORIZATION_CONSUMED_NO_RETRY"
        )
    else:
        status = (
            "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "POST_UPDATE_GET_VERIFICATION_NOT_CONFIRMED_"
            "NO_WRITE_NO_RETRY"
        )
        decision = (
            "FINAL_STATE_NOT_CONFIRMED_MANUAL_REVIEW_REQUIRED_"
            "AUTHORIZATION_REMAINS_CONSUMED"
        )

    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M28-POST-UPDATE-VERIFY"
        ),
        "status": status,
        "decision": decision,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "verification_path": str(
            VERIFICATION.relative_to(ROOT)
        ),
        "verification_digest_sha256": (
            verification[
                "verification_digest_sha256"
            ]
        ),
        "final_state_verified": (
            final_state_verified
        ),
        "request_method": "GET",
        "get_request_count": 1,
        "non_get_request_count": 0,
        "automatic_retry_count": 0,
        "redirect_followed": False,
        "http_response_received": (
            http_response_received
        ),
        "http_status_code": (
            http_status_code
        ),
        "safe_error_type": (
            safe_error_type
        ),
        "failure_codes": sorted(
            set(failure_codes)
        ),
        "final_post_id_matches": (
            verification_checks[
                "post_id_matches"
            ]
        ),
        "final_status_is_publish": (
            verification_checks[
                "status_is_publish"
            ]
        ),
        "final_title_matches": (
            verification_checks[
                "title_matches"
            ]
        ),
        "final_categories_match": (
            verification_checks[
                "categories_match"
            ]
        ),
        "final_comment_status_is_closed": (
            verification_checks[
                "comment_status_is_closed"
            ]
        ),
        "final_content_matches_m24": (
            verification_checks[
                "content_matches_m24"
            ]
        ),
        "observed_comment_status": (
            observed_comment_status
        ),
        "observed_content_sha256": (
            observed_content_sha256
        ),
        "authorization_consumed": True,
        "confirmation_consumed": True,
        "authorization_consumption_count": 1,
        "confirmation_consumption_count": 1,
        "authorization_reused": False,
        "automatic_retry_performed": False,
        "automatic_reissue_performed": False,
        "second_post_performed": False,
        "backlist_carousel_included": False,
        "source_artifacts_modified": (
            source_artifacts_modified
        ),
        "wordpress_access_performed": (
            wordpress_access_performed
        ),
        "wordpress_write_performed": False,
        "wordpress_update_performed": False,
        "wordpress_republish_performed": False,
        "wordpress_delete_performed": False,
        "x_post_performed": False,
        "production_status": "NO_GO",
        "required_next_phase": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M29-POST-UPDATE-FINALIZE"
        ),
        "ready_for_local_finalization": (
            final_state_verified
        ),
        "ready_for_retry": False,
        "ready_for_second_post": False,
        "ready_for_wordpress_publish": False,
        "completed_at_utc": now()
    }

    result = add_digest(
        result_without_digest,
        "result_digest_sha256",
    )
    write_json(
        RESULT,
        result,
    )

    write_text(
        REPORT,
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M28-POST-UPDATE-VERIFY

- Status: `{status}`
- Decision: `{decision}`
- WordPress post ID: `192`
- Final state verified: `{str(final_state_verified).lower()}`
- GET request count: `1`
- Non-GET request count: `0`
- Automatic retry count: `0`
- Redirect followed: `false`
- HTTP response received: `{str(http_response_received).lower()}`
- HTTP status: `{http_status_code}`
- Final post ID matches: `{str(verification_checks["post_id_matches"]).lower()}`
- Final status is publish: `{str(verification_checks["status_is_publish"]).lower()}`
- Final title matches: `{str(verification_checks["title_matches"]).lower()}`
- Final categories match: `{str(verification_checks["categories_match"]).lower()}`
- Final comment status is closed: `{str(verification_checks["comment_status_is_closed"]).lower()}`
- Final content matches M24: `{str(verification_checks["content_matches_m24"]).lower()}`
- Authorization consumed: `true`
- Confirmation consumed: `true`
- Second POST performed: `false`
- WordPress write performed in M28: `false`
- Backlist carousel included: `false`
- Production status: `NO_GO`
- Ready for local finalization: `{str(final_state_verified).lower()}`
- Ready for retry: `false`
""",
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-"
                        "M28-POST-UPDATE-VERIFY"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_POST_UPDATE_GET_"
                        "NO_WORDPRESS_ACCESS_NO_WRITE"
                    ),
                    "safe_error_code": str(exc),
                    "get_request_count": 0,
                    "wordpress_write_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_consumed": True,
                    "ready_for_retry": False,
                    "ready_for_second_post": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
