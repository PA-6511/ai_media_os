import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase19_9_phase19_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase19_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "19-1": "phase19_1_execute_live_final_start_conditions_actual_value_check_report.json",
        "19-2": "phase19_2_one_item_limited_publish_execution_plan_finalization_report.json",
        "19-3": "phase19_3_execute_live_pre_execution_stop_gate_report.json",
        "19-4": "phase19_4_human_final_go_execution_record_file_read_gate_report.json",
        "19-5": "phase19_5_execute_live_candidate_unlock_judgment_report.json",
        "19-6": "phase19_6_execute_live_pre_execution_no_go_maintenance_report.json",
        "19-7": "phase19_7_execute_live_candidate_final_confirmation_report.json",
        "19-8": "phase19_8_execute_live_unexecuted_no_go_maintenance_report.json",
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

    output_json = logs / "phase19_9_phase19_overall_completion_report.json"
    output_md = logs / "phase19_9_phase19_overall_completion_report.md"

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
    assert stdout["phase19_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 19-9"
    assert report["status"] == "PASS"
    assert report["phase19_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase19_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "19-1": "phase19_1_execute_live_final_start_conditions_actual_value_check_report.json",
        "19-2": "phase19_2_one_item_limited_publish_execution_plan_finalization_report.json",
        "19-3": "phase19_3_execute_live_pre_execution_stop_gate_report.json",
        "19-4": "phase19_4_human_final_go_execution_record_file_read_gate_report.json",
        "19-5": "phase19_5_execute_live_candidate_unlock_judgment_report.json",
        "19-6": "phase19_6_execute_live_pre_execution_no_go_maintenance_report.json",
        "19-7": "phase19_7_execute_live_candidate_final_confirmation_report.json",
        "19-8": "phase19_8_execute_live_unexecuted_no_go_maintenance_report.json",
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
        # Break one of the files by changing current_decision
        if phase == "19-6":
            data["current_decision"] = "GO"
        _write(logs / filename, data)

    output_json = logs / "phase19_9_phase19_overall_completion_report.json"
    output_md = logs / "phase19_9_phase19_overall_completion_report.md"

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
    assert "phase19-6" in stdout["reason"]
