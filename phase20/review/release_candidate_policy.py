from __future__ import annotations

import json

_FORBIDDEN_TERMS = [
    "APPLY_NOW",
    "APPLY_LIVE",
    "MERGE_NOW",
    "AUTO_MERGE",
    "DELETE",
    "PRODUCTION",
    "DEPLOY",
    "WRITE_LIVE",
]


def evaluate_release_candidate_policy(rc_package: dict) -> dict:
    reasons: list[str] = []

    if rc_package.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")

    if rc_package.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")

    if rc_package.get("apply_instruction") != "DO_NOT_APPLY_IN_PHASE20":
        reasons.append("apply_instruction_invalid")

    serialized = json.dumps(rc_package, ensure_ascii=False).upper()
    for term in _FORBIDDEN_TERMS:
        if term in serialized:
            reasons.append(f"forbidden_term_detected:{term}")

    policy_status = "PASS" if not reasons else "FAIL"
    return {
        "policy_status": policy_status,
        "reasons": reasons,
    }
