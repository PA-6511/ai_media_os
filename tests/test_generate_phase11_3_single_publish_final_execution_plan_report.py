import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase11_3_single_publish_final_execution_plan_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_generate_phase11_3_report_pass(tmp_path: Path):
    input_11_2 = tmp_path / "phase11_2.json"
    output_json = tmp_path / "phase11_3.json"
    output_md = tmp_path / "phase11_3.md"

    input_11_2.write_text(
        json.dumps(
            {
                "phase": "Phase 11-2",
                "status": "PASS",
                "phase11_2_audit_design_status": "PASS",
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
        "--input-11-2",
        str(input_11_2),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )

    assert res.returncode == 0, res.stdout + res.stderr
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "PASS"
    assert stdout["phase11_3_plan_status"] == "PASS"

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 11-3"
    assert report["status"] == "PASS"
    assert report["phase11_3_plan_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["next_step"] == "phase11_4_pre_publish_final_no_go_or_go_judgment_design"
    assert output_md.exists()


def test_generate_phase11_3_report_abort_on_invalid_input(tmp_path: Path):
    input_11_2 = tmp_path / "phase11_2.json"
    output_json = tmp_path / "phase11_3.json"
    output_md = tmp_path / "phase11_3.md"

    input_11_2.write_text(
        json.dumps(
            {
                "phase": "Phase 11-2",
                "status": "PASS",
                "phase11_2_audit_design_status": "PASS",
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
        "--input-11-2",
        str(input_11_2),
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
    assert report["status"] == "ABORT"
    assert report["plan_report_generated"] is False
    assert output_md.exists() is False
