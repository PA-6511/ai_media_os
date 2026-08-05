import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase22_9_phase22_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase22_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "22-1": "phase22_1_start_conditions_check_design_report.json",
        "22-2": "phase22_2_final_human_go_input_read_report.json",
        "22-3": "phase22_3_execute_live_final_viability_judgment_report.json",
        "22-4": "phase22_4_execute_live_candidate_unlock_judgment_report.json",
        "22-5": "phase22_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "22-6": "phase22_6_execute_live_unexecuted_final_confirmation_report.json",
        "22-7": "phase22_7_execute_live_candidate_final_confirmation_report.json",
        "22-8": "phase22_8_execute_live_unexecuted_no_go_maintenance_report.json",
    }

    for phase, filename in files.items():
        _write(
            logs / filename,
            {
                "phase": f"Phase {phase}",
                "status": "PASS",
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "target_draft_status": "draft",
            },
        )

    output_json = logs / "phase22_9_phase22_overall_completion_report.json"
    output_md = logs / "phase22_9_phase22_overall_completion_report.md"

    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logs-dir",
            str(logs),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert res.returncode == 0, res.stdout + res.stderr
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "PASS"
    assert stdout["phase22_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 22-9"
    assert report["status"] == "PASS"
    assert report["phase22_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase22_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "22-1": "phase22_1_start_conditions_check_design_report.json",
        "22-2": "phase22_2_final_human_go_input_read_report.json",
        "22-3": "phase22_3_execute_live_final_viability_judgment_report.json",
        "22-4": "phase22_4_execute_live_candidate_unlock_judgment_report.json",
        "22-5": "phase22_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "22-6": "phase22_6_execute_live_unexecuted_final_confirmation_report.json",
        "22-7": "phase22_7_execute_live_candidate_final_confirmation_report.json",
        "22-8": "phase22_8_execute_live_unexecuted_no_go_maintenance_report.json",
    }

    for phase, filename in files.items():
        data = {
            "phase": f"Phase {phase}",
            "status": "PASS",
            "current_decision": "KEEP_NO_GO",
            "publish_candidate_unlocked_for_operator": False,
            "wordpress_publish_execution": "NO_GO",
            "wordpress_write_executed": False,
            "production_status": "NO_GO",
            "target_draft_status": "draft",
        }
        if phase == "22-7":
            data["wordpress_write_executed"] = True
        _write(logs / filename, data)

    output_json = logs / "phase22_9_phase22_overall_completion_report.json"
    output_md = logs / "phase22_9_phase22_overall_completion_report.md"

    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logs-dir",
            str(logs),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "phase22-7" in stdout["reason"]
