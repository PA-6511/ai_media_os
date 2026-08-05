from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/validate_start_ls_next1_fill_human_content_item_intake.py"
BUILD_SCRIPT = Path("scripts/build_start_ls_next1_fill_human_content_item_intake.py")
VALIDATE_SCRIPT = Path("scripts/validate_start_ls_next1_fill_human_content_item_intake.py")


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {
        "next_phase": {
            "recommended_next_action_if_valid": "BEGIN_LS_NEXT_2_DRAFT_STATUS_AND_PAYLOAD_DRY_RUN",
            "recommended_next_action_if_missing": "WAIT_FOR_HUMAN_INPUT",
        }
    }


def _base_waiting_result() -> dict:
    return {
        "phase": "LS-NEXT-1-FILL",
        "document_type": "START_LS_NEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_RESULT",
        "status": "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION",
        "execution_mode": "HUMAN_INPUT_REGISTRATION_ONLY_NO_EXECUTION",
        "production_status": "WAITING_FOR_HUMAN_INPUT_NO_EXECUTION",
        "ls_next1_validated": True,
        "ls_reuse1_validated": True,
        "human_input_template_created": True,
        "human_input_record_exists": True,
        "human_filled": False,
        "human_confirmed": False,
        "human_input_required": True,
        "intake_registration_completed": False,
        "ready_for_ls_next_2": False,
        "execution_allowed": False,
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
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "publish_executed_by_this_phase": False,
        "next_post_created": False,
        "next_post_selected_by_ai": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "external_api_call_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
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
        "locked": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": "WAIT_FOR_HUMAN_INPUT",
        "recommended_next_phase_options": ["LS-NEXT-1-FILL_AFTER_HUMAN_INPUT", "LS-MON-2"],
        "errors": [],
    }


def _base_filled_result() -> dict:
    d = _base_waiting_result()
    d.update(
        {
            "status": "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_PASSED_NO_EXECUTION",
            "production_status": "NO_EXECUTION_HUMAN_INTAKE_FILLED",
            "human_filled": True,
            "human_confirmed": True,
            "human_input_required": False,
            "intake_registration_completed": True,
            "ready_for_ls_next_2": True,
            "content_item_id": "NEXT-001",
            "target_post_id": 555,
            "target_post_link": "https://example.com/?p=555",
            "payload_title": "Human Title",
            "payload_asin": "B000000001",
            "public_url": "https://example.com/post-555",
            "public_rest_url": "https://example.com/wp-json/wp/v2/posts/555",
            "missing_required_human_fields": [],
            "recommended_next_action": "BEGIN_LS_NEXT_2_DRAFT_STATUS_AND_PAYLOAD_DRY_RUN",
            "recommended_next_phase_options": ["LS-NEXT-2_AFTER_HUMAN_INPUT", "LS-MON-2"],
        }
    )
    return d


def _prepare(tmp_path: Path, filled: bool = False) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "human_template": tmp_path / "exchange/intake/template.json",
        "human_record": tmp_path / "exchange/intake/input.json",
        "filled_intake": tmp_path / "exchange/intake/filled.json",
        "ls_next1_result": tmp_path / "exchange/runtime/ls_next1.json",
        "ls_reuse1_result": tmp_path / "exchange/runtime/ls_reuse1.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    _write(paths["policy"], _base_policy())
    result = _base_filled_result() if filled else _base_waiting_result()
    _write(paths["result"], result)
    _write(paths["run"], result)
    _write(
        paths["lock"],
        {
            "status": "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_LOCKED_NO_EXECUTION"
            if filled
            else "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_LOCKED_NO_EXECUTION",
            "locked": True,
        },
    )
    _write(paths["human_template"], {"document_type": "START_LS_NEXT1_FILL_HUMAN_INPUT_TEMPLATE"})
    _write(paths["human_record"], {"document_type": "START_LS_NEXT1_FILL_HUMAN_INPUT_RECORD"})
    _write(paths["filled_intake"], {"phase": "LS-NEXT-1-FILL"})
    _write(paths["ls_next1_result"], {"status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION"})
    _write(
        paths["ls_reuse1_result"],
        {"status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION"},
    )
    return paths


def _run(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy", str(paths["policy"]),
        "--result", str(paths["result"]),
        "--lock", str(paths["lock"]),
        "--run-result", str(paths["run"]),
        "--human-input-template", str(paths["human_template"]),
        "--human-input-record", str(paths["human_record"]),
        "--filled-intake-record", str(paths["filled_intake"]),
        "--ls-next1-result", str(paths["ls_next1_result"]),
        "--ls-reuse1-result", str(paths["ls_reuse1_result"]),
        "--output", str(paths["output"]),
        "--report", str(paths["report"]),
    ]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _payload(paths: dict[str, Path]) -> dict:
    return json.loads(paths["output"].read_text(encoding="utf-8"))


# 54-60

def test_validation_waiting_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=False)
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_VALIDATED_NO_EXECUTION"


def test_validation_filled_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_VALIDATED_NO_EXECUTION"


def test_validation_detects_missing_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["result"].unlink()
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_NOT_VALIDATED"


