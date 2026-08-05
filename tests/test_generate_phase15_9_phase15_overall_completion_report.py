import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase15_9_phase15_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase15_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "15-1": "phase15_1_execute_live_resume_conditions_actual_value_check_report.json",
        "15-2": "phase15_2_human_final_go_input_record_file_design_report.json",
        "15-3": "phase15_3_execute_live_final_stop_gate_implementation_report.json",
        "15-4": "phase15_4_human_final_go_record_file_read_gate_report.json",
        "15-5": "phase15_5_execute_live_candidate_unlock_judgment_report.json",
        "15-6": "phase15_6_pre_execute_live_no_go_maintenance_report.json",
        "15-7": "phase15_7_execute_live_candidate_final_confirmation_report.json",
        "15-8": "phase15_8_pre_execute_live_no_go_maintenance_report.json",
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
                "wordpress_draft_id": 110,
                "target_draft_status": "draft",
            },
        )

    output_json = logs / "phase15_9_phase15_overall_completion_report.json"
    output_md = logs / "phase15_9_phase15_overall_completion_report.md"

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
    assert stdout["phase15_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 15-9"
    assert report["status"] == "PASS"
    assert report["phase15_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase15_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "15-1": "phase15_1_execute_live_resume_conditions_actual_value_check_report.json",
        "15-2": "phase15_2_human_final_go_input_record_file_design_report.json",
        "15-3": "phase15_3_execute_live_final_stop_gate_implementation_report.json",
        "15-4": "phase15_4_human_final_go_record_file_read_gate_report.json",
        "15-5": "phase15_5_execute_live_candidate_unlock_judgment_report.json",
        "15-6": "phase15_6_pre_execute_live_no_go_maintenance_report.json",
        "15-7": "phase15_7_execute_live_candidate_final_confirmation_report.json",
        "15-8": "phase15_8_pre_execute_live_no_go_maintenance_report.json",
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
                "wordpress_draft_id": 110,
                "target_draft_status": "draft",
            },
        )

    bad = logs / files["15-8"]
    payload = json.loads(bad.read_text(encoding="utf-8"))
    payload["publish_candidate_unlocked_for_operator"] = True
    _write(bad, payload)

    output_json = logs / "phase15_9_phase15_overall_completion_report.json"
    output_md = logs / "phase15_9_phase15_overall_completion_report.md"

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
    assert "publish_candidate_unlocked_for_operator" in stdout["reason"]
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["overall_report_generated"] is False
    assert output_md.exists() is False
