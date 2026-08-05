from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_phase_s4_overall_completion_report import (  # noqa: E402
    generate_security_phase_s4_overall_completion_report,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_overall_completion_pass(tmp_path: Path) -> None:
    result = generate_security_phase_s4_overall_completion_report(
        output_json_path=tmp_path / "report.json",
        output_md_path=tmp_path / "report.md",
    )
    assert result["final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["phase_status"] == "DESIGN_ONLY"
    assert result["execution"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["summary"]["phase_s4_validation_result"] == "PASS_DESIGN_ONLY"
    assert result["summary"]["phase_s4_overall_result"] == "PASS_DESIGN_ONLY"
    assert result["summary"]["phase_s4_1_final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["summary"]["phase_s4_2_final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["summary"]["phase_s4_3_final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["summary"]["phase_s4_2_scenario_count"] == 7
    assert result["summary"]["phase_s4_3_found_evidence_count"] == 6
    assert result["summary"]["phase_s4_3_missing_evidence_count"] == 0
    assert result["safety_flags"]["isolation_execution_allowed"] is False
    assert result["safety_flags"]["isolation_executed"] is False
    assert result["safety_flags"]["network_policy_applied"] is False
    assert result["safety_flags"]["container_stop_executed"] is False
    assert result["safety_flags"]["process_kill_executed"] is False
    assert result["safety_flags"]["firewall_applied"] is False
    assert result["safety_flags"]["scheduler_stop_executed"] is False
    assert result["safety_flags"]["wordpress_write_executed"] is False
    assert result["safety_flags"]["external_api_call_executed"] is False
    assert result["safety_flags"]["state_change_executed"] is False
    assert Path(tmp_path / "report.json").exists()
    assert Path(tmp_path / "report.md").exists()

    report = _load_json(tmp_path / "report.json")
    assert report["final_status"] == "PASS_DRY_RUN_ONLY"
    assert report["decision"]["production_release"] == "NOT_ALLOWED"
    assert report["decision"]["next_step"] == "Phase S-4.4 final isolation design gate or keep NO_GO"


def test_overall_completion_review_required_on_status_mismatch(tmp_path: Path) -> None:
    source_files = {
        "phase_s4_validation_result": ROOT / "exchange" / "logs" / "security_block_ai_isolation_design_phase_s4_validation_result.json",
        "phase_s4_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.json",
        "phase_s4_1_replay_result": ROOT / "exchange" / "logs" / "security_isolation_policy_dry_run_phase_s4_1_result.json",
        "phase_s4_1_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.json",
        "phase_s4_2_replay_result": ROOT / "exchange" / "logs" / "security_isolation_event_simulation_phase_s4_2_result.json",
        "phase_s4_2_overall_result": tmp_path / "phase_s4_2_overall_result.json",
        "phase_s4_3_audit_result": ROOT / "exchange" / "logs" / "security_isolation_audit_design_review_phase_s4_3_result.json",
        "phase_s4_3_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_3_overall_result.json",
    }
    broken_source = _load_json(ROOT / "exchange" / "logs" / "security_phase_s4_2_overall_result.json")
    broken_source["final_status"] = "BROKEN"
    source_files["phase_s4_2_overall_result"].write_text(json.dumps(broken_source, ensure_ascii=False, indent=2), encoding="utf-8")

    result = generate_security_phase_s4_overall_completion_report(
        source_files=source_files,
        output_json_path=tmp_path / "report2.json",
        output_md_path=tmp_path / "report2.md",
    )
    assert result["final_status"] == "S4_COMPLETION_REVIEW_REQUIRED"


def test_overall_completion_fail_if_source_missing(tmp_path: Path) -> None:
    result = generate_security_phase_s4_overall_completion_report(
        source_files={
            "phase_s4_validation_result": ROOT / "exchange" / "logs" / "security_block_ai_isolation_design_phase_s4_validation_result.json",
            "phase_s4_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.json",
            "phase_s4_1_replay_result": ROOT / "exchange" / "logs" / "security_isolation_policy_dry_run_phase_s4_1_result.json",
            "phase_s4_1_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.json",
            "phase_s4_2_replay_result": ROOT / "exchange" / "logs" / "security_isolation_event_simulation_phase_s4_2_result.json",
            "phase_s4_2_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_2_overall_result.json",
            "phase_s4_3_audit_result": ROOT / "exchange" / "logs" / "missing.json",
            "phase_s4_3_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_3_overall_result.json",
        },
        output_json_path=tmp_path / "report.json",
        output_md_path=tmp_path / "report.md",
    )
    assert result["final_status"] == "S4_COMPLETION_REVIEW_REQUIRED"
