from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/auto_builder_patch_draft_generator_policy.json"
SCRIPT_PATH = ROOT / "scripts/build_auto_builder_patch_draft_generator.py"
AB_T3_RESULT_PATH = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"


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
            "--ab-t3-result",
            str(AB_T3_RESULT_PATH),
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
        "draft_rules",
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


def test_max_patch_targets_is_5() -> None:
    assert load_policy()["draft_rules"]["max_patch_targets"] == 5


def test_generate_patch_template_true() -> None:
    assert load_policy()["draft_rules"]["generate_patch_template"] is True


def test_generate_unified_diff_false() -> None:
    assert load_policy()["draft_rules"]["generate_unified_diff"] is False


def test_generate_apply_command_false() -> None:
    assert load_policy()["draft_rules"]["generate_apply_command"] is False


def test_generate_git_command_false() -> None:
    assert load_policy()["draft_rules"]["generate_git_command"] is False


def test_script_execution_success(tmp_path: Path) -> None:
    cp, _, _ = run_script(tmp_path)
    assert cp.returncode == 0


def test_result_json_generated(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    assert out.exists()


def test_report_generated(tmp_path: Path) -> None:
    _, _, report = run_script(tmp_path)
    assert report.exists()


def test_generated_patch_draft_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["generated_patch_draft"] is True


def test_change_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["change_summary_generated"] is True


def test_risk_summary_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["risk_summary_generated"] is True


def test_validation_checklist_generated_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["validation_checklist_generated"] is True


def test_forbidden_operations_all_blocked_true(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["forbidden_operations_all_blocked"] is True


def test_next_phase_phase_ab_t5(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["phase"] == "AB-T5"


def test_next_phase_execution_allowed_false(tmp_path: Path) -> None:
    _, out, _ = run_script(tmp_path)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["next_phase"]["execution_allowed"] is False
