from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/auto_builder_related_file_selector_policy.json"
SCRIPT_PATH = ROOT / "scripts/select_auto_builder_related_files.py"


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def run_script(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    result_path = tmp_path / "exchange/logs/result.json"
    report_path = tmp_path / "reports/report.md"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy",
            str(POLICY_PATH),
            "--target-file",
            str(ROOT / "scripts/build_auto_builder_copilot_prompt_compression.py"),
            "--output",
            str(result_path),
            "--report",
            str(report_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return cp, result_path, report_path


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
        "selection_rules",
        "output_mode",
        "allowed_outputs",
        "forbidden_outputs",
        "next_phase",
    ]:
        assert key in policy


def test_max_related_files_is_5() -> None:
    assert load_policy()["selection_rules"]["max_related_files"] == 5


def test_max_lines_per_file_is_120() -> None:
    assert load_policy()["selection_rules"]["max_lines_per_file"] == 120


def test_execution_mode_design_only() -> None:
    assert load_policy()["execution_mode"] == "DESIGN_ONLY"


def test_production_status_no_go() -> None:
    assert load_policy()["production_status"] == "NO_GO"


def test_safety_state_dry_run_only() -> None:
    assert load_policy()["safety_state"] == "DRY_RUN_ONLY"


def test_exclude_patterns_exists() -> None:
    patterns = load_policy()["selection_rules"].get("exclude_patterns")
    assert isinstance(patterns, list)
    assert len(patterns) > 0


def test_selection_priority_exists() -> None:
    priority = load_policy()["selection_rules"].get("selection_priority")
    assert isinstance(priority, list)
    assert len(priority) > 0


def test_script_execution_success(tmp_path: Path) -> None:
    cp, _, _ = run_script(tmp_path)
    assert cp.returncode == 0


def test_result_json_generated(tmp_path: Path) -> None:
    _, result_path, _ = run_script(tmp_path)
    assert result_path.exists()


def test_report_generated(tmp_path: Path) -> None:
    _, _, report_path = run_script(tmp_path)
    assert report_path.exists()


def test_selector_ready_true(tmp_path: Path) -> None:
    _, result_path, _ = run_script(tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["selector_ready"] is True


def test_forbidden_operations_all_blocked_true(tmp_path: Path) -> None:
    _, result_path, _ = run_script(tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["forbidden_operations_all_blocked"] is True


def test_next_phase_phase_ab_t4(tmp_path: Path) -> None:
    _, result_path, _ = run_script(tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["next_phase"]["phase"] == "AB-T4"


def test_next_phase_execution_allowed_false(tmp_path: Path) -> None:
    _, result_path, _ = run_script(tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["next_phase"]["execution_allowed"] is False
