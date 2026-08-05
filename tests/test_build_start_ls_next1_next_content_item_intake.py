from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/build_start_ls_next1_next_content_item_intake.py"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {
        "phase": "LS-NEXT-1",
        "required_previous_phase": {
            "ls_reuse1": {
                "required_run_status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION",
                "required_validation_status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION",
                "required_production_status": "NO_EXECUTION_REUSE_TEMPLATE_ONLY",
                "required_source_post_id": 183,
                "required_reusable_template_built": True,
                "required_input_schema_created": True,
                "required_phase_map_created": True,
                "required_item_template_created": True,
                "required_safety_contract_created": True,
            }
        },
        "intake_policy": {
            "human_input_required": True,
            "human_review_required": True,
            "execution_allowed_initially": False,
        },
        "must_remain_false_flags": {
            "wordpress_api_call_executed": False,
            "wordpress_get_executed": False,
            "wordpress_post_executed": False,
            "wordpress_put_executed": False,
            "wordpress_patch_executed": False,
            "wordpress_delete_executed": False,
            "wordpress_write_executed_by_this_phase": False,
            "publish_executed_by_this_phase": False,
            "next_post_created": False,
            "next_post_selected_by_ai": False,
            "post119_update_executed": False,
            "post183_update_executed_by_this_phase": False,
            "wordpress_new_post_executed": False,
            "wordpress_content_update_executed": False,
            "wordpress_title_update_executed": False,
            "wordpress_meta_update_executed": False,
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
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_generated": False,
            "authorization_header_output": False,
            "basic_auth_string_generated": False,
            "basic_auth_string_output": False,
            "actual_publish_execution_runner_executed": False,
            "manual_publish_executed": False,
            "external_api_call_executed": False,
            "amazon_api_call_executed": False,
            "pa_api_call_executed": False,
            "creators_api_call_executed": False,
            "x_api_call_executed": False,
            "rerun_allowed": False,
            "publish_rerun_allowed": False,
        },
        "next_phase": {
            "recommended_next_action": "FILL_NEXT_CONTENT_ITEM_INTAKE_OR_CONTINUE_MONITORING",
            "recommended_next_phase_options": [
                "LS-NEXT-1-FILL",
                "LS-MON-2",
                "LS-NEXT-2_AFTER_HUMAN_INPUT",
            ],
        },
    }


def _base_reuse1_result() -> dict:
    return {
        "status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION",
        "production_status": "NO_EXECUTION_REUSE_TEMPLATE_ONLY",
        "source_post_id": 183,
        "reusable_template_built": True,
        "input_schema_created": True,
        "phase_map_created": True,
        "item_template_created": True,
        "safety_contract_created": True,
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "ls_reuse1_result": tmp_path / "exchange/runtime/reuse1_result.json",
        "ls_reuse1_lock": tmp_path / "exchange/locks/reuse1.lock.json",
        "ls_reuse1_run": tmp_path / "exchange/logs/reuse1_run.json",
        "ls_reuse1_validation": tmp_path / "exchange/logs/reuse1_validation.json",
        "input_schema": tmp_path / "config/input_schema.json",
        "phase_map": tmp_path / "config/phase_map.json",
        "item_template": tmp_path / "exchange/templates/item.template.json",
        "safety_contract": tmp_path / "exchange/templates/safety_contract.json",
        "intake_template": tmp_path / "exchange/intake/intake.template.json",
        "intake_record": tmp_path / "exchange/intake/intake.json",
        "output": tmp_path / "exchange/runtime/next1_result.json",
        "lock_output": tmp_path / "exchange/locks/next1.lock.json",
        "report": tmp_path / "reports/next1_report.md",
    }

    _write(paths["policy"], _base_policy())
    reuse = _base_reuse1_result()
    _write(paths["ls_reuse1_result"], reuse)
    _write(paths["ls_reuse1_run"], reuse)
    _write(
        paths["ls_reuse1_validation"],
        {"status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION"},
    )
    _write(paths["ls_reuse1_lock"], {"locked": True})

    _write(paths["input_schema"], {"schema_name": "START_LS_REUSABLE_PUBLISH_CHAIN_INPUT_SCHEMA"})
    _write(paths["phase_map"], {"reusable_sequence": [{"phase": "LS-NEXT-PUBLISH"}]})
    _write(paths["item_template"], {"template_name": "START_LS_REUSABLE_PUBLISH_CHAIN_ITEM_TEMPLATE"})
    _write(paths["safety_contract"], {"always_forbidden": {"publish": True}})

    return paths


