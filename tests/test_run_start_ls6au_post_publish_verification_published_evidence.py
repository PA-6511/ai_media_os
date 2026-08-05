from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6au_post_publish_verification_published_evidence import (
    STATUS_BAD_POST_CONFIRMATION,
    STATUS_BAD_STATUS_CONFIRMATION,
    STATUS_FAILED,
    STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG,
    STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG,
    STATUS_MISSING_FORBID_DELETE_FLAG,
    STATUS_MISSING_FORBID_NEW_POST_FLAG,
    STATUS_MISSING_FORBID_POST119_FLAG,
    STATUS_MISSING_FORBID_ROLLBACK_FLAG,
    STATUS_MISSING_FORBID_SCHEDULE_FLAG,
    STATUS_MISSING_NO_SECRET_OUTPUT_FLAG,
    STATUS_MISSING_NO_WRITE_FLAG,
    STATUS_MISSING_PUBLIC_URL_GET_ALLOW_FLAG,
    STATUS_MISSING_VERIFY_FLAG,
    STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG,
    STATUS_NOT_READY_PREREQ,
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
    def __init__(self, payload: dict | None = None, status_code: int = 200) -> None:
        self.payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self) -> dict:
        return dict(self.payload)


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6at_result": tmp_path / "exchange/runtime/ls6at_result.json",
        "ls6at_lock": tmp_path / "exchange/locks/ls6at_lock.json",
        "ls6at_run": tmp_path / "exchange/logs/ls6at_result.json",
        "ls6at_validation": tmp_path / "exchange/logs/ls6at_validation.json",
        "credential_env": tmp_path / "etc/credential.env",
        "runtime_output": tmp_path / "exchange/runtime/ls6au_result.json",
        "lock_output": tmp_path / "exchange/locks/ls6au_lock.json",
        "run_output": tmp_path / "exchange/logs/ls6au_result.json",
        "report": tmp_path / "reports/ls6au_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AU",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_status": "publish",
            },
            "credential_policy": {
                "accepted_site_url_keys": ["WORDPRESS_SITE_URL", "WORDPRESS_BASE_URL"],
                "required_key_names": ["WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
            },
            "required_previous_phase": {
                "ls6at": {
                    "required_run_status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED",
                    "required_validation_status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED",
                    "required_production_status": "PUBLISHED",
                    "required_post_id": 183,
                    "required_post_publish_status": "publish",
                    "required_updated_post_id": 183,
                    "required_updated_fields": ["status"],
                    "required_updated_status": "publish",
                }
            },
        },
    )

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
            "content_update_executed": False,
            "title_update_executed": False,
            "meta_update_executed": False,
            "new_post_created": False,
            "delete_executed": False,
            "future_schedule_executed": False,
            "credential_value_output": False,
        },
    )
    write_json(files["ls6at_run"], read_json(files["ls6at_result"]))
    write_json(files["ls6at_lock"], {"locked": True})
    write_json(
        files["ls6at_validation"],
        {"status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED"},
    )

    files["credential_env"].parent.mkdir(parents=True, exist_ok=True)
    files["credential_env"].write_text(
        "WORDPRESS_SITE_URL=https://example.com\nWORDPRESS_USERNAME=ai\nWORDPRESS_APP_PASSWORD=dummy\n",
        encoding="utf-8",
    )
    return files


def build_argv(files: dict[str, Path], with_flags: bool = True) -> list[str]:
    argv = [
        "prog",
        "--policy",
        str(files["policy"]),
        "--ls6at-publish-execution-result",
        str(files["ls6at_result"]),
        "--ls6at-publish-execution-lock",
        str(files["ls6at_lock"]),
        "--ls6at-run-result",
        str(files["ls6at_run"]),
        "--ls6at-validation-result",
        str(files["ls6at_validation"]),
        "--credential-env-path",
        str(files["credential_env"]),
        "--post-publish-verification-output",
        str(files["runtime_output"]),
        "--post-publish-verification-lock-output",
        str(files["lock_output"]),
        "--output",
        str(files["run_output"]),
        "--report",
        str(files["report"]),
    ]
    if with_flags:
        argv.extend(
            [
                "--verify-post-publish",
                "--confirm-post-id",
                "183",
                "--confirm-expected-status",
                "publish",
                "--allow-credential-env-read",
                "--allow-wordpress-get",
                "--allow-public-url-get",
                "--require-no-wordpress-write",
                "--require-no-secret-output",
                "--forbid-post119-update",
                "--forbid-content-update",
                "--forbid-new-post",
                "--forbid-delete",
                "--forbid-schedule",
                "--forbid-rollback-execution",
            ]
        )
    return argv


def patch_get(monkeypatch, rest_payload: dict | None = None, public_status: int = 200, raise_public: bool = False):
    def fake_get(url, *args, **kwargs):
        if "wp-json" in str(url):
            return FakeResponse(rest_payload or {"id": 183, "status": "publish"}, 200)
        if raise_public:
            raise RuntimeError("public URL GET fails")
        return FakeResponse({}, public_status)

    monkeypatch.setattr(
        "scripts.run_start_ls6au_post_publish_verification_published_evidence.requests.get",
        fake_get,
    )


def run_case(monkeypatch, files: dict[str, Path], with_flags: bool = True) -> dict:
    patch_get(monkeypatch)
    monkeypatch.setattr("sys.argv", build_argv(files, with_flags=with_flags))
    rc = main()
    assert rc == 0
    return read_json(files["run_output"])


