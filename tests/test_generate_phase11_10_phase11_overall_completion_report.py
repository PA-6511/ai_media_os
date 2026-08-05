import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase11_10_phase11_overall_completion_report.py"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_phase11_10_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "11-1": "phase11_1_publish_redecision_route_restart_design_report.json",
        "11-2": "phase11_2_pre_production_audit_design_report.json",
        "11-3": "phase11_3_single_publish_final_execution_plan_report.json",
        "11-4": "phase11_4_pre_publish_final_no_go_or_go_judgment_design_report.json",
        "11-5": "phase11_5_publish_command_final_dry_run_confirmation_report.json",
        "11-6": "phase11_6_execute_live_authorization_gate_report.json",
        "11-7": "phase11_7_pre_execution_final_freeze_release_judgment_report.json",
        "11-8": "phase11_8_post_execution_evidence_and_relock_final_confirmation_report.json",
        "11-9": "phase11_9_pre_publish_no_go_maintenance_report.json",
    }

    for phase, filename in files.items():
        _write(
            logs / filename,
            {
                "phase": f"Phase {phase}",
                "status": "PASS",
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "wordpress_draft_id": 110,
                "target_draft_status": "draft",
            },
        )

    # Add required per-phase extra status keys.
    _write(
        logs / files["11-1"],
        {
            **json.loads((logs / files["11-1"]).read_text(encoding="utf-8")),
            "phase11_1_design_status": "PASS",
        },
    )
    _write(
        logs / files["11-2"],
        {
            **json.loads((logs / files["11-2"]).read_text(encoding="utf-8")),
            "phase11_2_audit_design_status": "PASS",
        },
    )
    _write(
        logs / files["11-3"],
        {
            **json.loads((logs / files["11-3"]).read_text(encoding="utf-8")),
            "phase11_3_plan_status": "PASS",
        },
    )
    _write(
        logs / files["11-4"],
        {
            **json.loads((logs / files["11-4"]).read_text(encoding="utf-8")),
            "phase11_4_judgment_design_status": "PASS",
        },
    )
    _write(
        logs / files["11-5"],
        {
            **json.loads((logs / files["11-5"]).read_text(encoding="utf-8")),
            "phase11_5_dry_run_status": "PASS",
        },
    )
    _write(
        logs / files["11-6"],
        {
            **json.loads((logs / files["11-6"]).read_text(encoding="utf-8")),
            "phase11_6_gate_status": "PASS",
        },
    )
    _write(
        logs / files["11-7"],
        {
            **json.loads((logs / files["11-7"]).read_text(encoding="utf-8")),
            "phase11_7_judgment_status": "PASS",
            "phase11_7_final_judgment": "KEEP_NO_GO",
        },
    )
    _write(
        logs / files["11-8"],
        {
            **json.loads((logs / files["11-8"]).read_text(encoding="utf-8")),
            "phase11_8_final_confirmation_status": "PASS",
        },
    )
    _write(
        logs / files["11-9"],
        {
            **json.loads((logs / files["11-9"]).read_text(encoding="utf-8")),
            "phase11_9_maintenance_status": "PASS",
        },
    )

    output_json = logs / "phase11_10_phase11_overall_completion_report.json"
    output_md = logs / "phase11_10_phase11_overall_completion_report.md"

    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logs-dir",
            str(logs),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert res.returncode == 0, res.stdout + res.stderr
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "PASS"
    assert stdout["phase11_overall_status"] == "PASS"

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 11-10"
    assert report["status"] == "PASS"
    assert report["phase11_overall_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["target_draft_status"] == "draft"
    assert output_md.exists()


def test_generate_phase11_10_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"
    files = {
        "11-1": "phase11_1_publish_redecision_route_restart_design_report.json",
        "11-2": "phase11_2_pre_production_audit_design_report.json",
        "11-3": "phase11_3_single_publish_final_execution_plan_report.json",
        "11-4": "phase11_4_pre_publish_final_no_go_or_go_judgment_design_report.json",
        "11-5": "phase11_5_publish_command_final_dry_run_confirmation_report.json",
        "11-6": "phase11_6_execute_live_authorization_gate_report.json",
        "11-7": "phase11_7_pre_execution_final_freeze_release_judgment_report.json",
        "11-8": "phase11_8_post_execution_evidence_and_relock_final_confirmation_report.json",
        "11-9": "phase11_9_pre_publish_no_go_maintenance_report.json",
    }

    for phase, filename in files.items():
        _write(
            logs / filename,
            {
                "phase": f"Phase {phase}",
                "status": "PASS",
                "current_decision": "KEEP_NO_GO",
                "publish_candidate_unlocked_for_operator": False,
                "wordpress_publish_execution": "NO_GO",
                "wordpress_write_executed": False,
                "production_status": "NO_GO",
                "wordpress_draft_id": 110,
                "target_draft_status": "draft",
            },
        )

    bad = logs / files["11-9"]
    bad_payload = json.loads(bad.read_text(encoding="utf-8"))
    bad_payload["publish_candidate_unlocked_for_operator"] = True
    _write(bad, bad_payload)

    output_json = logs / "phase11_10_phase11_overall_completion_report.json"
    output_md = logs / "phase11_10_phase11_overall_completion_report.md"

    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logs-dir",
            str(logs),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert res.returncode == 1
    stdout = json.loads(res.stdout)
    assert stdout["status"] == "ABORT"
    assert "publish_candidate_unlocked_for_operator" in stdout["reason"]

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "ABORT"
    assert report["overall_report_generated"] is False
    assert output_md.exists() is False
