#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_tawawa_reference_layout_update_"
    "preflight_revised_single_get_retry_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_retry_approval.json"
)

REVISED_TRANSPORT = ROOT / (
    "scripts/"
    "run_ls_new_batch_4g_2e_recovery_m27_fix1_get_only.py"
)
FIX1_DIAGNOSTIC = ROOT / (
    "exchange/diagnostics/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_m27_transport_failure_diagnostic.json"
)
FIX1_PLAN = ROOT / (
    "exchange/plans/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_next_single_get_non_execution_plan.json"
)
FIX1_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_result.json"
)

M27_SNAPSHOT = ROOT / (
    "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_authenticated_get_preflight_snapshot.json"
)
M27_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_pre_network_result.json"
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

SNAPSHOT = ROOT / (
    "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_revised_single_get_retry_snapshot.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_retry_approval_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_"
    "revised_single_get_retry_report.md"
)

NETWORK_GATE = (
    "M27_FIX1_SINGLE_GET_NETWORK_APPROVED"
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
EXPECTED_REVISED_TRANSPORT_SHA = (
    "7302e74c3d69fc3ba4084c75b2f1c44c"
    "6602f928caf9e223018a2ffcab0b39d4"
)
EXPECTED_FIX1_DIAGNOSTIC_DIGEST = (
    "8c9830eb0aa607e50bc4133473fd6d30"
    "ee8658a776bedabbd91081a4046b72bd"
)
EXPECTED_FIX1_PLAN_DIGEST = (
    "ff961b087a009c110d5be657132399d9"
    "57d2c838e1872d483d4491b7dd320a4e"
)
EXPECTED_FIX1_RESULT_DIGEST = (
    "170ee13236c60f771f72c356b2682e54"
    "040a9e5d51b2acf3f725c08a562c59d9"
)
EXPECTED_M27_SNAPSHOT_DIGEST = (
    "640dccfc0d6abbaf553894100408ed76c"
    "547a8c4d6d382e1d8d43a40f8d63a84"
)
EXPECTED_M27_RESULT_DIGEST = (
    "6d32f2005c4486fb78569f5f9d15c32"
    "2e6dd6ed66300ae5619c7a6e8803b0cde"
)
EXPECTED_M26_AUTHORIZATION_DIGEST = (
    "d7f53a0eb02a037cde4b6ab71b4b026b"
    "79eb8c2d2c08a95a8bec5f1ad0b6e615"
)
EXPECTED_M26_RESULT_DIGEST = (
    "c4aca489eabd70405c27a852eaf29400"
    "786b8b9054667cae59a5d0429af68c12"
)
EXPECTED_M24_PAYLOAD_DIGEST = (
    "52ed18792454e5806b739059911c8117"
    "810cafcadacf35fb77429b608673cd60"
)
EXPECTED_M25_REVIEW_DIGEST = (
    "7fd7a9f0f5317435160010fac811b77d"
    "876f77919ad2b5905c6cdea82f8f1806"
)
EXPECTED_M25_REQUIREMENT_DIGEST = (
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


def import_transport_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "m27_fix1_revised_transport",
        REVISED_TRANSPORT,
    )

    require(
        spec is not None,
        "REVISED_TRANSPORT_SPEC_MISSING",
    )
    require(
        spec.loader is not None,
        "REVISED_TRANSPORT_LOADER_MISSING",
    )

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


def main() -> int:
    source_paths = {
        "revised_transport": REVISED_TRANSPORT,
        "fix1_diagnostic": FIX1_DIAGNOSTIC,
        "fix1_plan": FIX1_PLAN,
        "fix1_result": FIX1_RESULT,
        "m27_snapshot": M27_SNAPSHOT,
        "m27_result": M27_RESULT,
        "m26_authorization": M26_AUTHORIZATION,
        "m26_result": M26_RESULT,
        "m24_rendered": M24_RENDERED,
        "m24_payload": M24_PAYLOAD,
        "m25_review": M25_REVIEW,
        "m25_requirement": M25_REQUIREMENT,
        "rollback": ROLLBACK,
    }

    for output in [
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
        == (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M27-FIX1-RETRY-APPROVAL"
        ),
        "POLICY_PHASE_MISMATCH",
    )
    require(
        approval["approval_label"]
        == (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "PREFLIGHT_REVISED_SINGLE_GET_RETRY_APPROVED"
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
        approval["redirect_following_approved"] is False,
        "REDIRECT_FOLLOWING_APPROVED",
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
    require(
        os.environ.get(NETWORK_GATE) == "YES",
        "EXPLICIT_NETWORK_GATE_NOT_SET",
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

    require(
        source_hashes_before[
            "revised_transport"
        ] == EXPECTED_REVISED_TRANSPORT_SHA,
        "REVISED_TRANSPORT_SHA_MISMATCH",
    )
    require(
        source_hashes_before[
            "m24_rendered"
        ] == EXPECTED_UPDATE_CONTENT_SHA,
        "M24_RENDERED_SHA_MISMATCH",
    )

    fix1_diagnostic = load_json(
        FIX1_DIAGNOSTIC
    )
    fix1_plan = load_json(
        FIX1_PLAN
    )
    fix1_result = load_json(
        FIX1_RESULT
    )
    m27_snapshot = load_json(
        M27_SNAPSHOT
    )
    m27_result = load_json(
        M27_RESULT
    )
    m26_authorization = load_json(
        M26_AUTHORIZATION
    )
    m26_result = load_json(
        M26_RESULT
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
    rollback = load_json(
        ROLLBACK
    )

    verify_digest(
        fix1_diagnostic,
        "diagnostic_digest_sha256",
        EXPECTED_FIX1_DIAGNOSTIC_DIGEST,
    )
    verify_digest(
        fix1_plan,
        "plan_digest_sha256",
        EXPECTED_FIX1_PLAN_DIGEST,
    )
    verify_digest(
        fix1_result,
        "result_digest_sha256",
        EXPECTED_FIX1_RESULT_DIGEST,
    )
    verify_digest(
        m27_snapshot,
        "snapshot_digest_sha256",
        EXPECTED_M27_SNAPSHOT_DIGEST,
    )
    verify_digest(
        m27_result,
        "result_digest_sha256",
        EXPECTED_M27_RESULT_DIGEST,
    )
    verify_digest(
        m26_authorization,
        "authorization_digest_sha256",
        EXPECTED_M26_AUTHORIZATION_DIGEST,
    )
    verify_digest(
        m26_result,
        "result_digest_sha256",
        EXPECTED_M26_RESULT_DIGEST,
    )
    verify_digest(
        m24_payload,
        "update_payload_digest_sha256",
        EXPECTED_M24_PAYLOAD_DIGEST,
    )
    verify_digest(
        m25_review,
        "human_review_evidence_digest_sha256",
        EXPECTED_M25_REVIEW_DIGEST,
    )
    verify_digest(
        m25_requirement,
        "future_requirement_digest_sha256",
        EXPECTED_M25_REQUIREMENT_DIGEST,
    )
    verify_digest(
        rollback,
        "rollback_evidence_digest_sha256",
        EXPECTED_ROLLBACK_DIGEST,
    )

    request_body = m24_payload.get(
        "wordpress_request_body"
    )
    rendered_html = M24_RENDERED.read_text(
        encoding="utf-8"
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

    require(
        m25_review[
            "human_review_completed"
        ] is True,
        "HUMAN_REVIEW_NOT_COMPLETED",
    )
    require(
        m25_review[
            "human_review_verdict"
        ] == "APPROVED_NO_CHANGE_REQUIRED",
        "HUMAN_REVIEW_NOT_APPROVED",
    )
    require(
        m25_requirement[
            "implementation_authorized"
        ] is False,
        "BACKLIST_IMPLEMENTATION_AUTHORIZED",
    )
    require(
        m25_requirement[
            "included_in_current_wordpress_update"
        ] is False,
        "BACKLIST_INCLUDED_IN_CURRENT_UPDATE",
    )

    require(
        m26_authorization[
            "wordpress_post_id"
        ] == EXPECTED_POST_ID,
        "AUTHORIZATION_POST_ID_MISMATCH",
    )
    require(
        m26_authorization[
            "authorization_consumed"
        ] is False,
        "AUTHORIZATION_ALREADY_CONSUMED",
    )
    require(
        m26_authorization[
            "consumption_count"
        ] == 0,
        "AUTHORIZATION_CONSUMPTION_COUNT_NOT_ZERO",
    )
    require(
        m26_authorization[
            "single_use"
        ] is True,
        "AUTHORIZATION_NOT_SINGLE_USE",
    )
    require(
        m26_authorization[
            "reuse_allowed"
        ] is False,
        "AUTHORIZATION_REUSE_ALLOWED",
    )
    require(
        m26_authorization[
            "automatic_retry_allowed"
        ] is False,
        "AUTHORIZATION_AUTOMATIC_RETRY_ALLOWED",
    )
    require(
        m26_authorization[
            "automatic_reissue_allowed"
        ] is False,
        "AUTHORIZATION_AUTOMATIC_REISSUE_ALLOWED",
    )

    require(
        fix1_result[
            "ready_for_separate_single_get_retry_approval"
        ] is True,
        "FIX1_RETRY_GATE_NOT_READY",
    )
    require(
        fix1_result[
            "revised_transport"
        ] == "URLLIB_REQUEST",
        "FIX1_REVISED_TRANSPORT_MISMATCH",
    )
    require(
        fix1_result[
            "authorization_consumed"
        ] is False,
        "FIX1_AUTHORIZATION_CONSUMED",
    )

    credential_stat = CREDENTIAL_ENV.stat()

    require(
        stat.S_IMODE(
            credential_stat.st_mode
        ) == 0o600,
        "CREDENTIAL_ENV_MODE_NOT_0600",
    )
    require(
        credential_stat.st_uid
        == os.geteuid(),
        "CREDENTIAL_ENV_OWNER_MISMATCH",
    )

    revised_module = (
        import_transport_module()
    )

    values = revised_module.load_env_file(
        CREDENTIAL_ENV
    )
    url, authorization_value = (
        revised_module.build_request_material(
            values
        )
    )

    local_integrity_gate_passed = True
    local_failure_codes: list[str] = []
    remote_failure_codes: list[str] = []

    get_request_count = 1
    non_get_request_count = 0
    automatic_retry_count = 0
    redirect_followed = False

    transport_call_attempted = True
    transport_call_completed = False
    http_response_received = False
    wordpress_access_performed = False

    http_status_code: int | None = None
    response_size_bytes: int | None = None
    safe_exception_type: str | None = None
    failure_stage: str | None = None

    current_post_id: int | None = None
    current_status: str | None = None
    current_title: str | None = None
    current_title_source: str | None = None
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
        "content_raw_observed": False,
        "current_content_matches_rollback": False,
    }

    try:
        http_status_code, response_bytes = (
            revised_module
            .urllib_single_get_transport(
                url,
                authorization_value,
                25,
            )
        )

        transport_call_completed = True
        http_response_received = True
        wordpress_access_performed = True
        response_size_bytes = len(
            response_bytes
        )

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
                    title_raw = (
                        title_object.get(
                            "raw"
                        )
                    )
                    title_rendered = (
                        title_object.get(
                            "rendered"
                        )
                    )

                    if isinstance(
                        title_raw,
                        str,
                    ):
                        current_title = (
                            title_raw
                        )
                        current_title_source = (
                            "raw"
                        )
                    elif isinstance(
                        title_rendered,
                        str,
                    ):
                        current_title = (
                            title_rendered
                        )
                        current_title_source = (
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
                            len(content_raw)
                        )
                        remote_checks[
                            "content_raw_observed"
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

                for check_name, failure_code in [
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
                        "content_raw_observed",
                        "WORDPRESS_CONTENT_RAW_MISSING",
                    ),
                    (
                        "current_content_matches_rollback",
                        "WORDPRESS_CURRENT_CONTENT_ROLLBACK_MISMATCH",
                    ),
                ]:
                    if not remote_checks[
                        check_name
                    ]:
                        remote_failure_codes.append(
                            failure_code
                        )
            else:
                remote_failure_codes.append(
                    "RESPONSE_ROOT_NOT_OBJECT"
                )

    except Exception as exc:
        safe_exception_type = (
            type(exc).__name__
        )
        failure_stage = (
            "SINGLE_URLLIB_TRANSPORT_CALL"
        )
        remote_failure_codes.append(
            "REVISED_SINGLE_GET_REQUEST_FAILED"
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
            "SOURCE_ARTIFACT_MODIFIED_DURING_RETRY"
        )

    preflight_passed = (
        local_integrity_gate_passed
        and not local_failure_codes
        and not remote_failure_codes
        and get_request_count == 1
        and non_get_request_count == 0
        and automatic_retry_count == 0
        and redirect_followed is False
    )

    snapshot_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M27-FIX1-RETRY-APPROVAL"
        ),
        "document_role": (
            "REVISED_URLLIB_AUTHENTICATED_GET_ONLY_"
            "WORDPRESS_PREFLIGHT_SNAPSHOT"
        ),
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "wordpress_post_id": EXPECTED_POST_ID,
        "transport": (
            "URLLIB_REQUEST_SINGLE_OPEN"
        ),
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
        "transport_call_attempted": (
            transport_call_attempted
        ),
        "transport_call_completed": (
            transport_call_completed
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
        "safe_exception_type": (
            safe_exception_type
        ),
        "failure_stage": (
            failure_stage
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
        "current_title_source": (
            current_title_source
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
        "remote_checks": (
            remote_checks
        ),
        "local_failure_codes": (
            local_failure_codes
        ),
        "remote_failure_codes": sorted(
            set(remote_failure_codes)
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
        "authorization_consumed": False,
        "authorization_reused": False,
        "automatic_reissue_performed": False,
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
            "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "PREFLIGHT_REVISED_SINGLE_GET_RETRY_READY_FOR_"
            "EXPLICIT_EXECUTE_NOW_CONFIRMATION"
        )
        decision = (
            "WORDPRESS_CURRENT_STATE_MATCHED_"
            "M26_AUTHORIZATION_REMAINS_UNCONSUMED"
        )
    else:
        status = (
            "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "PREFLIGHT_REVISED_SINGLE_GET_RETRY_NO_WORDPRESS_WRITE"
        )
        decision = (
            "REVISED_SINGLE_GET_PREFLIGHT_NOT_READY_"
            "AUTHORIZATION_REMAINS_UNCONSUMED"
        )

    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-"
            "M27-FIX1-RETRY-APPROVAL"
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
            local_integrity_gate_passed
        ),
        "local_failure_codes": (
            local_failure_codes
        ),
        "remote_failure_codes": sorted(
            set(remote_failure_codes)
        ),
        "transport": (
            "URLLIB_REQUEST_SINGLE_OPEN"
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
        "redirect_followed": (
            redirect_followed
        ),
        "transport_call_attempted": (
            transport_call_attempted
        ),
        "transport_call_completed": (
            transport_call_completed
        ),
        "http_response_received": (
            http_response_received
        ),
        "http_status_code": (
            http_status_code
        ),
        "safe_exception_type": (
            safe_exception_type
        ),
        "failure_stage": (
            failure_stage
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
        "update_content_matches_m24": True,
        "request_body_digest_sha256": (
            EXPECTED_REQUEST_BODY_DIGEST
        ),
        "request_body_digest_matches": True,
        "authorization_id": (
            "WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_ONE_SHOT_AUTHORIZATION_V1"
        ),
        "authorization_digest_sha256": (
            EXPECTED_M26_AUTHORIZATION_DIGEST
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
            "REVISED_SINGLE_GET_PREFLIGHT_COMPLETE_"
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
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M27-FIX1-RETRY-APPROVAL

- Status: `{status}`
- Decision: `{decision}`
- WordPress post ID: `192`
- Transport: `URLLIB_REQUEST_SINGLE_OPEN`
- Preflight passed: `{str(preflight_passed).lower()}`
- GET request count: `{get_request_count}`
- Non-GET request count: `{non_get_request_count}`
- Automatic retry count: `{automatic_retry_count}`
- Redirect followed: `{str(redirect_followed).lower()}`
- HTTP status: `{http_status_code}`
- Current post ID matches: `{str(remote_checks["post_id_matches"]).lower()}`
- Current status is publish: `{str(remote_checks["status_is_publish"]).lower()}`
- Current title matches: `{str(remote_checks["title_matches"]).lower()}`
- Current categories match: `{str(remote_checks["categories_match"]).lower()}`
- Current comment status: `{current_comment_status}`
- Current content matches rollback: `{str(remote_checks["current_content_matches_rollback"]).lower()}`
- Update content matches M24: `true`
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
                        "M27-FIX1-RETRY-APPROVAL"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_REVISED_SINGLE_GET_"
                        "NO_WORDPRESS_WRITE"
                    ),
                    "safe_error_code": str(exc),
                    "get_request_count": 0,
                    "non_get_request_count": 0,
                    "automatic_retry_count": 0,
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
