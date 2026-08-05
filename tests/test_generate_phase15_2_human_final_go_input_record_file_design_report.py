import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase15_2_human_final_go_input_record_file_design_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase15_2_report_pass(tmp_path: Path):
    input_15_1 = tmp_path / "phase15_1.json"
    output_json = tmp_path / "phase15_2.json"
    output_md = tmp_path / "phase15_2.md"

    input_15_1.write_text(
        json.dumps(
            {
                "phase": "Phase 15-1",
                "status": "PASS",
                "phase15_1_actual_value_check_status": "PASS",
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
        "--input-15-1",
        str(input_15_1),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase15_2_design_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase15_2_report_abort_on_invalid_input(tmp_path: Path):
    input_15_1 = tmp_path / "phase15_1.json"
    output_json = tmp_path / "phase15_2.json"
    output_md = tmp_path / "phase15_2.md"

    input_15_1.write_text(
        json.dumps(
            {
                "phase": "Phase 15-1",
                "status": "PASS",
                "phase15_1_actual_value_check_status": "PASS",
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
        "--input-15-1",
        str(input_15_1),
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
    assert report["design_generated"] is False
    assert output_md.exists() is False
