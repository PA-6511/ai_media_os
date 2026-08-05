from __future__ import annotations


def build_pre_apply_checklist(plan: dict) -> dict:
    _ = plan
    return {
        "status": "CHECKLIST_READY",
        "items": [
            "confirm_single_file_scope",
            "confirm_target_file_exists",
            "confirm_no_delete_operation",
            "confirm_no_auto_merge",
            "confirm_no_production_apply",
            "confirm_dry_run_mode",
            "confirm_manual_approval_present",
        ],
    }
