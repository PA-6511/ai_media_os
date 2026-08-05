import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase24_4_phase24_overall_closure_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase24_4_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "24-1": "phase24_1_phase23_closure_evidence_reconfirmation_report.json",
        "24-2": "phase24_2_execute_live_final_stop_decision_report.json",
        "24-3": "phase24_3_continued_keep_no_go_fixation_report.json",
    }

    for phase, filename in files.items():
        payload = {
            "phase": f"Phase {phase}",
            "status": "PASS",
            "execute_live_executed": False,
            "current_decision": "KEEP_NO_GO",
            "publish_candidate_unlocked_for_operator": False,
            "wordpress_publish_execution": "NO_GO",
            "wordpress_write_executed": False,
            "production_status": "NO_GO",
            "target_draft_status": "draft",
        }
        _write(logs / filename, payload)

    output_json = logs / "phase24_4_phase24_overall_closure_report.json"
    output_md = logs / "phase24_4_phase24_overall_closure_report.md"

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
    assert stdout["phase24_overall_closure_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 24-4"
    assert report["status"] == "PASS"
    assert report["phase24_overall_status"] == "PASS"
    assert report["execute_live_executed"] is False
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase24_4_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "24-1": "phase24_1_phase23_closure_evidence_reconfirmation_report.json",
        "24-2": "phase24_2_execute_live_final_stop_decision_report.json",
        "24-3": "phase24_3_continued_keep_no_go_fixation_report.json",
    }

    for phase, filename in files.items():
        payload = {
            "phase": f"Phase {phase}",
            "status": "PASS",
            "execute_live_executed": False,
            "current_decision": "KEEP_NO_GO",
            "publish_candidate_unlocked_for_operator": False,
            "wordpress_publish_execution": "NO_GO",
            "wordpress_write_executed": False,
            "production_status": "NO_GO",
            "target_draft_status": "draft",
        }
        if phase == "24-2":
            payload["execute_live_executed"] = True
        _write(logs / filename, payload)

    output_json = logs / "phase24_4_phase24_overall_closure_report.json"
    output_md = logs / "phase24_4_phase24_overall_closure_report.md"

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
    assert "phase24-2" in stdout["reason"]