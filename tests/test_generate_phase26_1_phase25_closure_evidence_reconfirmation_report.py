import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase26_1_phase25_closure_evidence_reconfirmation_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_generate_phase26_1_report_pass(tmp_path: Path):
    input_25_4 = tmp_path / "phase25_4.json"
    output_json = tmp_path / "phase26_1.json"
    output_md = tmp_path / "phase26_1.md"

    input_25_4.write_text(
        json.dumps(
            {
                "phase": "Phase 25-4",
                "status": "PASS",
                "phase25_overall_closure_status": "PASS",
                "phase25_overall_status": "PASS",
                "execute_live_executed": False,
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "target_draft_status": "draft",
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    res = run_script(
        "--input-25-4", str(input_25_4),
        "--output-json", str(output_json),
        "--output-md", str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase26_1_reconfirmation_status"] == "PASS"
    assert report["execute_live_executed"] is False
    assert report["current_decision"] == "KEEP_NO_GO"
    assert output_md.exists()


def test_generate_phase26_1_report_abort_on_invalid_input(tmp_path: Path):
    input_25_4 = tmp_path / "phase25_4.json"
    output_json = tmp_path / "phase26_1.json"
    output_md = tmp_path / "phase26_1.md"

    input_25_4.write_text(
        json.dumps(
            {
                "phase": "Phase 25-4",
                "status": "PASS",
                "phase25_overall_closure_status": "PASS",
                "phase25_overall_status": "PASS",
                "execute_live_executed": True,
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "target_draft_status": "draft",
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    res = run_script(
        "--input-25-4", str(input_25_4),
        "--output-json", str(output_json),
        "--output-md", str(output_md),
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "execute_live_executed" in stdout["reason"]