def test_validation_detects_missing_lock(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["lock"].unlink()
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_NOT_VALIDATED"


def test_validation_detects_missing_run_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["run"].unlink()
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_NOT_VALIDATED"


def test_validation_detects_missing_human_input_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["human_template"].unlink()
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_NOT_VALIDATED"


def test_validation_detects_missing_human_input_record(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["human_record"].unlink()
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_NOT_VALIDATED"


# 61-70

def test_validation_detects_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["status"] = "BAD"
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("status mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_production_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["production_status"] = "BAD"
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("production_status mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_human_filled_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["human_filled"] = True
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("human_filled mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_human_confirmed_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["human_confirmed"] = True
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("human_confirmed mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_ready_true_while_missing(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["ready_for_ls_next_2"] = True
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("ready_for_ls_next_2=true while missing fields" in e for e in _payload(paths)["errors"])


def test_validation_detects_execution_allowed_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["execution_allowed"] = True
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("execution_allowed=true" in e for e in _payload(paths)["errors"])


def test_validation_detects_target_post_id_119(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    d = _base_filled_result()
    d["target_post_id"] = 119
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("target_post_id forbidden" in e for e in _payload(paths)["errors"])


def test_validation_detects_target_post_id_183(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    d = _base_filled_result()
    d["target_post_id"] = 183
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("target_post_id forbidden" in e for e in _payload(paths)["errors"])


def test_validation_detects_auto_content_selection_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["auto_content_selection_allowed"] = True
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("auto_content_selection_allowed=true" in e for e in _payload(paths)["errors"])


def test_validation_detects_next_post_creation_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["next_post_creation_allowed"] = True
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("next_post_creation_allowed=true" in e for e in _payload(paths)["errors"])


# 71-87

_TRUE_FLAG_CASES = [
    "wordpress_api_call_executed",
    "credential_env_read_executed",
    "publish_executed_by_this_phase",
    "next_post_created",
    "next_post_selected_by_ai",
    "post119_update_executed",
    "post183_update_executed_by_this_phase",
    "external_api_call_executed",
    "amazon_api_call_executed",
    "pa_api_call_executed",
    "creators_api_call_executed",
    "x_api_call_executed",
    "secret_length_output",
    "secret_hash_output",
    "authorization_header_output",
    "rerun_allowed",
]


def test_validation_true_flag_cases(tmp_path: Path) -> None:
    for key in _TRUE_FLAG_CASES:
        paths = _prepare(tmp_path / key)
        d = _base_waiting_result()
        d[key] = True
        _write(paths["result"], d)
        _write(paths["run"], d)
        _run(paths)
        assert any(key in e for e in _payload(paths)["errors"])


def test_validation_detects_recommended_next_action_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_waiting_result()
    d["recommended_next_action"] = "BAD"
    _write(paths["result"], d)
    _write(paths["run"], d)
    _run(paths)
    assert any("recommended_next_action mismatch" in e for e in _payload(paths)["errors"])


# 88-94

def test_source_has_no_requests_call() -> None:
    assert "requests." not in BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "requests." not in VALIDATE_SCRIPT.read_text(encoding="utf-8")


def test_source_has_no_urllib_request() -> None:
    assert "urllib.request" not in BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "urllib.request" not in VALIDATE_SCRIPT.read_text(encoding="utf-8")


def test_source_has_no_wp_json_literal() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8") + VALIDATE_SCRIPT.read_text(encoding="utf-8")
    assert "wp-json" not in text


def test_source_has_no_credential_env_open() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8") + VALIDATE_SCRIPT.read_text(encoding="utf-8")
    assert "credential.env" not in text


def test_source_has_no_authorization_output() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8") + VALIDATE_SCRIPT.read_text(encoding="utf-8")
    assert "Authorization:" not in text


def test_source_has_no_basic_string_output() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8") + VALIDATE_SCRIPT.read_text(encoding="utf-8")
    assert "print(\"Basic" not in text
    assert "print('Basic" not in text


def test_source_has_no_base64_import_or_use() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8") + VALIDATE_SCRIPT.read_text(encoding="utf-8")
    assert "base64" not in text


def test_validation_report_written(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths["report"].exists()


def test_validation_stdout_json(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    assert json.loads(proc.stdout)["phase"] == "LS-NEXT-1-FILL"


def test_validation_output_generated(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths["output"].exists()


def test_validation_detects_run_result_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    other = _base_waiting_result()
    other["content_item_id"] = "DIFF"
    _write(paths["run"], other)
    _run(paths)
    assert any("run result mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_missing_filled_intake_record(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["filled_intake"].unlink()
    _run(paths)
    assert _payload(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_NOT_VALIDATED"


def test_validation_detects_lock_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["lock"], {"status": "BAD", "locked": True})
    _run(paths)
    assert any("lock status mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_lock_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["lock"], {"status": "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_LOCKED_NO_EXECUTION", "locked": False})
    _run(paths)
    assert any("lock mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_ls_next1_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_next1_result"], {"status": "BAD"})
    _run(paths)
    assert any("LS-NEXT-1 status mismatch" in e for e in _payload(paths)["errors"])


def test_validation_detects_ls_reuse1_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_reuse1_result"], {"status": "BAD"})
    _run(paths)
    assert any("LS-REUSE-1 status mismatch" in e for e in _payload(paths)["errors"])
