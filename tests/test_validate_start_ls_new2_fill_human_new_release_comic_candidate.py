from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/validate_start_ls_new2_fill_human_new_release_comic_candidate.py"
VALID_WAITING = "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT_VALIDATED_NO_EXECUTION"
VALID_FILLED = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_VALIDATED_NO_EXECUTION"
INVALID = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_NOT_VALIDATED"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-2-FILL"}


def _base_result_waiting() -> dict:
    return {
        "phase": "LS-NEW-2-FILL",
        "status": "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT_NO_EXECUTION",
        "production_status": "WAITING_FOR_HUMAN_NEW_RELEASE_CANDIDATE_INPUT_NO_EXECUTION",
        "human_filled": False,
        "human_confirmed": False,
        "human_input_required": True,
        "candidate_intake_completed": False,
        "ready_for_ls_new_3": False,
        "execution_allowed": False,
        "missing_required_human_fields": ["content_item_id"],
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "external_api_call_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "amazon_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "rerun_allowed": False,
        "recommended_next_action": "WAIT_FOR_HUMAN_NEW_RELEASE_CANDIDATE_INPUT",
        "recommended_next_phase_options": ["LS-NEW-2-FILL_AFTER_HUMAN_INPUT", "LS-MON-2"],
    }


def _base_result_filled() -> dict:
    d = _base_result_waiting()
    d.update(
        {
            "status": "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION",
            "production_status": "NO_EXECUTION_HUMAN_NEW_RELEASE_CANDIDATE_FILLED",
            "human_filled": True,
            "human_confirmed": True,
            "human_input_required": False,
            "candidate_intake_completed": True,
            "ready_for_ls_new_3": True,
            "missing_required_human_fields": [],
            "recommended_next_action": "BEGIN_LS_NEW_3_CANDIDATE_EVIDENCE_DRY_RUN",
            "recommended_next_phase_options": ["LS-NEW-3_AFTER_HUMAN_INPUT", "LS-MON-2"],
        }
    )
    return d


def _base_lock() -> dict:
    return {"locked": True}


def _base_human_template() -> dict:
    return {"document_type": "START_LS_NEW2_FILL_HUMAN_CANDIDATE_INPUT_TEMPLATE"}


def _base_human_record() -> dict:
    return {"document_type": "START_LS_NEW2_FILL_HUMAN_CANDIDATE_INPUT_RECORD"}


def _base_filled_record() -> dict:
    return {"phase": "LS-NEW-2-FILL"}


def _base_ls_new2_result() -> dict:
    return {"status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"}


def _base_ls_new2_validation() -> dict:
    return {"validation_status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_VALIDATED_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"}


def _base_simple_x_md() -> str:
    return """# START-LS LS-NEW-2 Simple X Post Template

```text
配信開始です
#PR #Amazonmanga #Kindle #作者名
『タイトル』第○巻

URL
```
"""


def _prepare(tmp_path: Path, filled: bool = False) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "human_template": tmp_path / "exchange/new_release/human_template.json",
        "human_record": tmp_path / "exchange/new_release/human_record.json",
        "filled_record": tmp_path / "exchange/new_release/filled_record.json",
        "ls_new2_result": tmp_path / "exchange/runtime/ls_new2_result.json",
        "ls_new2_validation": tmp_path / "exchange/logs/ls_new2_validation.json",
        "simple_x": tmp_path / "exchange/templates/simple_x.md",
        "output": tmp_path / "exchange/logs/validation_result.json",
        "report": tmp_path / "reports/validation_report.md",
    }
    _write_json(paths["policy"], _base_policy())
    r = _base_result_filled() if filled else _base_result_waiting()
    _write_json(paths["result"], r)
    _write_json(paths["run_result"], r)
    _write_json(paths["lock"], _base_lock())
    _write_json(paths["human_template"], _base_human_template())
    _write_json(paths["human_record"], _base_human_record())
    _write_json(paths["filled_record"], _base_filled_record())
    _write_json(paths["ls_new2_result"], _base_ls_new2_result())
    _write_json(paths["ls_new2_validation"], _base_ls_new2_validation())
    _write_text(paths["simple_x"], _base_simple_x_md())
    return paths


