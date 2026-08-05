from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/build_start_ls_next1_fill_human_content_item_intake.py"

REQUIRED_FIELDS = [
    "content_item_id",
    "target_post_id",
    "target_post_link",
    "payload_title",
    "payload_asin",
    "public_url",
    "public_rest_url",
]


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {
        "phase": "LS-NEXT-1-FILL",
        "required_previous_phase": {
            "ls_next1": {
                "required_run_status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION",
                "required_validation_status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_VALIDATED_NO_EXECUTION",
                "required_production_status": "NO_EXECUTION_NEXT_ITEM_INTAKE_ONLY",
                "required_human_input_required": True,
                "required_execution_allowed": False,
                "required_ready_for_ls_next_2": False,
            },
            "ls_reuse1": {
                "required_validation_status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION",
                "required_reusable_template_built": True,
            },
        },
        "human_input_policy": {
            "ready_for_ls_next_2_if_valid": True,
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
            "recommended_next_action_if_valid": "BEGIN_LS_NEXT_2_DRAFT_STATUS_AND_PAYLOAD_DRY_RUN",
            "recommended_next_action_if_missing": "WAIT_FOR_HUMAN_INPUT",
            "recommended_next_phase_options": [
                "LS-NEXT-2_AFTER_HUMAN_INPUT",
                "LS-MON-2",
            ],
        },
    }


def _base_ls_next1_result() -> dict:
    return {
        "status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION",
        "production_status": "NO_EXECUTION_NEXT_ITEM_INTAKE_ONLY",
        "human_input_required": True,
        "execution_allowed": False,
        "ready_for_ls_next_2": False,
    }


def _base_human_record() -> dict:
    return {
        "document_type": "START_LS_NEXT1_FILL_HUMAN_INPUT_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1-FILL",
        "status": "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT",
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "public_url": "",
        "public_rest_url": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "human_filled": False,
        "human_confirmed": False,
        "execution_allowed": False,
        "ready_for_ls_next_2": False,
        "missing_required_human_fields": list(REQUIRED_FIELDS),
        "errors": [],
    }


def _filled_human_record() -> dict:
    return {
        "document_type": "START_LS_NEXT1_FILL_HUMAN_INPUT_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1-FILL",
        "status": "LSNEXT1_FILL_HUMAN_INPUT_FILLED",
        "content_item_id": "NEXT-001",
        "target_post_id": 555,
        "target_post_link": "https://example.com/?p=555",
        "payload_title": "Human Title",
        "payload_asin": "B000000001",
        "public_url": "https://example.com/post-555",
        "public_rest_url": "https://example.com/wp-json/wp/v2/posts/555",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "human_filled": True,
        "human_confirmed": True,
        "execution_allowed": False,
        "ready_for_ls_next_2": False,
        "missing_required_human_fields": [],
        "errors": [],
    }


def _prepare(tmp_path: Path, create_human_record: bool = True, filled: bool = False) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "ls_next1_result": tmp_path / "exchange/runtime/next1_result.json",
        "ls_next1_lock": tmp_path / "exchange/locks/next1.lock.json",
        "ls_next1_run": tmp_path / "exchange/logs/next1_run.json",
        "ls_next1_validation": tmp_path / "exchange/logs/next1_validation.json",
        "ls_next1_template": tmp_path / "exchange/intake/next1.template.json",
        "ls_next1_record": tmp_path / "exchange/intake/next1.json",
        "ls_reuse1_result": tmp_path / "exchange/runtime/reuse1_result.json",
        "human_template": tmp_path / "exchange/intake/fill.template.json",
        "human_record": tmp_path / "exchange/intake/fill.input.json",
        "filled_output": tmp_path / "exchange/intake/filled_intake.json",
        "output": tmp_path / "exchange/runtime/fill_result.json",
        "lock_output": tmp_path / "exchange/locks/fill.lock.json",
        "report": tmp_path / "reports/fill_report.md",
    }

    _write(paths["policy"], _base_policy())
    next1 = _base_ls_next1_result()
    _write(paths["ls_next1_result"], next1)
    _write(paths["ls_next1_run"], next1)
    _write(
        paths["ls_next1_validation"],
        {"status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_VALIDATED_NO_EXECUTION"},
    )
    _write(paths["ls_next1_lock"], {"locked": True})
    _write(paths["ls_next1_template"], {"document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE"})
    _write(paths["ls_next1_record"], {"document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_RECORD"})
    _write(
        paths["ls_reuse1_result"],
        {
            "status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION",
            "reusable_template_built": True,
        },
    )

    _write(paths["human_template"], {
        "document_type": "START_LS_NEXT1_FILL_HUMAN_INPUT_TEMPLATE",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1-FILL",
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "public_url": "",
        "public_rest_url": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "human_filled": False,
        "human_confirmed": False,
        "execution_allowed": False,
        "notes": "Fill this file manually. Do not let AI infer or guess these values.",
    })

    if create_human_record:
        _write(paths["human_record"], _filled_human_record() if filled else _base_human_record())

    return paths


