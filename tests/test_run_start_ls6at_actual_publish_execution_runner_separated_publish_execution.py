from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6at_actual_publish_execution_runner_separated_publish_execution import (
    STATUS_BAD_POST_CONFIRMATION,
    STATUS_BAD_STATUS_CONFIRMATION,
    STATUS_FAILED,
    STATUS_FAILED_ALREADY_PUBLISHED,
    STATUS_MISSING_ACTUAL_PUBLISH_ALLOW_FLAG,
    STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG,
    STATUS_MISSING_EXECUTE_FLAG,
    STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG,
    STATUS_MISSING_FORBID_DELETE_FLAG,
    STATUS_MISSING_FORBID_NEW_POST_FLAG,
    STATUS_MISSING_FORBID_POST119_FLAG,
    STATUS_MISSING_FORBID_SCHEDULE_FLAG,
    STATUS_MISSING_NO_SECRET_OUTPUT_FLAG,
    STATUS_MISSING_RUNNER_EXECUTION_ALLOW_FLAG,
    STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG,
    STATUS_MISSING_WORDPRESS_POST_ALLOW_FLAG,
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


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self) -> dict:
        return dict(self._payload)


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6as_template": tmp_path / "exchange/logs/ls6as_template.json",
        "ls6as_ready": tmp_path / "exchange/logs/ls6as_ready.json",
        "ls6as_final": tmp_path / "exchange/human_review/ls6as_final.json",
        "ls6ar_result": tmp_path / "exchange/runtime/ls6ar_result.json",
        "ls6ar_lock": tmp_path / "exchange/locks/ls6ar_lock.json",
        "ls6ar_validation": tmp_path / "exchange/logs/ls6ar_validation.json",
        "credential_env": tmp_path / "etc/credential.env",
        "runtime_output": tmp_path / "exchange/runtime/ls6at_result.json",
        "lock_output": tmp_path / "exchange/locks/ls6at_lock.json",
        "run_output": tmp_path / "exchange/logs/ls6at_result.json",
        "report": tmp_path / "reports/ls6at_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AT",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_pre_publish_status": "draft",
                "target_status": "publish",
            },
            "credential_policy": {
                "accepted_site_url_keys": ["WORDPRESS_SITE_URL", "WORDPRESS_BASE_URL"],
                "required_key_names": ["WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
            },
            "required_previous_phase": {
                "ls6as": {
                    "required_template_status": "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_TEMPLATE_READY_NO_PUBLISH",
                    "required_ready_status": "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_READY_NO_PUBLISH",
                    "required_command_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
                    "required_final_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_EXECUTION_PHASE_ONLY",
                    "required_final_command_consumed": False,
                    "required_final_command_allows_execution_by_this_phase": False,
                    "required_final_command_approved_for_later_separated_phase": True,
                    "required_separate_publish_execution_phase": True,
                    "required_actual_publish_execution_runner_separated_execution": True,
                    "required_publish_execution_still_blocked": True,
                },
                "ls6ar": {
                    "required_validation_status": "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
                    "required_credential_preflight_ready": True,
                    "required_credential_preflight_consumed": False,
                },
            },
            "actual_publish_execution_policy": {
                "actual_publish_execution_allowed_by_this_phase": True,
                "actual_runner_execution_allowed_by_this_phase": True,
                "manual_publish_execution_allowed_by_this_phase": False,
                "requires_pre_publish_status": "draft",
            },
            "next_phase": {
                "phase": "LS-6AU",
                "requires_post_publish_verification": True,
                "requires_published_evidence": True,
                "requires_rollback_readiness_record": True,
            },
        },
    )

    write_json(
        files["ls6as_template"],
        {"status": "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_TEMPLATE_READY_NO_PUBLISH"},
    )
    write_json(
        files["ls6as_ready"],
        {
            "status": "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_READY_NO_PUBLISH",
            "command_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execution_runner_final_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_EXECUTION_PHASE_ONLY",
            "actual_publish_execution_runner_final_command_consumed": False,
            "actual_publish_execution_runner_final_command_allows_execution_by_this_phase": False,
            "actual_publish_execution_runner_final_command_approved_for_later_separated_phase": True,
            "actual_publish_execution_runner_separate_publish_execution_phase_required": True,
            "requires_actual_publish_execution_runner_separated_execution": True,
            "publish_execution_still_blocked": True,
        },
    )
    write_json(
        files["ls6as_final"],
        {
            "command_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "final_command": {
                "actual_publish_execution_runner_final_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_EXECUTION_PHASE_ONLY"
            },
        },
    )
    write_json(
        files["ls6ar_result"],
        {
            "actual_publish_execution_runner_credential_preflight_ready": True,
            "actual_publish_execution_runner_credential_preflight_consumed": False,
            "ls6aq_final_boundary_validated": True,
        },
    )
    write_json(files["ls6ar_lock"], {"locked": True})
    write_json(
        files["ls6ar_validation"],
        {"status": "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATED_NO_PUBLISH"},
    )

    files["credential_env"].parent.mkdir(parents=True, exist_ok=True)
    files["credential_env"].write_text(
        "WORDPRESS_SITE_URL=https://example.com\n"
        "WORDPRESS_USERNAME=ai_publisher\n"
        "WORDPRESS_APP_PASSWORD=dummy\n",
        encoding="utf-8",
    )
    return files


