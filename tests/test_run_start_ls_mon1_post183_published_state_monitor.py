from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls_mon1_post183_published_state_monitor import (
    PUBLIC_REST_UNAVAILABLE_WARNING,
    STATUS_BAD_POST_CONFIRMATION,
    STATUS_BAD_STATUS_CONFIRMATION,
    STATUS_FAILED,
    STATUS_MISSING_FORBID_DELETE_FLAG,
    STATUS_MISSING_FORBID_POST119_FLAG,
    STATUS_MISSING_FORBID_POST183_UPDATE_FLAG,
    STATUS_MISSING_FORBID_NEW_POST_FLAG,
    STATUS_MISSING_FORBID_SCHEDULE_FLAG,
    STATUS_MISSING_NO_CREDENTIAL_READ_FLAG,
    STATUS_MISSING_NO_PUBLISH_FLAG,
    STATUS_MISSING_NO_ROLLBACK_FLAG,
    STATUS_MISSING_NO_WRITE_FLAG,
    STATUS_MISSING_PUBLIC_REST_GET_FLAG,
    STATUS_MISSING_PUBLIC_URL_GET_FLAG,
    STATUS_MISSING_RECORD_FLAG,
    STATUS_PASSED,
    main,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(path: Path, keys: tuple[str, ...], value) -> None:
    data = read_json(path)
    cur = data
    for key in keys[:-1]:
        cur = cur[key]
    cur[keys[-1]] = value
    write_json(path, data)


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls_close1_result": tmp_path / "exchange/runtime/ls_close1_result.json",
        "ls_close1_lock": tmp_path / "exchange/locks/ls_close1_lock.json",
        "ls_close1_run": tmp_path / "exchange/logs/ls_close1_run.json",
        "ls_close1_validation": tmp_path / "exchange/logs/ls_close1_validation.json",
        "ls6au_result": tmp_path / "exchange/runtime/ls6au_result.json",
        "ls6au_lock": tmp_path / "exchange/locks/ls6au_lock.json",
        "ls6au_validation": tmp_path / "exchange/logs/ls6au_validation.json",
        "monitor_output": tmp_path / "exchange/runtime/monitor_result.json",
        "monitor_lock": tmp_path / "exchange/locks/monitor_lock.json",
        "run_output": tmp_path / "exchange/logs/monitor_result.json",
        "report": tmp_path / "reports/monitor_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-MON-1",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "public_rest_url": "https://hoshido.jp/wp-json/wp/v2/posts/183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_status": "publish",
            },
            "required_previous_phase": {
                "ls_close1": {
                    "required_run_status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_PASSED_NO_EXECUTION",
                    "required_validation_status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_VALIDATED_NO_EXECUTION",
                    "required_production_status": "PUBLISHED_AND_VERIFIED_CLOSURE",
                    "required_completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
                    "required_post_id": 183,
                },
                "ls6au": {
                    "required_run_status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED",
                    "required_validation_status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED",
                    "required_production_status": "PUBLISHED_VERIFIED",
                    "required_post_id": 183,
                    "required_rest_returned_post_status": "publish",
                    "required_public_url_reachable": True,
                    "required_post_publish_verified": True,
                    "required_published_evidence_recorded": True,
                    "required_rollback_readiness_recorded": True,
                },
            },
            "monitor_policy": {
                "monitor_scope": "POST_183_ONLY",
                "monitor_window": "FIRST_24H_AFTER_PUBLISH",
                "monitor_checkpoint": "LS_MON_1_INITIAL_CHECKPOINT",
                "recommended_next_action": "CONTINUE_24H_GET_ONLY_MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
                "recommended_next_phase_options": ["LS-MON-2", "LS-NEXT-1", "LS-REUSE-1"],
            },
            "must_remain_false_flags": {
                "credential_env_read_executed": False,
                "credential_values_loaded_for_output": False,
                "credential_values_persisted": False,
                "credential_values_logged": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_generated": False,
                "authorization_header_output": False,
                "basic_auth_string_generated": False,
                "basic_auth_string_output": False,
                "wordpress_authenticated_api_call_executed": False,
                "wordpress_post_executed": False,
                "wordpress_put_executed": False,
                "wordpress_patch_executed": False,
                "wordpress_delete_executed": False,
                "wordpress_write_executed_by_this_phase": False,
                "wordpress_publish_executed_by_this_phase": False,
                "publish_executed_by_this_phase": False,
                "post119_update_executed": False,
                "post183_update_executed_by_this_phase": False,
                "wordpress_new_post_executed": False,
                "wordpress_content_update_executed": False,
                "wordpress_title_update_executed": False,
                "wordpress_meta_update_executed": False,
                "wordpress_schedule_executed": False,
                "future_schedule_executed": False,
                "delete_executed": False,
                "rollback_executed": False,
                "unpublish_executed": False,
                "draft_revert_executed": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "rerun_allowed": False,
                "publish_rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
            },
        },
    )

    close1_payload = {
        "status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_PASSED_NO_EXECUTION",
        "production_status": "PUBLISHED_AND_VERIFIED_CLOSURE",
        "completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
        "post_id": 183,
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "publish_executed_by_this_phase": False,
        "rollback_executed": False,
    }
    write_json(files["ls_close1_result"], close1_payload)
    write_json(files["ls_close1_run"], close1_payload)
    write_json(files["ls_close1_lock"], {"locked": True})
    write_json(
        files["ls_close1_validation"],
        {"status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_VALIDATED_NO_EXECUTION"},
    )

    ls6au_payload = {
        "status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED",
        "production_status": "PUBLISHED_VERIFIED",
        "post_id": 183,
        "rest_returned_post_status": "publish",
        "public_url_reachable": True,
        "post_publish_verified": True,
        "published_evidence_recorded": True,
        "rollback_readiness_recorded": True,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
    }
    write_json(files["ls6au_result"], ls6au_payload)
    write_json(files["ls6au_lock"], {"locked": True})
    write_json(files["ls6au_validation"], {"status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED"})

    return files