def _run(paths: dict[str, Path], include_human_flags: bool = False, omit_flag: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy", str(paths["policy"]),
        "--ls-next1-result", str(paths["ls_next1_result"]),
        "--ls-next1-lock", str(paths["ls_next1_lock"]),
        "--ls-next1-run-result", str(paths["ls_next1_run"]),
        "--ls-next1-validation-result", str(paths["ls_next1_validation"]),
        "--ls-next1-intake-template", str(paths["ls_next1_template"]),
        "--ls-next1-intake-record", str(paths["ls_next1_record"]),
        "--ls-reuse1-result", str(paths["ls_reuse1_result"]),
        "--human-input-template-output", str(paths["human_template"]),
        "--human-input-record", str(paths["human_record"]),
        "--filled-intake-output", str(paths["filled_output"]),
        "--output", str(paths["output"]),
        "--lock-output", str(paths["lock_output"]),
        "--report", str(paths["report"]),
        "--create-human-input-template",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-publish",
        "--require-no-next-post-creation",
        "--forbid-post119-update",
        "--forbid-post183-update",
        "--forbid-auto-content-selection",
    ]
    if include_human_flags:
        cmd.extend(["--require-human-filled", "--require-human-confirmed"])
    if omit_flag and omit_flag in cmd:
        cmd.remove(omit_flag)
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _result(paths: dict[str, Path]) -> dict:
    return json.loads(paths["output"].read_text(encoding="utf-8"))


def _lock(paths: dict[str, Path]) -> dict:
    return json.loads(paths["lock_output"].read_text(encoding="utf-8"))


# 1-5

def test_missing_policy_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].unlink()
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_missing_ls_next1_result_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls_next1_result"].unlink()
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_missing_ls_reuse1_result_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls_reuse1_result"].unlink()
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_ls_next1_status_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_ls_next1_result()
    d["status"] = "BAD"
    _write(paths["ls_next1_result"], d)
    _write(paths["ls_next1_run"], d)
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_ls_reuse1_status_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_reuse1_result"], {"status": "BAD", "reusable_template_built": True})
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


# 6-13

def test_missing_create_human_input_template_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths, omit_flag="--create-human-input-template")
    assert proc.returncode == 0
    assert any("create-human-input-template" in e for e in _result(paths)["errors"])


def test_missing_require_no_wordpress_api_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, omit_flag="--require-no-wordpress-api")
    assert any("require-no-wordpress-api" in e for e in _result(paths)["errors"])


def test_missing_require_no_credential_read_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, omit_flag="--require-no-credential-read")
    assert any("require-no-credential-read" in e for e in _result(paths)["errors"])


def test_missing_require_no_publish_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, omit_flag="--require-no-publish")
    assert any("require-no-publish" in e for e in _result(paths)["errors"])


def test_missing_require_no_next_post_creation_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, omit_flag="--require-no-next-post-creation")
    assert any("require-no-next-post-creation" in e for e in _result(paths)["errors"])


def test_missing_forbid_post119_update_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, omit_flag="--forbid-post119-update")
    assert any("forbid-post119-update" in e for e in _result(paths)["errors"])


def test_missing_forbid_post183_update_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, omit_flag="--forbid-post183-update")
    assert any("forbid-post183-update" in e for e in _result(paths)["errors"])


def test_missing_forbid_auto_content_selection_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, omit_flag="--forbid-auto-content-selection")
    assert any("forbid-auto-content-selection" in e for e in _result(paths)["errors"])


# 14-24

def test_no_human_input_record_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, create_human_record=False)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"


def test_blank_human_input_record_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"


def test_human_filled_false_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    r = _base_human_record()
    r["human_confirmed"] = True
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"


def test_human_confirmed_false_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    r = _base_human_record()
    r["human_filled"] = True
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"


def test_missing_content_item_id_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["content_item_id"] = ""
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert "content_item_id" in _result(paths)["missing_required_human_fields"]


def test_missing_target_post_id_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["target_post_id"] = None
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert "target_post_id" in _result(paths)["missing_required_human_fields"]


