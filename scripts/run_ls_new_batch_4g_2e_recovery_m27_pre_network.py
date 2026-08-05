#!/usr/bin/env python3

from __future__ import annotations

import base64
import copy
import hashlib
import http.client
import json
import os
import ssl
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_layout_"
    "update_authenticated_preflight_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m27_pre_network_approval.json"
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
M26_AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_one_shot_authorization.json"
)
M26_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m26_result.json"
)
ROLLBACK = ROOT / (
    "exchange/rollback/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_correction_current_content_rollback_fix2.json"
)

CREDENTIAL_ENV = Path(
    "/etc/ai-media-os/credential.env"
)

SNAPSHOT = ROOT / (
    "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_authenticated_get_preflight_snapshot.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_pre_network_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m27_pre_network_"
    "authenticated_get_preflight_report.md"
)

EXPECTED_POST_ID = 192
EXPECTED_STATUS = "publish"
EXPECTED_TITLE = "ダークギャザリング 第20巻｜配信開始"
EXPECTED_CATEGORIES = [10]

EXPECTED_CURRENT_CONTENT_SHA = (
    "c5851f15e4eb477038dca512c8990068"
    "736a306cf4fb8c207036a3186119f436"
)
EXPECTED_UPDATE_CONTENT_SHA = (
    "dc938ae164c70130a5fb27692d71c97c"
    "c367a8985c44c2c333801b337ee6caf4"
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
EXPECTED_AUTHORIZATION_DIGEST = (
    "d7f53a0eb02a037cde4b6ab71b4b026b"
    "79eb8c2d2c08a95a8bec5f1ad0b6e615"
)
EXPECTED_M26_RESULT_DIGEST = (
    "c4aca489eabd70405c27a852eaf29400"
    "786b8b9054667cae59a5d0429af68c12"
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


def text_sha(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def file_sha(
    path: Path,
) -> str:
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
        canonical_digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"DIGEST_EXPECTED_MISMATCH:{field}",
        )

    return stored


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


def collect_strings(
    value: Any,
) -> list[str]:
    found: list[str] = []

    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(
                collect_strings(item)
            )
    elif isinstance(value, list):
        for item in value:
            found.extend(
                collect_strings(item)
            )

    return found


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


def main() -> int:
    source_paths = {
        "m24_rendered": M24_RENDERED,
        "m24_payload": M24_PAYLOAD,
        "m25_review": M25_REVIEW,
        "m25_requirement": M25_REQUIREMENT,
        "m26_authorization": M26_AUTHORIZATION,
        "m26_result": M26_RESULT,
        "rollback": ROLLBACK,
    }

    for output in [
        SNAPSHOT,
        RESULT,
        REPORT,
    ]:
        require(
            not output.exists(),
            f"M27_PRE_NETWORK_OUTPUT_ALREADY_EXISTS:{output.name}",
        )

    policy = load_json(POLICY)
    approval = load_json(APPROVAL)

    verify_digest(
        approval,
        "approval_evidence_digest_sha256",
    )

    require(
        policy["phase_id"]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M27-PRE-NETWORK",
        "POLICY_PHASE_MISMATCH",
    )
    require(
        approval["approval_label"]
        == (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "AUTHENTICATED_PREFLIGHT_APPROVED"
        ),
        "APPROVAL_LABEL_MISMATCH",
    )
    require(
        approval["maximum_get_request_count"] == 1,
        "GET_REQUEST_COUNT_NOT_ONE",
    )
    require(
        approval["non_get_request_approved"] is False,
        "NON_GET_REQUEST_APPROVED",
    )
    require(
        approval["automatic_retry_approved"] is False,
        "AUTOMATIC_RETRY_APPROVED",
    )
    require(
        approval["wordpress_update_approved"] is False,
        "WORDPRESS_UPDATE_APPROVED",
    )
    require(
        approval[
            "authorization_consumption_approved"
        ] is False,
        "AUTHORIZATION_CONSUMPTION_APPROVED",
    )

    source_hashes_before = {
        name: file_sha(path)
        for name, path in source_paths.items()
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

    m24_payload = load_json(
        M24_PAYLOAD
    )
    m25_review = load_json(
        M25_REVIEW
    )
    m25_requirement = load_json(
        M25_REQUIREMENT
    )
    m26_authorization = load_json(
        M26_AUTHORIZATION
    )
    m26_result = load_json(
        M26_RESULT
    )
    rollback = load_json(
        ROLLBACK
    )

    local_checks: dict[str, bool] = {}
    local_failure_codes: list[str] = []

    def local_check(
        name: str,
        condition: bool,
        failure_code: str,
    ) -> None:
        local_checks[name] = condition

        if not condition:
            local_failure_codes.append(
                failure_code
            )

    try:
        verify_digest(
            m24_payload,
            "update_payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        local_check(
            "m24_payload_digest_valid",
            True,
            "M24_PAYLOAD_DIGEST_INVALID",
        )
    except ValidationError:
        local_check(
            "m24_payload_digest_valid",
            False,
            "M24_PAYLOAD_DIGEST_INVALID",
        )

    try:
        verify_digest(
            m25_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_REVIEW_DIGEST,
        )
        local_check(
            "m25_review_digest_valid",
            True,
            "M25_REVIEW_DIGEST_INVALID",
        )
    except ValidationError:
        local_check(
            "m25_review_digest_valid",
            False,
            "M25_REVIEW_DIGEST_INVALID",
        )

    try:
        verify_digest(
            m25_requirement,
            "future_requirement_digest_sha256",
            EXPECTED_REQUIREMENT_DIGEST,
        )
        local_check(
            "m25_requirement_digest_valid",
            True,
            "M25_REQUIREMENT_DIGEST_INVALID",
        )
    except ValidationError:
        local_check(
            "m25_requirement_digest_valid",
            False,
            "M25_REQUIREMENT_DIGEST_INVALID",
        )

    try:
        verify_digest(
            m26_authorization,
            "authorization_digest_sha256",
            EXPECTED_AUTHORIZATION_DIGEST,
        )
        local_check(
            "m26_authorization_digest_valid",
            True,
            "M26_AUTHORIZATION_DIGEST_INVALID",
        )
    except ValidationError:
        local_check(
            "m26_authorization_digest_valid",
            False,
            "M26_AUTHORIZATION_DIGEST_INVALID",
        )

    try:
        verify_digest(
            m26_result,
            "result_digest_sha256",
            EXPECTED_M26_RESULT_DIGEST,
        )
        local_check(
            "m26_result_digest_valid",
            True,
            "M26_RESULT_DIGEST_INVALID",
        )
    except ValidationError:
        local_check(
            "m26_result_digest_valid",
            False,
            "M26_RESULT_DIGEST_INVALID",
        )

    try:
        verify_digest(
            rollback,
            "rollback_evidence_digest_sha256",
            EXPECTED_ROLLBACK_DIGEST,
        )
        local_check(
            "rollback_digest_valid",
            True,
            "ROLLBACK_DIGEST_INVALID",
        )
    except ValidationError:
        local_check(
            "rollback_digest_valid",
            False,
            "ROLLBACK_DIGEST_INVALID",
        )

    rendered_html = M24_RENDERED.read_text(
        encoding="utf-8"
    )

    local_check(
        "m24_rendered_content_sha_matches",
        text_sha(rendered_html)
        == EXPECTED_UPDATE_CONTENT_SHA,
        "M24_RENDERED_CONTENT_SHA_MISMATCH",
    )

    request_body = m24_payload.get(
        "wordpress_request_body"
    )

    local_check(
        "request_body_is_object",
        isinstance(request_body, dict),
        "REQUEST_BODY_NOT_OBJECT",
    )

    if isinstance(request_body, dict):
        local_check(
            "request_fields_are_strictly_limited",
            set(request_body.keys())
            == {
                "content",
                "comment_status",
            },
            "REQUEST_FIELD_SET_MISMATCH",
        )
        local_check(
            "request_content_matches_m24_rendered",
            request_body.get("content")
            == rendered_html,
            "REQUEST_CONTENT_MISMATCH",
        )
        local_check(
            "request_comment_status_is_closed",
            request_body.get(
                "comment_status"
            ) == "closed",
            "REQUEST_COMMENT_STATUS_NOT_CLOSED",
        )
        local_check(
            "request_body_digest_matches",
            canonical_digest(request_body)
            == EXPECTED_REQUEST_BODY_DIGEST,
            "REQUEST_BODY_DIGEST_MISMATCH",
        )
    else:
        for name, code in [
            (
                "request_fields_are_strictly_limited",
                "REQUEST_FIELD_SET_MISMATCH",
            ),
            (
                "request_content_matches_m24_rendered",
                "REQUEST_CONTENT_MISMATCH",
            ),
            (
                "request_comment_status_is_closed",
                "REQUEST_COMMENT_STATUS_NOT_CLOSED",
            ),
            (
                "request_body_digest_matches",
                "REQUEST_BODY_DIGEST_MISMATCH",
            ),
        ]:
            local_check(
                name,
                False,
                code,
            )

    local_check(
        "rollback_contains_expected_current_content_sha",
        EXPECTED_CURRENT_CONTENT_SHA
        in collect_strings(rollback),
        "ROLLBACK_CURRENT_CONTENT_SHA_NOT_FOUND",
    )

    local_check(
        "human_review_completed",
        m25_review.get(
            "human_review_completed"
        ) is True,
        "HUMAN_REVIEW_NOT_COMPLETED",
    )
    local_check(
        "human_review_approved",
        m25_review.get(
            "human_review_verdict"
        ) == "APPROVED_NO_CHANGE_REQUIRED",
        "HUMAN_REVIEW_NOT_APPROVED",
    )
    local_check(
        "backlist_requirement_not_implemented",
        m25_requirement.get(
            "implementation_authorized"
        ) is False,
        "BACKLIST_IMPLEMENTATION_AUTHORIZED",
    )
    local_check(
        "backlist_requirement_not_in_current_update",
        m25_requirement.get(
            "included_in_current_wordpress_update"
        ) is False,
        "BACKLIST_INCLUDED_IN_CURRENT_UPDATE",
    )

    local_check(
        "authorization_issued",
        m26_authorization.get(
            "authorization_id"
        )
        == (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_ONE_SHOT_AUTHORIZATION_V1"
        ),
        "AUTHORIZATION_ID_MISMATCH",
    )
    local_check(
        "authorization_unconsumed",
        m26_authorization.get(
            "authorization_consumed"
        ) is False,
        "AUTHORIZATION_ALREADY_CONSUMED",
    )
    local_check(
        "authorization_consumption_count_zero",
        m26_authorization.get(
            "consumption_count"
        ) == 0,
        "AUTHORIZATION_CONSUMPTION_COUNT_NOT_ZERO",
    )
    local_check(
        "authorization_single_use",
        m26_authorization.get(
            "single_use"
        ) is True,
        "AUTHORIZATION_NOT_SINGLE_USE",
    )
    local_check(
        "authorization_reuse_blocked",
        m26_authorization.get(
            "reuse_allowed"
        ) is False,
        "AUTHORIZATION_REUSE_ALLOWED",
    )
    local_check(
        "authorization_retry_blocked",
        m26_authorization.get(
            "automatic_retry_allowed"
        ) is False,
        "AUTHORIZATION_AUTOMATIC_RETRY_ALLOWED",
    )
    local_check(
        "authorization_reissue_blocked",
        m26_authorization.get(
            "automatic_reissue_allowed"
        ) is False,
        "AUTHORIZATION_AUTOMATIC_REISSUE_ALLOWED",
    )
    local_check(
        "authorization_post_id_matches",
        m26_authorization.get(
            "wordpress_post_id"
        ) == EXPECTED_POST_ID,
        "AUTHORIZATION_POST_ID_MISMATCH",
    )
    local_check(
        "authorization_backlist_excluded",
        m26_authorization.get(
            "backlist_carousel_included"
        ) is False,
        "AUTHORIZATION_BACKLIST_INCLUDED",
    )

    local_gate_passed = (
        not local_failure_codes
    )

    get_request_count = 0
    non_get_request_count = 0
    automatic_retry_count = 0

    network_connection_attempted = False
    network_connection_performed = False
    dns_resolution_performed = False
    http_request_performed = False
    http_response_received = False
    wordpress_access_performed = False

    http_status_code: int | None = None
    response_size_bytes: int | None = None
    network_error_type: str | None = None

    current_post_id: int | None = None
    current_status: str | None = None
    current_title: str | None = None
    current_categories: list[int] | None = None
    current_comment_status: str | None = None
    current_content_sha256: str | None = None
    current_content_length: int | None = None

    remote_checks = {
        "http_status_200": False,
        "response_json_object": False,
        "post_id_matches": False,
        "status_is_publish": False,
        "title_matches": False,
        "categories_match": False,
        "comment_status_observed": False,
        "current_content_raw_observed": False,
        "current_content_matches_rollback": False,
    }
    remote_failure_codes: list[str] = []

    if local_gate_passed:
        credentials = load_credential_env(
            CREDENTIAL_ENV
        )

        parsed = urlsplit(
            credentials[
                "WORDPRESS_BASE_URL"
            ]
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

        base_path = parsed.path.rstrip(
            "/"
        )
        rest_path = (
            f"{base_path}/wp-json/wp/v2/posts/"
            f"{EXPECTED_POST_ID}"
            "?context=edit"
            "&_fields=id,status,title,categories,"
            "comment_status,content"
        )

        credential_token = base64.b64encode(
            (
                credentials["WORDPRESS_USERNAME"]
                + ":"
                + credentials[
                    "WORDPRESS_APP_PASSWORD"
                ]
            ).encode("utf-8")
        ).decode("ascii")

        connection = http.client.HTTPSConnection(
            parsed.hostname,
            parsed.port or 443,
            timeout=25,
            context=ssl.create_default_context(),
        )

        network_connection_attempted = True
        get_request_count = 1

        try:
            connection.request(
                "GET",
                rest_path,
                headers={
                    "Authorization": (
                        "Basic "
                        + credential_token
                    ),
                    "Accept": "application/json",
                    "User-Agent": (
                        "ai-media-os-m27-preflight/1.0"
                    ),
                    "Connection": "close",
                },
            )

            network_connection_performed = True
            dns_resolution_performed = True
            http_request_performed = True

            response = connection.getresponse()

            http_response_received = True
            wordpress_access_performed = True
            http_status_code = response.status

            response_bytes = response.read(
                MAX_RESPONSE_BYTES + 1
            )
            response_size_bytes = len(
                response_bytes
            )

            if (
                response_size_bytes
                > MAX_RESPONSE_BYTES
            ):
                remote_failure_codes.append(
                    "RESPONSE_SIZE_LIMIT_EXCEEDED"
                )
            else:
                remote_checks[
                    "http_status_200"
                ] = http_status_code == 200

                if not remote_checks[
                    "http_status_200"
                ]:
                    remote_failure_codes.append(
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
                        remote_failure_codes.append(
                            "RESPONSE_JSON_PARSE_FAILED"
                        )

                    remote_checks[
                        "response_json_object"
                    ] = isinstance(
                        response_json,
                        dict,
                    )

                    if isinstance(
                        response_json,
                        dict,
                    ):
                        current_post_id = (
                            response_json.get("id")
                        )
                        current_status = (
                            response_json.get(
                                "status"
                            )
                        )

                        title_object = (
                            response_json.get(
                                "title"
                            )
                        )
                        content_object = (
                            response_json.get(
                                "content"
                            )
                        )
                        categories_object = (
                            response_json.get(
                                "categories"
                            )
                        )

                        if isinstance(
                            title_object,
                            dict,
                        ):
                            title_raw = (
                                title_object.get(
                                    "raw"
                                )
                            )

                            if isinstance(
                                title_raw,
                                str,
                            ):
                                current_title = (
                                    title_raw
                                )

                        if isinstance(
                            categories_object,
                            list,
                        ) and all(
                            isinstance(item, int)
                            for item
                            in categories_object
                        ):
                            current_categories = (
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
                            current_comment_status = (
                                comment_status
                            )

                        if isinstance(
                            content_object,
                            dict,
                        ):
                            content_raw = (
                                content_object.get(
                                    "raw"
                                )
                            )

                            if isinstance(
                                content_raw,
                                str,
                            ):
                                current_content_sha256 = (
                                    text_sha(
                                        content_raw
                                    )
                                )
                                current_content_length = (
                                    len(
                                        content_raw
                                    )
                                )
                                remote_checks[
                                    "current_content_raw_observed"
                                ] = True

                        remote_checks[
                            "post_id_matches"
                        ] = (
                            current_post_id
                            == EXPECTED_POST_ID
                        )
                        remote_checks[
                            "status_is_publish"
                        ] = (
                            current_status
                            == EXPECTED_STATUS
                        )
                        remote_checks[
                            "title_matches"
                        ] = (
                            current_title
                            == EXPECTED_TITLE
                        )
                        remote_checks[
                            "categories_match"
                        ] = (
                            current_categories
                            is not None
                            and sorted(
                                current_categories
                            )
                            == EXPECTED_CATEGORIES
                        )
                        remote_checks[
                            "comment_status_observed"
                        ] = (
                            current_comment_status
                            in {
                                "open",
                                "closed",
                            }
                        )
                        remote_checks[
                            "current_content_matches_rollback"
                        ] = (
                            current_content_sha256
                            == EXPECTED_CURRENT_CONTENT_SHA
                        )

                        for name, code in [
                            (
                                "post_id_matches",
                                "WORDPRESS_POST_ID_MISMATCH",
                            ),
                            (
                                "status_is_publish",
                                "WORDPRESS_STATUS_NOT_PUBLISH",
                            ),
                            (
                                "title_matches",
                                "WORDPRESS_TITLE_MISMATCH",
                            ),
                            (
                                "categories_match",
                                "WORDPRESS_CATEGORIES_MISMATCH",
                            ),
                            (
                                "comment_status_observed",
                                "WORDPRESS_COMMENT_STATUS_INVALID",
                            ),
                            (
                                "current_content_raw_observed",
                                "WORDPRESS_CONTENT_RAW_MISSING",
                            ),
                            (
                                "current_content_matches_rollback",
                                "WORDPRESS_CURRENT_CONTENT_ROLLBACK_MISMATCH",
                            ),
                        ]:
                            if not remote_checks[name]:
                                remote_failure_codes.append(
                                    code
                                )
                    else:
                        remote_failure_codes.append(
                            "RESPONSE_ROOT_NOT_OBJECT"
                        )

        except Exception as exc:
            network_error_type = (
                type(exc).__name__
            )
            remote_failure_codes.append(
                "SINGLE_GET_REQUEST_FAILED"
            )
        finally:
            connection.close()
    else:
        remote_failure_codes.append(
            "LOCAL_INTEGRITY_GATE_BLOCKED_GET"
        )

    source_hashes_after = {
        name: file_sha(path)
        for name, path in source_paths.items()
    }

    source_artifacts_modified = (
        source_hashes_before
        != source_hashes_after
    )

    if source_artifacts_modified:
        remote_failure_codes.append(
            "SOURCE_ARTIFACT_MODIFIED_DURING_PREFLIGHT"
        )

    preflight_passed = (
        local_gate_passed
        and not remote_failure_codes
        and get_request_count == 1
        and non_get_request_count == 0
        and automatic_retry_count == 0
    )

    snapshot_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M27-PRE-NETWORK"
        ),
        "document_role": (
            "AUTHENTICATED_GET_ONLY_WORDPRESS_"
            "CURRENT_STATE_PREFLIGHT_SNAPSHOT"
        ),
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "request_method": "GET",
        "get_request_count": get_request_count,
        "non_get_request_count": (
            non_get_request_count
        ),
        "automatic_retry_count": (
            automatic_retry_count
        ),
        "redirect_followed": False,
        "network_connection_attempted": (
            network_connection_attempted
        ),
        "network_connection_performed": (
            network_connection_performed
        ),
        "dns_resolution_performed": (
            dns_resolution_performed
        ),
        "http_request_performed": (
            http_request_performed
        ),
        "http_response_received": (
            http_response_received
        ),
        "wordpress_access_performed": (
            wordpress_access_performed
        ),
        "http_status_code": http_status_code,
        "response_size_bytes": (
            response_size_bytes
        ),
        "network_error_type": (
            network_error_type
        ),
        "current_post_id": (
            current_post_id
        ),
        "current_status": (
            current_status
        ),
        "current_title": (
            current_title
        ),
        "current_category_ids": (
            current_categories
        ),
        "current_comment_status": (
            current_comment_status
        ),
        "current_content_sha256": (
            current_content_sha256
        ),
        "current_content_length": (
            current_content_length
        ),
        "expected_current_content_sha256": (
            EXPECTED_CURRENT_CONTENT_SHA
        ),
        "expected_update_content_sha256": (
            EXPECTED_UPDATE_CONTENT_SHA
        ),
        "local_checks": local_checks,
        "remote_checks": remote_checks,
        "local_failure_codes": sorted(
            set(local_failure_codes)
        ),
        "remote_failure_codes": sorted(
            set(remote_failure_codes)
        ),
        "current_content_stored": False,
        "full_store_url_stored": False,
        "credential_value_stored": False,
        "username_stored": False,
        "authorization_header_stored": False,
        "wordpress_write_performed": False,
        "wordpress_update_performed": False,
        "wordpress_republish_performed": False,
        "wordpress_delete_performed": False,
        "authorization_consumed": False,
        "authorization_reused": False,
        "backlist_carousel_included": False,
        "source_artifacts_modified": (
            source_artifacts_modified
        ),
        "preflight_passed": (
            preflight_passed
        ),
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

    if preflight_passed:
        status = (
            "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_AUTHENTICATED_GET_ONLY_PREFLIGHT_"
            "READY_FOR_EXPLICIT_EXECUTE_NOW_CONFIRMATION"
        )
        decision = (
            "CURRENT_WORDPRESS_STATE_MATCHED_"
            "ONE_SHOT_AUTHORIZATION_REMAINS_UNCONSUMED"
        )
    else:
        status = (
            "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_AUTHENTICATED_PREFLIGHT_MISMATCH_"
            "NO_WORDPRESS_WRITE"
        )
        decision = (
            "PREFLIGHT_NOT_READY_REVIEW_RECORDED_"
            "AUTHORIZATION_REMAINS_UNCONSUMED"
        )

    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M27-PRE-NETWORK"
        ),
        "status": status,
        "decision": decision,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "snapshot_path": str(
            SNAPSHOT.relative_to(ROOT)
        ),
        "snapshot_digest_sha256": (
            snapshot[
                "snapshot_digest_sha256"
            ]
        ),
        "preflight_passed": (
            preflight_passed
        ),
        "local_integrity_gate_passed": (
            local_gate_passed
        ),
        "local_failure_codes": sorted(
            set(local_failure_codes)
        ),
        "remote_failure_codes": sorted(
            set(remote_failure_codes)
        ),
        "get_request_count": (
            get_request_count
        ),
        "non_get_request_count": (
            non_get_request_count
        ),
        "automatic_retry_count": (
            automatic_retry_count
        ),
        "redirect_followed": False,
        "http_status_code": (
            http_status_code
        ),
        "current_post_id_matches": (
            remote_checks[
                "post_id_matches"
            ]
        ),
        "current_status_is_publish": (
            remote_checks[
                "status_is_publish"
            ]
        ),
        "current_title_matches": (
            remote_checks[
                "title_matches"
            ]
        ),
        "current_categories_match": (
            remote_checks[
                "categories_match"
            ]
        ),
        "current_comment_status": (
            current_comment_status
        ),
        "current_content_sha256": (
            current_content_sha256
        ),
        "current_content_matches_rollback": (
            remote_checks[
                "current_content_matches_rollback"
            ]
        ),
        "update_content_sha256": (
            EXPECTED_UPDATE_CONTENT_SHA
        ),
        "update_content_matches_m24": (
            local_checks.get(
                "m24_rendered_content_sha_matches",
                False,
            )
        ),
        "request_body_digest_sha256": (
            EXPECTED_REQUEST_BODY_DIGEST
        ),
        "request_body_digest_matches": (
            local_checks.get(
                "request_body_digest_matches",
                False,
            )
        ),
        "authorization_id": (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_ONE_SHOT_AUTHORIZATION_V1"
        ),
        "authorization_digest_sha256": (
            EXPECTED_AUTHORIZATION_DIGEST
        ),
        "authorization_issued": True,
        "authorization_consumed": False,
        "consumption_count": 0,
        "single_use": True,
        "maximum_update_count": 1,
        "authorization_reused": False,
        "automatic_reissue_performed": False,
        "backlist_carousel_included": False,
        "backlist_carousel_implemented": False,
        "source_artifacts_modified": (
            source_artifacts_modified
        ),
        "network_connection_attempted": (
            network_connection_attempted
        ),
        "network_connection_performed": (
            network_connection_performed
        ),
        "dns_resolution_performed": (
            dns_resolution_performed
        ),
        "http_request_performed": (
            http_request_performed
        ),
        "wordpress_access_performed": (
            wordpress_access_performed
        ),
        "wordpress_write_performed": False,
        "wordpress_update_performed": False,
        "wordpress_republish_performed": False,
        "wordpress_delete_performed": False,
        "authorization_consumption_performed": False,
        "x_post_performed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "AUTHENTICATED_GET_PREFLIGHT_COMPLETE_"
            "NO_WRITE_AUTHORIZATION_UNCONSUMED"
        ),
        "required_next_phase": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M27-EXECUTE-NOW-CONFIRMATION"
        ),
        "ready_for_execute_now_confirmation": (
            preflight_passed
        ),
        "ready_for_wordpress_update": False,
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
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M27-PRE-NETWORK

- Status: `{status}`
- Decision: `{decision}`
- WordPress post ID: `192`
- Preflight passed: `{str(preflight_passed).lower()}`
- GET request count: `{get_request_count}`
- Non-GET request count: `{non_get_request_count}`
- Automatic retry count: `{automatic_retry_count}`
- HTTP status: `{http_status_code}`
- Current status is publish: `{str(remote_checks["status_is_publish"]).lower()}`
- Current title matches: `{str(remote_checks["title_matches"]).lower()}`
- Current categories match: `{str(remote_checks["categories_match"]).lower()}`
- Current comment status: `{current_comment_status}`
- Current content matches rollback: `{str(remote_checks["current_content_matches_rollback"]).lower()}`
- Update content matches M24: `{str(local_checks.get("m24_rendered_content_sha_matches", False)).lower()}`
- Authorization consumed: `false`
- WordPress write performed: `false`
- WordPress update performed: `false`
- Backlist carousel included: `false`
- Production status: `NO_GO`
- Ready for execute-now confirmation: `{str(preflight_passed).lower()}`
- Ready for WordPress update: `false`
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
                        "M27-PRE-NETWORK"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_AUTHENTICATED_GET_"
                        "NO_WORDPRESS_WRITE"
                    ),
                    "error_code": str(exc),
                    "wordpress_write_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_consumed": False,
                    "execution_allowed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
