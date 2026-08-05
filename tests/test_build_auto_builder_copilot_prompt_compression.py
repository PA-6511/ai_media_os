from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/auto_builder_copilot_prompt_compression_policy.json"
SCRIPT_PATH = ROOT / "scripts/build_auto_builder_copilot_prompt_compression.py"


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_policy_json_exists() -> None:
    assert POLICY_PATH.exists()


def test_required_keys_exist() -> None:
    policy = load_policy()
    for key in [
        "phase",
        "status",
        "purpose",
        "max_files_per_ai_context",
        "max_lines_per_file_excerpt",
        "copilot_agent_default_allowed",
        "external_api_call_allowed",
        "credential_read_allowed",
        "credential_output_allowed",
        "wordpress_write_allowed",
        "production_write_allowed",
        "destructive_operation_allowed",
        "execution_mode",
        "production_status",
        "safety_state",
        "output_mode",
        "allowed_outputs",
        "forbidden_outputs",
        "next_phase",
    ]:
        assert key in policy


def test_max_files_per_ai_context_is_5() -> None:
    assert load_policy()["max_files_per_ai_context"] == 5


def test_max_lines_per_file_excerpt_is_120() -> None:
    assert load_policy()["max_lines_per_file_excerpt"] == 120


def test_copilot_agent_default_allowed_false() -> None:
    assert load_policy()["copilot_agent_default_allowed"] is False


def test_credential_read_allowed_false() -> None:
    assert load_policy()["credential_read_allowed"] is False


def test_credential_output_allowed_false() -> None:
    assert load_policy()["credential_output_allowed"] is False


def test_wordpress_write_allowed_false() -> None:
    assert load_policy()["wordpress_write_allowed"] is False


def test_production_write_allowed_false() -> None:
    assert load_policy()["production_write_allowed"] is False


def test_external_api_call_allowed_false() -> None:
    assert load_policy()["external_api_call_allowed"] is False


def test_destructive_operation_allowed_false() -> None:
    assert load_policy()["destructive_operation_allowed"] is False


def test_execution_mode_design_only() -> None:
    assert load_policy()["execution_mode"] == "DESIGN_ONLY"


def test_production_status_no_go() -> None:
    assert load_policy()["production_status"] == "NO_GO"


def test_safety_state_dry_run_only() -> None:
    assert load_policy()["safety_state"] == "DRY_RUN_ONLY"


def test_script_execution_generates_result_json(tmp_path: Path) -> None:
    out = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(out),
            "--report",
            str(report),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    assert out.exists()


def test_script_execution_generates_report_markdown(tmp_path: Path) -> None:
    out = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(out),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert report.exists()


def test_generated_prompt_template_exists_true(tmp_path: Path) -> None:
    out = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(out),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["generated_prompt_template_exists"] is True


def test_forbidden_operations_all_blocked_true(tmp_path: Path) -> None:
    out = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(out),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["forbidden_operations_all_blocked"] is True


def test_next_phase_phase_ab_t3(tmp_path: Path) -> None:
    out = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(out),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["phase"] == "AB-T3"


def test_next_phase_execution_allowed_false(tmp_path: Path) -> None:
    out = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(out),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["execution_allowed"] is False
