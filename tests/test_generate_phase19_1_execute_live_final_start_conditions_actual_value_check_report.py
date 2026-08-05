import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase19_1_execute_live_final_start_conditions_actual_value_check_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase19_1_report_pass(tmp_path: Path):
    input_18_9 = tmp_path / "phase18_9.json"
    output_json = tmp_path / "phase19_1.json"
    output_md = tmp_path / "phase19_1.md"

    input_18_9.write_text(
        json.dumps(
            {
                "phase": "Phase 18-9",
                "status": "PASS",
                "phase18_overall_status": "PASS",
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
        "--input-18-9",
        str(input_18_9),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase19_1_start_conditions_check_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase19_1_report_abort_on_invalid_input(tmp_path: Path):
    input_18_9 = tmp_path / "phase18_9.json"
    output_json = tmp_path / "phase19_1.json"
    output_md = tmp_path / "phase19_1.md"

    input_18_9.write_text(
        json.dumps(
            {
                "phase": "Phase 18-9",
                "status": "PASS",
                "phase18_overall_status": "PASS",
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
        "--input-18-9",
        str(input_18_9),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "current_decision" in stdout["reason"]