def _run(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--result",
        str(paths["result"]),
        "--lock",
        str(paths["lock"]),
        "--run-result",
        str(paths["run_result"]),
        "--human-input-template",
        str(paths["human_template"]),
        "--human-input-record",
        str(paths["human_record"]),
        "--filled-candidate-record",
        str(paths["filled_record"]),
        "--ls-new2-result",
        str(paths["ls_new2_result"]),
        "--ls-new2-validation-result",
        str(paths["ls_new2_validation"]),
        "--simple-x-template",
        str(paths["simple_x"]),
        "--output",
        str(paths["output"]),
        "--report",
        str(paths["report"]),
    ]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _payload(paths: dict[str, Path]) -> dict:
    return json.loads(paths["output"].read_text(encoding="utf-8"))


def _mutate_result_and_run(tmp_path: Path, key: str, value, filled: bool = False) -> dict:
    paths = _prepare(tmp_path, filled=filled)
    d = _base_result_filled() if filled else _base_result_waiting()
    d[key] = value
    _write_json(paths["result"], d)
    _write_json(paths["run_result"], d)
    _run(paths)
    return _payload(paths)


# 48-54

def test_48_validation_waiting_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cp = _run(paths)
    assert cp.returncode == 0
    assert _payload(paths)["validation_status"] == VALID_WAITING


def test_49_validation_filled_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    cp = _run(paths)
    assert cp.returncode == 0
    assert _payload(paths)["validation_status"] == VALID_FILLED


def test_50_validation_detects_missing_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["result"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_51_validation_detects_missing_lock(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["lock"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_52_validation_detects_missing_run_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["run_result"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_53_validation_detects_missing_human_input_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["human_template"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_54_validation_detects_missing_human_input_record(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["human_record"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


# 55-63

def test_55_validation_detects_status_mismatch(tmp_path: Path) -> None:
    payload = _mutate_result_and_run(tmp_path, "status", "BAD")
    assert payload["validation_status"] == INVALID


def test_56_validation_detects_production_status_mismatch(tmp_path: Path) -> None:
    payload = _mutate_result_and_run(tmp_path, "production_status", "BAD")
    assert payload["validation_status"] == INVALID


def test_57_validation_detects_human_filled_mismatch(tmp_path: Path) -> None:
    payload = _mutate_result_and_run(tmp_path, "human_filled", True)
    assert payload["validation_status"] == INVALID


def test_58_validation_detects_human_confirmed_mismatch(tmp_path: Path) -> None:
    payload = _mutate_result_and_run(tmp_path, "human_confirmed", True)
    assert payload["validation_status"] == INVALID


def test_59_validation_detects_ready_for_ls_new_3_true_while_missing_fields(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_result_waiting()
    d["ready_for_ls_new_3"] = True
    d["missing_required_human_fields"] = ["title"]
    _write_json(paths["result"], d)
    _write_json(paths["run_result"], d)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_60_validation_detects_execution_allowed_true(tmp_path: Path) -> None:
    payload = _mutate_result_and_run(tmp_path, "execution_allowed", True)
    assert payload["validation_status"] == INVALID


def test_61_validation_detects_simple_x_template_over_280(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["simple_x"], "```text\n" + ("あ" * 300) + "\n```")
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_62_validation_detects_missing_pr(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["simple_x"], _base_simple_x_md().replace("#PR ", ""))
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_63_validation_detects_missing_url(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["simple_x"], _base_simple_x_md().replace("URL", ""))
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


# 64-75

def test_64_validation_detects_wordpress_api_call_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "wordpress_api_call_executed", True)["validation_status"] == INVALID


def test_65_validation_detects_credential_env_read_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "credential_env_read_executed", True)["validation_status"] == INVALID


def test_66_validation_detects_external_api_call_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "external_api_call_executed", True)["validation_status"] == INVALID


def test_67_validation_detects_http_get_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "http_get_executed", True)["validation_status"] == INVALID


def test_68_validation_detects_web_scraping_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "web_scraping_executed", True)["validation_status"] == INVALID


def test_69_validation_detects_amazon_api_call_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "amazon_api_call_executed", True)["validation_status"] == INVALID


def test_70_validation_detects_x_api_call_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "x_api_call_executed", True)["validation_status"] == INVALID


def test_71_validation_detects_x_post_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "x_post_executed", True)["validation_status"] == INVALID


