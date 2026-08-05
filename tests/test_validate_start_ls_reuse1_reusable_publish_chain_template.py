from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls_reuse1_reusable_publish_chain_template import (
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
        "template_result": tmp_path / "exchange/runtime/template_result.json",
        "template_lock": tmp_path / "exchange/locks/template_lock.json",
        "run_result": tmp_path / "exchange/logs/template_result.json",
        "input_schema": tmp_path / "config/input_schema.json",
        "phase_map": tmp_path / "config/phase_map.json",
        "item_template": tmp_path / "exchange/templates/item_template.json",
        "safety_contract": tmp_path / "exchange/templates/safety_contract.json",
        "ls_mon1_result": tmp_path / "exchange/runtime/ls_mon1_result.json",
        "ls_close1_result": tmp_path / "exchange/runtime/ls_close1_result.json",
        "output": tmp_path / "exchange/logs/validation_result.json",
        "report": tmp_path / "reports/validation_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-REUSE-1",
            "source_chain": {
                "source_post_id": 183,
                "source_completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED",
                "source_monitor_status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_VALIDATED_GET_ONLY",
            },
            "next_phase": {
                "recommended_next_action": "BEGIN_NEXT_CONTENT_ITEM_WITH_REUSABLE_TEMPLATE_OR_CONTINUE_MONITORING",
                "recommended_next_phase_options": ["LS-NEXT-1", "LS-MON-2", "LS-REUSE-2"],
            },
        },
    )

    result = {
        "phase": "LS-REUSE-1",
        "document_type": "START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_RESULT",
        "status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION",
        "execution_mode": "TEMPLATE_BUILD_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_REUSE_TEMPLATE_ONLY",
        "source_post_id": 183,
        "source_post_link": "https://hoshido.jp/?p=183",
        "source_payload_title": "2.5次元の誘惑",
        "source_payload_asin": "B07X2G67B4",
        "ls_mon1_validated": True,
        "ls_close1_validated": True,
        "ls6au_validated": True,
        "ls6at_validated": True,
        "reusable_template_built": True,
        "input_schema_created": True,
        "phase_map_created": True,
        "item_template_created": True,
        "safety_contract_created": True,
        "parameterized_fields": [
            "content_item_id",
            "target_post_id",
            "target_post_link",
            "payload_title",
            "payload_asin",
            "expected_pre_publish_status",
            "target_publish_status",
            "public_url",
            "public_rest_url",
            "evidence_paths",
        ],
        "template_execution_allowed_by_this_phase": False,
        "next_item_creation_allowed_by_this_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "next_post_created": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "locked": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": "BEGIN_NEXT_CONTENT_ITEM_WITH_REUSABLE_TEMPLATE_OR_CONTINUE_MONITORING",
        "recommended_next_phase_options": ["LS-NEXT-1", "LS-MON-2", "LS-REUSE-2"],
        "errors": [],
    }
    write_json(files["template_result"], result)
    write_json(files["run_result"], result)

    write_json(
        files["template_lock"],
        {
            "phase": "LS-REUSE-1",
            "document_type": "START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_LOCK",
            "status": "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_LOCKED_NO_EXECUTION",
            "locked": True,
        },
    )

    write_json(
        files["input_schema"],
        {
            "schema_name": "START_LS_REUSABLE_PUBLISH_CHAIN_INPUT_SCHEMA",
            "required_fields": ["content_item_id", "target_post_id", "human_review_required"],
            "forbidden_values": {"target_post_id": [119]},
        },
    )
    write_json(
        files["phase_map"],
        {
            "reusable_sequence": [
                {"phase": "LS-NEXT-PUBLISH", "execution_allowed": "requires_explicit_human_approval"},
            ]
        },
    )
    write_json(
        files["item_template"],
        {
            "template_name": "START_LS_REUSABLE_PUBLISH_CHAIN_ITEM_TEMPLATE",
        },
    )
    write_json(
        files["safety_contract"],
        {
            "always_forbidden": {
                "post119_update": True,
                "publish_without_explicit_human_approval": True,
            }
        },
    )

    write_json(
        files["ls_mon1_result"],
        {
            "phase": "LS-MON-1",
            "status": "LSMON1_POST183_PUBLISHED_STATE_MONITOR_PASSED_GET_ONLY",
            "post_publish_state_monitor_ok": True,
        },
    )
    write_json(files["ls_close1_result"], {"completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED"})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--template-result",
        str(files["template_result"]),
        "--template-lock",
        str(files["template_lock"]),
        "--run-result",
        str(files["run_result"]),
        "--input-schema",
        str(files["input_schema"]),
        "--phase-map",
        str(files["phase_map"]),
        "--item-template",
        str(files["item_template"]),
        "--safety-contract",
        str(files["safety_contract"]),
        "--ls-mon1-result",
        str(files["ls_mon1_result"]),
        "--ls-close1-result",
        str(files["ls_close1_result"]),
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


