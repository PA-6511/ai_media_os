from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/validate_start_ls_next1_next_content_item_intake.py"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {
        "intake_policy": {
            "human_input_required": True,
            "human_review_required": True,
            "execution_allowed_initially": False,
        },
        "next_phase": {
            "recommended_next_action": "FILL_NEXT_CONTENT_ITEM_INTAKE_OR_CONTINUE_MONITORING"
        },
    }


def _base_result() -> dict:
    return {
        "phase": "LS-NEXT-1",
        "status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION",
        "execution_mode": "INTAKE_TEMPLATE_AND_GATE_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_NEXT_ITEM_INTAKE_ONLY",
        "ls_reuse1_validated": True,
        "reusable_template_available": True,
        "input_schema_available": True,
        "phase_map_available": True,
        "item_template_available": True,
        "safety_contract_available": True,
        "intake_template_created": True,
        "intake_record_created": True,
        "intake_registration_completed": False,
        "human_input_required": True,
        "human_review_required": True,
        "execution_allowed_initially": False,
        "execution_allowed": False,
        "ready_for_ls_next_2": False,
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "public_url": "",
        "public_rest_url": "",
        "missing_required_human_fields": [
            "content_item_id",
            "target_post_id",
            "target_post_link",
            "payload_title",
            "payload_asin",
            "public_url",
            "public_rest_url",
        ],
        "auto_content_selection_allowed": False,
        "next_post_creation_allowed": False,
        "template_execution_allowed_by_this_phase": False,
        "next_item_creation_allowed_by_this_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "next_post_created": False,
        "next_post_selected_by_ai": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "external_api_call_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "locked": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": "FILL_NEXT_CONTENT_ITEM_INTAKE_OR_CONTINUE_MONITORING",
        "recommended_next_phase_options": [
            "LS-NEXT-1-FILL",
            "LS-MON-2",
            "LS-NEXT-2_AFTER_HUMAN_INPUT",
        ],
        "errors": [],
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "template": tmp_path / "exchange/intake/template.json",
        "record": tmp_path / "exchange/intake/record.json",
        "reuse1": tmp_path / "exchange/runtime/reuse1_result.json",
        "input_schema": tmp_path / "config/input_schema.json",
        "phase_map": tmp_path / "config/phase_map.json",
        "item_template": tmp_path / "exchange/templates/item.template.json",
        "safety_contract": tmp_path / "exchange/templates/safety_contract.json",
        "output": tmp_path / "exchange/logs/validation_result.json",
        "report": tmp_path / "reports/validation_report.md",
    }

    _write(paths["policy"], _base_policy())
    base = _base_result()
    _write(paths["result"], base)
    _write(paths["run_result"], base)
    _write(
        paths["lock"],
        {
            "status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_LOCKED_NO_EXECUTION",
            "locked": True,
        },
    )
    _write(paths["template"], {"document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE"})
    _write(paths["record"], {"document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_RECORD"})
    _write(
        paths["reuse1"],
        {"status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION"},
    )
    _write(paths["input_schema"], {"schema_name": "START_LS_REUSABLE_PUBLISH_CHAIN_INPUT_SCHEMA"})
    _write(paths["phase_map"], {"reusable_sequence": [{"phase": "LS-NEXT-PUBLISH"}]})
    _write(paths["item_template"], {"template_name": "START_LS_REUSABLE_PUBLISH_CHAIN_ITEM_TEMPLATE"})
    _write(paths["safety_contract"], {"always_forbidden": {"publish": True}})
    return paths