def test_72_validation_detects_candidate_selected_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "candidate_selected", True)["validation_status"] == INVALID


def test_73_validation_detects_ls_next1_fill_updated_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "ls_next1_fill_updated", True)["validation_status"] == INVALID


def test_74_validation_detects_post119_update_executed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "post119_update_executed", True)["validation_status"] == INVALID


def test_75_validation_detects_post183_update_executed_by_this_phase_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "post183_update_executed_by_this_phase", True)["validation_status"] == INVALID


# 76-83

def test_76_validation_detects_secret_length_output_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "secret_length_output", True)["validation_status"] == INVALID


def test_77_validation_detects_secret_hash_output_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "secret_hash_output", True)["validation_status"] == INVALID


def test_78_validation_detects_authorization_header_output_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "authorization_header_output", True)["validation_status"] == INVALID


def test_79_validation_detects_rerun_allowed_true(tmp_path: Path) -> None:
    assert _mutate_result_and_run(tmp_path, "rerun_allowed", True)["validation_status"] == INVALID


def test_80_validation_detects_result_and_run_result_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_result_waiting()
    e = _base_result_waiting()
    e["status"] = "OTHER"
    _write_json(paths["result"], d)
    _write_json(paths["run_result"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_81_validation_detects_ls_new2_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_json(paths["ls_new2_result"], {"status": "BAD"})
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_82_validation_detects_ls_new2_validation_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_json(paths["ls_new2_validation"], {"validation_status": "BAD"})
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_83_validation_detects_filled_record_phase_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_json(paths["filled_record"], {"phase": "BAD"})
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


# 84-95 source checks

def _source() -> str:
    return Path("scripts/build_start_ls_new2_fill_human_new_release_comic_candidate.py").read_text(encoding="utf-8") + Path(
        "scripts/validate_start_ls_new2_fill_human_new_release_comic_candidate.py"
    ).read_text(encoding="utf-8")


def test_84_source_code_has_no_requests_call() -> None:
    assert "requests." not in _source()


def test_85_source_code_has_no_urllib_request() -> None:
    assert "urllib.request" not in _source()


def test_86_source_code_has_no_wp_json() -> None:
    assert "wp-json" not in _source()


def test_87_source_code_has_no_credential_env_open() -> None:
    src = _source()
    assert "credential.env" not in src
    assert "open(" not in src or "credential" not in src


def test_88_source_code_has_no_authorization_output() -> None:
    src = _source()
    assert "Authorization:" not in src
    assert "print(" not in src or "Authorization" not in src


def test_89_source_code_has_no_basic_string_output() -> None:
    src = _source()
    assert "Basic " not in src
    assert "print(" not in src or "Basic" not in src


def test_90_source_code_has_no_base64_import_use() -> None:
    assert "base64" not in _source()


def test_91_waiting_status_specific_validation_status(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert _payload(paths)["validation_status"] == VALID_WAITING


def test_92_filled_status_specific_validation_status(tmp_path: Path) -> None:
    paths = _prepare(tmp_path, filled=True)
    _run(paths)
    assert _payload(paths)["validation_status"] == VALID_FILLED


def test_93_validation_output_file_created(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths["output"].exists()


def test_94_validation_report_file_created(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths["report"].exists()


def test_95_validation_contains_recommended_next_action(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    payload = _payload(paths)
    assert "recommended_next_action" in payload