def test_52_validation_valid(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_53_validation_detects_missing_template_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["template_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_54_validation_detects_missing_lock(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["template_lock"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_55_validation_detects_missing_run_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["run_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


@pytest.mark.parametrize(
    "path_key",
    ["input_schema", "phase_map", "item_template", "safety_contract"],
)
def test_56_to_59_validation_detects_missing_generated_files(monkeypatch, tmp_path: Path, path_key: str) -> None:
    files = make_files(tmp_path)
    files[path_key].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("template_result", ("status",), "WRONG"),
        ("template_result", ("production_status",), "WRONG"),
        ("template_result", ("source_post_id",), 999),
        ("template_result", ("reusable_template_built",), False),
        ("template_result", ("input_schema_created",), False),
        ("template_result", ("phase_map_created",), False),
        ("template_result", ("item_template_created",), False),
        ("template_result", ("safety_contract_created",), False),
        ("template_result", ("template_execution_allowed_by_this_phase",), True),
        ("template_result", ("next_item_creation_allowed_by_this_phase",), True),
        ("template_result", ("wordpress_api_call_executed",), True),
        ("template_result", ("credential_env_read_executed",), True),
        ("template_result", ("publish_executed_by_this_phase",), True),
        ("template_result", ("post119_update_executed",), True),
        ("template_result", ("next_post_created",), True),
        ("template_result", ("rollback_executed",), True),
        ("template_result", ("rerun_allowed",), True),
        ("template_result", ("recommended_next_action",), "WRONG"),
    ],
)
def test_60_to_76_validation_detects_result_mismatches(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files[path_key], keys, value)
    if path_key == "template_result":
        write_json(files["run_result"], read_json(files[path_key]))
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_77_validation_detects_input_schema_missing_target_post_id(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["input_schema"], ("required_fields",), ["content_item_id", "human_review_required"])
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_78_validation_detects_input_schema_missing_human_review_required(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["input_schema"], ("required_fields",), ["content_item_id", "target_post_id"])
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_79_validation_detects_input_schema_does_not_forbid_119(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["input_schema"], ("forbidden_values", "target_post_id"), [])
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_80_validation_detects_phase_map_missing_ls_next_publish(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["phase_map"], ("reusable_sequence",), [{"phase": "LS-NEXT-1", "execution_allowed": False}])
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_81_validation_detects_phase_map_publish_not_separated(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["phase_map"], ("reusable_sequence", 0, "execution_allowed"), False)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_82_validation_detects_safety_contract_missing_post119_forbidden(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["safety_contract"], ("always_forbidden", "post119_update"), False)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_83_validation_detects_safety_contract_missing_human_approval_boundary(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["safety_contract"], ("always_forbidden", "publish_without_explicit_human_approval"), False)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_84_validation_detects_recommended_next_action_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    mutate(files["template_result"], ("recommended_next_action",), "WRONG")
    write_json(files["run_result"], read_json(files["template_result"]))
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_85_source_code_has_no_requests_call() -> None:
    merged = (
        Path("/home/deploy/ai_media_os/scripts/build_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
        + Path("/home/deploy/ai_media_os/scripts/validate_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
    )
    assert "requests." not in merged


def test_86_source_code_has_no_urllib_request() -> None:
    merged = (
        Path("/home/deploy/ai_media_os/scripts/build_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
        + Path("/home/deploy/ai_media_os/scripts/validate_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
    )
    assert "urllib.request" not in merged


def test_87_source_code_has_no_wp_json() -> None:
    merged = (
        Path("/home/deploy/ai_media_os/scripts/build_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
        + Path("/home/deploy/ai_media_os/scripts/validate_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
    )
    assert "wp-json" not in merged


def test_88_source_code_has_no_credential_env_open() -> None:
    merged = (
        Path("/home/deploy/ai_media_os/scripts/build_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
        + Path("/home/deploy/ai_media_os/scripts/validate_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
    )
    assert "credential.env" not in merged


def test_89_source_code_has_no_authorization_output() -> None:
    merged = (
        Path("/home/deploy/ai_media_os/scripts/build_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
        + Path("/home/deploy/ai_media_os/scripts/validate_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
    )
    assert "Authorization:" not in merged


def test_90_source_code_has_no_basic_string_output() -> None:
    merged = (
        Path("/home/deploy/ai_media_os/scripts/build_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
        + Path("/home/deploy/ai_media_os/scripts/validate_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
    )
    assert "Basic " not in merged


def test_91_source_code_has_no_base64_import_use() -> None:
    merged = (
        Path("/home/deploy/ai_media_os/scripts/build_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
        + Path("/home/deploy/ai_media_os/scripts/validate_start_ls_reuse1_reusable_publish_chain_template.py").read_text(encoding="utf-8")
    )
    assert "base64" not in merged
    assert "b64encode" not in merged


def test_92_validation_output_doc_type(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["document_type"] == "START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATION_RESULT"


def test_93_validation_output_phase(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["phase"] == "LS-REUSE-1"


def test_94_validation_output_errors_empty_on_valid(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["errors"] == []


def test_95_validation_locked_true_reflected(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["locked"] is True