def build_argv(files: dict[str, Path], full_flags: bool = True) -> list[str]:
    argv = [
        "prog",
        "--policy",
        str(files["policy"]),
        "--ls6as-template-result",
        str(files["ls6as_template"]),
        "--ls6as-ready-result",
        str(files["ls6as_ready"]),
        "--ls6as-final-command-result",
        str(files["ls6as_final"]),
        "--ls6ar-credential-preflight-result",
        str(files["ls6ar_result"]),
        "--ls6ar-credential-preflight-lock",
        str(files["ls6ar_lock"]),
        "--ls6ar-validation-result",
        str(files["ls6ar_validation"]),
        "--credential-env-path",
        str(files["credential_env"]),
        "--publish-execution-output",
        str(files["runtime_output"]),
        "--publish-execution-lock-output",
        str(files["lock_output"]),
        "--output",
        str(files["run_output"]),
        "--report",
        str(files["report"]),
    ]
    if full_flags:
        argv.extend(
            [
                "--execute-separated-publish",
                "--confirm-post-id",
                "183",
                "--confirm-current-status",
                "draft",
                "--confirm-target-status",
                "publish",
                "--allow-credential-env-read",
                "--allow-wordpress-get",
                "--allow-wordpress-post",
                "--allow-actual-publish",
                "--allow-runner-execution",
                "--require-no-secret-output",
                "--forbid-post119-update",
                "--forbid-content-update",
                "--forbid-new-post",
                "--forbid-delete",
                "--forbid-schedule",
            ]
        )
    return argv


def patch_wp(monkeypatch, pre: dict, post: dict, verify: dict, get_raises=False, post_raises=False):
    calls = {"get": 0, "post": 0}

    def fake_get(*args, **kwargs):
        calls["get"] += 1
        if get_raises:
            raise RuntimeError("WordPress GET exception")
        if calls["get"] == 1:
            return FakeResponse(pre)
        return FakeResponse(verify)

    def fake_post(*args, **kwargs):
        calls["post"] += 1
        if post_raises:
            raise RuntimeError("WordPress POST exception")
        return FakeResponse(post)

    monkeypatch.setattr(
        "scripts.run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "scripts.run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.requests.post",
        fake_post,
    )


def run_case(monkeypatch, files: dict[str, Path], full_flags: bool = True) -> dict:
    patch_wp(
        monkeypatch,
        pre={"id": 183, "status": "draft"},
        post={"id": 183, "status": "publish"},
        verify={"id": 183, "status": "publish"},
    )
    monkeypatch.setattr("sys.argv", build_argv(files, full_flags=full_flags))
    rc = main()
    assert rc == 0
    return read_json(files["run_output"])


@pytest.mark.parametrize(
    "remove_flag,expected",
    [
        ("--execute-separated-publish", STATUS_MISSING_EXECUTE_FLAG),
        ("--allow-credential-env-read", STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG),
        ("--allow-wordpress-get", STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG),
        ("--allow-wordpress-post", STATUS_MISSING_WORDPRESS_POST_ALLOW_FLAG),
        ("--allow-actual-publish", STATUS_MISSING_ACTUAL_PUBLISH_ALLOW_FLAG),
        ("--allow-runner-execution", STATUS_MISSING_RUNNER_EXECUTION_ALLOW_FLAG),
        ("--require-no-secret-output", STATUS_MISSING_NO_SECRET_OUTPUT_FLAG),
        ("--forbid-post119-update", STATUS_MISSING_FORBID_POST119_FLAG),
        ("--forbid-content-update", STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG),
        ("--forbid-new-post", STATUS_MISSING_FORBID_NEW_POST_FLAG),
        ("--forbid-delete", STATUS_MISSING_FORBID_DELETE_FLAG),
        ("--forbid-schedule", STATUS_MISSING_FORBID_SCHEDULE_FLAG),
    ],
)
def test_1_to_15_missing_required_flags(monkeypatch, tmp_path: Path, remove_flag: str, expected: str) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv.remove(remove_flag)
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", argv)
    main()
    out = read_json(files["run_output"])
    assert out["status"] == expected


