import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase10_16_phase10_overall_completion_report.py"


def run_script(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_phase_payload(phase_label: str) -> dict:
    return {
        "phase": phase_label,
        "status": "PASS",
    }


def test_generate_phase10_16_report_pass(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"

    _write(
        logs
        / "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report.json",
        _base_phase_payload("Phase 10-1"),
    )
    _write(
        logs / "phase10_2_manual_redecision_input_and_final_lock_validation_design_report.json",
        _base_phase_payload("Phase 10-2"),
    )
    _write(
        logs / "phase10_3_manual_redecision_record_and_final_lock_gate_design_report.json",
        _base_phase_payload("Phase 10-3"),
    )
    _write(
        logs / "phase10_4_manual_unlock_candidate_validation_design_report.json",
        _base_phase_payload("Phase 10-4"),
    )
    _write(
        logs / "phase10_5_manual_unlock_candidate_execution_guard_design_report.json",
        _base_phase_payload("Phase 10-5"),
    )
    _write(
        logs / "phase10_6_manual_publish_pre_execution_confirmation_design_report.json",
        _base_phase_payload("Phase 10-6"),
    )
    _write(
        logs / "phase10_7_manual_publish_immediate_pre_execution_go_freeze_decision_design_report.json",
        _base_phase_payload("Phase 10-7"),
    )
    _write(
        logs / "phase10_8_manual_publish_command_dry_run_payload_validation_report.json",
        _base_phase_payload("Phase 10-8"),
    )

    no_go_payload = {
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
    }

    _write(
        logs / "phase10_9_single_publish_manual_execution_script_implementation_report.json",
        {"phase": "Phase 10-9", **no_go_payload},
    )
    _write(
        logs / "phase10_10_default_stop_guard_confirmation_report.json",
        {"phase": "Phase 10-10", **no_go_payload},
    )
    _write(
        logs / "phase10_11_post_execution_evidence_and_relock_confirmation_design_report.json",
        {"phase": "Phase 10-11", **no_go_payload},
    )
    _write(
        logs / "phase10_12_manual_live_execution_readiness_review_report.json",
        {"phase": "Phase 10-12", **no_go_payload},
    )
    _write(
        logs / "phase10_13_execute_live_final_human_authorization_gate_report.json",
        {"phase": "Phase 10-13", **no_go_payload},
    )
    _write(
        logs / "phase10_14_pre_execution_final_freeze_release_judgment_report.json",
        {
            "phase": "Phase 10-14",
            "phase10_14_final_judgment": "KEEP_NO_GO",
            **no_go_payload,
        },
    )
    _write(
        logs / "phase10_15_pre_publish_no_go_maintenance_completion_report.json",
        {
            "phase": "Phase 10-15",
            "phase10_14_final_judgment": "KEEP_NO_GO",
            **no_go_payload,
        },
    )

    output_json = logs / "phase10_16_phase10_overall_completion_report.json"
    output_md = logs / "phase10_16_phase10_overall_completion_report.md"

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
    assert stdout["phase10_overall_status"] == "PASS"

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["phase"] == "Phase 10-16"
    assert report["status"] == "PASS"
    assert report["phase10_overall_status"] == "PASS"
    assert report["phase_statuses"]["10-15"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["production_status"] == "NO_GO"
    assert report["target_draft_status"] == "draft"
    assert output_md.exists()


def test_generate_phase10_16_report_abort_when_no_go_is_broken(tmp_path: Path):
    logs = tmp_path / "exchange" / "logs"

    for idx in range(1, 16):
        key = f"10-{idx}"
        if key == "10-1":
            filename = "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report.json"
        elif key == "10-2":
            filename = "phase10_2_manual_redecision_input_and_final_lock_validation_design_report.json"
        elif key == "10-3":
            filename = "phase10_3_manual_redecision_record_and_final_lock_gate_design_report.json"
        elif key == "10-4":
            filename = "phase10_4_manual_unlock_candidate_validation_design_report.json"
        elif key == "10-5":
            filename = "phase10_5_manual_unlock_candidate_execution_guard_design_report.json"
        elif key == "10-6":
            filename = "phase10_6_manual_publish_pre_execution_confirmation_design_report.json"
        elif key == "10-7":
            filename = "phase10_7_manual_publish_immediate_pre_execution_go_freeze_decision_design_report.json"
        elif key == "10-8":
            filename = "phase10_8_manual_publish_command_dry_run_payload_validation_report.json"
        elif key == "10-9":
            filename = "phase10_9_single_publish_manual_execution_script_implementation_report.json"
        elif key == "10-10":
            filename = "phase10_10_default_stop_guard_confirmation_report.json"
        elif key == "10-11":
            filename = "phase10_11_post_execution_evidence_and_relock_confirmation_design_report.json"
        elif key == "10-12":
            filename = "phase10_12_manual_live_execution_readiness_review_report.json"
        elif key == "10-13":
            filename = "phase10_13_execute_live_final_human_authorization_gate_report.json"
        elif key == "10-14":
            filename = "phase10_14_pre_execution_final_freeze_release_judgment_report.json"
        else:
            filename = "phase10_15_pre_publish_no_go_maintenance_completion_report.json"

        payload = {"phase": f"Phase {key}", "status": "PASS"}
        if key in {"10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"}:
            payload.update(
                {
                    "current_decision": "KEEP_NO_GO",
                    "publish_candidate_unlocked_for_operator": False,
                    "wordpress_publish_execution": "NO_GO",
                    "wordpress_write_executed": False,
                    "production_status": "NO_GO",
                    "wordpress_draft_id": 110,
                    "target_draft_status": "draft",
                }
            )
        _write(logs / filename, payload)

    # Break NO_GO condition intentionally.
    bad = logs / "phase10_15_pre_publish_no_go_maintenance_completion_report.json"
    bad_payload = json.loads(bad.read_text(encoding="utf-8"))
    bad_payload["publish_candidate_unlocked_for_operator"] = True
    _write(bad, bad_payload)

    output_json = logs / "phase10_16_phase10_overall_completion_report.json"
    output_md = logs / "phase10_16_phase10_overall_completion_report.md"

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
