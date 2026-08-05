import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase25_4_phase25_overall_closure_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase25_4_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "25-1": "phase25_1_phase24_closure_evidence_reconfirmation_report.json",
        "25-2": "phase25_2_no_human_go_execution_prohibition_confirmation_report.json",
        "25-3": "phase25_3_execute_live_candidate_not_unlocked_final_judgment_report.json",
    }

    for phase, filename in files.items():
        _write(
            logs / filename,
            {
                "phase": f"Phase {phase}",
                "status": "PASS",
                "execute_live_executed": False,
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "target_draft_status": "draft",
            },
        )

    output_json = logs / "phase25_4_phase25_overall_closure_report.json"
    output_md = logs / "phase25_4_phase25_overall_closure_report.md"

    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--logs-dir", str(logs),
         "--output-json", str(output_json), "--output-md", str(output_md)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )

    assert res.returncode == 0, res.stdout + res.stderr
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "PASS"
    assert stdout["phase25_overall_closure_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 25-4"
    assert report["status"] == "PASS"
    assert report["phase25_overall_status"] == "PASS"
    assert report["execute_live_executed"] is False
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase25_4_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "25-1": "phase25_1_phase24_closure_evidence_reconfirmation_report.json",
        "25-2": "phase25_2_no_human_go_execution_prohibition_confirmation_report.json",
        "25-3": "phase25_3_execute_live_candidate_not_unlocked_final_judgment_report.json",
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
        if phase == "25-3":
            payload["execute_live_executed"] = True
        _write(logs / filename, payload)

    output_json = logs / "phase25_4_phase25_overall_closure_report.json"
    output_md = logs / "phase25_4_phase25_overall_closure_report.md"

    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--logs-dir", str(logs),
         "--output-json", str(output_json), "--output-md", str(output_md)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "phase25-3" in stdout["reason"]
