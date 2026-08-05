from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/auto_builder_copilot_usage_saving_evidence_policy.json"
SCRIPT_PATH = ROOT / "scripts/build_auto_builder_copilot_usage_saving_evidence.py"
AB_T2 = ROOT / "exchange/logs/ab_t2_copilot_prompt_compression_result.json"
AB_T3 = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
AB_T4 = ROOT / "exchange/logs/ab_t4_patch_draft_generator_result.json"
AB_T5 = ROOT / "exchange/logs/ab_t5_limited_test_selector_result.json"


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


def test_required_keys_exist() -> None:
    policy = load_policy()
    for key in [
        "phase",
        "status",
        "purpose",
        "execution_mode",
        "production_status",
        "safety_state",
        "collect_from",
        "evidence_rules",
        "allowed_outputs",
        "forbidden_outputs",
        "next_phase",
    ]:
        assert key in policy


def test_execution_mode_design_only() -> None:
    assert load_policy()["execution_mode"] == "DESIGN_ONLY"


def test_production_status_no_go() -> None:
    assert load_policy()["production_status"] == "NO_GO"


def test_safety_state_dry_run_only() -> None:
    assert load_policy()["safety_state"] == "DRY_RUN_ONLY"


def test_ab_t2_to_t5_result_files_exist() -> None:
    assert AB_T2.exists()
    assert AB_T3.exists()
    assert AB_T4.exists()
    assert AB_T5.exists()


def test_script_execution_success(tmp_path: Path) -> None:
    cp, _, _ = run_script(tmp_path)
    assert cp.returncode == 0


def test_result_json_generated(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    assert out.exists()


def test_report_generated(tmp_path: Path) -> None:
    _, _, report = run_script(tmp_path)
    assert report.exists()


def test_all_previous_phases_verified_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["all_previous_phases_verified"] is True


def test_evidence_pack_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["evidence_pack_generated"] is True


def test_phase_status_table_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["phase_status_table_generated"] is True


def test_token_saving_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["token_saving_summary_generated"] is True


def test_safety_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["safety_summary_generated"] is True


def test_readiness_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["readiness_summary_generated"] is True


def test_forbidden_operations_all_blocked_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["forbidden_operations_all_blocked"] is True


def test_next_phase_phase_ab_t7(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["phase"] == "AB-T7"


def test_next_phase_execution_allowed_false(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["execution_allowed"] is False
