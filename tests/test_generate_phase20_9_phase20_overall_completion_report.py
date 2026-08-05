import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase20_9_phase20_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase20_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "20-1": "phase20_1_start_conditions_check_design_report.json",
        "20-2": "phase20_2_final_human_go_record_validation_report.json",
        "20-3": "phase20_3_execute_live_pre_execution_hard_stop_gate_report.json",
        "20-4": "phase20_4_execute_live_candidate_unlock_judgment_report.json",
        "20-5": "phase20_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "20-6": "phase20_6_execute_live_unexecuted_final_confirmation_report.json",
        "20-7": "phase20_7_execute_live_candidate_final_confirmation_report.json",
        "20-8": "phase20_8_execute_live_unexecuted_no_go_maintenance_report.json",
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

    output_json = logs / "phase20_9_phase20_overall_completion_report.json"
    output_md = logs / "phase20_9_phase20_overall_completion_report.md"

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
    assert stdout["phase20_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 20-9"
    assert report["status"] == "PASS"
    assert report["phase20_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase20_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "20-1": "phase20_1_start_conditions_check_design_report.json",
        "20-2": "phase20_2_final_human_go_record_validation_report.json",
        "20-3": "phase20_3_execute_live_pre_execution_hard_stop_gate_report.json",
        "20-4": "phase20_4_execute_live_candidate_unlock_judgment_report.json",
        "20-5": "phase20_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "20-6": "phase20_6_execute_live_unexecuted_final_confirmation_report.json",
        "20-7": "phase20_7_execute_live_candidate_final_confirmation_report.json",
        "20-8": "phase20_8_execute_live_unexecuted_no_go_maintenance_report.json",
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
        if phase == "20-5":
            data["publish_candidate_unlocked_for_operator"] = True
        _write(logs / filename, data)

    output_json = logs / "phase20_9_phase20_overall_completion_report.json"
    output_md = logs / "phase20_9_phase20_overall_completion_report.md"

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
    assert "phase20-5" in stdout["reason"]
