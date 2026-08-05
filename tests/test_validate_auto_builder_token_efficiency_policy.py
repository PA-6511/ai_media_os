import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_auto_builder_token_efficiency_policy import (  # noqa: E402
    validate_policy_file,
)


def base_policy() -> dict:
    return {
        "phase": "AB-T0",
        "name": "Auto Builder Token Efficiency Layer v1",
        "status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "execution_status": "NO_EXECUTION",
        "dry_run_only": True,
        "external_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "production_write_allowed": False,
        "credential_output_allowed": False,
        "live_execution_allowed": False,
        "copilot_agent_default_allowed": False,
        "max_files_per_ai_context": 5,
        "max_lines_per_file_excerpt": 120,
        "git_diff_full_paste_allowed": False,
        "pytest_full_log_paste_allowed": False,
        "evidence_index_full_paste_allowed": False,
        "report_full_regeneration_allowed": False,
        "allowed_ai_context_inputs": [
            "phase closure card",
            "repository snapshot digest",
            "file manifest",
            "diff digest",
            "error-only log",
            "safety rule pack",
        ],
        "forbidden_ai_context_inputs": [
            "full repository dump",
            "full git diff",
            "full pytest log",
            "full evidence index",
            "credential files",
            "unrelated historical phase reports",
        ],
        "safety_rule_pack_id": "SAFETY_RULE_PACK_AB_V1",
        "safety_rule_pack": {
            "production_write_allowed": False,
            "wordpress_write_allowed": False,
            "external_api_call_allowed": False,
            "credential_output_allowed": False,
            "live_execution_allowed": False,
            "dry_run_only": True,
            "evidence_only": True,
            "next_phase_forward_execution": False,
            "secret_reading_allowed": False,
            "secret_printing_allowed": False,
        },
    }


def write_policy(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "config/auto_builder_token_efficiency_policy.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_normal_policy_passes(tmp_path: Path):
    path = write_policy(tmp_path, base_policy())
    result = validate_policy_file(path)
    assert result["status"] == "PASS"


def test_fails_when_production_status_go(tmp_path: Path):
    payload = copy.deepcopy(base_policy())
    payload["production_status"] = "GO"
    path = write_policy(tmp_path, payload)
    with pytest.raises(ValueError):
        validate_policy_file(path)


def test_fails_when_dry_run_only_false(tmp_path: Path):
    payload = copy.deepcopy(base_policy())
    payload["dry_run_only"] = False
    path = write_policy(tmp_path, payload)
    with pytest.raises(ValueError):
        validate_policy_file(path)


def test_fails_when_production_write_allowed_true(tmp_path: Path):
    payload = copy.deepcopy(base_policy())
    payload["production_write_allowed"] = True
    path = write_policy(tmp_path, payload)
    with pytest.raises(ValueError):
        validate_policy_file(path)


def test_fails_when_max_files_per_ai_context_over_5(tmp_path: Path):
    payload = copy.deepcopy(base_policy())
    payload["max_files_per_ai_context"] = 6
    path = write_policy(tmp_path, payload)
    with pytest.raises(ValueError):
        validate_policy_file(path)


def test_fails_when_git_diff_full_paste_allowed_true(tmp_path: Path):
    payload = copy.deepcopy(base_policy())
    payload["git_diff_full_paste_allowed"] = True
    path = write_policy(tmp_path, payload)
    with pytest.raises(ValueError):
        validate_policy_file(path)


def test_fails_when_safety_rule_pack_id_mismatch(tmp_path: Path):
    payload = copy.deepcopy(base_policy())
    payload["safety_rule_pack_id"] = "SAFETY_RULE_PACK_AB_V2"
    path = write_policy(tmp_path, payload)
    with pytest.raises(ValueError):
        validate_policy_file(path)
