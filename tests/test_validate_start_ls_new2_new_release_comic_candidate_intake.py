from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
VALID = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_VALIDATED_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
INVALID = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_NOT_VALIDATED"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_policy() -> dict:
    return {
        "phase": "LS-NEW-2",
        "next_phase": {
            "recommended_next_action": "FILL_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_OR_CONTINUE_MONITORING",
            "recommended_next_phase_options": ["LS-NEW-2-FILL", "LS-MON-2", "LS-NEW-3_AFTER_HUMAN_INPUT"],
        },
    }


def _base_schema() -> dict:
    return {
        "phase": "LS-NEW-2",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "simple_x_post_rule": {
            "enabled": True,
            "max_characters": 280,
            "template": "配信開始です\n#PR #Amazonmanga #Kindle #作者名\n『タイトル』第○巻\n\nURL",
            "requires_pr_hashtag_when_affiliate_url_present": True,
            "requires_url": True,
            "does_not_require_synopsis": True,
            "does_not_require_price_or_point_rate": True,
            "does_not_require_store_comparison": True,
        },
    }


def _base_candidate_template() -> dict:
    return {
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_TEMPLATE",
        "phase": "LS-NEW-2",
    }


def _base_candidate_record() -> dict:
    return {
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_RECORD",
        "phase": "LS-NEW-2",
        "status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT",
    }


def _base_simple_x_template() -> str:
    return """# START-LS LS-NEW-2 Simple X Post Template

```text
配信開始です
#PR #Amazonmanga #Kindle #作者名
『タイトル』第○巻

URL
```
"""


def _base_result() -> dict:
    return {
        "phase": "LS-NEW-2",
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_RESULT",
        "status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION",
        "production_status": "NO_EXECUTION_NEW_RELEASE_CANDIDATE_INTAKE_ONLY",
        "simple_x_post_max_characters": 280,
        "simple_x_template_under_280": True,
        "human_input_required": True,
        "human_filled": False,
        "human_confirmed": False,
        "candidate_intake_completed": False,
        "ready_for_ls_new_3": False,
        "work_explanation_required": False,
        "long_work_explanation_required": False,
        "synopsis_required": False,
        "price_comparison_required_in_x_post": False,
        "point_reward_rate_required_in_x_post": False,
        "store_comparison_required_in_x_post": False,
        "execution_allowed": False,
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "external_api_call_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
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
        "recommended_next_action": "FILL_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_OR_CONTINUE_MONITORING",
        "recommended_next_phase_options": ["LS-NEW-2-FILL", "LS-MON-2", "LS-NEW-3_AFTER_HUMAN_INPUT"],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-2",
        "locked": True,
        "execution_allowed": False,
        "candidate_selected": False,
    }


def _base_lsnew1_result() -> dict:
    return {
        "validation_status": "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_VALIDATED_DESIGN_ONLY_NO_EXECUTION"
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "schema": tmp_path / "config/schema.json",
        "candidate_template": tmp_path / "exchange/new_release/template.json",
        "candidate_record": tmp_path / "exchange/new_release/record.json",
        "simple_x_template": tmp_path / "exchange/templates/simple_x.md",
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "lsnew1_result": tmp_path / "exchange/logs/lsnew1_result.json",
        "output": tmp_path / "exchange/logs/validation_result.json",
        "report": tmp_path / "reports/validation_report.md",
    }
    _write_json(paths["policy"], _base_policy())
    _write_json(paths["schema"], _base_schema())
    _write_json(paths["candidate_template"], _base_candidate_template())
    _write_json(paths["candidate_record"], _base_candidate_record())
    _write_text(paths["simple_x_template"], _base_simple_x_template())
    result = _base_result()
    _write_json(paths["result"], result)
    _write_json(paths["run_result"], result)
    _write_json(paths["lock"], _base_lock())
    _write_json(paths["lsnew1_result"], _base_lsnew1_result())
    return paths


def _run(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--schema",
        str(paths["schema"]),
        "--candidate-template",
        str(paths["candidate_template"]),
        "--candidate-record",
        str(paths["candidate_record"]),
        "--simple-x-template",
        str(paths["simple_x_template"]),
        "--result",
        str(paths["result"]),
        "--lock",
        str(paths["lock"]),
        "--run-result",
        str(paths["run_result"]),
        "--ls-new1-result",
        str(paths["lsnew1_result"]),
        "--output",
        str(paths["output"]),
        "--report",
        str(paths["report"]),
    ]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _payload(paths: dict[str, Path]) -> dict:
    return json.loads(paths["output"].read_text(encoding="utf-8"))


# 49-88