def _run(paths: dict[str, Path], extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--ls-reuse1-result",
        str(paths["ls_reuse1_result"]),
        "--ls-reuse1-lock",
        str(paths["ls_reuse1_lock"]),
        "--ls-reuse1-run-result",
        str(paths["ls_reuse1_run"]),
        "--ls-reuse1-validation-result",
        str(paths["ls_reuse1_validation"]),
        "--input-schema",
        str(paths["input_schema"]),
        "--phase-map",
        str(paths["phase_map"]),
        "--item-template",
        str(paths["item_template"]),
        "--safety-contract",
        str(paths["safety_contract"]),
        "--intake-template-output",
        str(paths["intake_template"]),
        "--intake-record-output",
        str(paths["intake_record"]),
        "--output",
        str(paths["output"]),
        "--lock-output",
        str(paths["lock_output"]),
        "--report",
        str(paths["report"]),
        "--create-intake-template",
        "--require-human-input",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-publish",
        "--require-no-next-post-creation",
        "--forbid-post119-update",
        "--forbid-post183-update",
        "--forbid-auto-content-selection",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_build_success(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0, proc.stderr

    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    lock_payload = json.loads(paths["lock_output"].read_text(encoding="utf-8"))
    intake_template = json.loads(paths["intake_template"].read_text(encoding="utf-8"))
    intake_record = json.loads(paths["intake_record"].read_text(encoding="utf-8"))

    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["ready_for_ls_next_2"] is False
    assert payload["target_post_id"] is None
    assert payload["intake_template_created"] is True
    assert payload["intake_record_created"] is True
    assert payload["intake_registration_completed"] is False
    assert payload["human_input_required"] is True
    assert payload["next_post_selected_by_ai"] is False
    assert payload["post119_update_executed"] is False
    assert payload["post183_update_executed_by_this_phase"] is False
    assert payload["errors"] == []

    assert lock_payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_LOCKED_NO_EXECUTION"
    assert lock_payload["locked"] is True

    assert intake_template["document_type"] == "START_LS_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE"
    assert intake_template["target_post_id"] is None
    assert intake_template["execution_allowed"] is False

    assert intake_record["document_type"] == "START_LS_NEXT_CONTENT_ITEM_INTAKE_RECORD"
    assert intake_record["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_WAITING_FOR_HUMAN_INPUT"
    assert intake_record["ready_for_ls_next_2"] is False


def test_build_fails_when_flag_missing(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--ls-reuse1-result",
        str(paths["ls_reuse1_result"]),
        "--ls-reuse1-lock",
        str(paths["ls_reuse1_lock"]),
        "--ls-reuse1-run-result",
        str(paths["ls_reuse1_run"]),
        "--ls-reuse1-validation-result",
        str(paths["ls_reuse1_validation"]),
        "--input-schema",
        str(paths["input_schema"]),
        "--phase-map",
        str(paths["phase_map"]),
        "--item-template",
        str(paths["item_template"]),
        "--safety-contract",
        str(paths["safety_contract"]),
        "--intake-template-output",
        str(paths["intake_template"]),
        "--intake-record-output",
        str(paths["intake_record"]),
        "--output",
        str(paths["output"]),
        "--lock-output",
        str(paths["lock_output"]),
        "--report",
        str(paths["report"]),
        "--create-intake-template",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-publish",
        "--require-no-next-post-creation",
        "--forbid-post119-update",
        "--forbid-post183-update",
        "--forbid-auto-content-selection",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert proc.returncode == 0

    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("missing --require-human-input" in e for e in payload["errors"])


def test_build_fails_when_reuse_validation_bad(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_reuse1_validation"], {"status": "BAD"})
    proc = _run(paths)
    assert proc.returncode == 0

    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("LS-REUSE-1 validation mismatch" in e for e in payload["errors"])


def test_build_fails_when_reuse_run_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_reuse1_run"], {"status": "DIFFERENT"})
    proc = _run(paths)
    assert proc.returncode == 0

    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("LS-REUSE-1 run result mismatch" in e for e in payload["errors"])


def test_build_fails_when_required_file_missing(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["phase_map"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0

    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("missing file" in e and "phase_map.json" in e for e in payload["errors"])


def test_build_keeps_all_sensitive_flags_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0

    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    must_false = [
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "authorization_header_generated",
        "authorization_header_output",
        "basic_auth_string_generated",
        "basic_auth_string_output",
        "publish_executed_by_this_phase",
        "external_api_call_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
    ]
    for key in must_false:
        assert payload[key] is False


def test_build_report_written(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    report = paths["report"].read_text(encoding="utf-8")
    assert "LS-NEXT-1 Next Content Item Intake Report" in report
    assert "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION" in report


def test_build_intake_record_missing_fields_list(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    record = json.loads(paths["intake_record"].read_text(encoding="utf-8"))
    expected = {
        "content_item_id",
        "target_post_id",
        "target_post_link",
        "payload_title",
        "payload_asin",
        "public_url",
        "public_rest_url",
    }
    assert set(record["missing_required_human_fields"]) == expected


def test_build_recommended_next_action_from_policy(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    policy = _base_policy()
    policy["next_phase"]["recommended_next_action"] = "CUSTOM_NEXT"
    _write(paths["policy"], policy)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["recommended_next_action"] == "CUSTOM_NEXT"


def test_build_source_post_id_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    reuse = _base_reuse1_result()
    reuse["source_post_id"] = 999
    _write(paths["ls_reuse1_result"], reuse)
    _write(paths["ls_reuse1_run"], reuse)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("source_post_id mismatch" in e for e in payload["errors"])


def test_build_lock_written_even_on_failure(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_reuse1_lock"], {"locked": False})
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    lock_payload = json.loads(paths["lock_output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert lock_payload["locked"] is False


def test_build_missing_policy_file(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("missing file" in e and "policy.json" in e for e in payload["errors"])


def test_build_invalid_policy_json(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].write_text("{", encoding="utf-8")
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("invalid json" in e for e in payload["errors"])


def test_build_missing_item_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["item_template"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("item template unavailable" in e for e in payload["errors"])


def test_build_missing_safety_contract(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["safety_contract"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("safety contract unavailable" in e for e in payload["errors"])


def test_build_missing_input_schema(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["input_schema"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("input schema unavailable" in e for e in payload["errors"])


def test_build_missing_reuse_lock(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls_reuse1_lock"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("reuse1.lock.json" in e for e in payload["errors"])


def test_build_missing_reuse_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls_reuse1_result"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("reuse1_result.json" in e for e in payload["errors"])


def test_build_missing_reuse_validation(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls_reuse1_validation"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("reuse1_validation.json" in e for e in payload["errors"])


def test_build_missing_reuse_run(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls_reuse1_run"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("reuse1_run.json" in e for e in payload["errors"])


def test_build_missing_create_template_flag(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--ls-reuse1-result",
        str(paths["ls_reuse1_result"]),
        "--ls-reuse1-lock",
        str(paths["ls_reuse1_lock"]),
        "--ls-reuse1-run-result",
        str(paths["ls_reuse1_run"]),
        "--ls-reuse1-validation-result",
        str(paths["ls_reuse1_validation"]),
        "--input-schema",
        str(paths["input_schema"]),
        "--phase-map",
        str(paths["phase_map"]),
        "--item-template",
        str(paths["item_template"]),
        "--safety-contract",
        str(paths["safety_contract"]),
        "--intake-template-output",
        str(paths["intake_template"]),
        "--intake-record-output",
        str(paths["intake_record"]),
        "--output",
        str(paths["output"]),
        "--lock-output",
        str(paths["lock_output"]),
        "--report",
        str(paths["report"]),
        "--require-human-input",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-publish",
        "--require-no-next-post-creation",
        "--forbid-post119-update",
        "--forbid-post183-update",
        "--forbid-auto-content-selection",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
    assert any("missing --create-intake-template" in e for e in payload["errors"])


def test_build_lock_status_pass_case(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    lock_payload = json.loads(paths["lock_output"].read_text(encoding="utf-8"))
    assert lock_payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_LOCKED_NO_EXECUTION"


def test_build_missing_fields_on_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    expected = {
        "content_item_id",
        "target_post_id",
        "target_post_link",
        "payload_title",
        "payload_asin",
        "public_url",
        "public_rest_url",
    }
    assert set(payload["missing_required_human_fields"]) == expected


def test_build_result_has_no_execution_mode(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["execution_mode"] == "INTAKE_TEMPLATE_AND_GATE_ONLY_NO_EXECUTION"
    assert payload["production_status"] == "NO_EXECUTION_NEXT_ITEM_INTAKE_ONLY"


def test_build_next_phase_options_default(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["recommended_next_phase_options"] == [
        "LS-NEXT-1-FILL",
        "LS-MON-2",
        "LS-NEXT-2_AFTER_HUMAN_INPUT",
    ]


def test_build_lock_includes_gate_fields(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    lock_payload = json.loads(paths["lock_output"].read_text(encoding="utf-8"))
    assert lock_payload["execution_allowed"] is False
    assert lock_payload["ready_for_ls_next_2"] is False
    assert lock_payload["target_post_id"] is None


def test_build_generates_json_stdout(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    parsed = json.loads(proc.stdout)
    assert parsed["phase"] == "LS-NEXT-1"


def test_build_fails_when_reuse_lock_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_reuse1_lock"], {"locked": False})
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("LS-REUSE-1 lock mismatch" in e for e in payload["errors"])


def test_build_no_target_post_id_before_human_input(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["target_post_id"] is None


def test_build_policy_phase_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    policy = _base_policy()
    policy["phase"] = "OTHER"
    _write(paths["policy"], policy)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("policy.phase mismatch" in e for e in payload["errors"])


def test_build_reuse_production_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    reuse = _base_reuse1_result()
    reuse["production_status"] = "BAD"
    _write(paths["ls_reuse1_result"], reuse)
    _write(paths["ls_reuse1_run"], reuse)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("production mismatch" in e for e in payload["errors"])


def test_build_reuse_capability_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    reuse = _base_reuse1_result()
    reuse["item_template_created"] = False
    _write(paths["ls_reuse1_result"], reuse)
    _write(paths["ls_reuse1_run"], reuse)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("item_template_created mismatch" in e for e in payload["errors"])


def test_build_output_files_exist(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    for key in ["output", "lock_output", "report", "intake_template", "intake_record"]:
        assert paths[key].exists(), key


def test_build_intake_template_core_fields(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    template = json.loads(paths["intake_template"].read_text(encoding="utf-8"))
    assert template["auto_content_selection_allowed"] is False
    assert template["next_post_creation_allowed"] is False
    assert template["wordpress_write_allowed"] is False
    assert template["publish_allowed"] is False


def test_build_intake_record_core_fields(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    record = json.loads(paths["intake_record"].read_text(encoding="utf-8"))
    assert record["execution_allowed"] is False
    assert record["intake_registration_completed"] is False


def test_build_errors_empty_on_success(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["errors"] == []


def test_build_errors_non_empty_on_failure(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["item_template"].unlink()
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["errors"]


def test_build_validation_anchor_flags(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["ls_reuse1_validated"] is True
    assert payload["reusable_template_available"] is True


def test_build_report_contains_recommended_action(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    report = paths["report"].read_text(encoding="utf-8")
    assert "recommended_next_action" in report


def test_build_missing_required_field_list_stable(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["missing_required_human_fields"][0] == "content_item_id"
