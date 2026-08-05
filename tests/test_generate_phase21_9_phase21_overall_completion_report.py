import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase21_9_phase21_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase21_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "21-1": "phase21_1_start_conditions_check_design_report.json",
        "21-2": "phase21_2_final_human_go_record_validation_report.json",
        "21-3": "phase21_3_execute_live_pre_execution_hard_stop_gate_report.json",
        "21-4": "phase21_4_execute_live_candidate_unlock_judgment_report.json",
        "21-5": "phase21_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "21-6": "phase21_6_execute_live_unexecuted_final_confirmation_report.json",
        "21-7": "phase21_7_execute_live_candidate_final_confirmation_report.json",
        "21-8": "phase21_8_execute_live_unexecuted_no_go_maintenance_report.json",
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

    output_json = logs / "phase21_9_phase21_overall_completion_report.json"
    output_md = logs / "phase21_9_phase21_overall_completion_report.md"

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
    assert stdout["phase21_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 21-9"
    assert report["status"] == "PASS"
    assert report["phase21_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase21_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "21-1": "phase21_1_start_conditions_check_design_report.json",
        "21-2": "phase21_2_final_human_go_record_validation_report.json",
        "21-3": "phase21_3_execute_live_pre_execution_hard_stop_gate_report.json",
        "21-4": "phase21_4_execute_live_candidate_unlock_judgment_report.json",
        "21-5": "phase21_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "21-6": "phase21_6_execute_live_unexecuted_final_confirmation_report.json",
        "21-7": "phase21_7_execute_live_candidate_final_confirmation_report.json",
        "21-8": "phase21_8_execute_live_unexecuted_no_go_maintenance_report.json",
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
        if phase == "21-6":
            data["wordpress_write_executed"] = True
        _write(logs / filename, data)

    output_json = logs / "phase21_9_phase21_overall_completion_report.json"
    output_md = logs / "phase21_9_phase21_overall_completion_report.md"

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
    assert "phase21-6" in stdout["reason"]
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase21_9_phase21_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase21_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "21-1": "phase21_1_start_conditions_check_design_report.json",
        "21-2": "phase21_2_final_human_go_record_validation_report.json",
        "21-3": "phase21_3_execute_live_pre_execution_hard_stop_gate_report.json",
        "21-4": "phase21_4_execute_live_candidate_unlock_judgment_report.json",
        "21-5": "phase21_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "21-6": "phase21_6_execute_live_unexecuted_final_confirmation_report.json",
        "21-7": "phase21_7_execute_live_candidate_final_confirmation_report.json",
        "21-8": "phase21_8_execute_live_unexecuted_no_go_maintenance_report.json",
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

    output_json = logs / "phase21_9_phase21_overall_completion_report.json"
    output_md = logs / "phase21_9_phase21_overall_completion_report.md"

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
    assert stdout["phase21_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 21-9"
    assert report["status"] == "PASS"
    assert report["phase21_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase21_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "21-1": "phase21_1_start_conditions_check_design_report.json",
        "21-2": "phase21_2_final_human_go_record_validation_report.json",
        "21-3": "phase21_3_execute_live_pre_execution_hard_stop_gate_report.json",
        "21-4": "phase21_4_execute_live_candidate_unlock_judgment_report.json",
        "21-5": "phase21_5_execute_live_pre_execution_no_go_maintenance_report.json",
        "21-6": "phase21_6_execute_live_unexecuted_final_confirmation_report.json",
        "21-7": "phase21_7_execute_live_candidate_final_confirmation_report.json",
        "21-8": "phase21_8_execute_live_unexecuted_no_go_maintenance_report.json",
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
        if phase == "21-6":
            data["wordpress_write_executed"] = True
        _write(logs / filename, data)

    output_json = logs / "phase21_9_phase21_overall_completion_report.json"
    output_md = logs / "phase21_9_phase21_overall_completion_report.md"

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
    assert "phase21-6" in stdout["reason"]
