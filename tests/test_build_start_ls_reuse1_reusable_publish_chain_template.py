from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_start_ls_reuse1_reusable_publish_chain_template import (
    STATUS_FAILED,
    STATUS_PASSED,
    main,
)


LS6AU_VALIDATION_REL = Path("exchange/logs/start_ls6au_post_publish_verification_published_evidence_validation_result.json")
LS6AT_VALIDATION_REL = Path("exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_validation_result.json")


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
        "ls_mon1_result": tmp_path / "exchange/runtime/ls_mon1_result.json",
        "ls_mon1_lock": tmp_path / "exchange/locks/ls_mon1_lock.json",
        "ls_mon1_validation": tmp_path / "exchange/logs/ls_mon1_validation.json",
        "ls_close1_result": tmp_path / "exchange/runtime/ls_close1_result.json",
        "ls_close1_lock": tmp_path / "exchange/locks/ls_close1_lock.json",
        "ls_close1_validation": tmp_path / "exchange/logs/ls_close1_validation.json",
        "ls6au_result": tmp_path / "exchange/runtime/ls6au_result.json",
        "ls6at_result": tmp_path / "exchange/runtime/ls6at_result.json",
        "output": tmp_path / "exchange/runtime/template_result.json",
        "lock_output": tmp_path / "exchange/locks/template_lock.json",
        "report": tmp_path / "reports/template_report.md",
        "input_schema": tmp_path / "config/start_ls_reusable_publish_chain_input_schema.json",
        "phase_map": tmp_path / "config/start_ls_reusable_publish_chain_phase_map.json",
        "item_template": tmp_path / "exchange/templates/start_ls_reusable_publish_chain_item.template.json",
        "safety_contract": tmp_path / "exchange/templates/start_ls_reusable_publish_chain_safety_contract.json",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-REUSE-1",
            "source_chain": {
                "source_post_id": 183,
                "source_post_link": "https://hoshido.jp/?p=183",
                "source_title": "2.5次元の誘惑",
                "source_asin": "B07X2G67B4",
                "source_completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
                "source_monitor_status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_VALIDATED_GET_ONLY",
            },
            "required_previous_phase": {
                "ls_mon1": {
                    "required_validation_status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_VALIDATED_GET_ONLY",
                    "required_production_status": "PUBLISHED_STATE_MONITORED",
                    "required_post_id": 183,
                    "required_public_url_reachable": True,
                    "required_public_rest_status": "publish",
                },
                "ls_close1": {
                    "required_validation_status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_VALIDATED_NO_EXECUTION",
                    "required_completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
                },
                "ls6au": {
                    "required_validation_status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED",
                    "required_production_status": "PUBLISHED_VERIFIED",
                },
                "ls6at": {
                    "required_validation_status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED",
                    "required_production_status": "PUBLISHED",
                },
            },
            "must_remain_false_flags": {
                "wordpress_api_call_executed": False,
                "wordpress_get_executed": False,
                "wordpress_post_executed": False,
                "wordpress_write_executed_by_this_phase": False,
                "publish_executed_by_this_phase": False,
                "post119_update_executed": False,
                "post183_update_executed_by_this_phase": False,
                "next_post_created": False,
                "rollback_executed": False,
                "unpublish_executed": False,
                "draft_revert_executed": False,
                "credential_env_read_executed": False,
                "credential_values_loaded_for_output": False,
                "credential_values_persisted": False,
                "credential_values_logged": False,
                "credential_value_output": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_generated": False,
                "authorization_header_output": False,
                "basic_auth_string_generated": False,
                "basic_auth_string_output": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "rerun_allowed": False,
                "publish_rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
            },
            "outputs": {
                "input_schema": str(files["input_schema"].relative_to(tmp_path)),
                "phase_map": str(files["phase_map"].relative_to(tmp_path)),
                "item_template": str(files["item_template"].relative_to(tmp_path)),
                "safety_contract": str(files["safety_contract"].relative_to(tmp_path)),
            },
            "next_phase": {
                "recommended_next_action": "BEGIN_NEXT_CONTENT_ITEM_WITH_REUSABLE_TEMPLATE_OR_CONTINUE_MONITORING",
                "recommended_next_phase_options": ["LS-NEXT-1", "LS-MON-2", "LS-REUSE-2"],
            },
        },
    )

    write_json(
        files["ls_mon1_result"],
        {
            "status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_PASSED_GET_ONLY",
            "production_status": "PUBLISHED_STATE_MONITORED",
            "post_id": 183,
            "public_url_reachable": True,
            "public_rest_returned_post_status": "publish",
        },
    )
    write_json(files["ls_mon1_lock"], {"locked": True})
    write_json(files["ls_mon1_validation"], {"status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_VALIDATED_GET_ONLY"})

    write_json(
        files["ls_close1_result"],
        {
            "completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
        },
    )
    write_json(files["ls_close1_lock"], {"locked": True})
    write_json(files["ls_close1_validation"], {"status": "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_VALIDATED_NO_EXECUTION"})

    write_json(files["ls6au_result"], {"production_status": "PUBLISHED_VERIFIED"})
    write_json(files["ls6at_result"], {"production_status": "PUBLISHED"})

    write_json(tmp_path / LS6AU_VALIDATION_REL, {"status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED"})
    write_json(tmp_path / LS6AT_VALIDATION_REL, {"status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED"})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--ls-mon1-result",
        str(files["ls_mon1_result"]),
        "--ls-mon1-lock",
        str(files["ls_mon1_lock"]),
        "--ls-mon1-validation-result",
        str(files["ls_mon1_validation"]),
        "--ls-close1-result",
        str(files["ls_close1_result"]),
        "--ls-close1-lock",
        str(files["ls_close1_lock"]),
        "--ls-close1-validation-result",
        str(files["ls_close1_validation"]),
        "--ls6au-result",
        str(files["ls6au_result"]),
        "--ls6at-result",
        str(files["ls6at_result"]),
        "--output",
        str(files["output"]),
        "--lock-output",
        str(files["lock_output"]),
        "--report",
        str(files["report"]),
    ]


