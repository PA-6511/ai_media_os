import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase22_8_execute_live_unexecuted_no_go_maintenance_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase22_8_report_pass(tmp_path: Path):
    input_22_7 = tmp_path / "phase22_7.json"
    output_json = tmp_path / "phase22_8.json"
    output_md = tmp_path / "phase22_8.md"

    input_22_7.write_text(
        json.dumps(
            {
                "phase": "Phase 22-7",
                "status": "PASS",
                "phase22_7_final_confirmation_status": "PASS",
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "target_draft_status": "draft",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    res = run_script(
        "--input-22-7",
        str(input_22_7),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase22_8_no_go_maintenance_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase22_8_report_abort_on_invalid_input(tmp_path: Path):
    input_22_7 = tmp_path / "phase22_7.json"
    output_json = tmp_path / "phase22_8.json"
    output_md = tmp_path / "phase22_8.md"

    input_22_7.write_text(
        json.dumps(
            {
                "phase": "Phase 22-7",
                "status": "ABORT",
                "phase22_7_final_confirmation_status": "PASS",
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "target_draft_status": "draft",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    res = run_script(
        "--input-22-7",
        str(input_22_7),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "status" in stdout["reason"]
