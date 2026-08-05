from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_phase_s4_overall_result import (  # noqa: E402
    generate_security_phase_s4_overall_result,
)
from scripts.validate_security_block_ai_isolation_design_phase_s4 import (  # noqa: E402
    validate_security_block_ai_isolation_design_phase_s4,
)


def build_validation_result(tmp_path: Path, validator_result: str) -> Path:
    validation = validate_security_block_ai_isolation_design_phase_s4(
        output_json_path=tmp_path / "validation.json",
        output_md_path=tmp_path / "validation.md",
    )
    validation["validator_result"] = validator_result
    validation["final_status"] = {
        "PASS": "PASS_DESIGN_ONLY",
        "WARN": "ISOLATION_DESIGN_REVIEW_REQUIRED",
        "FAIL": "ISOLATION_DESIGN_REVIEW_REQUIRED",
        "ABORT": "ABORT",
    }[validator_result]
    (tmp_path / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp_path / "validation.json"


def test_overall_result_pass(tmp_path: Path) -> None:
    validation_path = build_validation_result(tmp_path, "PASS")
    result = generate_security_phase_s4_overall_result(
        validation_result_path=validation_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "PASS_DESIGN_ONLY"
    assert result["execution"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["phase_status"] == "DESIGN_ONLY"
    assert result["isolation_design_only"] is True
    assert result["isolation_execution_allowed"] is False
    assert result["isolation_executed"] is False
    assert result["executor_action_allowed"] is False
    assert result["s3_2_audit_verified"] is True
    assert result["next_step"] == "phase_s4_1_isolation_policy_dry_run_validation"


def test_overall_result_warn_review(tmp_path: Path) -> None:
    validation_path = build_validation_result(tmp_path, "WARN")
    result = generate_security_phase_s4_overall_result(
        validation_result_path=validation_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ISOLATION_DESIGN_REVIEW_REQUIRED"


def test_overall_result_fail_review(tmp_path: Path) -> None:
    validation_path = build_validation_result(tmp_path, "FAIL")
    result = generate_security_phase_s4_overall_result(
        validation_result_path=validation_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ISOLATION_DESIGN_REVIEW_REQUIRED"


def test_overall_result_abort(tmp_path: Path) -> None:
    validation_path = build_validation_result(tmp_path, "ABORT")
    result = generate_security_phase_s4_overall_result(
        validation_result_path=validation_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ABORT"
