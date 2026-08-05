from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls_close1_one_shot_publish_chain_closure import (
    STATUS_BAD_COMPLETION_CONFIRMATION,
    STATUS_BAD_POST_CONFIRMATION,
    STATUS_FAILED,
    STATUS_MISSING_FORBID_DELETE_FLAG,
    STATUS_MISSING_FORBID_POST119_FLAG,
    STATUS_MISSING_FORBID_POST183_UPDATE_FLAG,
    STATUS_MISSING_FORBID_NEW_POST_FLAG,
    STATUS_MISSING_FORBID_SCHEDULE_FLAG,
    STATUS_MISSING_NO_CREDENTIAL_READ_FLAG,
    STATUS_MISSING_NO_PUBLISH_FLAG,
    STATUS_MISSING_NO_ROLLBACK_FLAG,
    STATUS_MISSING_NO_WORDPRESS_API_FLAG,
    STATUS_MISSING_REGISTER_FLAG,
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
        "ls6au_result": tmp_path / "exchange/runtime/ls6au_result.json",
        "ls6au_lock": tmp_path / "exchange/locks/ls6au_lock.json",
        "ls6au_run": tmp_path / "exchange/logs/ls6au_result.json",
        "ls6au_validation": tmp_path / "exchange/logs/ls6au_validation.json",
        "ls6at_result": tmp_path / "exchange/runtime/ls6at_result.json",
        "ls6at_lock": tmp_path / "exchange/locks/ls6at_lock.json",
        "ls6at_validation": tmp_path / "exchange/logs/ls6at_validation.json",
        "closure_output": tmp_path / "exchange/runtime/closure_result.json",
        "closure_lock": tmp_path / "exchange/locks/closure_lock.json",
        "run_output": tmp_path / "exchange/logs/closure_result.json",
        "report": tmp_path / "reports/closure_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-CLOSE-1",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "final_status": "publish",
            },
            "completion_state": {
                "status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
                "post_id": 183,
                "published": True,
                "post_publish_verified": True,
                "published_evidence_recorded": True,
                "rollback_readiness_recorded": True,
                "closure_registered": True,
                "publish_chain_closed": True,
                "recommended_next_action": "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
            },
            "required_previous_phase": {
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
                    "required_completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_PUBLISHED_AND_VERIFIED",
                    "required_no_wordpress_write_by_ls6au": True,
                    "required_no_publish_by_ls6au": True,
                    "required_no_rollback": True,
                    "required_no_unpublish": True,
                    "required_no_draft_revert": True,
                },
                "ls6at": {
                    "required_run_status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED",
                    "required_validation_status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED",
                    "required_production_status": "PUBLISHED",
                    "required_post_id": 183,
                    "required_pre_publish_status": "draft",
                    "required_post_publish_status": "publish",
                    "required_updated_post_id": 183,
                    "required_updated_fields": ["status"],
                    "required_updated_status": "publish",
                    "required_no_post119_update": True,
                    "required_no_new_post": True,
                    "required_no_content_update": True,
                    "required_no_title_update": True,
                    "required_no_meta_update": True,
                    "required_no_delete": True,
                },
            },
            "closure_policy": {
                "start_ls_one_shot_publish_chain_closed": True,
                "closure_registration_required": True,
                "closure_registration_allowed_by_this_phase": True,
                "closure_registration_executed": True,
                "closure_lock_required": True,
                "published_state_preserved": True,
                "post_publish_verified": True,
                "published_evidence_recorded": True,
                "rollback_readiness_recorded": True,
                "rerun_allowed": False,
                "ls6at_rerun_allowed": False,
                "ls6au_rerun_allowed": False,
                "publish_rerun_allowed": False,
                "wordpress_write_allowed_by_this_phase": False,
                "wordpress_api_call_allowed_by_this_phase": False,
                "credential_env_read_allowed_by_this_phase": False,
                "rollback_execution_allowed_by_this_phase": False,
                "unpublish_execution_allowed_by_this_phase": False,
                "draft_revert_execution_allowed_by_this_phase": False,
                "recommended_next_action": "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
                "recommended_next_phase_options": ["LS-MON-1", "LS-NEXT-1", "LS-REUSE-1"],
            },
            "must_remain_false_flags": {
                "wordpress_api_call_executed": False,
                "wordpress_get_executed": False,
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
                "credential_env_read_executed": False,
                "credential_values_loaded_for_output": False,
                "credential_values_persisted": False,
                "credential_values_logged": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_output": False,
                "basic_auth_string_output": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
            },
        },
    )

    write_json(
        files["ls6au_result"],
        {
            "status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED",
            "production_status": "PUBLISHED_VERIFIED",
            "post_id": 183,
            "rest_returned_post_status": "publish",
            "public_url_reachable": True,
            "post_publish_verified": True,
            "published_evidence_recorded": True,
            "rollback_readiness_recorded": True,
            "rollback_executed": False,
            "unpublish_executed": False,
            "draft_revert_executed": False,
            "wordpress_post_executed": False,
            "wordpress_write_executed_by_this_phase": False,
            "publish_executed_by_this_phase": False,
            "post119_update_executed": False,
            "credential_env_read_executed": False,
            "credential_values_loaded_for_output": False,
            "credential_values_persisted": False,
            "credential_values_logged": False,
            "credential_value_output": False,
            "credential_value_persisted": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
            "basic_auth_string_output": False,
            "allowed_post_id_only": True,
            "write_scope_verified_as_status_only_from_ls6at": True,
            "no_write_executed_by_this_phase": True,
            "start_ls_one_shot_publish_chain_closed": True,
            "completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_PUBLISHED_AND_VERIFIED",
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "recommended_next_action": "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
        },
    )
    write_json(files["ls6au_run"], read_json(files["ls6au_result"]))
    write_json(files["ls6au_validation"], {"status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED"})
    write_json(files["ls6au_lock"], {"locked": True})

    write_json(
        files["ls6at_result"],
        {
            "status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED",
            "production_status": "PUBLISHED",
            "post_id": 183,
            "post_publish_returned_post_status": "publish",
            "updated_post_id": 183,
            "updated_fields": ["status"],
            "updated_status": "publish",
            "post119_update_executed": False,
            "new_post_created": False,
            "content_update_executed": False,
            "title_update_executed": False,
            "meta_update_executed": False,
            "delete_executed": False,
        },
    )
    write_json(files["ls6at_lock"], {"locked": True})
    write_json(files["ls6at_validation"], {"status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED"})

    return files


