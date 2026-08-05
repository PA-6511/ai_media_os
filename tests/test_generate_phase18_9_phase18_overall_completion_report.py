import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase18_9_phase18_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase18_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "18-1": "phase18_1_phase18_start_conditions_actual_value_check_report.json",
        "18-2": "phase18_2_execute_live_production_candidate_final_risk_audit_report.json",
        "18-3": "phase18_3_execute_live_final_human_go_no_go_decision_design_report.json",
        "18-4": "phase18_4_final_human_decision_file_read_gate_report.json",
        "18-5": "phase18_5_execute_live_candidate_unlock_judgment_report.json",
        "18-6": "phase18_6_pre_execute_live_no_go_maintenance_report.json",
        "18-7": "phase18_7_execute_live_candidate_final_confirmation_report.json",
        "18-8": "phase18_8_pre_closure_no_go_maintenance_report.json",
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

    output_json = logs / "phase18_9_phase18_overall_completion_report.json"
    output_md = logs / "phase18_9_phase18_overall_completion_report.md"

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
    assert stdout["phase18_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 18-9"
    assert report["status"] == "PASS"
    assert report["phase18_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase18_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "18-1": "phase18_1_phase18_start_conditions_actual_value_check_report.json",
        "18-2": "phase18_2_execute_live_production_candidate_final_risk_audit_report.json",
        "18-3": "phase18_3_execute_live_final_human_go_no_go_decision_design_report.json",
        "18-4": "phase18_4_final_human_decision_file_read_gate_report.json",
        "18-5": "phase18_5_execute_live_candidate_unlock_judgment_report.json",
        "18-6": "phase18_6_pre_execute_live_no_go_maintenance_report.json",
        "18-7": "phase18_7_execute_live_candidate_final_confirmation_report.json",
        "18-8": "phase18_8_pre_closure_no_go_maintenance_report.json",
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
        # Break one of the files by changing publish_candidate_unlocked_for_operator
        if phase == "18-5":
            data["publish_candidate_unlocked_for_operator"] = True
        _write(logs / filename, data)

    output_json = logs / "phase18_9_phase18_overall_completion_report.json"
    output_md = logs / "phase18_9_phase18_overall_completion_report.md"

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
    assert "phase18-5" in stdout["reason"]
