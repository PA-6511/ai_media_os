from __future__ import annotations


def build_rerun_report(verify_result: dict, triage_result: dict) -> dict:
    """Build a compact rerun report with phase15 pipeline status."""
    category = triage_result.get("category", "UNKNOWN")
    returncode = verify_result.get("returncode", 1)

    if category == "PASS" and returncode == 0:
        pipeline_status = "PASS"
    elif category in {"IMPORT_ERROR", "SYNTAX_ERROR", "TEST_ASSERTION_FAILED", "TIMEOUT"}:
        pipeline_status = "WARN"
    else:
        pipeline_status = "FAIL"

    return {
        "phase": "15",
        "pipeline_status": pipeline_status,
        "verify_result": verify_result,
        "triage_result": triage_result,
    }
