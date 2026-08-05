import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase12_9_phase12_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase12_9_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "12-1": "phase12_1_phase12_start_conditions_actual_value_check_report.json",
        "12-2": "phase12_2_single_publish_final_go_redecision_input_design_report.json",
        "12-3": "phase12_3_publish_candidate_unlock_final_gate_design_report.json",
        "12-4": "phase12_4_publish_candidate_unlock_judgment_record_design_report.json",
        "12-5": "phase12_5_pre_execution_lock_reconfirmation_design_report.json",
        "12-6": "phase12_6_pre_execution_final_dry_run_audit_report.json",
        "12-7": "phase12_7_publish_candidate_unlock_final_confirmation_report.json",
        "12-8": "phase12_8_pre_publish_no_go_maintenance_report.json",
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

    output_json = logs / "phase12_9_phase12_overall_completion_report.json"
    output_md = logs / "phase12_9_phase12_overall_completion_report.md"

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
    assert stdout["phase12_overall_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 12-9"
    assert report["status"] == "PASS"
    assert report["phase12_overall_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase12_9_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "12-1": "phase12_1_phase12_start_conditions_actual_value_check_report.json",
        "12-2": "phase12_2_single_publish_final_go_redecision_input_design_report.json",
        "12-3": "phase12_3_publish_candidate_unlock_final_gate_design_report.json",
        "12-4": "phase12_4_publish_candidate_unlock_judgment_record_design_report.json",
        "12-5": "phase12_5_pre_execution_lock_reconfirmation_design_report.json",
        "12-6": "phase12_6_pre_execution_final_dry_run_audit_report.json",
        "12-7": "phase12_7_publish_candidate_unlock_final_confirmation_report.json",
        "12-8": "phase12_8_pre_publish_no_go_maintenance_report.json",
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

    bad = logs / files["12-8"]
    payload = json.loads(bad.read_text(encoding="utf-8"))
    payload["publish_candidate_unlocked_for_operator"] = True
    _write(bad, payload)

    output_json = logs / "phase12_9_phase12_overall_completion_report.json"
    output_md = logs / "phase12_9_phase12_overall_completion_report.md"

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
