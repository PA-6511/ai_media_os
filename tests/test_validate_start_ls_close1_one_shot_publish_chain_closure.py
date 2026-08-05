from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls_close1_one_shot_publish_chain_closure import (
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
        "closure_result": tmp_path / "exchange/runtime/closure_result.json",
        "closure_lock": tmp_path / "exchange/locks/closure_lock.json",
        "run_result": tmp_path / "exchange/logs/closure_result.json",
        "ls6au_result": tmp_path / "exchange/runtime/ls6au_result.json",
        "ls6au_lock": tmp_path / "exchange/locks/ls6au_lock.json",
        "ls6au_run": tmp_path / "exchange/logs/ls6au_result.json",
        "ls6au_validation": tmp_path / "exchange/logs/ls6au_validation.json",
        "ls6at_result": tmp_path / "exchange/runtime/ls6at_result.json",
        "ls6at_lock": tmp_path / "exchange/locks/ls6at_lock.json",
        "ls6at_validation": tmp_path / "exchange/logs/ls6at_validation.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
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
        files["closure_result"],
        {
            "status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_PASSED_NO_EXECUTION",
            "execution_mode": "CLOSURE_REGISTRATION_ONLY_NO_EXECUTION",
            "production_status": "PUBLISHED_AND_VERIFIED_CLOSURE",
            "post_id": 183,
            "post_link": "https://hoshido.jp/?p=183",
            "payload_title": "2.5次元の誘惑",
            "payload_asin": "B07X2G67B4",
            "ls6au_validated": True,
            "ls6au_production_status": "PUBLISHED_VERIFIED",
            "ls6au_completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_PUBLISHED_AND_VERIFIED",
            "ls6au_post_publish_verified": True,
            "ls6au_published_evidence_recorded": True,
            "ls6au_rollback_readiness_recorded": True,
            "ls6at_validated": True,
            "ls6at_production_status": "PUBLISHED",
            "ls6at_updated_post_id": 183,
            "ls6at_updated_fields": ["status"],
            "ls6at_updated_status": "publish",
            "start_ls_one_shot_publish_chain_closed": True,
            "closure_registration_executed": True,
            "published_state_preserved": True,
            "post_publish_verified": True,
            "published_evidence_recorded": True,
            "rollback_readiness_recorded": True,
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
            "locked": True,
            "rerun_allowed": False,
            "ls6at_rerun_allowed": False,
            "ls6au_rerun_allowed": False,
            "publish_rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
            "recommended_next_action": "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
            "recommended_next_phase_options": ["LS-MON-1", "LS-NEXT-1", "LS-REUSE-1"],
        },
    )
    write_json(files["run_result"], read_json(files["closure_result"]))

    write_json(
        files["closure_lock"],
        {
            "status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_LOCKED_NO_EXECUTION",
            "locked": True,
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
    write_json(files["ls6au_lock"], {"locked": True})
    write_json(files["ls6au_run"], read_json(files["ls6au_result"]))
    write_json(files["ls6au_validation"], {"status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED"})

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
            "locked": True,
        },
    )
    write_json(files["ls6at_lock"], {"locked": True})
    write_json(files["ls6at_validation"], {"status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED"})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--closure-result",
        str(files["closure_result"]),
        "--closure-lock",
        str(files["closure_lock"]),
        "--run-result",
        str(files["run_result"]),
        "--ls6au-result",
        str(files["ls6au_result"]),
        "--ls6au-lock",
        str(files["ls6au_lock"]),
        "--ls6au-validation-result",
        str(files["ls6au_validation"]),
        "--ls6at-result",
        str(files["ls6at_result"]),
        "--ls6at-lock",
        str(files["ls6at_lock"]),
        "--ls6at-validation-result",
        str(files["ls6at_validation"]),
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


def test_65_validation_valid(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_66_validation_missing_closure_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["closure_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_67_validation_missing_closure_lock(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["closure_lock"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_68_validation_missing_run_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["run_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("closure_result", ("status",), "WRONG"),
        ("closure_result", ("production_status",), "WRONG"),
        ("closure_result", ("post_id",), 999),
        ("closure_result", ("start_ls_one_shot_publish_chain_closed",), False),
        ("closure_result", ("closure_registration_executed",), False),
        ("closure_result", ("published_state_preserved",), False),
        ("closure_result", ("post_publish_verified",), False),
        ("closure_result", ("published_evidence_recorded",), False),
        ("closure_result", ("rollback_readiness_recorded",), False),
        ("closure_result", ("wordpress_api_call_executed",), True),
        ("closure_result", ("wordpress_post_executed",), True),
        ("closure_result", ("publish_executed_by_this_phase",), True),
        ("closure_result", ("credential_env_read_executed",), True),
        ("closure_result", ("rollback_executed",), True),
        ("closure_result", ("post119_update_executed",), True),
        ("closure_result", ("post183_update_executed_by_this_phase",), True),
        ("closure_result", ("rerun_allowed",), True),
        ("closure_result", ("completion_status",), "WRONG"),
        ("closure_result", ("recommended_next_action",), "WRONG"),
        ("ls6au_validation", ("status",), "WRONG"),
        ("ls6au_result", ("production_status",), "WRONG"),
        ("ls6au_result", ("completion_status",), "WRONG"),
        ("ls6au_result", ("post_publish_verified",), False),
        ("ls6au_result", ("published_evidence_recorded",), False),
        ("ls6au_result", ("rollback_readiness_recorded",), False),
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
def test_69_to_83_validation_checks(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    if path_key in files:
        mutate(files[path_key], keys, value)
        if path_key in {"closure_result", "ls6au_result", "ls6at_result"}:
            write_json(files["run_result"], read_json(files[path_key]))
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_84_source_has_no_requests_call() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
    ).read_text(encoding="utf-8")
    assert "requests." not in src


def test_85_source_has_no_urllib_request() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
    ).read_text(encoding="utf-8")
    assert "urllib.request" not in src


def test_86_source_has_no_wp_json() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
    ).read_text(encoding="utf-8")
    assert "wp-json" not in src


def test_87_source_has_no_wp_v2_posts() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
    ).read_text(encoding="utf-8")
    assert "/wp/v2/posts" not in src


def test_88_source_has_no_credential_env_open() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
    ).read_text(encoding="utf-8")
    assert "credential.env" not in src


def test_89_source_has_no_authorization_output() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
        ).read_text(encoding="utf-8")
    )
    assert "Authorization:" not in merged


def test_90_source_has_no_basic_output() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
        ).read_text(encoding="utf-8")
    )
    assert "Basic " not in merged


def test_91_source_has_no_base64_usage() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls_close1_one_shot_publish_chain_closure.py"
        ).read_text(encoding="utf-8")
    )
    assert "base64" not in merged
    assert "b64encode" not in merged