def build_argv(files: dict[str, Path], with_flags: bool = True) -> list[str]:
    argv = [
        "prog",
        "--policy",
        str(files["policy"]),
        "--ls-close1-result",
        str(files["ls_close1_result"]),
        "--ls-close1-lock",
        str(files["ls_close1_lock"]),
        "--ls-close1-run-result",
        str(files["ls_close1_run"]),
        "--ls-close1-validation-result",
        str(files["ls_close1_validation"]),
        "--ls6au-result",
        str(files["ls6au_result"]),
        "--ls6au-lock",
        str(files["ls6au_lock"]),
        "--ls6au-validation-result",
        str(files["ls6au_validation"]),
        "--monitor-output",
        str(files["monitor_output"]),
        "--monitor-lock-output",
        str(files["monitor_lock"]),
        "--output",
        str(files["run_output"]),
        "--report",
        str(files["report"]),
    ]
    if with_flags:
        argv.extend(
            [
                "--record-monitor-checkpoint",
                "--confirm-post-id",
                "183",
                "--confirm-expected-status",
                "publish",
                "--allow-public-url-get",
                "--allow-public-rest-get",
                "--require-no-credential-read",
                "--require-no-wordpress-write",
                "--require-no-publish",
                "--require-no-rollback",
                "--forbid-post119-update",
                "--forbid-post183-update",
                "--forbid-new-post",
                "--forbid-delete",
                "--forbid-schedule",
            ]
        )
    return argv