@pytest.mark.parametrize(
    "remove_flag,expected",
    [
        ("--verify-post-publish", STATUS_MISSING_VERIFY_FLAG),
        ("--allow-credential-env-read", STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG),
        ("--allow-wordpress-get", STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG),
        ("--allow-public-url-get", STATUS_MISSING_PUBLIC_URL_GET_ALLOW_FLAG),
        ("--require-no-wordpress-write", STATUS_MISSING_NO_WRITE_FLAG),
        ("--require-no-secret-output", STATUS_MISSING_NO_SECRET_OUTPUT_FLAG),
        ("--forbid-post119-update", STATUS_MISSING_FORBID_POST119_FLAG),
        ("--forbid-content-update", STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG),
        ("--forbid-new-post", STATUS_MISSING_FORBID_NEW_POST_FLAG),
        ("--forbid-delete", STATUS_MISSING_FORBID_DELETE_FLAG),
        ("--forbid-schedule", STATUS_MISSING_FORBID_SCHEDULE_FLAG),
        ("--forbid-rollback-execution", STATUS_MISSING_FORBID_ROLLBACK_FLAG),
    ],
)
def test_1_and_4_to_14_missing_flags(monkeypatch, tmp_path: Path, remove_flag: str, expected: str) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv.remove(remove_flag)
    patch_get(monkeypatch)
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == expected


def test_2_bad_confirm_post_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv[argv.index("--confirm-post-id") + 1] = "999"
    patch_get(monkeypatch)
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_POST_CONFIRMATION


def test_3_bad_confirm_expected_status(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv[argv.index("--confirm-expected-status") + 1] = "draft"
    patch_get(monkeypatch)
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["run_output"])["status"] == STATUS_BAD_STATUS_CONFIRMATION


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("ls6at_validation", ("status",), "WRONG"),
        ("ls6at_result", ("production_status",), "NO_PUBLISH"),
        ("ls6at_result", ("post_publish_returned_post_status",), "draft"),
        ("ls6at_result", ("updated_post_id",), 999),
        ("ls6at_result", ("updated_fields",), ["status", "title"]),
        ("ls6at_result", ("post119_update_executed",), True),
        ("ls6at_result", ("content_update_executed",), True),
        ("ls6at_result", ("title_update_executed",), True),
        ("ls6at_result", ("meta_update_executed",), True),
        ("ls6at_result", ("new_post_created",), True),
        ("ls6at_result", ("delete_executed",), True),
        ("ls6at_result", ("credential_value_output",), True),
    ],
)
def test_15_to_26_ls6at_prereq_not_ready(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files[path_key], keys, value)
    if path_key == "ls6at_result":
        write_json(files["ls6at_run"], read_json(files["ls6at_result"]))
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY_PREREQ


def test_27_credential_env_missing(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["credential_env"].unlink()
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY_PREREQ


def test_28_credential_env_required_key_missing(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["credential_env"].write_text("WORDPRESS_SITE_URL=https://example.com\nWORDPRESS_USERNAME=ai\n", encoding="utf-8")
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY_PREREQ


def test_29_credential_env_required_key_empty(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["credential_env"].write_text(
        "WORDPRESS_SITE_URL=https://example.com\nWORDPRESS_USERNAME=ai\nWORDPRESS_APP_PASSWORD=\n",
        encoding="utf-8",
    )
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY_PREREQ


def test_30_rest_get_wrong_post_id_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_get(monkeypatch, rest_payload={"id": 999, "status": "publish"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_31_rest_get_non_publish_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_get(monkeypatch, rest_payload={"id": 183, "status": "draft"})
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_32_public_url_get_fails(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_get(monkeypatch, raise_public=True)
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_33_public_url_returns_404(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    patch_get(monkeypatch, public_status=404)
    monkeypatch.setattr("sys.argv", build_argv(files))
    main()
    assert read_json(files["run_output"])["status"] == STATUS_FAILED


def test_34_valid_verification_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["status"] == STATUS_PASSED


def test_35_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["runtime_output"].exists()


def test_36_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["lock_output"].exists()


def test_37_run_log_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["run_output"].exists()


def test_38_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_case(monkeypatch, files)
    assert files["report"].exists()


def test_39_result_keeps_rest_status_publish(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["rest_returned_post_status"] == "publish"


def test_40_result_keeps_public_url_reachable_true(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["public_url_reachable"] is True


def test_41_result_keeps_post_publish_verified_true(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["post_publish_verified"] is True


def test_42_result_keeps_published_evidence_recorded_true(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["published_evidence_recorded"] is True


def test_43_result_keeps_rollback_readiness_recorded_true(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["rollback_readiness_recorded"] is True


def test_44_result_keeps_rollback_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["rollback_executed"] is False


def test_45_result_keeps_unpublish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["unpublish_executed"] is False


def test_46_result_keeps_draft_revert_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["draft_revert_executed"] is False


def test_47_result_keeps_wordpress_post_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["wordpress_post_executed"] is False


def test_48_result_keeps_wordpress_write_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["wordpress_write_executed_by_this_phase"] is False


def test_49_result_keeps_publish_executed_by_this_phase_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["publish_executed_by_this_phase"] is False


def test_50_result_keeps_post119_update_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["post119_update_executed"] is False


def test_51_result_keeps_content_title_meta_new_delete_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["wordpress_content_update_executed"] is False
    assert out["wordpress_title_update_executed"] is False
    assert out["wordpress_meta_update_executed"] is False
    assert out["wordpress_new_post_executed"] is False
    assert out["delete_executed"] is False


def test_52_result_keeps_credential_value_output_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["credential_value_output"] is False


def test_53_result_keeps_no_write_executed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["no_write_executed_by_this_phase"] is True


def test_54_result_keeps_chain_closed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_case(monkeypatch, files)
    assert out["start_ls_one_shot_publish_chain_closed"] is True