def test_2_bad_confirm_post_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    idx = argv.index("--confirm-post-id")
    argv[idx + 1] = "999"
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_POST_CONFIRMATION


def test_3_bad_confirm_current_status(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    idx = argv.index("--confirm-current-status")
    argv[idx + 1] = "publish"
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_STATUS_CONFIRMATION


def test_4_bad_confirm_target_status(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    idx = argv.index("--confirm-target-status")
    argv[idx + 1] = "draft"
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_STATUS_CONFIRMATION


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("ls6as_ready", ("status",), "WRONG"),
        ("ls6as_ready", ("actual_publish_execution_runner_final_command_label",), "WRONG"),
        ("ls6as_ready", ("actual_publish_execution_runner_final_command_consumed",), True),
        ("ls6as_ready", ("actual_publish_execution_runner_final_command_approved_for_later_separated_phase",), False),
        ("ls6as_ready", ("actual_publish_execution_runner_separate_publish_execution_phase_required",), False),
        ("ls6ar_validation", ("status",), "WRONG"),
        ("ls6ar_result", ("actual_publish_execution_runner_credential_preflight_ready",), False),
        ("ls6ar_result", ("actual_publish_execution_runner_credential_preflight_consumed",), True),
    ],
)
def test_16_to_23_previous_phase_mismatch(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files[path_key], keys, value)
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_FAILED


def test_24_credential_env_missing(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["credential_env"].unlink()
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_FAILED


def test_25_credential_env_required_key_missing(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["credential_env"].write_text("WORDPRESS_SITE_URL=https://example.com\nWORDPRESS_USERNAME=ai\n", encoding="utf-8")
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_FAILED


def test_26_credential_env_required_key_empty(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["credential_env"].write_text(
        "WORDPRESS_SITE_URL=https://example.com\nWORDPRESS_USERNAME=ai\nWORDPRESS_APP_PASSWORD=\n",
        encoding="utf-8",
    )
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_FAILED


def test_27_pre_get_wrong_post_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 999, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_28_pre_get_publish(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED_ALREADY_PUBLISHED


def test_29_pre_get_non_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "pending"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_30_post_response_wrong_post_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 999, "status": "publish"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_31_post_response_non_publish(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_32_post_get_wrong_post_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 999, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_33_post_get_non_publish(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "draft"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_34_wordpress_get_exception(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"}, get_raises=True)
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_35_wordpress_post_exception(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_wp(monkeypatch, {"id": 183, "status": "draft"}, {"id": 183, "status": "publish"}, {"id": 183, "status": "publish"}, post_raises=True)
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_36_valid_execution_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_PASSED


def test_37_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["runtime_output"].exists()


def test_38_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["lock_output"].exists()


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
        ("pre_publish_returned_post_status", "draft"),
        ("post_publish_returned_post_status", "publish"),
        ("publish_executed", True),
        ("wordpress_api_call_executed", True),
        ("wordpress_get_executed", True),
        ("wordpress_post_executed", True),
        ("wordpress_put_executed", False),
        ("wordpress_patch_executed", False),
        ("wordpress_delete_executed", False),
        ("post119_update_executed", False),
        ("content_update_executed", False),
        ("title_update_executed", False),
        ("meta_update_executed", False),
        ("new_post_created", False),
        ("credential_value_output", False),
        ("credential_value_persisted", False),
        ("secret_length_output", False),
        ("secret_hash_output", False),
        ("manual_publish_executed", False),
    ],
)
def test_41_to_59_result_field_expectations(monkeypatch, tmp_path: Path, key: str, expected) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out[key] == expected


def test_60_result_next_phase_ls6au(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["next_phase"]["phase"] == "LS-6AU"