def build_argv(files: dict[str, Path], with_flags: bool = True) -> list[str]:
    argv = [
        "prog",
        "--policy",
        str(files["policy"]),
        "--ls6au-result",
        str(files["ls6au_result"]),
        "--ls6au-lock",
        str(files["ls6au_lock"]),
        "--ls6au-run-result",
        str(files["ls6au_run"]),
        "--ls6au-validation-result",
        str(files["ls6au_validation"]),
        "--ls6at-result",
        str(files["ls6at_result"]),
        "--ls6at-lock",
        str(files["ls6at_lock"]),
        "--ls6at-validation-result",
        str(files["ls6at_validation"]),
        "--closure-output",
        str(files["closure_output"]),
        "--closure-lock-output",
        str(files["closure_lock"]),
        "--output",
        str(files["run_output"]),
        "--report",
        str(files["report"]),
    ]
    if with_flags:
        argv.extend(
            [
                "--register-chain-closure",
                "--confirm-post-id",
                "183",
                "--confirm-completion-status",
                "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
                "--require-no-wordpress-api",
                "--require-no-credential-read",
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


def run_case(monkeypatch, files: dict[str, Path], with_flags: bool = True) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, with_flags=with_flags))
    rc = main()
    assert rc == 0
    return read_json(files["run_output"])


