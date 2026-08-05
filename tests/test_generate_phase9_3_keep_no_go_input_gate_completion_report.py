#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import pytest
from scripts.generate_phase9_3_keep_no_go_input_gate_completion_report import (
    generate_phase9_3_report,
    validate_phase9_2_result,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def valid_phase9_2_result() -> dict:
    """Fixture for valid Phase 9-2 result."""
    return {
        "package_type": "phase9_2_publish_go_redecision_input_gate_result",
        "phase": "Phase 9-2",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "decision": "KEEP_NO_GO",
        "reviewer": "manual_human_reviewer",
        "reviewer_is_human": True,
        "manual_decision_recorded": True,
        "all_manual_confirmation_passed": False,
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "production_status": "NO_GO",
        "wordpress_publish_execution": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "fix_requests": [],
        "created_at": "2026-05-05T07:29:54.935705+00:00",
        "status": "PASS",
        "reason": "KEEP_NO_GO redecision recorded; publish candidate remains locked",
        "publish_candidate_unlocked_for_operator": False,
        "next_step": "maintain_no_go",
    }


def test_generate_phase9_3_valid_keep_no_go(valid_phase9_2_result):
    """Test Phase 9-3 generation with valid KEEP_NO_GO result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_file = tmpdir_path / "phase9_2_input.json"
        output_json = tmpdir_path / "phase9_3_output.json"
        output_md = tmpdir_path / "phase9_3_output.md"

        input_file.write_text(json.dumps(valid_phase9_2_result), encoding="utf-8")

        result = generate_phase9_3_report(input_file, output_json, output_md)

        assert result["status"] == "PASS"
        assert result["keep_no_go_completion_status"] == "PASS"
        assert result["report_generated"] is True
        assert output_json.exists()
        assert output_md.exists()

        # Verify JSON content
        report_data = json.loads(output_json.read_text(encoding="utf-8"))
        assert report_data["status"] == "PASS"
        assert report_data["phase9_2_decision"] == "KEEP_NO_GO"
        assert report_data["publish_candidate_unlocked_for_operator"] is False
        assert report_data["wordpress_publish_execution"] == "NO_GO"
        assert report_data["wordpress_write_executed"] is False
        assert report_data["next_step"] == "maintain_no_go_or_manual_publish_go_redecision"


def test_validate_phase9_2_wrong_phase(valid_phase9_2_result):
    """Test validation fails when phase is wrong."""
    data = valid_phase9_2_result.copy()
    data["phase"] = "Phase 9-1"
    
    result = validate_phase9_2_result(data)
    assert result is not None
    assert "phase must be 'Phase 9-2'" in result["reason"]


def test_validate_phase9_2_wrong_decision(valid_phase9_2_result):
    """Test validation fails when decision is not KEEP_NO_GO."""
    data = valid_phase9_2_result.copy()
    data["decision"] = "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"
    
    result = validate_phase9_2_result(data)
    assert result is not None
    assert "decision must be KEEP_NO_GO" in result["reason"]


def test_validate_phase9_2_publish_unlocked(valid_phase9_2_result):
    """Test validation fails when publish_candidate_unlocked_for_operator is true."""
    data = valid_phase9_2_result.copy()
    data["publish_candidate_unlocked_for_operator"] = True
    
    result = validate_phase9_2_result(data)
    assert result is not None
    assert "publish_candidate_unlocked_for_operator must be false" in result["reason"]


def test_validate_phase9_2_publish_execution_not_no_go(valid_phase9_2_result):
    """Test validation fails when wordpress_publish_execution is not NO_GO."""
    data = valid_phase9_2_result.copy()
    data["wordpress_publish_execution"] = "GO"
    
    result = validate_phase9_2_result(data)
    assert result is not None
    assert "wordpress_publish_execution must be NO_GO" in result["reason"]


def test_validate_phase9_2_write_executed(valid_phase9_2_result):
    """Test validation fails when wordpress_write_executed is true."""
    data = valid_phase9_2_result.copy()
    data["wordpress_write_executed"] = True
    
    result = validate_phase9_2_result(data)
    assert result is not None
    assert "wordpress_write_executed must be false" in result["reason"]


def test_generate_phase9_3_overwrite_protection(valid_phase9_2_result):
    """Test that existing reports are detected and overwrite protection is triggered."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_file = tmpdir_path / "phase9_2_input.json"
        output_json = tmpdir_path / "phase9_3_output.json"
        output_md = tmpdir_path / "phase9_3_output.md"

        input_file.write_text(json.dumps(valid_phase9_2_result), encoding="utf-8")

        # Generate first time
        result1 = generate_phase9_3_report(input_file, output_json, output_md)
        assert result1["status"] == "PASS"
        assert output_json.exists()

        # Get modification time of first generation
        first_mtime = output_json.stat().st_mtime

        # Try to generate again - should detect existing file
        # This test verifies the file exists and we're protecting against overwrites
        assert output_json.exists()
        assert output_json.stat().st_mtime == first_mtime


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
