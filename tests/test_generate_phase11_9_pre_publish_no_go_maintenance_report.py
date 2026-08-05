import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase11_9_pre_publish_no_go_maintenance_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase11_9_report_pass(tmp_path: Path):
    input_11_8 = tmp_path / "phase11_8.json"
    output_json = tmp_path / "phase11_9.json"
    output_md = tmp_path / "phase11_9.md"

    input_11_8.write_text(
        json.dumps(
            {
                "phase": "Phase 11-8",
                "status": "PASS",
                "phase11_8_final_confirmation_status": "PASS",
                "phase11_7_final_judgment": "KEEP_NO_GO",
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "wordpress_draft_id": 110,
                "target_draft_status": "draft",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    res = run_script(
        "--input-11-8",
        str(input_11_8),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "PASS"
    assert stdout["phase11_9_maintenance_status"] == "PASS"

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 11-9"
    assert report["status"] == "PASS"
    assert report["phase11_9_maintenance_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["next_step"] == "phase11_10_phase11_overall_completion_report"
    assert output_md.exists()


def test_generate_phase11_9_report_abort_on_invalid_input(tmp_path: Path):
    input_11_8 = tmp_path / "phase11_8.json"
    output_json = tmp_path / "phase11_9.json"
    output_md = tmp_path / "phase11_9.md"

    input_11_8.write_text(
        json.dumps(
            {
                "phase": "Phase 11-8",
                "status": "PASS",
                "phase11_8_final_confirmation_status": "PASS",
                "phase11_7_final_judgment": "KEEP_NO_GO",
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": True,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "wordpress_draft_id": 110,
                "target_draft_status": "draft",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    res = run_script(
        "--input-11-8",
        str(input_11_8),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "publish_candidate_unlocked_for_operator" in stdout["reason"]

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "ABORT"
    assert report["maintenance_report_generated"] is False
    assert output_md.exists() is False
