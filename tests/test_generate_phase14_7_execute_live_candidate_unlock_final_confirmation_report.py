import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "scripts"
    / "generate_phase14_7_execute_live_candidate_unlock_final_confirmation_report.py"
)


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase14_7_report_pass(tmp_path: Path):
    input_14_6 = tmp_path / "phase14_6.json"
    output_json = tmp_path / "phase14_7.json"
    output_md = tmp_path / "phase14_7.md"

    input_14_6.write_text(
        json.dumps(
            {
                "phase": "Phase 14-6",
                "status": "PASS",
                "phase14_6_audit_status": "PASS",
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
        "--input-14-6",
        str(input_14_6),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["phase14_7_confirmation_status"] == "PASS"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert output_md.exists()


def test_generate_phase14_7_report_abort_on_invalid_input(tmp_path: Path):
    input_14_6 = tmp_path / "phase14_6.json"
    output_json = tmp_path / "phase14_7.json"
    output_md = tmp_path / "phase14_7.md"

    input_14_6.write_text(
        json.dumps(
            {
                "phase": "Phase 14-6",
                "status": "PASS",
                "phase14_6_audit_status": "PASS",
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
        "--input-14-6",
        str(input_14_6),
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
    assert report["final_confirmation_generated"] is False
    assert output_md.exists() is False
