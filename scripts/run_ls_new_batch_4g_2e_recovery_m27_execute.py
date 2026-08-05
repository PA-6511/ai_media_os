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
    "new_release_wp_tawawa_reference_layout_update_"
    "one_shot_execution_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m27_execute_approval.json"
)

M27_CONFIRMATION = ROOT / (
    "exchange/confirmations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "execute_now_confirmation.json"
)
M27_CONFIRMATION_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_"
    "execute_now_confirmation_result.json"
)
M27_RETRY_SNAPSHOT = ROOT / (
    "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_revised_single_get_retry_snapshot.json"
)
M27_RETRY_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m27_fix1_retry_approval_result.json"
)
M26_AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_one_shot_authorization.json"
)
M24_RENDERED = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.html"
)
M24_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_payload_v1.json"
)
M25_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "human_review_approved.json"
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
    "wordpress_layout_correction_current_content_"
    "rollback_fix2.json"
)

CREDENTIAL_ENV = Path(
    "/etc/ai-media-os/credential.env"
)

CONSUMPTION = ROOT / (
    "exchange/consumptions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_consumption.json"
)
SNAPSHOT = ROOT / (
    "exchange/executions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_execution_snapshot.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_execute_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m27_execute_"
    "one_shot_wordpress_update_report.md"
)

EXPECTED_POST_ID = 192
EXPECTED_STATUS = "publish"
EXPECTED_TITLE = "ダークギャザリング 第20巻｜配信開始"
EXPECTED_CATEGORIES = [10]

