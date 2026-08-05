from __future__ import annotations

import copy
import grp
import importlib.util
import json
import os
import pwd
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCRIPT_PATH = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2d.py"
)
POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_one_shot_actual_category_candidate_search_policy.json"
)
APPROVAL_PATH = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2d_approval.json"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_module():
    spec = importlib.util.spec_from_file_location(
        "execute_ls_new_batch_4g_2d_test_module",
        SCRIPT_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


def current_user_policy() -> dict:
    policy = load_json(POLICY_PATH)
    contract = policy["credential_contract"]

    contract["expected_owner"] = pwd.getpwuid(
        os.getuid()
    ).pw_name
    contract["expected_group"] = grp.getgrgid(
        os.getgid()
    ).gr_name

    return policy


def write_test_credentials(
    path: Path,
) -> None:
    path.write_text(
        (
            "WORDPRESS_BASE_URL=https://hoshido.jp\n"
            "WORDPRESS_READONLY_USERNAME=TEST_USER\n"
            "WORDPRESS_READONLY_APP_PASSWORD=TEST_PASSWORD\n"
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def valid_response() -> dict:
    body = json.dumps(
        [
            {
                "id": 15,
                "slug": "comic",
                "name": "コミック",
                "count": 12,
            },
            {
                "id": 27,
                "slug": "new-comic",
                "name": "コミック新刊",
                "count": 3,
            }
        ],
        ensure_ascii=False,
    ).encode("utf-8")

    return {
        "http_status": 200,
        "content_type": (
            "application/json; charset=UTF-8"
        ),
        "body": body,
        "response_bytes": len(body),
    }


def test_policy_is_exact_one_shot_get() -> None:
    policy = load_json(POLICY_PATH)
    scope = policy["one_shot_http_scope"]
    boundary = policy["execution_boundary"]

    assert scope["maximum_http_requests"] == 1
    assert scope["maximum_attempts"] == 1
    assert scope["retry_allowed"] is False
    assert scope["method"] == "GET"
    assert (
        scope["rest_path"]
        == "/wp-json/wp/v2/categories"
    )
    assert (
        scope["query_parameters"]["search"]
        == "コミック新刊"
    )
    assert scope["redirect_follow_allowed"] is False
    assert scope["proxy_use_allowed"] is False
    assert scope["tls_verification_required"] is True
    assert boundary["wordpress_write_allowed"] is False
    assert (
        boundary[
            "production_payload_modification_allowed"
        ]
        is False
    )


def test_approval_evidence_is_exact() -> None:
    approval = load_json(APPROVAL_PATH)

    assert (
        approval["approval_label"]
        == (
            "APPROVED_FOR_ONE_SHOT_READ_ONLY_"
            "CATEGORY_CANDIDATE_SEARCH_ONLY"
        )
    )
    assert approval["human_explicit_approval"] is True
    assert approval["approved_by"] == "HUMAN_OPERATOR"
    assert approval["approval_label_consumed"] is False
    assert approval["approval_reuse_allowed"] is False
    assert approval["execution_allowed"] is True
    assert (
        approval["approval_scope"][
            "automatic_candidate_selection_allowed"
        ]
        is False
    )


def test_base_url_accepts_exact_host() -> None:
    module = load_module()

    origin, hostname = module.validate_base_url(
        "https://hoshido.jp/",
        load_json(POLICY_PATH),
    )

    assert origin == "https://hoshido.jp"
    assert hostname == "hoshido.jp"


def test_base_url_rejects_wrong_host() -> None:
    module = load_module()

    try:
        module.validate_base_url(
            "https://example.com/",
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == "BLOCKED_WORDPRESS_HOSTNAME_MISMATCH"
        )
    else:
        raise AssertionError(
            "wrong hostname was accepted"
        )


def test_valid_response_records_candidates() -> None:
    module = load_module()

    candidate_list = module.validate_response(
        valid_response(),
        load_json(POLICY_PATH),
    )

    assert candidate_list["candidate_count"] == 2
    assert (
        candidate_list[
            "exact_search_term_name_match_count"
        ]
        == 1
    )
    assert candidate_list["candidate_selected"] is False
    assert (
        candidate_list[
            "automatic_selection_performed"
        ]
        is False
    )
    assert candidate_list["category_mapping_fixed"] is False
    assert (
        candidate_list["candidates"][1]["id"]
        == 27
    )
    assert (
        candidate_list["candidates"][1]["selected"]
        is False
    )


def test_empty_response_blocks() -> None:
    module = load_module()
    response = valid_response()
    response["body"] = b"[]"
    response["response_bytes"] = 2

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_WORDPRESS_CATEGORY_"
                "CANDIDATE_LIST_EMPTY"
            )
        )
    else:
        raise AssertionError(
            "empty candidate list was accepted"
        )


def test_too_many_candidates_block() -> None:
    module = load_module()
    items = [
        {
            "id": index + 1,
            "slug": f"candidate-{index}",
            "name": f"候補{index}",
            "count": 0,
        }
        for index in range(101)
    ]
    body = json.dumps(
        items,
        ensure_ascii=False,
    ).encode("utf-8")

    response = {
        "http_status": 200,
        "content_type": "application/json",
        "body": body,
        "response_bytes": len(body),
    }

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_WORDPRESS_CATEGORY_"
                "CANDIDATE_LIST_TOO_LARGE"
            )
        )
    else:
        raise AssertionError(
            "oversized candidate list was accepted"
        )


