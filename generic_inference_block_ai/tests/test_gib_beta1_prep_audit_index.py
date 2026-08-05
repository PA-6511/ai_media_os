from __future__ import annotations

import json
from pathlib import Path

from generic_inference_block_ai.src.gib_beta1_prep_audit_index import (
    build_beta1_prep_audit_index,
    write_beta1_prep_audit_index,
)


def test_beta1_prep_audit_index_pass_on_current_reports() -> None:
    report = build_beta1_prep_audit_index()

    assert report["final_status"] == "PASS_REPORTS_ONLY_BETA1_PREP_AUDIT_INDEX_FIXED"
    assert report["phase"] == "beta1_prep_a"
    assert report["report_type"] == "BETA1_PREP_AUDIT_INDEX_REPORTS_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["reference_reports_ready"] is True

    continuity = report["guardrail_continuity"]
    assert continuity["all_real_llm_call_allowed_false"] is True
    assert continuity["all_execution_allowed_false"] is True
    assert continuity["all_can_execute_now_false"] is True
    assert continuity["violations"] == []


def test_beta1_prep_audit_index_detects_true_flags(tmp_path: Path) -> None:
    freeze = {
        "report_type": "BETA099_FINAL_FREEZE_REPORT",
        "safety_summary": {
            "real_llm_call_allowed": False,
            "execution_allowed": False,
            "can_execute_now": False,
            "production_status": "NO_GO",
        },
    }
    prep = {
        "phase": "beta1_prep",
        "final_status": "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED",
        "status": "DRY_RUN_BETA1_PREP_ONLY",
        "production_status": "NO_GO",
        "real_llm_call_allowed": False,
        "execution_allowed": False,
        "can_execute_now": False,
    }
    violating = {
        "phase": "betaX",
        "final_status": "TEST",
        "status": "TEST",
        "production_status": "NO_GO",
        "real_llm_call_allowed": True,
        "execution_allowed": True,
        "can_execute_now": True,
    }

    (tmp_path / "gib_beta099_freeze_report.json").write_text(json.dumps(freeze), encoding="utf-8")
    (tmp_path / "gib_beta1_prep_validation_report.json").write_text(json.dumps(prep), encoding="utf-8")
    (tmp_path / "gib_violation_report.json").write_text(json.dumps(violating), encoding="utf-8")

    report = build_beta1_prep_audit_index(tmp_path)

    assert report["reference_reports_ready"] is True
    assert report["final_status"] == "FAIL_BETA1_PREP_AUDIT_INDEX"

    continuity = report["guardrail_continuity"]
    assert continuity["all_real_llm_call_allowed_false"] is False
    assert continuity["all_execution_allowed_false"] is False
    assert continuity["all_can_execute_now_false"] is False
    assert len(continuity["violations"]) == 3


def test_beta1_prep_audit_index_missing_reference_reports_fails(tmp_path: Path) -> None:
    only_one = {
        "phase": "beta1_prep",
        "final_status": "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED",
        "status": "DRY_RUN_BETA1_PREP_ONLY",
        "production_status": "NO_GO",
        "real_llm_call_allowed": False,
        "execution_allowed": False,
        "can_execute_now": False,
    }
    (tmp_path / "gib_beta1_prep_validation_report.json").write_text(json.dumps(only_one), encoding="utf-8")

    report = build_beta1_prep_audit_index(tmp_path)

    assert report["reference_reports_ready"] is False
    assert report["missing_reference_reports"] == ["gib_beta099_freeze_report.json"]
    assert report["final_status"] == "FAIL_BETA1_PREP_AUDIT_INDEX"


def test_beta1_prep_audit_index_writer_creates_report(tmp_path: Path) -> None:
    freeze = {
        "report_type": "BETA099_FINAL_FREEZE_REPORT",
        "safety_summary": {
            "real_llm_call_allowed": False,
            "execution_allowed": False,
            "can_execute_now": False,
            "production_status": "NO_GO",
        },
    }
    prep = {
        "phase": "beta1_prep",
        "final_status": "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED",
        "status": "DRY_RUN_BETA1_PREP_ONLY",
        "production_status": "NO_GO",
        "real_llm_call_allowed": False,
        "execution_allowed": False,
        "can_execute_now": False,
    }

    (tmp_path / "gib_beta099_freeze_report.json").write_text(json.dumps(freeze), encoding="utf-8")
    (tmp_path / "gib_beta1_prep_validation_report.json").write_text(json.dumps(prep), encoding="utf-8")

    output = write_beta1_prep_audit_index(tmp_path)
    assert output.exists()

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["report_type"] == "BETA1_PREP_AUDIT_INDEX_REPORTS_ONLY"