def mock_http(monkeypatch, *, url_status: int = 200, rest_status: int = 200, rest_payload: dict | None = None, url_exc: Exception | None = None, rest_exc: Exception | None = None) -> None:
    from scripts import run_start_ls_mon1_post183_published_state_monitor as target

    if rest_payload is None:
        rest_payload = {"id": 183, "status": "publish"}

    def fake_url(_url: str, timeout: float = 20.0) -> int:
        if url_exc is not None:
            raise url_exc
        return url_status

    def fake_rest(_url: str, timeout: float = 20.0) -> tuple[int, dict]:
        if rest_exc is not None:
            raise rest_exc
        return rest_status, dict(rest_payload)

    monkeypatch.setattr(target, "http_get_status", fake_url)
    monkeypatch.setattr(target, "http_get_json", fake_rest)


def run_case(monkeypatch, files: dict[str, Path], with_flags: bool = True) -> dict:
    mock_http(monkeypatch)
    monkeypatch.setattr("sys.argv", build_argv(files, with_flags=with_flags))
    rc = main()
    assert rc == 0
    return read_json(files["run_output"])


@pytest.mark.parametrize(
    "remove_flag,expected",
    [
        ("--record-monitor-checkpoint", STATUS_MISSING_RECORD_FLAG),
        ("--allow-public-url-get", STATUS_MISSING_PUBLIC_URL_GET_FLAG),
        ("--allow-public-rest-get", STATUS_MISSING_PUBLIC_REST_GET_FLAG),
        ("--require-no-credential-read", STATUS_MISSING_NO_CREDENTIAL_READ_FLAG),
        ("--require-no-wordpress-write", STATUS_MISSING_NO_WRITE_FLAG),
        ("--require-no-publish", STATUS_MISSING_NO_PUBLISH_FLAG),
        ("--require-no-rollback", STATUS_MISSING_NO_ROLLBACK_FLAG),
        ("--forbid-post119-update", STATUS_MISSING_FORBID_POST119_FLAG),
        ("--forbid-post183-update", STATUS_MISSING_FORBID_POST183_UPDATE_FLAG),
        ("--forbid-new-post", STATUS_MISSING_FORBID_NEW_POST_FLAG),
        ("--forbid-delete", STATUS_MISSING_FORBID_DELETE_FLAG),
        ("--forbid-schedule", STATUS_MISSING_FORBID_SCHEDULE_FLAG),
    ],
)
def test_1_to_14_missing_flags(monkeypatch, tmp_path: Path, remove_flag: str, expected: str) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch)
    argv = build_argv(files)
    argv.remove(remove_flag)
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == expected


def test_2_bad_post_confirmation(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch)
    argv = build_argv(files)
    argv[argv.index("--confirm-post-id") + 1] = "999"
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_POST_CONFIRMATION


def test_3_bad_status_confirmation(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch)
    argv = build_argv(files)
    argv[argv.index("--confirm-expected-status") + 1] = "draft"
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_STATUS_CONFIRMATION


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("ls_close1_validation", ("status",), "WRONG"),
        ("ls_close1_result", ("completion_status",), "WRONG"),
        ("ls_close1_result", ("wordpress_api_call_executed",), True),
        ("ls_close1_result", ("credential_env_read_executed",), True),
        ("ls_close1_result", ("publish_executed_by_this_phase",), True),
        ("ls_close1_result", ("rollback_executed",), True),
        ("ls6au_validation", ("status",), "WRONG"),
        ("ls6au_result", ("production_status",), "WRONG"),
        ("ls6au_result", ("rest_returned_post_status",), "draft"),
        ("ls6au_result", ("public_url_reachable",), False),
        ("ls6au_result", ("wordpress_post_executed",), True),
        ("ls6au_result", ("wordpress_write_executed_by_this_phase",), True),
    ],
)
def test_15_to_26_prerequisite_not_ready(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files[path_key], keys, value)
    if path_key == "ls_close1_result":
        write_json(files["ls_close1_run"], read_json(files[path_key]))
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_FAILED


@pytest.mark.parametrize("url_status", [404, 500])
def test_27_to_29_public_url_non_success_failed(monkeypatch, tmp_path: Path, url_status: int) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch, url_status=url_status)
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    out = read_json(files["run_output"])
    assert out["status"] == STATUS_FAILED


