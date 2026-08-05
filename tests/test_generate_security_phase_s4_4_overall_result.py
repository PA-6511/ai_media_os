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
from scripts.generate_security_phase_s4_4_overall_result import (  # noqa: E402
    generate_security_phase_s4_4_overall_result,
)


def _build_gate(tmp_path: Path, gate_result: str) -> Path:
    result = generate_security_final_isolation_design_gate_phase_s4_4(
        output_json_path=tmp_path / "gate.json",
        output_md_path=tmp_path / "gate.md",
    )
    result["gate_result"] = gate_result
    if gate_result != "PASS":
        result["s4_completion_verified"] = False
    (tmp_path / "gate.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp_path / "gate.json"


def test_overall_pass_design_gate_only(tmp_path: Path) -> None:
    gate_path = _build_gate(tmp_path, "PASS")
    result = generate_security_phase_s4_4_overall_result(
        gate_result_path=gate_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "PASS_DESIGN_GATE_ONLY"
    assert result["gate_result"] == "PASS"
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


def test_overall_review_required_on_gate_failure(tmp_path: Path) -> None:
    gate_path = _build_gate(tmp_path, "FAIL")
    result = generate_security_phase_s4_4_overall_result(
        gate_result_path=gate_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "DESIGN_GATE_REVIEW_REQUIRED"


def test_overall_abort(tmp_path: Path) -> None:
    gate_path = _build_gate(tmp_path, "ABORT")
    result = generate_security_phase_s4_4_overall_result(
        gate_result_path=gate_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ABORT"
