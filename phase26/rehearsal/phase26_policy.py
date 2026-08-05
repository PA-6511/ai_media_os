from __future__ import annotations


def evaluate_phase26_policy(
    procedure: dict,
    observation_points: dict,
    abort_conditions: dict,
    evidence_review: dict,
) -> dict:
    reasons: list[str] = []

    if procedure.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if procedure.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if procedure.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if procedure.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")

    if observation_points.get("status") != "OBSERVATION_POINTS_READY":
        reasons.append("observation_points_not_ready")
    if abort_conditions.get("status") != "ABORT_CONDITIONS_READY":
        reasons.append("abort_conditions_not_ready")

    if evidence_review.get("evidence_review_required") is not True:
        reasons.append("evidence_review_required_not_true")
    if evidence_review.get("evidence_does_not_execute") is not True:
        reasons.append("evidence_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
