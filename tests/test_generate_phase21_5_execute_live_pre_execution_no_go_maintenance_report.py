import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase21_5_execute_live_pre_execution_no_go_maintenance_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase21_5_report_pass(tmp_path: Path):
    input_21_4 = tmp_path / "phase21_4.json"
    output_json = tmp_path / "phase21_5.json"
    output_md = tmp_path / "phase21_5.md"

    input_21_4.write_text(
        json.dumps(
            {
                "phase": "Phase 21-4",
                "status": "PASS",
                "phase21_4_judgment_status": "PASS",
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
        "--input-21-4",
        str(input_21_4),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase21_5_no_go_maintenance_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase21_5_report_abort_on_invalid_input(tmp_path: Path):
    input_21_4 = tmp_path / "phase21_4.json"
    output_json = tmp_path / "phase21_5.json"
    output_md = tmp_path / "phase21_5.md"

    input_21_4.write_text(
        json.dumps(
            {
                "phase": "Phase 21-4",
                "status": "PASS",
                "phase21_4_judgment_status": "ABORT",
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
        "--input-21-4",
        str(input_21_4),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "phase21_4_judgment_status" in stdout["reason"]
