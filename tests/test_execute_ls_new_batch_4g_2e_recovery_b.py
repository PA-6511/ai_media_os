from __future__ import annotations

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
    "execute_ls_new_batch_4g_2e_recovery_b.py"
)
POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_one_shot_actual_"
    "category_index_recovery_policy.json"
)
APPROVAL_PATH = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_b_approval.json"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_module():
    spec = importlib.util.spec_from_file_location(
        "execute_recovery_b_test_module",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
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


def write_test_credentials(path: Path) -> None:
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
                "slug": "books",
                "name": "書籍",
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
        "x_wp_total": "2",
        "x_wp_total_pages": "1",
    }


def test_policy_is_exact_one_shot_get() -> None:
    policy = load_json(POLICY_PATH)
    scope = policy["one_shot_http_scope"]
    boundary = policy["execution_boundary"]

    assert scope["maximum_http_requests"] == 1
    assert scope["maximum_attempts"] == 1
    assert scope["retry_allowed"] is False
    assert scope["method"] == "GET"
    assert scope["query_parameters"] == {
        "per_page": 100,
        "orderby": "name",
        "order": "asc",
        "hide_empty": "false",
        "_fields": "id,slug,name,count",
    }
    assert scope["redirect_follow_allowed"] is False
    assert scope["proxy_use_allowed"] is False
    assert scope["maximum_total_pages"] == 1
    assert boundary["wordpress_write_allowed"] is False


def test_approval_evidence_is_exact() -> None:
    approval = load_json(APPROVAL_PATH)

    assert (
        approval["approval_label"]
        == (
            "APPROVED_FOR_ONE_SHOT_READ_ONLY_"
            "CATEGORY_INDEX_RECOVERY_ONLY"
        )
    )
    assert approval["human_explicit_approval"] is True
    assert approval["approved_by"] == "HUMAN_OPERATOR"
    assert approval["approval_label_consumed"] is False
    assert approval["approval_reuse_allowed"] is False
    assert approval["execution_allowed"] is True


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


def test_valid_response_records_index() -> None:
    module = load_module()

    category_index = module.validate_response(
        valid_response(),
        load_json(POLICY_PATH),
    )

    assert category_index["category_count"] == 2
    assert category_index["x_wp_total"] == 2
    assert category_index["x_wp_total_pages"] == 1
    assert category_index["category_selected"] is False
    assert (
        category_index[
            "automatic_selection_performed"
        ]
        is False
    )
    assert category_index["category_mapping_fixed"] is False
    assert category_index["categories"][1]["id"] == 27
    assert (
        category_index["categories"][1]["selected"]
        is False
    )


def test_missing_pagination_headers_block() -> None:
    module = load_module()
    response = valid_response()
    response["x_wp_total"] = None

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_WORDPRESS_CATEGORY_INDEX_"
                "PAGINATION_METADATA_MISSING"
            )
        )
    else:
        raise AssertionError(
            "missing pagination metadata was accepted"
        )


def test_multiple_pages_block() -> None:
    module = load_module()
    response = valid_response()
    response["x_wp_total"] = "150"
    response["x_wp_total_pages"] = "2"

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_WORDPRESS_CATEGORY_INDEX_"
                "PAGINATION_REQUIRED"
            )
        )
    else:
        raise AssertionError(
            "multi-page category index was accepted"
        )


def test_empty_index_blocks() -> None:
    module = load_module()
    response = valid_response()
    response["body"] = b"[]"
    response["response_bytes"] = 2
    response["x_wp_total"] = "0"
    response["x_wp_total_pages"] = "0"

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == "BLOCKED_WORDPRESS_CATEGORY_INDEX_EMPTY"
        )
    else:
        raise AssertionError(
            "empty category index was accepted"
        )


def test_invalid_category_id_blocks() -> None:
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
    response["response_bytes"] = len(response["body"])
    response["x_wp_total"] = "1"

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == "BLOCKED_WORDPRESS_INVALID_CATEGORY_ID"
        )
    else:
        raise AssertionError(
            "invalid category ID was accepted"
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
                "name": "漫画",
                "count": 2,
            }
        ],
        ensure_ascii=False,
    ).encode("utf-8")
    response["response_bytes"] = len(response["body"])

    try:
        module.validate_response(
            response,
            load_json(POLICY_PATH),
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_WORDPRESS_DUPLICATE_CATEGORY_SLUG"
            )
        )
    else:
        raise AssertionError(
            "duplicate category slug was accepted"
        )


def test_one_shot_lock_blocks_second_use(
    tmp_path: Path,
) -> None:
    module = load_module()
    approval = load_json(APPROVAL_PATH)
    lock_path = tmp_path / "one-shot.lock.json"

    module.reserve_one_shot(
        lock_path,
        approval,
    )

    try:
        module.reserve_one_shot(
            lock_path,
            approval,
        )
    except module.ControlledBlock as exc:
        assert (
            exc.status
            == (
                "BLOCKED_CATEGORY_INDEX_RECOVERY_"
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

    values = module.read_credentials(policy)

    assert set(values) == {
        "WORDPRESS_BASE_URL",
        "WORDPRESS_READONLY_USERNAME",
        "WORDPRESS_READONLY_APP_PASSWORD",
    }


def test_fake_transport_success_is_one_request(
    tmp_path: Path,
) -> None:
    module = load_module()

    credential_path = tmp_path / "credential.env"
    write_test_credentials(credential_path)

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
        assert "per_page=100" in kwargs["request_url"]
        assert "hide_empty=false" in kwargs["request_url"]
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
    assert result["http_request_attempt_count"] == 1
    assert (
        result["status"]
        == (
            "PASS_ONE_SHOT_ACTUAL_READ_ONLY_"
            "CATEGORY_INDEX_RECOVERY"
        )
    )
    assert result["category_count"] == 2
    assert result["category_selected"] is False
    assert result["category_mapping_fixed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["production_payload_modified"] is False
    assert (
        result[
            "ready_for_ls_new_batch_4g_2e_recovery_c"
        ]
        is True
    )
    assert "TEST_PASSWORD" not in serialized
    assert "TEST_USER" not in serialized


def test_fake_pagination_block_consumes_attempt(
    tmp_path: Path,
) -> None:
    module = load_module()

    credential_path = tmp_path / "credential.env"
    write_test_credentials(credential_path)

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
        response = valid_response()
        response["x_wp_total"] = "150"
        response["x_wp_total_pages"] = "2"
        return response

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
            "BLOCKED_WORDPRESS_CATEGORY_INDEX_"
            "PAGINATION_REQUIRED"
        )
    )
    assert (
        lock["state"]
        == "CONSUMED_COMPLETED_BLOCKED"
    )
    assert lock["approval_label_consumed"] is True
    assert lock["http_request_attempt_count"] == 1
