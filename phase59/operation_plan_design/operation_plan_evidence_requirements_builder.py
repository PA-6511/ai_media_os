from __future__ import annotations


def build_operation_plan_evidence_requirements(package: dict) -> dict:
    return {
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "required_evidence": [
            "manual_approval_reference",
            "policy_snapshot",
            "target_file",
            "sandbox_scope_confirmation",
            "single_file_scope_confirmation",
            "dry_run_mode_confirmation",
        ],
        "operation_plan_evidence_does_not_execute": True,
        "status": "OPERATION_PLAN_EVIDENCE_REQUIREMENTS_READY",
    }
