import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase24_3_continued_keep_no_go_fixation_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase24_3_report_pass(tmp_path: Path):
    input_24_2 = tmp_path / "phase24_2.json"
    output_json = tmp_path / "phase24_3.json"
    output_md = tmp_path / "phase24_3.md"

    input_24_2.write_text(
        json.dumps(
            {
                "phase": "Phase 24-2",
                "status": "PASS",
                "phase24_2_stop_decision_status": "PASS",
                "execute_live_executed": False,
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
        "--input-24-2",
        str(input_24_2),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase24_3_fixation_status"] == "PASS"
    assert report["execute_live_executed"] is False
    assert report["current_decision"] == "KEEP_NO_GO"
    assert output_md.exists()


def test_generate_phase24_3_report_abort_on_invalid_input(tmp_path: Path):
    input_24_2 = tmp_path / "phase24_2.json"
    output_json = tmp_path / "phase24_3.json"
    output_md = tmp_path / "phase24_3.md"

    input_24_2.write_text(
        json.dumps(
            {
                "phase": "Phase 24-2",
                "status": "PASS",
                "phase24_2_stop_decision_status": "PASS",
                "execute_live_executed": False,
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": True,
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
        "--input-24-2",
        str(input_24_2),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "publish_candidate_unlocked_for_operator" in stdout["reason"]