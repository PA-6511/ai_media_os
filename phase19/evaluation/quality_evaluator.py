from __future__ import annotations


def evaluate_quality(phase18_result: dict) -> dict:
    execution_status = phase18_result.get("execution_status")
    verify_status = phase18_result.get("verify_status")
    applied_files = phase18_result.get("applied_files", [])
    blocked_files = phase18_result.get("blocked_files", [])
    findings = list(phase18_result.get("findings", []))

    if execution_status != "PASS" or verify_status == "FAIL":
        quality_status = "FAIL"
        score = 20
        findings.append("execution_or_verify_failed")
    elif blocked_files:
        quality_status = "WARN"
        score = 70
        findings.append("blocked_files_present")
    elif execution_status == "PASS" and verify_status == "PASS":
        quality_status = "PASS"
        score = 100
    else:
        quality_status = "WARN"
        score = 60

    findings.append(f"applied_files_count={len(applied_files)}")
    findings.append(f"blocked_files_count={len(blocked_files)}")

    return {
        "quality_status": quality_status,
        "score": score,
        "findings": findings,
    }
