import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase23_to_26_final_no_go_baseline_summary_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_payload(phase_label: str, overall_key: str) -> dict:
    return {
        "phase": phase_label,
        "status": "PASS",
        overall_key: "PASS",
        "execute_live_executed": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "target_draft_status": "draft",
    }


def _write_inputs(logs: Path) -> None:
    _write(logs / "phase23_4_phase23_overall_closure_report.json",
           _base_payload("Phase 23-4", "phase23_overall_status"))
    _write(logs / "phase24_4_phase24_overall_closure_report.json",
           _base_payload("Phase 24-4", "phase24_overall_status"))
    _write(logs / "phase25_4_phase25_overall_closure_report.json",
           _base_payload("Phase 25-4", "phase25_overall_status"))
    _write(logs / "phase26_4_phase26_overall_closure_report.json",
           _base_payload("Phase 26-4", "phase26_overall_status"))


def test_generate_phase23_to_26_summary_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    _write_inputs(logs)

    output_json = logs / "phase23_to_26_final_no_go_baseline_summary_report.json"
    output_md = logs / "phase23_to_26_final_no_go_baseline_summary_report.md"

    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--logs-dir", str(logs),
         "--output-json", str(output_json), "--output-md", str(output_md)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )

    assert res.returncode == 0, res.stdout + res.stderr
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "PASS"
    assert stdout["baseline_summary_status"] == "PASS"
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["baseline_summary_status"] == "PASS"
    assert report["execute_live_executed"] is False
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["final_no_go_baseline"]["execute_live_never_executed_across_phases_23_to_26"] is True
    assert output_md.exists()


def test_generate_phase23_to_26_summary_abort_when_closure_fails(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    _write_inputs(logs)

    # break phase 24-4
    broken = logs / "phase24_4_phase24_overall_closure_report.json"
    payload = json.loads(broken.read_text(encoding="utf-8"))
    payload["execute_live_executed"] = True
    broken.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    output_json = logs / "phase23_to_26_final_no_go_baseline_summary_report.json"
    output_md = logs / "phase23_to_26_final_no_go_baseline_summary_report.md"

    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--logs-dir", str(logs),
         "--output-json", str(output_json), "--output-md", str(output_md)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "phase24-4" in stdout["reason"]