def test_invalid_candidate_id_blocks() -> None:
    module = load_module()
    response = valid_response()
    response["body"] = json.dumps(
        [
            {
                "id": 0,
                "slug": "comic",
                "name": "コミック",
                "count": 1,
            }
        ],
        ensure_ascii=False,
    ).encode("utf-8")
    response["response_bytes"] = len(
        response["body"]
    )

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_WORDPRESS_INVALID_"
                "CANDIDATE_ID"
            )
        )
    else:
        raise AssertionError(
            "invalid candidate ID was accepted"
        )


def test_duplicate_slug_blocks() -> None:
    module = load_module()
    response = valid_response()
    response["body"] = json.dumps(
        [
            {
                "id": 1,
                "slug": "comic",
                "name": "コミック",
                "count": 1,
            },
            {
                "id": 2,
                "slug": "comic",
                "name": "別コミック",
                "count": 2,
            }
        ],
        ensure_ascii=False,
    ).encode("utf-8")
    response["response_bytes"] = len(
        response["body"]
    )

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_WORDPRESS_DUPLICATE_"
                "CANDIDATE_SLUG"
            )
        )
    else:
        raise AssertionError(
            "duplicate candidate slug was accepted"
        )


def test_one_shot_lock_blocks_second_use(
    tmp_path: Path,
) -> None:
    module = load_module()
    approval = load_json(APPROVAL_PATH)
    lock_path = tmp_path / "one-shot.lock.json"

    module.reserve_one_shot(
        lock_path,
        approval=approval,
    )

    try:
        module.reserve_one_shot(
            lock_path,
            approval=approval,
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_ONE_SHOT_CANDIDATE_SEARCH_"
                "APPROVAL_ALREADY_CONSUMED"
            )
        )
    else:
        raise AssertionError(
            "one-shot approval was reused"
        )


def test_credential_parser_reads_exact_keys(
    tmp_path: Path,
) -> None:
    module = load_module()
    path = tmp_path / "credential.env"
    write_test_credentials(path)

    policy = current_user_policy()
    policy["credential_contract"][
        "credential_file_path"
    ] = str(path)

    values = module.read_credentials(
        policy
    )

    assert set(values) == {
        "WORDPRESS_BASE_URL",
        "WORDPRESS_READONLY_USERNAME",
        "WORDPRESS_READONLY_APP_PASSWORD",
    }


def test_fake_transport_success_is_one_request(
    tmp_path: Path,
) -> None:
    module = load_module()

    credential_path = (
        tmp_path / "credential.env"
    )
    write_test_credentials(
        credential_path
    )

    policy = current_user_policy()
    policy["credential_contract"][
        "credential_file_path"
    ] = str(credential_path)

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            policy,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result_path = tmp_path / "result.json"
    report_path = tmp_path / "report.md"
    lock_path = tmp_path / "lock.json"

    calls = {"count": 0}

    def fake_transport(**kwargs):
        calls["count"] += 1

        assert kwargs["request_url"].startswith(
            "https://hoshido.jp/"
        )
        assert (
            "search=%E3%82%B3%E3%83%9F%E3%83%83"
            in kwargs["request_url"]
        )
        assert kwargs["username"] == "TEST_USER"
        assert kwargs["password"] == "TEST_PASSWORD"

        return valid_response()

    return_code, result = module.execute(
        transport=fake_transport,
        policy_path=policy_path,
        approval_path=APPROVAL_PATH,
        source_result_path=module.SOURCE_RESULT_PATH,
        source_package_path=module.SOURCE_PACKAGE_PATH,
        result_path=result_path,
        report_path=report_path,
        lock_path_override=lock_path,
    )

    serialized = json.dumps(
        result,
        ensure_ascii=False,
    )

    assert return_code == 0
    assert calls["count"] == 1
    assert (
        result["http_request_attempt_count"]
        == 1
    )
    assert (
        result["status"]
        == (
            "PASS_ONE_SHOT_ACTUAL_READ_ONLY_"
            "CATEGORY_CANDIDATE_SEARCH"
        )
    )
    assert result["candidate_count"] == 2
    assert result["candidate_selected"] is False
    assert result["category_mapping_fixed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["production_payload_modified"] is False
    assert result["ready_for_ls_new_batch_4g_2e"] is True
    assert "TEST_PASSWORD" not in serialized
    assert "TEST_USER" not in serialized
    assert (
        "WORDPRESS_BASE_URL=https://"
        not in serialized
    )


def test_fake_empty_response_consumes_attempt(
    tmp_path: Path,
) -> None:
    module = load_module()

    credential_path = (
        tmp_path / "credential.env"
    )
    write_test_credentials(
        credential_path
    )

    policy = current_user_policy()
    policy["credential_contract"][
        "credential_file_path"
    ] = str(credential_path)

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            policy,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result_path = tmp_path / "result.json"
    report_path = tmp_path / "report.md"
    lock_path = tmp_path / "lock.json"

    def fake_transport(**kwargs):
        body = b"[]"
        return {
            "http_status": 200,
            "content_type": "application/json",
            "body": body,
            "response_bytes": len(body),
        }

    return_code, result = module.execute(
        transport=fake_transport,
        policy_path=policy_path,
        approval_path=APPROVAL_PATH,
        source_result_path=module.SOURCE_RESULT_PATH,
        source_package_path=module.SOURCE_PACKAGE_PATH,
        result_path=result_path,
        report_path=report_path,
        lock_path_override=lock_path,
    )

    lock = load_json(lock_path)

    assert return_code == 3
    assert (
        result["status"]
        == (
            "BLOCKED_WORDPRESS_CATEGORY_"
            "CANDIDATE_LIST_EMPTY"
        )
    )
    assert (
        lock["state"]
        == "CONSUMED_COMPLETED_BLOCKED"
    )
    assert lock["approval_label_consumed"] is True
    assert lock["http_request_attempt_count"] == 1
