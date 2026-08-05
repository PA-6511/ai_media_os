import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase25_1_phase24_closure_evidence_reconfirmation_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase25_1_report_pass(tmp_path: Path):
    input_24_4 = tmp_path / "phase24_4.json"
    output_json = tmp_path / "phase25_1.json"
    output_md = tmp_path / "phase25_1.md"

    input_24_4.write_text(
        json.dumps(
            {
                "phase": "Phase 24-4",
                "status": "PASS",
                "phase24_overall_closure_status": "PASS",
                "phase24_overall_status": "PASS",
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
        "--input-24-4",
        str(input_24_4),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase25_1_reconfirmation_status"] == "PASS"
    assert report["execute_live_executed"] is False
    assert report["current_decision"] == "KEEP_NO_GO"
    assert output_md.exists()


def test_generate_phase25_1_report_abort_on_invalid_input(tmp_path: Path):
    input_24_4 = tmp_path / "phase24_4.json"
    output_json = tmp_path / "phase25_1.json"
    output_md = tmp_path / "phase25_1.md"

    input_24_4.write_text(
        json.dumps(
            {
                "phase": "Phase 24-4",
                "status": "PASS",
                "phase24_overall_closure_status": "PASS",
                "phase24_overall_status": "PASS",
                "execute_live_executed": True,
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
        "--input-24-4",
        str(input_24_4),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "execute_live_executed" in stdout["reason"]