from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_block_ai_isolation_design_phase_s4 import (  # noqa: E402
    validate_security_block_ai_isolation_design_phase_s4,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_bundle(tmp_path: Path) -> dict[str, Path]:
    mapping = {
        "policy_path": ROOT / "config" / "security_block_ai_isolation_policy_phase_s4.json",
        "risk_classification_path": ROOT / "config" / "security_block_ai_risk_classification_phase_s4.json",
        "communication_matrix_path": ROOT / "config" / "security_inter_block_communication_matrix_phase_s4.json",
        "capability_boundary_path": ROOT / "config" / "security_capability_boundary_policy_phase_s4.json",
        "recommendation_rules_path": ROOT / "config" / "security_isolation_recommendation_rules_phase_s4.json",
        "reconnect_conditions_path": ROOT / "config" / "security_isolation_reconnect_conditions_phase_s4.json",
        "s3_2_audit_path": ROOT / "exchange" / "logs" / "security_cross_phase_audit_view_phase_s3_2_result.json",
    }
    result: dict[str, Path] = {}
    for key, src in mapping.items():
        dst = tmp_path / src.name
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        result[key] = dst
    return result


def run_validator(tmp_path: Path, mutate: dict[str, tuple[str, object]] | None = None) -> dict:
    paths = write_bundle(tmp_path)
    mutate = mutate or {}
    for key, (field, value) in mutate.items():
        payload = load_json(paths[key])
        payload[field] = value
        paths[key].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return validate_security_block_ai_isolation_design_phase_s4(
        policy_path=paths["policy_path"],
        risk_classification_path=paths["risk_classification_path"],
        communication_matrix_path=paths["communication_matrix_path"],
        capability_boundary_path=paths["capability_boundary_path"],
        recommendation_rules_path=paths["recommendation_rules_path"],
        reconnect_conditions_path=paths["reconnect_conditions_path"],
        s3_2_audit_path=paths["s3_2_audit_path"],
        output_json_path=tmp_path / "validation.json",
        output_md_path=tmp_path / "validation.md",
    )


def test_normal_pass(tmp_path: Path) -> None:
    result = run_validator(tmp_path)
    assert result["validator_result"] == "PASS"
    assert result["final_status"] == "PASS_DESIGN_ONLY"
    assert result["phase_status"] == "DESIGN_ONLY"
    assert result["execution"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["isolation_design_only"] is True
    assert result["isolation_execution_allowed"] is False
    assert result["isolation_executed"] is False
    assert result["executor_action_allowed"] is False
    assert result["network_policy_apply_allowed"] is False
    assert result["network_policy_applied"] is False
    assert result["container_stop_allowed"] is False
    assert result["container_stop_executed"] is False
    assert result["process_kill_allowed"] is False
    assert result["process_kill_executed"] is False
    assert result["firewall_apply_allowed"] is False
    assert result["firewall_applied"] is False
    assert result["scheduler_stop_allowed"] is False
    assert result["scheduler_stop_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    assert result["state_change_executed"] is False
    assert result["s3_2_audit_verified"] is True
    assert result["next_step"] == "phase_s4_1_isolation_policy_dry_run_validation"


def test_missing_config_fail(tmp_path: Path) -> None:
    paths = write_bundle(tmp_path)
    paths["policy_path"].unlink()
    result = validate_security_block_ai_isolation_design_phase_s4(
        policy_path=paths["policy_path"],
        risk_classification_path=paths["risk_classification_path"],
        communication_matrix_path=paths["communication_matrix_path"],
        capability_boundary_path=paths["capability_boundary_path"],
        recommendation_rules_path=paths["recommendation_rules_path"],
        reconnect_conditions_path=paths["reconnect_conditions_path"],
        s3_2_audit_path=paths["s3_2_audit_path"],
        output_json_path=tmp_path / "validation.json",
        output_md_path=tmp_path / "validation.md",
    )
    assert result["validator_result"] == "FAIL"


def test_execution_live_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("execution", "LIVE")})
    assert result["validator_result"] == "ABORT"


def test_production_go_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("production_status", "GO")})
    assert result["validator_result"] == "ABORT"


def test_isolation_execution_allowed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("isolation_execution_allowed", True)})
    assert result["validator_result"] == "ABORT"


