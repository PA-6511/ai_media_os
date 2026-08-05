from __future__ import annotations


def build_execution_checklist(plan: dict) -> dict:
    _ = plan
    return {
        "status": "EXECUTION_CHECKLIST_READY",
        "items": [
            "confirm_single_file_scope",
            "confirm_dry_run_mode",
            "confirm_manual_approval_attached",
            "confirm_no_delete",
            "confirm_no_auto_merge",
            "confirm_no_production_execute",
            "confirm_evidence_format_ready",
        ],
    }
