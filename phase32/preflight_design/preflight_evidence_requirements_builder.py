from __future__ import annotations


def build_preflight_evidence_requirements(preflight_package: dict) -> dict:
    if preflight_package.get("status") != "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY":
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_preflight_package_not_ready",
        }

    return {
        "evidence_required": True,
        "required_artifacts": [
            "target_file_path",
            "sandbox_proof",
            "manual_approval_record",
            "preflight_controls_snapshot",
            "preflight_stop_conditions_snapshot",
            "policy_evaluation_result",
        ],
        "missing_evidence_blocks_progress": True,
        "preflight_evidence_does_not_execute": True,
        "status": "PREFLIGHT_EVIDENCE_REQUIREMENTS_READY",
    }
