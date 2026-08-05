from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_cross_phase_audit_view_phase_s3_2 import (  # noqa: E402
    generate_security_cross_phase_audit_view_phase_s3_2,
)


CONFIG_PATH = ROOT / "config" / "security_cross_phase_audit_view_phase_s3_2.json"


def test_normal_audit_pass(tmp_path: Path) -> None:
    result = generate_security_cross_phase_audit_view_phase_s3_2(
        config_path=CONFIG_PATH,
        output_json_path=tmp_path / "audit.json",
        output_md_path=tmp_path / "audit.md",
    )
    assert result["audit_result"] == "PASS"
    assert result["final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["required_evidence_count"] > 0
    assert result["found_evidence_count"] == result["required_evidence_count"]
    assert result["missing_evidence_count"] == 0
    assert result["audited_phases"] == ["PHASE_S0", "PHASE_S1", "PHASE_S2", "PHASE_S3", "PHASE_S3_1"]
    assert result["production_status"] == "NO_GO"
    assert result["execution"] == "DRY_RUN"
    assert result["audit_view_only"] is True
    assert result["recommendation_only"] is True
    assert result["executor_action_allowed"] is False
    assert result["s3_1_replay_summary"]["event_count"] == 5
    assert result["s3_1_replay_summary"]["matched_expected_count"] == 5
    assert result["s3_1_replay_summary"]["mismatched_expected_count"] == 0
    assert result["s3_1_replay_summary"]["freeze_recommendation_detected"] is True
    assert result["s3_1_replay_summary"]["human_review_recommendation_detected"] is True
    assert result["freeze_executed"] is False
    assert result["revoke_executed"] is False
    assert result["isolation_executed"] is False
    assert result["process_kill_executed"] is False
    assert result["scheduler_stop_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    assert result["state_change_executed"] is False
    assert result["next_step"] == "prepare_phase_s4_block_ai_isolation_design"


def test_missing_evidence_fail(tmp_path: Path) -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["required_evidence_files"]["phase_s0"] = ["exchange/logs/missing_file.json"]
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    result = generate_security_cross_phase_audit_view_phase_s3_2(
        config_path=config_path,
        output_json_path=tmp_path / "audit.json",
        output_md_path=tmp_path / "audit.md",
    )
    assert result["audit_result"] == "FAIL"
    assert result["final_status"] == "AUDIT_REVIEW_REQUIRED"


def test_abort_on_live_or_go(tmp_path: Path) -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["required_invariants"]["production_status"] = "GO"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    result = generate_security_cross_phase_audit_view_phase_s3_2(
        config_path=config_path,
        output_json_path=tmp_path / "audit.json",
        output_md_path=tmp_path / "audit.md",
    )
    assert result["audit_result"] == "ABORT"
    assert result["final_status"] == "ABORT"