@pytest.mark.parametrize(
    "remove_flag,expected",
    [
        ("--register-chain-closure", STATUS_MISSING_REGISTER_FLAG),
        ("--require-no-wordpress-api", STATUS_MISSING_NO_WORDPRESS_API_FLAG),
        ("--require-no-credential-read", STATUS_MISSING_NO_CREDENTIAL_READ_FLAG),
        ("--require-no-publish", STATUS_MISSING_NO_PUBLISH_FLAG),
        ("--require-no-rollback", STATUS_MISSING_NO_ROLLBACK_FLAG),
        ("--forbid-post119-update", STATUS_MISSING_FORBID_POST119_FLAG),
        ("--forbid-post183-update", STATUS_MISSING_FORBID_POST183_UPDATE_FLAG),
        ("--forbid-new-post", STATUS_MISSING_FORBID_NEW_POST_FLAG),
        ("--forbid-delete", STATUS_MISSING_FORBID_DELETE_FLAG),
        ("--forbid-schedule", STATUS_MISSING_FORBID_SCHEDULE_FLAG),
    ],
)
def test_1_to_12_missing_flags(monkeypatch, tmp_path: Path, remove_flag: str, expected: str) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv.remove(remove_flag)
    monkeypatch.setattr("sys.argv", argv)
    rc = main()
    assert rc == 0
    assert read_json(files["run_output"])["status"] == expected


def test_2_bad_post_confirmation(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv[argv.index("--confirm-post-id") + 1] = "999"
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_POST_CONFIRMATION


def test_3_bad_completion_confirmation(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv[argv.index("--confirm-completion-status") + 1] = "WRONG"
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_COMPLETION_CONFIRMATION


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("ls6au_validation", ("status",), "WRONG"),
        ("ls6au_result", ("production_status",), "WRONG"),
        ("ls6au_result", ("completion_status",), "WRONG"),
        ("ls6au_result", ("post_publish_verified",), False),
        ("ls6au_result", ("published_evidence_recorded",), False),
        ("ls6au_result", ("rollback_readiness_recorded",), False),
        ("ls6au_result", ("wordpress_post_executed",), True),
        ("ls6au_result", ("wordpress_write_executed_by_this_phase",), True),
        ("ls6au_result", ("publish_executed_by_this_phase",), True),
        ("ls6au_result", ("rollback_executed",), True),
        ("ls6au_result", ("unpublish_executed",), True),
        ("ls6au_result", ("draft_revert_executed",), True),
        ("ls6at_validation", ("status",), "WRONG"),
        ("ls6at_result", ("production_status",), "WRONG"),
        ("ls6at_result", ("updated_post_id",), 999),
        ("ls6at_result", ("updated_fields",), ["title"]),
        ("ls6at_result", ("updated_status",), "draft"),
        ("ls6at_result", ("post119_update_executed",), True),
        ("ls6at_result", ("new_post_created",), True),
        ("ls6at_result", ("content_update_executed",), True),
        ("ls6at_result", ("title_update_executed",), True),
        ("ls6at_result", ("meta_update_executed",), True),
        ("ls6at_result", ("delete_executed",), True),
    ],
)
def test_13_to_35_prereq_checks(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files[path_key], keys, value)
    if path_key == "ls6au_result":
        write_json(files["ls6au_run"], read_json(files[path_key]))
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_FAILED


def test_36_valid_closure_registration_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_PASSED


def test_37_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["closure_output"].exists()


def test_38_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["closure_lock"].exists()


def test_39_run_log_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["run_output"].exists()


def test_40_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["report"].exists()


@pytest.mark.parametrize(
    "key,expected",
    [
        ("closure_registration_executed", True),
        ("start_ls_one_shot_publish_chain_closed", True),
        ("published_state_preserved", True),
        ("post_publish_verified", True),
        ("published_evidence_recorded", True),
        ("rollback_readiness_recorded", True),
        ("wordpress_api_call_executed", False),
        ("wordpress_get_executed", False),
        ("wordpress_post_executed", False),
        ("wordpress_write_executed_by_this_phase", False),
        ("publish_executed_by_this_phase", False),
        ("credential_env_read_executed", False),
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
        ("rerun_allowed", False),
        ("ls6at_rerun_allowed", False),
        ("ls6au_rerun_allowed", False),
        ("publish_rerun_allowed", False),
        ("completion_status", "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED"),
        ("recommended_next_action", "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM"),
    ],
)
def test_41_to_64_result_field_expectations(monkeypatch, tmp_path: Path, key: str, expected) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out[key] == expected
