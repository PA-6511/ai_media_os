import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase13_8_phase13_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase13_8_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "13-1": "phase13_1_publish_execution_conditions_reconfirmation_report.json",
        "13-2": "phase13_2_human_final_go_input_file_creation_report.json",
        "13-3": "phase13_3_execute_live_pre_final_stop_gate_report.json",
        "13-4": "phase13_4_human_final_decision_file_read_design_report.json",
        "13-5": "phase13_5_unlock_candidate_judgment_on_go_conditions_design_report.json",
        "13-6": "phase13_6_pre_execute_live_final_no_go_maintenance_report.json",
        "13-7": "phase13_7_pre_publish_no_go_maintenance_report.json",
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

    output_json = logs / "phase13_8_phase13_overall_completion_report.json"
    output_md = logs / "phase13_8_phase13_overall_completion_report.md"

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
    assert stdout["phase13_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 13-8"
    assert report["status"] == "PASS"
    assert report["phase13_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase13_8_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "13-1": "phase13_1_publish_execution_conditions_reconfirmation_report.json",
        "13-2": "phase13_2_human_final_go_input_file_creation_report.json",
        "13-3": "phase13_3_execute_live_pre_final_stop_gate_report.json",
        "13-4": "phase13_4_human_final_decision_file_read_design_report.json",
        "13-5": "phase13_5_unlock_candidate_judgment_on_go_conditions_design_report.json",
        "13-6": "phase13_6_pre_execute_live_final_no_go_maintenance_report.json",
        "13-7": "phase13_7_pre_publish_no_go_maintenance_report.json",
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

    bad = logs / files["13-7"]
    payload = json.loads(bad.read_text(encoding="utf-8"))
    payload["publish_candidate_unlocked_for_operator"] = True
    _write(bad, payload)

    output_json = logs / "phase13_8_phase13_overall_completion_report.json"
    output_md = logs / "phase13_8_phase13_overall_completion_report.md"

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
