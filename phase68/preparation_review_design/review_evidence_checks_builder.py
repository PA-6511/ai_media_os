from __future__ import annotations


def build_review_evidence_checks(package: dict) -> dict:
    return {
        "evidence_checks_required": True,
        "missing_evidence_blocks_progress": True,
        "required_checks": [
            "phase67_report_reference",
            "preparation_scope_consistency",
            "target_files_manifest_consistency",
            "sandbox_scope_confirmation",
            "single_file_scope_confirmation",
            "non_execution_confirmation",
        ],
        "review_evidence_checks_does_not_execute": True,
        "status": "REVIEW_EVIDENCE_CHECKS_READY",
    }
