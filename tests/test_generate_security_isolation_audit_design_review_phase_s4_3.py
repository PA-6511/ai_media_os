from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_isolation_audit_design_review_phase_s4_3 import (  # noqa: E402
    generate_security_isolation_audit_design_review_phase_s4_3,
)


CONFIG_PATH = ROOT / "config" / "security_isolation_audit_design_review_phase_s4_3.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_normal_audit_pass(tmp_path: Path) -> None:
    result = generate_security_isolation_audit_design_review_phase_s4_3(
        config_path=CONFIG_PATH,
        output_json_path=tmp_path / "audit.json",
        output_md_path=tmp_path / "audit.md",
    )
    assert result["audit_result"] == "PASS"
    assert result["final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["required_evidence_count"] == 6
    assert result["found_evidence_count"] == 6
    assert result["missing_evidence_count"] == 0
    assert result["phase_status"] == "DESIGN_ONLY"
    assert result["execution"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["audit_view_only"] is True
    assert result["simulation_only"] is True
    assert result["recommendation_only"] is True
    assert result["isolation_execution_allowed"] is False
    assert result["isolation_executed"] is False
    assert result["network_policy_applied"] is False
    assert result["container_stop_executed"] is False
    assert result["process_kill_executed"] is False
    assert result["firewall_applied"] is False
    assert result["scheduler_stop_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    assert result["state_change_executed"] is False


def test_missing_evidence_fail(tmp_path: Path) -> None:
    config = _load_json(CONFIG_PATH)
    config["required_evidence_files"]["phase_s4_2"].append("exchange/logs/not_found_s4_2_result.json")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    result = generate_security_isolation_audit_design_review_phase_s4_3(
        config_path=config_path,
        output_json_path=tmp_path / "audit.json",
        output_md_path=tmp_path / "audit.md",
    )
    assert result["audit_result"] == "FAIL"
    assert result["final_status"] == "ISOLATION_AUDIT_REVIEW_REQUIRED"


def test_abort_on_invalid_action_config(tmp_path: Path) -> None:
    config = _load_json(CONFIG_PATH)
    config["actions"]["auto_isolation_execute"] = True
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    result = generate_security_isolation_audit_design_review_phase_s4_3(
        config_path=config_path,
        output_json_path=tmp_path / "audit.json",
        output_md_path=tmp_path / "audit.md",
    )
    assert result["audit_result"] == "ABORT"
    assert result["final_status"] == "ABORT"