def _run(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--intake-result",
        str(paths["result"]),
        "--intake-lock",
        str(paths["lock"]),
        "--run-result",
        str(paths["run_result"]),
        "--intake-template",
        str(paths["template"]),
        "--intake-record",
        str(paths["record"]),
        "--ls-reuse1-result",
        str(paths["reuse1"]),
        "--input-schema",
        str(paths["input_schema"]),
        "--phase-map",
        str(paths["phase_map"]),
        "--item-template",
        str(paths["item_template"]),
        "--safety-contract",
        str(paths["safety_contract"]),
        "--output",
        str(paths["output"]),
        "--report",
        str(paths["report"]),
    ]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_validate_success(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_VALIDATED_NO_EXECUTION"


def test_validate_fail_when_run_status_bad(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["status"] = "BAD"
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_fail_when_run_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    other = _base_result()
    other["content_item_id"] = "X"
    _write(paths["run_result"], other)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"
    assert any("run result mismatch" in e for e in payload["errors"])


def test_validate_fail_target_post_forbidden_119(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["target_post_id"] = 119
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("target_post_id forbidden" in e for e in payload["errors"])


def test_validate_fail_target_post_forbidden_183(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["target_post_id"] = 183
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("target_post_id forbidden" in e for e in payload["errors"])


def test_validate_fail_when_flag_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["publish_executed_by_this_phase"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("publish_executed_by_this_phase" in e for e in payload["errors"])


def test_validate_fail_when_template_missing(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["template"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_fail_when_record_missing(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["record"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_fail_when_reuse1_bad(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["reuse1"], {"status": "BAD"})
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("LS-REUSE-1 status mismatch" in e for e in payload["errors"])


def test_validate_fail_when_schema_bad(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["input_schema"], {"schema_name": "BAD"})
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("input schema mismatch" in e for e in payload["errors"])


def test_validate_fail_when_phase_map_bad(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["phase_map"], {"reusable_sequence": [{"phase": "NOPE"}]})
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("phase map missing LS-NEXT-PUBLISH" in e for e in payload["errors"])


def test_validate_fail_when_item_template_bad(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["item_template"], {"template_name": "BAD"})
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("item template mismatch" in e for e in payload["errors"])


def test_validate_fail_when_safety_contract_bad(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["safety_contract"], {"x": 1})
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("safety contract mismatch" in e for e in payload["errors"])


def test_validate_fail_recommended_action_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["recommended_next_action"] = "BAD"
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("recommended_next_action mismatch" in e for e in payload["errors"])


def test_validate_fail_lock_status(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["lock"], {"status": "BAD", "locked": True})
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("lock status mismatch" in e for e in payload["errors"])


def test_validate_fail_lock_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(
        paths["lock"],
        {
            "status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_LOCKED_NO_EXECUTION",
            "locked": False,
        },
    )
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("lock mismatch" in e for e in payload["errors"])


def test_validate_fail_execution_allowed_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["execution_allowed"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("execution_allowed mismatch" in e for e in payload["errors"])


def test_validate_fail_ready_for_next2_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["ready_for_ls_next_2"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("ready_for_ls_next_2 mismatch" in e for e in payload["errors"])


def test_validate_fail_auto_selection_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["auto_content_selection_allowed"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("auto_content_selection_allowed mismatch" in e for e in payload["errors"])


def test_validate_fail_next_post_creation_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["next_post_creation_allowed"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("next_post_creation_allowed mismatch" in e for e in payload["errors"])


def test_validate_fail_human_input_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["human_input_required"] = False
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("human_input_required mismatch" in e for e in payload["errors"])


def test_validate_fail_human_review_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["human_review_required"] = False
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("human_review_required mismatch" in e for e in payload["errors"])


def test_validate_fail_initial_execution_allowed_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["execution_allowed_initially"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("execution_allowed_initially mismatch" in e for e in payload["errors"])


def test_validate_fail_registration_completed_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["intake_registration_completed"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("intake_registration_completed mismatch" in e for e in payload["errors"])


def test_validate_report_written(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    report = paths["report"].read_text(encoding="utf-8")
    assert "Validation Report" in report


def test_validate_stdout_is_json(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["phase"] == "LS-NEXT-1"


def test_validate_missing_policy(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["result"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_run_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["run_result"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_lock(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["lock"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_reuse1(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["reuse1"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_schema(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["input_schema"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_phase_map(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["phase_map"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_item_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["item_template"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_missing_safety_contract(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["safety_contract"].unlink()
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def test_validate_error_list_present_on_failure(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["credential_secret_output"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["errors"]


def test_validate_error_list_empty_on_success(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["errors"] == []


def test_validate_copies_fields(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["content_item_id"] == ""
    assert payload["target_post_id"] is None


def test_validate_detects_publish_rerun_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["publish_rerun_allowed"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("publish_rerun_allowed" in e for e in payload["errors"])


def test_validate_detects_rerun_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["rerun_allowed"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("rerun_allowed" in e for e in payload["errors"])


def test_validate_detects_external_call_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["external_api_call_executed"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("external_api_call_executed" in e for e in payload["errors"])


def test_validate_detects_auth_header_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["authorization_header_generated"] = True
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert any("authorization_header_generated" in e for e in payload["errors"])


def test_validate_detects_lock_false_in_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    data = _base_result()
    data["locked"] = False
    _write(paths["result"], data)
    _write(paths["run_result"], data)
    _run(paths)
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["locked"] is False
