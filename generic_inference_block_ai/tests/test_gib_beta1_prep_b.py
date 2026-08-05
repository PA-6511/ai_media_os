from __future__ import annotations

import json
from pathlib import Path

from generic_inference_block_ai.src.gib_beta1_prep_b import evaluate_beta1_prep_b, load_json
from generic_inference_block_ai.src.gib_beta1_prep_b_validator import validate_beta1_prep_b_contract


def _base_config() -> dict:
    return {
        "schema_version": "gib.beta1.prep_b.approval_protocol.v0.1",
        "phase": "beta1_prep_b",
        "status": "DRY_RUN_BETA1_PREP_B_APPROVAL_PROTOCOL_ONLY",
        "production_status": "NO_GO",
        "real_llm_call_allowed": False,
        "execution_allowed": False,
        "generate_call_allowed": False,
        "chat_call_allowed": False,
        "can_execute_now": False,
        "output_scope": "generic_inference_block_ai/reports",
        "approval_protocol": {
            "required_approval_statement_template": "ApprovalToken={APPROVAL_TOKEN_ID}; ChangeID={CHANGE_MANAGEMENT_ID}; This approval does not authorize automatic execution.",
            "required_identifiers": ["APPROVAL_TOKEN_ID", "CHANGE_MANAGEMENT_ID"],
            "identifier_reference_rules": {
                "approval_token": "^APR-[0-9]{8}-[A-Z0-9]{6}$",
                "change_management_id": "^CHG-[0-9]{8}-[A-Z0-9]{4}$",
            },
            "manual_only": True,
            "auto_execute_after_approval": False,
        },
        "non_execution_guards": {
            "keep_real_llm_call_allowed_false": True,
            "keep_execution_allowed_false": True,
            "keep_generate_chat_unexecuted": True,
            "wordpress_write_forbidden": True,
            "credential_access_forbidden": True,
            "systemd_forbidden": True,
        },
        "required_prerequisites": {
            "beta1_prep_report": "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED",
            "beta1_prep_a_report": "PASS_REPORTS_ONLY_BETA1_PREP_AUDIT_INDEX_FIXED",
        },
    }


def _prep_ok() -> dict:
    return {
        "final_status": "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED",
        "can_execute_now": False,
    }


def _prep_a_ok() -> dict:
    return {
        "final_status": "PASS_REPORTS_ONLY_BETA1_PREP_AUDIT_INDEX_FIXED",
        "reference_reports_ready": True,
        "guardrail_continuity": {
            "all_real_llm_call_allowed_false": True,
            "all_execution_allowed_false": True,
            "all_can_execute_now_false": True,
        },
    }


def test_beta1_prep_b_contract_passes_and_stays_no_execution() -> None:
    report = validate_beta1_prep_b_contract()

    assert report["final_status"] == "PASS_REPORTS_ONLY_BETA1_PREP_B_APPROVAL_PROTOCOL_FIXED"
    assert report["report_type"] == "BETA1_PREP_B_APPROVAL_PROTOCOL_REPORTS_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["output_scope"] == "generic_inference_block_ai/reports"
    assert report["prerequisites_ok"] is True
    assert report["protocol_ok"] is True
    assert report["non_execution_ok"] is True
    assert report["real_llm_call_allowed"] is False
    assert report["execution_allowed"] is False
    assert report["generate_call_allowed"] is False
    assert report["chat_call_allowed"] is False
    assert report["can_execute_now"] is False


def test_beta1_prep_b_config_failure_is_detected(tmp_path: Path) -> None:
    cfg = _base_config()
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")

    loaded = load_json(p)
    loaded["execution_allowed"] = True

    result = evaluate_beta1_prep_b(loaded, _prep_ok(), _prep_a_ok())
    assert result.config_valid is False
    assert "execution_allowed must be false" in result.config_issues


def test_beta1_prep_b_prereq_failure_is_detected() -> None:
    bad_prep = {"final_status": "FAIL", "can_execute_now": True}
    bad_prep_a = {
        "final_status": "FAIL",
        "reference_reports_ready": False,
        "guardrail_continuity": {
            "all_real_llm_call_allowed_false": False,
            "all_execution_allowed_false": False,
            "all_can_execute_now_false": False,
        },
    }

    result = evaluate_beta1_prep_b(_base_config(), bad_prep, bad_prep_a)
    assert result.prerequisites_ok is False
    assert result.can_execute_now is False


def test_beta1_prep_b_protocol_template_placeholder_failure_is_detected() -> None:
    cfg = _base_config()
    cfg["approval_protocol"]["required_approval_statement_template"] = "manual approval only"

    result = evaluate_beta1_prep_b(cfg, _prep_ok(), _prep_a_ok())
    assert result.protocol_ok is False
    assert "approval statement template must contain {APPROVAL_TOKEN_ID}" in result.protocol_issues
    assert "approval statement template must contain {CHANGE_MANAGEMENT_ID}" in result.protocol_issues
