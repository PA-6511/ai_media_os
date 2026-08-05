from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls_mon1_post183_published_state_monitor import (
    PUBLIC_REST_UNAVAILABLE_WARNING,
    STATUS_NOT_VALIDATED,
    STATUS_VALIDATED,
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
        "monitor_result": tmp_path / "exchange/runtime/monitor_result.json",
        "monitor_lock": tmp_path / "exchange/locks/monitor_lock.json",
        "run_result": tmp_path / "exchange/logs/monitor_result.json",
        "ls_close1_result": tmp_path / "exchange/runtime/ls_close1_result.json",
        "ls_close1_lock": tmp_path / "exchange/locks/ls_close1_lock.json",
        "ls_close1_validation": tmp_path / "exchange/logs/ls_close1_validation.json",
        "ls6au_result": tmp_path / "exchange/runtime/ls6au_result.json",
        "ls6au_lock": tmp_path / "exchange/locks/ls6au_lock.json",
        "ls6au_validation": tmp_path / "exchange/logs/ls6au_validation.json",
        "output": tmp_path / "exchange/logs/validation_result.json",
        "report": tmp_path / "reports/validation_report.md",
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
                },
                "ls6au": {
                    "required_run_status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED",
                    "required_validation_status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED",
                    "required_production_status": "PUBLISHED_VERIFIED",
                    "required_rest_returned_post_status": "publish",
                },
            },
            "monitor_policy": {
                "monitor_scope": "POST_183_ONLY",
                "monitor_window": "FIRST_24H_AFTER_PUBLISH",
                "monitor_checkpoint": "LS_MON_1_INITIAL_CHECKPOINT",
                "recommended_next_action": "CONTINUE_24H_GET_ONLY_MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
            },
        },
    )

    monitor_payload = {
        "phase": "LS-MON-1",
        "document_type": "POST_183_PUBLISHED_STATE_MONITOR_RESULT",
        "status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_PASSED_GET_ONLY",
        "execution_mode": "GET_ONLY_MONITOR_NO_CREDENTIAL_NO_WRITE",
        "production_status": "PUBLISHED_STATE_MONITORED",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "public_rest_url": "https://hoshido.jp/wp-json/wp/v2/posts/183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "ls_close1_validated": True,
        "ls_close1_completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
        "ls6au_validated": True,
        "ls6au_production_status": "PUBLISHED_VERIFIED",
        "ls6au_rest_returned_post_status": "publish",
        "ls6au_public_url_reachable": True,
        "monitor_checkpoint_recorded": True,
        "monitor_scope": "POST_183_ONLY",
        "monitor_window": "FIRST_24H_AFTER_PUBLISH",
        "monitor_checkpoint": "LS_MON_1_INITIAL_CHECKPOINT",
        "public_url_get_executed": True,
        "public_url_http_status": 200,
        "public_url_reachable": True,
        "public_url_reachable_status_ok": True,
        "public_rest_get_executed": True,
        "public_rest_http_status": 200,
        "public_rest_reachable": True,
        "public_rest_returned_post_id": 183,
        "public_rest_returned_post_status": "publish",
        "public_rest_status_verified": True,
        "public_rest_warning": None,
        "published_state_preserved": True,
        "post_publish_state_monitor_ok": True,
        "wordpress_authenticated_api_call_executed": False,
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
        "locked": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "recommended_next_action": "CONTINUE_24H_GET_ONLY_MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
        "recommended_next_phase_options": ["LS-MON-2", "LS-NEXT-1", "LS-REUSE-1"],
        "errors": [],
    }
    write_json(files["monitor_result"], monitor_payload)
    write_json(files["run_result"], monitor_payload)

    write_json(
        files["monitor_lock"],
        {
            "phase": "LS-MON-1",
            "document_type": "POST_183_PUBLISHED_STATE_MONITOR_LOCK",
            "status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_LOCKED_GET_ONLY",
            "locked": True,
        },
    )

    write_json(
        files["ls_close1_result"],
        {
            "status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_PASSED_NO_EXECUTION",
            "completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
        },
    )
    write_json(files["ls_close1_lock"], {"locked": True})
    write_json(
        files["ls_close1_validation"],
        {"status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_VALIDATED_NO_EXECUTION"},
    )

    write_json(
        files["ls6au_result"],
        {
            "status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED",
            "production_status": "PUBLISHED_VERIFIED",
            "rest_returned_post_status": "publish",
        },
    )
    write_json(files["ls6au_lock"], {"locked": True})
    write_json(files["ls6au_validation"], {"status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED"})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--monitor-result",
        str(files["monitor_result"]),
        "--monitor-lock",
        str(files["monitor_lock"]),
        "--run-result",
        str(files["run_result"]),
        "--ls-close1-result",
        str(files["ls_close1_result"]),
        "--ls-close1-lock",
        str(files["ls_close1_lock"]),
        "--ls-close1-validation-result",
        str(files["ls_close1_validation"]),
        "--ls6au-result",
        str(files["ls6au_result"]),
        "--ls6au-lock",
        str(files["ls6au_lock"]),
        "--ls6au-validation-result",
        str(files["ls6au_validation"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]


def run_validate(monkeypatch, files: dict[str, Path]) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_56_validation_valid(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_57_validation_accepts_rest_warning_when_public_url_reachable(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["monitor_result"], ("public_rest_reachable",), False)
    mutate(files["monitor_result"], ("public_rest_status_verified",), False)
    mutate(files["monitor_result"], ("public_rest_warning",), PUBLIC_REST_UNAVAILABLE_WARNING)
    write_json(files["run_result"], read_json(files["monitor_result"]))
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_58_validation_detects_missing_monitor_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["monitor_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_59_validation_detects_missing_monitor_lock(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["monitor_lock"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_60_validation_detects_missing_run_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["run_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("monitor_result", ("status",), "WRONG"),
        ("monitor_result", ("production_status",), "WRONG"),
        ("monitor_result", ("post_id",), 999),
        ("monitor_result", ("public_url_get_executed",), False),
        ("monitor_result", ("public_url_reachable",), False),
        ("monitor_result", ("monitor_checkpoint_recorded",), False),
        ("monitor_result", ("published_state_preserved",), False),
        ("monitor_result", ("post_publish_state_monitor_ok",), False),
        ("monitor_result", ("credential_env_read_executed",), True),
        ("monitor_result", ("wordpress_authenticated_api_call_executed",), True),
        ("monitor_result", ("wordpress_post_executed",), True),
        ("monitor_result", ("wordpress_write_executed_by_this_phase",), True),
        ("monitor_result", ("publish_executed_by_this_phase",), True),
        ("monitor_result", ("rollback_executed",), True),
        ("monitor_result", ("post119_update_executed",), True),
        ("monitor_result", ("post183_update_executed_by_this_phase",), True),
        ("monitor_result", ("secret_length_output",), True),
        ("monitor_result", ("secret_hash_output",), True),
        ("monitor_result", ("rerun_allowed",), True),
        ("monitor_result", ("recommended_next_action",), "WRONG"),
    ],
)
def test_61_to_80_validation_checks(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files[path_key], keys, value)
    if path_key == "monitor_result":
        write_json(files["run_result"], read_json(files[path_key]))
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_81_source_has_no_requests_post() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.post" not in src


def test_82_source_has_no_requests_put() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.put" not in src


def test_83_source_has_no_requests_patch() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.patch" not in src


def test_84_source_has_no_requests_delete() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "requests.delete" not in src


def test_85_source_has_no_credential_env_open() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "credential.env" not in src


def test_86_source_has_no_authorization_output() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "Authorization:" not in src


def test_87_source_has_no_basic_output() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "Basic " not in src


def test_88_source_has_no_base64_usage() -> None:
    src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls_mon1_post183_published_state_monitor.py").read_text(encoding="utf-8")
    assert "base64" not in src
    assert "b64encode" not in src
