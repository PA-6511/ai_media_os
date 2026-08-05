from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6an_fix_a_actual_publish_execution_runner_status_normalization import (
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
        "skeleton": tmp_path / "exchange/runtime/skeleton.json",
        "implementation": tmp_path / "exchange/runtime/implementation.json",
        "implementation_lock": tmp_path / "exchange/locks/implementation.lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "validation": tmp_path / "exchange/logs/validation.json",
        "normalization": tmp_path / "exchange/runtime/normalization.json",
        "normalization_lock": tmp_path / "exchange/locks/normalization.lock.json",
        "output": tmp_path / "exchange/logs/validation_out.json",
        "report": tmp_path / "reports/validation.md",
        "normalization_report": tmp_path / "reports/normalization.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AN-FIX-A",
            "execution_mode": "STATUS_NORMALIZATION_ONLY_NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "status_normalization": {
                "skeleton_status": {
                    "canonical": "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_SKELETON_NO_EXECUTION_READY_NO_PUBLISH",
                    "accepted_aliases": [
                        "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_SKELETON_READY"
                    ],
                    "alias_accepted": True,
                    "normalized": True,
                },
                "run_status": {
                    "canonical": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_PASSED_NO_PUBLISH",
                    "accepted_aliases": [
                        "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_READY_NO_PUBLISH"
                    ],
                    "alias_accepted": True,
                    "normalized": True,
                },
                "validation_status": {
                    "canonical": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATED_NO_PUBLISH",
                    "accepted_aliases": [],
                    "alias_accepted": False,
                    "normalized": False,
                },
            },
            "must_remain_true_flags": {
                "ls6an_validation_validated": True,
                "skeleton_status_alias_accepted": True,
                "run_status_alias_accepted": True,
                "status_normalized": True,
                "source_artifacts_unchanged": True,
                "actual_publish_execution_runner_no_execution_implementation_ready": True,
                "actual_publish_execution_runner_implementation_allowed_by_this_phase": True,
                "actual_publish_execution_runner_implemented_by_this_phase": True,
                "actual_publish_execution_runner_file_created_by_this_phase": True,
                "requires_actual_publish_execution_runner_no_execution_validation": True,
                "requires_actual_publish_execution_runner_execution_approval_gate": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
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
            "outputs": {
                "normalization_report": str(files["normalization_report"]).replace(str(tmp_path) + "/", "")
            },
            "next_phase": {
                "phase": "LS-6AO",
                "execution_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_actual_publish_execution_runner_no_execution_validation": True,
                "requires_actual_publish_execution_runner_execution_approval_gate": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
        },
    )

    write_json(
        files["skeleton"],
        {
            "phase": "LS-6AN",
            "status": "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_SKELETON_READY",
        },
    )

    run_like = {
        "phase": "LS-6AN",
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
        "requires_actual_publish_execution_runner_no_execution_validation": True,
        "requires_actual_publish_execution_runner_execution_approval_gate": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }

    write_json(
        files["implementation"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_RECORDED_NO_PUBLISH",
            **run_like,
        },
    )
    write_json(
        files["implementation_lock"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_LOCKED_NO_PUBLISH",
            "locked": True,
            **run_like,
        },
    )
    write_json(
        files["run"],
        {
            "status": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_READY_NO_PUBLISH",
            **run_like,
        },
    )
    write_json(
        files["validation"],
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
        "--skeleton-result",
        str(files["skeleton"]),
        "--implementation-result",
        str(files["implementation"]),
        "--implementation-lock",
        str(files["implementation_lock"]),
        "--run-result",
        str(files["run"]),
        "--validation-result",
        str(files["validation"]),
        "--normalization-output",
        str(files["normalization"]),
        "--normalization-lock-output",
        str(files["normalization_lock"]),
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


def test_valid_alias_statuses_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == VALIDATED_STATUS


def test_canonical_skeleton_status_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["skeleton"])
    p["status"] = "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_SKELETON_NO_EXECUTION_READY_NO_PUBLISH"
    write_json(files["skeleton"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == VALIDATED_STATUS


def test_canonical_run_status_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["status"] = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_PASSED_NO_PUBLISH"
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == VALIDATED_STATUS


def test_unknown_skeleton_status_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["skeleton"])
    p["status"] = "UNKNOWN"
    write_json(files["skeleton"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_unknown_run_status_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["status"] = "UNKNOWN"
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_validation_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["validation"])
    p["status"] = "BROKEN"
    write_json(files["validation"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_post_id_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["post_id"] = 999
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_returned_post_status_not_draft_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["returned_post_status"] = "publish"
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


@pytest.mark.parametrize(
    "field",
    [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_publish_executed",
        "publish_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "authorization_header_output",
        "actual_publish_execution_runner_no_execution_implementation_consumed",
        "actual_publish_execution_runner_implementation_gate_consumed",
        "actual_publish_execution_runner_network_call_enabled",
        "actual_publish_execution_runner_credential_read_enabled",
        "actual_publish_execution_runner_publish_enabled",
        "actual_publish_execution_runner_execution_enabled",
        "actual_publish_execution_runner_executed",
        "manual_publish_executed",
        "rerun_allowed",
    ],
)
def test_false_flags_true_not_ready(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p[field] = True
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_source_artifacts_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["run"].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == NOT_READY_STATUS


def test_normalization_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["normalization"].exists()


def test_normalization_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["normalization_lock"].exists()


def test_source_artifacts_unchanged_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["source_artifacts_unchanged"] is True


def test_skeleton_alias_accepted_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["skeleton_status_alias_accepted"] is True


def test_run_alias_accepted_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["run_status_alias_accepted"] is True


def test_status_normalized_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["status_normalized"] is True


def test_canonical_skeleton_recorded(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["normalization"])
    assert (
        data["skeleton_status_canonical"]
        == "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_SKELETON_NO_EXECUTION_READY_NO_PUBLISH"
    )


def test_canonical_run_recorded(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["normalization"])
    assert (
        data["run_status_canonical"]
        == "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_PASSED_NO_PUBLISH"
    )


def test_validation_canonical_recorded(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["normalization"])
    assert (
        data["validation_status_canonical"]
        == "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATED_NO_PUBLISH"
    )


def test_next_phase_ls6ao(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["next_phase"]["phase"] == "LS-6AO"


def test_publish_execution_still_blocked_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["publish_execution_still_blocked"] is True


def test_no_wordpress_api_code_in_validator() -> None:
    p = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6an_fix_a_actual_publish_execution_runner_status_normalization.py")
    src = p.read_text(encoding="utf-8")
    for token in ["wp-json", "requests.get", "requests.post", "urllib.request"]:
        assert token not in src


def test_no_credential_read_code_in_validator() -> None:
    p = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6an_fix_a_actual_publish_execution_runner_status_normalization.py")
    src = p.read_text(encoding="utf-8")
    for token in ["credential.env", "load_dotenv", "WORDPRESS_APP_PASSWORD", "Basic "]:
        assert token not in src


def test_validation_output_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["output"].exists()


def test_validation_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["report"].exists()


def test_normalization_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["normalization_report"].exists()


def test_ls6an_validation_validated_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["ls6an_validation_validated"] is True


def test_runner_not_executed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["actual_publish_execution_runner_executed"] is False


def test_manual_publish_not_executed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["output"])
    assert data["manual_publish_executed"] is False


def test_locked_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    data = read_json(files["normalization"])
    assert data["locked"] is True


def test_no_errors_on_valid_case(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["errors"] == []
