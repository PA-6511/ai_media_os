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
from scripts.generate_security_phase_s4_3_overall_result import (  # noqa: E402
    generate_security_phase_s4_3_overall_result,
)


def _build_audit(tmp_path: Path, audit_result: str) -> Path:
    result = generate_security_isolation_audit_design_review_phase_s4_3(
        output_json_path=tmp_path / "audit.json",
        output_md_path=tmp_path / "audit.md",
    )
    result["audit_result"] = audit_result
    if audit_result != "PASS":
        result["missing_evidence_count"] = 1
    (tmp_path / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp_path / "audit.json"


def test_overall_pass_dry_run_only(tmp_path: Path) -> None:
    audit_path = _build_audit(tmp_path, "PASS")
    result = generate_security_phase_s4_3_overall_result(
        audit_result_path=audit_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "PASS_DRY_RUN_ONLY"
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


def test_overall_review_required(tmp_path: Path) -> None:
    audit_path = _build_audit(tmp_path, "FAIL")
    result = generate_security_phase_s4_3_overall_result(
        audit_result_path=audit_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ISOLATION_AUDIT_REVIEW_REQUIRED"


def test_overall_abort(tmp_path: Path) -> None:
    audit_path = _build_audit(tmp_path, "ABORT")
    result = generate_security_phase_s4_3_overall_result(
        audit_result_path=audit_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ABORT"
