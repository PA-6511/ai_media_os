from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_final_isolation_design_gate_phase_s4_4 import (  # noqa: E402
    generate_security_final_isolation_design_gate_phase_s4_4,
)


CONFIG_PATH = ROOT / "config" / "security_final_isolation_design_gate_phase_s4_4.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate_pass(tmp_path: Path) -> None:
    result = generate_security_final_isolation_design_gate_phase_s4_4(
        config_path=CONFIG_PATH,
        output_json_path=tmp_path / "gate.json",
        output_md_path=tmp_path / "gate.md",
    )
    assert result["gate_result"] == "PASS"
    assert result["final_status"] == "PASS_DESIGN_GATE_ONLY"
    assert result["production_status"] == "NO_GO"
    assert result["execution"] == "DRY_RUN"
    assert result["human_approval_required"] is True
    assert result["final_gate_only"] is True
    assert result["s4_completion_verified"] is True
    assert result["required_evidence_count"] == 8
    assert result["found_evidence_count"] == 8
    assert result["missing_evidence_count"] == 0
    assert result["isolation_design_ready"] is True
    assert result["future_execution_allowed"] is False
    assert result["isolation_execution_allowed"] is False
    assert result["isolation_executed"] is False
    assert result["network_policy_applied"] is False
    assert result["firewall_applied"] is False
    assert result["container_stop_executed"] is False
    assert result["process_kill_executed"] is False
    assert result["scheduler_stop_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    assert result["state_change_executed"] is False
    assert result["executor_action_allowed"] is False
    assert result["next_step"] == "pause_before_execution_or_prepare_s5_design_only"
    assert _load_json(tmp_path / "gate.json")["final_status"] == "PASS_DESIGN_GATE_ONLY"


def test_gate_abort_on_live_production(tmp_path: Path) -> None:
    config = _load_json(CONFIG_PATH)
    config["production_status"] = "GO"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    result = generate_security_final_isolation_design_gate_phase_s4_4(
        config_path=config_path,
        output_json_path=tmp_path / "gate.json",
        output_md_path=tmp_path / "gate.md",
    )
    assert result["gate_result"] == "ABORT"
    assert result["final_status"] == "ABORT"


def test_gate_fail_on_missing_evidence(tmp_path: Path) -> None:
    config = _load_json(CONFIG_PATH)
    config["required_evidence_files"]["phase_s4_completion"] = ["exchange/logs/missing.json"]
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    result = generate_security_final_isolation_design_gate_phase_s4_4(
        config_path=config_path,
        output_json_path=tmp_path / "gate.json",
        output_md_path=tmp_path / "gate.md",
    )
    assert result["gate_result"] == "FAIL"
