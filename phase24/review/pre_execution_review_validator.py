from __future__ import annotations

_REQUIRED_KEYS = [
    "phase",
    "mode",
    "human_approval_required",
    "review_scope",
    "max_files_to_execute",
    "execute_allowed",
    "status",
]


def validate_pre_execution_review(review: dict) -> dict:
    findings: list[str] = []
    missing_keys = [key for key in _REQUIRED_KEYS if key not in review]
    if missing_keys:
        findings.append("missing_keys:" + ",".join(missing_keys))

    if review.get("phase") != "24":
        findings.append("phase_must_be_24")
    if review.get("mode") != "DRY_RUN":
        findings.append("mode_must_be_dry_run")
    if review.get("human_approval_required") is not True:
        findings.append("human_approval_required_must_be_true")
    if review.get("review_scope") != "single_file_pre_execution_review_only":
        findings.append("review_scope_invalid")
    if review.get("max_files_to_execute") != 1:
        findings.append("max_files_to_execute_must_be_1")
    if review.get("execute_allowed") is not False:
        findings.append("execute_allowed_must_be_false")

    return {"status": "PASS" if not findings else "FAIL", "findings": findings}
