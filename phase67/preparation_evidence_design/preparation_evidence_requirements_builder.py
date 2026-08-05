from __future__ import annotations


def build_preparation_evidence_requirements(package: dict) -> dict:
    return {
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "required_evidence": [
            "phase66_go_no_go_report_reference",
            "preparation_scope_statement",
            "target_files_manifest",
            "sandbox_scope_confirmation",
            "single_file_scope_confirmation",
            "dry_run_mode_confirmation",
            "non_execution_confirmation",
        ],
        "preparation_evidence_does_not_execute": True,
        "status": "PREPARATION_EVIDENCE_REQUIREMENTS_READY",
    }
