import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase23_1_final_no_go_state_reconfirmation_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase23_1_report_pass(tmp_path: Path):
    input_22_9 = tmp_path / "phase22_9.json"
    output_json = tmp_path / "phase23_1.json"
    output_md = tmp_path / "phase23_1.md"

    input_22_9.write_text(
        json.dumps(
            {
                "phase": "Phase 22-9",
                "status": "PASS",
                "phase22_overall_status": "PASS",
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
        "--input-22-9",
        str(input_22_9),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase23_1_reconfirmation_status"] == "PASS"
    assert report["execute_live_executed"] is False
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["production_status"] == "NO_GO"
    assert report["target_draft_status"] == "draft"
    assert output_md.exists()


def test_generate_phase23_1_report_abort_on_invalid_input(tmp_path: Path):
    input_22_9 = tmp_path / "phase22_9.json"
    output_json = tmp_path / "phase23_1.json"
    output_md = tmp_path / "phase23_1.md"

    input_22_9.write_text(
        json.dumps(
            {
                "phase": "Phase 22-9",
                "status": "PASS",
                "phase22_overall_status": "PASS",
                "current_decision": "GO",
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
        "--input-22-9",
        str(input_22_9),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "current_decision" in stdout["reason"]