def run_build(monkeypatch, files: dict[str, Path], cwd: Path) -> dict:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr("sys.argv", build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_1_missing_policy_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    argv = build_argv(files)
    argv[argv.index("--policy") + 1] = str(tmp_path / "missing_policy.json")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", argv)
    main()
    assert read_json(files["output"])["status"] == STATUS_FAILED


def test_2_missing_ls_mon1_result_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["ls_mon1_result"].unlink()
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


def test_3_missing_ls_close1_result_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["ls_close1_result"].unlink()
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


def test_4_ls_mon1_status_mismatch_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["ls_mon1_validation"], ("status",), "WRONG")
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


def test_5_ls_close1_completion_mismatch_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["ls_close1_result"], ("completion_status",), "WRONG")
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


def test_6_ls6au_status_mismatch_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    write_json(tmp_path / LS6AU_VALIDATION_REL, {"status": "WRONG"})
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


def test_7_ls6at_status_mismatch_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    write_json(tmp_path / LS6AT_VALIDATION_REL, {"status": "WRONG"})
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


def test_8_source_post_id_mismatch_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["policy"], ("source_chain", "source_post_id"), 999)
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


@pytest.mark.parametrize("missing_output_key", ["input_schema", "phase_map", "item_template", "safety_contract"])
def test_9_to_12_missing_output_path_failed(monkeypatch, tmp_path: Path, missing_output_key: str) -> None:
    files = make_files(tmp_path)
    data = read_json(files["policy"])
    del data["outputs"][missing_output_key]
    write_json(files["policy"], data)
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_FAILED


def test_13_valid_build_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_build(monkeypatch, files, tmp_path)
    assert out["status"] == STATUS_PASSED


