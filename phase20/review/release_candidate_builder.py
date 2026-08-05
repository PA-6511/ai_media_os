from __future__ import annotations


def build_release_candidate_package(design_review_package: dict) -> dict:
    if design_review_package.get("status") != "REVIEW_READY":
        return {
            "phase": "20",
            "mode": "DRY_RUN",
            "human_approval_required": True,
            "status": "FAIL",
            "reason": "design_review_not_ready",
        }

    return {
        "phase": "20",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "candidate_manifest": {
            "source_phase": "19",
            "review_status": "REVIEW_READY",
            "artifacts": ["design_review_package", "phase19_report"],
        },
        "non_goals": [
            "no_live_apply",
            "no_merge",
            "no_delete_operation",
        ],
        "constraints": [
            "sandbox_only_context",
            "dry_run_only",
            "human_approval_required",
        ],
        "apply_instruction": "DO_NOT_APPLY_IN_PHASE20",
        "status": "RC_PACKAGE_READY",
    }