EXPECTED_PRE_CONTENT_SHA = (
    "c5851f15e4eb477038dca512c8990068"
    "736a306cf4fb8c207036a3186119f436"
)
EXPECTED_POST_CONTENT_SHA = (
    "dc938ae164c70130a5fb27692d71c97c"
    "c367a8985c44c2c333801b337ee6caf4"
)
EXPECTED_CONFIRMATION_DIGEST = (
    "74cc04d1d01a5ae81a2367ed098ce17b"
    "a4896db8e1ac713a8014fd2c01cc1c64"
)
EXPECTED_CONFIRMATION_RESULT_DIGEST = (
    "dd7705f008508846c627b5114c2d35d2"
    "389a63acadfc1bac748f4ee7e0ef02ce"
)
EXPECTED_PREFLIGHT_SNAPSHOT_DIGEST = (
    "2a86005667e2dbbb3a93fadb72ed60ae"
    "1840de625e2ad6b55dad30671134a384"
)
EXPECTED_PREFLIGHT_RESULT_DIGEST = (
    "a127d49abcdeb6784e1602cb339a0e1d"
    "ebb7268675183ad03a8c49c20f611ab4"
)
EXPECTED_AUTHORIZATION_DIGEST = (
    "d7f53a0eb02a037cde4b6ab71b4b026b"
    "79eb8c2d2c08a95a8bec5f1ad0b6e615"
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


def perform_single_post(
    values: dict[str, str],
    request_body: dict[str, Any],
) -> tuple[int, bytes]:
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

    request_bytes = json.dumps(
        request_body,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    request = Request(
        target_url,
        data=request_bytes,
        method="POST",
        headers={
            "Authorization": (
                "Basic " + token
            ),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Content-Type": (
                "application/json; charset=utf-8"
            ),
            "User-Agent": (
                "ai-media-os-m27-one-shot-update/1.0"
            ),
            "Connection": "close",
        },
    )

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
        "execute_now_confirmation": (
            M27_CONFIRMATION
        ),
        "execute_now_result": (
            M27_CONFIRMATION_RESULT
        ),
        "preflight_snapshot": (
            M27_RETRY_SNAPSHOT
        ),
        "preflight_result": (
            M27_RETRY_RESULT
        ),
        "authorization": (
            M26_AUTHORIZATION
        ),
        "rendered": M24_RENDERED,
        "payload": M24_PAYLOAD,
        "human_review": M25_REVIEW,
        "backlist_requirement": (
            M25_REQUIREMENT
        ),
        "rollback": ROLLBACK,
    }

    for output in [
        CONSUMPTION,
        SNAPSHOT,
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
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE",
        "POLICY_PHASE_MISMATCH",
    )
    require(
        approval["approval_label"]
        == (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_ONE_SHOT_EXECUTION_APPROVED"
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
            "maximum_post_request_count"
        ] == 1,
        "MAXIMUM_POST_COUNT_NOT_ONE",
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

    confirmation = load_json(
        M27_CONFIRMATION
    )
    confirmation_result = load_json(
        M27_CONFIRMATION_RESULT
    )
    preflight_snapshot = load_json(
        M27_RETRY_SNAPSHOT
    )
    preflight_result = load_json(
        M27_RETRY_RESULT
    )
    authorization = load_json(
        M26_AUTHORIZATION
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
        confirmation,
        "confirmation_digest_sha256",
        EXPECTED_CONFIRMATION_DIGEST,
    )
    verify_digest(
        confirmation_result,
        "result_digest_sha256",
        EXPECTED_CONFIRMATION_RESULT_DIGEST,
    )
    verify_digest(
        preflight_snapshot,
        "snapshot_digest_sha256",
        EXPECTED_PREFLIGHT_SNAPSHOT_DIGEST,
    )
    verify_digest(
        preflight_result,
        "result_digest_sha256",
        EXPECTED_PREFLIGHT_RESULT_DIGEST,
    )
    verify_digest(
        authorization,
        "authorization_digest_sha256",
        EXPECTED_AUTHORIZATION_DIGEST,
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
        == EXPECTED_POST_CONTENT_SHA,
        "M24_RENDERED_SHA_MISMATCH",
    )

    require(
        confirmation[
            "execute_now_confirmation_recorded"
        ] is True,
        "EXECUTE_NOW_CONFIRMATION_NOT_RECORDED",
    )
    require(
        confirmation[
            "confirmation_consumed"
        ] is False,
        "CONFIRMATION_ALREADY_CONSUMED",
    )
    require(
        confirmation[
            "confirmed_future_execution_phase"
        ] == (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M27-EXECUTE"
        ),
        "CONFIRMED_EXECUTION_PHASE_MISMATCH",
    )
    require(
        confirmation_result[
            "ready_for_separate_one_shot_update_execution_approval"
        ] is True,
        "EXECUTION_APPROVAL_GATE_NOT_READY",
    )

    require(
        preflight_result[
            "preflight_passed"
        ] is True,
        "PREFLIGHT_NOT_PASSED",
    )
    require(
        preflight_result[
            "http_status_code"
        ] == 200,
        "PREFLIGHT_HTTP_NOT_200",
    )

    for check_field in [
        "current_post_id_matches",
        "current_status_is_publish",
        "current_title_matches",
        "current_categories_match",
        "current_content_matches_rollback",
        "update_content_matches_m24",
        "request_body_digest_matches",
    ]:
        require(
            preflight_result[
                check_field
            ] is True,
            f"PREFLIGHT_CHECK_FALSE:{check_field}",
        )

    require(
        preflight_result[
            "current_comment_status"
        ] == "open",
        "PREFLIGHT_COMMENT_STATUS_NOT_OPEN",
    )

    require(
        authorization[
            "wordpress_post_id"
        ] == EXPECTED_POST_ID,
        "AUTHORIZATION_POST_ID_MISMATCH",
    )
    require(
        authorization[
            "authorization_consumed"
        ] is False,
        "AUTHORIZATION_ALREADY_CONSUMED",
    )
    require(
        authorization[
            "consumption_count"
        ] == 0,
        "AUTHORIZATION_CONSUMPTION_NOT_ZERO",
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
        "MAXIMUM_UPDATE_COUNT_NOT_ONE",
    )
    require(
        authorization[
            "reuse_allowed"
        ] is False,
        "AUTHORIZATION_REUSE_ALLOWED",
    )
    require(
        authorization[
            "automatic_retry_allowed"
        ] is False,
        "AUTHORIZATION_AUTOMATIC_RETRY_ALLOWED",
    )
    require(
        authorization[
            "automatic_reissue_allowed"
        ] is False,
        "AUTHORIZATION_AUTOMATIC_REISSUE_ALLOWED",
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
        ] == "closed",
        "REQUEST_COMMENT_STATUS_NOT_CLOSED",
    )
    require(
        canonical_digest(request_body)
        == EXPECTED_REQUEST_BODY_DIGEST,
        "REQUEST_BODY_DIGEST_MISMATCH",
    )

    for forbidden_field in [
        "title",
        "status",
        "categories",
        "slug",
        "excerpt",
        "featured_media",
    ]:
        require(
            forbidden_field
            not in request_body,
            f"FORBIDDEN_FIELD_PRESENT:{forbidden_field}",
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

    consumption_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M27-EXECUTE"
        ),
        "document_role": (
            "IMMUTABLE_ONE_SHOT_AUTHORIZATION_"
            "AND_CONFIRMATION_CONSUMPTION_EVIDENCE"
        ),
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "authorization_id": (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_ONE_SHOT_AUTHORIZATION_V1"
        ),
        "bound_authorization_digest_sha256": (
            EXPECTED_AUTHORIZATION_DIGEST
        ),
        "bound_confirmation_digest_sha256": (
            EXPECTED_CONFIRMATION_DIGEST
        ),
        "bound_request_body_digest_sha256": (
            EXPECTED_REQUEST_BODY_DIGEST
        ),
        "bound_rendered_content_sha256": (
            EXPECTED_POST_CONTENT_SHA
        ),
        "authorization_consumed": True,
        "confirmation_consumed": True,
        "authorization_consumption_count": 1,
        "confirmation_consumption_count": 1,
        "maximum_post_request_count": 1,
        "post_transport_call_reserved": True,
        "consumed_immediately_before_transport_call": True,
        "authorization_reuse_allowed": False,
        "automatic_retry_allowed": False,
        "automatic_reissue_allowed": False,
        "second_post_allowed": False,
        "original_authorization_file_modified": False,
        "original_confirmation_file_modified": False,
        "credential_value_stored": False,
        "username_stored": False,
        "full_url_stored": False,
        "authorization_header_stored": False,
        "wordpress_content_stored": False,
        "affiliate_identifier_stored": False,
        "consumed_at_utc": now()
    }

    consumption = add_digest(
        consumption_without_digest,
        "consumption_digest_sha256",
    )

    write_json(
        CONSUMPTION,
        consumption,
    )

    require(
        stat.S_IMODE(
            CONSUMPTION.stat().st_mode
        ) == 0o600,
        "CONSUMPTION_MODE_NOT_0600",
    )

    post_request_count = 1
    non_post_request_count = 0
    automatic_retry_count = 0
    redirect_followed = False

    post_transport_call_attempted = True
    http_response_received = False
    wordpress_access_performed = False

    http_status_code: int | None = None
    response_size_bytes: int | None = None
    safe_error_type: str | None = None

    response_json_object = False
    response_post_id: int | None = None
    response_status: str | None = None
    response_title: str | None = None
    response_title_source: str | None = None
    response_categories: list[int] | None = None
    response_comment_status: str | None = None
    response_content_sha256: str | None = None
    response_content_length: int | None = None

    response_checks = {
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
        ) = perform_single_post(
            credentials,
            request_body,
        )

        http_response_received = True
        wordpress_access_performed = True
        response_size_bytes = len(
            response_bytes
        )

        response_checks[
            "http_status_200"
        ] = http_status_code == 200

        if not response_checks[
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

            response_json_object = isinstance(
                response_json,
                dict,
            )
            response_checks[
                "response_json_object"
            ] = response_json_object

            if isinstance(
                response_json,
                dict,
            ):
                response_post_id = (
                    response_json.get("id")
                )
                response_status = (
                    response_json.get(
                        "status"
                    )
                )

                title_object = (
                    response_json.get(
                        "title"
                    )
                )
                category_object = (
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
                        response_title = raw_title
                        response_title_source = (
                            "raw"
                        )
                    elif isinstance(
                        rendered_title,
                        str,
                    ):
                        response_title = (
                            html.unescape(
                                rendered_title
                            )
                        )
                        response_title_source = (
                            "rendered"
                        )

                if isinstance(
                    category_object,
                    list,
                ) and all(
                    isinstance(item, int)
                    for item
                    in category_object
                ):
                    response_categories = (
                        category_object
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
                    response_comment_status = (
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
                        response_content_sha256 = (
                            text_sha(
                                raw_content
                            )
                        )
                        response_content_length = (
                            len(raw_content)
                        )
                        response_checks[
                            "content_raw_observed"
                        ] = True

                response_checks[
                    "post_id_matches"
                ] = (
                    response_post_id
                    == EXPECTED_POST_ID
                )
                response_checks[
                    "status_is_publish"
                ] = (
                    response_status
                    == EXPECTED_STATUS
                )
                response_checks[
                    "title_matches"
                ] = (
                    response_title
                    == EXPECTED_TITLE
                )
                response_checks[
                    "categories_match"
                ] = (
                    response_categories
                    is not None
                    and sorted(
                        response_categories
                    )
                    == EXPECTED_CATEGORIES
                )
                response_checks[
                    "comment_status_is_closed"
                ] = (
                    response_comment_status
                    == "closed"
                )
                response_checks[
                    "content_matches_m24"
                ] = (
                    response_content_sha256
                    == EXPECTED_POST_CONTENT_SHA
                )

                for name, code in [
                    (
                        "post_id_matches",
                        "RESPONSE_POST_ID_MISMATCH",
                    ),
                    (
                        "status_is_publish",
                        "RESPONSE_STATUS_NOT_PUBLISH",
                    ),
                    (
                        "title_matches",
                        "RESPONSE_TITLE_MISMATCH",
                    ),
                    (
                        "categories_match",
                        "RESPONSE_CATEGORIES_MISMATCH",
                    ),
                    (
                        "comment_status_is_closed",
                        "RESPONSE_COMMENT_STATUS_NOT_CLOSED",
                    ),
                    (
                        "content_raw_observed",
                        "RESPONSE_CONTENT_RAW_MISSING",
                    ),
                    (
                        "content_matches_m24",
                        "RESPONSE_CONTENT_M24_MISMATCH",
                    ),
                ]:
                    if not response_checks[name]:
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
            "POST_RESPONSE_INDETERMINATE"
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

    response_validated = (
        http_response_received
        and http_status_code == 200
        and all(
            response_checks.values()
        )
        and not failure_codes
        and post_request_count == 1
        and non_post_request_count == 0
        and automatic_retry_count == 0
        and redirect_followed is False
    )

    if response_validated:
        outcome = (
            "VALIDATED_HTTP_200_UPDATE_RESPONSE"
        )
        status = (
            "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_ONE_SHOT_POST_RESPONSE_VALIDATED_"
            "AWAITING_GET_ONLY_VERIFICATION"
        )
        decision = (
            "ONE_SHOT_UPDATE_RESPONSE_MATCHED_"
            "AUTHORIZATION_AND_CONFIRMATION_CONSUMED_NO_RETRY"
        )
        wordpress_update_performed = True
        wordpress_update_may_have_occurred = True
    elif not http_response_received:
        outcome = "INDETERMINATE"
        status = (
            "INDETERMINATE_WORDPRESS_TAWAWA_REFERENCE_"
            "LAYOUT_UPDATE_POST_RESPONSE_UNKNOWN_"
            "AUTHORIZATION_CONSUMED_NO_RETRY"
        )
        decision = (
            "POST_TRANSPORT_ATTEMPTED_RESPONSE_UNKNOWN_"
            "GET_ONLY_RECONCILIATION_REQUIRED"
        )
        wordpress_update_performed = False
        wordpress_update_may_have_occurred = True
    elif http_status_code != 200:
        outcome = "HTTP_NON_200"
        status = (
            "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_POST_HTTP_NON_200_AUTHORIZATION_"
            "CONSUMED_NO_RETRY"
        )
        decision = (
            "POST_RESPONSE_NON_200_GET_ONLY_"
            "RECONCILIATION_REQUIRED"
        )
        wordpress_update_performed = False
        wordpress_update_may_have_occurred = True
    else:
        outcome = "RESPONSE_MISMATCH"
        status = (
            "INDETERMINATE_WORDPRESS_TAWAWA_REFERENCE_"
            "LAYOUT_UPDATE_POST_RESPONSE_MISMATCH_"
            "AUTHORIZATION_CONSUMED_NO_RETRY"
        )
        decision = (
            "POST_RESPONSE_RECEIVED_BUT_VALIDATION_"
            "MISMATCH_GET_ONLY_RECONCILIATION_REQUIRED"
        )
        wordpress_update_performed = False
        wordpress_update_may_have_occurred = True

    snapshot_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE"
        ),
        "document_role": (
            "WORDPRESS_ONE_SHOT_POST_UPDATE_EXECUTION_SNAPSHOT"
        ),
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "request_method": "POST",
        "post_request_count": (
            post_request_count
        ),
        "non_post_request_count": (
            non_post_request_count
        ),
        "automatic_retry_count": (
            automatic_retry_count
        ),
        "redirect_followed": (
            redirect_followed
        ),
        "post_transport_call_attempted": (
            post_transport_call_attempted
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
        "outcome": outcome,
        "response_validated": (
            response_validated
        ),
        "response_post_id": (
            response_post_id
        ),
        "response_status": (
            response_status
        ),
        "response_title": (
            response_title
        ),
        "response_title_source": (
            response_title_source
        ),
        "response_category_ids": (
            response_categories
        ),
        "response_comment_status": (
            response_comment_status
        ),
        "response_content_sha256": (
            response_content_sha256
        ),
        "response_content_length": (
            response_content_length
        ),
        "response_checks": (
            response_checks
        ),
        "failure_codes": sorted(
            set(failure_codes)
        ),
        "request_body_digest_sha256": (
            EXPECTED_REQUEST_BODY_DIGEST
        ),
        "request_fields": [
            "content",
            "comment_status",
        ],
        "title_sent": False,
        "status_sent": False,
        "categories_sent": False,
        "slug_sent": False,
        "excerpt_sent": False,
        "featured_media_sent": False,
        "backlist_carousel_included": False,
        "authorization_consumed": True,
        "confirmation_consumed": True,
        "consumption_count": 1,
        "source_artifacts_modified": (
            source_artifacts_modified
        ),
        "credential_value_stored": False,
        "username_stored": False,
        "full_url_stored": False,
        "authorization_header_stored": False,
        "wordpress_content_stored": False,
        "affiliate_identifier_stored": False,
        "wordpress_delete_performed": False,
        "x_post_performed": False,
        "captured_at_utc": now()
    }

    snapshot = add_digest(
        snapshot_without_digest,
        "snapshot_digest_sha256",
    )
    write_json(
        SNAPSHOT,
        snapshot,
    )

    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE"
        ),
        "status": status,
        "decision": decision,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "consumption_path": str(
            CONSUMPTION.relative_to(ROOT)
        ),
        "consumption_digest_sha256": (
            consumption[
                "consumption_digest_sha256"
            ]
        ),
        "snapshot_path": str(
            SNAPSHOT.relative_to(ROOT)
        ),
        "snapshot_digest_sha256": (
            snapshot[
                "snapshot_digest_sha256"
            ]
        ),
        "outcome": outcome,
        "response_validated": (
            response_validated
        ),
        "request_method": "POST",
        "post_request_count": 1,
        "non_post_request_count": 0,
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
        "response_post_id_matches": (
            response_checks[
                "post_id_matches"
            ]
        ),
        "response_status_is_publish": (
            response_checks[
                "status_is_publish"
            ]
        ),
        "response_title_matches": (
            response_checks[
                "title_matches"
            ]
        ),
        "response_categories_match": (
            response_checks[
                "categories_match"
            ]
        ),
        "response_comment_status_is_closed": (
            response_checks[
                "comment_status_is_closed"
            ]
        ),
        "response_content_matches_m24": (
            response_checks[
                "content_matches_m24"
            ]
        ),
        "request_body_digest_sha256": (
            EXPECTED_REQUEST_BODY_DIGEST
        ),
        "allowed_update_fields": [
            "content",
            "comment_status",
        ],
        "target_comment_status": "closed",
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
        "wordpress_write_request_attempted": True,
        "wordpress_update_performed": (
            wordpress_update_performed
        ),
        "wordpress_update_may_have_occurred": (
            wordpress_update_may_have_occurred
        ),
        "wordpress_republish_performed": False,
        "wordpress_delete_performed": False,
        "x_post_performed": False,
        "production_status": "NO_GO",
        "required_next_phase": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M28-POST-UPDATE-VERIFY"
        ),
        "ready_for_post_update_get_verification": True,
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
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M27-EXECUTE

- Status: `{status}`
- Decision: `{decision}`
- WordPress post ID: `192`
- Outcome: `{outcome}`
- POST request count: `1`
- Non-POST request count: `0`
- Automatic retry count: `0`
- Redirect followed: `false`
- HTTP response received: `{str(http_response_received).lower()}`
- HTTP status: `{http_status_code}`
- Response validated: `{str(response_validated).lower()}`
- Allowed update fields: `content, comment_status`
- Target comment status: `closed`
- Authorization consumed: `true`
- Confirmation consumed: `true`
- Consumption count: `1`
- Second POST performed: `false`
- Backlist carousel included: `false`
- WordPress update confirmed: `{str(wordpress_update_performed).lower()}`
- WordPress update may have occurred: `{str(wordpress_update_may_have_occurred).lower()}`
- Production status: `NO_GO`
- Required next phase: `LS-NEW-BATCH-4G-2E-RECOVERY-M28-POST-UPDATE-VERIFY`
- Ready for GET-only verification: `true`
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
                        "M27-EXECUTE"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_ONE_SHOT_POST_"
                        "NO_AUTHORIZATION_CONSUMPTION"
                    ),
                    "safe_error_code": str(exc),
                    "post_request_count": 0,
                    "authorization_consumed": False,
                    "confirmation_consumed": False,
                    "wordpress_update_performed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
