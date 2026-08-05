from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation import (
    NOT_READY_STATUS,
    VALIDATED_STATUS,
    main,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "fixa_result": tmp_path / "exchange/runtime/fixa_result.json",
        "fixa_lock": tmp_path / "exchange/locks/fixa_lock.json",
        "fixa_validation": tmp_path / "exchange/logs/fixa_validation.json",
        "skeleton_result": tmp_path / "exchange/runtime/skeleton_result.json",
        "runner_skeleton": tmp_path / "scripts/runner_skeleton.py",
        "implementation_result": tmp_path / "exchange/runtime/implementation_result.json",
        "implementation_lock": tmp_path / "exchange/locks/implementation_lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "validation_result": tmp_path / "exchange/logs/validation_result.json",
        "validation_output": tmp_path / "exchange/runtime/ao_result.json",
        "validation_lock_output": tmp_path / "exchange/locks/ao_lock.json",
        "output": tmp_path / "exchange/logs/ao_log.json",
        "report": tmp_path / "reports/ao_report.md",
    }

    files["runner_skeleton"].parent.mkdir(parents=True, exist_ok=True)
    files["runner_skeleton"].write_text(
        "#!/usr/bin/env python3\n"
        "def build_no_execution_runner_blueprint():\n"
        "    return {\n"
        "        'execution_enabled': False,\n"
        "        'network_call_enabled': False,\n"
        "        'credential_read_enabled': False,\n"
        "        'publish_enabled': False,\n"
        "    }\n",
        encoding="utf-8",
    )

    write_json(
        files["policy"],
        {
            "phase": "LS-6AO",
            "execution_mode": "NO_EXECUTION_IMPLEMENTATION_VALIDATION_ONLY_NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "required_previous_phase": {
                "ls6an_fix_a": {
                    "required_validation_status": "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_VALIDATED_NO_PUBLISH",
                    "required_source_artifacts_unchanged": True,
                    "required_skeleton_status_alias_accepted": True,
                    "required_run_status_alias_accepted": True,
                    "required_status_normalized": True,
                    "required_ls6an_validation_validated": True,
                },
                "ls6an": {
                    "required_skeleton_canonical_status": "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_SKELETON_NO_EXECUTION_READY_NO_PUBLISH",
                    "accepted_skeleton_status_alias": "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_SKELETON_READY",
                    "required_run_canonical_status": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_PASSED_NO_PUBLISH",
                    "accepted_run_status_alias": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_READY_NO_PUBLISH",
                    "required_validation_status": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATED_NO_PUBLISH",
                },
            },
            "validation_policy": {
                "ls6an_fix_a_status_normalization_validated": True,
                "ls6an_no_execution_implementation_validated": True,
                "runner_skeleton_static_safety_validated": True,
                "source_artifacts_unchanged": True,
                "runner_skeleton_reexecuted_by_this_phase": False,
                "actual_publish_execution_runner_reexecuted_by_this_phase": False,
            },
            "static_safety_scan": {
                "forbidden_tokens": [
                    "requests.post",
                    "requests.put",
                    "requests.patch",
                    "requests.delete",
                    "requests.get",
                    "urllib.request",
                    "wp-json",
                    "/wp/v2/posts",
                    "Authorization",
                    "Basic ",
                    "WORDPRESS_APP_PASSWORD",
                    "/etc/ai-media-os/credential.env",
                    "credential.env",
                ]
            },
            "must_remain_false_flags": {
                "wordpress_api_call_executed": False,
                "wordpress_get_executed": False,
                "wordpress_post_executed": False,
                "wordpress_put_executed": False,
                "wordpress_patch_executed": False,
                "wordpress_delete_executed": False,
                "wordpress_write_executed_by_this_phase": False,
                "wordpress_publish_executed": False,
                "publish_executed": False,
                "future_schedule_executed": False,
                "delete_executed": False,
                "post119_update_executed": False,
                "credential_env_read_executed": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_output": False,
                "runner_skeleton_reexecuted_by_this_phase": False,
                "actual_publish_execution_runner_reexecuted_by_this_phase": False,
                "actual_publish_execution_runner_no_execution_implementation_consumed": False,
                "actual_publish_execution_runner_implementation_gate_consumed": False,
                "actual_publish_execution_runner_network_call_enabled": False,
                "actual_publish_execution_runner_credential_read_enabled": False,
                "actual_publish_execution_runner_publish_enabled": False,
                "actual_publish_execution_runner_execution_enabled": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
            },
            "next_phase": {
                "phase": "LS-6AP",
                "execution_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_actual_publish_execution_runner_execution_approval_gate": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
        },
    )

    write_json(
        files["fixa_result"],
        {
            "status": "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_READY_NO_PUBLISH",
            "source_artifacts_unchanged": True,
            "skeleton_status_alias_accepted": True,
            "run_status_alias_accepted": True,
            "status_normalized": True,
            "ls6an_validation_validated": True,
        },
    )
    write_json(
        files["fixa_lock"],
        {
            "status": "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_LOCKED_NO_PUBLISH",
            "locked": True,
        },
    )
    write_json(
        files["fixa_validation"],
        {
            "status": "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_VALIDATED_NO_PUBLISH"
        },
    )

    run_like = {
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "returned_post_status": "draft",
        "actual_publish_execution_runner_no_execution_implementation_ready": True,
        "actual_publish_execution_runner_no_execution_implementation_consumed": False,
        "actual_publish_execution_runner_implementation_gate_consumed": False,
        "actual_publish_execution_runner_implementation_allowed_by_this_phase": True,
        "actual_publish_execution_runner_implemented_by_this_phase": True,
        "actual_publish_execution_runner_file_created_by_this_phase": True,
        "actual_publish_execution_runner_network_call_enabled": False,
        "actual_publish_execution_runner_credential_read_enabled": False,
        "actual_publish_execution_runner_publish_enabled": False,
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_execution_runner_execution_approval_gate": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }

    write_json(files["skeleton_result"], {"status": "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_SKELETON_READY"})
    write_json(files["implementation_result"], {"status": "OK", **run_like})
    write_json(files["implementation_lock"], {"status": "OK", **run_like})
    write_json(
        files["run_result"],
        {
            "status": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_READY_NO_PUBLISH",
            **run_like,
        },
    )
    write_json(
        files["validation_result"],
        {
            "status": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATED_NO_PUBLISH",
            **run_like,
        },
    )

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--ls6an-fix-a-normalization-result",
        str(files["fixa_result"]),
        "--ls6an-fix-a-normalization-lock",
        str(files["fixa_lock"]),
        "--ls6an-fix-a-validation-result",
        str(files["fixa_validation"]),
        "--ls6an-skeleton-result",
        str(files["skeleton_result"]),
        "--ls6an-runner-skeleton",
        str(files["runner_skeleton"]),
        "--ls6an-implementation-result",
        str(files["implementation_result"]),
        "--ls6an-implementation-lock",
        str(files["implementation_lock"]),
        "--ls6an-run-result",
        str(files["run_result"]),
        "--ls6an-validation-result",
        str(files["validation_result"]),
        "--validation-output",
        str(files["validation_output"]),
        "--validation-lock-output",
        str(files["validation_lock_output"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]


def invoke(monkeypatch, files: dict[str, Path]) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_valid_artifacts_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == VALIDATED_STATUS


@pytest.mark.parametrize(
    "missing_key",
    [
        "policy",
        "fixa_result",
        "fixa_lock",
        "fixa_validation",
        "skeleton_result",
        "runner_skeleton",
        "implementation_result",
        "implementation_lock",
        "run_result",
        "validation_result",
    ],
)
def test_missing_required_files_not_ready(monkeypatch, tmp_path: Path, missing_key: str) -> None:
    files = make_inputs(tmp_path)
    files[missing_key].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_post_id_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["run_result"])
    data["post_id"] = 999
    write_json(files["run_result"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_returned_post_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["run_result"])
    data["returned_post_status"] = "publish"
    write_json(files["run_result"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_ls6an_fix_a_validation_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["fixa_validation"])
    data["status"] = "BROKEN"
    write_json(files["fixa_validation"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


@pytest.mark.parametrize(
    "key",
    [
        "source_artifacts_unchanged",
        "skeleton_status_alias_accepted",
        "run_status_alias_accepted",
        "status_normalized",
        "ls6an_validation_validated",
    ],
)
def test_fix_a_required_true_flags_false_not_ready(monkeypatch, tmp_path: Path, key: str) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["fixa_result"])
    data[key] = False
    write_json(files["fixa_result"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_ls6an_validation_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["validation_result"])
    data["status"] = "BROKEN"
    write_json(files["validation_result"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


@pytest.mark.parametrize(
    "key,value",
    [
        ("actual_publish_execution_runner_no_execution_implementation_ready", False),
        ("actual_publish_execution_runner_no_execution_implementation_consumed", True),
        ("actual_publish_execution_runner_implementation_gate_consumed", True),
        ("actual_publish_execution_runner_file_created_by_this_phase", False),
        ("actual_publish_execution_runner_network_call_enabled", True),
        ("actual_publish_execution_runner_credential_read_enabled", True),
        ("actual_publish_execution_runner_publish_enabled", True),
        ("actual_publish_execution_runner_execution_enabled", True),
        ("actual_publish_execution_runner_executed", True),
        ("manual_publish_executed", True),
        ("wordpress_api_call_executed", True),
        ("wordpress_get_executed", True),
        ("wordpress_post_executed", True),
        ("wordpress_write_executed_by_this_phase", True),
        ("wordpress_publish_executed", True),
        ("publish_executed", True),
        ("credential_env_read_executed", True),
        ("credential_value_output", True),
        ("authorization_header_output", True),
        ("rerun_allowed", True),
    ],
)
def test_run_flags_break_not_ready(monkeypatch, tmp_path: Path, key: str, value) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["run_result"])
    data[key] = value
    write_json(files["run_result"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


@pytest.mark.parametrize(
    "token",
    [
        "requests.post",
        "requests.get",
        "urllib.request",
        "wp-json",
        "/wp/v2/posts",
        "Authorization",
        "Basic ",
        "WORDPRESS_APP_PASSWORD",
        "credential.env",
    ],
)
def test_runner_skeleton_forbidden_token_not_ready(monkeypatch, tmp_path: Path, token: str) -> None:
    files = make_inputs(tmp_path)
    src = files["runner_skeleton"].read_text(encoding="utf-8")
    files["runner_skeleton"].write_text(src + f"# {token}\n", encoding="utf-8")
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_runner_skeleton_reexecuted_flag_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["policy"])
    data["validation_policy"]["runner_skeleton_reexecuted_by_this_phase"] = True
    write_json(files["policy"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_actual_runner_reexecuted_flag_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    data = read_json(files["policy"])
    data["validation_policy"]["actual_publish_execution_runner_reexecuted_by_this_phase"] = True
    write_json(files["policy"], data)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_validation_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["validation_output"].exists()


def test_validation_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["validation_lock_output"].exists()


def test_validation_log_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["output"].exists()


def test_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["report"].exists()


def test_result_source_artifacts_unchanged_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["source_artifacts_unchanged"] is True


def test_result_runner_skeleton_static_safety_validated_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["runner_skeleton_static_safety_validated"] is True


def test_result_runner_skeleton_reexecuted_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["runner_skeleton_reexecuted_by_this_phase"] is False


def test_result_actual_runner_reexecuted_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_reexecuted_by_this_phase"] is False


def test_result_wordpress_api_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False


def test_result_credential_env_read_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["credential_env_read_executed"] is False


def test_result_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["publish_executed"] is False


def test_result_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_executed"] is False


def test_result_next_phase_ls6ap(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["next_phase"]["phase"] == "LS-6AP"


def test_result_publish_execution_still_blocked_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["publish_execution_still_blocked"] is True


def test_result_requires_execution_approval_gate_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["requires_actual_publish_execution_runner_execution_approval_gate"] is True


def test_result_status_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == VALIDATED_STATUS


def test_lock_status_locked(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    lock_data = read_json(files["validation_lock_output"])
    assert lock_data["status"] == "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_LOCKED_NO_PUBLISH"


def test_validation_output_and_log_equal(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    runtime_data = read_json(files["validation_output"])
    log_data = read_json(files["output"])
    assert runtime_data == log_data


def test_skeleton_status_alias_accepted_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["skeleton_status_alias_accepted"] is True


def test_run_status_alias_accepted_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["run_status_alias_accepted"] is True


def test_status_normalized_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status_normalized"] is True


def test_ls6an_fix_a_status_normalization_validated_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["ls6an_fix_a_status_normalization_validated"] is True


def test_ls6an_no_execution_implementation_validated_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["ls6an_no_execution_implementation_validated"] is True


def test_no_errors_on_valid_case(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["errors"] == []