def test_49_validation_valid_waiting_validated(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cp = _run(paths)
    assert cp.returncode == 0
    assert _payload(paths)["validation_status"] == VALID


def test_50_validation_detects_missing_schema(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["schema"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_51_validation_detects_missing_candidate_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["candidate_template"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_52_validation_detects_missing_candidate_record(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["candidate_record"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_53_validation_detects_missing_simple_x_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["simple_x_template"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_54_validation_detects_missing_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["result"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_55_validation_detects_missing_lock(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["lock"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_56_validation_detects_missing_run_result(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["run_result"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_57_validation_detects_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_result()
    d["status"] = "BAD"
    _write_json(paths["result"], d)
    _write_json(paths["run_result"], d)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_58_validation_detects_production_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_result()
    d["production_status"] = "BAD"
    _write_json(paths["result"], d)
    _write_json(paths["run_result"], d)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_59_validation_detects_simple_x_template_over_280(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["simple_x_template"], "```text\n" + ("あ" * 300) + "\n```")
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_60_validation_detects_missing_pr_in_simple_x_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["simple_x_template"], _base_simple_x_template().replace("#PR ", ""))
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_61_validation_detects_missing_url_in_simple_x_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["simple_x_template"], _base_simple_x_template().replace("URL", ""))
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_62_validation_detects_missing_title_placeholder_in_simple_x_template(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["simple_x_template"], _base_simple_x_template().replace("『タイトル』第○巻", "タイトル"))
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_63_validation_detects_synopsis_required_in_simple_x_rule(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    s = _base_schema()
    s["simple_x_post_rule"]["does_not_require_synopsis"] = False
    _write_json(paths["schema"], s)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_64_validation_detects_price_comparison_required_in_x_post(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    s = _base_schema()
    s["simple_x_post_rule"]["does_not_require_price_or_point_rate"] = False
    _write_json(paths["schema"], s)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_65_validation_detects_point_reward_required_in_x_post(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    r = _base_result()
    r["point_reward_rate_required_in_x_post"] = True
    _write_json(paths["result"], r)
    _write_json(paths["run_result"], r)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_66_validation_detects_store_comparison_required_in_x_post(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    s = _base_schema()
    s["simple_x_post_rule"]["does_not_require_store_comparison"] = False
    _write_json(paths["schema"], s)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_67_validation_detects_human_input_required_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    r = _base_result()
    r["human_input_required"] = False
    _write_json(paths["result"], r)
    _write_json(paths["run_result"], r)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def _assert_result_forbidden_true(tmp_path: Path, key: str) -> None:
    paths = _prepare(tmp_path)
    r = _base_result()
    r[key] = True
    _write_json(paths["result"], r)
    _write_json(paths["run_result"], r)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_68_validation_detects_ready_for_ls_new_3_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "ready_for_ls_new_3")


def test_69_validation_detects_execution_allowed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "execution_allowed")


def test_70_validation_detects_wordpress_api_call_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "wordpress_api_call_executed")


def test_71_validation_detects_credential_env_read_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "credential_env_read_executed")


def test_72_validation_detects_external_api_call_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "external_api_call_executed")


def test_73_validation_detects_http_get_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "http_get_executed")


def test_74_validation_detects_web_scraping_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "web_scraping_executed")


def test_75_validation_detects_amazon_api_call_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "amazon_api_call_executed")


def test_76_validation_detects_pa_api_call_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "pa_api_call_executed")


def test_77_validation_detects_creators_api_call_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "creators_api_call_executed")


def test_78_validation_detects_x_api_call_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "x_api_call_executed")


def test_79_validation_detects_x_post_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "x_post_executed")


def test_80_validation_detects_candidate_selected_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "candidate_selected")


def test_81_validation_detects_ls_next1_fill_updated_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "ls_next1_fill_updated")


def test_82_validation_detects_post119_update_executed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "post119_update_executed")


def test_83_validation_detects_post183_update_executed_by_this_phase_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "post183_update_executed_by_this_phase")


def test_84_validation_detects_secret_length_output_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "secret_length_output")


def test_85_validation_detects_secret_hash_output_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "secret_hash_output")


def test_86_validation_detects_authorization_header_output_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "authorization_header_output")


def test_87_validation_detects_rerun_allowed_true(tmp_path: Path) -> None:
    _assert_result_forbidden_true(tmp_path, "rerun_allowed")


def test_88_validation_detects_recommended_next_action_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    r = _base_result()
    r["recommended_next_action"] = "BAD"
    _write_json(paths["result"], r)
    _write_json(paths["run_result"], r)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


# 89-95 source code safety checks

def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_89_source_code_has_no_requests_call() -> None:
    src = _source("scripts/build_start_ls_new2_new_release_comic_candidate_intake.py") + _source(
        "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
    )
    assert "requests." not in src


def test_90_source_code_has_no_urllib_request() -> None:
    src = _source("scripts/build_start_ls_new2_new_release_comic_candidate_intake.py") + _source(
        "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
    )
    assert "urllib.request" not in src


def test_91_source_code_has_no_wp_json() -> None:
    src = _source("scripts/build_start_ls_new2_new_release_comic_candidate_intake.py") + _source(
        "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
    )
    assert "wp-json" not in src


def test_92_source_code_has_no_credential_env_open() -> None:
    src = _source("scripts/build_start_ls_new2_new_release_comic_candidate_intake.py") + _source(
        "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
    )
    assert "credential.env" not in src
    assert "open(" not in src or "credential" not in src


def test_93_source_code_has_no_authorization_output() -> None:
    src = _source("scripts/build_start_ls_new2_new_release_comic_candidate_intake.py") + _source(
        "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
    )
    assert "Authorization:" not in src
    assert "print(" not in src or "Authorization" not in src


def test_94_source_code_has_no_basic_string_output() -> None:
    src = _source("scripts/build_start_ls_new2_new_release_comic_candidate_intake.py") + _source(
        "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
    )
    assert "Basic " not in src
    assert "print(" not in src or "Basic" not in src


def test_95_source_code_has_no_base64_import_or_use() -> None:
    src = _source("scripts/build_start_ls_new2_new_release_comic_candidate_intake.py") + _source(
        "scripts/validate_start_ls_new2_new_release_comic_candidate_intake.py"
    )
    assert "base64" not in src
