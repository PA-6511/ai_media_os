import json

from phase65.reporting.phase65_completion_report import write_phase65_completion_report


def _valid_payload() -> dict:
    return {
        "completion_status": "PASS",
        "phase_range": "15-64",
        "phases_passed_count": 50,
        "total_phases_in_scope": 50,
        "pass_evidence_summary": {
            "phase64_unit_tests": "18 passed",
            "full_regression": "1218 passed / 0 failed",
            "warnings": "1 warning",
            "subtests": "8 subtests passed",
        },
        "safety_boundaries": {
            "dry_run_fixed": True,
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
            "max_files_to_execute": 1,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute_guards": True,
        },
        "unreleased_items": [
            "production_reflection",
            "merge_automation",
            "delete_operations",
            "live_execution",
        ],
        "next_stage_go_no_go_conditions": {
            "go_requires": [
                "manual_gate_approval",
                "policy_consistency_check",
                "evidence_integrity_check",
            ],
            "no_go_if": [
                "any_execute_flag_true",
                "policy_mismatch",
                "missing_evidence",
            ],
        },
        "recommended_next_step": "prepare_phase66_go_no_go_readiness_review",
    }


def test_write_report_fails_when_missing_key(tmp_path) -> None:
    payload = _valid_payload()
    payload.pop("recommended_next_step")
    out = tmp_path / "phase65.json"
    result = write_phase65_completion_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "missing keys" in result["reason"]


def test_write_report_fails_when_safety_is_not_dict(tmp_path) -> None:
    payload = _valid_payload()
    payload["safety_boundaries"] = []
    out = tmp_path / "phase65.json"
    result = write_phase65_completion_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "must be a dict" in result["reason"]


def test_write_report_fails_when_can_execute_true(tmp_path) -> None:
    payload = _valid_payload()
    payload["safety_boundaries"]["can_execute"] = True
    out = tmp_path / "phase65.json"
    result = write_phase65_completion_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "safety_boundaries.can_execute must be False" in result["reason"]


def test_write_report_fails_when_execute_allowed_true(tmp_path) -> None:
    payload = _valid_payload()
    payload["safety_boundaries"]["execute_allowed"] = True
    out = tmp_path / "phase65.json"
    result = write_phase65_completion_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "safety_boundaries.execute_allowed must be False" in result["reason"]


def test_write_report_fails_when_max_files_invalid(tmp_path) -> None:
    payload = _valid_payload()
    payload["safety_boundaries"]["max_files_to_execute"] = 2
    out = tmp_path / "phase65.json"
    result = write_phase65_completion_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "safety_boundaries.max_files_to_execute must be 1" in result["reason"]


def test_write_report_fails_when_does_not_execute_guards_false(tmp_path) -> None:
    payload = _valid_payload()
    payload["safety_boundaries"]["does_not_execute_guards"] = False
    out = tmp_path / "phase65.json"
    result = write_phase65_completion_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "safety_boundaries.does_not_execute_guards must be True" in result["reason"]


def test_write_report_pass_and_persist(tmp_path) -> None:
    out = tmp_path / "phase65.json"
    result = write_phase65_completion_report(_valid_payload(), str(out))
    assert result["status"] == "PASS"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phase"] == "65"
    assert data["report_type"] == "manual_dry_run_pre_execution_design_completion_report"
    assert data["scope"] == "phase15_to_phase64"
    assert data["completion_status"] == "PASS"