def test_isolation_executed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("isolation_executed", True)})
    assert result["validator_result"] == "ABORT"


def test_network_policy_apply_allowed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("network_policy_apply_allowed", True)})
    assert result["validator_result"] == "ABORT"


def test_network_policy_applied_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("network_policy_applied", True)})
    assert result["validator_result"] == "ABORT"


def test_container_stop_executed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("container_stop_executed", True)})
    assert result["validator_result"] == "ABORT"


def test_process_kill_executed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("process_kill_executed", True)})
    assert result["validator_result"] == "ABORT"


def test_firewall_applied_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("firewall_applied", True)})
    assert result["validator_result"] == "ABORT"


def test_scheduler_stop_executed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("scheduler_stop_executed", True)})
    assert result["validator_result"] == "ABORT"


def test_wordpress_write_executed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("wordpress_write_executed", True)})
    assert result["validator_result"] == "ABORT"


def test_external_api_call_executed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("external_api_call_executed", True)})
    assert result["validator_result"] == "ABORT"


def test_state_change_executed_true_aborts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"policy_path": ("state_change_executed", True)})
    assert result["validator_result"] == "ABORT"


def test_communication_default_not_deny_fails(tmp_path: Path) -> None:
    result = run_validator(tmp_path, {"communication_matrix_path": ("communication_default", "ALLOW")})
    assert result["validator_result"] == "FAIL"


def test_unknown_block_default_deny_missing_fails(tmp_path: Path) -> None:
    paths = write_bundle(tmp_path)
    payload = load_json(paths["communication_matrix_path"])
    payload["blocked_routes"] = [route for route in payload["blocked_routes"] if route["from"] != "unknown_block_ai"]
    paths["communication_matrix_path"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result = validate_security_block_ai_isolation_design_phase_s4(
        policy_path=paths["policy_path"],
        risk_classification_path=paths["risk_classification_path"],
        communication_matrix_path=paths["communication_matrix_path"],
        capability_boundary_path=paths["capability_boundary_path"],
        recommendation_rules_path=paths["recommendation_rules_path"],
        reconnect_conditions_path=paths["reconnect_conditions_path"],
        s3_2_audit_path=paths["s3_2_audit_path"],
        output_json_path=tmp_path / "validation.json",
        output_md_path=tmp_path / "validation.md",
    )
    assert result["validator_result"] == "FAIL"


def test_restricted_ai_production_core_block_missing_fails(tmp_path: Path) -> None:
    paths = write_bundle(tmp_path)
    payload = load_json(paths["communication_matrix_path"])
    payload["blocked_routes"] = [route for route in payload["blocked_routes"] if route["from"] != "adult_or_risky_experiment_ai"]
    paths["communication_matrix_path"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result = validate_security_block_ai_isolation_design_phase_s4(
        policy_path=paths["policy_path"],
        risk_classification_path=paths["risk_classification_path"],
        communication_matrix_path=paths["communication_matrix_path"],
        capability_boundary_path=paths["capability_boundary_path"],
        recommendation_rules_path=paths["recommendation_rules_path"],
        reconnect_conditions_path=paths["reconnect_conditions_path"],
        s3_2_audit_path=paths["s3_2_audit_path"],
        output_json_path=tmp_path / "validation.json",
        output_md_path=tmp_path / "validation.md",
    )
    assert result["validator_result"] == "FAIL"


def test_s3_2_audit_result_not_pass_fails(tmp_path: Path) -> None:
    paths = write_bundle(tmp_path)
    payload = load_json(paths["s3_2_audit_path"])
    payload["audit_result"] = "WARN"
    paths["s3_2_audit_path"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result = validate_security_block_ai_isolation_design_phase_s4(
        policy_path=paths["policy_path"],
        risk_classification_path=paths["risk_classification_path"],
        communication_matrix_path=paths["communication_matrix_path"],
        capability_boundary_path=paths["capability_boundary_path"],
        recommendation_rules_path=paths["recommendation_rules_path"],
        reconnect_conditions_path=paths["reconnect_conditions_path"],
        s3_2_audit_path=paths["s3_2_audit_path"],
        output_json_path=tmp_path / "validation.json",
        output_md_path=tmp_path / "validation.md",
    )
    assert result["validator_result"] == "FAIL"
