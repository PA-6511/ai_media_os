from __future__ import annotations


def build_readiness_review_evidence_requirements(package: dict) -> dict:
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
        "readiness_review_evidence_does_not_execute": True,
        "status": "READINESS_REVIEW_EVIDENCE_REQUIREMENTS_READY",
    }
