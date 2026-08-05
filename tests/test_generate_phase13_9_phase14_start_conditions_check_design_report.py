import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase13_9_phase14_start_conditions_check_design_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase13_9_report_pass(tmp_path: Path):
    input_13_8 = tmp_path / "phase13_8.json"
    output_json = tmp_path / "phase13_9.json"
    output_md = tmp_path / "phase13_9.md"

    input_13_8.write_text(
        json.dumps(
            {
                "phase": "Phase 13-8",
                "status": "PASS",
                "phase13_overall_status": "PASS",
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
        "--input-13-8",
        str(input_13_8),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase13_9_design_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase13_9_report_abort_on_invalid_input(tmp_path: Path):
    input_13_8 = tmp_path / "phase13_8.json"
    output_json = tmp_path / "phase13_9.json"
    output_md = tmp_path / "phase13_9.md"

    input_13_8.write_text(
        json.dumps(
            {
                "phase": "Phase 13-8",
                "status": "PASS",
                "phase13_overall_status": "PASS",
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
        "--input-13-8",
        str(input_13_8),
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
    assert report["phase14_check_design_generated"] is False
    assert output_md.exists() is False