def test_27_public_url_get_fails(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch, url_exc=TimeoutError("timeout"))
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    out = read_json(files["run_output"])
    assert out["status"] == STATUS_FAILED


def test_30_public_rest_wrong_id_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch, rest_payload={"id": 999, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    out = read_json(files["run_output"])
    assert out["status"] == STATUS_FAILED


def test_31_public_rest_wrong_status_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch, rest_payload={"id": 183, "status": "draft"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    out = read_json(files["run_output"])
    assert out["status"] == STATUS_FAILED


def test_32_public_rest_unavailable_but_url_reachable_passed_with_warning(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch, rest_exc=ValueError("unavailable"))
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    out = read_json(files["run_output"])
    assert out["status"] == STATUS_PASSED
    assert out["public_rest_warning"] == PUBLIC_REST_UNAVAILABLE_WARNING
    assert out["post_publish_state_monitor_ok"] is True


def test_33_valid_monitor_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_PASSED


def test_34_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["monitor_output"].exists()


def test_35_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["monitor_lock"].exists()


def test_36_run_log_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["run_output"].exists()


def test_37_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["report"].exists()


@pytest.mark.parametrize(
    "key,expected",
    [
        ("public_url_get_executed", True),
        ("public_url_reachable", True),
        ("monitor_checkpoint_recorded", True),
        ("published_state_preserved", True),
        ("post_publish_state_monitor_ok", True),
        ("credential_env_read_executed", False),
        ("wordpress_authenticated_api_call_executed", False),
        ("wordpress_post_executed", False),
        ("wordpress_write_executed_by_this_phase", False),
        ("publish_executed_by_this_phase", False),
        ("rollback_executed", False),
        ("unpublish_executed", False),
        ("draft_revert_executed", False),
        ("post119_update_executed", False),
        ("post183_update_executed_by_this_phase", False),
        ("wordpress_new_post_executed", False),
        ("wordpress_content_update_executed", False),
        ("wordpress_title_update_executed", False),
        ("wordpress_meta_update_executed", False),
        ("delete_executed", False),
        ("future_schedule_executed", False),
        ("secret_length_output", False),
        ("secret_hash_output", False),
        ("recommended_next_action", "CONTINUE_24H_GET_ONLY_MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM"),
    ],
)
def test_38_to_55_result_field_expectations(monkeypatch, tmp_path: Path, key: str, expected) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out[key] == expected


def test_56_phase_and_mode_fields(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["phase"] == "LS-MON-1"
    assert out["execution_mode"] == "GET_ONLY_MONITOR_NO_CREDENTIAL_NO_WRITE"


def test_57_rest_fields_when_success(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["public_rest_reachable"] is True
    assert out["public_rest_returned_post_id"] == 183
    assert out["public_rest_returned_post_status"] == "publish"
    assert out["public_rest_status_verified"] is True


def test_58_lock_payload_status(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    lock = read_json(files["monitor_lock"])
    assert lock["locked"] is True
    assert "LOCKED_GET_ONLY" in lock["status"]


def test_59_run_output_matches_runtime_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert read_json(files["run_output"]) == read_json(files["monitor_output"])


def test_60_fail_lock_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mock_http(monkeypatch, url_status=500)
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    lock = read_json(files["monitor_lock"])
    assert lock["locked"] is False


def test_61_source_has_no_requests_post() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.post" not in src


def test_62_source_has_no_requests_put() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.put" not in src


def test_63_source_has_no_requests_patch() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.patch" not in src


def test_64_source_has_no_requests_delete() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.delete" not in src


def test_65_source_has_no_credential_env_open() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "credential.env" not in src


def test_66_source_has_no_authorization_output() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "Authorization:" not in src


def test_67_source_has_no_basic_output() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "Basic " not in src


def test_68_source_has_no_base64_usage() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/run_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "base64" not in src
    assert "b64encode" not in src