def test_missing_target_post_link_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["target_post_link"] = ""
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert "target_post_link" in _result(paths)["missing_required_human_fields"]


def test_missing_payload_title_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["payload_title"] = ""
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert "payload_title" in _result(paths)["missing_required_human_fields"]


def test_missing_payload_asin_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["payload_asin"] = ""
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert "payload_asin" in _result(paths)["missing_required_human_fields"]


def test_missing_public_url_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["public_url"] = ""
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert "public_url" in _result(paths)["missing_required_human_fields"]


def test_missing_public_rest_url_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["public_rest_url"] = ""
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert "public_rest_url" in _result(paths)["missing_required_human_fields"]


# 25-30

def test_target_post_id_119_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["target_post_id"] = 119
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_target_post_id_183_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["target_post_id"] = 183
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_target_post_id_non_integer_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["target_post_id"] = "A"
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_target_post_id_negative_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["target_post_id"] = -1
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_expected_pre_publish_status_not_draft_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["expected_pre_publish_status"] = "publish"
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_target_publish_status_not_publish_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    r = _filled_human_record()
    r["target_publish_status"] = "draft"
    _write(paths["human_record"], r)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


# 31-53

def test_valid_human_input_passed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_PASSED_NO_EXECUTION"


def test_result_generated(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths["output"].exists()


def test_lock_generated(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths["lock_output"].exists()


def test_report_generated(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths["report"].exists()


def test_human_input_template_generated(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["human_template"].unlink()
    _run(paths)
    assert paths["human_template"].exists()


def test_filled_intake_generated_when_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert paths["filled_output"].exists()


def test_ready_for_ls_next_2_true_when_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["ready_for_ls_next_2"] is True


def test_execution_allowed_false_when_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["execution_allowed"] is False


def test_intake_registration_completed_true_when_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["intake_registration_completed"] is True


def test_missing_required_fields_empty_when_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["missing_required_human_fields"] == []


_FALSE_FLAGS = [
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
    "credential_value_output",
    "credential_secret_output",
]


def test_no_execution_flags_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    payload = _result(paths)
    for key in _FALSE_FLAGS:
        assert payload[key] is False


def test_auto_content_selection_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert _result(paths)["auto_content_selection_allowed"] is False


def test_next_post_creation_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert _result(paths)["next_post_creation_allowed"] is False


def test_waiting_recommended_next_action(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, include_human_flags=True)
    assert _result(paths)["recommended_next_action"] == "WAIT_FOR_HUMAN_INPUT"


def test_valid_recommended_next_action(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["recommended_next_action"] == "BEGIN_LS_NEXT_2_DRAFT_STATUS_AND_PAYLOAD_DRY_RUN"


def test_waiting_phase_options(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, include_human_flags=True)
    assert _result(paths)["recommended_next_phase_options"] == ["LS-NEXT-1-FILL_AFTER_HUMAN_INPUT", "LS-MON-2"]


def test_valid_phase_options(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["recommended_next_phase_options"] == ["LS-NEXT-2_AFTER_HUMAN_INPUT", "LS-MON-2"]


def test_lock_written_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, include_human_flags=True)
    assert _lock(paths)["status"] == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_LOCKED_NO_EXECUTION"


def test_lock_written_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _lock(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_LOCKED_NO_EXECUTION"


def test_stdout_is_json(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    proc = _run(paths)
    payload = json.loads(proc.stdout)
    assert payload["phase"] == "LS-NEXT-1-FILL"


def test_ls_next1_validation_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_next1_validation"], {"status": "BAD"})
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_ls_next1_run_result_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_next1_run"], {"status": "DIFF"})
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_ls_next1_lock_false_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_next1_lock"], {"locked": False})
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_ls_reuse1_reusable_template_built_false_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write(paths["ls_reuse1_result"], {"status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION", "reusable_template_built": False})
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_policy_invalid_json_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].write_text("{", encoding="utf-8")
    _run(paths)
    assert _result(paths)["status"] == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"


def test_waiting_human_input_required_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths, include_human_flags=True)
    assert _result(paths)["human_input_required"] is True


def test_valid_human_input_required_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    assert _result(paths)["human_input_required"] is False


def test_valid_fields_propagated(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths, include_human_flags=True)
    payload = _result(paths)
    assert payload["content_item_id"] == "NEXT-001"
    assert payload["target_post_id"] == 555
    assert payload["payload_title"] == "Human Title"


def test_report_contains_status_line(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    report = paths["report"].read_text(encoding="utf-8")
    assert "status:" in report