def test_14_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    assert files["output"].exists()


def test_15_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    assert files["lock_output"].exists()


def test_16_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    assert files["report"].exists()


def test_17_input_schema_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    assert files["input_schema"].exists()


def test_18_phase_map_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    assert files["phase_map"].exists()


def test_19_item_template_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    assert files["item_template"].exists()


def test_20_safety_contract_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    assert files["safety_contract"].exists()


@pytest.mark.parametrize(
    "key,expected",
    [
        ("reusable_template_built", True),
        ("input_schema_created", True),
        ("phase_map_created", True),
        ("item_template_created", True),
        ("safety_contract_created", True),
        ("template_execution_allowed_by_this_phase", False),
        ("next_item_creation_allowed_by_this_phase", False),
        ("wordpress_api_call_executed", False),
        ("credential_env_read_executed", False),
        ("publish_executed_by_this_phase", False),
        ("post119_update_executed", False),
        ("next_post_created", False),
        ("rollback_executed", False),
        ("rerun_allowed", False),
    ],
)
def test_21_to_38_result_flags(monkeypatch, tmp_path: Path, key: str, expected) -> None:
    files = make_files(tmp_path)
    out = run_build(monkeypatch, files, tmp_path)
    assert out[key] == expected


def test_26_to_29_parameterized_fields_include_expected(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_build(monkeypatch, files, tmp_path)
    fields = out["parameterized_fields"]
    assert "target_post_id" in fields
    assert "payload_title" in fields
    assert "payload_asin" in fields
    assert "public_url" in fields


def test_39_input_schema_requires_content_item_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    schema = read_json(files["input_schema"])
    assert "content_item_id" in schema["required_fields"]


def test_40_input_schema_requires_target_post_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    schema = read_json(files["input_schema"])
    assert "target_post_id" in schema["required_fields"]


def test_41_input_schema_forbids_119(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    schema = read_json(files["input_schema"])
    assert 119 in schema["forbidden_values"]["target_post_id"]


def test_42_input_schema_human_review_required_true(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    schema = read_json(files["input_schema"])
    assert schema["field_definitions"]["human_review_required"]["required_value"] is True


def test_43_input_schema_execution_allowed_initially_false(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    schema = read_json(files["input_schema"])
    assert schema["field_definitions"]["execution_allowed_initially"]["required_value"] is False


def test_44_to_48_phase_map_includes_required_phases(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    phase_map = read_json(files["phase_map"])
    phases = [item["phase"] for item in phase_map["reusable_sequence"]]
    assert "LS-NEXT-1" in phases
    assert "LS-NEXT-PUBLISH" in phases
    assert "LS-NEXT-VERIFY" in phases
    assert "LS-NEXT-CLOSE" in phases
    assert "LS-NEXT-MON" in phases


def test_49_to_51_safety_contract_rules(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    safety = read_json(files["safety_contract"])
    assert safety["always_forbidden"]["post119_update"] is True
    assert safety["always_forbidden"]["credential_value_output"] is True
    assert safety["always_forbidden"]["publish_without_separated_phase"] is True


def test_52_lock_status_locked_no_execution(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_build(monkeypatch, files, tmp_path)
    lock = read_json(files["lock_output"])
    assert lock["status"] == "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_LOCKED_NO_EXECUTION"


def test_53_result_has_expected_next_action(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_build(monkeypatch, files, tmp_path)
    assert out["recommended_next_action"] == "BEGIN_NEXT_CONTENT_ITEM_WITH_REUSABLE_TEMPLATE_OR_CONTINUE_MONITORING"


def test_54_result_has_expected_phase_options(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_build(monkeypatch, files, tmp_path)
    assert out["recommended_next_phase_options"] == ["LS-NEXT-1", "LS-MON-2", "LS-REUSE-2"]


def test_55_result_errors_empty_on_success(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_build(monkeypatch, files, tmp_path)
    assert out["errors"] == []
