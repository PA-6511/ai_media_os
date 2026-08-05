from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/auto_builder_copilot_saving_dry_run_policy.json"
SCRIPT_PATH = ROOT / "scripts/build_auto_builder_copilot_saving_dry_run.py"
AB_T2 = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
AB_T3 = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
AB_T4 = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
AB_T5 = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"
AB_T6 = ROOT / "exchange/logs/ab_t6_copilot_usage_saving_evidence_result.json"
AB_T7 = ROOT / "exchange/logs/ab_t7_copilot_saving_integration_gate_result.json"


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def run_script(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    out = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--ab-t2-result",
            str(AB_T2),
            "--ab-t3-result",
            str(AB_T3),
            "--ab-t4-result",
            str(AB_T4),
            "--ab-t5-result",
            str(AB_T5),
            "--ab-t6-result",
            str(AB_T6),
            "--ab-t7-result",
            str(AB_T7),
            "--output",
            str(out),
            "--report",
            str(report),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return cp, out, report


def test_policy_json_exists() -> None:
    assert POLICY_PATH.exists()


def test_execution_mode_design_only() -> None:
    assert load_policy()["execution_mode"] == "DESIGN_ONLY"


def test_production_status_no_go() -> None:
    assert load_policy()["production_status"] == "NO_GO"


def test_safety_state_dry_run_only() -> None:
    assert load_policy()["safety_state"] == "DRY_RUN_ONLY"


def test_ab_t2_to_t7_result_files_exist() -> None:
    assert AB_T2.exists()
    assert AB_T3.exists()
    assert AB_T4.exists()
    assert AB_T5.exists()
    assert AB_T6.exists()
    assert AB_T7.exists()


def test_script_execution_success(tmp_path: Path) -> None:
    cp, _, _ = run_script(tmp_path)
    assert cp.returncode == 0


def test_result_json_generated(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    assert out.exists()


def test_report_generated(tmp_path: Path) -> None:
    _, _, report = run_script(tmp_path)
    assert report.exists()


def test_verified_phase_count_6(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["verified_phase_count"] == 6


def test_pipeline_ready_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["pipeline_ready"] is True


def test_dry_run_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["dry_run_summary_generated"] is True


def test_simulated_prompt_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["simulated_prompt_generated"] is True


def test_simulated_patch_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["simulated_patch_generated"] is True


def test_simulated_test_plan_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["simulated_test_plan_generated"] is True


def test_pipeline_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["pipeline_summary_generated"] is True


def test_safety_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["safety_summary_generated"] is True


def test_forbidden_operations_all_blocked_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["forbidden_operations_all_blocked"] is True


def test_next_phase_phase_ab_t9(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["phase"] == "AB-T9"


def test_next_phase_execution_allowed_false(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["execution_allowed"] is False